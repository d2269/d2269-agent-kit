from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from controller.config import ProjectConfig
from controller.herdr import RunnerBlocked, RunnerError, RunnerTimeoutUncertain, RunnerUnknown
from controller.models import ExecutionContext, Receipt, Ticket, Waiver, utc_now
from controller.tracker import TrackerPreconditionError


STATUS = {
    "ready": "Ready",
    "in_development": "In Progress",
    "in_code_review": "In Review",
    "in_qa": "QA",
    "blocked": "Blocked",
    "human_review_required": "Needs Decision",
    "done": "Done",
}


class SimulatedProcessCrash(BaseException):
    pass


def config(
    root: Path,
    project_id: str = "project",
    rework_limit: int = 3,
    partial_policy: str = "stop",
    authorized_minimal_waivers: list[dict[str, str]] | None = None,
) -> ProjectConfig:
    repository = root / f"repo-{project_id}"
    repository.mkdir(parents=True, exist_ok=True)
    (repository / ".git").mkdir(exist_ok=True)
    config_path = repository / "controller.json"
    config_path.write_text("{}", encoding="utf-8")
    return ProjectConfig(
        path=config_path,
        project_id=project_id,
        repository=repository,
        state_root=root / "state",
        tracker={"kind": "linear", "status_mapping": STATUS},
        runner={"kind": "herdr", "agent_kind": "codex"},
        git={"base_branch": "main", "branch_prefix": "controller/"},
        policy={
            "rework_limit": rework_limit,
            "default_profile": "standard",
            "partial_policy": partial_policy,
            "authorized_minimal_waivers": authorized_minimal_waivers or [],
        },
    )


def ticket(
    ticket_id: str = "ABC-1",
    *,
    waiver: bool = False,
    delivery_profile: str | None = None,
) -> Ticket:
    revision = "ticket-r1"
    return Ticket(
        id=ticket_id,
        external_id=f"linear-{ticket_id}",
        title=f"Ticket {ticket_id}",
        description="Implementation readiness: READY",
        url=f"https://linear.example/{ticket_id}",
        revision=revision,
        tracker_marker="m0",
        state="Ready",
        semantic_readiness="READY",
        delivery_profile=delivery_profile,
        waiver=Waiver(
            ticket_revision=revision,
            implementation_revision="git:one",
            policy="test-policy",
            authorized_owner="owner",
            authoritative_source="ticket-contract",
        )
        if waiver
        else None,
    )


