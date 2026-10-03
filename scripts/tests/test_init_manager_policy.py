#!/usr/bin/env python3
"""Tests for optional D2269 manager-policy initialization and validation."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import init_manager_policy as init  # noqa: E402
import validate_manager_policy as validation  # noqa: E402

TEST_TMP = Path(__file__).resolve().parent / ".tmp"


def tearDownModule() -> None:
    shutil.rmtree(TEST_TMP, ignore_errors=True)


class ManagerPolicyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(dir=TEST_TMP))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def project(self, name: str = "project") -> Path:
        root = self.tmp / name
        root.mkdir()
        return root

    def template(self) -> dict[str, object]:
        return json.loads((REPO_ROOT / "manager-policy" / "template.json").read_text())

    def initialize(
        self,
        project: Path,
        *,
        dry_run: bool = False,
        add_agents_marker: bool = False,
    ) -> tuple[int, list[str]]:
        return init.run_init(
            project_root=project,
            repo_root=REPO_ROOT,
            dry_run=dry_run,
            add_agents_marker=add_agents_marker,
        )


class PolicyValidationTests(ManagerPolicyTestCase):
    def test_template_and_schema_are_valid_json_and_template_is_valid(self) -> None:
        schema = json.loads((REPO_ROOT / "manager-policy" / "schema.json").read_text())
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(
            set(schema["properties"]["routes"]["properties"]),
            set(validation.SKILL_NAMES),
        )
        self.assertEqual(validation.validate_policy(self.template()), [])

    def test_accepts_native_and_herdr_routes(self) -> None:
        policy = self.template()
        routes = policy["routes"]  # type: ignore[index]
        routes["d2269-developer"] = {  # type: ignore[index]
            "primary": {
                "executor": "herdr",
                "kind": "local-worker",
                "model": "project-configured",
                "args": [],
            },
            "alternatives": [{"executor": "native", "model": "runtime-configured"}],
        }
        self.assertEqual(validation.validate_policy(policy), [])

    def test_accepts_partial_routes_and_requires_primary_for_configured_role(self) -> None:
        policy = self.template()
        policy["routes"]["d2269-developer"] = {  # type: ignore[index]
            "primary": {"executor": "native", "model": "opaque-runtime-id"},
            "alternatives": [],
        }
        self.assertEqual(validation.validate_policy(policy), [])
        del policy["routes"]["d2269-developer"]["primary"]  # type: ignore[index]
        self.assertTrue(any("missing required field" in error for error in validation.validate_policy(policy)))

    def test_rejects_unknown_fields_and_skills(self) -> None:
        policy = self.template()
        policy["provider"] = "unknown"  # type: ignore[index]
        self.assertTrue(any("unknown field" in error for error in validation.validate_policy(policy)))

        policy = self.template()
        policy["routes"]["d2269-manager"] = {"primary": {}, "alternatives": []}  # type: ignore[index]
        self.assertTrue(any("unknown field" in error for error in validation.validate_policy(policy)))

    def test_rejects_bad_executor_shapes(self) -> None:
        policy = self.template()
        policy["routes"]["d2269-developer"] = {  # type: ignore[index]
            "primary": {"executor": "invented"}, "alternatives": []
        }
        self.assertTrue(any("executor must" in error for error in validation.validate_policy(policy)))

        policy = self.template()
        policy["routes"]["d2269-developer"] = {  # type: ignore[index]
            "primary": {
                "executor": "herdr",
                "kind": "worker",
                "model": "opaque",
                "args": [1],
            },
            "alternatives": [],
        }
        self.assertTrue(any("array of strings" in error for error in validation.validate_policy(policy)))

        policy = self.template()
        policy["routes"]["d2269-developer"] = {  # type: ignore[index]
            "primary": {"executor": "herdr", "kind": "worker", "args": []},
            "alternatives": [],
        }
        self.assertTrue(any("missing required field" in error for error in validation.validate_policy(policy)))

    def test_rejects_bad_version_and_removed_policy_switches(self) -> None:
        for field, bad_value in (
            ("schema_version", "2"),
            ("fallback_policy", "use-alternative"),
            ("allow_unlisted_workers", True),
        ):
            with self.subTest(field=field):
                policy = self.template()
                policy[field] = bad_value  # type: ignore[index]
                self.assertTrue(validation.validate_policy(policy))

    def test_rejects_credential_fields_and_never_echoes_user_keys_or_values(self) -> None:
        policy = self.template()
        secret_value = "very-private-test-value"
        secret_key = "private-token-name"
        policy["routes"]["d2269-developer"] = {  # type: ignore[index]
            "primary": {
                "executor": "native",
                "model": "opaque",
                secret_key: secret_value,
            },
            "alternatives": [],
        }
        errors = validation.validate_policy(policy)
        self.assertTrue(any("credential-like field" in error for error in errors))
        self.assertNotIn(secret_key, " ".join(errors))
        self.assertNotIn(secret_value, " ".join(errors))

        policy = self.template()
        policy["routes"]["d2269-developer"] = {  # type: ignore[index]
            "primary": {
                "executor": "herdr",
                "kind": "worker",
                "model": "opaque",
                "args": ["--token=not-a-secret"],
            },
            "alternatives": [],
        }
        self.assertTrue(any("credential-like command-line" in error for error in validation.validate_policy(policy)))

        policy = self.template()
        policy["routes"]["d2269-developer"] = {  # type: ignore[index]
            "primary": {
                "executor": "herdr",
                "kind": "worker",
                "model": "opaque",
                "args": ["ghp_123456789012345678901234567890123456"],
            },
            "alternatives": [],
        }
        self.assertTrue(any("credential-like value" in error for error in validation.validate_policy(policy)))

    def test_rejects_required_environment_and_token_value_families(self) -> None:
        secret_arguments = (
            "--token=value",
            "--token value",
            "--api-key=value",
            "--env OPENAI_API_KEY=value",
            "OPENAI_API_KEY=value",
            "Bearer abcdefghijklmnop",
            "sk-12345678901234567890",
            "ghp_123456789012345678901234567890123456",
            "glpat-12345678901234567890",
            "xoxb-123456789012-123456789012-abcdefghijkl",
            "AKIA1234567890ABCDEF",
            "ASIA1234567890ABCDEF",
        )
        for args in secret_arguments:
            with self.subTest(args_label=args.split()[0]):
                policy = self.template()
                policy["routes"]["d2269-developer"] = {  # type: ignore[index]
                    "primary": {
                        "executor": "herdr",
                        "kind": "worker",
                        "model": "opaque",
                        "args": args.split(),
                    },
                    "alternatives": [],
                }
                errors = validation.validate_policy(policy)
                self.assertTrue(errors)
                self.assertNotIn(args, " ".join(errors))

    def test_environment_wrapper_parsing_uses_argument_boundaries(self) -> None:
        rejected = (
            ["--env", "OPENAI_API_KEY", "synthetic-value"],
            ["--environment", "OPENAI_API_KEY,synthetic-value"],
            ["-e", "OPENAI_API_KEY=synthetic-value"],
            ["--env=OPENAI_API_KEY,synthetic-value"],
            ["--env=OPENAI_API_KEY=synthetic-value"],
            ["--environment=OPENAI_API_KEY,synthetic-value"],
            ["-e=OPENAI_API_KEY=synthetic-value"],
        )
        accepted = (
            ["--env", "MAX_OUTPUT_TOKENS", "2048"],
            ["--environment", "MAX_OUTPUT_TOKENS,2048"],
            ["-e", "MAX_OUTPUT_TOKENS=2048"],
            ["--env", "BUILD_MAX_OUTPUT_TOKENS", "2048"],
            ["--env=MAX_OUTPUT_TOKENS,2048"],
            ["--environment=MAX_OUTPUT_TOKENS=2048"],
            ["-e=BUILD_MAX_OUTPUT_TOKENS,2048"],
        )

        def policy_with_args(args: list[str]) -> dict[str, object]:
            policy = self.template()
            policy["routes"]["d2269-developer"] = {  # type: ignore[index]
                "primary": {
                    "executor": "herdr",
                    "kind": "worker",
                    "model": "opaque",
                    "args": args,
                },
                "alternatives": [],
            }
            return policy

        for args in rejected:
            with self.subTest(args=args):
                errors = validation.validate_policy(policy_with_args(args))
                self.assertTrue(errors)
                self.assertNotIn("synthetic-value", " ".join(errors))
        for args in accepted:
            with self.subTest(args=args):
                self.assertEqual(validation.validate_policy(policy_with_args(args)), [])

    def test_environment_name_matrix_rejects_credential_names_and_allows_token_limit(self) -> None:
        forms = (
            lambda name: [f"{name}=synthetic-value"],
            lambda name: ["--env", name, "synthetic-value"],
            lambda name: ["--environment", f"{name},synthetic-value"],
            lambda name: ["-e", f"{name}=synthetic-value"],
            lambda name: [f"--env={name},synthetic-value"],
            lambda name: [f"--env={name}=synthetic-value"],
            lambda name: [f"--environment={name},synthetic-value"],
            lambda name: [f"-e={name}=synthetic-value"],
        )

        def policy_with_args(args: list[str]) -> dict[str, object]:
            policy = self.template()
            policy["routes"]["d2269-developer"] = {  # type: ignore[index]
                "primary": {
                    "executor": "herdr",
                    "kind": "worker",
                    "model": "opaque",
                    "args": args,
                },
                "alternatives": [],
            }
            return policy

        for name in (
            "AWS_ACCESS_KEY_ID",
            "PROD_AWS_ACCESS_KEY_ID",
            "PRIVATE_KEY",
            "SERVICE_PRIVATE_KEY",
        ):
            for make_args in forms:
                args = make_args(name)
                with self.subTest(name=name, args=args):
                    errors = validation.validate_policy(policy_with_args(args))
                    self.assertTrue(errors)
                    diagnostic = " ".join(errors)
                    self.assertNotIn(name, diagnostic)
                    self.assertNotIn("synthetic-value", diagnostic)

        for name in ("MAX_OUTPUT_TOKENS", "BUILD_MAX_OUTPUT_TOKENS"):
            for make_args in forms:
                with self.subTest(name=name, args=make_args(name)):
                    self.assertEqual(
                        validation.validate_policy(policy_with_args(make_args(name))),
                        [],
                    )

    def test_unrelated_argument_boundaries_are_not_joined_for_secret_values(self) -> None:
        policy = self.template()
        policy["routes"]["d2269-developer"] = {  # type: ignore[index]
            "primary": {
                "executor": "herdr",
                "kind": "worker",
                "model": "opaque",
                "args": ["ordinary-prefix", "sk-", "ordinary-suffix"],
            },
            "alternatives": [],
        }
        self.assertEqual(validation.validate_policy(policy), [])

    def test_unknown_and_duplicate_json_fields_do_not_echo_user_controlled_text(self) -> None:
        policy = self.template()
        private_key = "customer-private-key-name"
        policy[private_key] = "innocent-value"  # type: ignore[index]
        errors = validation.validate_policy(policy)
        self.assertTrue(errors)
        self.assertNotIn(private_key, " ".join(errors))
        self.assertNotIn("innocent-value", " ".join(errors))

        path = self.tmp / "duplicate.json"
        duplicate_key = "hidden-secret-field"
        path.write_text(
            '{"schema_version":"1","' + duplicate_key + '":1,"' + duplicate_key + '":2}',
            encoding="utf-8",
        )
        with self.assertRaises(validation.PolicyError) as raised:
            validation.load_policy(path)
        self.assertNotIn(duplicate_key, str(raised.exception))

    def test_accepts_benign_argument_containing_token_substring(self) -> None:
        policy = self.template()
        policy["routes"]["d2269-developer"] = {  # type: ignore[index]
            "primary": {
                "executor": "herdr",
                "kind": "worker",
                "model": "opaque",
                "args": ["--max-output-tokens", "2048"],
            },
            "alternatives": [],
        }
        self.assertEqual(validation.validate_policy(policy), [])

        policy["routes"]["d2269-developer"]["primary"] = {  # type: ignore[index]
            "executor": "herdr",
            "kind": "worker",
            "model": "opaque",
            "args": ["MAX_OUTPUT_TOKENS=2048"],
        }
        self.assertEqual(validation.validate_policy(policy), [])

    def test_rejects_duplicate_json_fields(self) -> None:
        path = self.tmp / "duplicate.json"
        path.write_text('{"schema_version":"1","schema_version":"1"}', encoding="utf-8")
        with self.assertRaises(validation.PolicyError):
            validation.load_policy(path)


class InitializerTests(ManagerPolicyTestCase):
    @unittest.skipUnless(hasattr(os, "mkfifo"), "physical FIFO creation unavailable")
    def test_policy_fifo_is_refused_without_blocking_or_modification(self) -> None:
        project = self.project()
        policy_dir = project / ".d2269"
        policy_dir.mkdir()
        fifo_path = policy_dir / "manager-policy.json"
        os.mkfifo(fifo_path)
        before = fifo_path.lstat()

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "init_manager_policy.py"),
                "--project-root",
                str(project),
                "--root",
                str(REPO_ROOT),
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )

        after = fifo_path.lstat()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(stat.S_ISFIFO(after.st_mode))
        self.assertEqual((after.st_dev, after.st_ino, after.st_mode), (before.st_dev, before.st_ino, before.st_mode))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "physical FIFO creation unavailable")
    def test_agents_fifo_is_refused_without_blocking_or_changing_policy(self) -> None:
        project = self.project()
        policy_dir = project / ".d2269"
        policy_dir.mkdir()
        policy_path = policy_dir / "manager-policy.json"
        original_policy = '{"project":"preserve"}\n'
        policy_path.write_text(original_policy, encoding="utf-8")
        agents_path = project / "AGENTS.md"
        os.mkfifo(agents_path)
        before = agents_path.lstat()

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "init_manager_policy.py"),
                "--project-root",
                str(project),
                "--root",
                str(REPO_ROOT),
                "--add-agents-marker",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )

        after = agents_path.lstat()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(policy_path.read_text(encoding="utf-8"), original_policy)
        self.assertTrue(stat.S_ISFIFO(after.st_mode))
        self.assertEqual((after.st_dev, after.st_ino, after.st_mode), (before.st_dev, before.st_ino, before.st_mode))

    def test_requires_existing_project_directory(self) -> None:
        with self.assertRaisesRegex(init.InitError, "missing or changed"):
            self.initialize(self.tmp / "missing")

        not_a_directory = self.tmp / "file"
        not_a_directory.write_text("content", encoding="utf-8")
        with self.assertRaisesRegex(init.InitError, "non-directory"):
            self.initialize(not_a_directory)

    def test_dry_run_writes_nothing(self) -> None:
        project = self.project()
        original = "# Existing instructions\n"
        (project / "AGENTS.md").write_text(original, encoding="utf-8")
        with self.assertRaises(init.InitError):
            self.initialize(project, dry_run=True, add_agents_marker=True)
        self.assertFalse((project / ".d2269").exists())
        self.assertEqual((project / "AGENTS.md").read_text(), original)

        project = self.project("dry-run-empty")
        code, lines = self.initialize(project, dry_run=True, add_agents_marker=True)
        self.assertEqual(code, 0)
        self.assertFalse((project / ".d2269").exists())
        self.assertFalse((project / "AGENTS.md").exists())
        self.assertTrue(any("dry-run" in line for line in lines))

    def test_creates_template_without_modifying_agents_by_default(self) -> None:
        project = self.project()
        agents = project / "AGENTS.md"
        original = "# Project instructions\n"
        agents.write_text(original, encoding="utf-8")

        code, lines = self.initialize(project)

        self.assertEqual(code, 0)
        policy_path = project / ".d2269" / "manager-policy.json"
        self.assertEqual(json.loads(policy_path.read_text()), self.template())
        self.assertEqual(agents.read_text(), original)
        self.assertTrue(any(line.startswith("created ") for line in lines))

    def test_creates_agents_file_with_bounded_marker_only_when_requested(self) -> None:
        project = self.project()
        agents = project / "AGENTS.md"

        self.initialize(project, add_agents_marker=True)
        result = agents.read_text(encoding="utf-8")
        self.assertIn(init.MARKER_BLOCK, result)
        self.assertEqual(result.count(init.MARKER_START), 1)
        self.assertEqual(result.count(init.MARKER_END), 1)

        code, lines = self.initialize(project, add_agents_marker=True)
        self.assertEqual(code, 0)
        self.assertEqual(agents.read_text(encoding="utf-8"), result)
        self.assertTrue(any(line.startswith("unchanged exact manager-policy marker") for line in lines))

    def test_existing_agents_without_exact_marker_is_refused_without_mutation(self) -> None:
        project = self.project()
        agents = project / "AGENTS.md"
        original = "# Existing project instructions\n"
        agents.write_text(original, encoding="utf-8")
        with self.assertRaisesRegex(init.InitError, "exists without the exact"):
            self.initialize(project, add_agents_marker=True)
        self.assertEqual(agents.read_text(encoding="utf-8"), original)
        self.assertFalse((project / ".d2269").exists())

    def test_conflicting_or_partial_agents_marker_is_refused_without_mutation(self) -> None:
        project = self.project()
        agents = project / "AGENTS.md"
        for content in (
            f"{init.MARKER_START}\ncustom\n{init.MARKER_END}\n",
            f"{init.MARKER_START}\npartial\n",
        ):
            agents.write_text(content, encoding="utf-8")
            with self.assertRaises(init.InitError):
                self.initialize(project, add_agents_marker=True)
            self.assertEqual(agents.read_text(encoding="utf-8"), content)
            self.assertFalse((project / ".d2269").exists())

    def test_existing_policy_is_preserved_and_initialization_is_idempotent(self) -> None:
        project = self.project()
        self.initialize(project)
        self.assertEqual(self.initialize(project)[0], 0)

        policy_path = project / ".d2269" / "manager-policy.json"
        policy_path.write_text('{"user":"content"}\n', encoding="utf-8")
        code, lines = self.initialize(project)
        self.assertEqual(code, 0)
        self.assertTrue(any(line.startswith("unchanged ") for line in lines))
        self.assertEqual(policy_path.read_text(), '{"user":"content"}\n')

    def test_symlink_destinations_are_refused(self) -> None:
        project = self.project()
        outside = self.tmp / "outside"
        outside.mkdir()
        victim = outside / "manager-policy.json"
        victim.write_text("leave-me-alone", encoding="utf-8")
        (project / ".d2269").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(init.InitError):
            self.initialize(project)
        self.assertEqual(victim.read_text(encoding="utf-8"), "leave-me-alone")

        (project / ".d2269").unlink()
        agents = project / "AGENTS.md"
        agents.symlink_to(outside / "AGENTS.md")
        with self.assertRaises(init.InitError):
            self.initialize(project, add_agents_marker=True)
        self.assertFalse((outside / "AGENTS.md").exists())

    def test_policy_directory_symlink_swap_before_open_is_refused(self) -> None:
        project = self.project()
        outside = self.tmp / "outside"
        outside.mkdir()
        victim = outside / "manager-policy.json"
        victim.write_text("untouched", encoding="utf-8")

        original_open = init._open_policy_directory
        injected = False

        def replace_with_symlink(root_fd: int, display_path: Path, *, create: bool) -> int | None:
            nonlocal injected
            if create and not injected:
                injected = True
                (project / ".d2269").symlink_to(outside, target_is_directory=True)
            return original_open(root_fd, display_path, create=create)

        with mock.patch.object(init, "_open_policy_directory", side_effect=replace_with_symlink):
            with self.assertRaises(init.InitError):
                self.initialize(project)
        self.assertEqual(victim.read_text(encoding="utf-8"), "untouched")

    def test_project_root_rejects_symlinked_parent_component(self) -> None:
        real_parent = self.tmp / "real-parent"
        real_parent.mkdir()
        project = real_parent / "project"
        project.mkdir()
        alias = self.tmp / "alias"
        alias.symlink_to(real_parent, target_is_directory=True)

        with self.assertRaisesRegex(init.InitError, "symlink component"):
            self.initialize(alias / "project")
        self.assertFalse((project / ".d2269").exists())

    def test_project_root_detects_intermediate_parent_replacement_during_walk(self) -> None:
        parent = self.tmp / "parent"
        parent.mkdir()
        project = parent / "project"
        project.mkdir()
        outside = self.tmp / "outside"
        outside.mkdir()
        pinned_name = self.tmp / "pinned-parent"
        real_open = os.open
        injected = False

        def replace_parent_before_leaf_open(
            path: str,
            flags: int,
            mode: int = 0o777,
            *,
            dir_fd: int | None = None,
        ) -> int:
            nonlocal injected
            if path == "project" and dir_fd is not None and not injected:
                injected = True
                parent.rename(pinned_name)
                parent.symlink_to(outside, target_is_directory=True)
            return real_open(path, flags, mode, dir_fd=dir_fd)

        with mock.patch.object(init.os, "open", side_effect=replace_parent_before_leaf_open):
            with self.assertRaisesRegex(init.InitError, "changed during component traversal"):
                self.initialize(project)
        self.assertFalse((outside / ".d2269").exists())
        self.assertFalse((pinned_name / "project" / ".d2269").exists())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_opened_policy_directory_descriptor_survives_name_swap(self) -> None:
        project = self.project()
        outside = self.tmp / "outside"
        outside.mkdir()
        victim = outside / "manager-policy.json"
        victim.write_text("untouched", encoding="utf-8")
        original_open = init._open_policy_directory
        swapped = False

        def swap_name_after_open(root_fd: int, display_path: Path, *, create: bool) -> int | None:
            nonlocal swapped
            descriptor = original_open(root_fd, display_path, create=create)
            if create and descriptor is not None and not swapped:
                swapped = True
                (project / ".d2269").rename(project / "pinned-directory")
                (project / ".d2269").symlink_to(outside, target_is_directory=True)
            return descriptor

        with mock.patch.object(init, "_open_policy_directory", side_effect=swap_name_after_open):
            self.initialize(project)
        self.assertEqual(victim.read_text(encoding="utf-8"), "untouched")
        self.assertTrue((project / "pinned-directory" / "manager-policy.json").exists())

    def test_agents_creation_race_leaves_policy_and_requests_manual_inspection(self) -> None:
        project = self.project()
        outside = self.tmp / "outside"
        outside.mkdir()
        victim = outside / "AGENTS.md"
        victim.write_text("untouched", encoding="utf-8")
        original_write = init._write_new_file_at
        injected = False

        def add_raced_symlink(
            directory_fd: int, filename: str, contents: str, display_path: Path
        ) -> tuple[int, int]:
            nonlocal injected
            if filename == "AGENTS.md" and not injected:
                injected = True
                (project / "AGENTS.md").symlink_to(victim)
            return original_write(directory_fd, filename, contents, display_path)

        with mock.patch.object(init, "_write_new_file_at", side_effect=add_raced_symlink):
            with self.assertRaises(init.InitError) as raised:
                self.initialize(project, add_agents_marker=True)
        self.assertEqual(victim.read_text(encoding="utf-8"), "untouched")
        policy_path = project / ".d2269" / "manager-policy.json"
        self.assertTrue(policy_path.exists())
        self.assertIn("policy remains", str(raised.exception))
        self.assertIn("inspect both destinations manually", str(raised.exception))

    def test_agents_creation_failure_preserves_existing_policy(self) -> None:
        project = self.project()
        policy_path = project / ".d2269" / "manager-policy.json"
        policy_path.parent.mkdir()
        original_policy = '{"project":"existing"}\n'
        policy_path.write_text(original_policy, encoding="utf-8")
        outside = self.tmp / "outside"
        outside.mkdir()
        agents = project / "AGENTS.md"
        original_write = init._write_new_file_at

        def add_agents_race(
            directory_fd: int, filename: str, contents: str, display_path: Path
        ) -> None:
            if filename == "AGENTS.md":
                agents.symlink_to(outside / "AGENTS.md")
            original_write(directory_fd, filename, contents, display_path)

        with mock.patch.object(init, "_write_new_file_at", side_effect=add_agents_race):
            with self.assertRaises(init.InitError):
                self.initialize(project, add_agents_marker=True)
        self.assertEqual(policy_path.read_text(encoding="utf-8"), original_policy)

    def test_write_failure_never_unlinks_and_requests_manual_inspection(self) -> None:
        project = self.project()
        writer = mock.MagicMock()
        writer.__enter__.return_value = writer
        writer.__exit__.return_value = False
        writer.write.side_effect = OSError("synthetic write failure")

        with mock.patch.object(init.os, "fdopen", return_value=writer), mock.patch.object(
            init.os, "unlink", side_effect=AssertionError("automatic unlink is forbidden")
        ):
            with self.assertRaisesRegex(init.InitError, "inspect and remove it manually"):
                self.initialize(project)
        policy_path = project / ".d2269" / "manager-policy.json"
        self.assertTrue(policy_path.exists())
        self.assertEqual(policy_path.read_text(encoding="utf-8"), "")

    def test_flush_failure_leaves_published_file_for_manual_inspection(self) -> None:
        project = self.project()
        writer = mock.MagicMock()
        writer.__enter__.return_value = writer
        writer.__exit__.return_value = False
        writer.flush.side_effect = OSError("synthetic flush failure")

        with mock.patch.object(init.os, "fdopen", return_value=writer):
            with self.assertRaisesRegex(init.InitError, "inspect and remove it manually"):
                self.initialize(project)
        self.assertTrue((project / ".d2269" / "manager-policy.json").exists())

    def test_close_failure_leaves_published_file_for_manual_inspection(self) -> None:
        project = self.project()
        destination = project / ".d2269"
        destination.mkdir()
        directory_fd = os.open(destination, os.O_RDONLY | os.O_DIRECTORY)
        real_close = init._close_descriptor

        def close_then_report_failure(file_fd: int) -> None:
            if file_fd != directory_fd:
                real_close(file_fd)
                raise OSError("synthetic close failure")
            real_close(file_fd)

        try:
            with mock.patch.object(init, "_close_descriptor", side_effect=close_then_report_failure):
                with self.assertRaisesRegex(init.InitError, "inspect and remove"):
                    init._write_new_file_at(
                        directory_fd,
                        "manager-policy.json",
                        json.dumps(self.template()),
                        destination / "manager-policy.json",
                    )
        finally:
            real_close(directory_fd)
        self.assertTrue((destination / "manager-policy.json").exists())

    def _assert_final_close_failure_is_reported(self, *, fail_policy_fd: bool) -> None:
        project = self.project()
        policy_path = project / ".d2269" / "manager-policy.json"
        descriptors: dict[str, int] = {}
        real_open_root = init._open_project_root
        real_open_policy = init._open_policy_directory
        real_close = init._close_descriptor

        def capture_root(path: Path) -> tuple[int, Path]:
            descriptor, root = real_open_root(path)
            descriptors["root"] = descriptor
            return descriptor, root

        def capture_policy(root_fd: int, display_path: Path, *, create: bool) -> int | None:
            descriptor = real_open_policy(root_fd, display_path, create=create)
            if descriptor is not None and create:
                descriptors["policy"] = descriptor
            return descriptor

        def close_selected(descriptor: int) -> None:
            target = "policy" if fail_policy_fd else "root"
            if descriptors.get(target) == descriptor:
                real_close(descriptor)
                raise OSError("synthetic directory close failure")
            real_close(descriptor)

        captured_stderr = io.StringIO()
        with mock.patch.object(init, "_open_project_root", side_effect=capture_root), mock.patch.object(
            init, "_open_policy_directory", side_effect=capture_policy
        ), mock.patch.object(init, "_close_descriptor", side_effect=close_selected), mock.patch.object(
            init.os, "unlink", side_effect=AssertionError("automatic unlink is forbidden")
        ), contextlib.redirect_stderr(captured_stderr):
            status = init.main(["--project-root", str(project), "--root", str(REPO_ROOT)])

        self.assertEqual(status, 2)
        self.assertTrue(policy_path.is_file())
        self.assertEqual(json.loads(policy_path.read_text(encoding="utf-8")), self.template())
        self.assertIn("manually inspect", captured_stderr.getvalue())
        self.assertIn(str(policy_path), captured_stderr.getvalue())

    def test_policy_directory_close_failure_after_publication_is_actionable(self) -> None:
        self._assert_final_close_failure_is_reported(fail_policy_fd=True)

    def test_root_directory_close_failure_after_publication_is_actionable(self) -> None:
        self._assert_final_close_failure_is_reported(fail_policy_fd=False)

    def test_root_close_failure_without_publication_does_not_claim_published_files(self) -> None:
        project = self.project()
        real_open_root = init._open_project_root
        real_close = init._close_descriptor
        root_fd: int | None = None

        def capture_root(path: Path) -> tuple[int, Path]:
            nonlocal root_fd
            root_fd, root = real_open_root(path)
            return root_fd, root

        def fail_root_close(descriptor: int) -> None:
            real_close(descriptor)
            if descriptor == root_fd:
                raise OSError("synthetic root close failure")

        captured_stderr = io.StringIO()
        with mock.patch.object(init, "_open_project_root", side_effect=capture_root), mock.patch.object(
            init, "_close_descriptor", side_effect=fail_root_close
        ), contextlib.redirect_stderr(captured_stderr):
            status = init.main([
                "--project-root", str(project), "--root", str(REPO_ROOT), "--dry-run"
            ])

        self.assertEqual(status, 2)
        self.assertFalse((project / ".d2269").exists())
        self.assertIn("no destination was published", captured_stderr.getvalue())
        self.assertNotIn("manually inspect", captured_stderr.getvalue())

    def test_fsync_failure_leaves_policy_for_manual_inspection(self) -> None:
        project = self.project()
        with mock.patch.object(init.os, "fsync", side_effect=OSError("synthetic fsync failure")):
            with self.assertRaisesRegex(init.InitError, "inspect and remove it manually"):
                self.initialize(project)
        policy_path = project / ".d2269" / "manager-policy.json"
        self.assertTrue(policy_path.exists())
        self.assertEqual(json.loads(policy_path.read_text(encoding="utf-8")), self.template())

    def test_later_failure_does_not_unlink_a_concurrently_replaced_policy_path(self) -> None:
        project = self.project()
        policy_path = project / ".d2269" / "manager-policy.json"

        def replace_then_fail(_fd: int) -> None:
            policy_path.unlink()
            policy_path.write_text("concurrent replacement", encoding="utf-8")
            raise OSError("synthetic fsync failure")

        with mock.patch.object(init.os, "fsync", side_effect=replace_then_fail):
            with self.assertRaisesRegex(init.InitError, "inspect and remove it manually"):
                self.initialize(project)
        self.assertEqual(policy_path.read_text(encoding="utf-8"), "concurrent replacement")

    def test_fails_closed_when_descriptor_relative_support_is_missing(self) -> None:
        project = self.project()
        with mock.patch.object(os, "supports_dir_fd", set()):
            with self.assertRaisesRegex(init.InitError, "unsupported"):
                self.initialize(project)
        self.assertFalse((project / ".d2269").exists())


if __name__ == "__main__":
    unittest.main()
