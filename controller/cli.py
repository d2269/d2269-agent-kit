"""Command-line interface for the lifecycle controller."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from .config import ProjectConfig, load_config
from .engine import LifecycleController, SafeStop
from .git import GitWorktrees
from .herdr import HerdrRunner
from .linear import LinearTracker
from .state import StateStore, find_run_database


def _controller(config: ProjectConfig, *, mutations_authorized: bool) -> tuple[LifecycleController, StateStore]:
    store = StateStore(config.state_root, config.project_id)
    tracker = LinearTracker(
        {**config.tracker, "controller_project_id": config.project_id},
        mutations_authorized=mutations_authorized,
    )
    runner = HerdrRunner(config.repository, config.runner)
    worktrees = GitWorktrees(
        config.repository,
        store.project_dir,
        base_branch=config.git["base_branch"],
        branch_prefix=config.git["branch_prefix"],
    )
    return (
        LifecycleController(
            config,
            store,
            tracker,
            runner,
            worktrees,
            mutations_authorized=mutations_authorized,
        ),
        store,
    )


def _state_root(value: str | None) -> Path:
    raw = value or os.environ.get("D2269_CONTROLLER_STATE_ROOT")
    if not raw:
        raise ValueError("--state-root or D2269_CONTROLLER_STATE_ROOT is required")
    return Path(raw).expanduser().resolve()


def _config_for_run(state_root: Path, run_id: str) -> ProjectConfig:
    database, _project_id = find_run_database(state_root, run_id)
    connection = sqlite3.connect(database)
    try:
        row = connection.execute("SELECT project_path FROM runs WHERE run_id=?", (run_id,)).fetchone()
    finally:
        connection.close()
    if not row:
        raise ValueError(f"unknown run: {run_id}")
    return replace(load_config(Path(row[0])), state_root=state_root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="D2269 deterministic lifecycle controller")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="validate project configuration and local integrations")
    doctor.add_argument("--project", type=Path, required=True)

    run = sub.add_parser("run", help="start or recover a workflow run")
    run.add_argument("--project", type=Path, required=True)
    run.add_argument("--profile", choices=("minimal", "standard", "planned", "consequential"), required=True)
    target = run.add_mutually_exclusive_group(required=True)
    target.add_argument("--ticket")
    target.add_argument("--scope", type=Path)
    run.add_argument("--dry-run", action="store_true")
    run.add_argument(
        "--authorize-mutations",
        action="store_true",
        help="authorize controller-owned Linear comments, transitions, and plan publication for this run",
    )

    status = sub.add_parser("status", help="show durable run state")
    status.add_argument("--run", required=True)
    status.add_argument("--state-root")

    decide = sub.add_parser("decide", help="record a human decision and continue when permitted")
    decide.add_argument("--run", required=True)
    decide.add_argument("--decision-file", type=Path, required=True)
    decide.add_argument("--state-root")
    decide.add_argument("--authorize-mutations", action="store_true", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store: StateStore | None = None
    try:
        if args.command == "doctor":
            config = load_config(args.project)
            runner = HerdrRunner(config.repository, config.runner)
            token_env = config.tracker.get("token_env", "LINEAR_API_KEY")
            result = {
                "project_id": config.project_id,
                "repository": str(config.repository),
                "state_directory": str(config.state_root / config.project_id),
                "herdr": runner.doctor(),
                "linear_token_available": bool(os.environ.get(token_env)),
                "mutations_performed": False,
            }
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["linear_token_available"] else 1
        if args.command == "run":
            config = load_config(args.project)
            controller, store = _controller(config, mutations_authorized=args.authorize_mutations)
            if args.dry_run:
                result = controller.dry_run(args.profile, ticket_id=args.ticket, scope_path=args.scope)
                print(json.dumps(result, indent=2, sort_keys=True))
                return 0
            run_id = controller.start(args.profile, ticket_id=args.ticket, scope_path=args.scope)
            print(json.dumps(store.summary(run_id), indent=2, sort_keys=True))
            return 0
        state_root = _state_root(args.state_root)
        config = _config_for_run(state_root, args.run)
        if args.command == "status":
            store = StateStore(config.state_root, config.project_id)
            print(json.dumps(store.summary(args.run), indent=2, sort_keys=True))
            return 0
        decision = json.loads(args.decision_file.read_text(encoding="utf-8"))
        if not isinstance(decision, dict):
            raise ValueError("decision file must contain a JSON object")
        controller, store = _controller(config, mutations_authorized=args.authorize_mutations)
        controller.decide(args.run, decision)
        print(json.dumps(store.summary(args.run), indent=2, sort_keys=True))
        return 0
    except (ValueError, KeyError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    finally:
        if store is not None:
            store.close()
