"""SQLite-backed workflow state and project-scoped locking."""

from __future__ import annotations

import fcntl
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .models import Receipt, utc_now


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    project_path TEXT NOT NULL,
    profile TEXT NOT NULL,
    target_kind TEXT NOT NULL,
    target_ref TEXT NOT NULL,
    lifecycle_state TEXT NOT NULL,
    policy_json TEXT NOT NULL,
    data_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS runs_project_state ON runs(project_id, lifecycle_state);
CREATE TABLE IF NOT EXISTS invocations (
    invocation_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    project_id TEXT NOT NULL,
    role TEXT NOT NULL,
    mode TEXT,
    ticket_id TEXT,
    ticket_revision TEXT,
    implementation_revision TEXT,
    status TEXT NOT NULL,
    context_path TEXT NOT NULL,
    envelope_path TEXT NOT NULL,
    logical_key TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS artifacts (
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    invocation_id TEXT NOT NULL REFERENCES invocations(invocation_id),
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    digest TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (invocation_id, kind)
);
CREATE TABLE IF NOT EXISTS receipts (
    project_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    kind TEXT NOT NULL,
    external_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (project_id, idempotency_key)
);
CREATE TABLE IF NOT EXISTS rework_events (
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    ticket_id TEXT NOT NULL,
    ticket_revision TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    source_role TEXT NOT NULL,
    invocation_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (run_id, ticket_id, ticket_revision, sequence)
);
CREATE TABLE IF NOT EXISTS human_decisions (
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    sequence INTEGER NOT NULL,
    gate TEXT NOT NULL,
    decision_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (run_id, sequence)
);
CREATE TABLE IF NOT EXISTS mappings (
    project_id TEXT NOT NULL,
    local_id TEXT NOT NULL,
    external_id TEXT NOT NULL,
    revision TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (project_id, local_id)
);
CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    invocation_id TEXT,
    code TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class StateStore:
    def __init__(self, state_root: Path, project_id: str):
        self.project_id = project_id
        self.project_dir = state_root.expanduser().resolve() / project_id
        for name in ("runs", "artifacts", "receipts", "locks", "worktrees"):
            (self.project_dir / name).mkdir(parents=True, exist_ok=True)
        self.database_path = self.project_dir / "controller.sqlite3"
        self.connection = sqlite3.connect(self.database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        columns = {
            row[1]
            for row in self.connection.execute("PRAGMA table_info(invocations)")
        }
        if "logical_key" not in columns:
            self.connection.execute("ALTER TABLE invocations ADD COLUMN logical_key TEXT")
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS invocations_logical_key "
            "ON invocations(run_id, logical_key, created_at)"
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    @contextmanager
    def lock(self) -> Iterator[None]:
        path = self.project_dir / "locks" / "project.lock"
        with path.open("a+", encoding="utf-8") as handle:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError(f"project {self.project_id!r} already has an active run") from exc
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def create_run(
        self,
        *,
        run_id: str,
        project_path: str,
        profile: str,
        target_kind: str,
        target_ref: str,
        policy: dict[str, Any],
        data: dict[str, Any],
    ) -> None:
        now = utc_now()
        with self.connection:
            self.connection.execute(
                """INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    self.project_id,
                    project_path,
                    profile,
                    target_kind,
                    target_ref,
                    "RUNNING",
                    json.dumps(policy, sort_keys=True),
                    json.dumps(data, sort_keys=True),
                    now,
                    now,
                ),
            )

    def get_run(self, run_id: str) -> dict[str, Any]:
        row = self.connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown run: {run_id}")
        result = dict(row)
        result["policy"] = json.loads(result.pop("policy_json"))
        result["data"] = json.loads(result.pop("data_json"))
        return result

    def update_run(
        self,
        run_id: str,
        *,
        lifecycle_state: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        current = self.get_run(run_id)
        state = lifecycle_state or current["lifecycle_state"]
        new_data = data if data is not None else current["data"]
        with self.connection:
            self.connection.execute(
                "UPDATE runs SET lifecycle_state=?, data_json=?, updated_at=? WHERE run_id=?",
                (state, json.dumps(new_data, sort_keys=True), utc_now(), run_id),
            )

    def find_active(self, target_kind: str, target_ref: str) -> str | None:
        row = self.connection.execute(
            """SELECT run_id FROM runs
               WHERE project_id=? AND target_kind=? AND target_ref=?
                 AND lifecycle_state NOT IN ('COMPLETED','STOPPED','FAILED')
               ORDER BY created_at DESC LIMIT 1""",
            (self.project_id, target_kind, target_ref),
        ).fetchone()
        return str(row[0]) if row else None

    def create_invocation(self, values: dict[str, Any]) -> None:
        with self.connection:
            self.connection.execute(
                """INSERT INTO invocations
                   (invocation_id, run_id, project_id, role, mode, ticket_id,
                    ticket_revision, implementation_revision, status, context_path,
                    envelope_path, logical_key, created_at, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'STARTED', ?, ?, ?, ?, NULL)""",
                (
                    values["invocation_id"],
                    values["run_id"],
                    self.project_id,
                    values["role"],
                    values.get("mode"),
                    values.get("ticket_id"),
                    values.get("ticket_revision"),
                    values.get("implementation_revision"),
                    values["context_path"],
                    values["envelope_path"],
                    values["logical_key"],
                    utc_now(),
                ),
            )

    def find_invocation(self, run_id: str, logical_key: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            """SELECT * FROM invocations
               WHERE run_id=? AND logical_key=? AND status!='ABANDONED'
               ORDER BY created_at DESC LIMIT 1""",
            (run_id, logical_key),
        ).fetchone()
        return dict(row) if row else None

    def complete_invocation(
        self, invocation_id: str, status: str, *, envelope_path: str | None = None
    ) -> None:
        with self.connection:
            if envelope_path is None:
                self.connection.execute(
                    "UPDATE invocations SET status=?, completed_at=? WHERE invocation_id=?",
                    (status, utc_now(), invocation_id),
                )
            else:
                self.connection.execute(
                    """UPDATE invocations SET status=?, envelope_path=?, completed_at=?
                       WHERE invocation_id=?""",
                    (status, envelope_path, utc_now(), invocation_id),
                )

    def pending_invocation(
        self, run_id: str, role: str, mode: str | None, ticket_id: str | None
    ) -> dict[str, Any] | None:
        row = self.connection.execute(
            """SELECT * FROM invocations
               WHERE run_id=? AND role=? AND mode IS ? AND ticket_id IS ? AND status='STARTED'
               ORDER BY created_at DESC LIMIT 1""",
            (run_id, role, mode, ticket_id),
        ).fetchone()
        return dict(row) if row else None

    def abandon_pending_invocations(self, run_id: str) -> None:
        with self.connection:
            self.connection.execute(
                """UPDATE invocations SET status='ABANDONED', completed_at=?
                   WHERE run_id=? AND status='STARTED'""",
                (utc_now(), run_id),
            )

    def artifact_context(self, run_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """SELECT i.role, i.mode, i.ticket_id, i.ticket_revision,
                      i.implementation_revision, i.status, a.kind, a.path, a.digest
               FROM invocations i JOIN artifacts a ON a.invocation_id=i.invocation_id
               WHERE i.run_id=? ORDER BY i.created_at, a.kind""",
            (run_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def receipt_context(self, run_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """SELECT kind, idempotency_key, external_id, payload_json, created_at
               FROM receipts WHERE run_id=? ORDER BY created_at""",
            (run_id,),
        ).fetchall()
        return [
            {
                **{key: row[key] for key in ("kind", "idempotency_key", "external_id", "created_at")},
                "payload": json.loads(row["payload_json"]),
            }
            for row in rows
        ]

    def add_artifact(
        self, run_id: str, invocation_id: str, kind: str, path: str, digest: str
    ) -> None:
        with self.connection:
            self.connection.execute(
                """INSERT OR REPLACE INTO artifacts
                   (run_id, invocation_id, kind, path, digest, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (run_id, invocation_id, kind, path, digest, utc_now()),
            )

    def get_receipt(self, key: str) -> Receipt | None:
        row = self.connection.execute(
            "SELECT * FROM receipts WHERE project_id=? AND idempotency_key=?",
            (self.project_id, key),
        ).fetchone()
        if row is None:
            return None
        return Receipt(
            kind=row["kind"],
            idempotency_key=row["idempotency_key"],
            external_id=row["external_id"],
            verified=True,
            payload=json.loads(row["payload_json"]),
        )

    def save_receipt(self, run_id: str, receipt: Receipt) -> None:
        if not receipt.verified:
            raise ValueError("cannot persist an unverified receipt")
        with self.connection:
            self.connection.execute(
                """INSERT OR IGNORE INTO receipts
                   (project_id, idempotency_key, run_id, kind, external_id,
                    payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    self.project_id,
                    receipt.idempotency_key,
                    run_id,
                    receipt.kind,
                    receipt.external_id,
                    json.dumps(receipt.payload, sort_keys=True),
                    utc_now(),
                ),
            )

    def add_rework(
        self,
        run_id: str,
        ticket_id: str,
        ticket_revision: str,
        source_role: str,
        invocation_id: str,
    ) -> int:
        row = self.connection.execute(
            """SELECT COALESCE(MAX(sequence), 0) FROM rework_events
               WHERE run_id=? AND ticket_id=? AND ticket_revision=?""",
            (run_id, ticket_id, ticket_revision),
        ).fetchone()
        sequence = int(row[0]) + 1
        with self.connection:
            self.connection.execute(
                """INSERT INTO rework_events VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    ticket_id,
                    ticket_revision,
                    sequence,
                    source_role,
                    invocation_id,
                    utc_now(),
                ),
            )
        return sequence

    def rework_count(self, run_id: str, ticket_id: str, ticket_revision: str) -> int:
        row = self.connection.execute(
            """SELECT COUNT(*) FROM rework_events
               WHERE run_id=? AND ticket_id=? AND ticket_revision=?""",
            (run_id, ticket_id, ticket_revision),
        ).fetchone()
        return int(row[0])

    def record_decision(self, run_id: str, gate: str, decision: dict[str, Any]) -> None:
        row = self.connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) FROM human_decisions WHERE run_id=?",
            (run_id,),
        ).fetchone()
        with self.connection:
            self.connection.execute(
                "INSERT INTO human_decisions VALUES (?, ?, ?, ?, ?)",
                (run_id, int(row[0]) + 1, gate, json.dumps(decision, sort_keys=True), utc_now()),
            )

    def save_mapping(
        self, local_id: str, external_id: str, revision: str, payload: dict[str, Any]
    ) -> None:
        with self.connection:
            self.connection.execute(
                """INSERT INTO mappings VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(project_id, local_id) DO UPDATE SET
                     external_id=excluded.external_id,
                     revision=excluded.revision,
                     payload_json=excluded.payload_json,
                     updated_at=excluded.updated_at""",
                (
                    self.project_id,
                    local_id,
                    external_id,
                    revision,
                    json.dumps(payload, sort_keys=True),
                    utc_now(),
                ),
            )

    def get_mapping(self, local_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM mappings WHERE project_id=? AND local_id=?",
            (self.project_id, local_id),
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["payload"] = json.loads(result.pop("payload_json"))
        return result

    def record_error(
        self, run_id: str | None, invocation_id: str | None, code: str, message: str
    ) -> None:
        with self.connection:
            self.connection.execute(
                """INSERT INTO errors(run_id, invocation_id, code, message, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (run_id, invocation_id, code, message, utc_now()),
            )

    def summary(self, run_id: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        invocations = [
            dict(row)
            for row in self.connection.execute(
                "SELECT * FROM invocations WHERE run_id=? ORDER BY created_at", (run_id,)
            )
        ]
        receipts = [
            dict(row)
            for row in self.connection.execute(
                "SELECT * FROM receipts WHERE run_id=? ORDER BY created_at", (run_id,)
            )
        ]
        rework = [
            dict(row)
            for row in self.connection.execute(
                "SELECT * FROM rework_events WHERE run_id=? ORDER BY created_at", (run_id,)
            )
        ]
        decisions = [
            dict(row)
            for row in self.connection.execute(
                "SELECT * FROM human_decisions WHERE run_id=? ORDER BY sequence", (run_id,)
            )
        ]
        return {"run": run, "invocations": invocations, "receipts": receipts, "rework": rework, "decisions": decisions}


def find_run_database(state_root: Path, run_id: str) -> tuple[Path, str]:
    matches: list[tuple[Path, str]] = []
    for database in state_root.expanduser().resolve().glob("*/controller.sqlite3"):
        connection = sqlite3.connect(database)
        try:
            row = connection.execute(
                "SELECT project_id FROM runs WHERE run_id=?", (run_id,)
            ).fetchone()
            if row:
                matches.append((database, str(row[0])))
        finally:
            connection.close()
    if len(matches) != 1:
        raise KeyError(f"run {run_id!r} resolved to {len(matches)} project databases")
    return matches[0]
