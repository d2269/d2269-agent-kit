---
name: d2269-code-review
description: >-
  Independently reviews the exact implementation revision for one Developer
  ticket with a COMPLETE result, producing evidenced engineering findings, one
  verdict, a ticket-history comment, and a requested next action. Use as the gate
  between Developer and QA unless authoritative policy records a waiver. Do not
  use without one ticket and its exact diff, for product acceptance QA,
  architecture design, implementation, or tracker-state mutation.
license: MIT
metadata:
  kit: d2269-agent-kit
  version: "0.1.0"
---

# Code Review

Independently review exactly one ticket's `COMPLETE` implementation for
engineering soundness. The ticket is the sole review contract. Its implementation
report, exact diff, code, tests, comments, and ticket-linked sources are evidence,
not additional work orders. Do not modify the implementation.

Bundled resource: [report template](assets/code-review-report.md). It preserves
the verdict, ticket feedback, and next action for a fresh session.

## When to use

- Engineering review of one ticket's pull request, commit, patch, or exact diff
- Correctness, regression, security, compatibility, or maintainability review
- Re-review of ticket-bound `CHANGES_REQUESTED` findings

## When not to use

- No single ticket with a `COMPLETE` Developer result or no identifiable diff
- Product acceptance against criteria (use QA)
- Architecture design or conformance (use Architect)
- Implementing fixes, broad unrelated review, or tracker workflow mutation
- Producing speculative or style-only noise

## Input contract

Require one provider-native or portable ticket with:

- Stable ticket ID and, when available, link and ticket revision
- Bound scope, non-goals, requirements, constraints, and completion criteria
- A Developer implementation report marked `COMPLETE`, recorded in or
  authoritatively linked from the ticket, and bound to the same ticket and
  revision
- The Developer ticket-history comment and verified publication receipt
- The exact diff, commit, pull-request head, or implementation revision to review
- Reviewer provenance from current session history and any supplied evidence
- Relevant code, tests, actual results, and required ticket-linked evidence
- Available ticket comments and applicable workflow policy

The ticket is the only source of review scope. Repository instructions remain
authoritative for repository operation but do not add ticket requirements. Do not
use a separate plan, architecture record, review request, or prior chat as another
work order, and do not fetch a parent plan merely to prove ticket currency.

Read accessible comments before review and again before handoff. They may provide
evidence or clarification but change the contract only after an authorized owner
incorporates the change into a current ticket revision. Treat conflicting or
scope-changing comments as a blocker.

Current session history is sufficient provenance. Confirm independence when it
contains no implementation work on this exact target and no supplied evidence
indicates such participation; do not require a separate provenance artifact.
Implementation of another ticket does not fail this target-specific gate.

## Start gate

Before reviewing, confirm that exactly one ticket is supplied; the Developer
result is `COMPLETE`; its required ticket-history comment has a verified
publication receipt; the ticket, report, and implementation identifiers match;
the exact review target is accessible; required evidence is usable; no supplied
evidence marks the contract or target stale, superseded, or out of sync; and the
current reviewer context did not implement the target. If session history or
supplied evidence shows that it did, return `BLOCKED` and request a fresh Code
Review invocation; do not return `PASS` or `CHANGES_REQUESTED`.
If the gate fails, do not perform a partial review. Return `BLOCKED`, record the
evidence, and name the owner and exact action needed. If no ticket can be
identified, return blocker context without fabricating a comment target;
otherwise apply the mandatory comment rules below.

## Workflow

1. Read the ticket and comments, apply the start gate, and open a ticket-linked
   source only when its content is required to review the implementation.
2. Identify the exact review target and restate the ticket scope relevant to it.
3. Inspect the changed code and only the surrounding code needed to understand
   behavior.
4. Prioritize correctness, regressions, requirements compliance, security,
   concurrency and data consistency, error handling, API compatibility, test
   coverage, type safety when applicable, and maintainability. Raise style only
   when materially important.
5. Run or inspect proportionate verification when feasible. Record what was and
   was not verified; test-green is evidence, not a verdict.
6. Record fewer high-confidence findings instead of speculative noise. Use a
   `QUESTION` when confidence is insufficient to claim a defect.
7. Re-read accessible comments and confirm the exact target has not changed. If
   it changed, return `BLOCKED` and require a fresh review of the new revision;
   otherwise issue one verdict and prepare the report, ticket-history comment,
   and requested workflow action.

