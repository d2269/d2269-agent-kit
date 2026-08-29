# Conformance Review Mode

Use `CONFORMANCE_REVIEW` after a defined scope is implemented. This is an
architecture-level audit, not product acceptance, detailed diff review, or final
merge authority.

Run this as a separate invocation from `DESIGN` for the same scope. A fresh
context that did not design or implement the scope is strongly preferred. If the
current context participated earlier, disclose that limitation in the report and
require stronger implementation evidence before reaching a verdict. Keep the
assessment independent and do not modify production code. Establish the verdict
before applying any authorized architecture-documentation changes.

## Required context

- Completed scope and system-level definition of done
- Accepted architecture baseline and decision records
- Relevant implementation, contracts, schemas, migrations, tests, metrics, and
  operational evidence
- Known deviations and their approvals

Return `NOT_VERIFIABLE` when evidence is insufficient for a defensible verdict.

## Procedure

1. Map accepted architecture expectations to implementation evidence.
2. Inspect component boundaries, ownership, public and cross-component
   contracts, data flow, migration behavior, and applicable quality attributes.
3. Classify each difference as an intentional approved deviation, accidental
   architecture drift, incomplete implementation, or documentation drift.
4. Identify systemic risks and architecture debt. Leave file-local correctness
   findings to Code Review and acceptance failures to QA.
5. Set exactly one verdict:
   - `ALIGNED`
   - `ALIGNED_WITH_DEVIATIONS`
   - `NOT_ALIGNED`
   - `NOT_VERIFIABLE`
6. Identify decision statuses and architecture documents that evidence supports
   changing. Mark an accepted decision `IMPLEMENTED` only when its validation
   criteria are verified; workflow or ticket status is not evidence.
7. Produce a durable close-out. When repository writes are authorized, update
   supported decision statuses and current, target, or partially implemented
   architecture labels after the verdict. Otherwise provide file-ready changes
   with exact target paths. Preserve unsupported areas as explicitly stale or
   unverified.
8. Hand blocking implementation work to Tech Lead, acceptance gaps to QA,
   diff-level findings to Code Review, and approval questions to the human owner.

## Completion

Complete when the verdict is traceable to evidence, unverified areas are
explicit, deviations are classified, systemic findings are prioritized, and
every required follow-up has one owner. The durable baseline is synchronized, or
file-ready close-out changes and their exact target paths are provided when
writes are not authorized.
