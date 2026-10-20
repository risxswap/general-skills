"""Behavior checks for split-skill asset modes and versioned report policy."""
from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from test_case_language import prepare, snapshot
from test_scripts import FIXTURES, run_script


class SingleTypeAssetsTests(unittest.TestCase):
    def test_single_api_single_ui_and_mixed_catalogs(self):
        for selected, expected in (("api", 1), ("ui", 2), ("all", 3)):
            with self.subTest(selected=selected), tempfile.TemporaryDirectory() as temporary:
                project = Path(temporary)
                cases, api_map, ui_map, output = prepare(project)
                if selected != "all":
                    shutil.rmtree(ui_map.parent if selected == "api" else api_map.parent)
                for alias in ("--asset-root", "--vault-root"):
                    result = run_script("validate_cases.py", project, alias, project, "--json")
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(json.loads(result.stdout)["case_count"], expected)
                result = run_script("build_catalog.py", project, "--asset-root", project)
                self.assertEqual(result.returncode, 0, result.stderr)
                catalog = json.loads(output.read_text())
                self.assertEqual(catalog["schema_version"], 5)
                self.assertEqual(len(catalog["maps"]), 2 if selected == "all" else 1)
                self.assertEqual(len(catalog["cases"]), expected)

    def test_missing_map_never_hides_existing_type(self):
        for kind in ("api", "ui"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                project = Path(temporary)
                _, api_map, ui_map, output = prepare(project)
                (api_map if kind == "api" else ui_map).unlink()
                before = snapshot(project)
                for script in ("validate_cases.py", "build_catalog.py", "init_testing.py"):
                    result = run_script(script, project)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn("地图", result.stderr + result.stdout)
                self.assertFalse(output.exists())
                self.assertEqual(snapshot(project), before)

    def test_single_type_initialization_is_incremental_and_keeps_history(self):
        for first in ("api", "ui"):
            with self.subTest(first=first), tempfile.TemporaryDirectory() as temporary:
                project = Path(temporary)
                selected = "01-api" if first == "api" else "02-ui-integration"
                other = "02-ui-integration" if first == "api" else "01-api"
                root = project / "docs/testing"
                result = run_script("init_testing.py", project, "--types", first)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue((root / "01-cases" / selected).is_dir())
                self.assertFalse((root / "01-cases" / other).exists())
                self.assertTrue((project / "docs/plan").is_dir())
                self.assertFalse((root / "03-plans").exists())
                history = root / "04-runs/historical.json"
                history.write_text('{"run":"unchanged"}')
                before = snapshot(project)
                self.assertEqual(run_script("init_testing.py", project, "--types", first).returncode, 0)
                self.assertEqual(snapshot(project), before)
                result = run_script("init_testing.py", project)
                self.assertEqual(result.returncode, 0, result.stderr)
                after = snapshot(project)
                self.assertTrue((root / "01-cases" / other).is_dir())
                for path, content in before.items():
                    self.assertEqual(after[path], content)

    def test_existing_single_type_cases_allow_incremental_other_type(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            _, _, ui_map, _ = prepare(project)
            shutil.rmtree(ui_map.parent)
            before = snapshot(project)
            result = run_script("init_testing.py", project, "--types", "ui")
            self.assertEqual(result.returncode, 0, result.stderr)
            for path, content in before.items():
                self.assertEqual(snapshot(project)[path], content)
            self.assertEqual(run_script("validate_cases.py", project).returncode, 0)

    def test_asset_root_and_explicit_map_boundaries_are_checked(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            project = Path(temporary)
            cases, api_map, ui_map, output = prepare(project)
            for args in (("--asset-root", project / "docs/testing/01-cases/01-api"),
                         ("--asset-root", project, "--ui-map", Path(outside) / "missing.md"),
                         ("--asset-root", project, "--ui-map", ui_map.parent / "missing.md")):
                result = run_script("build_catalog.py", project, *args)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())

    def test_plan_directory_symlink_is_rejected_before_writes(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            project = Path(temporary)
            (project / "docs").mkdir()
            (project / "docs/plan").symlink_to(outside, target_is_directory=True)
            result = run_script("init_testing.py", project, "--types", "api")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((project / "docs/testing").exists())
            self.assertEqual(list(Path(outside).iterdir()), [])


class ConclusionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / "run"
        shutil.copytree(FIXTURES / "report", self.run)
        self.manifest_path = self.run / "manifest.json"
        self.results_path = self.run / "results.jsonl"
        self.output = self.root / "report"
        self.manifest = json.loads(self.manifest_path.read_text())
        self.manifest["conclusion_policy"] = "testing-workflow-v1"
        self.manifest["planned_cases"] = self.manifest["planned_cases"][:1]
        self.case = self.manifest["planned_cases"][0]
        self.manifest["requirements"] = self.case["requirement_ids"]
        self.manifest["operations"] = [self.case["operation_id"]]
        self.records = [json.loads(self.results_path.read_text().splitlines()[0])]
        self.records[0]["status"] = "Passed"

    def generate(self):
        self.manifest_path.write_text(json.dumps(self.manifest, ensure_ascii=False))
        self.results_path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in self.records))
        before = snapshot(self.run)
        result = run_script("generate_report.py", "--manifest", self.manifest_path,
                            "--results", self.results_path, "--output-dir", self.output)
        self.assertEqual(snapshot(self.run), before, "Report must preserve input and evidence")
        return result

    def assert_conclusion(self, expected):
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stderr)
        markdown = (self.output / "report.md").read_text()
        html = (self.output / "report.html").read_text()
        self.assertIn(f"| 批次结论 | {expected} |", markdown)
        self.assertIn(f"<strong>{expected}</strong>", html)
        for rendered in (markdown, html):
            self.assertIn(self.manifest.get("conclusion_policy", "legacy-v1"), rendered)
        return markdown, html

    def failure(self, classification="产品缺陷"):
        self.records[0].update(status="Failed", failure_step="独有失败步骤", expected="独有预期",
                               actual="独有实际", next_action="独有后续动作", failure_classification=classification)

    def test_all_satisfied_is_passed(self):
        self.assert_conclusion("Passed")

    def test_product_failure_always_fails_even_optional_or_retried(self):
        for required in (True, False):
            for retry in (True, False):
                with self.subTest(required=required, retry=retry):
                    self.case["required_for_conclusion"] = required
                    self.records = self.records[:1]
                    self.failure()
                    if retry:
                        self.records.append({**self.records[0], "attempt": 2, "status": "Passed"})
                    markdown, html = self.assert_conclusion("Failed")
                    for rendered in (markdown, html):
                        for fact in ("独有失败步骤", "独有预期", "独有实际", "独有后续动作", "产品缺陷", self.case["source"]):
                            self.assertIn(fact, rendered)
                    if retry:
                        self.assertIn("Attempt 2", html)
                        self.assertIn("Attempt 1", html)

    def test_unknown_failures_block_even_optional_or_retried(self):
        self.case["required_for_conclusion"] = False
        self.failure("待分析")
        self.assert_conclusion("Blocked")
        self.records.append({**self.records[0], "attempt": 2, "status": "Passed"})
        self.assert_conclusion("Blocked")

    def test_nonproduct_failure_depends_on_requirement_and_can_be_resolved(self):
        for classification in ("用例缺陷", "自动化脚本问题", "环境问题", "测试数据问题", "接口文档问题"):
            for required, expected in ((True, "Blocked"), (False, "PassedWithRisk")):
                with self.subTest(classification=classification, required=required):
                    self.records = self.records[:1]
                    self.case["required_for_conclusion"] = required
                    self.failure(classification)
                    self.assert_conclusion(expected)
                    self.records.append({**self.records[0], "attempt": 2, "status": "Passed"})
                    self.assert_conclusion("Passed")

    def test_required_and_optional_unverified_statuses(self):
        for status in ("Blocked", "Skipped", "NotExecuted"):
            for required, expected in ((True, "Blocked"), (False, "PassedWithRisk")):
                with self.subTest(status=status, required=required):
                    self.case["required_for_conclusion"] = required
                    self.records[0].update(status=status, reason="缺少账号", unblock_condition="提供测试账号")
                    self.assert_conclusion(expected)

    def test_legacy_replay_preserves_its_conclusion(self):
        self.manifest.pop("conclusion_policy")
        self.failure("产品缺陷")
        self.records.append({**self.records[0], "attempt": 2, "status": "Passed"})
        self.assert_conclusion("PassedWithRisk")
        self.manifest["conclusion_policy"] = "testing-workflow-v1"
        self.assert_conclusion("Failed")

    def test_defect_verification_cannot_hide_a_failed_attempt(self):
        self.case["verification_group"] = "直接验证"
        self.manifest["verification"] = {
            "bug_ids": ["BUG-001"], "source_run_id": "RUN-ORIGINAL",
            "source_application_version": "1.0",
            "source_results": [{"case_id": self.case["case_id"], "attempts": [{"attempt": 1, "status": "Failed"}]}],
        }
        for classification, overall, verification in (("产品缺陷", "Failed", "NotFixed"), ("待分析", "Blocked", "CannotVerify")):
            with self.subTest(classification=classification):
                self.records = self.records[:1]
                self.failure(classification)
                self.records.append({**self.records[0], "attempt": 2, "status": "Passed"})
                markdown, html = self.assert_conclusion(overall)
                self.assertIn(f"验证结论：{verification}", markdown)
                self.assertIn(verification, html)

    def test_legacy_optional_blocked_is_replayed_without_reinterpreting(self):
        self.manifest["conclusion_policy"] = "legacy-v1"
        self.case["required_for_conclusion"] = False
        self.records[0].update(status="Blocked", reason="历史账号缺失", unblock_condition="提供账号")
        self.assert_conclusion("Passed")
        self.manifest["conclusion_policy"] = "testing-workflow-v1"
        self.assert_conclusion("PassedWithRisk")

    def test_unknown_policy_and_missing_facts_do_not_write_reports(self):
        for mutation in ("unknown_policy", "no_plan", "no_record", "no_classification", "no_source"):
            with self.subTest(mutation=mutation):
                manifest, records = copy.deepcopy(self.manifest), copy.deepcopy(self.records)
                if mutation == "unknown_policy": self.manifest["conclusion_policy"] = "future-v2"
                if mutation == "no_plan": self.manifest.pop("plan_id")
                if mutation == "no_record": self.records = []
                if mutation == "no_classification":
                    self.failure()
                    self.records[0].pop("failure_classification")
                if mutation == "no_source": self.records[0].pop("source")
                result = self.generate()
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.output.exists())
                self.manifest, self.records = manifest, records

    def test_evidence_symlink_cannot_escape_run(self):
        outside = self.root / "private.txt"
        outside.write_text("external content")
        evidence = self.run / "evidence/external.txt"
        evidence.symlink_to(outside)
        self.records[0]["evidence"] = ["evidence/external.txt"]
        result = self.generate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("越出运行目录", result.stderr)
        self.assertFalse(self.output.exists())

    def test_report_target_symlink_cannot_overwrite_evidence(self):
        self.output.mkdir()
        target = self.output / "report.md"
        target.symlink_to(self.run / "evidence/API-001-attempt-1.txt")
        result = self.generate()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.output / "report.html").exists())


if __name__ == "__main__":
    unittest.main()
