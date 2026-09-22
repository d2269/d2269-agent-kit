# Lifecycle Role Contracts

Review status: IN PROGRESS

This document records the development lifecycle one role at a time. It defines
what each role receives, how it interprets the assignment, what it produces, and
which condition permits the next handoff. It is the textual companion to
[`development-lifecycle.md`](development-lifecycle.md).

This is the standard and consequential delivery contract, not a requirement to
invoke every role for every request. Select the proportional route first in
[Execution Profiles](execution-profiles.md); the role contracts below remain
unchanged whenever their stages are selected.

Only behavior defined by the role skills or explicitly adopted workflow policy
belongs here. Role outputs are semantic results; a human or the Lifecycle
Controller performs authorized tracker transitions.

## Current artifact flow

```text
Human Product / Task Specification
                |
                v
        Architect — DESIGN
                |
                v
Architecture Baseline + decision records + workstreams + handoff
                |
                +-- required decision remains PROPOSED --> named decision owner
                |
                `-- required decisions ACCEPTED --------> Tech Lead — PLAN
                                                            |
                                                            v
                                                   Implementation Plan
                                                   + one Implementation Task
                                                     per child ticket
                                                            |
                                                            +-- DRAFT/BLOCKED -->
                                                            |   named prerequisite owner
                                                            |
                                                            `-- READY_FOR_IMPLEMENTATION -->
                                                                optional tracker publication
```

## 1. Human — define the requested product outcome

### Intent

Describe what should be achieved and the conditions the delivered product must
satisfy. This is the source of product intent, not an architecture design or an
implementation plan.

### Input

- Product need, problem, or requested change
- Existing business or operational context
- Known constraints and existing authoritative requirements

### Work

The human or product owner prepares a Product / Task Specification containing:

- objective and expected product result;
- scope and non-goals;
- product acceptance criteria;
- system-level definition of done;
- constraints that may invalidate an approach;
- named decision owner and the source and scope of any delegated decision
  authority.

### Output

One authoritative Product / Task Specification suitable as input to Architect
`DESIGN`.

### Handoff condition

Invoke Architect `DESIGN` when the requested outcome and known constraints are
recorded. The specification may still contain uncertainty: Architect must expose
material gaps instead of silently inventing product intent.

## 2. Architect — DESIGN

### Intent

Translate the requested product outcome into a system-level technical design.
Architect owns architecture semantics: boundaries, major contracts, quality
attributes, consequential decisions, and the minimal durable architecture
baseline.

Architect does not create implementation tickets, provide file-level execution
steps, implement production code, perform Code Review, or issue a QA verdict.

### Input

- Product / Task Specification from the human owner
- Objective, scope, non-goals, and system-level definition of done
- Product acceptance criteria and constraints
- Named decision owner and explicit delegated authority, when any
- Existing code, architecture documents, contracts, schemas, and accepted
  decision records when accessible

### Work

Architect:

1. Inspects the current system and records any uninspected areas.
2. Separates verified facts, assumptions, proposals, accepted decisions, and
   unresolved questions.
3. Defines target behavior, quality attributes, component boundaries,
   responsibilities, ownership, and major contracts.
4. Compares materially viable approaches, prefers the least complex architecture
   that satisfies current requirements and quality attributes, and records
   consequential choices as architecture decision records.
5. Decomposes the design into outcome-oriented technical workstreams with
   dependencies, interface owners, and verification evidence.
6. Defines migration, compatibility, rollback, risks, and unresolved questions.
7. Produces or updates the durable architecture artifacts when writes are
   authorized; otherwise returns file-ready content with exact target paths.

Architect asks the human owner explicit questions when missing or contradictory
product intent materially prevents a responsible design. It does not ask for
clarification that can be resolved safely from repository evidence or within an
already delegated architecture decision.

### Output

The Architecture Package contains only the artifacts required for this scope:

- Architecture Baseline describing current and planned target behavior
- Architecture decision records for consequential choices
- Decision status and authority evidence
- Component boundaries, responsibilities, and major contracts
- Architecturally consequential schema, type, and compatibility expectations for
  public or cross-component contracts
- Outcome-oriented technical workstreams and dependencies
- Migration, compatibility, rollback, risks, and unresolved questions
- Verification evidence expected from implementation
- A fresh-session Architecture Handoff

Architect workstreams are not implementation tickets. Tech Lead owns the
Implementation Plan, child-ticket specifications, execution order, likely write
surfaces, and detailed test planning.

### Result and next action

| Condition | Architect result | Next action |
| --- | --- | --- |
| Product intent is materially missing or contradictory | Explicit questions and the affected unresolved decisions | Human owner supplies or corrects the input; invoke `DESIGN` again |
| A required binding decision is not approved | Architecture Package with the decision marked `PROPOSED` | Named decision owner accepts, rejects, or requests revision |
| A proposed decision is explicitly rejected | Decision marked `REJECTED` | Stop dependent planning or request a revised design |
| All required binding decisions are accepted | Architecture Package with required decisions marked `ACCEPTED` and an implementation-ready handoff | Invoke Tech Lead `PLAN` in a separate session |

### Completion boundary

Architect `DESIGN` is complete only when the architecture is specific enough for
Tech Lead to plan without inventing system boundaries or reopening accepted
decisions. Work that depends on a required `PROPOSED` decision must not be handed
to Tech Lead as implementation-ready.

