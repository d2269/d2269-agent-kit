# Handoff Contract

Role outputs must be usable by a **fresh agent session** that did not participate in prior discussion. Do not assume shared conversation history.

This contract is shared. Role-specific output skeletons live in each skill's `assets/` directory so they remain available after standalone installation. Do not paste entire skill instructions into a handoff.

## Required properties

Include the following whenever they exist. Omit a field only when it is genuinely not applicable, and say so.

| Field | Purpose |
| --- | --- |
| Task / objective | What the next agent must accomplish |
| Verified facts | Statements confirmed from code, tests, docs, or primary sources |
| Assumptions | Unverified statements the work currently depends on |
| Decisions already made | Bound choices the next agent must not reopen without escalation |
| Constraints | Time, compatibility, scope, platform, or policy limits |
| Relevant files / components | Concrete paths and ownership boundaries |
| Work completed | What is already done |
| Tests performed | Commands run, results, and tests that could not be run |
| Unresolved issues | Open questions, defects, and missing evidence |
| Risks | What can go wrong if the next agent proceeds |
| Exact requested next action | One clear request, not a transcript |

Spec-driven implementation tasks additionally preserve or link inherited product
acceptance criteria and include an observable outcome, scope and non-goals,
source requirements or decision IDs, dependencies, affected components and
interfaces, constraints, technical completion criteria, verification evidence,
delivery impact, risks, and one exact Developer action. Tracker IDs and tracker
state are external mappings, not substitutes for this semantic contract. When
Tech Lead publishes tasks, the plan records stable local IDs, verified external
IDs and links, publication status, and any partial failures so a later session
does not create duplicates. Plans also preserve a stable plan ID, revision,
superseded revision, change summary, and validation basis. Changing mapped task
semantics or relationships invalidates their previously `SYNCED` state until the
new revision is published and verified. Every child-task specification identifies
the parent plan ID and revision it implements.

## Developer ticket contract

Developer consumes exactly one ticket assigned to Developer whose implementation
readiness is `READY`. This semantic field is distinct from tracker workflow
columns such as Todo, In Progress, or Ready for QA. That ticket is the sole work
contract. Repository instructions,
inspected code and tests, ticket comments, and sources authoritatively linked by
the ticket provide context but do not independently add scope. Plans, architecture
records, review messages, and prior chat must not become parallel work orders.

Tech Lead or the deterministic controller owns confirmation that the
published ticket mapping is current. Developer does not fetch or reconstruct the
parent plan solely to prove currency; it stops only when the ticket or supplied
evidence exposes a stale, superseded, or out-of-sync contract.

Developer reads accessible comments before implementation and again before
handoff. Comments may add evidence, clarification, progress, questions, or
handoff context for Tech Lead, Code Review, QA, or an already requested Architect
review. A comment changes task semantics only after an authorized owner
incorporates it into a current ticket revision. Conflicting or scope-changing
comments block implementation pending Tech Lead review.

Every final Developer result (`COMPLETE`, `PARTIAL`, or `BLOCKED`) for an
identifiable ticket requires a ticket-history comment that distinguishes completed
and verified work, failures or incomplete work, unverified work, blockers, and the
next action. When external comment mutation is explicitly authorized and an
appropriate connector is available, Developer posts it and preserves the verified
receipt. Otherwise the implementation report contains `READY_TO_POST` text, which
a controller or human publishes before routing. Reading or posting comments does
not authorize priority, assignment, schedule, workflow-state, or acceptance
changes. A comment cannot create, authorize, or modify a Code Review waiver.

A `COMPLETE` result enters Code Review only after the Developer comment is
durable and the exact implementation revision is identified. It may enter QA
directly only when the current ticket-revision contract or an authoritative
linked workflow-policy record contains an authorized waiver bound to that exact
ticket revision, applies to the implementation target, and names the permitting
policy and authorized owner.
`PARTIAL` or `BLOCKED` work does not enter Code Review or QA as ready.

## Code Review ticket contract

Code Review independently evaluates exactly one ticket in a reviewer context that
did not implement the target. Its Developer implementation report is `COMPLETE`
and required history comment has a verified publication receipt. The ticket is
the sole review contract. The matching report, exact diff or implementation
revision, code, tests, comments, and ticket-linked sources provide evidence
without adding scope. The report, ticket, and exact review target must agree; a
later implementation change invalidates the prior verdict for QA entry.

Code Review returns exactly one semantic verdict: `PASS`,
`CHANGES_REQUESTED`, or `BLOCKED`. `PASS` means no evidenced must-fix finding
exists; `CHANGES_REQUESTED` means at least one must-fix finding exists and the
review can otherwise complete; `BLOCKED` means a reliable review cannot complete
and takes precedence when conditions overlap. Known must-fix evidence remains
recorded. `PASS` and `CHANGES_REQUESTED` require confirmed reviewer independence
and contract alignment; otherwise the verdict is `BLOCKED`. Code Review never
modifies implementation files or tracker workflow state.

