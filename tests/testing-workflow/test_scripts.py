from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from html import escape
from html.parser import HTMLParser
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[2] / "skills/testing-workflow/scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ReportHTMLInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))


def run_script(name: str, *args: object, python_args: tuple[str, ...] = ()) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *python_args, str(SCRIPTS / name), *(str(arg) for arg in args)],
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


class ReportTests(unittest.TestCase):
    def prepare_run(self, temporary: str) -> tuple[Path, Path, Path]:
        run_dir = Path(temporary) / "docs" / "testing" / "04-runs" / "RUN-20260908-001"
        shutil.copytree(FIXTURES / "report", run_dir)
        output = Path(temporary) / "docs" / "testing" / "05-reports" / "RUN-20260908-001"
        return run_dir / "manifest.json", run_dir / "results.jsonl", output

    def read_manifest(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def write_manifest(self, path: Path, manifest: dict) -> None:
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def read_results(self, path: Path) -> list[dict]:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def write_results(self, path: Path, records: list[dict]) -> None:
        path.write_text(
            "".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n" for record in records),
            encoding="utf-8",
        )

    def test_generates_consistent_markdown_and_html_with_five_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest, results, output = self.prepare_run(temporary)
            result = run_script("generate_report.py", "--manifest", manifest, "--results", results, "--output-dir", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = (output / "report.md").read_text(encoding="utf-8")
            html = (output / "report.html").read_text(encoding="utf-8")
            for status in ("Passed", "Failed", "Blocked", "Skipped", "NotExecuted"):
                self.assertIn(status, markdown)
                self.assertIn(status, html)
            self.assertIn("| 总用例数 | 5 |", markdown)
            self.assertIn("| Passed | 1 / 5 (20.0%) |", markdown)
            self.assertIn("| 通过率（Passed / (Passed + Failed)） | 50.0% |", markdown)
            self.assertIn("| 执行完成率（非 NotExecuted / 总数） | 80.0% |", markdown)
            self.assertIn("| 需求覆盖率 | 40.0% |", markdown)
            self.assertIn("| 接口覆盖率 | 100.0% |", markdown)
            self.assertIn("API-001-attempt-1.txt", markdown)
            self.assertIn("Attempt | 执行器", markdown)
            self.assertIn("agent-browser", markdown)
            self.assertIn("playwright", markdown)
            self.assertIn("### P0/P1 风险", markdown)
            self.assertIn("历史失败后重试通过", markdown)
            for case_id in ("API-001", "API-002", "UI-001", "UI-002", "UI-003"):
                self.assertIn(case_id, markdown)
                self.assertIn(case_id, html)
            self.assertIn("50.0%", html)
            self.assertIn("80.0%", html)
            self.assertIn("Attempt 1", html)
            self.assertIn("Attempt 2", html)
            self.assertIn("模块风险矩阵", html)
            self.assertIn('href="#case-', html)

    def test_html_supports_all_filters_sorting_and_per_case_details_without_javascript(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest, results, output = self.prepare_run(temporary)
            result = run_script("generate_report.py", "--manifest", manifest, "--results", results, "--output-dir", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = (output / "report.html").read_text(encoding="utf-8")
            inspector = ReportHTMLInspector()
            inspector.feed(report)
            filters = {
                attrs["data-filter"]
                for tag, attrs in inspector.tags
                if tag == "select" and "data-filter" in attrs
            }
            self.assertEqual(
                filters,
                {"status", "executor", "caseType", "module", "priority", "requirements", "operation", "failureClassification", "hasBug"},
            )
            sort_buttons = [attrs for tag, attrs in inspector.tags if tag == "button" and "data-sort-index" in attrs]
            self.assertEqual(len(sort_buttons), 10)
            self.assertEqual({attrs["data-sort-index"] for attrs in sort_buttons}, {str(index) for index in range(10)})
            case_rows = [attrs for tag, attrs in inspector.tags if tag == "tr" and "data-case-row" in attrs]
            self.assertEqual(len(case_rows), 5)
            self.assertTrue(all("data-requirements" in attrs and "data-executor" in attrs and "data-has-bug" in attrs for attrs in case_rows))
            self.assertEqual(sum(1 for tag, _ in inspector.tags if tag == "details"), 5)
            self.assertIn("JSON.parse(row.dataset.requirements)", report)
            self.assertIn("localeCompare", report)
            reset_buttons = [attrs for tag, attrs in inspector.tags if tag == "button" and attrs.get("id") == "reset-filters"]
            self.assertEqual(len(reset_buttons), 1)
            section_ids = {
                attrs["id"]
                for tag, attrs in inspector.tags
                if tag == "section" and attrs.get("id")
            }
            self.assertTrue({"overview", "risks", "cases", "failures", "coverage", "evidence", "residual"}.issubset(section_ids))
            self.assertIn('class="state-badge state-failed"', report)
            self.assertIn('class="coverage-badge coverage-covered"', report)
            self.assertIn('class="badge-list"', report)
            self.assertIn('href="#requirement-', report)
            self.assertIn('href="#operation-', report)
            self.assertIn("resetButton.addEventListener", report)
            self.assertIn('class="report-header report-header-failed"', report)
            self.assertIn('class="nav-run"', report)
            self.assertIn('class="time-range"', report)
            self.assertIn("window.addEventListener('scroll'", report)
            self.assertIn("@media (max-width: 420px)", report)
            self.assertNotIn("https://", report)

            static_report = report.split("<script>", 1)[0]
            self.assertIn("<strong>总用例数</strong>", static_report)
            self.assertIn('<span class="metric-value">5</span>', static_report)
            failure_section = static_report.split("<h2>失败与阻塞</h2>", 1)[1].split("<h2>覆盖分析</h2>", 1)[0]
            self.assertIn("API-002", failure_section)
            self.assertIn("404", failure_section)
            self.assertIn('<details class="case-details">', static_report)
            self.assertIn("Attempt 2", static_report)

    def test_both_reports_preserve_scope_notes_and_html_escapes_them(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest, results, output = self.prepare_run(temporary)
            run_manifest = self.read_manifest(manifest)
            notes = {
                "excluded": "排除范围：支付通道 <img src=x onerror=alert(1)>",
                "unverified": "未验证范围：导出页面 <img src=y onerror=alert(2)>",
                "residual_risks": "剩余风险：共享数据 <img src=z onerror=alert(3)>",
            }
            run_manifest.update({field: [value] for field, value in notes.items()})
            self.write_manifest(manifest, run_manifest)
            result = run_script("generate_report.py", "--manifest", manifest, "--results", results, "--output-dir", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = (output / "report.md").read_text(encoding="utf-8")
            report = (output / "report.html").read_text(encoding="utf-8")
            for field, value in notes.items():
                with self.subTest(field=field):
                    self.assertIn(value, markdown)
                    self.assertIn(escape(value), report)
                    self.assertNotIn(value, report)
            inspector = ReportHTMLInspector()
            inspector.feed(report)
            self.assertFalse(any(tag == "img" or "onerror" in attrs for tag, attrs in inspector.tags))
            self.assertIn("<h3>排除项</h3>", report)

    def test_html_escapes_dynamic_text_and_data_attributes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest, results, output = self.prepare_run(temporary)
            malicious = '用户"><img src=x onerror=alert(1)>'
            records = self.read_results(results)
            for record in records:
                if record["module"] == "用户":
                    record["module"] = malicious
            run_manifest = self.read_manifest(manifest)
            for planned in run_manifest["planned_cases"]:
                if planned["module"] == "用户":
                    planned["module"] = malicious
            self.write_results(results, records)
            self.write_manifest(manifest, run_manifest)
            result = run_script("generate_report.py", "--manifest", manifest, "--results", results, "--output-dir", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = (output / "report.html").read_text(encoding="utf-8")
            self.assertNotIn(malicious, report)
            self.assertNotIn("<img src=x onerror=alert(1)>", report)
            inspector = ReportHTMLInspector()
            inspector.feed(report)
            user_rows = [attrs for tag, attrs in inspector.tags if tag == "tr" and attrs.get("data-module") == malicious]
            self.assertEqual(len(user_rows), 2)
            self.assertTrue(all("onerror" not in attrs for attrs in user_rows))

    def test_rejects_malformed_jsonl_unknown_status_missing_source_and_sensitive_values(self) -> None:
        mutations = {
            "unknown": (lambda record: record.update(status="Unknown"), "状态无效"),
            "missing_source": (lambda record: record.pop("source"), "source"),
            "sensitive": (lambda record: record.update(access_token="plain-secret"), "未脱敏"),
        }
        for name, (mutate, expected) in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                manifest, results, output = self.prepare_run(temporary)
                records = self.read_results(results)
                mutate(records[0])
                self.write_results(results, records)
                result = run_script("generate_report.py", "--manifest", manifest, "--results", results, "--output-dir", output)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)
                self.assertFalse((output / "report.md").exists())
        with tempfile.TemporaryDirectory() as temporary:
            manifest, results, output = self.prepare_run(temporary)
            results.write_text("{bad json}\n", encoding="utf-8")
            result = run_script("generate_report.py", "--manifest", manifest, "--results", results, "--output-dir", output)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("JSONL 无效", result.stderr)

    def test_rejects_missing_or_escaping_evidence_path(self) -> None:
        for evidence in ("evidence/missing.txt", "../outside.txt"):
            with self.subTest(evidence=evidence), tempfile.TemporaryDirectory() as temporary:
                manifest, results, output = self.prepare_run(temporary)
                records = self.read_results(results)
                record = next(item for item in records if item["case_id"] == "API-002")
                record["evidence"] = [evidence]
                self.write_results(results, records)
                result = run_script("generate_report.py", "--manifest", manifest, "--results", results, "--output-dir", output)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("证据", result.stderr)

    def test_rejects_manifest_identity_mismatch_and_attempt_gaps(self) -> None:
        for name, transform, expected in (
            (
                "run mismatch",
                lambda content: content.replace('"run_id":"RUN-20260908-001"', '"run_id":"RUN-OTHER"', 1),
                "与 manifest 不一致",
            ),
            (
                "attempt gap",
                lambda content: content.replace('"case_id":"API-001","case_revision":"r1","attempt":2', '"case_id":"API-001","case_revision":"r1","attempt":3'),
                "连续递增",
            ),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                manifest, results, output = self.prepare_run(temporary)
                results.write_text(transform(results.read_text(encoding="utf-8")), encoding="utf-8")
                result = run_script("generate_report.py", "--manifest", manifest, "--results", results, "--output-dir", output)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)

    def test_rejects_missing_and_unplanned_case_results(self) -> None:
        for name, mutate, expected in (
            (
                "missing",
                lambda records: [record for record in records if record["case_id"] != "UI-003"],
                "计划用例缺少结果记录",
            ),
            (
                "unplanned",
                lambda records: records + [{**records[-1], "case_id": "UI-999"}],
                "计划外用例",
            ),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                manifest, results, output = self.prepare_run(temporary)
                self.write_results(results, mutate(self.read_results(results)))

                result = run_script("generate_report.py", "--manifest", manifest, "--results", results, "--output-dir", output)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)

    def test_rejects_invalid_priority_classification_and_missing_api_operation(self) -> None:
        mutations = (
            (lambda record: record.update(priority="PX"), "priority"),
            (lambda record: record.update(failure_classification="未知分类"), "failure_classification 无效"),
            (lambda record: record.pop("operation_id"), "必须提供 operation_id"),
        )
        for mutate, expected in mutations:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temporary:
                manifest, results, output = self.prepare_run(temporary)
                records = self.read_results(results)
                target = next(record for record in records if record["case_id"] == "API-002")
                mutate(target)
                self.write_results(results, records)

                result = run_script("generate_report.py", "--manifest", manifest, "--results", results, "--output-dir", output)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)

    def test_rejects_manifest_timestamp_without_timezone(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest, results, output = self.prepare_run(temporary)
            run_manifest = self.read_manifest(manifest)
            run_manifest["started_at"] = "2026-09-08T10:00:00"
            self.write_manifest(manifest, run_manifest)

            result = run_script("generate_report.py", "--manifest", manifest, "--results", results, "--output-dir", output)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("必须包含时区", result.stderr)

    def test_conclusion_uses_required_plan_cases(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest, results, output = self.prepare_run(temporary)
            records = self.read_results(results)
            failed = next(record for record in records if record["case_id"] == "API-002")
            failed["status"] = "Passed"
            self.write_results(results, records)

            strict = run_script("generate_report.py", "--manifest", manifest, "--results", results, "--output-dir", output)
            self.assertEqual(strict.returncode, 0, strict.stderr)
            self.assertIn("| 批次结论 | Blocked |", (output / "report.md").read_text(encoding="utf-8"))

            run_manifest = self.read_manifest(manifest)
            next(item for item in run_manifest["planned_cases"] if item["case_id"] == "UI-001")["required_for_conclusion"] = False
            self.write_manifest(manifest, run_manifest)
            relaxed = run_script("generate_report.py", "--manifest", manifest, "--results", results, "--output-dir", output)
            self.assertEqual(relaxed.returncode, 0, relaxed.stderr)
            self.assertIn("| 批次结论 | PassedWithRisk |", (output / "report.md").read_text(encoding="utf-8"))

    def test_generates_defect_verification_comparison_and_conclusion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest, results, output = self.prepare_run(temporary)
            run_manifest = self.read_manifest(manifest)
            for planned in run_manifest["planned_cases"]:
                planned["verification_group"] = "直接验证" if planned["case_id"] == "API-001" else "影响回归"
            run_manifest["verification"] = {
                "bug_ids": ["BUG-001"],
                "source_run_id": "RUN-20260901-001",
                "source_application_version": "1.2.2",
                "source_results": [
                    {"case_id": "API-001", "attempts": [{"attempt": 1, "status": "Failed"}]}
                ],
            }
            self.write_manifest(manifest, run_manifest)

            result = run_script("generate_report.py", "--manifest", manifest, "--results", results, "--output-dir", output)

            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = (output / "report.md").read_text(encoding="utf-8")
            html = (output / "report.html").read_text(encoding="utf-8")
            self.assertIn("## 缺陷修复验证对比", markdown)
            self.assertIn("验证结论：RegressionFound", markdown)
            self.assertIn("Attempt 1: Failed, Attempt 2: Passed", markdown)
            self.assertIn("缺陷修复验证对比", html)
            self.assertIn("RegressionFound", html)

            records = self.read_results(results)
            next(record for record in records if record["case_id"] == "API-002")["failure_classification"] = "自动化脚本问题"
            self.write_results(results, records)
            rerun = run_script("generate_report.py", "--manifest", manifest, "--results", results, "--output-dir", output)
            self.assertEqual(rerun.returncode, 0, rerun.stderr)
            self.assertIn("验证结论：PartiallyVerified", (output / "report.md").read_text(encoding="utf-8"))

    def test_rejects_executor_that_does_not_match_case_type(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest, results, output = self.prepare_run(temporary)
            records = self.read_results(results)
            api_result = next(record for record in records if record["case_id"] == "API-002")
            api_result["executor"] = "agent-browser"
            api_result["executor_version"] = "Codex browser fixture-1"
            self.write_results(results, records)

            result = run_script("generate_report.py", "--manifest", manifest, "--results", results, "--output-dir", output)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("接口测试必须使用 http", result.stderr)

    def test_rejects_executor_switch_between_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest, results, output = self.prepare_run(temporary)
            records = self.read_results(results)
            original = next(record for record in records if record["case_id"] == "UI-001")
            retry = {**original, "attempt": 2, "executor": "agent-browser", "executor_version": "Codex browser fixture-1"}
            records.append(retry)
            self.write_results(results, records)

            result = run_script("generate_report.py", "--manifest", manifest, "--results", results, "--output-dir", output)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("executor 与计划快照不一致", result.stderr)


if __name__ == "__main__":
    unittest.main()