## 3. Tech Lead — PLAN

### Intent

Convert the defined product scope and accepted architecture into one coherent
Implementation Plan and independently usable child-ticket specifications. Tech
Lead owns implementation-level planning semantics, coverage, dependencies,
sequencing, and technical completion criteria.

`Implementation Plan` and `Implementation Task` are artifact types, not separate
roles or modes. One Tech Lead `PLAN` invocation produces both levels. There is no
later `Implementation Task` role to invoke.

### Input

- Product / Task Specification
- Objective, scope, non-goals, and unchanged product acceptance criteria
- System-level definition of done
- Accepted Architecture Baseline and applicable accepted decision records
- Architect workstreams and required verification evidence
- Relevant code, tests, contracts, schemas, migrations, documentation, and
  repository conventions
- Delivery workflow policy, including any authoritative Code Review waiver
  policy
- Tracker constraints and publication authority only when publication is
  requested

The input is the complete relevant authoritative package, not every project file
and not the prior Architect conversation. Tech Lead inspects additional relevant
repository evidence as needed.

### Work

Tech Lead:

1. Establishes the verified implementation baseline and identifies uninspected
   areas.
2. Preserves the supplied product acceptance criteria and accepted architecture
   without silently reinterpreting either.
3. Sets the plan status to exactly one of `READY_FOR_IMPLEMENTATION`, `DRAFT`, or
   `BLOCKED`.
4. Builds a coverage matrix from every in-scope requirement, system-level
   completion condition, accepted decision, Architect workstream, and required
   verification item to an implementation outcome and its evidence.
5. Decomposes those outcomes into the smallest coherent, independently
   understandable and verifiable child tasks.
6. Assigns a stable Plan ID and revision and stable local Task IDs.
7. Defines dependencies, required sequence, safe parallel groups, likely write
   surfaces, supported intermediate states, migration order, and rollback order.
8. Creates one Implementation Task specification for every child ticket.
   Each task carries applicable repository engineering constraints and configured
   type or static-analysis checks without inventing project policy or generic
   `SOLID` compliance criteria.
9. Validates coverage, task independence, dependencies, completion evidence,
   required Code Review and QA gates, and write-conflict assumptions across the
   complete plan.

Tech Lead does not implement production code, change product acceptance
criteria, reopen accepted architecture, or turn optional improvements into
required scope.

### Clarification and backward handoff

Tech Lead may return a bounded clarification request instead of moving the scope
forward.

| Condition | Plan/task state | Next action |
| --- | --- | --- |
| Required architecture decision is missing, contradictory, or `PROPOSED` | Plan or affected tasks remain `DRAFT`/`BLOCKED` | Architect or the named decision owner supplies an accepted decision; invoke Tech Lead `PLAN` again |
| Product intent or acceptance criteria are contradictory | `BLOCKED` | Human/product owner resolves the contradiction |
| Relevant implementation evidence is missing but can be inspected | No status is inferred yet | Tech Lead inspects the repository evidence |
| An ordinary local implementation choice remains | The task may remain `READY` when its boundaries are clear | Developer chooses within the recorded constraints |

An architecture clarification must name the missing or contradictory decision,
the affected outcomes or tasks, and the exact response needed. Tech Lead must not
invent an architecture answer merely to complete decomposition.

### Output A — Implementation Plan

Produce exactly one Implementation Plan for the scope using
[`implementation-plan.md`](../skills/d2269-tech-lead/assets/implementation-plan.md).
It records:

- Plan ID, revision, source artifacts, and plan status
- Required outcomes, non-goals, optional improvements, and unrelated cleanup
- Verified facts, assumptions, constraints, and accepted decisions
- Coverage matrix
- Child-task graph, dependencies, parallel groups, likely write surfaces, and
  task readiness
- Sequencing, compatibility, supported intermediate states, migration, and
  rollback
- Cross-cutting testing, observability, operations, documentation, and security
  considerations
- Risks, open prerequisites, their owners, and exact next actions
- Handoff containing ready and blocked Task IDs

### Output B — Implementation Task specifications

Produce one Implementation Task specification per child ticket using
[`implementation-task.md`](../skills/d2269-tech-lead/assets/implementation-task.md).
Each specification records:

- stable Task ID and parent Plan ID/revision;
- one outcome-oriented title and expected result;
- execution role, normally `Developer`;
- implementation readiness: `READY` or `BLOCKED`;
- scope, non-goals, requirements, and acceptance-criteria sources;
- applicable architecture decision IDs and constraints;
- dependencies, affected components, and interfaces;
- technical completion criteria and required verification;
- required Code Review and QA gates or an already authorized waiver;
- data, API, migration, observability, documentation, and security impact;
- risks, unresolved prerequisites, decisions to preserve, and one exact requested
  Developer action.

An Implementation Task must be usable by a fresh Developer session as its sole
work contract. The plan and architecture remain linked sources and do not become
additional work orders for Developer.

### Readiness and forward handoff

| Status | Meaning | May move to implementation? |
| --- | --- | --- |
| `READY_FOR_IMPLEMENTATION` | All blocking requirements and decisions are bound and the complete task set is executable | Yes, for an individual `READY` task whose blocking dependencies are satisfied |
| `DRAFT` | Useful decomposition exists, but named prerequisites remain open | No; the plan is not ready for implementation handoff or publication |
| `BLOCKED` | Responsible decomposition is not possible from the current inputs | No; resolve the named blocker first |

