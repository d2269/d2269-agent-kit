# AD-001: Deterministic Lifecycle Controller Runtime

- Status: `ACCEPTED`
- Decision owner: Repository owner
- Authority / status evidence: Explicit scope expansion and accepted decisions in the 2026-09-19 implementation request
- Date: 2026-09-19
- Supersedes: N/A
- Superseded by: N/A

## Context

- Objective: automate the accepted development lifecycle through Herdr and
  Linear without turning a reasoning role into a workflow engine.
- Verified facts: the repository previously shipped role contracts only; Herdr
  0.9.0 exposes JSON CLI operations for workspaces, worktrees, panes, and agents;
  Linear exposes the required ticket, comment, issue-update, and child-issue
  operations through GraphQL.
- Constraints: one shared controller, sequential tickets per project, project
  isolation, fresh role sessions, exact revisions, durable recovery,
  idempotent mutations, and mandatory human gates.
- Assumptions: a controlled Linear team provides the configured workflow states
  and a supported coding agent is installed for Herdr.

## Decision

Implement one stdlib-only Python controller with a shared deterministic engine,
SQLite project state, a narrow provider-neutral `TrackerPort`, one production
Linear GraphQL adapter, one Herdr CLI runner, and Git worktree isolation.

Roles return one versioned JSON envelope plus their canonical Markdown reports.
Automated roles return `READY_TO_POST`; only the controller publishes comments
and performs permitted tracker transitions. Herdr lifecycle state is never a
semantic success verdict. Every project is isolated below
`state_root/<project_id>`, and every invocation uses a fresh agent session.

## Material Alternatives

| Alternative | Trade-offs | Disposition |
| --- | --- | --- |
| Encode the lifecycle in Orchestrator instructions | Cannot provide durable locks, exact-once recovery, or mutation receipts; violates role boundaries | Rejected |
| Use Herdr socket API directly | Duplicates the documented CLI wrapper surface without a current requirement | Rejected |
| Add a daemon, webhook server, broker, or distributed queue | Adds operational components while workflows are human-started and sequential | Rejected |
| Use one controller with SQLite and CLI adapters | Satisfies current reliability and portability needs with the fewest boundaries | Accepted |

## Consequences

- Benefits: one auditable state machine, deterministic recovery, minimal
  dependencies, isolated role contexts, explicit human gates, and a replaceable
  tracker mechanism without a generic Kanban framework.
- Costs and limitations: local single-project serialization, POSIX `fcntl`
  locking in version 0.1, operator-managed worktree cleanup, and a small
  remaining compare/read/update race because Linear issue updates do not expose
  atomic compare-and-set semantics.
- Compatibility and migration impact: existing role skills remain canonical and
  unchanged; existing users can continue to invoke them manually.
- Operational impact: operators configure one JSON file, provide credentials by
  environment, start runs explicitly, and inspect SQLite-backed status.

## Validation

- Evidence required to mark this decision `IMPLEMENTED`: all controller and
  existing repository tests pass; demonstrations verify state and receipts; a
  controlled live Herdr/Linear pilot verifies command responses, permissions,
  exact workflow mapping, and crash recovery without production data.
- Relevant tests: `python3 -m unittest discover -s controller/tests -t . -v`,
  `python3 scripts/demo_controller.py`, and the repository validation commands.

## References

- [`docs/controller.md`](../controller.md)
- [`docs/architecture.md`](../architecture.md)
- [`docs/lifecycle-role-contracts.md`](../lifecycle-role-contracts.md)
- [Herdr agent automation](https://herdr.dev/docs/agent-automation/)
- [Linear GraphQL](https://linear.app/developers/graphql)
