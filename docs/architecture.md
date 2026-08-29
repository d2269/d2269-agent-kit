# Architecture

D2269 Agent Kit is an **agent engineering toolkit**: reusable role skills, structured handoffs, validation, and platform adapters. It is not a prompt pack and not a development lifecycle engine.

## Canonical source

`skills/` is the only source of truth for custom skills. Adapters install, copy, or link those directories into agent-specific locations. Do not maintain edited forks for Cursor, Codex, Claude, or Herdr.

## Two kinds of logic

| Kind | Belongs in | Examples |
| --- | --- | --- |
| Agent reasoning | Skills | Architecture, planning, implementation judgment, QA reasoning, research, review, documentation, escalation analysis, structured handoffs |
| Deterministic automation | Software (later) | Retry counters, locks, queues, polling, webhooks, status mutation, worktrees, process supervision, timeouts, persistent workflow state, model selection, quota, schedulers |

Never encode a state machine in natural language when it can be implemented as code. Version 0.1 ships reasoning skills plus a skill validator and a conservative installer. It does not ship a controller.

## Role skills vs workflow

The eight initial skills define **role boundaries and output contracts** for a
lifecycle that may later look like:

Researcher -> Architect `DESIGN` -> Tech Lead -> Developer -> Code Review -> QA
-> policy-defined next gate or `Done`. At scope completion, policy may require
Tech Lead `COMPLETENESS_REVIEW`; consequential scope then proceeds to Architect
`CONFORMANCE_REVIEW` before human merge.

Architect `ESCALATION_REVIEW` is an evidence-driven exception during execution,
not a mandatory gate for every ticket. Architect produces the minimal durable
architecture baseline and semantic decision records. Technical Documentation is
a cross-cutting capability for audience-focused documentation and may publish or
synchronize architecture records without changing their technical meaning.
The three Architect stages are separate invocations. Conformance establishes its
verdict before synchronizing supported architecture records or producing
file-ready close-out changes.

Tech Lead converts accepted architecture workstreams and requirements into a
traceable implementation plan and spec-driven child tasks. These artifacts are
tracker-ready. Tech Lead may publish the validated artifacts through an
available connector when the user or applicable policy explicitly authorizes
mutation and names the target. The connector is not another reasoning role: it
owns authentication, idempotency, retries, API errors, and durable external
state, while Tech Lead owns task content, hierarchy, and dependencies. A bundled
[universal capability contract](../skills/tech-lead/references/tracker-connector-contract.md)
normalizes required operations and receipts without hardcoding a provider API.

Each Developer invocation consumes one child ticket assigned to Developer whose
implementation readiness is `READY`; this semantic field is distinct from tracker
workflow state. The ticket is the sole work contract and embeds or authoritatively
links required inputs;
repository evidence and ticket comments provide context without becoming
parallel work orders. Every final Developer result produces a ticket-history
comment. Developer publishes it through an available provider-neutral connector
when explicitly authorized; otherwise a controller or human publishes the
ready-to-post text before routing. Scope-changing comments require an authorized
ticket revision before implementation continues.

Developer never changes tracker workflow state. A future deterministic controller
or human workflow owner validates the implementation artifact and performs any
authorized transition to Code Review.

Code Review independently judges the same ticket's exact `COMPLETE`
implementation revision for engineering soundness in a reviewer context that did
not implement it. It produces an evidenced verdict and mandatory ticket-history
comment but never fixes the code or changes tracker state. A matching `PASS`
admits that revision to QA; an authoritative contract source may record an
explicit workflow-policy waiver bound to the current ticket revision. A comment
cannot create the waiver. Any later implementation change invalidates the
earlier review for QA entry.

QA then evaluates that same single ticket as the sole acceptance contract after a
matching Code Review `PASS` or authorized waiver. The implementation and review
reports are evidence, not additional work orders. QA owns the semantic verdict,
findings, ticket-comment content, and requested next action, but never modifies
implementation files or tracker workflow state. A ticket-history comment is
mandatory for every verdict and distinguishes passed, failed, and unverified
checks. A controller or human workflow owner publishes ready-to-post feedback
before routing, and advances `PASS` work to the next policy-defined gate or
`Done` only when QA is terminal for that ticket.

That diagram shapes the skills. It is not implemented. Orchestrator is a reasoning policy for ambiguous routing, not a process manager.

The diagram is the consequential-scope path, not a requirement to invoke every
role for every request. [Execution profiles](execution-profiles.md) define
proportional routes ranging from one bounded Researcher investigation through
lean and standard ticket delivery to the full scope lifecycle. Profiles do not
change role authority or implement control flow. The human or authoritative
workflow policy selects a profile; deterministic software eventually performs
the selected routing.

Future orchestration should consume the same handoff documents. Adding a controller later must not require renaming skills or splitting `skills/` by platform.

### Future lifecycle controller boundary

A future deterministic controller owns happy-path routing, durable tracker
transitions, and a rework counter scoped to the current ticket-contract revision.
The limit is workflow policy—three completed return events is a reasonable
initial setting, not role logic. At the configured limit the controller pauses
the ticket and invokes Tech Lead `BLOCKER_REVIEW` with the ticket history,
comments, role outputs, return events, and current revision evidence. A material
blocker may trigger the same review immediately without waiting for the limit.

Every `BLOCKER_REVIEW` result enters `HUMAN_REVIEW_REQUIRED`. Tech Lead provides
the diagnosis, proposed resolution, impact, alternatives, and recommended next
role; it does not authorize its own proposal. The controller must not resume the
ticket, publish revised work, invoke Architect, or perform another lifecycle
transition until it records the human decision. The human may resume the ticket,
require revised decomposition or additional project steps, request Architect or
other investigation, or choose another action.

Role-session runners are replaceable mechanisms behind the controller. Tools
such as Herdr or Conductor may launch isolated role sessions, but they do not own
the lifecycle policy, technical classification, or human decision gate.

## Repository layout

```text
skills/          Canonical, self-contained Agent Skills with bundled assets
docs/            Human and agent documentation for this toolkit
scripts/         Deterministic tools (validate, install)
adapters/        Platform notes and installer entry points
```

Optional skill subdirectories (`references/`, `scripts/`, `assets/`) are created only when they carry real content.

There is deliberately no top-level `templates/` directory. Output skeletons live in the owning skill's `assets/` directory. Keeping package dependencies inside the skill root makes copy and symlink installations portable; repository-level docs are not runtime dependencies.

## Extensibility

Safe to add later without restructuring:

- Additional references or scripts inside an existing skill
- New non-overlapping skills that pass the test in `AGENTS.md`
- Deterministic packages beside `scripts/` (for example a future controller)
- Adapter destinations as official docs confirm them
- Authorized tracker publication that serializes existing bundled handoff assets
  through an externally supplied connector conforming to the universal
  capability contract

Unsafe without an explicit redesign:

- Platform-specific forks of `skills/`
- Role instructions that implement tracker retry or lifecycle state machines,
  spawn agents, or infer external mutation authority
- Model-to-role assignment inside skills
- Overlapping skills (`dev`, `implementation-plan`, `reviewer`, `debugging`, and similar)

## Adapters

Adapters are thin. They map this repository onto verified discovery paths. They must not rewrite skill bodies. If a platform path is not verified against current official documentation, the adapter documents a TODO and the installer refuses that target.

## Version 0.1 non-goals

A bundled Linear or Kanban connector, Developer→Code Review→QA automation, retry loops, queues,
schedulers, worktree control, Herdr daemons, manager agents, automatic model
routing, quota management, CI deployment, and model benchmarks are out of scope.