The trigger for the next lifecycle stage is therefore not merely the existence
of an Implementation Task. All of the following must hold:

1. The parent plan is `READY_FOR_IMPLEMENTATION`.
2. The selected child task is `READY`.
3. Its blocking dependencies are satisfied.
4. Its specification is independently usable and has one exact requested action.
5. If the tracker is the authoritative execution channel, the selected external
   record and its mappings are verified `SYNCED` before selection there.

When these conditions hold, a human or the Lifecycle Controller may select
one ready child ticket for the next role invocation.

### Optional tracker publication

Publication is an optional final phase of the same Tech Lead `PLAN` invocation,
not another role. It runs only when external mutation is explicitly authorized,
the target is named, and an authorized connector can preserve and verify the
required semantics.

Publication returns exactly one status: `NOT_REQUESTED`, `SYNCED`, `PARTIAL`,
`OUT_OF_SYNC`, or `BLOCKED`. Only `SYNCED` proves that every requested external
record and relationship was verified. Publication does not authorize Tech Lead
to invent priority, assignee, schedule, sprint, estimate, or workflow status.

### Completion boundary

Tech Lead `PLAN` is complete when the plan has an accurate readiness status,
coverage is traceable, every child task is usable without prior conversation,
dependencies and parallelism are explicit, and every unresolved prerequisite has
one owner and exact next action. If publication was requested, the output must
also include verified external mappings or an exact non-synced publication
status.

## 4. Select one executable ticket

### Intent

Select the next executable child ticket without making Developer reconstruct the
plan, choose its own work, or combine multiple tickets.

This is workflow coordination, not a reasoning role. A human workflow owner or
deterministic Lifecycle Controller performs the selection. A ticket
number is a stable identity, not an execution priority.

### Input

- An Implementation Plan with status `READY_FOR_IMPLEMENTATION`
- Its child-ticket specifications and dependency graph
- Current dependency outcomes
- Authoritative priority or scheduling policy, when supplied
- Tech Lead parallel groups and material write-conflict constraints
- Verified external mappings when the tracker is the authoritative execution
  channel

### Selection rule

A child ticket is executable only when:

1. Its parent plan is `READY_FOR_IMPLEMENTATION`.
2. Its implementation readiness is `READY`.
3. Its blocking dependencies are satisfied.
4. Any required preceding work is complete.
5. Its contract is independently usable by Developer.

When several tickets are executable, the human or controller uses authoritative
priority and the plan's dependency and sequencing constraints. Separate tickets
may run in parallel only when Tech Lead identified a safe parallel group and no
material write conflict exists. Each Developer invocation still receives
exactly one ticket.

Developer does not scan the plan or tracker to choose work. A tracker column
named Ready does not establish semantic implementation readiness.

### Output and handoff

Output exactly one selected, current `READY` ticket per Developer invocation.
The ticket is Developer's sole work contract. Its plan, architecture records,
repository instructions, code, tests, comments, and ticket-linked sources are
supporting context rather than additional work orders.

## 5. Developer — implement one ticket

### Intent

Implement exactly one selected ticket with semantic implementation readiness
`READY`. The ticket is the sole work contract. Repository instructions, code,
tests, comments, and ticket-linked sources support execution but do not create
additional scope.

### Input

- One current ticket assigned to execution role `Developer`
- Implementation readiness `READY`
- Stable ticket ID and parent Plan ID/revision when applicable
- Outcome, scope, non-goals, requirements, and product acceptance criteria
- Bound constraints and applicable architecture decision IDs or links
- Dependencies, affected components, technical completion criteria, required
  verification, risks, and one exact requested action
- Ticket-bound Code Review or QA findings for follow-up work
- Accessible ticket comments

Before changing code, Developer confirms that the ticket contract is usable and
blocking dependencies are satisfied. Supplied evidence that the ticket is stale,
superseded, or out of sync makes it non-ready. Developer does not fetch a parent
plan merely to prove currency.

### Work

Developer:

1. Reads the ticket and comments and applies its start gate.
2. Inspects the affected code and tests.
3. Implements only ticketed work using the simplest sufficient design and avoids
   speculative abstractions or unrelated cleanup.
4. Preserves or improves type safety on the changed surface when supported by the
   language and repository, with explicit justification for escape hatches.
5. Adds or updates the tests required by the ticket and observed risk.
6. Updates documentation made inaccurate by the change.
7. Runs relevant available verification, including applicable configured type or
   static-analysis checks, and records actual results.
8. Records local implementation decisions, assumptions, risks, and deviations.
9. Produces an implementation report and one mandatory ticket-history comment.

Developer does not redefine requirements, change architecture, perform
independent Code Review or QA, declare QA success, or mutate tracker workflow
state.

### Output

Use
[`implementation-report.md`](../skills/d2269-developer/assets/implementation-report.md)
to return:

- source ticket and ticket revision;
- implementation summary and exact implementation revision;
- changed components and directly affected documentation;
- acceptance and technical-completion evidence;
- tests added or updated and actual verification results;
- local decisions, assumptions, risks, and contract deviations;
- resolution of supplied Code Review or QA findings when applicable;
- exactly one result: `COMPLETE`, `PARTIAL`, or `BLOCKED`;
- a mandatory ticket-history comment;
- one exact next owner and action.