Every Code Review verdict for an identifiable ticket requires a ticket-history
comment with the exact review target, findings, verification limits, blocker
details when applicable, and one next action. Code Review posts it only when
mutation is explicitly authorized and preserves the verified receipt; otherwise
it returns `READY_TO_POST` text. Publication is required before routing. A
controller or human workflow owner routes `PASS` to QA, `CHANGES_REQUESTED` to
Developer, and `BLOCKED` to its named owner.

## QA ticket contract

QA evaluates exactly one ticket whose Developer implementation report is
`COMPLETE` after a Code Review `PASS` and durable history comment bound to the
exact implementation revision, or an explicit waiver applicable to the current
ticket revision and evaluation target in the ticket contract or an authoritative
linked workflow-policy record that names the permitting policy and authorized
owner. The ticket is the sole
evaluation contract. The matching implementation and review reports, exact diff
or implementation revision, code, tests, comments, and ticket-linked sources
provide evidence without adding scope. QA does not
reconstruct scope from a plan, architecture record, review report, or prior
conversation and does not fetch the parent plan merely to prove ticket currency.
Missing, non-passing, mismatched, or unpublished review evidence blocks QA unless
an authorized waiver applies.

QA returns exactly one semantic verdict: `PASS`, `CHANGES_REQUESTED`, or
`BLOCKED`. `PASS` requires every required acceptance criterion to be `PASS` or
justified `NOT_APPLICABLE`; a `FAIL` or must-fix defect requires
`CHANGES_REQUESTED`; a required `NOT_VERIFIED` result requires `BLOCKED` and takes
precedence when conditions overlap. Known failures remain recorded. Material
evidence that the ticket's technical contract or accepted design may be wrong
also blocks acceptance and routes to Tech Lead for classification. QA never
modifies the implementation or tracker workflow state.

Every QA verdict for an identifiable ticket requires a ticket-history comment. It
distinguishes passed, failed, and unverified checks and, for `BLOCKED`, names the
blocker, evidence, owner, and unblock condition. QA posts it only when mutation is
explicitly authorized and preserves the verified receipt; otherwise it returns
`READY_TO_POST` text. Any requested action may accompany either form, but the
ready-to-post comment must be published before routing or transition. For `PASS`,
the workflow owner marks the ticket `Done` only when authoritative policy makes
QA the final gate. `BLOCKED` routes to the owner of the missing contract,
artifact, access, environment, or decision. Publication, routing, or transition
is never claimed without its corresponding verified receipt.

## Tech Lead blocker-review decision contract

Tech Lead `BLOCKER_REVIEW` consumes the active ticket contract, current
implementation evidence, relevant ticket comments and role outputs, and any
workflow trigger supplied by a controller or human. A return count may trigger
review but cannot establish the cause.

The result always has status `HUMAN_REVIEW_REQUIRED` and includes the primary
classification, supporting and missing evidence, work that remains valid,
proposed resolution, material alternatives, scope or decomposition impact,
external-mapping impact, recommended next role and bounded action, and one exact
human decision request. Any proposed plan or task revision remains non-published.

The result is a decision package, not authorization. No controller or role may
resume the ticket, publish the proposed revision, invoke Architect or another
investigator, or perform a tracker transition until the named human records a
decision. The recorded decision becomes authoritative input for the next
invocation; it may require resumption, a separate Tech Lead `PLAN` update,
additional project work, Architect review, investigation, or another action.

## Labeling rules

Distinguish these categories explicitly. Do not blend them.

- **Verified fact** — observed in code, tests, documentation, or a cited primary source
- **Assumption** — believed but not verified
- **Decision** — already accepted by its named owner or bound under explicit
  delegated authority; changing it requires the owning role or an escalation
- **Recommendation** — advised but not bound
- **Unresolved question** — must be answered before a later stage can complete

Architecture decision records additionally use lifecycle statuses:
`PROPOSED`, `ACCEPTED`, `IMPLEMENTED`, `SUPERSEDED`, or `REJECTED`. A proposal is
not a bound decision. `IMPLEMENTED` requires verification evidence rather than
the passage of a ticket through a workflow. `REJECTED` requires an explicit
decision from the named decision owner. An accepted decision remains active
until a replacement is accepted; only then may the old decision become
`SUPERSEDED`.

Architecture-overview labels (`TARGET`, `CURRENT`, `PARTIALLY_IMPLEMENTED`) are
not decision lifecycle statuses. They summarize the relationship between the
accepted target and verified implementation. A proposed replacement remains a
non-authoritative delta until accepted.

## Size and format

- Prefer concise structured markdown over conversation transcripts.
- Include file paths, commands, and verdicts verbatim when they matter.
- Do not attach huge logs. Summarize and point to artifacts.
- Outputs should be copyable later into an issue comment without structural rewriting.

## Fresh-session test

A handoff is complete only if an agent with repository access and this document can continue without asking for prior chat context.
