from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from controller.engine import LifecycleController, SafeStop
from controller.herdr import HerdrRunner, RunnerError
from controller.linear import LinearTracker
from controller.models import ExecutionContext, InvocationRequest, ROLE_SKILL_NAMES
from controller.state import StateStore
from controller.tracker import TrackerError, TrackerPreconditionError

from .fakes import (
    FakeRunner,
    FakeTracker,
    FakeWorktrees,
    SimulatedProcessCrash,
    blocker,
    completeness,
    config,
    conformance,
    design,
    dev,
    plan,
    qa,
    review,
    ticket,
)


class ControllerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def controller(
        self,
        tickets,
        specs,
        *,
        project_id="project",
        rework_limit=3,
        partial_policy="stop",
        authorized_minimal_waivers=None,
    ):
        cfg = config(
            self.root,
            project_id,
            rework_limit,
            partial_policy,
            authorized_minimal_waivers,
        )
        store = StateStore(cfg.state_root, cfg.project_id)
        self.addCleanup(store.close)
        tracker = FakeTracker(tickets)
        worktrees = FakeWorktrees(self.root / "worktrees" / project_id)
        runner = FakeRunner(specs, worktrees, tracker)
        controller = LifecycleController(
            cfg, store, tracker, runner, worktrees, mutations_authorized=True
        )
        return controller, store, tracker, worktrees, runner

    def state(self, store, run_id):
        return store.get_run(run_id)["lifecycle_state"]

    def test_01_minimal_success_with_waiver(self):
        authority = {
            "policy": "test-policy",
            "authorized_owner": "owner",
            "authoritative_source": "ticket-contract",
        }
        controller, store, tracker, _worktrees, _runner = self.controller(
            [ticket(waiver=True)],
            [dev(action="SEND_TO_QA"), qa()],
            authorized_minimal_waivers=[authority],
        )
        run_id = controller.start("minimal", ticket_id="ABC-1")
        self.assertEqual(self.state(store, run_id), "COMPLETED")
        self.assertEqual(tracker.tickets["ABC-1"].state, "Done")

    def test_02_minimal_refuses_missing_waiver(self):
        controller, _store, tracker, _worktrees, runner = self.controller([ticket()], [])
        with self.assertRaises(ValueError):
            controller.dry_run("minimal", ticket_id="ABC-1", scope_path=None)
        self.assertEqual(tracker.mutation_calls, 0)
        self.assertEqual(runner.calls, 0)

    def test_03_standard_success(self):
        controller, store, tracker, _worktrees, _runner = self.controller(
            [ticket()], [dev(), review(), qa()]
        )
        run_id = controller.start("standard", ticket_id="ABC-1")
        self.assertEqual(self.state(store, run_id), "COMPLETED")
        self.assertEqual(tracker.tickets["ABC-1"].state, "Done")

    def test_04_code_review_changes_return_to_developer(self):
        specs = [dev("git:one"), review("CHANGES_REQUESTED"), dev("git:two"), review(), qa()]
        controller, store, _tracker, _worktrees, _runner = self.controller([ticket()], specs)
        run_id = controller.start("standard", ticket_id="ABC-1")
        self.assertEqual(self.state(store, run_id), "COMPLETED")
        self.assertEqual(len(store.summary(run_id)["rework"]), 1)

    def test_05_qa_changes_return_to_developer(self):
        specs = [dev("git:one"), review(), qa("CHANGES_REQUESTED"), dev("git:two"), review(), qa()]
        controller, store, _tracker, _worktrees, _runner = self.controller([ticket()], specs)
        run_id = controller.start("standard", ticket_id="ABC-1")
        self.assertEqual(self.state(store, run_id), "COMPLETED")
        self.assertEqual(len(store.summary(run_id)["rework"]), 1)

    def test_06_rework_limit_triggers_blocker_review(self):
        specs = [
            dev("git:one"), review("CHANGES_REQUESTED"),
            dev("git:two"), review("CHANGES_REQUESTED"),
            dev("git:three"), review("CHANGES_REQUESTED"), blocker(),
        ]
        controller, store, _tracker, _worktrees, _runner = self.controller(
            [ticket()], specs, rework_limit=3
        )
        run_id = controller.start("standard", ticket_id="ABC-1")
        self.assertEqual(self.state(store, run_id), "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(len(store.summary(run_id)["rework"]), 3)

    def test_07_developer_blocked_requires_human_review(self):
        controller, store, _tracker, _worktrees, _runner = self.controller(
            [ticket()], [dev(result="BLOCKED", revision="git:base"), blocker()]
        )
        run_id = controller.start("standard", ticket_id="ABC-1")
        self.assertEqual(self.state(store, run_id), "HUMAN_REVIEW_REQUIRED")

    def test_08_cannot_resume_without_human_decision(self):
        controller, store, _tracker, _worktrees, _runner = self.controller(
            [ticket()], [dev(result="BLOCKED", revision="git:base"), blocker()]
        )
        run_id = controller.start("standard", ticket_id="ABC-1")
        with self.assertRaises(SafeStop):
            controller.resume(run_id)
        self.assertEqual(self.state(store, run_id), "HUMAN_REVIEW_REQUIRED")

    def test_09_stale_ticket_revision_stops(self):
        controller, store, _tracker, _worktrees, _runner = self.controller(
            [ticket()], [dev(ticket_revision_after="ticket-r2")]
        )
        run_id = controller.start("standard", ticket_id="ABC-1")
        self.assertEqual(self.state(store, run_id), "STALE_TICKET_REVISION")

    def test_10_implementation_change_after_review_invalidates_verdict(self):
        controller, store, _tracker, _worktrees, _runner = self.controller(
            [ticket()], [dev(), review(implementation_revision_after="git:changed")]
        )
        run_id = controller.start("standard", ticket_id="ABC-1")
        self.assertEqual(self.state(store, run_id), "IMPLEMENTATION_CHANGED")

    def test_11_missing_required_comment_stops(self):
        controller, store, _tracker, _worktrees, _runner = self.controller(
            [ticket()], [dev(omit_comment=True)]
        )
        run_id = controller.start("standard", ticket_id="ABC-1")
        self.assertEqual(self.state(store, run_id), "MISSING_ARTIFACT")

    def test_12_duplicate_comment_and_transition_replay(self):
        controller, store, tracker, _worktrees, runner = self.controller(
            [ticket()], [dev(), review(), qa()]
        )
        original_save = store.save_receipt
        crashed = False

        def crash_after_comment(run_id, receipt):
            nonlocal crashed
            if receipt.kind == "comment" and not crashed:
                crashed = True
                raise SimulatedProcessCrash("crash after external comment creation")
            return original_save(run_id, receipt)

        with mock.patch.object(store, "save_receipt", side_effect=crash_after_comment):
            with self.assertRaises(SimulatedProcessCrash):
                controller.start("standard", ticket_id="ABC-1")
        run_id = store.find_active("ticket", "ABC-1")
        self.assertIsNotNone(run_id)
        controller.start("standard", ticket_id="ABC-1")
        self.assertEqual(len(tracker.comments), 3)
        self.assertEqual(len(tracker.transitions), 4)
        self.assertEqual(runner.calls, 3)
        self.assertEqual(len(store.summary(run_id)["receipts"]), 7)

    def test_13_herdr_blocked_safe_stop(self):
        controller, store, _tracker, _worktrees, _runner = self.controller(
            [ticket()], [{"role": "developer", "error": "blocked"}]
        )
        run_id = controller.start("standard", ticket_id="ABC-1")
        self.assertEqual(self.state(store, run_id), "HERDR_BLOCKED")

    def test_14_herdr_unknown_safe_stop(self):
        controller, store, _tracker, _worktrees, _runner = self.controller(
            [ticket()], [{"role": "developer", "error": "unknown"}]
        )
        run_id = controller.start("standard", ticket_id="ABC-1")
        self.assertEqual(self.state(store, run_id), "HERDR_UNKNOWN")

    def test_15_timeout_after_possible_prompt_submission_is_uncertain(self):
        controller, store, _tracker, _worktrees, _runner = self.controller(
            [ticket()], [{"role": "developer", "error": "timeout"}, dev(), review(), qa()]
        )
        run_id = controller.start("standard", ticket_id="ABC-1")
        self.assertEqual(self.state(store, run_id), "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(store.get_run(run_id)["data"]["stop_reason"], "HERDR_TIMEOUT_UNCERTAIN")
        with self.assertRaises(SafeStop):
            controller.resume(run_id)
        self.assertEqual(_runner.calls, 1)
        controller.decide(
            run_id,
            {"action": "CONFIRM_PROMPT_NOT_ACCEPTED_RETRY", "owner": "human"},
        )
        self.assertEqual(self.state(store, run_id), "COMPLETED")

    def test_16_crash_recovery_continues_without_duplicate_tracker_effects(self):
        controller, store, tracker, _worktrees, runner = self.controller(
            [ticket()], [{**dev(), "error": "crash_after_result"}, review(), qa()]
        )
        with self.assertRaises(SimulatedProcessCrash):
            controller.start("standard", ticket_id="ABC-1")
        run_id = store.find_active("ticket", "ABC-1")
        self.assertIsNotNone(run_id)
        recovered_run = controller.start("standard", ticket_id="ABC-1")
        self.assertEqual(recovered_run, run_id)
        self.assertEqual(self.state(store, run_id), "COMPLETED")
        self.assertEqual(len(tracker.comments), 3)
        self.assertEqual(runner.calls, 3)

    def test_17_two_projects_are_isolated_with_same_ticket_id(self):
        first, first_store, first_tracker, *_ = self.controller(
            [ticket()], [dev(), review(), qa()], project_id="one"
        )
        second, second_store, second_tracker, *_ = self.controller(
            [ticket()], [dev(), review(), qa()], project_id="two"
        )
        first_run = first.start("standard", ticket_id="ABC-1")
        second_run = second.start("standard", ticket_id="ABC-1")
        self.assertNotEqual(first_store.database_path, second_store.database_path)
        self.assertNotEqual(first_run, second_run)
        self.assertEqual(first_tracker.tickets["ABC-1"].state, "Done")
        self.assertEqual(second_tracker.tickets["ABC-1"].state, "Done")

    def test_18_planned_scope_reaches_human_closeout(self):
        scope = self.root / "scope.json"
        scope.write_text("{}", encoding="utf-8")
        payload = {
            "plan_id": "SCOPE-PLAN",
            "revision": "plan-r1",
            "title": "Scope plan",
            "description": "Validated implementation plan",
            "tickets": [{"local_id": "T1", "title": "Child", "description": "Work", "contract": {"implementation_readiness": "READY", "delivery_profile": "standard"}}],
        }
        controller, store, tracker, _worktrees, _runner = self.controller(
            [], [plan(payload), dev(), review(), qa(), completeness()]
        )
        run_id = controller.start("planned", scope_path=scope)
        self.assertEqual(self.state(store, run_id), "HUMAN_REVIEW_REQUIRED")
        self.assertIn("PLAN-1", tracker.tickets)

    def test_19_consequential_scope_acceptance_and_conformance(self):
        scope = self.root / "scope.json"
        scope.write_text("{}", encoding="utf-8")
        payload = {
            "plan_id": "SCOPE-PLAN",
            "revision": "plan-r1",
            "title": "Scope plan",
            "description": "Validated implementation plan",
            "tickets": [{"local_id": "T1", "title": "Child", "description": "Work", "contract": {"implementation_readiness": "READY", "delivery_profile": "standard"}}],
        }
        specs = [design(), plan(payload), dev(), review(), qa(), completeness("SEND_TO_CONFORMANCE"), conformance()]
        controller, store, _tracker, _worktrees, _runner = self.controller([], specs)
        run_id = controller.start("consequential", scope_path=scope)
        self.assertEqual(self.state(store, run_id), "HUMAN_REVIEW_REQUIRED")
        controller.decide(run_id, {"action": "ACCEPT_ARCHITECTURE", "owner": "human"})
        self.assertEqual(self.state(store, run_id), "HUMAN_REVIEW_REQUIRED")
        controller.decide(run_id, {"action": "CLOSE_SCOPE", "owner": "human"})
        self.assertEqual(self.state(store, run_id), "COMPLETED")

    def test_20_linear_http_200_graphql_errors_are_failure(self):
        response = mock.MagicMock()
        response.read.return_value = json.dumps({"data": {"issue": None}, "errors": [{"message": "denied"}]}).encode()
        response.__enter__.return_value = response
        with mock.patch.dict("os.environ", {"LINEAR_API_KEY": "secret"}), mock.patch(
            "urllib.request.urlopen", return_value=response
        ):
            tracker = LinearTracker(
                {"team_id": "team", "controller_project_id": "project", "status_mapping": {key: value for key, value in __import__("controller.tests.fakes", fromlist=["STATUS"]).STATUS.items()}},
                mutations_authorized=False,
            )
            with self.assertRaises(TrackerError):
                tracker.get_ticket("ABC-1")

    def test_21_tracker_receipt_mismatch_stops(self):
        controller, store, tracker, _worktrees, _runner = self.controller([ticket()], [dev()])
        tracker.receipt_valid = False
        run_id = controller.start("standard", ticket_id="ABC-1")
        self.assertEqual(self.state(store, run_id), "RECEIPT_MISMATCH")

    def test_22_dry_run_has_no_mutations_or_agent_invocations(self):
        controller, _store, tracker, _worktrees, runner = self.controller([ticket()], [])
        result = controller.dry_run("standard", ticket_id="ABC-1", scope_path=None)
        self.assertTrue(result["dry_run"])
        self.assertEqual(tracker.mutation_calls, 0)
        self.assertEqual(runner.calls, 0)

    def test_23_safe_stop_does_not_implicitly_relaunch_role(self):
        controller, store, _tracker, _worktrees, runner = self.controller(
            [ticket()], [{"role": "developer", "error": "blocked"}, dev()]
        )
        run_id = controller.start("standard", ticket_id="ABC-1")
        controller.resume(run_id)
        self.assertEqual(self.state(store, run_id), "HERDR_BLOCKED")
        self.assertEqual(runner.calls, 1)

    def test_24_partial_continue_policy_reinvokes_developer(self):
        controller, store, _tracker, _worktrees, runner = self.controller(
            [ticket()],
            [
                dev(result="PARTIAL", action="CONTINUE_DEVELOPER"),
                dev(),
                review(),
                qa(),
            ],
            partial_policy="continue",
        )
        run_id = controller.start("standard", ticket_id="ABC-1")
        self.assertEqual(self.state(store, run_id), "COMPLETED")
        self.assertEqual(runner.calls, 4)

    def test_25_modified_review_context_invalidates_verdict(self):
        controller, store, _tracker, _worktrees, _runner = self.controller(
            [ticket()], [dev(), review(context_revision_after="git:tampered")]
        )
        run_id = controller.start("standard", ticket_id="ABC-1")
        self.assertEqual(self.state(store, run_id), "REVIEW_CONTEXT_CHANGED")

    def test_26_crash_without_result_requires_explicit_retry_decision(self):
        controller, store, _tracker, _worktrees, runner = self.controller(
            [ticket()],
            [
                {"role": "developer", "error": "crash_before_result"},
                dev(),
                review(),
                qa(),
            ],
        )
        with self.assertRaises(SimulatedProcessCrash):
            controller.start("standard", ticket_id="ABC-1")
        run_id = store.find_active("ticket", "ABC-1")
        self.assertIsNotNone(run_id)
        controller.resume(run_id)
        self.assertEqual(self.state(store, run_id), "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(runner.calls, 1)
        controller.decide(
            run_id,
            {"action": "CONFIRM_PROMPT_NOT_ACCEPTED_RETRY", "owner": "human"},
        )
        self.assertEqual(self.state(store, run_id), "COMPLETED")

    def test_27_configuration_snapshot_change_stops_resume(self):
        controller, store, _tracker, _worktrees, runner = self.controller(
            [ticket()], [{"role": "developer", "error": "blocked"}]
        )
        run_id = controller.start("standard", ticket_id="ABC-1")
        controller.config.policy["rework_limit"] = 99
        controller.resume(run_id)
        self.assertEqual(self.state(store, run_id), "CONFIG_CHANGED")
        self.assertEqual(runner.calls, 1)

    def test_28_project_lock_covers_run_creation(self):
        controller, store, _tracker, _worktrees, _runner = self.controller(
            [ticket()], [dev(), review(), qa()]
        )
        with store.lock(), self.assertRaises(RuntimeError):
            controller.start("standard", ticket_id="ABC-1")
        self.assertIsNone(store.find_active("ticket", "ABC-1"))

    def test_29_planned_minimal_requires_configured_waiver_authority(self):
        scope = self.root / "scope-minimal.json"
        scope.write_text("{}", encoding="utf-8")
        authority = {
            "policy": "test-policy",
            "authorized_owner": "owner",
            "authoritative_source": "ticket-contract",
        }
        contract = {
            "implementation_readiness": "READY",
            "delivery_profile": "minimal",
            "ticket_revision": "ticket-r1",
            "code_review_waiver": {
                "ticket_revision": "ticket-r1",
                "implementation_revision": "git:one",
                **authority,
            },
        }
        payload = {
            "plan_id": "MINIMAL-PLAN",
            "revision": "plan-r1",
            "title": "Minimal scope",
            "description": "Pre-authorized exact revision",
            "tickets": [
                {
                    "local_id": "T1",
                    "title": "Child",
                    "description": "Work",
                    "contract": contract,
                }
            ],
        }
        controller, store, _tracker, _worktrees, _runner = self.controller(
            [],
            [plan(payload), dev(action="SEND_TO_QA"), qa(), completeness()],
            authorized_minimal_waivers=[authority],
        )
        run_id = controller.start("planned", scope_path=scope)
        self.assertEqual(self.state(store, run_id), "HUMAN_REVIEW_REQUIRED")

    def test_30_safe_stop_can_retry_only_after_explicit_decision(self):
        controller, store, _tracker, _worktrees, runner = self.controller(
            [ticket()],
            [{"role": "developer", "error": "blocked"}, dev(), review(), qa()],
        )
        run_id = controller.start("standard", ticket_id="ABC-1")
        self.assertEqual(self.state(store, run_id), "HERDR_BLOCKED")
        controller.decide(run_id, {"action": "RETRY_ROLE", "owner": "human"})
        self.assertEqual(self.state(store, run_id), "COMPLETED")
        self.assertEqual(runner.calls, 4)

    def test_31_linear_plan_sync_refuses_intervening_human_edit(self):
        tracker = object.__new__(LinearTracker)
        tracker.team_id = "team"
        current = {
            "id": "issue",
            "identifier": "ABC-1",
            "title": "Human edit",
            "description": "Do not overwrite",
            "parent": None,
            "team": {"id": "team"},
        }
        tracker._issue_identity = mock.Mock(return_value=current)
        tracker._graphql = mock.Mock()
        prior_digest = tracker._content_digest("Old", "Old description", None)
        with self.assertRaises(TrackerPreconditionError):
            tracker._sync_issue(
                external_id="issue",
                mapping={"payload": {"content_sha256": prior_digest}},
                title="New plan",
                description="New description",
                parent_id=None,
                create_input={},
            )
        tracker._graphql.assert_not_called()

    def test_32_explicit_ticket_revision_is_still_content_bound(self):
        contract = {"ticket_revision": "declared-r1"}
        base = {
            "id": "issue",
            "title": "Title",
            "description": "Description",
            "labels": {"nodes": []},
            "parent": None,
        }
        first = LinearTracker._ticket_revision(base, contract)
        second = LinearTracker._ticket_revision(
            {**base, "description": "Changed description"}, contract
        )
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("linear-contract:declared-r1:"))

    def test_33_transition_replay_after_receipt_persistence_crash(self):
        controller, store, tracker, _worktrees, runner = self.controller(
            [ticket()], [dev(), review(), qa()]
        )
        original_save = store.save_receipt
        crashed = False

        def crash_after_transition(run_id, receipt):
            nonlocal crashed
            if receipt.kind == "transition" and not crashed:
                crashed = True
                raise SimulatedProcessCrash("crash after external state transition")
            return original_save(run_id, receipt)

        with mock.patch.object(store, "save_receipt", side_effect=crash_after_transition):
            with self.assertRaises(SimulatedProcessCrash):
                controller.start("standard", ticket_id="ABC-1")
        run_id = store.find_active("ticket", "ABC-1")
        self.assertIsNotNone(run_id)
        controller.start("standard", ticket_id="ABC-1")
        self.assertEqual(self.state(store, run_id), "COMPLETED")
        self.assertEqual(len(tracker.transitions), 4)
        self.assertEqual(len(tracker.comments), 3)
        self.assertEqual(runner.calls, 3)

    def test_34_code_review_blocked_stops_for_named_owner(self):
        controller, store, _tracker, _worktrees, runner = self.controller(
            [ticket()], [dev(), review("BLOCKED", next_owner="security-owner")]
        )
        run_id = controller.start("standard", ticket_id="ABC-1")
        run = store.get_run(run_id)
        self.assertEqual(run["lifecycle_state"], "BLOCKED")
        self.assertEqual(run["data"]["blocked_next_owner"], "security-owner")
        self.assertEqual(runner.calls, 2)

    def test_35_qa_blocked_stops_for_named_owner(self):
        controller, store, _tracker, _worktrees, runner = self.controller(
            [ticket()], [dev(), review(), qa("BLOCKED", next_owner="product-owner")]
        )
        run_id = controller.start("standard", ticket_id="ABC-1")
        run = store.get_run(run_id)
        self.assertEqual(run["lifecycle_state"], "BLOCKED")
        self.assertEqual(run["data"]["blocked_next_owner"], "product-owner")
        self.assertEqual(runner.calls, 3)

    def test_36_direct_minimal_rejects_unconfigured_waiver_authority(self):
        controller, _store, _tracker, _worktrees, _runner = self.controller(
            [ticket(waiver=True)], []
        )
        with self.assertRaises(ValueError):
            controller.start("minimal", ticket_id="ABC-1")

    def test_37_uncertain_comment_mutation_reuses_original_idempotency_key(self):
        controller, store, tracker, _worktrees, runner = self.controller(
            [ticket()], [dev(), review(), qa()]
        )
        original_publish = tracker.publish_comment
        failed_verification = False

        def publish_then_fail(ticket_value, body, idempotency_key):
            nonlocal failed_verification
            receipt = original_publish(ticket_value, body, idempotency_key)
            if not failed_verification:
                failed_verification = True
                raise TrackerError("verification response was unavailable")
            return receipt

        with mock.patch.object(
            tracker, "publish_comment", side_effect=publish_then_fail
        ):
            run_id = controller.start("standard", ticket_id="ABC-1")
            run = store.get_run(run_id)
            self.assertEqual(run["lifecycle_state"], "SAFE_STOP")
            self.assertEqual(
                run["data"]["human_gate"], "external_mutation_recovery"
            )
            controller.decide(
                run_id, {"action": "RETRY_MUTATION", "owner": "human"}
            )
        self.assertEqual(self.state(store, run_id), "COMPLETED")
        self.assertEqual(len(tracker.comments), 3)
        self.assertEqual(runner.calls, 3)

    def test_38_ticket_profile_blocker_cannot_replan(self):
        controller, store, _tracker, _worktrees, _runner = self.controller(
            [ticket()], [dev(result="BLOCKED", revision="git:base"), blocker()]
        )
        run_id = controller.start("standard", ticket_id="ABC-1")
        with self.assertRaises(ValueError):
            controller.decide(run_id, {"action": "REPLAN", "owner": "human"})
        self.assertEqual(self.state(store, run_id), "HUMAN_REVIEW_REQUIRED")

    def test_39_herdr_prompt_maps_role_id_to_namespaced_skill(self):
        request = InvocationRequest(
            run_id="run-1",
            invocation_id="invocation-1",
            project_id="project",
            role="developer",
            mode=None,
            ticket=ticket(),
            implementation_revision=None,
            context=ExecutionContext(self.root, None),
            report_path=self.root / "report.md",
            comment_path=self.root / "comment.md",
            envelope_path=self.root / "result.json",
            payload_path=None,
            extra_context={"allowed_results": ["COMPLETE"], "allowed_actions": {}},
        )

        prompt = HerdrRunner._prompt(request)

        self.assertIn("installed `d2269-developer` skill", prompt)
        self.assertNotIn("Use the `developer` skill", prompt)
        self.assertIn('"schema_version": "1"', prompt)
        self.assertIn('"role": "developer"', prompt)
        self.assertIn('"mode": null', prompt)
        self.assertIn("installed package name is not the protocol", prompt)
        self.assertIn("exact resulting Git revision for `COMPLETE`", prompt)
        controller_block = prompt.split("Contract:", 1)[0]
        self.assertNotIn('"implementation_revision":', controller_block)

    def test_40_herdr_prompt_maps_every_role_id_to_its_package(self):
        expected_mapping = {
            "architect": "d2269-architect",
            "tech-lead": "d2269-tech-lead",
            "developer": "d2269-developer",
            "code-review": "d2269-code-review",
            "qa": "d2269-qa",
            "researcher": "d2269-researcher",
            "technical-documentation": "d2269-technical-documentation",
            "orchestrator": "d2269-orchestrator",
        }
        self.assertEqual(ROLE_SKILL_NAMES, expected_mapping)

        for role, skill in expected_mapping.items():
            with self.subTest(role=role):
                request = InvocationRequest(
                    run_id="run-1",
                    invocation_id=f"invocation-{role}",
                    project_id="project",
                    role=role,
                    mode=None,
                    ticket=ticket(),
                    implementation_revision="git:reviewed",
                    context=ExecutionContext(self.root, "git:reviewed"),
                    report_path=self.root / f"{role}-report.md",
                    comment_path=self.root / f"{role}-comment.md",
                    envelope_path=self.root / f"{role}-result.json",
                    payload_path=None,
                )

                prompt = HerdrRunner._prompt(request)

                self.assertIn(f"installed `{skill}` skill", prompt)
                self.assertIn(f'"role": "{role}"', prompt)
                if role == "developer":
                    self.assertNotIn(
                        '"implementation_revision":',
                        prompt.split("Contract:", 1)[0],
                    )
                else:
                    self.assertIn(
                        '"implementation_revision": "git:reviewed"', prompt
                    )

    def test_41_scope_prompt_preserves_json_null_identity_values(self):
        request = InvocationRequest(
            run_id="run-1",
            invocation_id="invocation-architect",
            project_id="project",
            role="architect",
            mode="DESIGN",
            ticket=None,
            implementation_revision=None,
            context=ExecutionContext(self.root, None),
            report_path=self.root / "architect-report.md",
            comment_path=self.root / "architect-comment.md",
            envelope_path=self.root / "architect-result.json",
            payload_path=None,
        )

        prompt = HerdrRunner._prompt(request)

        self.assertIn('"mode": "DESIGN"', prompt)
        self.assertIn('"ticket_id": null', prompt)
        self.assertIn('"ticket_revision": null', prompt)
        self.assertIn('"implementation_revision": null', prompt)
        self.assertNotIn("Ticket ID: N/A", prompt)

    def test_42_herdr_prompt_rejects_unmapped_role(self):
        request = InvocationRequest(
            run_id="run-1",
            invocation_id="invocation-unknown",
            project_id="project",
            role="unknown-role",
            mode=None,
            ticket=ticket(),
            implementation_revision=None,
            context=ExecutionContext(self.root, None),
            report_path=self.root / "unknown-report.md",
            comment_path=self.root / "unknown-comment.md",
            envelope_path=self.root / "unknown-result.json",
            payload_path=None,
        )

        with self.assertRaisesRegex(
            RunnerError, "No installed skill mapping for role: unknown-role"
        ):
            HerdrRunner._prompt(request)


if __name__ == "__main__":
    unittest.main()
