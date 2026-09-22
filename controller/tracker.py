"""Provider-neutral tracker operations used by the workflow engine."""

from __future__ import annotations

from typing import Any, Protocol

from .models import Receipt, Ticket


class TrackerPort(Protocol):
    def get_ticket(self, ticket_id: str) -> Ticket: ...

    def get_comments(self, ticket_id: str) -> list[dict[str, Any]]: ...

    def publish_comment(
        self, ticket: Ticket, body: str, idempotency_key: str
    ) -> Receipt: ...

    def verify_comment_receipt(self, receipt: Receipt) -> bool: ...

    def transition(
        self,
        ticket: Ticket,
        semantic_target: str,
        expected_semantic_state: str,
        idempotency_key: str,
    ) -> Receipt: ...

    def verify_transition_receipt(self, receipt: Receipt) -> bool: ...

    def sync_plan(
        self,
        plan: dict[str, Any],
        existing_mappings: dict[str, dict[str, Any]],
        idempotency_prefix: str,
    ) -> tuple[list[Ticket], list[Receipt]]: ...


class TrackerError(RuntimeError):
    pass


class TrackerPreconditionError(TrackerError):
    pass