The final comment states what completed and passed, what failed or remains
incomplete, what was not verified, any blocker and unblock condition, and the
next action. Developer posts it only with explicit mutation authority and a
connector and records the receipt; otherwise it returns `READY_TO_POST` text.
Routing cannot occur until the required comment is durable.

### Result and next action

| Result | Meaning | Next action |
| --- | --- | --- |
| `COMPLETE` | Required behavior and tests are implemented, verification is recorded, and the exact revision is identified | Route the same ticket and exact revision to a fresh Code Review invocation after the comment is durable |
| `PARTIAL` | Some valid work exists but the ticket outcome is incomplete | Continue the same ticket or follow the named blocker owner; do not send it to Code Review or QA as ready |
| `BLOCKED` | The ticket cannot be completed responsibly from the current contract or environment | Follow the named owner and action; request Tech Lead `BLOCKER_REVIEW` for ticket, dependency, requirements, plan, or suspected architecture problems |

The only permitted bypass of Code Review is an explicit waiver already bound to
the current ticket revision by authoritative workflow policy. Developer cannot
create or infer that waiver. With a valid waiver, `COMPLETE` may route directly
to QA for the same exact revision.

### Completion boundary

Developer finishes after producing the implementation, evidence, result,
mandatory comment, and next handoff. It does not select the next ticket, approve
its own implementation, or execute the tracker transition.

## 6. Code Review — review one completed ticket

### Intent

Independently review the exact implementation revision for one ticket with a
Developer result of `COMPLETE`. The ticket is the sole review contract. Code
Review evaluates engineering soundness; QA owns product acceptance.

### Input

- One current ticket and its bound scope, non-goals, requirements, constraints,
  and completion criteria
- Matching Developer implementation report marked `COMPLETE`
- Developer ticket-history comment with a verified publication receipt
- Exact diff, commit, pull-request head, or implementation revision
- Relevant code, tests, actual results, ticket comments, and required
  ticket-linked evidence
- Current-session provenance sufficient to confirm that this reviewer context
  did not implement the exact target

The ticket, report, and implementation identifiers must match. Code Review does
not fetch the parent plan to reconstruct scope. If the exact target, required
evidence, contract alignment, access, environment, or reviewer independence is
unusable, it returns `BLOCKED` instead of performing a partial review.

### Work

Code Review:

1. Reads the ticket and comments and identifies the exact review target.
2. Restates the ticket scope relevant to that target.
3. Inspects the changed code and only the surrounding code needed to understand
   its behavior.
4. Evaluates correctness, requirement compliance, regression risk, security,
   concurrency and data consistency, error handling, API compatibility, tests,
   applicable type safety, and maintainability.
5. Runs or inspects proportionate verification when feasible and records what
   was and was not verified.
6. Produces fewer evidenced, high-confidence findings instead of speculative or
   style-only comments.
7. Rechecks that the exact target has not changed, then issues one verdict,
   mandatory ticket comment, and requested next action.

`SOLID`, `KISS`, `DRY`, separation of concerns, coupling, cohesion, naming, and
similar principles are maintainability heuristics, not automatic pass/fail
rules. A concern is actionable only when it has a material effect such as a
defect, regression risk, unsafe coupling, contract violation, or significant
maintenance cost. Personal style preference alone does not justify
`CHANGES_REQUESTED`.

When static typing is supported and configured, Code Review inspects changed
public boundaries, data models, meaningful state variants, and new escape
hatches. A material contract risk or bypass of an enforced check can be
`MUST_FIX`; redundant annotations and out-of-scope legacy migration are not
required.

### Findings and output

Each finding is exactly one of:

- `MUST_FIX`: evidenced defect or material engineering risk that must be
  corrected before progression;
- `NON_BLOCKING`: useful observation that does not prevent progression;
- `QUESTION`: unresolved point whose evidence is insufficient to claim a defect.

Use
[`code-review-report.md`](../skills/d2269-code-review/assets/code-review-report.md) to
return:

- source ticket and exact review target;
- review scope and contract alignment;
- evidenced findings and questions;
- verification performed and not performed;
- exactly one verdict: `PASS`, `CHANGES_REQUESTED`, or `BLOCKED`;
- a mandatory ticket-history comment;
- one requested workflow action and next handoff.

Every identifiable-ticket verdict requires a durable comment containing the
verdict, exact target, reviewed evidence, findings, unverified areas, blocker and
unblock condition when applicable, report reference, and exact next action. Code
Review posts it only with explicit authority and a connector; otherwise it
returns `READY_TO_POST` text. Routing cannot occur until the comment is durable.

### Verdict and next action

| Verdict | Rule | Next action |
| --- | --- | --- |
| `BLOCKED` | Reliable review cannot complete or contract alignment is not established | Resolve the named blocker; send material artifact, plan, or design uncertainty to Tech Lead for classification |
| `CHANGES_REQUESTED` | Review is not blocked and at least one `MUST_FIX` finding exists | Return the same ticket and ticket-bound findings to Developer; the controller records a rework event |
| `PASS` | Review is not blocked, contract alignment is matched, and no `MUST_FIX` finding exists | Route the same ticket and exact revision to QA |

`BLOCKED` takes precedence when conditions overlap. Any `MUST_FIX` evidence
already observed remains recorded. `NON_BLOCKING` findings and `QUESTION`s do not
independently prevent `PASS`.

