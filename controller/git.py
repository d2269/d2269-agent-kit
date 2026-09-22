"""Git worktree isolation and exact implementation revision calculation."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

from .models import ExecutionContext


SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


class GitError(RuntimeError):
    pass


class GitWorktrees:
    def __init__(
        self,
        repository: Path,
        project_state_dir: Path,
        *,
        base_branch: str,
        branch_prefix: str,
    ):
        self.repository = repository.resolve()
        self.root = project_state_dir / "worktrees"
        self.base_branch = base_branch
        self.branch_prefix = branch_prefix

    def _run(
        self, args: list[str], *, cwd: Path | None = None, text: bool = True
    ) -> subprocess.CompletedProcess:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd or self.repository,
            capture_output=True,
            text=text,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr if text else result.stderr.decode("utf-8", "replace")
            raise GitError(f"git {' '.join(args)} failed: {stderr.strip()}")
        return result

    @staticmethod
    def _safe(value: str) -> str:
        return SAFE_NAME.sub("-", value).strip("-.")[:48] or "work"

    def developer_context(self, run_id: str, ticket_id: str) -> ExecutionContext:
        path = self.root / self._safe(run_id) / ("developer-" + self._safe(ticket_id))
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            branch = self.branch_prefix + self._safe(ticket_id.lower()) + "-" + run_id[:8]
            self._run(["worktree", "add", "-b", branch, str(path), self.base_branch])
        return ExecutionContext(path=path, implementation_revision=self.revision(path))

    def review_context(
        self,
        run_id: str,
        invocation_id: str,
        source: Path,
        expected_revision: str,
    ) -> ExecutionContext:
        path = self.root / self._safe(run_id) / self._safe(invocation_id)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            head = self._run(["rev-parse", "HEAD"], cwd=source).stdout.strip()
            self._run(["worktree", "add", "--detach", str(path), head])
            if expected_revision.startswith("snapshot:"):
                patch = self._run(["diff", "--binary", "HEAD"], cwd=source, text=False).stdout
                if patch:
                    applied = subprocess.run(
                        ["git", "apply", "--index", "--binary", "-"],
                        cwd=path,
                        input=patch,
                        capture_output=True,
                        check=False,
                    )
                    if applied.returncode != 0:
                        raise GitError(
                            "cannot reproduce snapshot in review worktree: "
                            + applied.stderr.decode("utf-8", "replace").strip()
                        )
                listed = self._run(
                    ["ls-files", "--others", "--exclude-standard", "-z"],
                    cwd=source,
                    text=False,
                ).stdout
                for raw in listed.split(b"\0"):
                    if not raw:
                        continue
                    relative = Path(os.fsdecode(raw))
                    target = path / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source / relative, target)
            actual = self.revision(path)
            if actual != expected_revision:
                raise GitError(
                    f"fresh context revision mismatch: expected {expected_revision}, observed {actual}"
                )
        return ExecutionContext(
            path=path,
            implementation_revision=expected_revision,
            source_path=source,
        )

    def revision(self, worktree: Path) -> str:
        head = self._run(["rev-parse", "HEAD"], cwd=worktree).stdout.strip()
        status = self._run(["status", "--porcelain", "-z"], cwd=worktree, text=False).stdout
        if not status:
            return "git:" + head
        digest = hashlib.sha256()
        digest.update(head.encode("ascii"))
        digest.update(self._run(["diff", "--binary", "HEAD"], cwd=worktree, text=False).stdout)
        untracked = self._run(
            ["ls-files", "--others", "--exclude-standard", "-z"],
            cwd=worktree,
            text=False,
        ).stdout.split(b"\0")
        for raw in sorted(item for item in untracked if item):
            digest.update(raw)
            digest.update((worktree / Path(os.fsdecode(raw))).read_bytes())
        return f"snapshot:{head}:{digest.hexdigest()}"

