# Universal Tracker Connector Contract

Use this provider-neutral contract when `PLAN` publishes or synchronizes
implementation records. Concrete connectors may expose different tool names and
payloads; Tech Lead reasons from declared capabilities and normalized results,
not from a Linear-, Jira-, Trello-, or Kanban-specific API.

## Capability report

Before mutation, establish whether the available connector can:

- resolve and read the named target;
- find existing records from stable mappings or local IDs, or provide equivalent
  idempotent upsert behavior from a stable key;
- create and update parent and child records;
- preserve parent-child relationships when the plan requires them;
- preserve dependency relationships when the plan requires them;
- read back or otherwise verify task-defining fields and relationships;
- return external IDs, links, per-operation outcomes, and retry-safety evidence.

Target resolution, lookup or equivalent idempotent upsert, create or update,
verification, and a structured receipt are required for safe publication.
Relationship capabilities are conditionally required by the plan. If a required
semantic cannot be preserved, return `BLOCKED` before mutation or `PARTIAL` after
a partial write; never silently flatten it. An explicitly authorized, documented
representation may substitute only when it preserves the required meaning.

## Normalized publication request

Keep these semantics available even when the concrete connector uses another
shape:

- requested operation: initial publication or synchronization;
- authorization source and named target;
- plan ID, current revision, and superseded revision when applicable;
- parent record and child records keyed by stable local IDs;
- task-defining content, parent links, dependencies, and authoritative tracker
  fields supplied by the request or policy;
- existing local-to-external mappings and last verified plan revision.

Do not invent provider fields, priority, assignment, dates, estimates, sprint
placement, or workflow state to satisfy a connector schema.

## Normalized receipt

Require enough result data to record and verify:

- connector and target identity;
- capabilities used and unsupported required semantics;
- plan ID and revision applied;
- for every local ID: external ID, link, action, and verification result;
- parent and dependency relationship results;
- failures, partial writes, and whether replay is safe;
- overall publication status and one exact next action when not `SYNCED`.

The connector owns authentication, provider translation, idempotency, retries,
and API error behavior. Tech Lead owns the requested technical semantics and the
decision whether the receipt proves `SYNCED`. Tool availability or a successful
create call alone proves neither authorization nor complete synchronization.