### Completion boundary

Code Review finishes after reviewing the exact target or explaining the blocker,
recording evidenced findings, issuing one verdict, preparing the mandatory
comment, and naming one next action. It does not modify implementation code,
perform QA, approve architecture, merge the change, or mutate tracker workflow
state.

## 7. QA — evaluate one reviewed ticket

### Intent

Independently determine whether the exact implementation revision for one ticket
satisfies its bound product acceptance criteria. QA owns the acceptance verdict;
it does not repeat ordinary Code Review, implement fixes, or declare broader
release safety.

### Input and start gate

QA requires:

- exactly one current ticket with a usable acceptance contract;
- a matching Developer implementation report marked `COMPLETE`;
- the exact diff, commit, or implementation revision to evaluate;
- a Code Review `PASS` for that exact target with its durable ticket-history
  comment and verified receipt; or an explicit authorized waiver bound to the
  current ticket revision and exact target;
- relevant code, tests, actual results, accessible comments, and required
  ticket-linked evidence.

The ticket is the sole evaluation contract. Code Review is a gate and evidence,
not another scope source. QA does not fetch a parent plan or reconstruct scope
from architecture records, reports, chat, or comments.

If Developer is not `COMPLETE`, Code Review did not return a matching `PASS`, a
valid waiver is absent, identifiers do not match, required evidence is
inaccessible, or supplied evidence marks the target stale or out of sync, QA
returns `BLOCKED` without performing a partial acceptance evaluation.

### Work

QA:

1. Reads the ticket and comments and applies the start gate.
2. Restates the ticket scope and acceptance criteria.
3. Inspects the implementation report, Code Review gate evidence, exact diff,
   and only the surrounding code needed for acceptance evaluation.
4. Maps every acceptance criterion to one result.
5. Runs or inspects relevant tests and observable behavior and records actual
   evidence and verification gaps.
6. Evaluates ticket-relevant regressions, edge cases, failure modes, error
   handling, and compatibility.
7. Records actionable findings with evidence.
8. Issues exactly one verdict, mandatory ticket-history comment, and requested
   next action.

QA does not overrule the engineering Code Review verdict. It may use review
findings as evidence when they materially affect product acceptance.

### Acceptance-criterion results

Each criterion receives exactly one result:

| Result | Meaning |
| --- | --- |
| `PASS` | Available evidence confirms the required behavior |
| `FAIL` | Observed behavior contradicts the criterion |
| `NOT_VERIFIED` | A required criterion could not be evaluated reliably |
| `NOT_APPLICABLE` | The criterion does not apply to this target; justification is mandatory |

Finding dispositions are `MUST_FIX`, `NON_BLOCKING`, or `QUESTION`. Every
actionable finding records the affected criterion, expected and actual behavior,
evidence or reproduction, location, and impact.

### Output

Use [`qa-report.md`](../skills/d2269-qa/assets/qa-report.md) to return:

- source ticket and exact evaluation target;
- satisfied Code Review gate or authorized waiver;
- acceptance-criteria matrix;
- verification performed, results, and unverified areas;
- ticket-relevant regression risks and edge cases;
- evidenced findings and questions;
- exactly one verdict: `PASS`, `CHANGES_REQUESTED`, or `BLOCKED`;
- one mandatory ticket-history comment;
- one requested workflow action and next handoff.

The comment records the verdict and target, what passed, what failed, what was
not verified, supporting evidence, blocker and unblock condition when
applicable, report reference, and exact next action. For
`CHANGES_REQUESTED`, it also records finding IDs, expected versus actual
behavior, impact, and the exact Developer action. For `BLOCKED`, it separates
completed checks from failed and unverified checks.

QA posts the comment only with explicit mutation authority and an available
connector and records the receipt; otherwise it returns `READY_TO_POST` text.
Routing or transition waits until the mandatory comment is durable.

### Verdict and next action

Apply verdict rules in this order:

| Verdict | Rule | Next action |
| --- | --- | --- |
| `BLOCKED` | Reliable evaluation cannot complete, including when a required criterion is `NOT_VERIFIED` | Resolve the named blocker; route material contract, plan, or design uncertainty to Tech Lead for classification |
| `CHANGES_REQUESTED` | Evaluation is not blocked and at least one criterion is `FAIL` or a `MUST_FIX` defect exists | Return the same ticket and ticket-bound findings to Developer; the controller records a rework event |
| `PASS` | Evaluation is not blocked, every required criterion is `PASS` or justified `NOT_APPLICABLE`, and no `MUST_FIX` finding exists | Request progression under the authoritative workflow policy |

`BLOCKED` takes precedence when conditions overlap. Any observed `FAIL` or
`MUST_FIX` remains recorded even when the final verdict is `BLOCKED`.

Under the adopted ticket lifecycle, QA `PASS` requests `Done` when the
authoritative workflow policy identifies QA as the final required gate. A human
or Lifecycle Controller performs that transition after the comment is durable.
If policy requires another gate, QA requests that gate instead. QA never mutates
tracker workflow state itself.

After QA `CHANGES_REQUESTED`, Developer works on the same ticket and produces a
new exact implementation revision. That revision follows the normal Developer
`COMPLETE` → Code Review `PASS` → QA sequence again; QA does not send failed
implementation back to Code Review.

### Completion boundary

