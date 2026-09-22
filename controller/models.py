"""Small shared data contracts for the lifecycle controller."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROFILES = ("minimal", "standard", "planned", "consequential")
ROLE_SKILL_NAMES = {
    "architect": "d2269-architect",
    "tech-lead": "d2269-tech-lead",
    "developer": "d2269-developer",
    "code-review": "d2269-code-review",
    "qa": "d2269-qa",
    "researcher": "d2269-researcher",
    "technical-documentation": "d2269-technical-documentation",
    "orchestrator": "d2269-orchestrator",
}
ROLE_RESULTS = {
    ("developer", None): {"COMPLETE", "PARTIAL", "BLOCKED"},
    ("code-review", None): {"PASS", "CHANGES_REQUESTED", "BLOCKED"},
    ("qa", None): {"PASS", "CHANGES_REQUESTED", "BLOCKED"},
    ("tech-lead", "PLAN"): {"PLAN_READY", "DRAFT", "BLOCKED"},
    ("tech-lead", "BLOCKER_REVIEW"): {"HUMAN_REVIEW_REQUIRED"},
    ("tech-lead", "COMPLETENESS_REVIEW"): {
        "TECHNICALLY_COMPLETE",
        "CHANGES_REQUIRED",
        "NOT_VERIFIABLE",
    },
    ("architect", "DESIGN"): {"DESIGN_READY", "BLOCKED"},
    ("architect", "ESCALATION_REVIEW"): {
        "RESOLVED",
        "CHANGE_REQUIRED",
        "NOT_VERIFIABLE",
    },
    ("architect", "CONFORMANCE_REVIEW"): {
        "ALIGNED",
        "ALIGNED_WITH_DEVIATIONS",
        "NOT_ALIGNED",
        "NOT_VERIFIABLE",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class Waiver:
    ticket_revision: str
    implementation_revision: str | None
    policy: str
    authorized_owner: str
    authoritative_source: str


@dataclass(frozen=True)
class Ticket:
    id: str
    external_id: str
    title: str
    description: str
    url: str
    revision: str
    tracker_marker: str
    state: str
    semantic_readiness: str | None
    delivery_profile: str | None = None
    links: tuple[str, ...] = ()
    waiver: Waiver | None = None


@dataclass(frozen=True)
class Receipt:
    kind: str
    idempotency_key: str
    external_id: str
    verified: bool
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionContext:
    path: Path
    implementation_revision: str | None
    source_path: Path | None = None


@dataclass(frozen=True)
class InvocationRequest:
    run_id: str
    invocation_id: str
    project_id: str
    role: str
    mode: str | None
    ticket: Ticket | None
    implementation_revision: str | None
    context: ExecutionContext
    report_path: Path
    comment_path: Path
    envelope_path: Path
    payload_path: Path | None
    extra_context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResultEnvelope:
    schema_version: str
    run_id: str
    invocation_id: str
    project_id: str
    role: str
    mode: str | None
    ticket_id: str | None
    ticket_revision: str | None
    implementation_revision: str | None
    result: str
    report_path: str
    comment_state: str
    comment_path: str
    requested_action: str
    next_owner: str
    created_at: str
    payload_path: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ResultEnvelope":
        required = {
            "schema_version",
            "run_id",
            "invocation_id",
            "project_id",
            "role",
            "mode",
            "ticket_id",
            "ticket_revision",
            "implementation_revision",
            "result",
            "report_path",
            "comment_state",
            "comment_path",
            "requested_action",
            "next_owner",
            "created_at",
        }
        missing = sorted(required - value.keys())
        if missing:
            raise ValueError("result envelope missing fields: " + ", ".join(missing))
        extra = sorted(set(value) - required - {"payload_path"})
        if extra:
            raise ValueError("result envelope has unsupported fields: " + ", ".join(extra))
        string_fields = {
            "schema_version",
            "run_id",
            "invocation_id",
            "project_id",
            "role",
            "result",
            "report_path",
            "comment_state",
            "comment_path",
            "requested_action",
            "next_owner",
            "created_at",
        }
        for key in string_fields:
            if not isinstance(value.get(key), str) or not value[key]:
                raise ValueError(f"result envelope {key} must be a non-empty string")
        for key in {"mode", "ticket_id", "ticket_revision", "implementation_revision", "payload_path"}:
            if value.get(key) is not None and not isinstance(value[key], str):
                raise ValueError(f"result envelope {key} must be a string or null")
        return cls(**value)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
