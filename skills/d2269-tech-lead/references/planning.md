# Planning Mode

Use `PLAN` to convert a defined scope into an implementation plan and
spec-driven child tickets that fresh Developer sessions can execute as their sole
work contracts.

## Required context

- Objective, scope, non-goals, and unchanged product acceptance criteria
- System-level definition of done, accepted architecture decisions, Architect
  workstreams, and required verification evidence when applicable
- Existing code, tests, contracts, schemas, migrations, and documentation
- Repository conventions and relevant delivery constraints
- Authoritative delivery workflow policy and any permitted review-waiver authority
- Tracker field constraints when tracker-ready formatting is requested
- For requested publication: explicit mutation authority, named workspace or
  project and team as applicable, and an available authorized connector

If required product intent is contradictory, return `BLOCKED` with questions for
the human owner. If a required architecture decision is not `ACCEPTED`, a draft
may expose likely work, but affected tasks must remain non-ready and the next
action must target Architect or the decision owner.

## Procedure

1. Establish the verified implementation baseline and uninspected areas.
2. Set plan readiness to exactly one of:
   - `READY_FOR_IMPLEMENTATION`: all blocking requirements and decisions are
     bound and the task set is executable.
   - `DRAFT`: useful decomposition exists, but named prerequisites remain open.
   - `BLOCKED`: responsible decomposition is not possible from current inputs.
   Plan status and task readiness are distinct: a `DRAFT` plan may contain both
   `READY` and `BLOCKED` task specifications, but the plan itself is not ready
   for publication or implementation handoff.
3. Build a coverage map from every in-scope requirement, system-level completion
   condition, accepted decision, Architect workstream, and required verification
   item to an implementation outcome and verification evidence.
4. Decompose the outcomes into the smallest coherent tasks that can be understood
   and verified independently. Preserve cross-cutting atomicity when splitting
   would create unsafe intermediate states; document the reason and observable
   internal checkpoints for every larger atomic task.
5. Assign a stable plan ID and revision plus stable local task IDs. Start a new
   revision when task semantics, scope, readiness, dependencies, sequencing, or
   verification changes. Preserve local IDs for unchanged outcomes, identify the
   superseded revision, summarize the change, and record what the new revision
   was validated against. Formatting-only edits do not require a new revision.
   An external tracker may map stable local IDs to its own IDs.
6. For every task, define outcome, scope, non-goals, sources, dependencies,
   affected components and interfaces, constraints, technical completion
   criteria, verification, required post-implementation gates, any permitted Code
   Review waiver policy and authority, documentation or operational impact, and
   one exact Developer action. A `READY` child ticket must be independently
   executable; plans and architecture records remain authoritative links, not
   additional work orders for Developer. Tech Lead may copy a pre-existing
   authorized waiver into the task contract but must not create or approve one.
   Comments cannot authorize or modify a waiver.
   Carry applicable repository engineering constraints into the task when they
   affect completion: for example configured type checking, public-boundary type
   safety, compatibility, security, or static analysis. Do not turn `SOLID`,
   `KISS`, or another general heuristic into a context-free checkbox; express an
   observable constraint or risk only when the scope requires it.
7. Order dependencies and identify safe parallel groups. Sequence migrations,
   contract changes, compatibility work, and removals so supported intermediate
   states remain valid.
8. Validate the complete plan:
   - every required source item maps to at least one task;
   - every required task maps back to a source item;
   - no required outcome is duplicated or hidden inside optional work;
   - each ready task has observable completion and verification evidence;
   - each ready task includes applicable configured type or static-analysis
     checks without inventing project policy;
   - each ready task records Code Review followed by QA, or the authoritative
     policy and owner permitted to waive Code Review;
   - parallel tasks do not have material write or ordering conflicts.
9. If publication is explicitly requested, continue only after the plan is
   `READY_FOR_IMPLEMENTATION` and follow the tracker publication procedure
   and universal connector contract linked from `SKILL.md`. Publication does
   not authorize priority changes, assignment, scheduling, or unrelated tracker
   state changes.

## Completion

Complete when the plan has an accurate readiness status, coverage is traceable,
each child task is usable without prior chat, dependencies and parallelism are
explicit, and unresolved prerequisites have one owner and next action. When
publication was requested, also report verified external mappings or an exact
non-synced publication state. Do not claim `READY_FOR_IMPLEMENTATION` while a
required decision remains unbound, and do not claim tracker publication from
locally prepared artifacts alone.