QA finishes when every acceptance criterion has exactly one matrix result, the
verdict follows the precedence rules, uncertainty is explicit, the mandatory
comment is prepared or posted, and the next owner has one exact action. It does
not implement fixes, redefine requirements, approve architecture, combine
tickets, or execute tracker transitions.

## 8. Rework limit and Tech Lead — BLOCKER_REVIEW

### Intent

Pause unproductive ticket cycling, classify an evidence-backed technical
blocker, and prepare a proposed resolution for mandatory human review. Rework
count is a workflow trigger, not evidence of the blocker cause.

### Trigger and input

The Lifecycle Controller triggers `BLOCKER_REVIEW` when the configured
ticket-rework limit is reached. A material ticket, dependency, requirements,
plan, or suspected architecture blocker may trigger it earlier without waiting
for the limit.

Provide the active ticket and Plan ID/revision, expected and observed behavior,
attempts, tests, logs, Developer/Code Review/QA comments and findings, applicable
accepted decisions, affected components, and work already completed.

### Output and mandatory human decision

Tech Lead assigns exactly one primary classification:

- `IMPLEMENTATION_DEFECT`;
- `PLAN_GAP`;
- `SUSPECTED_ARCHITECTURE_ISSUE`;
- `REQUIREMENTS_GAP`;
- `INSUFFICIENT_EVIDENCE`.

Use [`blocker-review.md`](../skills/d2269-tech-lead/assets/blocker-review.md) to record
the classification, evidence, retained work, proposed resolution, material
alternatives, scope and external-sync impact, recommended next role, and one
exact human decision request.

Every `BLOCKER_REVIEW` ends in `HUMAN_REVIEW_REQUIRED`. Tech Lead does not resume
Developer, publish a proposed plan revision, invoke Architect or another role,
or request a tracker transition before the human decision is recorded. The
human may authorize resumption, replanning or decomposition, Architect review,
additional investigation or project work, deferment, or stop.

### Completion boundary

`BLOCKER_REVIEW` is complete when its classification is supported by evidence,
preserved work and impact are explicit, and the human has one concrete decision
to make. The result is a decision package, not authorization to execute its
recommendation.

## 9. Tech Lead — COMPLETENESS_REVIEW

### Intent

Determine whether the complete implementation scope satisfies its approved
Implementation Plan and technical completion obligations. This is a scope-level
review after ticket delivery, not another per-ticket Code Review or QA pass.

### Trigger and input

Invoke `COMPLETENESS_REVIEW` after implementation evidence exists for the defined
plan or task set. Provide:

- approved Implementation Plan and child-task specifications;
- system-level definition of done;
- Architect-required verification evidence when applicable;
- current exact implementation revision for every required task;
- Developer implementation evidence;
- current-revision Code Review and QA verdicts or authorized waivers;
- relevant tests, schemas, contracts, migrations, documentation, metrics, and
  operational evidence;
- declared deviations and their approval source.

An earlier `PASS` does not cover a task changed after that verdict. Tech Lead
records Code Review and QA results as independent evidence and does not replace
or overrule them.

### Work

Tech Lead:

1. Maps every required plan item and technical completion criterion to inspected
   implementation evidence.
2. Verifies dependency completion, supported intermediate states, interfaces,
   schemas, migrations, compatibility, tests, documentation impact, and material
   operational requirements.
3. Classifies deviations as approved implementation-level variation, plan gap,
   incomplete implementation, suspected architecture issue, or undocumented
   scope change.
4. Determines whether Architect conformance is required.
5. Issues one technical-completeness verdict and one exact next action.
6. For consequential scope, prepares a complete evidence pack for a fresh
   Architect `CONFORMANCE_REVIEW` invocation.

### Output and next action

Use
[`technical-completeness-review.md`](../skills/d2269-tech-lead/assets/technical-completeness-review.md)
to return the review basis, completion matrix, deviations, independent verdicts,
conformance applicability, evidence pack when required, and handoff.

| Verdict | Meaning | Next action |
| --- | --- | --- |
| `TECHNICALLY_COMPLETE` | Required technical work and evidence are complete | Consequential scope → Architect `CONFORMANCE_REVIEW`; otherwise → human merge or release authority |
| `CHANGES_REQUIRED` | Named implementation or plan work remains | Route the named work to Developer, Tech Lead `PLAN`, Code Review, or QA according to the identified gap |
| `NOT_VERIFIABLE` | Evidence or access is insufficient for a defensible judgment | Route to the owner of the missing bounded evidence |

A scope is consequential when it implements an accepted architecture decision
or Architect workstream, or affects a named system boundary, public or
cross-component contract, quality attribute, or migration decision. Otherwise
Architect conformance is optional unless repository policy or the human owner
requires it.

### Architect conformance evidence pack

When conformance is required, the Tech Lead output includes:

- accepted decision IDs;
- implemented Task IDs and their exact revisions;
- affected boundaries and contracts;
- relevant code, schema, and migration paths;
- tests, metrics, and operational evidence;
- approved deviations;
- unverified areas and residual risks.

Every field must be populated or marked `N/A` with a reason. Tech Lead does not
issue an architecture-conformance verdict or grant merge authority.

### Completion boundary

`COMPLETENESS_REVIEW` is complete when every required task is accounted for, the
technical verdict is traceable to named evidence, deviations and gaps are
classified, and the next role receives a fresh-session handoff.

## 10. Architect — CONFORMANCE_REVIEW

