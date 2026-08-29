#!/usr/bin/env python3
"""Tests for scripts/validate_skills.py."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import validate_skills as vs  # noqa: E402

REPO_ROOT = vs.repo_root_from()


class ParseYamlTests(unittest.TestCase):
    def test_folded_description_and_metadata(self) -> None:
        yaml_text = (
            "name: architect\n"
            "description: >-\n"
            "  Owns system-level architecture.\n"
            "  Use when designing boundaries.\n"
            "license: MIT\n"
            "metadata:\n"
            '  kit: d2269-agent-kit\n'
            '  version: "0.1.0"\n'
        )
        data = vs.parse_simple_yaml(yaml_text)
        self.assertEqual(data["name"], "architect")
        self.assertIn("Owns system-level architecture.", data["description"])
        self.assertIn("Use when designing boundaries.", data["description"])
        self.assertEqual(data["license"], "MIT")
        self.assertEqual(data["metadata"]["kit"], "d2269-agent-kit")
        self.assertEqual(data["metadata"]["version"], "0.1.0")

    def test_rejects_malformed_flow_scalar(self) -> None:
        with self.assertRaises(vs.FrontmatterError):
            vs.parse_simple_yaml("name: bad\ndescription: [unterminated\n")

    def test_rejects_nested_metadata_mapping(self) -> None:
        yaml_text = (
            "name: bad\n"
            "description: Valid description.\n"
            "metadata:\n"
            "  owner:\n"
            "    name: someone\n"
        )
        with self.assertRaises(vs.FrontmatterError):
            vs.parse_simple_yaml(yaml_text)

    def test_rejects_duplicate_keys(self) -> None:
        with self.assertRaises(vs.FrontmatterError):
            vs.parse_simple_yaml(
                "name: first\nname: second\ndescription: Valid description.\n"
            )


class RepositoryValidationTests(unittest.TestCase):
    def test_canonical_skills_pass(self) -> None:
        errors = vs.validate_repository(REPO_ROOT)
        self.assertEqual(errors, [])

    def test_expected_skill_set(self) -> None:
        names = {path.name for path in vs.skill_directories(REPO_ROOT / "skills")}
        self.assertEqual(
            names,
            {
                "architect",
                "tech-lead",
                "developer",
                "qa",
                "orchestrator",
                "researcher",
                "code-review",
                "technical-documentation",
            },
        )


class FailureTests(unittest.TestCase):
    def test_duplicate_declared_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
            for directory, declared in (("qa", "qa"), ("qa-review", "QA")):
                skill_dir = root / "skills" / directory
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(
                    "---\n"
                    f"name: {declared}\n"
                    "description: A description that is long enough.\n"
                    "---\n\n"
                    "# Role\n",
                    encoding="utf-8",
                )
            errors = vs.validate_repository(root)
            self.assertTrue(any("duplicate skill name" in item for item in errors))

    def test_missing_skill_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
            skill_dir = root / "skills" / "broken"
            skill_dir.mkdir(parents=True)
            errors = vs.validate_repository(root)
            self.assertTrue(any("missing SKILL.md" in item for item in errors))

    def test_name_mismatch_and_non_english(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
            skill_dir = root / "skills" / "good-name"
            skill_dir.mkdir(parents=True)
            # Non-Latin heading is the fixture for the English-content check.
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: other-name\n"
                "description: A description that is long enough.\n"
                "---\n\n"
                "# \u0417\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a\n",
                encoding="utf-8",
            )
            errors = vs.validate_skill_dir(skill_dir, root)
            joined = "\n".join(errors)
            self.assertIn("does not match directory", joined)
            self.assertIn("non-English", joined)

    def test_required_fields_must_be_strings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
            skill_dir = root / "skills" / "mapped-description"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: mapped-description\n"
                "description:\n"
                "  text: Invalid mapping instead of string.\n"
                "---\n\n"
                "# Invalid\n",
                encoding="utf-8",
            )
            errors = vs.validate_skill_dir(skill_dir, root)
            self.assertTrue(
                any("description" in item and "must be a string" in item for item in errors)
            )

    def test_broken_relative_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
            skill_dir = root / "skills" / "linker"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: linker\n"
                "description: Checks relative links.\n"
                "---\n\n"
                "See [missing](references/nope.md).\n",
                encoding="utf-8",
            )
            errors = vs.validate_skill_dir(skill_dir, root)
            self.assertTrue(any("does not resolve" in item for item in errors))

    def test_skill_link_must_not_escape_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
            docs = root / "docs"
            docs.mkdir()
            (docs / "shared.md").write_text("# Shared\n", encoding="utf-8")
            skill_dir = root / "skills" / "linker"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: linker\n"
                "description: Checks package-contained links.\n"
                "---\n\n"
                "See [shared](../../docs/shared.md).\n",
                encoding="utf-8",
            )
            errors = vs.validate_skill_dir(skill_dir, root)
            self.assertTrue(any("escapes the skill package" in item for item in errors))

    def test_supporting_file_link_must_not_escape_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
            (root / "README.md").write_text("# Root\n", encoding="utf-8")
            skill_dir = root / "skills" / "linker"
            references = skill_dir / "references"
            references.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: linker\n"
                "description: Checks supporting file links.\n"
                "---\n\n"
                "See [reference](references/guide.md).\n",
                encoding="utf-8",
            )
            (references / "guide.md").write_text(
                "See [root](../../../README.md).\n", encoding="utf-8"
            )
            errors = vs.validate_repository(root)
            self.assertTrue(any("escapes the skill package" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
