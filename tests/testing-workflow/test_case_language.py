"""Public-CLI checks for numbered Chinese cases, type maps, and frozen report facts."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from test_scripts import FIXTURES, SCRIPTS, run_script


MINIMAL_API_MAP = '---\nmindmap-plugin: basic\n---\n\n# 接口测试用例\n'
MINIMAL_UI_MAP = '---\nmindmap-plugin: basic\n---\n\n# UI 测试用例\n'
TEMPLATES = SCRIPTS.parent / 'assets/templates'


def snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def prepare(project: Path) -> tuple[Path, Path, Path, Path]:
    cases = project / 'docs/testing/01-cases'
    shutil.copytree(FIXTURES / 'cases', cases)
    return (cases, cases / '01-api/00-接口测试用例.md', cases / '02-ui-integration/00-UI测试用例.md',
            project / 'docs/testing/00-data/04-catalogs/case-catalog.json')


class CaseLanguageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.cases, self.api_map, self.ui_map, self.output = prepare(self.project)
        self.api = self.cases / '01-api/01-预约流程.md'
        self.ui = self.cases / '02-ui-integration/01-预约流程.md'

    def replace(self, path: Path, old: str, new: str, count: int = -1) -> None:
        text = path.read_text(encoding='utf-8')
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, count), encoding='utf-8')

    def catalog(self, *args: object) -> dict:
        result = run_script('build_catalog.py', self.project, *args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(self.output.read_text(encoding='utf-8'))

    def validate(self, *args: object) -> None:
        result = run_script('validate_cases.py', self.project, *args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_invalid(self, *, path: Path | None = None) -> None:
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_text('preserve existing catalog', encoding='utf-8')
        before = snapshot(self.project)
        result = run_script('validate_cases.py', path or self.project, '--json')
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertTrue(result.stderr.strip() or result.stdout.strip())
        if result.stdout.strip().startswith('{'):
            self.assertFalse(json.loads(result.stdout)['valid'])
        built = run_script('build_catalog.py', path or self.project)
        self.assertNotEqual(built.returncode, 0, built.stdout)
        self.assertEqual(snapshot(self.project), before, 'Invalid inputs must not rewrite sources or previous catalog')

    def test_valid_cases_build_stable_v5_catalog_and_real_locations(self) -> None:
        result = run_script('validate_cases.py', self.project, '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['case_count'], 3)
        catalog = self.catalog()
        first = self.output.read_bytes()
        self.catalog()
        self.assertEqual(first, self.output.read_bytes())
        self.assertEqual(catalog['schema_version'], 5)
        self.assertEqual(catalog['case_format'], 'chinese-markdown-v2')
        self.assertEqual(catalog['cases_root'], 'docs/testing/01-cases')
        maps = json.dumps(catalog['maps'], ensure_ascii=False)
        self.assertIn(hashlib.sha256(self.api_map.read_bytes()).hexdigest(), maps)
        self.assertIn(hashlib.sha256(self.ui_map.read_bytes()).hexdigest(), maps)
        self.assertIn('docs/testing/01-cases/01-api/00-接口测试用例.md', maps)
        self.assertIn('docs/testing/01-cases/02-ui-integration/00-UI测试用例.md', maps)
        self.assertNotIn('00-接口测试用例.md', json.dumps(catalog['documents'], ensure_ascii=False))
        self.assertNotIn('00-UI测试用例.md', json.dumps(catalog['documents'], ensure_ascii=False))
        self.assertEqual([c['case_id'] for c in catalog['cases']], ['API-BOOK-010', 'UI-BOOK-001', 'UI-BOOK-002'])
        for case in catalog['cases']:
            self.assertNotIn('keyword', case)
            self.assertNotIn('tags', case)
            self.assertRegex(case['case_revision'], r'^h-[0-9a-f]{12}$')
            self.assertEqual(case['anchor'], 'case-' + case['case_id'].lower())
            line = (self.cases / case['source_file']).read_text(encoding='utf-8').splitlines()[case['source_line'] - 1]
            self.assertIn(case['case_id'], line)
        api, success, rejected = catalog['cases']
        self.assertEqual(api['operation_id'], 'createBooking')
        self.assertEqual(api['risk_ids'], ['RISK-BOOK-001', 'RISK-BOOK-002'])
        self.assertEqual(api['classification_path'], ['会议预约', '预约流程', '并发竞争'])
        self.assertEqual(success['lifecycle_status'], '可执行')
        self.assertEqual(rejected['lifecycle_status'], '草拟')
        self.assertEqual(rejected['source_kind'], '契约')
        self.assertIn('contracts/booking.yaml', rejected['source_reference'])

    def test_project_testing_and_case_roots_select_same_collection(self) -> None:
        for root in (self.project, self.project / 'docs', self.project / 'docs/testing', self.cases):
            with self.subTest(root=root):
                result = run_script('validate_cases.py', root, '--json')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['case_count'], 3)
        self.assert_invalid(path=self.cases / '01-api')

    def test_legacy_layout_remains_readable_without_creating_new_tree(self) -> None:
        legacy = self.project / 'testing'
        shutil.move(self.project / 'docs/testing', legacy)
        for document in legacy.rglob('*.md'):
            document.write_text(document.read_text().replace('docs/testing/', 'testing/'))
        before = snapshot(self.project)
        for root in (self.project, legacy, legacy / '01-cases'):
            with self.subTest(root=root):
                result = run_script('validate_cases.py', root, '--json')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)['case_count'], 3)
        self.assertEqual(snapshot(self.project), before)
        result = run_script('build_catalog.py', self.project)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        catalog = json.loads((legacy / '00-data/04-catalogs/case-catalog.json').read_text())
        self.assertEqual(catalog['cases_root'], 'testing/01-cases')
        self.assertFalse((self.project / 'docs/testing').exists())

    def test_two_asset_roots_require_explicit_collection(self) -> None:
        shutil.copytree(self.project / 'docs/testing', self.project / 'testing')
        self.assert_invalid()
        result = run_script('validate_cases.py', self.cases, '--json')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['case_count'], 3)

    def test_runs_without_site_packages(self) -> None:
        for command in ('validate_cases.py', 'build_catalog.py'):
            result = run_script(command, self.project, python_args=('-S',))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_testing_vault_chinese_same_name_paths_and_md_suffix(self) -> None:
        for document in (self.api_map, self.ui_map, self.api, self.ui):
            self.replace(document, 'docs/testing/', '')
        self.replace(self.api_map, '01-预约流程#', '01-预约流程.md#')
        self.validate('--vault-root', self.project / 'docs/testing',
                      '--api-map', self.api_map, '--ui-map', self.ui_map)
        catalog = self.catalog('--vault-root', self.project / 'docs/testing',
                               '--api-map', self.api_map, '--ui-map', self.ui_map)
        self.assertEqual(catalog['cases_root'], '01-cases')
        self.assertEqual(len({c['source_file'] for c in catalog['cases']}), 2)

    def test_custom_cases_root_requires_explicit_context(self) -> None:
        custom = self.project / '自定义集合'
        shutil.move(self.cases, custom)
        self.api_map = custom / '01-api/00-接口测试用例.md'
        self.ui_map = custom / '02-ui-integration/00-UI测试用例.md'
        for map_path in (self.api_map, self.ui_map):
            self.replace(map_path, 'docs/testing/01-cases/', '自定义集合/')
        self.replace(custom / '01-api/01-预约流程.md',
                     'docs/testing/01-cases/01-api/00-接口测试用例', '自定义集合/01-api/00-接口测试用例')
        self.replace(custom / '02-ui-integration/01-预约流程.md',
                     'docs/testing/01-cases/02-ui-integration/00-UI测试用例', '自定义集合/02-ui-integration/00-UI测试用例')
        implicit = run_script('validate_cases.py', custom)
        self.assertNotEqual(implicit.returncode, 0)
        explicit = run_script('validate_cases.py', custom, '--api-map', self.api_map,
                              '--ui-map', self.ui_map, '--vault-root', self.project)
        self.assertEqual(explicit.returncode, 0, explicit.stderr)

    def test_missing_map_and_empty_collection_are_not_valid(self) -> None:
        self.api_map.unlink()
        self.assert_invalid()
        self.api_map.write_text(MINIMAL_API_MAP, encoding='utf-8')
        shutil.rmtree(self.cases / '01-api')
        shutil.rmtree(self.cases / '02-ui-integration')
        self.assert_invalid()

    def test_structure_errors_are_locatable_and_leave_no_outputs(self) -> None:
        source = self.api.read_text(encoding='utf-8')
        mutations = {
            'priority': ('优先级：P0\n', ''),
            'lifecycle': ('状态：可执行', '状态：已通过'),
            'source': ('关联需求：REQ-BOOK-001、REQ-BOOK-002\n', ''),
            'operation': ('关联接口：createBooking\n', ''),
            'id': ('用例编号：API-BOOK-010', '用例编号：API-BOOK-099'),
            'anchor': ('^case-api-book-010', '^case-api-book-099'),
            'empty preparation': ('- 满足“公共准备”。\n- 两个独立员工会话已登录；「测试会议室」在「预约日期」10:00—11:00 没有预约。\n- 各账号使用独立凭据，记录测试前预约数量。', ''),
            'unknown section': ('#### 数据', '#### 数具'),
            'unknown attribute': ('优先级：P0', '优先级：P0\n分类：并发'),
            'unknown step field': ('   等待：', '   等侍：'),
            'duplicate section': ('#### 数据', '#### 准备\n- 新条件。\n\n#### 数据'),
            'number gap': ('2. 核实持久化', '3. 核实持久化'),
        }
        for name, (old, new) in mutations.items():
            with self.subTest(name=name):
                self.api.write_text(source.replace(old, new), encoding='utf-8')
                result = run_script('validate_cases.py', self.project)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('预约流程.md', result.stderr + result.stdout)
                self.assert_invalid()
        self.api.write_text(source, encoding='utf-8')

    def test_unknown_step_field_with_bullet_is_rejected(self) -> None:
        self.replace(self.api, '   检查：', '   - 检査：')
        result = run_script('validate_cases.py', self.project)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('未知', result.stderr)
        self.assertIn('检査', result.stderr)
        self.assert_invalid()

    def test_nested_business_fields_remain_operation_content(self) -> None:
        self.replace(self.api, '   并发：', '     - 业务字段：测试值。\n   并发：', 1)
        self.validate()
        self.catalog()

    def test_case_number_block_requires_independent_paragraph(self) -> None:
        self.replace(self.api, '^case-api-book-010\n\n优先级', '^case-api-book-010\n优先级')
        self.assert_invalid()

    def test_missing_action_or_observable_check_is_invalid(self) -> None:
        source = self.api.read_text(encoding='utf-8')
        for mode in ('action', 'check', 'vague'):
            with self.subTest(mode=mode):
                lines = source.splitlines()
                if mode == 'action':
                    lines = ['   操作：' if line.startswith('   操作：') else line for line in lines]
                elif mode == 'check':
                    lines = [line for line in lines if not line.startswith('   检查：') and not line.startswith('   - ')]
                else:
                    lines = ['   - 正常。' if line.startswith('   - ') else line for line in lines]
                changed = '\n'.join(lines) + '\n'
                if mode == 'check':
                    before, final = changed.split('#### 最终检查', 1)
                    changed = before + '#### 清理' + final.split('#### 清理', 1)[1]
                self.api.write_text(changed, encoding='utf-8')
                self.assert_invalid()
        self.api.write_text(source, encoding='utf-8')

    def test_duplicate_ids_and_blocks_are_rejected(self) -> None:
        duplicate = self.cases / '01-api/02-重复.md'
        shutil.copyfile(self.api, duplicate)
        self.assert_invalid()
        duplicate.unlink()
        self.replace(self.api, '#### 清理', '#### 清理\n\n重复块 ^case-api-book-010')
        self.assert_invalid()

    def test_map_rejects_broken_missing_duplicate_mismatch_and_outside_targets(self) -> None:
        source = self.api_map.read_text(encoding='utf-8')
        leaf = next(line for line in source.splitlines() if '|API-BOOK-010' in line)
        mutations = {
            'missing file': source.replace('/01-api/01-预约流程#', '/01-api/01-不存在#'),
            'missing block': source.replace('#^case-api-book-010', '#^case-api-book-999'),
            'duplicate primary': source.replace(leaf, leaf + '\n' + leaf),
            'wrong identity': source.replace('|API-BOOK-010]]', '|UI-BOOK-001]]'),
            'omitted case': source.replace(leaf + '\n', ''),
            'ambiguous basename': source.replace('docs/testing/01-cases/01-api/01-预约流程#', '01-预约流程#'),
            'escape': source.replace('docs/testing/01-cases/01-api/01-预约流程#', '../outside#'),
            'external URL': source.replace('docs/testing/01-cases/01-api/01-预约流程#', 'https://example.test/cases#'),
            'leaf child': source.replace(leaf, leaf + '\n        - 无效子节点'),
            'empty placeholder': source.replace(leaf, '      - 待补充'),
        }
        for name, text in mutations.items():
            with self.subTest(name=name):
                self.api_map.write_text(text, encoding='utf-8')
                self.assert_invalid()
        self.api_map.write_text(source, encoding='utf-8')

    def test_map_requires_one_leaf_with_only_trailing_id_linked(self) -> None:
        source = self.api_map.read_text(encoding='utf-8')
        leaf = next(line for line in source.splitlines() if '|API-BOOK-010]]' in line)
        prefix, link = leaf.split('[[', 1)
        target = link.split('|', 1)[0]
        mutations = {
            'whole leaf linked': f'      - [[{target}|API-BOOK-010｜🔵 可执行｜仅一人成功]]',
            'title in alias': leaf.replace('|API-BOOK-010]]', '|仅一人成功｜API-BOOK-010]]'),
            'wiki title link': leaf.replace('仅一人成功', '[[other|仅一人成功]]'),
            'markdown title link': leaf.replace('仅一人成功', '[仅一人成功](other.md)'),
            'empty title': leaf.replace('仅一人成功', ' '),
            'trailing text': leaf + ' 更多',
            'second link': leaf + f' [[{target}|API-BOOK-010]]',
            'split siblings': prefix.rstrip('｜') + '\n      - [[' + link,
            'split children': prefix.rstrip('｜') + '\n        - [[' + link,
        }
        for name, replacement in mutations.items():
            with self.subTest(name=name):
                self.api_map.write_text(source.replace(leaf, replacement), encoding='utf-8')
                self.assert_invalid()
        self.api_map.write_text(source, encoding='utf-8')
        self.validate()

    def test_map_rejects_metadata_title_and_non_business_content(self) -> None:
        source = self.api_map.read_text(encoding='utf-8')
        mutations = {
            'missing frontmatter': source.replace('---\nmindmap-plugin: basic\n---\n\n', '', 1),
            'wrong plugin mode': source.replace('mindmap-plugin: basic', 'mindmap-plugin: rich'),
            'extra metadata': source.replace('mindmap-plugin: basic', 'mindmap-plugin: basic\ntags: [test]'),
            'wrong title': source.replace('# 接口测试用例', '# 测试地图'),
            'usage section': source + '\n## 使用说明\n',
            'free text': source + '\n这是额外说明。\n',
            'code fence': source + '\n```markdown\n- 示例\n```\n',
        }
        for name, text in mutations.items():
            with self.subTest(name=name):
                self.api_map.write_text(text, encoding='utf-8')
                self.assert_invalid()
        self.api_map.write_text(source, encoding='utf-8')

    def test_map_lifecycle_labels_follow_body_without_changing_revision(self) -> None:
        body, mapping = self.api.read_text(), self.api_map.read_text()
        baseline = self.catalog()['cases'][0]['case_revision']
        for status, label in (('草拟', '🟠 草拟'), ('可执行', '🔵 可执行'), ('已废弃', '⚪ 已废弃')):
            with self.subTest(status=status):
                self.api.write_text(body.replace('状态：可执行', f'状态：{status}'))
                self.api_map.write_text(mapping.replace('🔵 可执行', label))
                case = self.catalog()['cases'][0]
                self.assertEqual(case['lifecycle_status'], status)
                self.assertEqual(case['case_revision'], baseline)
                self.api_map.write_text(mapping.replace('🔵 可执行', '🟢 已通过'))
                self.assert_invalid()

    def test_map_rejects_missing_stale_or_fabricated_status_and_hint(self) -> None:
        source = self.api_map.read_text()
        for replacement in ('', '🟠 草拟｜', '🔵 已废弃｜', '🔵 可执行 · 待复核｜'):
            with self.subTest(label=replacement):
                self.api_map.write_text(source.replace('🔵 可执行｜', replacement))
                self.assert_invalid()

    def test_draft_hints_require_body_evidence_and_matching_map(self) -> None:
        body, mapping = self.ui.read_text(), self.ui_map.read_text()
        baseline = self.catalog()['cases'][2]['case_revision']
        evidence = '评审记录.md 的 QUESTION-001'
        for hint in ('待独立评审', '待修订', '待复核', '待澄清'):
            with self.subTest(hint=hint):
                self.ui.write_text(body.replace('状态：草拟', f'状态：草拟\n处理提示：{hint}\n处理依据：{evidence}'))
                self.ui_map.write_text(mapping.replace('🟠 草拟', f'🟠 草拟 · {hint}'))
                case = self.catalog()['cases'][2]
                self.assertEqual(case['draft_hint'], hint)
                self.assertEqual(case['draft_hint_source'], evidence)
                self.assertEqual(case['case_revision'], baseline)
                for label in ('🟠 草拟', '🟠 草拟 · 未执行'):
                    self.ui_map.write_text(mapping.replace('🟠 草拟', label))
                    self.assert_invalid()
        self.ui.write_text(body)
        self.ui_map.write_text(mapping.replace('🟠 草拟', '🟠 草拟 · 待澄清'))
        self.assert_invalid()
        self.ui_map.write_text(mapping)
        self.assertNotIn('draft_hint', self.catalog()['cases'][2])

    def test_draft_hint_metadata_rejects_missing_evidence_and_non_draft(self) -> None:
        body, mapping = self.ui.read_text(), self.ui_map.read_text()
        for metadata in ('处理提示：待澄清', '处理依据：评审记录.md 的 QUESTION-001',
                         '处理提示：待澄清\n处理依据：   ',
                         '处理提示：待执行\n处理依据：评审记录.md',
                         '处理提示：待修订、待复核\n处理依据：评审记录.md'):
            with self.subTest(metadata=metadata):
                self.ui.write_text(body.replace('状态：草拟', '状态：草拟\n' + metadata))
                self.ui_map.write_text(mapping.replace('🟠 草拟', '🟠 草拟 · 待澄清'))
                self.assert_invalid()
        for status, label in (('可执行', '🔵 可执行'), ('已废弃', '⚪ 已废弃')):
            with self.subTest(status=status):
                self.ui.write_text(body.replace('状态：草拟', f'状态：{status}\n处理提示：待复核\n处理依据：评审记录.md'))
                self.ui_map.write_text(mapping.replace('🟠 草拟', f'{label} · 待复核'))
                self.assert_invalid()

    def test_map_rejects_target_outside_collection_and_symlink_outside_vault(self) -> None:
        outside_collection = self.project / '其他用例.md'
        shutil.copyfile(self.api, outside_collection)
        original = self.api_map.read_text(encoding='utf-8')
        self.replace(self.api_map, 'docs/testing/01-cases/01-api/01-预约流程#', '其他用例#')
        self.assert_invalid()
        self.api_map.write_text(original, encoding='utf-8')
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / '01-预约流程.md'
            shutil.copyfile(self.api, target)
            self.api.unlink()
            self.api.symlink_to(target)
            self.assert_invalid()

    def test_backlink_must_resolve_to_selected_map(self) -> None:
        self.replace(self.api, '[[docs/testing/01-cases/01-api/00-接口测试用例|', '[[docs/testing/别的地图|')
        (self.project / 'docs/testing/别的地图.md').write_text(MINIMAL_API_MAP, encoding='utf-8')
        self.assert_invalid()

    def test_additional_map_is_rejected(self) -> None:
        shutil.copyfile(self.api_map, self.api_map.with_name('01-另一个测试用例.md'))
        result = run_script('validate_cases.py', self.project)
        self.assertNotEqual(result.returncode, 0)

    def test_case_files_require_number_and_separator(self) -> None:
        unnumbered = self.api.with_name('预约流程.md')
        self.api.rename(unnumbered)
        self.replace(self.api_map, '/01-api/01-预约流程#', '/01-api/预约流程#')
        self.api = unnumbered
        self.assert_invalid()

        numbered = self.cases / '01-api/01-预约流程.md'
        unnumbered.rename(numbered)
        self.api = numbered
        self.replace(self.api_map, '/01-api/预约流程#', '/01-api/01-预约流程#')

        self.ui = self.cases / '02-ui-integration/01-预约流程.md'
        source = self.ui.read_text(encoding='utf-8')
        self.ui.write_text(source.replace('\n---\n\n### UI-BOOK-002', '\n### UI-BOOK-002'), encoding='utf-8')
        self.assert_invalid()

    def test_case_filename_module_must_match_document_title(self) -> None:
        self.replace(self.api, '# 预约流程', '# 预约创建')
        self.assert_invalid()

    def test_unstructured_file_is_not_silently_skipped(self) -> None:
        self.api.write_text('# 预约接口\n\n这里没有结构化用例正文。\n', encoding='utf-8')
        self.assert_invalid()

    def test_code_fences_and_quoted_labels_are_literal_content(self) -> None:
        self.replace(self.api, '#### 数据', '#### 数据\n\n```json\n{"说明": "「不是变量」"}\n### API-FAKE-001｜这不是用例\n操作：这不是步骤\n```')
        self.replace(self.ui, '页面显示“预约成功”', '页面显示“「我的预约」创建正常，共 1 条”')
        self.validate()

    def test_named_data_checks_undefined_duplicate_cycle_and_early_output(self) -> None:
        source = self.api.read_text(encoding='utf-8')
        mutations = {
            'undefined': source.replace('「时段」', '「未定义时段」'),
            'duplicate': source.replace('- 时段：10:00—11:00。', '- 时段：10:00—11:00。\n- 时段：11:00—12:00。'),
            'cycle': source.replace('- 时段：10:00—11:00。', '- 时段：「第二时段」。\n- 第二时段：「时段」。'),
            'early output': source.replace('以两个员工会话', '先读取「成功预约编号」，以两个员工会话'),
            'duplicate output': source.replace('2. 核实持久化', '2. 核实持久化\n   保存为：成功预约编号 ← 新响应 id。'),
            'missing shared': source[source.index('# 预约流程'):].replace('## 公共准备\n\n- 测试会议室：青山会议室，处于启用状态。\n- 预约日期：用例开始时按 Asia/Shanghai 时区确定的明天。\n\n', ''),
        }
        for name, text in mutations.items():
            with self.subTest(name=name):
                self.api.write_text(text, encoding='utf-8')
                self.assert_invalid()
        self.api.write_text(source, encoding='utf-8')

    def test_semantic_changes_update_revision(self) -> None:
        original = self.api.read_text(encoding='utf-8')
        baseline = self.catalog()['cases'][0]['case_revision']
        for old, new in (
            ('状态码为 201', '状态码为 202'),
            ('各账号使用独立凭据', '各账号使用独立凭据且账号已启用'),
            ('- 时段：10:00—11:00。', '- 时段：11:00—12:00。'),
            ('处于启用状态', '处于启用且可预约状态'),
            ('关联接口：createBooking', '关联接口：reserveRoom'),
            ('最多等待 5 秒', '最多等待 8 秒'),
            ('同时释放', '以 10 毫秒间隔释放'),
            ('保留脱敏证据', '保留脱敏证据及取消响应'),
        ):
            with self.subTest(change=new):
                self.api.write_text(original.replace(old, new), encoding='utf-8')
                self.assertNotEqual(self.catalog()['cases'][0]['case_revision'], baseline)
        self.api.write_text(original, encoding='utf-8')

    def test_presentation_classification_order_and_location_keep_revision(self) -> None:
        baseline = {c['case_id']: c['case_revision'] for c in self.catalog()['cases']}
        self.replace(self.api, '优先级：P0', '优先级：P2')
        self.replace(self.api, '状态：可执行', '状态：已废弃')
        self.replace(self.api, '两人争抢同一时段仅一人成功', '同一时段的并发预约')
        self.replace(self.api_map, '  - 预约流程\n', '  - 预约冲突\n')
        self.replace(self.api_map, '🔵 可执行｜仅一人成功｜', '⚪ 已废弃｜并发唯一性｜')
        moved = self.api.with_name('02-预约流程.md')
        self.api.rename(moved)
        self.replace(self.api_map, '/01-api/01-预约流程#', '/01-api/02-预约流程#')
        text = self.ui.read_text(encoding='utf-8')
        head, cases = text.split('### UI-BOOK-001', 1)
        first, second = cases.split('\n---\n\n### UI-BOOK-002', 1)
        self.ui.write_text(head + '### UI-BOOK-002' + second + '\n\n---\n\n### UI-BOOK-001' + first,
                           encoding='utf-8')
        actual = self.catalog()
        self.assertEqual({c['case_id']: c['case_revision'] for c in actual['cases']}, baseline)
        self.assertEqual(actual['cases'][0]['classification_path'][1], '预约冲突')
        self.assertEqual(actual['cases'][0]['source_file'], '01-api/02-预约流程.md')

    def test_unreferenced_shared_preparation_does_not_change_case_revision(self) -> None:
        original = self.catalog()
        self.replace(self.ui, '## 用例', '## 公共准备\n\n- 未使用条件：状态甲。\n\n## 用例')
        added = self.catalog()
        self.replace(self.ui, '状态甲', '状态乙')
        changed = self.catalog()
        for case_id in ('UI-BOOK-001', 'UI-BOOK-002'):
            revisions = [next(c['case_revision'] for c in x['cases'] if c['case_id'] == case_id) for x in (original, added, changed)]
            self.assertEqual(len(set(revisions)), 1)

    def test_catalog_output_cannot_escape_data_boundary(self) -> None:
        for target in (self.project / 'catalog.json', self.api_map, self.ui_map):
            with self.subTest(target=target):
                before = snapshot(self.project)
                result = run_script('build_catalog.py', self.project, '--output', target)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(snapshot(self.project), before)

    def test_default_output_symlink_cannot_overwrite_external_file(self) -> None:
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'external.json'
            target.write_text('external content must survive', encoding='utf-8')
            self.output.parent.mkdir(parents=True)
            self.output.symlink_to(target)
            before = snapshot(self.project)
            result = run_script('build_catalog.py', self.project)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertEqual(target.read_text(encoding='utf-8'), 'external content must survive')
            self.assertTrue(self.output.is_symlink())
            self.assertEqual(snapshot(self.project), before)

    def test_default_output_symlink_cannot_overwrite_source(self) -> None:
        self.output.parent.mkdir(parents=True)
        self.output.symlink_to(self.api)
        before = snapshot(self.project)
        result = run_script('build_catalog.py', self.project)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertTrue(self.output.is_symlink())
        self.assertEqual(snapshot(self.project), before)

    def test_catalog_to_frozen_manifest_results_and_reports(self) -> None:
        catalog = self.catalog()
        run_dir = self.project / 'docs/testing/04-runs/RUN-20260908-001'
        run_dir.mkdir(parents=True)
        manifest = json.loads((FIXTURES / 'report/manifest.json').read_text(encoding='utf-8'))
        planned = []
        for case in catalog['cases']:
            if case['lifecycle_status'] != '可执行':
                continue
            planned.append({
                **{key: case[key] for key in ('case_id', 'case_revision', 'case_type', 'priority', 'requirement_ids', 'operation_id')},
                'module': case['classification_path'][1],
                'source': f"01-cases/{case['source_file']}:{case['source_line']}",
                'executor': 'http' if case['operation_id'] else 'agent-browser',
                'executor_version': 'synthetic-fixture-1',
                'required_for_conclusion': True,
            })
        manifest.update(planned_cases=planned, requirements=['REQ-BOOK-001', 'REQ-BOOK-002'], operations=['createBooking'], unverified=[], residual_risks=[])
        manifest_path = run_dir / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
        results = [{**case, 'run_id': manifest['run_id'], 'plan_id': manifest['plan_id'], 'attempt': 1, 'status': 'Passed', 'evidence': []} for case in planned]
        result_path = run_dir / 'results.jsonl'
        result_path.write_text(''.join(json.dumps(record, ensure_ascii=False) + '\n' for record in results), encoding='utf-8')
        facts = snapshot(run_dir)
        sources = snapshot(self.cases)
        output = self.project / 'docs/testing/05-reports/RUN-20260908-001'
        result = run_script('generate_report.py', '--manifest', manifest_path, '--results', result_path, '--output-dir', output)
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ('report.md', 'report.html'):
            text = (output / name).read_text(encoding='utf-8')
            for case in planned:
                self.assertIn(case['case_id'], text)
            self.assertIn('Passed', text)
        self.assertEqual(snapshot(run_dir), facts)
        self.assertEqual(snapshot(self.cases), sources)
        # The report consumer rejects a result that changes a frozen case revision.
        valid_results = result_path.read_bytes()
        results[0]['case_revision'] = 'h-000000000000'
        result_path.write_text(''.join(json.dumps(record, ensure_ascii=False) + '\n' for record in results), encoding='utf-8')
        report_before = snapshot(output)
        mismatch = run_script('generate_report.py', '--manifest', manifest_path, '--results', result_path, '--output-dir', output)
        self.assertNotEqual(mismatch.returncode, 0)
        self.assertIn('case_revision', mismatch.stderr)
        self.assertEqual(snapshot(output), report_before)
        result_path.write_bytes(valid_results)
        # Frozen facts remain reportable independently of current case availability.
        shutil.rmtree(self.cases)
        rerun = run_script('generate_report.py', '--manifest', manifest_path, '--results', result_path, '--output-dir', output)
        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        self.assertEqual(snapshot(run_dir), facts)


class InitLanguageTests(unittest.TestCase):
    def test_old_root_blocks_initialization_without_creating_docs_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            legacy = project / 'testing'
            legacy.mkdir()
            (legacy / 'keep.md').write_text('existing test assets')
            before = snapshot(project)
            result = run_script('init_testing.py', project)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('旧位置', result.stderr)
            self.assertEqual(snapshot(project), before)
            self.assertFalse((project / 'docs').exists())

    def test_docs_symlink_cannot_write_outside_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as external:
            project = Path(temporary)
            (project / 'docs').symlink_to(external, target_is_directory=True)
            result = run_script('init_testing.py', project)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list(Path(external).iterdir()), [])

    def test_empty_initialization_is_repeatable_but_not_a_valid_case_set(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            first = run_script('init_testing.py', project)
            self.assertEqual(first.returncode, 0, first.stderr)
            root = project / 'docs/testing'
            self.assertFalse((project / 'testing').exists())
            for directory in ('00-data/01-sources/01-requirements', '00-data/01-sources/02-openapi', '00-data/02-analysis', '00-data/04-catalogs', '01-cases/01-api', '01-cases/02-ui-integration', '02-checks', '04-runs', '05-reports', '06-bugs/01-pending-fix', '06-bugs/02-pending-verification', '06-bugs/03-verified'):
                self.assertTrue((root / directory).is_dir(), directory)
            self.assertTrue((project / 'docs/plan').is_dir())
            self.assertFalse((root / '03-plans').exists())
            self.assertFalse((root / '02-explorations').exists())
            self.assertFalse((root / '测试地图.md').exists())
            self.assertEqual((root / '01-cases/01-api/00-接口测试用例.md').read_text(encoding='utf-8'), MINIMAL_API_MAP)
            self.assertEqual((root / '01-cases/02-ui-integration/00-UI测试用例.md').read_text(encoding='utf-8'), MINIMAL_UI_MAP)
            before = snapshot(root)
            self.assertEqual(run_script('init_testing.py', project).returncode, 0)
            self.assertEqual(snapshot(root), before)
            self.assertNotEqual(run_script('validate_cases.py', project).returncode, 0)

    def test_preserves_user_map(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            root = project / 'docs/testing'
            (root / '01-cases/01-api').mkdir(parents=True)
            (root / '01-cases/02-ui-integration').mkdir(parents=True)
            custom_api = MINIMAL_API_MAP
            custom_ui = MINIMAL_UI_MAP
            (root / '01-cases/01-api/00-接口测试用例.md').write_text(custom_api, encoding='utf-8')
            (root / '01-cases/02-ui-integration/00-UI测试用例.md').write_text(custom_ui, encoding='utf-8')
            result = run_script('init_testing.py', project)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / '01-cases/01-api/00-接口测试用例.md').read_text(encoding='utf-8'), custom_api)
            self.assertEqual((root / '01-cases/02-ui-integration/00-UI测试用例.md').read_text(encoding='utf-8'), custom_ui)

    def test_old_root_map_does_not_create_a_second_map(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            old_map = project / 'docs/testing/测试地图.md'
            old_map.parent.mkdir(parents=True)
            old_map.write_text('# 测试地图\n', encoding='utf-8')
            before = snapshot(project)
            result = run_script('init_testing.py', project)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(snapshot(project), before)
            self.assertFalse((project / 'docs/testing/01-cases/01-api/00-接口测试用例.md').exists())
            self.assertFalse((project / 'docs/testing/01-cases/02-ui-integration/00-UI测试用例.md').exists())

    def test_existing_cases_without_map_require_author_maintenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            cases, api_map_path, ui_map_path, _ = prepare(project)
            api_map_path.unlink()
            before = snapshot(cases)
            result = run_script('init_testing.py', project)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('地图', result.stderr + result.stdout)
            self.assertFalse(api_map_path.exists())
            self.assertTrue(ui_map_path.exists())
            self.assertEqual(snapshot(cases), before)

    def test_preflights_path_conflicts_without_partial_directories(self) -> None:
        for conflict_path in ('docs', 'docs/testing', 'docs/testing/06-bugs/03-verified',
                              'docs/testing/01-cases/01-api/00-接口测试用例.md',
                              'docs/testing/01-cases/02-ui-integration/00-UI测试用例.md'):
            with self.subTest(path=conflict_path), tempfile.TemporaryDirectory() as temporary:
                project = Path(temporary)
                conflict = project / conflict_path
                if conflict.name in {'00-接口测试用例.md', '00-UI测试用例.md'}:
                    conflict.mkdir(parents=True)
                else:
                    conflict.parent.mkdir(parents=True, exist_ok=True)
                    conflict.write_text('keep', encoding='utf-8')
                before = sorted(p.relative_to(project).as_posix() for p in project.rglob('*'))
                result = run_script('init_testing.py', project)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(sorted(p.relative_to(project).as_posix() for p in project.rglob('*')), before)

    def test_rejects_old_or_mixed_layout_without_creating_second_asset_tree(self) -> None:
        for layout in ('cases/api', '01-cases/api', 'runs'):
            with self.subTest(layout=layout), tempfile.TemporaryDirectory() as temporary:
                project = Path(temporary)
                (project / 'docs/testing' / layout).mkdir(parents=True)
                before = sorted(p.relative_to(project).as_posix() for p in project.rglob('*'))
                result = run_script('init_testing.py', project)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(sorted(p.relative_to(project).as_posix() for p in project.rglob('*')), before)


class TemplateContractTests(unittest.TestCase):
    def test_plan_and_map_links_resolve_to_actual_task_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            plans = project / 'docs/plan'
            plans.mkdir(parents=True)
            plan_path = plans / 'YYYY-MM-DD-topic.md'
            map_path = plans / 'YYYY-MM-DD-topic-map.md'
            shutil.copyfile(TEMPLATES / 'execution-plan.md', plan_path)
            shutil.copyfile(TEMPLATES / 'execution-plan-map.md', map_path)
            plan = plan_path.read_text(encoding='utf-8')
            mapping = map_path.read_text(encoding='utf-8')
            links = re.findall(r'\[\[([^#|]+)#\^([^|\]]+)\|([^\]]+)\]\]', mapping)
            self.assertTrue(links, 'The plan map must reference real task blocks')
            seen = set()
            for path, anchor, case_id in links:
                target = project / (path if path.endswith('.md') else path + '.md')
                self.assertEqual(target.resolve(), plan_path.resolve())
                self.assertEqual(len(re.findall(r'\^' + re.escape(anchor) + r'$', plan, re.MULTILINE)), 1)
                self.assertNotIn(anchor, seen)
                seen.add(anchor)
            backlinks = re.findall(r'\[\[([^#|]+)(?:\|[^\]]+)?\]\]', plan)
            self.assertIn(map_path.resolve(), [
                (project / (path if path.endswith('.md') else path + '.md')).resolve() for path in backlinks])

    def test_api_ui_and_map_templates_validate_in_default_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            cases = project / 'docs/testing/01-cases'
            (cases / '01-api').mkdir(parents=True)
            (cases / '02-ui-integration').mkdir()
            shutil.copyfile(TEMPLATES / 'api-test-map.md', cases / '01-api/00-接口测试用例.md')
            shutil.copyfile(TEMPLATES / 'ui-test-map.md', cases / '02-ui-integration/00-UI测试用例.md')
            shutil.copyfile(SCRIPTS.parent.parent / 'api-testing/assets/templates/api-test-case.md', cases / '01-api/01-预约管理.md')
            shutil.copyfile(SCRIPTS.parent.parent / 'ui-testing/assets/templates/ui-integration-test-case.md', cases / '02-ui-integration/01-预约流程.md')

            for path, items in (
                (cases / '01-api/00-接口测试用例.md', [('API-BOOK-010', '01-api/01-预约管理')]),
                (cases / '02-ui-integration/00-UI测试用例.md', [('UI-BOOK-001', '02-ui-integration/01-预约流程'), ('UI-BOOK-002', '02-ui-integration/01-预约流程')]),
            ):
                with path.open('a', encoding='utf-8') as handle:
                    handle.write('\n- 合成预约场景\n  - 预约流程\n    - 已声明规则\n')
                    for case_id, document in items:
                        handle.write(f'      - 🟠 草拟｜模板场景｜[[docs/testing/01-cases/{document}#^case-{case_id.lower()}|{case_id}]]\n')
            result = run_script('validate_cases.py', project, '--asset-root', project, '--json')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload['valid'])
            self.assertEqual(payload['case_count'], 3)
            catalog = run_script('build_catalog.py', project, '--asset-root', project)
            self.assertEqual(catalog.returncode, 0, catalog.stderr)
            content = json.loads((project / 'docs/testing/00-data/04-catalogs/case-catalog.json').read_text())
            self.assertEqual({item['lifecycle_status'] for item in content['cases']}, {'草拟'})


if __name__ == '__main__':
    unittest.main()