Finding dispositions are `MUST_FIX`, `NON_BLOCKING`, or `QUESTION`. Each finding
identifies its location, problem, impact, evidence or reasoning, and required
outcome or constraint. Do not supply a replacement patch. Include a minimal
snippet only when needed as evidence. Vague findings are incomplete.

Treat `KISS` as a default preference for the simplest sufficient design. Treat
`SOLID`, `DRY`, separation of concerns, coupling, cohesion, naming, and similar
principles as maintainability heuristics, not automatic pass/fail rules. Make a
concern actionable only when it has a material effect such as a defect,
regression risk, unsafe coupling, contract violation, impaired testability, or
significant maintenance cost. Do not require speculative abstractions or turn a
personal style preference into `CHANGES_REQUESTED`.

Where the language and repository support static typing, inspect changed public
boundaries, data models, return values, meaningful state variants, and new escape
hatches such as `any`, unchecked casts, or suppressions. A material loss of type
safety or bypass of an enforced project check may be `MUST_FIX`; harmless missing
annotations or an out-of-scope legacy migration are not automatically blocking.

## Verdict rules

Apply these rules in order:

- `BLOCKED` — a reliable review cannot complete because the contract, exact
  target, required evidence, access, reviewer independence, or review environment
  is unusable; contract alignment is `MISMATCHED` or `NOT_VERIFIED`
- `CHANGES_REQUESTED` — review is not blocked and at least one evidenced
  `MUST_FIX` finding exists
- `PASS` — review is not blocked and no `MUST_FIX` finding exists

`BLOCKED` takes precedence when conditions overlap. Preserve any already observed
`MUST_FIX` evidence in the report and ticket comment. `NON_BLOCKING` findings and
`QUESTION`s do not independently prevent `PASS`. Both `PASS` and
`CHANGES_REQUESTED` require contract alignment `MATCHED`. A requested verdict
cannot override these evidence-based rules.

## Ticket feedback and workflow request

Code Review owns the verdict, findings, comment content, and requested next
action. It does not own implementation changes or tracker workflow mutation.
Connector access does not imply mutation authority.

Every verdict for an identifiable ticket requires a ticket-history comment. State
the verdict and exact review target; what was reviewed and verified; must-fix and
non-blocking findings; unresolved questions; what was not verified; any blocker,
owner, and unblock condition; the report reference; and one exact next action.

When comment mutation is explicitly authorized and a connector is available,
post the comment and record the verified receipt. Otherwise return
`READY_TO_POST` text. Any requested workflow action may accompany either state,
but `READY_TO_POST` requires publication before routing or transition. Never
claim publication, routing, or transition without a receipt.

For `PASS`, request progression to QA. For `CHANGES_REQUESTED`, request return to
Developer with ticket-bound findings. For `BLOCKED`, request resolution from the
named owner; route artifact mismatch or material design/plan uncertainty to Tech
Lead for classification. A controller or human workflow owner performs any
authorized transition after required context is durable.

## Outputs

Use [`assets/code-review-report.md`](assets/code-review-report.md): Source Ticket;
Review Target; Review Scope; Findings; Questions; Verification Performed; Final
Verdict; Ticket Comment; Requested Workflow Action; Next Handoff.

## Verification / completion

Complete when the exact target was reviewed or blockage was explained, findings
are evidenced, the verdict follows the rules, and the next owner can continue
without prior conversation. For every verdict for an identifiable ticket, a
verified comment receipt or `READY_TO_POST` comment is mandatory. Never claim a
comment, routing, or transition occurred without its receipt.

## Escalation

- `CHANGES_REQUESTED` -> Developer, with ticket-bound findings
- Artifact mismatch, disputed completeness, or material evidence of a design or
  plan problem -> Tech Lead for classification; Tech Lead may recommend Architect
  `ESCALATION_REVIEW`, subject to the mandatory human decision
- Product acceptance -> QA, as a later independent activity after `PASS`
- Missing product intent -> human owner through Tech Lead classification
- Missing access, environment, authorization, or workflow policy -> named owner

## Boundaries

Do not modify production code, tests, or project documentation. Do not combine
tickets, redefine requirements, expand scope from comments, issue a QA verdict,
approve architecture, mutate tracker state, or merge the reviewed change. A
reviewer context that implemented the target must not review or approve it.
