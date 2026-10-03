#!/usr/bin/env python3
"""Initialize an optional project-local D2269 manager policy safely.

All project mutations are relative to an opened project directory and use
no-follow, exclusive creation. The implementation fails closed when the
platform cannot provide those filesystem guarantees.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from validate_manager_policy import PolicyError, validate_policy

POLICY_DIRECTORY = ".d2269"
POLICY_FILENAME = "manager-policy.json"
MARKER_START = "<!-- BEGIN D2269 MANAGER POLICY -->"
MARKER_END = "<!-- END D2269 MANAGER POLICY -->"
MARKER_BLOCK = (
    f"{MARKER_START}\n"
    "When delegating a D2269 role, read `.d2269/manager-policy.json` and use its "
    "configured primary. If it is missing or unavailable, ask the human. Use a "
    "listed alternative only after explicit human selection; never invent an "
    "executor. Preserve the role skill's responsibilities.\n"
    f"{MARKER_END}"
)
AGENTS_FILENAME = "AGENTS.md"
REQUIRED_FLAGS = (
    "O_DIRECTORY", "O_NOFOLLOW", "O_EXCL", "O_CREAT", "O_RDONLY", "O_WRONLY",
    "O_NONBLOCK",
)
DIRECTORY_RELATIVE_OPERATIONS = (os.open, os.mkdir, os.stat)


class InitError(ValueError):
    """Raised when initialization cannot proceed without risking user data."""


def _close_descriptor(descriptor: int) -> None:
    """Descriptor-close boundary kept small for state-aware finalization."""
    os.close(descriptor)


def _require_secure_filesystem_support() -> None:
    missing_flags = [name for name in REQUIRED_FLAGS if not hasattr(os, name)]
    unsupported = [
        name for name, operation in zip(
            ("open", "mkdir", "stat"), DIRECTORY_RELATIVE_OPERATIONS
        ) if operation not in os.supports_dir_fd
    ]
    if missing_flags or unsupported:
        details = []
        if missing_flags:
            details.append("required flags unavailable")
        if unsupported:
            details.append("descriptor-relative operations unavailable")
        raise InitError("secure project initialization is unsupported on this platform (" +
                        "; ".join(details) + ")")


def _read_template(repo_root: Path) -> str:
    template_path = repo_root / "manager-policy" / "template.json"
    try:
        policy = json.loads(template_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InitError("cannot read bundled policy template") from exc
    errors = validate_policy(policy)
    if errors:
        raise InitError("bundled policy template failed validation")
    return json.dumps(policy, indent=2, ensure_ascii=False) + "\n"


def _same_directory_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
        and stat.S_IFMT(left.st_mode) == stat.S_IFMT(right.st_mode)
        and stat.S_ISDIR(left.st_mode)
        and stat.S_ISDIR(right.st_mode)
    )


def _open_project_root(project_root: Path) -> tuple[int, Path]:
    """Open each absolute path component without following symlinks.

    Each component is checked before and after opening, and every pathname edge
    is rechecked after traversal. This detects swaps during path resolution.
    """
    absolute = Path(os.path.abspath(os.fspath(project_root.expanduser())))
    if absolute == Path("/"):
        raise InitError("project root must not be the filesystem root")
    try:
        current_fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        raise InitError("cannot safely open filesystem root") from exc

    opened_fds = [current_fd]
    edges: list[tuple[int, str, int]] = []
    try:
        for component in absolute.parts[1:]:
            try:
                before = os.stat(component, dir_fd=current_fd, follow_symlinks=False)
                if not stat.S_ISDIR(before.st_mode):
                    raise InitError("project root contains a non-directory or symlink component")
                child_fd = os.open(
                    component,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=current_fd,
                )
                opened_fds.append(child_fd)
                pinned = os.fstat(child_fd)
                after_open = os.stat(component, dir_fd=current_fd, follow_symlinks=False)
            except InitError:
                raise
            except OSError as exc:
                raise InitError("project root component is missing or changed during open") from exc
            if not _same_directory_identity(before, pinned) or not _same_directory_identity(pinned, after_open):
                raise InitError("project root changed during component traversal")
            edges.append((current_fd, component, child_fd))
            current_fd = child_fd

        for parent_fd, component, child_fd in edges:
            try:
                current_entry = os.stat(component, dir_fd=parent_fd, follow_symlinks=False)
                pinned = os.fstat(child_fd)
            except OSError as exc:
                raise InitError("project root changed during component traversal") from exc
            if not _same_directory_identity(current_entry, pinned):
                raise InitError("project root changed during component traversal")

        for fd in opened_fds[:-1]:
            _close_descriptor(fd)
        return opened_fds[-1], absolute
    except Exception:
        for fd in reversed(opened_fds):
            try:
                _close_descriptor(fd)
            except OSError:
                pass
        raise


def _read_regular_file_at(directory_fd: int, filename: str, display_path: Path) -> str | None:
    try:
        entry = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise InitError(f"cannot safely inspect {display_path}") from exc
    if not stat.S_ISREG(entry.st_mode):
        raise InitError(f"{display_path} is not a regular file")

    try:
        file_fd = os.open(
            filename,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=directory_fd,
        )
    except OSError as exc:
        raise InitError(f"cannot safely open {display_path}") from exc
    try:
        opened = os.fstat(file_fd)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_dev != entry.st_dev
            or opened.st_ino != entry.st_ino
        ):
            raise InitError(f"{display_path} is not a regular file")
        with os.fdopen(file_fd, "r", encoding="utf-8", closefd=False) as source:
            return source.read()
    except (OSError, UnicodeError) as exc:
        raise InitError(f"cannot safely read {display_path}") from exc
    finally:
        os.close(file_fd)


def _marker_state(text: str) -> str:
    starts = text.count(MARKER_START)
    ends = text.count(MARKER_END)
    if starts == 0 and ends == 0:
        return "absent"
    if starts != 1 or ends != 1:
        return "conflicting"
    start = text.index(MARKER_START)
    end = text.index(MARKER_END) + len(MARKER_END)
    if start > end or text[start:end] != MARKER_BLOCK:
        return "conflicting"
    return "present"


def _open_policy_directory(root_fd: int, display_path: Path, *, create: bool) -> int | None:
    try:
        directory_fd = os.open(
            POLICY_DIRECTORY,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=root_fd,
        )
    except FileNotFoundError:
        if not create:
            return None
        try:
            os.mkdir(POLICY_DIRECTORY, 0o755, dir_fd=root_fd)
        except FileExistsError:
            # Re-open the name with O_NOFOLLOW below; never trust the raced entry.
            pass
        except OSError as exc:
            raise InitError(f"cannot create {display_path}") from exc
        try:
            return os.open(
                POLICY_DIRECTORY,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=root_fd,
            )
        except OSError as exc:
            raise InitError(f"cannot safely open {display_path}") from exc
    except OSError as exc:
        raise InitError(f"cannot safely open {display_path}") from exc
    return directory_fd


def _write_new_file_at(
    directory_fd: int,
    filename: str,
    contents: str,
    display_path: Path,
) -> None:
    try:
        file_fd = os.open(
            filename,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o644,
            dir_fd=directory_fd,
        )
    except FileExistsError as exc:
        raise InitError(f"{display_path} appeared during initialization; no file was replaced") from exc
    except OSError as exc:
        raise InitError(f"cannot safely create {display_path}") from exc
    failure: str | None = None
    try:
        with os.fdopen(file_fd, "w", encoding="utf-8", closefd=False) as output:
            output.write(contents)
            output.flush()
        os.fsync(file_fd)
    except (OSError, UnicodeError):
        failure = (
            f"could not complete creation of {display_path}; the destination may be partial; "
            "inspect and remove it manually before retrying"
        )
    finally:
        try:
            _close_descriptor(file_fd)
        except OSError:
            if failure is None:
                failure = (
                    f"could not close newly created file {display_path}; inspect and remove "
                    "the destination manually before retrying"
                )
    if failure is not None:
        raise InitError(failure)


def _finalize_descriptors(
    policy_dir_fd: int | None,
    root_fd: int,
    *,
    primary_error: BaseException | None,
    published_paths: list[Path],
) -> None:
    close_errors: list[OSError] = []
    for descriptor in (policy_dir_fd, root_fd):
        if descriptor is None:
            continue
        try:
            _close_descriptor(descriptor)
        except OSError as exc:
            close_errors.append(exc)

    # A body failure remains authoritative. In particular, do not replace an
    # existing safe-stop message with a descriptor-close diagnostic.
    if primary_error is not None:
        raise primary_error.with_traceback(primary_error.__traceback__)
    if not close_errors:
        return

    if published_paths:
        destinations = ", ".join(str(path) for path in published_paths)
        message = (
            "could not finalize project directory descriptors after publishing files; "
            f"manually inspect the following destinations; removal may be required: {destinations}"
        )
    else:
        message = "could not finalize project directory descriptors; no destination was published"
    raise InitError(message) from close_errors[0]


def run_init(
    *,
    project_root: Path,
    repo_root: Path,
    dry_run: bool = False,
    add_agents_marker: bool = False,
) -> tuple[int, list[str]]:
    _require_secure_filesystem_support()
    template_text = _read_template(repo_root.resolve())
    root_fd, root = _open_project_root(project_root)
    display_policy_dir = root / POLICY_DIRECTORY
    display_policy = display_policy_dir / POLICY_FILENAME
    display_agents = root / AGENTS_FILENAME
    lines: list[str] = []

    policy_dir_fd: int | None = None
    policy_created = False
    published_paths: list[Path] = []
    primary_error: BaseException | None = None
    result: tuple[int, list[str]] | None = None
    try:
        policy_dir_fd = _open_policy_directory(root_fd, display_policy_dir, create=False)
        policy_state = "absent" if policy_dir_fd is None else "unknown"
        if policy_dir_fd is not None:
            existing = _read_regular_file_at(
                policy_dir_fd, POLICY_FILENAME, display_policy
            )
            policy_state = "present" if existing is not None else "absent"

        agents_text: str | None = None
        marker_state = "absent"
        if add_agents_marker:
            agents_text = _read_regular_file_at(root_fd, AGENTS_FILENAME, display_agents)
            if agents_text is not None:
                marker_state = _marker_state(agents_text)
                if marker_state == "absent":
                    raise InitError(
                        "AGENTS.md exists without the exact manager-policy marker; "
                        "add it manually or use a file with the exact marker"
                    )
                if marker_state == "conflicting":
                    raise InitError(
                        "AGENTS.md has a conflicting manager-policy marker; "
                        "resolve it manually"
                    )

        if policy_state == "present":
            lines.append(f"unchanged {display_policy}")
        elif dry_run:
            lines.append(f"dry-run: would create {display_policy}")
        else:
            if policy_dir_fd is None:
                policy_dir_fd = _open_policy_directory(
                    root_fd, display_policy_dir, create=True
                )
            assert policy_dir_fd is not None
            _write_new_file_at(policy_dir_fd, POLICY_FILENAME, template_text, display_policy)
            policy_created = True
            published_paths.append(display_policy)
            lines.append(f"created {display_policy}")

        if add_agents_marker:
            if marker_state == "present":
                lines.append(f"unchanged exact manager-policy marker in {display_agents}")
            elif dry_run:
                lines.append(f"dry-run: would create {display_agents} with the bounded marker")
            else:
                try:
                    _write_new_file_at(
                        root_fd, AGENTS_FILENAME, MARKER_BLOCK + "\n", display_agents
                    )
                    published_paths.append(display_agents)
                except InitError as exc:
                    message = str(exc)
                    if policy_created:
                        message += (
                            f"; the newly created policy remains at {display_policy}; "
                            "no automatic cleanup was attempted; inspect both destinations manually"
                        )
                    raise InitError(message) from exc
                lines.append(f"created {display_agents} with the bounded manager-policy marker")
        result = (0, lines)
    except BaseException as exc:
        primary_error = exc

    _finalize_descriptors(
        policy_dir_fd,
        root_fd,
        primary_error=primary_error,
        published_paths=published_paths,
    )
    assert result is not None
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create an optional project-local D2269 manager-policy template."
    )
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1],
        help="kit repository root",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--add-agents-marker",
        action="store_true",
        help="create AGENTS.md with the bounded manager-policy marker when absent",
    )
    args = parser.parse_args(argv)
    try:
        _code, lines = run_init(
            project_root=args.project_root,
            repo_root=args.root,
            dry_run=args.dry_run,
            add_agents_marker=args.add_agents_marker,
        )
    except (InitError, OSError, UnicodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