class FakeTracker:
    def __init__(self, tickets: list[Ticket]):
        self.tickets = {item.id: item for item in tickets}
        self.by_external = {item.external_id: item.id for item in tickets}
        self.comments: dict[str, Receipt] = {}
        self.transitions: dict[str, Receipt] = {}
        self.mutation_calls = 0
        self.read_calls = 0
        self.marker = 0
        self.receipt_valid = True

    def get_ticket(self, ticket_id: str) -> Ticket:
        self.read_calls += 1
        resolved = self.by_external.get(ticket_id, ticket_id)
        return self.tickets[resolved]

    def get_comments(self, ticket_id: str) -> list[dict[str, Any]]:
        self.read_calls += 1
        return []

    def publish_comment(self, ticket: Ticket, body: str, idempotency_key: str) -> Receipt:
        self.mutation_calls += 1
        current = self.get_ticket(ticket.external_id)
        if current.revision != ticket.revision or current.tracker_marker != ticket.tracker_marker:
            raise TrackerPreconditionError("ticket changed before comment publication")
        if idempotency_key not in self.comments:
            self.comments[idempotency_key] = Receipt(
                "comment", idempotency_key, f"comment-{len(self.comments) + 1}", True, {"body": body}
            )
        return self.comments[idempotency_key]

    def verify_comment_receipt(self, receipt: Receipt) -> bool:
        return self.receipt_valid and receipt.idempotency_key in self.comments

    def transition(
        self,
        ticket: Ticket,
        semantic_target: str,
        expected_semantic_state: str,
        idempotency_key: str,
    ) -> Receipt:
        self.mutation_calls += 1
        current = self.get_ticket(ticket.id)
        target = STATUS[semantic_target]
        expected = STATUS[expected_semantic_state]
        if current.state not in {expected, target}:
            raise TrackerPreconditionError(f"expected {expected}, observed {current.state}")
        if idempotency_key not in self.transitions:
            self.marker += 1
            updated = replace(current, state=target, tracker_marker=f"m{self.marker}")
            self.tickets[current.id] = updated
            self.transitions[idempotency_key] = Receipt(
                "transition", idempotency_key, current.external_id, True, {"from": expected, "to": target}
            )
        return self.transitions[idempotency_key]

    def verify_transition_receipt(self, receipt: Receipt) -> bool:
        if not self.receipt_valid:
            return False
        ticket_id = self.by_external[receipt.external_id]
        return self.tickets[ticket_id].state == receipt.payload["to"]

    def sync_plan(
        self,
        plan: dict[str, Any],
        existing_mappings: dict[str, dict[str, Any]],
        idempotency_prefix: str,
    ) -> tuple[list[Ticket], list[Receipt]]:
        self.mutation_calls += 1
        produced: list[Ticket] = []
        receipts: list[Receipt] = [
            Receipt(
                "plan-sync",
                f"{idempotency_prefix}:{plan['plan_id']}:{plan['revision']}",
                f"linear-plan-{plan['plan_id']}",
                True,
                {"local_id": plan["plan_id"], "revision": plan["revision"], "identifier": "PLAN"},
            )
        ]
        for index, item in enumerate(plan["tickets"], start=1):
            contract = item.get("contract", {})
            child = ticket(
                item.get("ticket_id", f"PLAN-{index}"),
                waiver=contract.get("delivery_profile") == "minimal",
                delivery_profile=contract.get("delivery_profile", "standard"),
            )
            self.tickets[child.id] = child
            self.by_external[child.external_id] = child.id
            produced.append(child)
            receipts.append(
                Receipt(
                    "plan-sync",
                    f"{idempotency_prefix}:{item['local_id']}:{plan['revision']}",
                    child.external_id,
                    True,
                    {"local_id": item["local_id"], "revision": plan["revision"], "identifier": child.id},
                )
            )
        return produced, receipts


class FakeWorktrees:
    def __init__(self, root: Path):
        self.root = root
        self.revisions: dict[Path, str] = {}
        self.developer_paths: dict[tuple[str, str], Path] = {}

    def developer_context(self, run_id: str, ticket_id: str) -> ExecutionContext:
        key = (run_id, ticket_id)
        path = self.developer_paths.setdefault(key, self.root / run_id / f"developer-{ticket_id}")
        path.mkdir(parents=True, exist_ok=True)
        self.revisions.setdefault(path, "git:base")
        return ExecutionContext(path, self.revisions[path])

    def review_context(
        self, run_id: str, invocation_id: str, source: Path, expected_revision: str
    ) -> ExecutionContext:
        path = self.root / run_id / invocation_id
        path.mkdir(parents=True, exist_ok=True)
        self.revisions[path] = expected_revision
        return ExecutionContext(path, expected_revision, source)

    def revision(self, path: Path) -> str:
        return self.revisions[path]


