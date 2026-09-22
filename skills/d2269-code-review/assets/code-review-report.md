# Code Review Report

Independent engineering review of one ticket's exact implementation revision. Do
not modify the implementation or tracker workflow state. Final verdict must be
exactly one of `PASS`, `CHANGES_REQUESTED`, or `BLOCKED`.

## Source Ticket

- Ticket ID and link:
- Ticket revision or last-updated marker:
- Ticket comments reviewed through:
- Developer implementation report and result:
- Developer history-comment publication receipt:
- Reviewer independence: `CONFIRMED` | `NOT_CONFIRMED`
- Reviewer provenance evidence:

## Review Target

- Diff, commit, pull-request head, or implementation revision:
- Relevant components inspected:
- Contract alignment: `MATCHED` | `MISMATCHED` | `NOT_VERIFIED`

## Review Scope

- Ticket requirements and constraints reviewed:
- Surrounding code inspected:
- Explicit exclusions:

## Must-fix Findings

| ID | Location | Problem | Impact | Evidence / reasoning | Required outcome or constraint |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

## Non-blocking Findings

| ID | Location | Problem | Impact | Evidence / reasoning | Required outcome or constraint |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

Do not provide a replacement patch. Use a minimal snippet only when needed as
evidence for a finding.

## Questions

| ID | Location | Question | Why it matters | Owner |
| --- | --- | --- | --- | --- |
| | | | | |

## Verification Performed

- Commands and checks run:
- Results:
- Evidence inspected:
- What was not verified:

## Final Verdict

- Verdict: `PASS` | `CHANGES_REQUESTED` | `BLOCKED`
- Basis:

## Ticket Comment

- Required: `YES`
- Publication status: `POSTED` | `READY_TO_POST`
- Verified receipt, when posted:
- Report reference:

### Comment text

- Verdict and exact review target:
- Reviewed and verified:
- Must-fix findings:
- Non-blocking findings and questions:
- Not verified:
- Blocker, evidence, owner, and unblock condition:
- Exact requested action:

For `CHANGES_REQUESTED`, identify every must-fix finding and exact Developer
outcome. For `BLOCKED`, distinguish completed review from unverified work.

## Requested Workflow Action

- Requested action: `ADVANCE_TO_QA` | `RETURN_TO_DEVELOPMENT` |
  `RESOLVE_BLOCKER`
- Authoritative workflow-policy source:
- Transition precondition or publication step:
- Mutation performed by Code Review: `NO`

## Next Handoff

- Next owner:
- Task / objective:
- Verified facts:
- Assumptions:
- Decisions already made:
- Constraints:
- Relevant files / components:
- Work completed:
- Verification performed:
- Unresolved issues:
- Risks:
- Exact requested next action:

Any requested action may accompany either `POSTED` or `READY_TO_POST` feedback.
For `READY_TO_POST`, a controller or human workflow owner publishes the comment
before routing or transition. Never claim publication, routing, or transition
without a verified receipt.

`PASS` and `CHANGES_REQUESTED` require contract alignment `MATCHED`.
`MISMATCHED` or `NOT_VERIFIED` alignment requires `BLOCKED`.
