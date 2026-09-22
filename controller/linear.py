"""Minimal production Linear GraphQL adapter."""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
import uuid
from dataclasses import replace
from typing import Any

from .models import Receipt, Ticket, Waiver
from .tracker import TrackerError, TrackerPreconditionError


CONTRACT_RE = re.compile(
    r"<!--\s*d2269-controller-contract\s*(\{.*?\})\s*-->", re.DOTALL
)
COMMENT_MARKER = "<!-- d2269-controller:{key} -->"


class LinearTracker:
    def __init__(self, config: dict[str, Any], *, mutations_authorized: bool):
        self.endpoint = config.get("endpoint", "https://api.linear.app/graphql")
        token_env = config.get("token_env", "LINEAR_API_KEY")
        self.token = os.environ.get(token_env)
        self.team_id = config.get("team_id")
        self.controller_project_id = config.get("controller_project_id")
        self.status_mapping = dict(config["status_mapping"])
        self.mutations_authorized = mutations_authorized
        if not self.token:
            raise TrackerError(f"Linear token environment variable is not set: {token_env}")
        if not self.team_id:
            raise TrackerError("tracker.team_id is required")
        if not self.controller_project_id:
            raise TrackerError("controller project_id is required")

    def _graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": self.token},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            raise TrackerError(f"Linear request failed: {exc}") from exc
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TrackerError("Linear returned non-JSON data") from exc
        if decoded.get("errors"):
            messages = [str(item.get("message", "unknown GraphQL error")) for item in decoded["errors"]]
            raise TrackerError("Linear GraphQL errors: " + "; ".join(messages))
        data = decoded.get("data")
        if not isinstance(data, dict):
            raise TrackerError("Linear response has no data object")
        return data

    @staticmethod
    def _contract(description: str) -> dict[str, Any]:
        match = CONTRACT_RE.search(description or "")
        if not match:
            return {}
        try:
            value = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            raise TrackerError("Linear ticket has malformed d2269 controller contract") from exc
        if not isinstance(value, dict):
            raise TrackerError("Linear ticket controller contract must be a JSON object")
        return value

    @staticmethod
    def _ticket_revision(raw: dict[str, Any], contract: dict[str, Any]) -> str:
        stable = {
            "id": raw["id"],
            "title": raw.get("title", ""),
            "description": raw.get("description", ""),
            "labels": sorted(node["name"] for node in raw.get("labels", {}).get("nodes", [])),
            "parent": (raw.get("parent") or {}).get("id"),
        }
        digest = hashlib.sha256(json.dumps(stable, sort_keys=True).encode("utf-8")).hexdigest()
        explicit = contract.get("ticket_revision")
        if isinstance(explicit, str) and explicit:
            return f"linear-contract:{explicit}:content-sha256:{digest}"
        return "linear-content-sha256:" + digest

    @staticmethod
    def _waiver(contract: dict[str, Any]) -> Waiver | None:
        value = contract.get("code_review_waiver")
        if not isinstance(value, dict):
            return None
        required = (
            "ticket_revision",
            "implementation_revision",
            "policy",
            "authorized_owner",
            "authoritative_source",
        )
        if any(not isinstance(value.get(key), str) or not value[key] for key in required):
            raise TrackerError("code_review_waiver is missing required string fields")
        implementation = value.get("implementation_revision")
        return Waiver(
            ticket_revision=value["ticket_revision"],
            implementation_revision=implementation,
            policy=value["policy"],
            authorized_owner=value["authorized_owner"],
            authoritative_source=value["authoritative_source"],
        )

    def get_ticket(self, ticket_id: str) -> Ticket:
        query = """
        query Ticket($id: String!) {
          issue(id: $id) {
            id identifier title description url updatedAt
            state { id name }
            team { id }
            labels { nodes { name } }
            parent { id identifier }
          }
        }
        """
        raw = self._graphql(query, {"id": ticket_id}).get("issue")
        if not isinstance(raw, dict):
            raise TrackerError(f"Linear ticket not found: {ticket_id}")
        if (raw.get("team") or {}).get("id") != self.team_id:
            raise TrackerError("Linear ticket is outside the configured team")
        description = raw.get("description") or ""
        contract = self._contract(description)
        links = contract.get("links", [])
        if not isinstance(links, list) or any(not isinstance(item, str) for item in links):
            raise TrackerError("ticket contract links must be a list of strings")
        revision = self._ticket_revision(raw, contract)
        waiver = self._waiver(contract)
        explicit_revision = contract.get("ticket_revision")
        if waiver and waiver.ticket_revision == explicit_revision:
            waiver = replace(waiver, ticket_revision=revision)
        return Ticket(
            id=raw.get("identifier") or ticket_id,
            external_id=raw["id"],
            title=raw.get("title") or "",
            description=description,
            url=raw.get("url") or "",
            revision=revision,
            tracker_marker=raw["updatedAt"],
            state=(raw.get("state") or {}).get("name", ""),
            semantic_readiness=contract.get("implementation_readiness"),
            delivery_profile=contract.get("delivery_profile"),
            links=tuple(links),
            waiver=waiver,
        )

    def get_comments(self, ticket_id: str) -> list[dict[str, Any]]:
        query = """
        query Comments($id: String!) {
          issue(id: $id) { comments { nodes { id body createdAt updatedAt } } }
        }
        """
        issue = self._graphql(query, {"id": ticket_id}).get("issue")
        if not isinstance(issue, dict):
            raise TrackerError(f"Linear ticket not found: {ticket_id}")
        return list((issue.get("comments") or {}).get("nodes") or [])

    def _require_mutation(self) -> None:
        if not self.mutations_authorized:
            raise TrackerError("external mutations require --authorize-mutations")

    def publish_comment(self, ticket: Ticket, body: str, idempotency_key: str) -> Receipt:
        self._require_mutation()
        current = self.get_ticket(ticket.external_id)
        if current.revision != ticket.revision:
            raise TrackerPreconditionError("ticket contract revision changed before comment publication")
        if current.tracker_marker != ticket.tracker_marker:
            raise TrackerPreconditionError("Linear issue changed before comment publication")
        marker = COMMENT_MARKER.format(key=idempotency_key)
        deterministic_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"d2269-linear-comment:{self.controller_project_id}:{idempotency_key}",
            )
        )
        existing = self._graphql(
            "query Comment($id: String!) { comment(id: $id) { id body } }",
            {"id": deterministic_id},
        ).get("comment")
        if isinstance(existing, dict):
            return Receipt("comment", idempotency_key, deterministic_id, True, {"replayed": True})
        for comment in self.get_comments(ticket.external_id):
            if marker in (comment.get("body") or ""):
                return Receipt("comment", idempotency_key, comment["id"], True, {"replayed": True})
        mutation = """
        mutation Comment($input: CommentCreateInput!) {
          commentCreate(input: $input) { success comment { id body } }
        }
        """
        result = self._graphql(
            mutation,
            {
                "input": {
                    "id": deterministic_id,
                    "issueId": ticket.external_id,
                    "body": body.rstrip() + "\n\n" + marker,
                }
            },
        ).get("commentCreate")
        if not isinstance(result, dict) or not result.get("success") or not result.get("comment"):
            raise TrackerError("Linear commentCreate did not confirm success")
        receipt = Receipt("comment", idempotency_key, result["comment"]["id"], True)
        if not self.verify_comment_receipt(receipt):
            raise TrackerError("Linear comment receipt verification failed")
        return receipt

    def verify_comment_receipt(self, receipt: Receipt) -> bool:
        query = "query Comment($id: String!) { comment(id: $id) { id body } }"
        comment = self._graphql(query, {"id": receipt.external_id}).get("comment")
        marker = COMMENT_MARKER.format(key=receipt.idempotency_key)
        return (
            isinstance(comment, dict)
            and comment.get("id") == receipt.external_id
            and marker in (comment.get("body") or "")
        )

    def _semantic_for_state(self, state: str) -> str | None:
        for semantic, configured in self.status_mapping.items():
            if configured == state:
                return semantic
        return None

    def _state_id(self, name: str) -> str:
        query = "query Team($id: String!) { team(id: $id) { states { nodes { id name } } } }"
        team = self._graphql(query, {"id": self.team_id}).get("team")
        for state in (team or {}).get("states", {}).get("nodes", []):
            if state.get("name") == name:
                return str(state["id"])
        raise TrackerError(f"Linear team has no workflow state named {name!r}")

    def _issue_identity(self, issue_id: str) -> dict[str, Any] | None:
        value = self._graphql(
            """query IssueIdentity($id: String!) {
                 issue(id: $id) {
                   id identifier title description
                   parent { id }
                   team { id }
                 }
               }""",
            {"id": issue_id},
        ).get("issue")
        if not isinstance(value, dict):
            return None
        if (value.get("team") or {}).get("id") != self.team_id:
            raise TrackerError("mapped Linear issue is outside the configured team")
        return value

    @staticmethod
    def _content_digest(title: str, description: str, parent_id: str | None) -> str:
        stable = {"title": title, "description": description, "parent_id": parent_id}
        return hashlib.sha256(json.dumps(stable, sort_keys=True).encode("utf-8")).hexdigest()

    def _sync_issue(
        self,
        *,
        external_id: str,
        mapping: dict[str, Any] | None,
        title: str,
        description: str,
        parent_id: str | None,
        create_input: dict[str, Any],
    ) -> tuple[dict[str, Any], str]:
        desired_digest = self._content_digest(title, description, parent_id)
        current = self._issue_identity(external_id)
        if current:
            current_parent = (current.get("parent") or {}).get("id")
            if parent_id is None and current_parent is not None:
                raise TrackerPreconditionError(
                    "controller plan issue unexpectedly has a parent"
                )
            current_digest = self._content_digest(
                current.get("title") or "",
                current.get("description") or "",
                current_parent,
            )
            if current_digest != desired_digest:
                if not mapping:
                    raise TrackerPreconditionError(
                        "deterministic Linear issue ID exists with unexpected content"
                    )
                prior_digest = mapping.get("payload", {}).get("content_sha256")
                if not prior_digest or current_digest != prior_digest:
                    raise TrackerPreconditionError(
                        "mapped Linear issue changed since the prior controller revision"
                    )
                mutation = """
                mutation Update($id: String!, $input: IssueUpdateInput!) {
                  issueUpdate(id: $id, input: $input) { success issue { id identifier } }
                }
                """
                result = self._graphql(
                    mutation,
                    {
                        "id": external_id,
                        "input": {
                            "title": title,
                            "description": description,
                            **({"parentId": parent_id} if parent_id else {}),
                        },
                    },
                ).get("issueUpdate")
                issue = result.get("issue") if isinstance(result, dict) else None
                if not result or not result.get("success") or not issue:
                    raise TrackerError("Linear issue update did not confirm success")
        else:
            if mapping:
                raise TrackerPreconditionError("mapped Linear issue no longer exists")
            result = self._graphql(
                """mutation Create($input: IssueCreateInput!) {
                     issueCreate(input: $input) { success issue { id identifier } }
                   }""",
                {"input": {"id": external_id, **create_input}},
            ).get("issueCreate")
            issue = result.get("issue") if isinstance(result, dict) else None
            if not result or not result.get("success") or not issue:
                raise TrackerError("Linear issue creation did not confirm success")
        verified = self._issue_identity(external_id)
        if not verified:
            raise TrackerError("Linear issue synchronization could not be verified")
        verified_digest = self._content_digest(
            verified.get("title") or "",
            verified.get("description") or "",
            (verified.get("parent") or {}).get("id"),
        )
        if verified_digest != desired_digest:
            raise TrackerError("Linear issue content does not match the synchronized plan")
        return verified, desired_digest

    def transition(
        self,
        ticket: Ticket,
        semantic_target: str,
        expected_semantic_state: str,
        idempotency_key: str,
    ) -> Receipt:
        self._require_mutation()
        current = self.get_ticket(ticket.external_id)
        target_name = self.status_mapping[semantic_target]
        expected_name = self.status_mapping[expected_semantic_state]
        if current.revision != ticket.revision:
            raise TrackerPreconditionError("ticket contract revision changed before transition")
        if current.state == target_name:
            return Receipt(
                "transition",
                idempotency_key,
                current.external_id,
                True,
                {"from": expected_name, "to": target_name, "replayed": True},
            )
        if current.state != expected_name:
            raise TrackerPreconditionError(
                f"expected Linear state {expected_name!r}, observed {current.state!r}"
            )
        if current.tracker_marker != ticket.tracker_marker:
            raise TrackerPreconditionError("Linear issue changed after the transition precondition read")
        mutation = """
        mutation Transition($id: String!, $input: IssueUpdateInput!) {
          issueUpdate(id: $id, input: $input) {
            success issue { id updatedAt state { id name } }
          }
        }
        """
        result = self._graphql(
            mutation,
            {"id": current.external_id, "input": {"stateId": self._state_id(target_name)}},
        ).get("issueUpdate")
        issue = result.get("issue") if isinstance(result, dict) else None
        if not result or not result.get("success") or not issue or issue["state"]["name"] != target_name:
            raise TrackerError("Linear transition did not confirm the requested state")
        receipt = Receipt(
            "transition",
            idempotency_key,
            current.external_id,
            True,
            {"from": current.state, "to": target_name, "updatedAt": issue["updatedAt"]},
        )
        if not self.verify_transition_receipt(receipt):
            raise TrackerError("Linear transition receipt verification failed")
        return receipt

    def verify_transition_receipt(self, receipt: Receipt) -> bool:
        current = self.get_ticket(receipt.external_id)
        return current.state == receipt.payload.get("to")

    def sync_plan(
        self,
        plan: dict[str, Any],
        existing_mappings: dict[str, dict[str, Any]],
        idempotency_prefix: str,
    ) -> tuple[list[Ticket], list[Receipt]]:
        self._require_mutation()
        revision = plan.get("revision")
        tasks = plan.get("tickets")
        plan_id = plan.get("plan_id")
        if not all(isinstance(plan.get(key), str) and plan[key] for key in ("plan_id", "revision", "title", "description")) or not isinstance(tasks, list):
            raise TrackerError("plan payload requires plan_id, revision, title, description, and tickets")
        tickets: list[Ticket] = []
        receipts: list[Receipt] = []
        parent_mapping = existing_mappings.get(plan_id)
        parent_id = parent_mapping["external_id"] if parent_mapping else str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"d2269-linear-plan:{self.controller_project_id}:{self.team_id}:{plan_id}",
            )
        )
        parent_input = {
            "title": plan["title"],
            "description": plan["description"],
        }
        parent_desired_digest = self._content_digest(
            plan["title"], plan["description"], None
        )
        if (
            parent_mapping
            and parent_mapping.get("revision") == revision
            and parent_mapping.get("payload", {}).get("content_sha256")
            != parent_desired_digest
        ):
            raise TrackerPreconditionError("plan content changed without a new revision")
        parent_issue, parent_digest = self._sync_issue(
            external_id=parent_id,
            mapping=parent_mapping,
            title=plan["title"],
            description=plan["description"],
            parent_id=None,
            create_input={"teamId": self.team_id, **parent_input},
        )
        receipts.append(
            Receipt(
                "plan-sync",
                f"{idempotency_prefix}:{plan_id}:{revision}",
                parent_issue["id"],
                True,
                {
                    "local_id": plan_id,
                    "revision": revision,
                    "identifier": parent_issue["identifier"],
                    "content_sha256": parent_digest,
                },
            )
        )
        local_ids: set[str] = set()
        for item in tasks:
            if not isinstance(item, dict) or not all(
                isinstance(item.get(key), str) and item[key].strip()
                for key in ("local_id", "title", "description")
            ):
                raise TrackerError("each plan ticket requires non-empty local_id, title, and description")
            local_id = item["local_id"]
            if local_id == plan_id or local_id in local_ids:
                raise TrackerError("plan and task local IDs must be unique")
            local_ids.add(local_id)
            mapping = existing_mappings.get(local_id)
            marker = f"{idempotency_prefix}:{local_id}:{revision}"
            contract = item.get("contract", {})
            if not isinstance(contract, dict):
                raise TrackerError(f"plan task {local_id} contract must be an object")
            if contract.get("implementation_readiness") != "READY":
                raise TrackerError(f"plan task {local_id} is not semantically READY")
            if contract.get("delivery_profile", "standard") not in {"minimal", "standard"}:
                raise TrackerError(f"plan task {local_id} has an invalid delivery_profile")
            description = item["description"].rstrip() + "\n\n<!-- d2269-controller-contract\n" + json.dumps(contract, sort_keys=True) + "\n-->"
            desired_digest = self._content_digest(
                item["title"], description, parent_issue["id"]
            )
            if (
                mapping
                and mapping.get("revision") == revision
                and mapping.get("payload", {}).get("content_sha256")
                != desired_digest
            ):
                raise TrackerPreconditionError(
                    f"plan task {local_id} changed without a new revision"
                )
            external_id = mapping["external_id"] if mapping else str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"d2269-linear-task:{self.controller_project_id}:{self.team_id}:{plan_id}:{local_id}",
                )
            )
            issue, content_digest = self._sync_issue(
                external_id=external_id,
                mapping=mapping,
                title=item["title"],
                description=description,
                parent_id=parent_issue["id"],
                create_input={
                    "teamId": self.team_id,
                    "parentId": parent_issue["id"],
                    "stateId": self._state_id(self.status_mapping["ready"]),
                    "title": item["title"],
                    "description": description,
                },
            )
            ticket = self.get_ticket(issue["id"])
            tickets.append(ticket)
            receipts.append(
                Receipt(
                    "plan-sync",
                    marker,
                    issue["id"],
                    True,
                    {
                        "local_id": local_id,
                        "revision": revision,
                        "identifier": issue["identifier"],
                        "content_sha256": content_digest,
                    },
                )
            )
        return tickets, receipts
