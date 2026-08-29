# Tracker Publication

Use this procedure only as the optional final phase of `PLAN`, after the
implementation plan and every task specification have been validated.

The Tech Lead performs publication through an available Linear, Kanban, or other
tracker connector. The connector is a technical mechanism, not a separate role.
It owns low-level authentication, idempotency, retries, and API failure handling;
the Tech Lead owns the records' technical content, hierarchy, and dependency
semantics. Apply the universal connector capability contract linked directly
from `SKILL.md`; do not depend on provider-specific operation names.

## Publication gate

Publish only when all conditions hold:

- The plan is `READY_FOR_IMPLEMENTATION`.
- The current request or applicable policy explicitly authorizes external
  mutation.
- The destination workspace or board, project, and team are named where the
  tracker requires them.
- An authorized connector is available.
- Its declared capabilities can preserve and verify the required record and
  relationship semantics.
- Existing local-to-external mappings and likely matching records have been
  inspected when available.

If any condition is missing, return the tracker-ready artifacts and name the one
missing prerequisite. Do not infer authorization from connector availability.

## Procedure

1. Preserve the plan ID, plan revision, and stable local task IDs as source
   mapping keys. Obtain the connector capability report before mutation.
2. Create or update the requested parent scope and child records from the
   validated artifacts. Preserve parent-child relationships, dependency order,
   technical completion criteria, verification, and relevant labels or links.
3. Do not choose product priority, assignees, dates, estimates, sprint placement,
   or workflow status unless the request or an authoritative mapping supplies
   those values.
4. Record each external ID and link against its local ID and plan revision.
   Verify through the connector receipt or read-after-write capability that the
   remote records contain the intended hierarchy and task-defining fields.
5. If publication is partial, record successful mappings and exact failures.
   Stop before blind retry when the connector cannot guarantee idempotency; do
   not report `SYNCED` while any requested record or relation is unverified.

## Completion

Set publication status to exactly one of:

- `NOT_REQUESTED`: only tracker-ready artifacts were requested.
- `SYNCED`: every requested record and relation was verified in the tracker.
- `PARTIAL`: some records exist, with successful mappings and failures listed.
- `OUT_OF_SYNC`: mapped records exist, but the validated local revision changed
  after the last verified publication.
- `BLOCKED`: publication did not begin because a gate condition was missing.

Publication is complete only at `SYNCED`. `PARTIAL`, `OUT_OF_SYNC`, and `BLOCKED`
require one exact next action and must preserve enough mapping and revision
evidence to avoid duplicates in a later invocation.
