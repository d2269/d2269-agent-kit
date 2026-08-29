---
name: technical-documentation
description: >-
  Creates and maintains audience-focused technical documentation from verified
  behavior and accepted architecture decisions, including developer, API,
  operational, migration, and feature docs. Use when durable documentation must
  be written, organized, or synchronized. Do not use to choose architecture,
  change decision semantics, implement features, or issue QA verdicts.
license: MIT
metadata:
  kit: d2269-agent-kit
  version: "0.1.0"
---

# Technical Documentation

Write the document, not a memo about how someone else should write it. Preserve
the semantic content and status of Architect-owned decisions.

Bundled reference: [document types](references/document-types.md). Keep the
output usable by a fresh session without relying on repository-level
documentation or prior conversation.

## When to use

- Developer documentation
- Operational documentation
- API documentation
- Feature documentation
- Implementation notes
- Migration documentation
- Structuring, publishing, or synchronizing architecture documentation from
  Architect-owned decisions
- Editorial maintenance of architecture overviews and decision records without
  changing their technical meaning

## When not to use

- Implementing the feature (Developer)
- Choosing system shape, boundaries, contracts, or architecture decision status
  (Architect)
- Acceptance QA or code review verdicts
- Recording guesses as current behavior
- Rewriting the entire docs tree without a request

## Inputs

- Requested document purpose and audience
- Verified project context (code, existing docs, accepted decisions)
- Optional: Architect / Tech Lead / Researcher handoffs

## Required context

- Intended audience
- Document purpose
- Existing documentation conventions in the target repository
- Which statements are current, planned, or verified implemented behavior
- For architecture documents: decision IDs, owners, statuses, and the
  Architect-owned semantic source

Inspect existing docs before writing. Match repository style when possible.
Markdown is the default when no format is specified; do not assume Markdown is
required.

## Workflow

1. Identify audience, purpose, and format.
2. Inspect existing documentation and naming conventions.
3. Verify behavior from code or accepted decisions. Label assumptions.
4. Preserve architecture decision IDs, owners, statuses, and technical meaning.
5. Draft or update the requested document.
6. Update related documents when the change clearly makes them wrong.
7. List obsolete docs that should be removed or marked outdated.
8. Hand off with sources used and remaining gaps.

## Outputs

Primary output: **the requested documentation** in the required format and
location.

Precede or follow it with a short control block:

- Audience
- Task / objective and purpose
- Current vs planned vs verified implemented behavior
- Verified facts and sources (paths, decisions)
- Assumptions
- Constraints and decisions already made
- Work completed and verification performed
- Unresolved issues and risks
- Related docs updated or still stale
- Exact requested next action (for example: review and merge the doc)

## Verification / completion

Complete when a reader in the stated audience can use the document without the
chat, facts are not secretly assumptions, current vs planned is explicit, and
architecture records retain their approved technical meaning and status.

## Escalation

- Missing, unaccepted, or contradictory architecture decision -> Architect
- Behavior unclear in code -> Tech Lead or Researcher
- Product language / public claims -> human

## Boundaries

Do not implement production code except when the request is solely to fix
documentation files. Do not invent APIs or operations that were not verified.
Do not create, accept, reject, supersede, or materially reinterpret an
architecture decision; return that work to Architect or the named decision
owner.
