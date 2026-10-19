import shutil
from pathlib import Path
import tempfile
import unittest

from scripts.validate_skills import validate


ROOT = Path(__file__).resolve().parents[1]


class BundleValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "skills", self.root / "skills")
        self.entry = self.root / "skills/java-backend/SKILL.md"

    def append(self, text):
        self.entry.write_text(self.entry.read_text() + "\n" + text + "\n")

    def test_bundle_is_relocatable(self):
        self.assertEqual(validate(self.root), [])

    def test_missing_sibling_is_reported(self):
        shutil.rmtree(self.root / "skills/frontend-development")
        errors = validate(self.root)
        self.assertTrue(any("skill set differs" in e for e in errors))
        self.assertFalse(any("missing target" in e for e in errors))

    def test_missing_humanizer_is_reported(self):
        shutil.rmtree(self.root / "skills/humanizer-zh")
        errors = validate(self.root)
        self.assertTrue(any("skill set differs" in e for e in errors))
        self.assertTrue(any("missing target ../humanizer-zh/SKILL.md" in e for e in errors))

    def test_missing_method_skills_are_reported(self):
        for name in ("diagnosing-bugs", "code-review", "business-modeling"):
            with self.subTest(skill=name):
                source = self.root / "skills" / name
                saved = self.root / name
                shutil.move(source, saved)
                try:
                    errors = validate(self.root)
                    self.assertTrue(any("skill set differs" in e for e in errors))
                    self.assertTrue(any(f"missing target ../{name}/SKILL.md" in e for e in errors))
                finally:
                    shutil.move(saved, source)

    def test_existing_external_runtime_dependency_is_rejected(self):
        (self.root / "private.md").write_text("external dependency")
        self.append("[private](../../private.md)")
        self.assertTrue(any("escapes skill bundle" in e for e in validate(self.root)))

    def test_orphan_reference_is_reported(self):
        (self.entry.parent / "references/orphan.md").write_text("Unreachable rule")
        self.assertTrue(any("unreachable" in e for e in validate(self.root)))

    def test_nested_orphan_reference_is_reported(self):
        ref = self.entry.parent / "references/advanced/orphan.md"
        ref.parent.mkdir()
        ref.write_text("Unreachable nested rule")
        self.assertTrue(any("unreachable" in e for e in validate(self.root)))

    def test_nested_reference_is_reachable_through_local_reference(self):
        ref = self.entry.parent / "references/advanced/rule.md"
        ref.parent.mkdir()
        ref.write_text("Nested rule")
        parent = self.entry.parent / "references/java-conventions.md"
        parent.write_text(parent.read_text() + "\n[advanced](advanced/rule.md)\n")
        self.assertEqual(validate(self.root), [])

    def test_reference_must_be_reachable_from_its_own_skill(self):
        ref = self.entry.parent / "references/foreign-only.md"
        ref.write_text("Only another skill knows this rule")
        other = self.root / "skills/humanizer-zh/SKILL.md"
        other.write_text(other.read_text() + "\n[rule](../java-backend/references/foreign-only.md)\n")
        self.assertTrue(any("unreachable" in e for e in validate(self.root)))

    def test_prompt_must_mention_exact_skill_name(self):
        metadata = self.entry.parent / "agents/openai.yaml"
        metadata.write_text(metadata.read_text().replace("$java-backend", "$java-backend-old"))
        self.assertTrue(any("default_prompt" in e for e in validate(self.root)))

    def test_encoded_filename_and_fenced_example(self):
        (self.entry.parent / "references/space name.md").write_text("Reachable")
        self.append("[space](references/space%20name.md)\n```md\n[example](missing.md)\n```")
        self.assertEqual(validate(self.root), [])

    def test_metadata_mismatch_is_reported(self):
        metadata = self.entry.parent / "agents/openai.yaml"
        metadata.write_text(metadata.read_text().replace("$java-backend", "$wrong"))
        self.assertTrue(any("default_prompt" in e for e in validate(self.root)))

    def test_malformed_metadata_is_reported(self):
        (self.entry.parent / "agents/openai.yaml").write_text("interface: [")
        self.assertTrue(validate(self.root))


if __name__ == "__main__":
    unittest.main()
