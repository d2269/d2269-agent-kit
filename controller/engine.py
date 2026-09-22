"""Shared deterministic workflow engine for all delivery profiles."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import uuid
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import ProjectConfig
from .herdr import RunnerBlocked, RunnerError, RunnerTimeoutUncertain, RunnerUnknown
from .models import (
    PROFILES,
    ROLE_RESULTS,
    ExecutionContext,
    InvocationRequest,
    Receipt,
    ResultEnvelope,
    Ticket,
)
from .state import StateStore
from .tracker import TrackerError, TrackerPort


ACTION_RULES = {
    ("developer", None, "COMPLETE"): {"SEND_TO_CODE_REVIEW", "SEND_TO_QA"},
    ("developer", None, "PARTIAL"): {"CONTINUE_DEVELOPER", "STOP"},
    ("developer", None, "BLOCKED"): {"SEND_TO_BLOCKER_REVIEW"},
    ("code-review", None, "PASS"): {"ADVANCE_TO_QA"},
    ("code-review", None, "CHANGES_REQUESTED"): {"RETURN_TO_DEVELOPER"},
    ("code-review", None, "BLOCKED"): {"RESOLVE_BLOCKER"},
    ("qa", None, "PASS"): {"ADVANCE_PER_POLICY", "MARK_DONE"},
    ("qa", None, "CHANGES_REQUESTED"): {"RETURN_TO_DEVELOPER"},
    ("qa", None, "BLOCKED"): {"RESOLVE_BLOCKER"},
    ("tech-lead", "PLAN", "PLAN_READY"): {"PUBLISH_PLAN"},
    ("tech-lead", "PLAN", "DRAFT"): {"RESOLVE_BLOCKER"},
    ("tech-lead", "PLAN", "BLOCKED"): {"RESOLVE_BLOCKER"},
    ("tech-lead", "BLOCKER_REVIEW", "HUMAN_REVIEW_REQUIRED"): {
        "REQUEST_HUMAN_DECISION"
    },
    ("tech-lead", "COMPLETENESS_REVIEW", "TECHNICALLY_COMPLETE"): {
        "SEND_TO_CONFORMANCE",
        "REQUEST_HUMAN_CLOSE_OUT",
    },
    ("tech-lead", "COMPLETENESS_REVIEW", "CHANGES_REQUIRED"): {"RESOLVE_BLOCKER"},
    ("tech-lead", "COMPLETENESS_REVIEW", "NOT_VERIFIABLE"): {"RESOLVE_BLOCKER"},
    ("architect", "DESIGN", "DESIGN_READY"): {"REQUEST_ARCHITECTURE_ACCEPTANCE"},
    ("architect", "DESIGN", "BLOCKED"): {"RESOLVE_BLOCKER"},
    ("architect", "ESCALATION_REVIEW", "RESOLVED"): {"REQUEST_HUMAN_DECISION"},
    ("architect", "ESCALATION_REVIEW", "CHANGE_REQUIRED"): {"REQUEST_HUMAN_DECISION"},
    ("architect", "ESCALATION_REVIEW", "NOT_VERIFIABLE"): {"REQUEST_HUMAN_DECISION"},
    ("architect", "CONFORMANCE_REVIEW", "ALIGNED"): {"REQUEST_HUMAN_CLOSE_OUT"},
    ("architect", "CONFORMANCE_REVIEW", "ALIGNED_WITH_DEVIATIONS"): {
        "REQUEST_HUMAN_CLOSE_OUT"
    },
    ("architect", "CONFORMANCE_REVIEW", "NOT_ALIGNED"): {"RESOLVE_BLOCKER"},
    ("architect", "CONFORMANCE_REVIEW", "NOT_VERIFIABLE"): {"RESOLVE_BLOCKER"},
}


class SafeStop(RuntimeError):
    def __init__(self, state: str, message: str):
        super().__init__(message)
        self.state = state


class LifecycleController:
    def __init__(
        self,
        config: ProjectConfig,
        store: StateStore,
        tracker: TrackerPort,
        runner: Any,
        worktrees: Any,
        *,
        mutations_authorized: bool,
    ):
        self.config = config
        self.store = store
        self.tracker = tracker
        self.runner = runner
        self.worktrees = worktrees
        self.mutations_authorized = mutations_authorized

    @staticmethod
    def _id(prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex}"

    def dry_run(self, profile: str, *, ticket_id: str | None, scope_path: Path | None) -> dict[str, Any]:
        if profile not in PROFILES:
            raise ValueError(f"unsupported profile: {profile}")
        if profile in {"minimal", "standard"}:
            if not ticket_id or scope_path:
                raise ValueError(f"{profile} requires exactly one --ticket")
            ticket = self.tracker.get_ticket(ticket_id)
            self._ticket_start_gate(ticket, profile)
            roles = ["developer", "qa"] if profile == "minimal" else ["developer", "code-review", "qa"]
            mutations = ["comment after each role", "status: in_development", "status gates", "status: done"]
            worktrees = ["developer writable", *[f"{role} fresh exact-revision" for role in roles[1:]]]
            gates = ["rework-limit blocker review", "human decision after blocker review"]
        else:
            if not scope_path or ticket_id:
                raise ValueError(f"{profile} requires exactly one --scope")
            if not scope_path.expanduser().resolve().is_file():
                raise ValueError(f"scope file does not exist: {scope_path}")
            roles = []
            if profile == "consequential":
                roles.append("architect DESIGN")
            roles += ["tech-lead PLAN", "per-ticket minimal/standard delivery", "tech-lead COMPLETENESS_REVIEW"]
            if profile == "consequential":
                roles.append("architect CONFORMANCE_REVIEW")
            mutations = ["publish/sync validated child tickets", "per-ticket comments and status transitions"]
            worktrees = ["fresh role context for every invocation", "developer writable per ticket", "review/QA exact-revision"]
            gates = ["architecture acceptance" if profile == "consequential" else "none before planning", "human scope close-out", "blocker decisions"]
        return {
            "dry_run": True,
            "profile": profile,
            "target": ticket_id or str(scope_path),
            "planned_role_invocations": roles,
            "tracker_mutations": mutations,
            "worktrees": worktrees,
            "human_gates": gates,
        }

    def start(
        self,
        profile: str,
        *,
        ticket_id: str | None = None,
        scope_path: Path | None = None,
    ) -> str:
        if not self.mutations_authorized:
            raise ValueError("non-dry runs require explicit external mutation authorization")
        if profile not in PROFILES:
            raise ValueError(f"unsupported profile: {profile}")
        with self.store.lock():
            if profile in {"minimal", "standard"}:
                if not ticket_id or scope_path:
                    raise ValueError(f"{profile} requires exactly one ticket")
                target_kind, target_ref = "ticket", ticket_id
                active = self.store.find_active(target_kind, target_ref)
                if active:
                    if self.store.get_run(active)["profile"] != profile:
                        raise ValueError("the active target run uses a different profile")
                    return self._resume_locked(active)
                ticket = self.tracker.get_ticket(ticket_id)
                self._ticket_start_gate(ticket, profile)
                data = {
                    "stage": "ticket",
                    "ticket_stage": "developer",
                    "ticket_queue": [ticket.id],
                    "ticket_index": 0,
                    "tickets": {ticket.id: self._ticket_data(ticket)},
                    "started_tickets": [],
                    "implementation_revision": None,
                    "review_pass_revision": None,
                    "qa_pass_revision": None,
                }
            else:
                if not scope_path or ticket_id:
                    raise ValueError(f"{profile} requires exactly one scope file")
                scope_path = scope_path.expanduser().resolve()
                target_kind, target_ref = "scope", str(scope_path)
                active = self.store.find_active(target_kind, target_ref)
                if active:
                    if self.store.get_run(active)["profile"] != profile:
                        raise ValueError("the active target run uses a different profile")
                    return self._resume_locked(active)
                scope = scope_path.read_text(encoding="utf-8")
                data = {
                    "stage": "architect_design" if profile == "consequential" else "plan",
                    "scope_path": str(scope_path),
                    "scope": scope,
                    "ticket_queue": [],
                    "ticket_index": 0,
                    "tickets": {},
                    "started_tickets": [],
                }
            run_id = self._id("run")
            self.store.create_run(
                run_id=run_id,
                project_path=str(self.config.path),
                profile=profile,
                target_kind=target_kind,
                target_ref=target_ref,
                policy={**self.config.snapshot(), "mutations_authorized": True},
                data=data,
            )
            return self._resume_locked(run_id)

    def resume(self, run_id: str) -> str:
        with self.store.lock():
            return self._resume_locked(run_id)

    def _resume_locked(self, run_id: str) -> str:
        run = self.store.get_run(run_id)
        expected_policy = {**self.config.snapshot(), "mutations_authorized": True}
        if run["policy"] != expected_policy:
            self.store.record_error(
                run_id,
                None,
                "CONFIG_CHANGED",
                "current project configuration differs from the immutable run snapshot",
            )
            data = run["data"]
            data["human_gate"] = "safe_stop_resolution"
            data["stop_reason"] = "CONFIG_CHANGED"
            self.store.update_run(run_id, lifecycle_state="CONFIG_CHANGED", data=data)
            return run_id
        if run["lifecycle_state"] == "HUMAN_REVIEW_REQUIRED":
            raise SafeStop("HUMAN_REVIEW_REQUIRED", "a recorded human decision is required")
        if run["lifecycle_state"] != "RUNNING":
            return run_id
        try:
            self._drive(run_id)
        except SafeStop as exc:
            self.store.record_error(run_id, None, exc.state, str(exc))
            if exc.state in {"HERDR_TIMEOUT_UNCERTAIN", "INVOCATION_UNCERTAIN"}:
                data = self.store.get_run(run_id)["data"]
                data["human_gate"] = "prompt_delivery_uncertain"
                data["stop_reason"] = exc.state
                self.store.update_run(
                    run_id, lifecycle_state="HUMAN_REVIEW_REQUIRED", data=data
                )
            elif exc.state == "RECEIPT_MISMATCH":
                data = self.store.get_run(run_id)["data"]
                data["human_gate"] = "external_mutation_recovery"
                data["stop_reason"] = exc.state
                self.store.update_run(run_id, lifecycle_state=exc.state, data=data)
            else:
                data = self.store.get_run(run_id)["data"]
                data["human_gate"] = "safe_stop_resolution"
                data["stop_reason"] = exc.state
                self.store.update_run(run_id, lifecycle_state=exc.state, data=data)
        except TrackerError as exc:
            self.store.record_error(run_id, None, type(exc).__name__, str(exc))
            data = self.store.get_run(run_id)["data"]
            data["human_gate"] = "external_mutation_recovery"
            data["stop_reason"] = type(exc).__name__
            self.store.update_run(run_id, lifecycle_state="SAFE_STOP", data=data)
        except (RunnerError, ValueError, OSError) as exc:
            self.store.record_error(run_id, None, type(exc).__name__, str(exc))
            data = self.store.get_run(run_id)["data"]
            data["human_gate"] = "safe_stop_resolution"
            data["stop_reason"] = type(exc).__name__
            self.store.update_run(run_id, lifecycle_state="SAFE_STOP", data=data)
        return run_id

    def decide(self, run_id: str, decision: dict[str, Any]) -> str:
        with self.store.lock():
            run = self.store.get_run(run_id)
            action = decision.get("action")
            if (
                run["policy"]
                != {**self.config.snapshot(), "mutations_authorized": True}
                and action != "STOP"
            ):
                raise ValueError("current project configuration differs from the immutable run snapshot")
            if not run["data"].get("human_gate"):
                raise ValueError("run is not waiting at a human decision gate")
            data = run["data"]
            gate = data.get("human_gate")
            allowed = {
                "architecture_acceptance": {"ACCEPT_ARCHITECTURE", "REJECT_ARCHITECTURE", "STOP"},
                "blocker_review": {"RESUME_DEVELOPER", "REPLAN", "INVOKE_ARCHITECT", "STOP"},
                "scope_closeout": {"CLOSE_SCOPE", "REPLAN", "STOP"},
                "prompt_delivery_uncertain": {"CONFIRM_PROMPT_NOT_ACCEPTED_RETRY", "STOP"},
                "safe_stop_resolution": {"RETRY_ROLE", "STOP"},
                "external_mutation_recovery": {"RETRY_MUTATION", "STOP"},
            }.get(gate, set())
            if gate == "blocker_review" and run["profile"] in {"minimal", "standard"}:
                allowed.discard("REPLAN")
            if gate == "scope_closeout" and run["profile"] not in {
                "planned",
                "consequential",
            }:
                allowed.discard("REPLAN")
            if action not in allowed:
                raise ValueError(f"decision {action!r} is not permitted for gate {gate!r}")
            self.store.record_decision(run_id, gate, decision)
            data.pop("human_gate", None)
            if action == "ACCEPT_ARCHITECTURE":
                data["stage"] = "plan"
            elif action == "RESUME_DEVELOPER":
                data["stage"] = "ticket"
                data["ticket_stage"] = "developer"
            elif action == "REPLAN":
                data["stage"] = "plan"
                data["retry_generation"] = int(data.get("retry_generation", 0)) + 1
            elif action == "INVOKE_ARCHITECT":
                data["stage"] = "architect_escalation"
            elif action == "CLOSE_SCOPE":
                self.store.update_run(run_id, lifecycle_state="COMPLETED", data=data)
                return run_id
            elif action == "CONFIRM_PROMPT_NOT_ACCEPTED_RETRY":
                self.store.abandon_pending_invocations(run_id)
                data["retry_generation"] = int(data.get("retry_generation", 0)) + 1
                data.pop("stop_reason", None)
            elif action == "RETRY_ROLE":
                data["retry_generation"] = int(data.get("retry_generation", 0)) + 1
                data.pop("stop_reason", None)
            elif action == "RETRY_MUTATION":
                data.pop("stop_reason", None)
            else:
                self.store.update_run(run_id, lifecycle_state="STOPPED", data=data)
                return run_id
            self.store.update_run(run_id, lifecycle_state="RUNNING", data=data)
        return self.resume(run_id)

    @staticmethod
    def _ticket_data(ticket: Ticket) -> dict[str, Any]:
        return {
            "id": ticket.id,
            "revision": ticket.revision,
            "state": ticket.state,
            "tracker_marker": ticket.tracker_marker,
        }

    def _ticket_start_gate(self, ticket: Ticket, profile: str) -> None:
        if ticket.semantic_readiness != "READY":
            raise ValueError(f"ticket {ticket.id} implementation_readiness is not READY")
        if ticket.state != self.config.status_mapping["ready"]:
            raise ValueError(f"ticket {ticket.id} is not in configured ready state")
        if profile == "minimal":
            waiver = ticket.waiver
            if not waiver or waiver.ticket_revision != ticket.revision:
                raise ValueError("minimal profile requires a current ticket-revision-bound Code Review waiver")
            if not waiver.implementation_revision:
                raise ValueError("minimal profile waiver must name the exact implementation revision")
            if not all((waiver.policy, waiver.authorized_owner, waiver.authoritative_source)):
                raise ValueError("minimal profile waiver lacks policy, owner, or authoritative source")
            authority = {
                "policy": waiver.policy,
                "authorized_owner": waiver.authorized_owner,
                "authoritative_source": waiver.authoritative_source,
            }
            if authority not in self.config.policy["authorized_minimal_waivers"]:
                raise ValueError("minimal profile waiver authority is not configured")

    def _drive(self, run_id: str) -> None:
        while True:
            run = self.store.get_run(run_id)
            if run["lifecycle_state"] != "RUNNING":
                return
            data, profile = run["data"], run["profile"]
            stage = data["stage"]
            if stage == "architect_design":
                envelope = self._invoke_scope(run_id, "architect", "DESIGN", data)
                if envelope.result != "DESIGN_READY":
                    raise SafeStop("BLOCKED", "Architect DESIGN did not produce a ready design")
                data["human_gate"] = "architecture_acceptance"
                self.store.update_run(run_id, lifecycle_state="HUMAN_REVIEW_REQUIRED", data=data)
                return
            if stage == "architect_escalation":
                self._invoke_scope(run_id, "architect", "ESCALATION_REVIEW", data)
                data["human_gate"] = "blocker_review"
                self.store.update_run(run_id, lifecycle_state="HUMAN_REVIEW_REQUIRED", data=data)
                return
            if stage == "plan":
                envelope = self._invoke_scope(run_id, "tech-lead", "PLAN", data, payload=True)
                if envelope.result != "PLAN_READY" or not envelope.payload_path:
                    raise SafeStop("BLOCKED", "Tech Lead PLAN is not ready for publication")
                plan = self._load_plan(Path(envelope.payload_path))
                existing = {
                    item_id: mapping
                    for item_id in [plan.get("plan_id"), *[item["local_id"] for item in plan.get("tickets", [])]]
                    if item_id
                    if (mapping := self.store.get_mapping(item_id))
                }
                tickets, receipts = self.tracker.sync_plan(
                    plan, existing, f"{run_id}:plan:{plan.get('revision')}"
                )
                for receipt in receipts:
                    self.store.save_receipt(run_id, receipt)
                    local_id = receipt.payload["local_id"]
                    self.store.save_mapping(local_id, receipt.external_id, receipt.payload["revision"], receipt.payload)
                if not tickets:
                    raise SafeStop("BLOCKED", "validated plan contains no child tickets")
                data["ticket_queue"] = [ticket.id for ticket in tickets]
                data["tickets"] = {ticket.id: self._ticket_data(ticket) for ticket in tickets}
                data["ticket_index"] = 0
                data["started_tickets"] = []
                data["stage"] = "ticket"
                data["ticket_stage"] = "developer"
                data["implementation_revision"] = None
                data["review_pass_revision"] = None
                data["qa_pass_revision"] = None
                self.store.update_run(run_id, data=data)
                continue
            if stage == "ticket":
                if data["ticket_index"] >= len(data["ticket_queue"]):
                    data["stage"] = "completeness" if profile in {"planned", "consequential"} else "complete"
                    self.store.update_run(run_id, data=data)
                    continue
                self._drive_ticket(run_id, run)
                continue
            if stage == "completeness":
                envelope = self._invoke_scope(run_id, "tech-lead", "COMPLETENESS_REVIEW", data)
                if envelope.result != "TECHNICALLY_COMPLETE":
                    raise SafeStop("BLOCKED", "scope is not technically complete")
                expected_action = (
                    "SEND_TO_CONFORMANCE"
                    if profile == "consequential"
                    else "REQUEST_HUMAN_CLOSE_OUT"
                )
                if envelope.requested_action != expected_action:
                    raise SafeStop(
                        "MISMATCHED_RESULT",
                        "Tech Lead completeness action does not match the selected profile",
                    )
                data["stage"] = "conformance" if profile == "consequential" else "human_closeout"
                self.store.update_run(run_id, data=data)
                continue
            if stage == "conformance":
                envelope = self._invoke_scope(run_id, "architect", "CONFORMANCE_REVIEW", data)
                if envelope.result not in {"ALIGNED", "ALIGNED_WITH_DEVIATIONS"}:
                    raise SafeStop("BLOCKED", "architecture conformance did not pass")
                data["stage"] = "human_closeout"
                self.store.update_run(run_id, data=data)
                continue
            if stage == "human_closeout":
                data["human_gate"] = "scope_closeout"
                self.store.update_run(run_id, lifecycle_state="HUMAN_REVIEW_REQUIRED", data=data)
                return
            if stage == "complete":
                self.store.update_run(run_id, lifecycle_state="COMPLETED", data=data)
                return
            raise SafeStop("SAFE_STOP", f"unknown lifecycle stage: {stage}")

    def _current_ticket(self, data: dict[str, Any]) -> Ticket:
        ticket_id = data["ticket_queue"][data["ticket_index"]]
        ticket = self.tracker.get_ticket(ticket_id)
        expected = data["tickets"][ticket_id]["revision"]
        if ticket.revision != expected:
            raise SafeStop("STALE_TICKET_REVISION", f"ticket {ticket_id} revision changed")
        return ticket

    def _drive_ticket(self, run_id: str, run: dict[str, Any]) -> None:
        data, profile = run["data"], run["profile"]
        ticket = self._current_ticket(data)
        ticket_profile = profile if profile in {"minimal", "standard"} else (ticket.delivery_profile or "standard")
        if ticket_profile not in {"minimal", "standard"}:
            raise SafeStop("INVALID_TICKET_PROFILE", f"ticket {ticket.id} has invalid delivery_profile")
        if ticket.id not in data.setdefault("started_tickets", []):
            self._ticket_start_gate(ticket, ticket_profile)
            data["started_tickets"].append(ticket.id)
            self.store.update_run(run_id, data=data)
        if ticket_profile == "minimal":
            waiver = ticket.waiver
            if not waiver or waiver.ticket_revision != ticket.revision:
                raise SafeStop("WAIVER_MISMATCH", "minimal ticket no longer has a current waiver")
        stage = data["ticket_stage"]
        developer = self.worktrees.developer_context(run_id, ticket.id)
        if stage == "developer":
            attempt = self.store.rework_count(run_id, ticket.id, ticket.revision)
            self._transition(
                run_id,
                ticket,
                "in_development",
                self._semantic_state(ticket.state),
                f"enter-development-{attempt}",
            )
            ticket = self.tracker.get_ticket(ticket.id)
            envelope = self._invoke(run_id, "developer", None, ticket, developer, None, data)
            if envelope.result == "PARTIAL":
                expected_action = (
                    "CONTINUE_DEVELOPER"
                    if self.config.policy["partial_policy"] == "continue"
                    else "STOP"
                )
                if envelope.requested_action != expected_action:
                    raise SafeStop(
                        "MISMATCHED_RESULT",
                        "Developer PARTIAL action does not match project policy",
                    )
                if self.config.policy["partial_policy"] == "continue":
                    data["partial_generation"] = int(data.get("partial_generation", 0)) + 1
                    self.store.update_run(run_id, data=data)
                    return
                raise SafeStop("PARTIAL", "Developer returned PARTIAL")
            if envelope.result == "BLOCKED":
                self._transition(
                    run_id,
                    ticket,
                    "blocked",
                    self._semantic_state(ticket.state),
                    f"developer-blocked-{attempt}",
                )
                data["blocked_next_owner"] = envelope.next_owner
                data["ticket_stage"] = "blocker_review"
                self.store.update_run(run_id, data=data)
                return
            expected_complete_action = (
                "SEND_TO_QA" if ticket_profile == "minimal" else "SEND_TO_CODE_REVIEW"
            )
            if envelope.requested_action != expected_complete_action:
                raise SafeStop(
                    "MISMATCHED_RESULT",
                    "Developer COMPLETE action does not match the ticket delivery profile",
                )
            actual = self.worktrees.revision(developer.path)
            if envelope.implementation_revision != actual:
                raise SafeStop("REVISION_MISMATCH", "Developer envelope does not match the exact implementation revision")
            data["implementation_revision"] = actual
            data["review_pass_revision"] = None
            data["qa_pass_revision"] = None
            if ticket_profile == "minimal":
                waiver = ticket.waiver
                if not waiver or (
                    waiver.implementation_revision != actual
                ):
                    raise SafeStop("WAIVER_MISMATCH", "Code Review waiver does not apply to the Developer result")
                data["waiver_bound_revision"] = waiver.implementation_revision
                data["ticket_stage"] = "qa"
                self._transition(
                    run_id, ticket, "in_qa", "in_development", f"developer-to-qa-{attempt}"
                )
            else:
                data["ticket_stage"] = "code_review"
                self._transition(
                    run_id,
                    ticket,
                    "in_code_review",
                    "in_development",
                    f"developer-to-review-{attempt}",
                )
            self.store.update_run(run_id, data=data)
            return
        expected_revision = data.get("implementation_revision")
        if stage == "code_review":
            if self.worktrees.revision(developer.path) != expected_revision:
                raise SafeStop("IMPLEMENTATION_CHANGED", "implementation changed after the prior gate")
            invocation_id, _logical_key = self._invocation_identity(
                run_id, "code-review", None, ticket, data
            )
            context = self.worktrees.review_context(run_id, invocation_id, developer.path, expected_revision)
            envelope = self._invoke(
                run_id, "code-review", None, ticket, context, expected_revision, data, invocation_id=invocation_id
            )
            if self.worktrees.revision(developer.path) != expected_revision:
                raise SafeStop("IMPLEMENTATION_CHANGED", "implementation changed during Code Review")
            if self.worktrees.revision(context.path) != expected_revision:
                raise SafeStop("REVIEW_CONTEXT_CHANGED", "Code Review context changed during evaluation")
            if envelope.result == "BLOCKED":
                self._transition(
                    run_id,
                    ticket,
                    "blocked",
                    self._semantic_state(ticket.state),
                    f"review-blocked-{self.store.rework_count(run_id, ticket.id, ticket.revision)}",
                )
                data["blocked_next_owner"] = envelope.next_owner
                self.store.update_run(run_id, data=data)
                raise SafeStop(
                    "BLOCKED", f"Code Review requires owner {envelope.next_owner}"
                )
            if envelope.result == "CHANGES_REQUESTED":
                self._rework_or_block(run_id, data, ticket, "code-review", envelope.invocation_id)
                return
            data["review_pass_revision"] = expected_revision
            data["ticket_stage"] = "qa"
            attempt = self.store.rework_count(run_id, ticket.id, ticket.revision)
            self._transition(
                run_id, ticket, "in_qa", "in_code_review", f"review-to-qa-{attempt}"
            )
            self.store.update_run(run_id, data=data)
            return
        if stage == "qa":
            if self.worktrees.revision(developer.path) != expected_revision:
                raise SafeStop("IMPLEMENTATION_CHANGED", "implementation changed after the prior gate")
            if ticket_profile != "minimal" and data.get("review_pass_revision") != expected_revision:
                raise SafeStop("REVIEW_INVALIDATED", "QA gate has no matching Code Review PASS")
            invocation_id, _logical_key = self._invocation_identity(
                run_id, "qa", None, ticket, data
            )
            context = self.worktrees.review_context(run_id, invocation_id, developer.path, expected_revision)
            envelope = self._invoke(
                run_id, "qa", None, ticket, context, expected_revision, data, invocation_id=invocation_id
            )
            if self.worktrees.revision(context.path) != expected_revision:
                raise SafeStop("QA_CONTEXT_CHANGED", "QA context changed during evaluation")
            if envelope.result == "BLOCKED":
                self._transition(
                    run_id,
                    ticket,
                    "blocked",
                    self._semantic_state(ticket.state),
                    f"qa-blocked-{self.store.rework_count(run_id, ticket.id, ticket.revision)}",
                )
                data["blocked_next_owner"] = envelope.next_owner
                self.store.update_run(run_id, data=data)
                raise SafeStop("BLOCKED", f"QA requires owner {envelope.next_owner}")
            if envelope.result == "CHANGES_REQUESTED":
                self._rework_or_block(run_id, data, ticket, "qa", envelope.invocation_id)
                return
            if self.worktrees.revision(developer.path) != expected_revision:
                raise SafeStop("IMPLEMENTATION_CHANGED", "implementation changed after QA evaluation")
            data["qa_pass_revision"] = expected_revision
            self._transition(run_id, ticket, "done", "in_qa", "qa-to-done")
            data["ticket_index"] += 1
            data["ticket_stage"] = "developer"
            data["implementation_revision"] = None
            data["review_pass_revision"] = None
            data["qa_pass_revision"] = None
            self.store.update_run(run_id, data=data)
            return
        if stage == "blocker_review":
            envelope = self._invoke_scope(run_id, "tech-lead", "BLOCKER_REVIEW", data, ticket=ticket)
            if envelope.result != "HUMAN_REVIEW_REQUIRED":
                raise SafeStop("SAFE_STOP", "Tech Lead blocker review returned an invalid result")
            data["human_gate"] = "blocker_review"
            self._transition(
                run_id,
                ticket,
                "human_review_required",
                self._semantic_state(ticket.state),
                "blocker-to-human",
            )
            self.store.update_run(run_id, lifecycle_state="HUMAN_REVIEW_REQUIRED", data=data)
            return
        raise SafeStop("SAFE_STOP", f"unknown ticket stage: {stage}")

    def _load_plan(self, path: Path) -> dict[str, Any]:
        try:
            plan = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SafeStop("MALFORMED_PLAN", "plan payload is not readable JSON") from exc
        if not isinstance(plan, dict):
            raise SafeStop("MALFORMED_PLAN", "plan payload must be a JSON object")
        for key in ("plan_id", "revision", "title", "description"):
            if not isinstance(plan.get(key), str) or not plan[key].strip():
                raise SafeStop("MALFORMED_PLAN", f"plan {key} must be a non-empty string")
        tickets = plan.get("tickets")
        if not isinstance(tickets, list) or not tickets:
            raise SafeStop("MALFORMED_PLAN", "plan tickets must be a non-empty array")
        local_ids: set[str] = set()
        for item in tickets:
            if not isinstance(item, dict):
                raise SafeStop("MALFORMED_PLAN", "each plan ticket must be an object")
            for key in ("local_id", "title", "description"):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    raise SafeStop(
                        "MALFORMED_PLAN", f"each plan ticket {key} must be a non-empty string"
                    )
            local_id = item["local_id"]
            if local_id == plan["plan_id"] or local_id in local_ids:
                raise SafeStop("MALFORMED_PLAN", "plan and ticket local IDs must be unique")
            local_ids.add(local_id)
            contract = item.get("contract")
            if not isinstance(contract, dict):
                raise SafeStop("MALFORMED_PLAN", f"plan ticket {local_id} needs a contract")
            if contract.get("implementation_readiness") != "READY":
                raise SafeStop("MALFORMED_PLAN", f"plan ticket {local_id} is not READY")
            delivery_profile = contract.get("delivery_profile", "standard")
            if delivery_profile not in {"minimal", "standard"}:
                raise SafeStop(
                    "MALFORMED_PLAN", f"plan ticket {local_id} has an invalid delivery profile"
                )
            if delivery_profile == "minimal":
                waiver = contract.get("code_review_waiver")
                declared_revision = contract.get("ticket_revision")
                if not isinstance(waiver, dict) or not isinstance(declared_revision, str):
                    raise SafeStop(
                        "UNAUTHORIZED_PLAN_WAIVER",
                        f"minimal plan ticket {local_id} lacks a revision-bound waiver",
                    )
                required = (
                    "ticket_revision",
                    "implementation_revision",
                    "policy",
                    "authorized_owner",
                    "authoritative_source",
                )
                if any(not isinstance(waiver.get(key), str) or not waiver[key] for key in required):
                    raise SafeStop(
                        "UNAUTHORIZED_PLAN_WAIVER",
                        f"minimal plan ticket {local_id} has an incomplete waiver",
                    )
                if waiver["ticket_revision"] != declared_revision:
                    raise SafeStop(
                        "UNAUTHORIZED_PLAN_WAIVER",
                        f"minimal plan ticket {local_id} waiver revision does not match",
                    )
                authority = {
                    key: waiver[key]
                    for key in ("policy", "authorized_owner", "authoritative_source")
                }
                if authority not in self.config.policy["authorized_minimal_waivers"]:
                    raise SafeStop(
                        "UNAUTHORIZED_PLAN_WAIVER",
                        f"minimal plan ticket {local_id} waiver authority is not configured",
                    )
        return plan

    def _rework_or_block(
        self,
        run_id: str,
        data: dict[str, Any],
        ticket: Ticket,
        role: str,
        invocation_id: str,
    ) -> None:
        count = self.store.add_rework(run_id, ticket.id, ticket.revision, role, invocation_id)
        if count >= self.config.policy["rework_limit"]:
            data["ticket_stage"] = "blocker_review"
            self._transition(
                run_id,
                ticket,
                "blocked",
                self._semantic_state(ticket.state),
                f"rework-limit-{count}",
            )
        else:
            data["ticket_stage"] = "developer"
            self._transition(
                run_id,
                ticket,
                "in_development",
                self._semantic_state(ticket.state),
                f"{role}-to-development-{count}",
            )
        data["review_pass_revision"] = None
        data["qa_pass_revision"] = None
        self.store.update_run(run_id, data=data)

    def _semantic_state(self, state_name: str) -> str:
        for semantic, configured in self.config.status_mapping.items():
            if configured == state_name:
                return semantic
        raise SafeStop("TRACKER_STATE_UNKNOWN", f"unmapped tracker state: {state_name}")

    def _transition(
        self,
        run_id: str,
        ticket: Ticket,
        target: str,
        expected: str,
        suffix: str,
    ) -> None:
        key = f"{run_id}:transition:{ticket.id}:{suffix}"
        receipt = self.store.get_receipt(key)
        if receipt:
            if not self.tracker.verify_transition_receipt(receipt):
                raise SafeStop("RECEIPT_MISMATCH", f"transition receipt mismatch: {key}")
            return
        current = self.tracker.get_ticket(ticket.id)
        if current.revision != ticket.revision:
            raise SafeStop("STALE_TICKET_REVISION", f"ticket {ticket.id} revision changed before transition")
        receipt = self.tracker.transition(current, target, expected, key)
        if not receipt.verified or not self.tracker.verify_transition_receipt(receipt):
            raise SafeStop("RECEIPT_MISMATCH", f"transition was not verified: {key}")
        self.store.save_receipt(run_id, receipt)

    def _invoke_scope(
        self,
        run_id: str,
        role: str,
        mode: str,
        data: dict[str, Any],
        *,
        payload: bool = False,
        ticket: Ticket | None = None,
    ) -> ResultEnvelope:
        context = ExecutionContext(path=self.config.repository, implementation_revision=data.get("implementation_revision"))
        return self._invoke(
            run_id,
            role,
            mode,
            ticket,
            context,
            data.get("implementation_revision"),
            data,
            payload=payload,
        )

    def _invocation_identity(
        self,
        run_id: str,
        role: str,
        mode: str | None,
        ticket: Ticket | None,
        data: dict[str, Any],
    ) -> tuple[str, str]:
        rework = (
            self.store.rework_count(run_id, ticket.id, ticket.revision)
            if ticket
            else 0
        )
        identity = {
            "project_id": self.config.project_id,
            "run_id": run_id,
            "role": role,
            "mode": mode,
            "ticket_id": ticket.id if ticket else None,
            "ticket_revision": ticket.revision if ticket else None,
            "stage": data.get("stage"),
            "ticket_stage": data.get("ticket_stage"),
            "ticket_index": data.get("ticket_index"),
            "rework": rework,
            "partial_generation": data.get("partial_generation", 0),
            "retry_generation": data.get("retry_generation", 0),
        }
        logical_key = hashlib.sha256(
            json.dumps(identity, sort_keys=True).encode("utf-8")
        ).hexdigest()
        invocation_id = "inv-" + uuid.uuid5(
            uuid.NAMESPACE_URL, f"d2269-invocation:{logical_key}"
        ).hex
        return invocation_id, logical_key

    def _invoke(
        self,
        run_id: str,
        role: str,
        mode: str | None,
        ticket: Ticket | None,
        context: ExecutionContext,
        implementation_revision: str | None,
        data: dict[str, Any],
        *,
        payload: bool = False,
        invocation_id: str | None = None,
    ) -> ResultEnvelope:
        expected_invocation_id, logical_key = self._invocation_identity(
            run_id, role, mode, ticket, data
        )
        if invocation_id and invocation_id != expected_invocation_id:
            raise SafeStop("INVOCATION_ID_MISMATCH", "invocation identity is not deterministic")
        invocation_id = expected_invocation_id
        existing = self.store.find_invocation(run_id, logical_key)
        if existing:
            invocation_id = existing["invocation_id"]
            if (
                existing["role"] != role
                or existing["mode"] != mode
                or existing["ticket_id"] != (ticket.id if ticket else None)
                or existing["ticket_revision"] != (ticket.revision if ticket else None)
                or existing["implementation_revision"] != implementation_revision
            ):
                raise SafeStop("INVOCATION_MISMATCH", "recorded invocation does not match the current gate")
            context = ExecutionContext(
                Path(existing["context_path"]),
                existing["implementation_revision"],
                context.source_path,
            )
            envelope_path = Path(existing["envelope_path"])
            directory = envelope_path.parent
            report_path = directory / "report.md"
            comment_path = directory / "comment.md"
            payload_path = directory / "payload.json" if payload else None
            if existing["status"] == "STARTED" and not envelope_path.is_file():
                raise SafeStop(
                    "INVOCATION_UNCERTAIN",
                    "a prior role prompt may have been accepted but has no durable result",
                )
            status_stops = {
                "BLOCKED": "HERDR_BLOCKED",
                "UNKNOWN": "HERDR_UNKNOWN",
                "TIMEOUT_UNCERTAIN": "HERDR_TIMEOUT_UNCERTAIN",
                "ERROR": "HERDR_ERROR",
            }
            if existing["status"] in status_stops:
                raise SafeStop(
                    status_stops[existing["status"]],
                    f"recorded invocation stopped with status {existing['status']}",
                )
        else:
            staging = (
                Path(tempfile.gettempdir())
                / "d2269-controller"
                / self.config.project_id
                / run_id
                / invocation_id
            )
            staging.mkdir(parents=True, exist_ok=True)
            report_path = staging / "report.md"
            comment_path = staging / "comment.md"
            envelope_path = staging / "result.json"
            payload_path = staging / "payload.json" if payload else None
        request = InvocationRequest(
            run_id=run_id,
            invocation_id=invocation_id,
            project_id=self.config.project_id,
            role=role,
            mode=mode,
            ticket=ticket,
            implementation_revision=implementation_revision,
            context=context,
            report_path=report_path,
            comment_path=comment_path,
            envelope_path=envelope_path,
            payload_path=payload_path,
            extra_context={
                "scope": data.get("scope", ""),
                "state": data,
                "comments": self.tracker.get_comments(ticket.id) if ticket else [],
                "prior_artifacts": self.store.artifact_context(run_id),
                "receipts": self.store.receipt_context(run_id),
                "authorized_minimal_waivers": self.config.policy[
                    "authorized_minimal_waivers"
                ],
                "allowed_results": sorted(ROLE_RESULTS.get((role, mode), set())),
                "allowed_actions": {
                    result: sorted(ACTION_RULES.get((role, mode, result), set()))
                    for result in ROLE_RESULTS.get((role, mode), set())
                },
            },
        )
        if not existing:
            self.store.create_invocation(
                {
                    "invocation_id": invocation_id,
                    "logical_key": logical_key,
                    "run_id": run_id,
                    "role": role,
                    "mode": mode,
                    "ticket_id": ticket.id if ticket else None,
                    "ticket_revision": ticket.revision if ticket else None,
                    "implementation_revision": implementation_revision,
                    "context_path": str(context.path),
                    "envelope_path": str(envelope_path),
                }
            )
            try:
                self.runner.invoke(request)
            except RunnerBlocked as exc:
                self.store.complete_invocation(invocation_id, "BLOCKED")
                raise SafeStop("HERDR_BLOCKED", str(exc)) from exc
            except RunnerUnknown as exc:
                self.store.complete_invocation(invocation_id, "UNKNOWN")
                raise SafeStop("HERDR_UNKNOWN", str(exc)) from exc
            except RunnerTimeoutUncertain as exc:
                self.store.complete_invocation(invocation_id, "TIMEOUT_UNCERTAIN")
                raise SafeStop("HERDR_TIMEOUT_UNCERTAIN", str(exc)) from exc
            except RunnerError:
                self.store.complete_invocation(invocation_id, "ERROR")
                raise
        try:
            envelope = self._validate_envelope(request)
        except SafeStop as exc:
            self.store.complete_invocation(invocation_id, exc.state)
            raise
        durable_directory = self.store.project_dir / "artifacts" / run_id / invocation_id
        durable_directory.mkdir(parents=True, exist_ok=True)
        durable_report = durable_directory / "report.md"
        durable_comment = durable_directory / "comment.md"
        durable_payload = durable_directory / "payload.json" if payload_path else None
        if report_path.resolve() != durable_report.resolve():
            shutil.copy2(report_path, durable_report)
        if comment_path.resolve() != durable_comment.resolve():
            shutil.copy2(comment_path, durable_comment)
        if payload_path and durable_payload and payload_path.resolve() != durable_payload.resolve():
            shutil.copy2(payload_path, durable_payload)
        durable_envelope = replace(
            envelope,
            report_path=str(durable_report),
            comment_path=str(durable_comment),
            payload_path=str(durable_payload) if durable_payload else None,
        )
        durable_envelope_path = durable_directory / "result.json"
        durable_envelope_path.write_text(
            json.dumps(durable_envelope.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self._record_artifact(run_id, invocation_id, "report", durable_report)
        self._record_artifact(run_id, invocation_id, "comment", durable_comment)
        self._record_artifact(run_id, invocation_id, "envelope", durable_envelope_path)
        if durable_payload:
            self._record_artifact(run_id, invocation_id, "payload", durable_payload)
        self.store.complete_invocation(
            invocation_id, durable_envelope.result, envelope_path=str(durable_envelope_path)
        )
        if ticket:
            self._publish_comment(run_id, ticket, durable_envelope, durable_comment)
        return durable_envelope

    def _validate_envelope(self, request: InvocationRequest) -> ResultEnvelope:
        if not request.envelope_path.is_file():
            raise SafeStop("MISSING_ARTIFACT", "role result envelope is missing")
        try:
            raw = json.loads(request.envelope_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SafeStop("MALFORMED_RESULT", "role result envelope is not valid JSON") from exc
        if not isinstance(raw, dict):
            raise SafeStop("MALFORMED_RESULT", "role result envelope must be a JSON object")
        try:
            envelope = ResultEnvelope.from_dict(raw)
        except (TypeError, ValueError) as exc:
            raise SafeStop("MALFORMED_RESULT", str(exc)) from exc
        expected = {
            "schema_version": "1",
            "run_id": request.run_id,
            "invocation_id": request.invocation_id,
            "project_id": request.project_id,
            "role": request.role,
            "mode": request.mode,
            "ticket_id": request.ticket.id if request.ticket else None,
            "ticket_revision": request.ticket.revision if request.ticket else None,
        }
        for key, value in expected.items():
            if getattr(envelope, key) != value:
                raise SafeStop("MISMATCHED_RESULT", f"result envelope {key} mismatch")
        if envelope.result not in ROLE_RESULTS.get((request.role, request.mode), set()):
            raise SafeStop("MALFORMED_RESULT", "result is not valid for the role and mode")
        actions = ACTION_RULES.get((request.role, request.mode, envelope.result), set())
        if envelope.requested_action not in actions:
            raise SafeStop("MALFORMED_RESULT", "requested_action is not permitted for the result")
        if envelope.comment_state != "READY_TO_POST":
            raise SafeStop("MALFORMED_RESULT", "automated roles must return READY_TO_POST")
        if Path(envelope.report_path).resolve() != request.report_path.resolve():
            raise SafeStop("MISMATCHED_RESULT", "report path does not match the invocation")
        if Path(envelope.comment_path).resolve() != request.comment_path.resolve():
            raise SafeStop("MISMATCHED_RESULT", "comment path does not match the invocation")
        for path in (request.report_path, request.comment_path):
            if not path.is_file() or not path.read_text(encoding="utf-8").strip():
                raise SafeStop("MISSING_ARTIFACT", f"required artifact is missing or empty: {path}")
        if request.payload_path:
            if not envelope.payload_path or Path(envelope.payload_path).resolve() != request.payload_path.resolve():
                raise SafeStop("MISMATCHED_RESULT", "payload path does not match the invocation")
            if not request.payload_path.is_file():
                raise SafeStop("MISSING_ARTIFACT", "required machine-readable payload is missing")
        if request.implementation_revision is not None and envelope.implementation_revision != request.implementation_revision:
            raise SafeStop("MISMATCHED_RESULT", "implementation revision does not match invocation target")
        try:
            created_at = datetime.fromisoformat(envelope.created_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise SafeStop("MALFORMED_RESULT", "created_at is not an RFC3339 timestamp") from exc
        if created_at.tzinfo is None:
            raise SafeStop("MALFORMED_RESULT", "created_at must include an RFC3339 timezone")
        return envelope

    def _publish_comment(
        self, run_id: str, ticket: Ticket, envelope: ResultEnvelope, comment_path: Path
    ) -> None:
        key = f"{run_id}:comment:{envelope.invocation_id}"
        receipt = self.store.get_receipt(key)
        if receipt:
            if not self.tracker.verify_comment_receipt(receipt):
                raise SafeStop("RECEIPT_MISMATCH", f"comment receipt mismatch: {key}")
            return
        current = self.tracker.get_ticket(ticket.id)
        if current.revision != ticket.revision:
            raise SafeStop(
                "STALE_TICKET_REVISION",
                f"ticket {ticket.id} revision changed before comment publication",
            )
        if current.tracker_marker != ticket.tracker_marker:
            raise SafeStop(
                "STALE_TRACKER_MARKER",
                f"ticket {ticket.id} changed before comment publication",
            )
        body = comment_path.read_text(encoding="utf-8")
        receipt = self.tracker.publish_comment(ticket, body, key)
        if not receipt.verified or not self.tracker.verify_comment_receipt(receipt):
            raise SafeStop("RECEIPT_MISMATCH", "comment publication was not verified")
        self.store.save_receipt(run_id, receipt)

    def _record_artifact(self, run_id: str, invocation_id: str, kind: str, path: Path) -> None:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.store.add_artifact(run_id, invocation_id, kind, str(path), digest)