### Intent

Determine whether a completed consequential scope conforms to the accepted
Architecture Baseline and decision records. This is an architecture-level audit,
not product acceptance, ordinary diff review, or final merge approval.

Run this as a separate invocation from Architect `DESIGN` for the same scope. A
fresh context that did not design or implement the scope is strongly preferred.
Prior participation must be disclosed and requires stronger implementation
evidence.

### Trigger and input

The normal trigger is a Tech Lead `TECHNICALLY_COMPLETE` verdict plus a finding
that the scope is consequential. Provide:

- completed scope and system-level definition of done;
- accepted Architecture Baseline and decision records;
- Tech Lead Technical Completeness Review and conformance evidence pack;
- relevant implementation, contracts, schemas, migrations, tests, metrics, and
  operational evidence;
- known deviations and their approvals.

### Work

Architect:

1. Maps accepted architecture expectations to implementation evidence.
2. Inspects component boundaries, ownership, public and cross-component
   contracts, data flow, migration behavior, and applicable quality attributes.
3. Classifies differences as approved intentional deviation, accidental
   architecture drift, incomplete implementation, or documentation drift.
4. Identifies systemic risks and architecture debt without duplicating ordinary
   Code Review or QA findings.
5. Issues exactly one conformance verdict.
6. Identifies decision statuses and architecture documents that evidence
   supports changing.
7. Produces a durable architecture close-out after establishing the verdict.
8. Assigns every required follow-up to one owner.

### Output and next action

Use
[`architecture-conformance-review.md`](../skills/d2269-architect/assets/architecture-conformance-review.md)
to return the review basis, conformance matrix, prioritized systemic findings,
decision and documentation status, durable close-out, residual risks,
architecture debt, and handoff.

The verdict is exactly one of:

- `ALIGNED`;
- `ALIGNED_WITH_DEVIATIONS`;
- `NOT_ALIGNED`;
- `NOT_VERIFIABLE`.

Architect may mark an accepted decision `IMPLEMENTED` only when its validation
criteria are verified. Ticket or workflow status alone is not evidence.

When repository writes are authorized, Architect updates supported decision
statuses and current, target, or partially implemented architecture labels only
after the verdict. Otherwise it returns file-ready close-out changes with exact
target paths. Unsupported areas remain explicitly stale or unverified.

Blocking implementation work returns to Tech Lead, acceptance gaps return to QA,
diff-local findings return to Code Review, and approval questions go to the human
owner. Architect does not implement remediation or grant merge/release authority.

### Completion boundary

`CONFORMANCE_REVIEW` is complete when its verdict is traceable to evidence,
unverified areas are explicit, deviations are classified, systemic findings are
prioritized, every required follow-up has one owner, and the durable architecture
baseline is synchronized or exact file-ready changes are supplied.

## 11. Human decision and close-out

### Intent

Apply the final authority that the reasoning roles do not own. Human review is
the terminal decision point for merge, release, remediation, replanning, or
stopping the scope.

### Input

- Tech Lead Technical Completeness Review
- Architect Conformance Review when required
- Durable Code Review and QA verdicts
- Unresolved risks, deviations, blockers, and requested decisions
- Applicable repository and release policy

### Output

The human records one authorized outcome and its next action, such as merge or
release, remediation, replanning, another bounded review, deferment, or stop. A
human decision may create a new scope or return named work to an earlier role; it
does not retroactively change the semantic verdicts already recorded.

## Scope-completion flow

```text
All required ticket evidence is available
                |
                v
    Tech Lead COMPLETENESS_REVIEW
                |
                +-- CHANGES_REQUIRED / NOT_VERIFIABLE --> named owner
                |
                `-- TECHNICALLY_COMPLETE
                            |
                            +-- non-consequential --> Human decision / close-out
                            |
                            `-- consequential
                                    |
                                    v
                      Architect CONFORMANCE_REVIEW
                                    |
                                    v
                         Human decision / close-out
```

The abbreviated consequential path is:

```text
Tech Lead COMPLETENESS_REVIEW
        ↓
Architect CONFORMANCE_REVIEW
        ↓
Human decision / close-out
```

## Lifecycle contract summary

The `Trigger / gate` column is intentionally separate from `Input`: possessing
an artifact does not by itself authorize the next role invocation.

