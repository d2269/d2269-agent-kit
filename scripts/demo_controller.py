#!/usr/bin/env python3
"""Credential-free controller demonstrations with state and receipt assertions."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from controller.engine import LifecycleController
from controller.state import StateStore
from controller.tests.fakes import (
    FakeRunner,
    FakeTracker,
    FakeWorktrees,
    blocker,
    config,
    dev,
    qa,
    review,
    ticket,
)


def build(root: Path, project_id: str, specs: list[dict], rework_limit: int = 3):
    cfg = config(root, project_id, rework_limit)
    store = StateStore(cfg.state_root, cfg.project_id)
    tracker = FakeTracker([ticket()])
    worktrees = FakeWorktrees(root / "worktrees" / project_id)
    runner = FakeRunner(specs, worktrees, tracker)
    controller = LifecycleController(
        cfg, store, tracker, runner, worktrees, mutations_authorized=True
    )
    return controller, store


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        standard, standard_store = build(
            root, "demo-standard", [dev(), review(), qa()]
        )
        standard_run = standard.start("standard", ticket_id="ABC-1")
        standard_summary = standard_store.summary(standard_run)
        assert standard_summary["run"]["lifecycle_state"] == "COMPLETED"
        assert len(standard_summary["receipts"]) == 7

        rework_specs = [
            dev("git:one"),
            review("CHANGES_REQUESTED"),
            dev("git:two"),
            review("CHANGES_REQUESTED"),
            dev("git:three"),
            review("CHANGES_REQUESTED"),
            blocker(),
        ]
        rework, rework_store = build(root, "demo-rework", rework_specs)
        rework_run = rework.start("standard", ticket_id="ABC-1")
        rework_summary = rework_store.summary(rework_run)
        assert rework_summary["run"]["lifecycle_state"] == "HUMAN_REVIEW_REQUIRED"
        assert len(rework_summary["rework"]) == 3
        assert any(row["kind"] == "comment" for row in rework_summary["receipts"])
        assert any(row["kind"] == "transition" for row in rework_summary["receipts"])

        print(
            json.dumps(
                {
                    "standard": {
                        "state": standard_summary["run"]["lifecycle_state"],
                        "invocations": [row["role"] for row in standard_summary["invocations"]],
                        "receipt_count": len(standard_summary["receipts"]),
                    },
                    "three_returns": {
                        "state": rework_summary["run"]["lifecycle_state"],
                        "rework_count": len(rework_summary["rework"]),
                        "last_role": rework_summary["invocations"][-1]["role"],
                        "receipt_count": len(rework_summary["receipts"]),
                    },
                    "external_mutations": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        standard_store.close()
        rework_store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
