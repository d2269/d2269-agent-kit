"""Project configuration loading and validation."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import PROFILES


PROJECT_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
REQUIRED_STATES = {
    "ready",
    "in_development",
    "in_code_review",
    "in_qa",
    "blocked",
    "human_review_required",
    "done",
}


@dataclass(frozen=True)
class ProjectConfig:
    path: Path
    project_id: str
    repository: Path
    state_root: Path
    tracker: dict[str, Any]
    runner: dict[str, Any]
    git: dict[str, Any]
    policy: dict[str, Any]

    @property
    def status_mapping(self) -> dict[str, str]:
        return dict(self.tracker["status_mapping"])

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": "1",
            "project_id": self.project_id,
            "repository": str(self.repository),
            "tracker": {key: value for key, value in self.tracker.items() if key != "token"},
            "runner": self.runner,
            "git": self.git,
            "policy": self.policy,
        }


def _resolve(base: Path, raw: str) -> Path:
    candidate = Path(raw).expanduser()
    return (base / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()


def load_config(project: Path) -> ProjectConfig:
    project = project.expanduser().resolve()
    config_path = project if project.is_file() else project / "controller.json"
    if not config_path.is_file():
        raise ValueError(f"missing controller project configuration: {config_path}")
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read controller configuration: {exc}") from exc
    if raw.get("schema_version") != "1":
        raise ValueError("controller configuration schema_version must be '1'")
    project_id = raw.get("project_id")
    if not isinstance(project_id, str) or not PROJECT_ID_RE.fullmatch(project_id):
        raise ValueError("project_id must match [a-z][a-z0-9_-]{0,63}")
    base = config_path.parent
    repository = _resolve(base, raw.get("repository", "."))
    if not (repository / ".git").exists():
        raise ValueError(f"repository is not a Git checkout: {repository}")
    state_env = os.environ.get("D2269_CONTROLLER_STATE_ROOT")
    state_raw = state_env or raw.get("state_root")
    if not state_raw:
        raise ValueError(
            "state_root is required in controller.json or D2269_CONTROLLER_STATE_ROOT"
        )
    state_root = _resolve(base, state_raw)
    tracker = raw.get("tracker")
    runner = raw.get("runner")
    git = raw.get("git", {})
    policy = raw.get("policy", {})
    if not isinstance(tracker, dict) or tracker.get("kind") != "linear":
        raise ValueError("tracker.kind must be 'linear'")
    if "token" in tracker:
        raise ValueError("tracker credentials must use token_env, not an inline token")
    for key in ("team_id", "token_env"):
        if not isinstance(tracker.get(key), str) or not tracker[key].strip():
            raise ValueError(f"tracker.{key} must be a non-empty string")
    if "endpoint" in tracker and (
        not isinstance(tracker["endpoint"], str)
        or not tracker["endpoint"].startswith("https://")
    ):
        raise ValueError("tracker.endpoint must be an HTTPS URL")
    mapping = tracker.get("status_mapping")
    if not isinstance(mapping, dict) or REQUIRED_STATES - set(mapping):
        missing = sorted(REQUIRED_STATES - set(mapping or {}))
        raise ValueError("status_mapping missing semantic states: " + ", ".join(missing))
    if any(not isinstance(mapping[key], str) or not mapping[key].strip() for key in REQUIRED_STATES):
        raise ValueError("every status_mapping value must be a non-empty string")
    if not isinstance(runner, dict) or runner.get("kind") != "herdr":
        raise ValueError("runner.kind must be 'herdr'")
    if runner.get("agent_kind") not in {"codex", "claude", "cursor"}:
        raise ValueError("runner.agent_kind must be codex, claude, or cursor")
    agent_args = runner.get("agent_args", [])
    if not isinstance(agent_args, list) or any(not isinstance(item, str) for item in agent_args):
        raise ValueError("runner.agent_args must be an array of strings")
    timeout_ms = runner.get("timeout_ms", 1_800_000)
    if not isinstance(timeout_ms, int) or timeout_ms < 1:
        raise ValueError("runner.timeout_ms must be a positive integer")
    rework_limit = policy.get("rework_limit", 3)
    if not isinstance(rework_limit, int) or rework_limit < 1:
        raise ValueError("policy.rework_limit must be a positive integer")
    default_profile = policy.get("default_profile", "standard")
    if default_profile not in PROFILES:
        raise ValueError("policy.default_profile is invalid")
    partial_policy = policy.get("partial_policy", "stop")
    if partial_policy not in {"stop", "continue"}:
        raise ValueError("policy.partial_policy must be 'stop' or 'continue'")
    waiver_authorities = policy.get("authorized_minimal_waivers", [])
    if not isinstance(waiver_authorities, list):
        raise ValueError("policy.authorized_minimal_waivers must be an array")
    normalized_waivers: list[dict[str, str]] = []
    waiver_fields = ("policy", "authorized_owner", "authoritative_source")
    for authority in waiver_authorities:
        if not isinstance(authority, dict) or any(
            not isinstance(authority.get(key), str) or not authority[key]
            for key in waiver_fields
        ):
            raise ValueError(
                "each authorized_minimal_waivers entry requires policy, "
                "authorized_owner, and authoritative_source"
            )
        normalized_waivers.append({key: authority[key] for key in waiver_fields})
    normalized_policy = {
        "rework_limit": rework_limit,
        "default_profile": default_profile,
        "partial_policy": partial_policy,
        "authorized_minimal_waivers": normalized_waivers,
    }
    normalized_git = {
        "base_branch": git.get("base_branch", "main"),
        "branch_prefix": git.get("branch_prefix", "controller/"),
    }
    if any(not isinstance(value, str) or not value for value in normalized_git.values()):
        raise ValueError("git.base_branch and git.branch_prefix must be non-empty strings")
    return ProjectConfig(
        path=config_path,
        project_id=project_id,
        repository=repository,
        state_root=state_root,
        tracker=tracker,
        runner=runner,
        git=normalized_git,
        policy=normalized_policy,
    )