| Stage | Role or workflow actor | Mode / specification | Trigger / gate | Input | Output | Next recipient or action |
| --- | --- | --- | --- | --- | --- | --- |
| Product definition | Human / product owner | Product / Task Specification | A product need or requested change exists | Business context, expected result, known requirements and constraints | Objective, scope, non-goals, acceptance criteria, system DoD, decision owner and authority | Architect `DESIGN` |
| Architecture design | Architect | `DESIGN`;<br>Architecture Overview;<br>decision records;<br>Architecture Handoff | Product outcome and known constraints are recorded | Product / Task Specification, existing architecture, code and contracts when available | Architecture Baseline;<br>ADRs and their status;<br>workstreams and dependencies;<br>risks and verification expectations;<br>fresh-session handoff | `ACCEPTED` package<br>↳ Tech Lead `PLAN`<br><br>`PROPOSED` decision<br>↳ named decision owner<br><br>Missing product input<br>↳ human owner |
| Implementation planning | Tech Lead | `PLAN`;<br>Implementation Plan;<br>Implementation Task specifications | Required product intent and binding architecture decisions are available | Product specification, accepted architecture, workstreams, repository evidence, workflow policy | One plan with `READY_FOR_IMPLEMENTATION`, `DRAFT`, or `BLOCKED`;<br>one `READY` or `BLOCKED` specification per child ticket;<br>optional publication receipt | `READY_FOR_IMPLEMENTATION`<br>↳ ticket selection<br><br>Architecture gap<br>↳ Architect / decision owner<br><br>Product gap<br>↳ human owner |
| Ticket selection | Human workflow owner / Lifecycle Controller | Deterministic selection policy | Parent plan is `READY_FOR_IMPLEMENTATION` and at least one child ticket is executable | Ready tasks, dependencies, sequencing, priority policy, parallel groups, tracker mappings when authoritative | Exactly one current executable `READY` ticket per Developer invocation | Developer |
| Implementation | Developer | Implementation Task;<br>Implementation Report | Exactly one current `READY` Developer ticket with satisfied blocking dependencies | Ticket contract, comments, relevant code/tests, ticket-linked sources | Code, tests, affected docs, exact revision, report, durable comment;<br>result: `COMPLETE`, `PARTIAL`, or `BLOCKED` | `COMPLETE`<br>↳ Code Review<br><br>Valid Code Review waiver<br>↳ QA<br><br>`PARTIAL` or `BLOCKED`<br>↳ named owner or Tech Lead |
| Engineering review | Code Review | Code Review Report | Developer `COMPLETE`, exact target, matching artifacts, durable Developer comment, independent reviewer context | One ticket, implementation report, exact diff/revision, code, tests, comments and required evidence | Findings, verification evidence, durable comment;<br>verdict: `PASS`, `CHANGES_REQUESTED`, or `BLOCKED` | `PASS`<br>↳ QA<br><br>`CHANGES_REQUESTED`<br>↳ Developer<br><br>`BLOCKED`<br>↳ named owner or Tech Lead |
| Acceptance evaluation | QA | QA Report | Developer `COMPLETE` plus matching Code Review `PASS`, or valid revision-bound waiver | One ticket, exact revision, implementation and review evidence, acceptance criteria, tests and comments | Acceptance matrix, findings, durable comment;<br>verdict: `PASS`, `CHANGES_REQUESTED`, or `BLOCKED` | `PASS`<br>↳ policy-defined Done or next gate<br><br>`CHANGES_REQUESTED`<br>↳ Developer<br><br>`BLOCKED`<br>↳ named owner or Tech Lead |
| Technical blocker review | Tech Lead | `BLOCKER_REVIEW`;<br>Blocker Review | Material technical blocker or configured ticket-rework limit | Active ticket and plan revision, observed failure, attempts, tests, logs, role comments/findings, accepted decisions and retained work | Evidence-backed classification;<br>proposal and alternatives;<br>impact and retained work;<br>`HUMAN_REVIEW_REQUIRED` | Every result<br>↳ human decision owner<br><br>Tech Lead does not execute the recommendation |
| Technical scope close-out | Tech Lead | `COMPLETENESS_REVIEW`;<br>Technical Completeness Review | Implementation evidence exists for the defined plan/task set | Approved plan/tasks, current revisions, system DoD, Developer evidence, Code Review/QA verdicts, tests, migrations, docs and operations evidence | Completion matrix and deviations;<br>verdict: `TECHNICALLY_COMPLETE`, `CHANGES_REQUIRED`, or `NOT_VERIFIABLE`;<br>conformance evidence pack when required | `TECHNICALLY_COMPLETE` + consequential scope<br>↳ Architect `CONFORMANCE_REVIEW`<br><br>`TECHNICALLY_COMPLETE` + non-consequential scope<br>↳ human close-out<br><br>`CHANGES_REQUIRED` or `NOT_VERIFIABLE`<br>↳ named role or evidence owner |
| Architecture close-out | Architect | `CONFORMANCE_REVIEW`;<br>Architecture Conformance Review | Scope is technically complete and consequential, or policy/human explicitly requires conformance | Accepted baseline/ADRs, completeness review and evidence pack, implementation/contracts/migrations/tests/metrics, approved deviations | Conformance matrix and systemic findings;<br>durable architecture close-out;<br>verdict: `ALIGNED`, `ALIGNED_WITH_DEVIATIONS`, `NOT_ALIGNED`, or `NOT_VERIFIABLE` | Completed review and approval questions<br>↳ human decision<br><br>Blocking implementation work<br>↳ Tech Lead<br><br>Acceptance gap<br>↳ QA<br><br>Diff-local issue<br>↳ Code Review |
| Final authority | Human | Decision / close-out record | Required technical and architecture reviews are available | Review artifacts, risks, deviations, blockers and applicable policy | One recorded decision:<br>merge/release;<br>remediation;<br>replan or further review;<br>defer or stop | Close the scope<br>or<br>invoke the named follow-up |

## Pending hardening before controlled pilot

- Define verdict precedence for overlapping known incompleteness and missing
  evidence in `COMPLETENESS_REVIEW`.
- Define exact verdict boundaries and precedence for Architect
  `CONFORMANCE_REVIEW`.
- Add behavioral eval cases for Architect modes, especially
  `CONFORMANCE_REVIEW`.
- Run one focused independent audit of the interface between the two close-out
  modes rather than re-auditing all role behavior.
