# QA Report

Independent acceptance evaluation of one ticket. Do not implement fixes or mutate
tracker workflow state. Final verdict must be exactly one of `PASS`,
`CHANGES_REQUESTED`, or `BLOCKED`.

## Source Ticket

- Ticket ID and link:
- Ticket revision or last-updated marker:
- Requirements and acceptance-criteria source:
- Ticket comments reviewed through:

## Evaluation Target

- Developer implementation report and result:
- Diff, commit, or implementation revision:
- Relevant components inspected:
- Contract alignment: `MATCHED` | `MISMATCHED` | `NOT_VERIFIED`

## Code Review Gate

- Gate: `PASS` | `WAIVED` | `NOT_SATISFIED`
- Code Review report and exact target, when passed:
- Code Review history-comment publication receipt, when passed:
- Waiver applicability to current ticket revision and exact target, permitting
  policy, authorized owner, and authoritative contract source, when waived:
- Gate alignment: `MATCHED` | `MISMATCHED` | `NOT_VERIFIED`

## Acceptance Criteria Matrix

| Criterion ID or summary | Result | Evidence or justification |
| --- | --- | --- |
| | PASS / FAIL / NOT_VERIFIED / NOT_APPLICABLE | |

Every `NOT_APPLICABLE` result requires justification. A required
`NOT_VERIFIED` criterion requires `BLOCKED` and takes precedence over a known
failure; preserve that failure in the report.

## Verification Performed

- Commands and tests run:
- Results:
- Behavior observed:
- Evidence inspected:
- What could not be verified:

## Regression Risks

-

## Edge Cases

| Case | Result | Evidence |
| --- | --- | --- |
| | | |

## Must-fix Findings

| ID | Criterion | Location | Expected / actual | Evidence / reproduction | Impact |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

## Non-blocking Findings

| ID | Criterion or area | Evidence | Impact |
| --- | --- | --- | --- |
| | | | |

## Questions

| ID | Question | Why it matters | Owner |
| --- | --- | --- | --- |
| | | | |

## Final Verdict

- Verdict: `PASS` | `CHANGES_REQUESTED` | `BLOCKED`
- Basis:

## Ticket Comment

- Required: `YES`
- Publication status: `POSTED` | `READY_TO_POST`
- Verified receipt, when posted:
- Report reference:

### Comment text

- Verdict and evaluation target:
- Passed and verified:
- Failed criteria and finding IDs:
- Not verified:
- Expected versus actual behavior, evidence, and impact:
- Blocker, owner, and unblock condition:
- Exact requested action:

For `CHANGES_REQUESTED`, identify every failed criterion and exact Developer
action. For `BLOCKED`, clearly distinguish completed checks, failures, and
unverified checks.

## Requested Workflow Action

- Requested action: `RETURN_TO_DEVELOPMENT` | `ADVANCE_PER_POLICY` |
  `RESOLVE_BLOCKER`
- Authoritative workflow-policy source:
- Terminal after QA: `YES` | `NO` | `NOT_VERIFIED`
- Requested tracker outcome when terminal:
- Transition precondition or publication step:
- Mutation performed by QA: `NO`

## Next Handoff

- Next owner:
- Task / objective:
- Verified facts:
- Assumptions:
- Decisions already made:
- Constraints:
- Relevant files / components:
- Work completed:
- Tests performed:
- Unresolved issues:
- Risks:
- Exact requested next action:

A `RETURN_TO_DEVELOPMENT` request may accompany either `POSTED` or
`READY_TO_POST` feedback. For `READY_TO_POST`, a controller or human workflow
owner publishes the comment before performing any requested routing or authorized
transition. Never claim publication, routing, or a transition without its
corresponding verified receipt.
