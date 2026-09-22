#!/usr/bin/env python3
"""Tests for scripts/install_skills.py."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import install_skills as inst  # noqa: E402
import validate_skills as vs  # noqa: E402

REPO_ROOT = vs.repo_root_from()
# Temporary trees stay inside the repository (gitignored) so the suite also runs
# where the system temp directory is not writable.
TEST_TMP = Path(__file__).resolve().parent / ".tmp"


def tearDownModule() -> None:
    shutil.rmtree(TEST_TMP, ignore_errors=True)


class TempTreeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(dir=TEST_TMP))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def new_dir(self, name: str) -> Path:
        path = self.tmp / name
        path.mkdir(parents=True)
        return path

    def mini_kit(self, name: str = "kit") -> Path:
        root = self.new_dir(name)
        (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
        skill = root / "skills" / "d2269-architect"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: d2269-architect\ndescription: Architecture role.\n---\n\n# Architect\n",
            encoding="utf-8",
        )
        return root


class DestinationTests(TempTreeTestCase):
    def test_herdr_is_refused(self) -> None:
        with self.assertRaises(inst.InstallError) as ctx:
            inst.destination_root("herdr", "user", None)
        self.assertIn("Herdr does not document", str(ctx.exception))

    def test_project_cursor_path(self) -> None:
        root = self.new_dir("project")
        dest = inst.destination_root("cursor", "project", root)
        self.assertEqual(dest, root.resolve() / ".cursor" / "skills")

    def test_project_requires_root(self) -> None:
        with self.assertRaises(inst.InstallError):
            inst.destination_root("codex", "project", None)

    def test_project_root_must_exist(self) -> None:
        missing = self.tmp / "missing"
        with self.assertRaises(inst.InstallError) as ctx:
            inst.destination_root("cursor", "project", missing)
        self.assertIn("does not exist", str(ctx.exception))

    def test_project_root_must_be_directory(self) -> None:
        file_path = self.tmp / "not-a-directory"
        file_path.write_text("content\n", encoding="utf-8")
        with self.assertRaises(inst.InstallError) as ctx:
            inst.destination_root("claude", "project", file_path)
        self.assertIn("not a directory", str(ctx.exception))


class InstallBehaviorTests(TempTreeTestCase):
    def test_copy_is_idempotent_and_protects_divergence(self) -> None:
        kit = self.mini_kit()
        project = self.new_dir("project")
        code, lines = inst.run_install(
            repo_root=kit,
            platform="codex",
            scope="project",
            project_root=project,
            mode="copy",
            dry_run=False,
            force=False,
            skill_names=["d2269-architect"],
        )
        self.assertEqual(code, 0)
        dest = project / ".agents" / "skills" / "d2269-architect"
        self.assertTrue((dest / "SKILL.md").is_file())
        self.assertTrue(any(item.startswith("installed d2269-architect") for item in lines))

        code, lines = inst.run_install(
            repo_root=kit,
            platform="codex",
            scope="project",
            project_root=project,
            mode="copy",
            dry_run=False,
            force=False,
            skill_names=["d2269-architect"],
        )
        self.assertEqual(code, 0)
        self.assertTrue(any(item.startswith("unchanged d2269-architect") for item in lines))

        (dest / "SKILL.md").write_text("user-modified\n", encoding="utf-8")
        code, lines = inst.run_install(
            repo_root=kit,
            platform="codex",
            scope="project",
            project_root=project,
            mode="copy",
            dry_run=False,
            force=False,
            skill_names=["d2269-architect"],
        )
        self.assertEqual(code, 1)
        self.assertTrue(any(item.startswith("CONFLICT d2269-architect") for item in lines))
        self.assertEqual((dest / "SKILL.md").read_text(encoding="utf-8"), "user-modified\n")

    def test_dry_run_writes_nothing(self) -> None:
        kit = self.mini_kit()
        project = self.new_dir("project")
        code, lines = inst.run_install(
            repo_root=kit,
            platform="claude",
            scope="project",
            project_root=project,
            mode="copy",
            dry_run=True,
            force=False,
            skill_names=["d2269-architect"],
        )
        self.assertEqual(code, 0)
        self.assertFalse((project / ".claude" / "skills" / "d2269-architect").exists())
        self.assertTrue(any("would install d2269-architect" in item for item in lines))

    def test_copy_includes_bundled_assets_and_resolves_links(self) -> None:
        project = self.new_dir("project")
        code, _lines = inst.run_install(
            repo_root=REPO_ROOT,
            platform="codex",
            scope="project",
            project_root=project,
            mode="copy",
            dry_run=False,
            force=False,
            skill_names=["d2269-architect"],
        )
        self.assertEqual(code, 0)
        dest = project / ".agents" / "skills" / "d2269-architect"
        self.assertTrue((dest / "assets" / "architecture-handoff.md").is_file())
        for markdown in dest.rglob("*.md"):
            for target in vs.extract_markdown_targets(
                markdown.read_text(encoding="utf-8")
            ):
                if vs.is_external_or_anchor(target):
                    continue
                resolved = (markdown.parent / target.split("#", 1)[0]).resolve()
                self.assertTrue(resolved.exists(), f"broken installed link: {target}")
                resolved.relative_to(dest.resolve())

    def test_symlink_install(self) -> None:
        kit = self.mini_kit()
        project = self.new_dir("project")
        code, _lines = inst.run_install(
            repo_root=kit,
            platform="codex",
            scope="project",
            project_root=project,
            mode="symlink",
            dry_run=False,
            force=False,
            skill_names=["d2269-architect"],
        )
        self.assertEqual(code, 0)
        dest = project / ".agents" / "skills" / "d2269-architect"
        self.assertTrue(dest.is_symlink())
        self.assertEqual(dest.resolve(), (kit / "skills" / "d2269-architect").resolve())

    def test_unprefixed_copy_is_reported_without_claiming_ownership(self) -> None:
        kit = self.mini_kit()
        project = self.new_dir("project")
        legacy = project / ".agents" / "skills" / "architect"
        legacy.mkdir(parents=True)
        (legacy / "SKILL.md").write_text("legacy\n", encoding="utf-8")

        code, lines = inst.run_install(
            repo_root=kit,
            platform="codex",
            scope="project",
            project_root=project,
            mode="copy",
            dry_run=False,
            force=False,
            skill_names=["d2269-architect"],
        )

        self.assertEqual(code, 0)
        self.assertTrue((legacy / "SKILL.md").is_file())
        self.assertTrue(
            any(
                item.startswith(
                    "WARNING a potentially legacy or unrelated skill exists"
                )
                and "confirm it is an earlier D2269 installation" in item
                for item in lines
            )
        )
        self.assertTrue(
            (project / ".agents" / "skills" / "d2269-architect" / "SKILL.md").is_file()
        )

    def test_cli_herdr_exits_nonzero(self) -> None:
        self.assertEqual(inst.main(["--platform", "herdr", "--root", str(REPO_ROOT)]), 2)


if __name__ == "__main__":
    unittest.main()