class FakeRunner:
    def __init__(self, specs: list[dict[str, Any]], worktrees: FakeWorktrees, tracker: FakeTracker):
        self.specs = list(specs)
        self.worktrees = worktrees
        self.tracker = tracker
        self.calls = 0

    def invoke(self, request: Any) -> None:
        self.calls += 1
        if not self.specs:
            raise AssertionError(f"unexpected invocation: {request.role} {request.mode}")
        spec = self.specs.pop(0)
        if spec.get("role") and spec["role"] != request.role:
            raise AssertionError(f"expected role {spec['role']}, got {request.role}")
        error = spec.get("error")
        if error == "blocked":
            raise RunnerBlocked("blocked")
        if error == "unknown":
            raise RunnerUnknown("unknown")
        if error == "timeout":
            raise RunnerTimeoutUncertain("timeout after possible prompt submission")
        if error == "crash":
            raise RunnerError("simulated runner crash")
        if error == "crash_before_result":
            raise SimulatedProcessCrash("simulated process exit before result persistence")
        implementation_revision = spec.get("implementation_revision", request.implementation_revision)
        if request.role == "developer" and implementation_revision:
            self.worktrees.revisions[request.context.path] = implementation_revision
        request.report_path.write_text("# Verified role report\n", encoding="utf-8")
        if not spec.get("omit_comment"):
            request.comment_path.write_text("Durable ticket history comment.\n", encoding="utf-8")
        payload_path = None
        if request.payload_path:
            payload = spec.get("payload", {"revision": "plan-r1", "tickets": []})
            request.payload_path.write_text(json.dumps(payload), encoding="utf-8")
            payload_path = str(request.payload_path)
        envelope = {
            "schema_version": "1",
            "run_id": request.run_id,
            "invocation_id": request.invocation_id,
            "project_id": request.project_id,
            "role": request.role,
            "mode": request.mode,
            "ticket_id": request.ticket.id if request.ticket else None,
            "ticket_revision": request.ticket.revision if request.ticket else None,
            "implementation_revision": implementation_revision,
            "result": spec["result"],
            "report_path": str(request.report_path),
            "comment_state": "READY_TO_POST",
            "comment_path": str(request.comment_path),
            "requested_action": spec["action"],
            "next_owner": spec.get("next_owner", "controller"),
            "created_at": utc_now(),
        }
        if payload_path:
            envelope["payload_path"] = payload_path
        request.envelope_path.write_text(json.dumps(envelope), encoding="utf-8")
        if spec.get("ticket_revision_after") and request.ticket:
            current = self.tracker.tickets[request.ticket.id]
            self.tracker.tickets[request.ticket.id] = replace(
                current, revision=spec["ticket_revision_after"]
            )
        if spec.get("implementation_revision_after") and request.context.source_path:
            self.worktrees.revisions[request.context.source_path] = spec["implementation_revision_after"]
        if spec.get("context_revision_after"):
            self.worktrees.revisions[request.context.path] = spec["context_revision_after"]
        if error == "crash_after_result":
            raise SimulatedProcessCrash("simulated process exit after result persistence")


def dev(revision: str = "git:one", result: str = "COMPLETE", **extra: Any) -> dict[str, Any]:
    action = {
        "COMPLETE": "SEND_TO_CODE_REVIEW",
        "PARTIAL": "STOP",
        "BLOCKED": "SEND_TO_BLOCKER_REVIEW",
    }[result]
    return {"role": "developer", "result": result, "action": action, "implementation_revision": revision, **extra}


def review(result: str = "PASS", **extra: Any) -> dict[str, Any]:
    action = {"PASS": "ADVANCE_TO_QA", "CHANGES_REQUESTED": "RETURN_TO_DEVELOPER", "BLOCKED": "RESOLVE_BLOCKER"}[result]
    return {"role": "code-review", "result": result, "action": action, **extra}


def qa(result: str = "PASS", **extra: Any) -> dict[str, Any]:
    action = {"PASS": "MARK_DONE", "CHANGES_REQUESTED": "RETURN_TO_DEVELOPER", "BLOCKED": "RESOLVE_BLOCKER"}[result]
    return {"role": "qa", "result": result, "action": action, **extra}


def blocker() -> dict[str, Any]:
    return {"role": "tech-lead", "result": "HUMAN_REVIEW_REQUIRED", "action": "REQUEST_HUMAN_DECISION"}


def plan(payload: dict[str, Any]) -> dict[str, Any]:
    return {"role": "tech-lead", "result": "PLAN_READY", "action": "PUBLISH_PLAN", "payload": payload}


def completeness(action: str = "REQUEST_HUMAN_CLOSE_OUT") -> dict[str, Any]:
    return {"role": "tech-lead", "result": "TECHNICALLY_COMPLETE", "action": action}


def design() -> dict[str, Any]:
    return {"role": "architect", "result": "DESIGN_READY", "action": "REQUEST_ARCHITECTURE_ACCEPTANCE"}


def conformance() -> dict[str, Any]:
    return {"role": "architect", "result": "ALIGNED", "action": "REQUEST_HUMAN_CLOSE_OUT"}
