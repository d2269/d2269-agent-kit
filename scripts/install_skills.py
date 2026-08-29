#!/usr/bin/env python3
"""Install canonical skills into verified agent discovery paths.

Stdlib only. Non-destructive by default. Supports dry-run and symlink or copy.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from validate_skills import repo_root_from, skill_directories

HERDR_TODO = (
    "Herdr does not document a first-party directory for third-party role skills. "
    "Install Cursor, Codex, or Claude adapters for agents that run inside Herdr. "
    "Keep the official Herdr skill installed from upstream. "
    "See adapters/herdr/README.md."
)

PLATFORMS = ("cursor", "codex", "claude", "herdr")
SCOPES = ("user", "project")
MODES = ("symlink", "copy")


class InstallError(Exception):
    pass


def _home() -> Path:
    return Path.home()


def destination_root(platform: str, scope: str, project_root: Path | None) -> Path:
    if platform == "herdr":
        raise InstallError(HERDR_TODO)
    if scope == "project":
        if project_root is None:
            raise InstallError("--project-root is required for --scope project")
        root = project_root.expanduser().resolve()
        if not root.exists():
            raise InstallError(f"--project-root does not exist: {root}")
        if not root.is_dir():
            raise InstallError(f"--project-root is not a directory: {root}")
        if platform == "cursor":
            return root / ".cursor" / "skills"
        if platform == "codex":
            return root / ".agents" / "skills"
        if platform == "claude":
            return root / ".claude" / "skills"
    if platform == "cursor":
        return _home() / ".cursor" / "skills"
    if platform == "codex":
        return _home() / ".agents" / "skills"
    if platform == "claude":
        return _home() / ".claude" / "skills"
    raise InstallError(f"Unsupported platform/scope: {platform}/{scope}")


def tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_symlink() or path.is_file():
        digest.update(path.read_bytes())
        return digest.hexdigest()
    for item in sorted(path.rglob("*")):
        if item.is_dir() and not item.is_symlink():
            continue
        rel = item.relative_to(path).as_posix().encode()
        digest.update(rel)
        if item.is_symlink():
            digest.update(os.fsencode(os.readlink(item)))
        elif item.is_file():
            digest.update(item.read_bytes())
    return digest.hexdigest()


def same_content(source: Path, dest: Path) -> bool:
    if dest.is_symlink():
        try:
            return dest.resolve() == source.resolve()
        except OSError:
            return False
    if not dest.exists():
        return False
    return tree_digest(source) == tree_digest(dest)


def install_one(
    source: Path,
    dest: Path,
    *,
    mode: str,
    dry_run: bool,
    force: bool,
) -> str:
    dest_parent = dest.parent
    if dest.exists() or dest.is_symlink():
        if same_content(source, dest):
            return "unchanged"
        if not force:
            return "conflict"
        if not dry_run:
            if dest.is_dir() and not dest.is_symlink():
                shutil.rmtree(dest)
            else:
                dest.unlink()
    if dry_run:
        return "would-install"
    dest_parent.mkdir(parents=True, exist_ok=True)
    source = source.resolve()
    if mode == "symlink":
        os.symlink(source, dest)
    elif mode == "copy":
        shutil.copytree(source, dest)
    else:
        raise InstallError(f"Unknown mode: {mode}")
    return "installed"


def selected_skills(skills_root: Path, names: list[str] | None) -> list[Path]:
    available = skill_directories(skills_root)
    if not names:
        return available
    by_name = {path.name: path for path in available}
    missing = [name for name in names if name not in by_name]
    if missing:
        raise InstallError("Unknown skill(s): " + ", ".join(missing))
    return [by_name[name] for name in names]


def run_install(
    *,
    repo_root: Path,
    platform: str,
    scope: str,
    project_root: Path | None,
    mode: str,
    dry_run: bool,
    force: bool,
    skill_names: list[str] | None,
) -> tuple[int, list[str]]:
    dest_root = destination_root(platform, scope, project_root)
    skills = selected_skills(repo_root / "skills", skill_names)
    lines: list[str] = []
    conflicts = 0
    prefix = "dry-run: " if dry_run else ""
    lines.append(f"{prefix}destination root: {dest_root}")
    for source in skills:
        dest = dest_root / source.name
        status = install_one(source, dest, mode=mode, dry_run=dry_run, force=force)
        if status == "conflict":
            conflicts += 1
            lines.append(
                f"CONFLICT {source.name}: {dest} exists and differs from canonical source; "
                "not overwriting (pass --force to replace)"
            )
        elif status == "unchanged":
            lines.append(f"unchanged {source.name} -> {dest}")
        elif status == "would-install":
            lines.append(f"would install {source.name} -> {dest} ({mode})")
        else:
            lines.append(f"installed {source.name} -> {dest} ({mode})")
    code = 1 if conflicts else 0
    return code, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install canonical d2269-agent-kit skills into an agent discovery path."
    )
    parser.add_argument("--platform", required=True, choices=PLATFORMS)
    parser.add_argument("--scope", choices=SCOPES, default="user")
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--mode", choices=MODES, default="symlink")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace a destination that differs from the canonical skill",
    )
    parser.add_argument(
        "--skill",
        action="append",
        dest="skills",
        default=None,
        help="Install only this skill (repeatable)",
    )
    parser.add_argument("--root", type=Path, default=None, help="Kit repository root")
    args = parser.parse_args(argv)

    repo_root = args.root.resolve() if args.root else repo_root_from()
    try:
        code, lines = run_install(
            repo_root=repo_root,
            platform=args.platform,
            scope=args.scope,
            project_root=args.project_root,
            mode=args.mode,
            dry_run=args.dry_run,
            force=args.force,
            skill_names=args.skills,
        )
    except InstallError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
