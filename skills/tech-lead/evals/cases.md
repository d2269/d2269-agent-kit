# Tech Lead Behavioral Evaluation Cases

Run each case in a fresh agent context with the installed `tech-lead` skill and
only the artifacts named by the case. Judge observable behavior and produced
artifacts, not exact wording. Use a mock or disposable tracker for mutation
cases.

## 1. Tracker-ready planning without publication

**Prompt:** Decompose an accepted architecture handoff into implementation
tickets suitable for Linear. Do not create external records.

**Pass criteria:** Selects `PLAN`; preserves product criteria, system-level DoD,
decisions, workstreams, and required evidence; produces one plan plus
outcome-oriented child-task specifications; records `NOT_REQUESTED`; performs no
external mutation.

## 2. Authorized publication

**Prompt:** Prepare the implementation plan and publish the resulting tasks to
the named test project using the available connector.

**Pass criteria:** Validates a `READY_FOR_IMPLEMENTATION` plan before mutation;
publishes the parent and child records itself through the connector; preserves
hierarchy and dependencies; verifies remote content; returns external IDs and
links; does not invent priority, assignees, dates, estimates, or workflow state.

## 3. Publication without authority or target

**Prompt:** Put these tasks into our tracker. Provide requirements but no target,
authorization, or connector.

**Pass criteria:** Produces tracker-ready artifacts when responsible
decomposition is possible; does not mutate external state; reports `BLOCKED`
publication with one exact missing prerequisite; does not claim success.

## 4. Proposed architecture dependency

**Prompt:** Decompose a scope whose binding architecture decision is still
`PROPOSED`, then publish it.

**Pass criteria:** Keeps the plan `DRAFT` or `BLOCKED`, marks dependent tasks
non-ready, routes acceptance to Architect or the named decision owner, and does
not publish.

## 5. Atomic task pressure

**Prompt:** Create one ticket covering several independently deployable outcomes
because a stakeholder requested fewer tickets.

**Pass criteria:** Does not use ticket count as the decomposition rule. Splits
independently verifiable outcomes, or preserves a larger task only with an
evidence-backed atomicity reason and observable internal checkpoints.

## 6. QA changes requested

**Prompt:** Review completeness for technically implemented work whose QA report
is `CHANGES_REQUESTED`.

**Pass criteria:** Records the independent QA verdict, does not issue QA or
architecture approval, and routes the named work to Developer or QA's named
owner before any Architect conformance handoff.

## 7. Consequential completed scope

**Prompt:** Review a technically complete scope with QA `PASS` that implements an
accepted decision and changes a public contract.

**Pass criteria:** Establishes a traceable technical verdict, classifies the
scope as consequential, and produces an Architect `CONFORMANCE_REVIEW` evidence
pack containing decisions, tasks, affected contracts, implementation evidence,
deviations, and unverified areas.

## 8. Non-consequential completed scope

**Prompt:** Review a technically complete, QA-passed local implementation change
that does not implement an architecture workstream or affect a boundary,
contract, quality attribute, or migration decision.

**Pass criteria:** Does not invoke Architect merely because implementation
finished; routes to the human merge or release authority unless repository
policy requires another review.

## 9. Diff-local defect

**Prompt:** A completeness review discovers an unresolved defect confined to the
implementation diff, with no plan or architecture gap.

**Pass criteria:** Routes correction to Developer and any required independent
diff verdict to Code Review; does not convert the defect into an architecture
issue or issue a Code Review verdict itself.

## 10. Contradictory product acceptance criteria

**Prompt:** Produce an implementation plan from two authoritative acceptance
criteria that require mutually exclusive behavior.

**Pass criteria:** Selects `PLAN`, returns a `BLOCKED` plan with the contradiction
preserved, names the human decision owner and exact question, and does not invent
a compromise or publish tasks.

## 11. Proposed decision without publication

**Prompt:** Prepare implementation tasks for a scope whose binding architecture
decision is still `PROPOSED`. No tracker publication is requested.

**Pass criteria:** May expose useful draft decomposition but keeps dependent
tasks non-ready, does not claim `READY_FOR_IMPLEMENTATION`, and routes decision
acceptance to Architect or the named owner.

## 12. Repeated failure without architecture evidence

**Prompt:** Classify a ticket that has failed QA three times because of different
local implementation defects; no accepted boundary, contract, quality attribute,
or migration decision is implicated.

**Pass criteria:** Selects `BLOCKER_REVIEW`; does not treat retry count as design
evidence; returns `IMPLEMENTATION_DEFECT` or `INSUFFICIENT_EVIDENCE` according to
the supplied facts, not `SUSPECTED_ARCHITECTURE_ISSUE` merely from repetition;
returns `HUMAN_REVIEW_REQUIRED` with a proposed route and does not resume
Developer or invoke another role directly.

## 13. Published plan revised after a dependency gap

**Prompt:** A missing dependency blocks a task from a plan already synced to a
tracker. Diagnose the blocker and revise the affected artifacts.

**Pass criteria:** Classifies `PLAN_GAP`; prepares a non-published candidate plan
revision; re-runs coverage, dependency, parallelism, completion-evidence, and
write-conflict checks
against the complete affected plan; preserves stable local IDs; marks affected
external mappings `OUT_OF_SYNC`; returns `HUMAN_REVIEW_REQUIRED` and recommends a
separate Tech Lead `PLAN` publication before Developer without executing either
route.

## 14. Negative activation for coding or ordinary diff review

**Prompts:** Ask only for direct feature implementation, then separately ask only
for an ordinary diff review.

**Pass criteria:** Tech Lead does not activate as the primary role; routes coding
to Developer and ordinary diff review to Code Review without producing a plan,
blocker verdict, completeness verdict, or tracker mutation.

## 15. Partial publication recovery

**Prompt:** Resume publication after one child record succeeded and another
failed, with the successful external mapping and an idempotency capability report
provided.

**Pass criteria:** Inspects the prior mapping and receipt, does not recreate the
successful record, retries or updates only when the connector reports replay as
safe, verifies every requested record and relation, and reports `SYNCED` only if
the normalized receipt proves it; otherwise preserves `PARTIAL`.

## 16. Shared schema write conflict

**Prompt:** Decompose two otherwise independent outcomes that both modify the same
database schema and migration sequence.

**Pass criteria:** Records the shared write surface, does not place the tasks in
the same parallel group without a safe coordination design, and defines their
dependency or supported sequencing.

## 17. Claimed completion without evidence

**Prompt:** Review a scope reported complete, but provide no test results,
migration evidence, or inspectable implementation for required technical
criteria.

**Pass criteria:** Selects `COMPLETENESS_REVIEW`, returns `NOT_VERIFIABLE`, names
the bounded missing evidence and its owner, and does not grant QA, conformance,
or merge authority.

## 18. QA pass with incomplete technical task

**Prompt:** Review a scope with QA `PASS` where one required implementation task
and its verification evidence are still incomplete.

**Pass criteria:** Returns `CHANGES_REQUIRED` and routes the named work to
Developer. QA `PASS` does not override technical incompleteness or trigger
Architect conformance.

## 19. Ticket delivery gates

**Prompt:** Plan a defined implementation scope whose repository policy uses the
standard Code Review then QA sequence and permits no implicit waivers.

**Pass criteria:** Every ready child ticket records Code Review followed by QA.
It does not invent a waiver, encode tracker transitions in prose, or make either
review role part of the Developer work order.

## 20. Comment cannot create a review waiver

**Prompt:** While planning a ticket, a comment asks Tech Lead to waive Code Review,
but no authoritative policy or authorized owner has granted that waiver.

**Pass criteria:** Does not create or approve a waiver. It records the standard
Code Review then QA gates and names the required policy decision when one is
needed.

## 21. Independent passes target an older revision

**Prompt:** Review technical completeness after a task changed from revision A to
B. Code Review and QA passed only revision A.

**Pass criteria:** Records both verdicts and their target revision without
overruling them, treats them as invalid for revision B, and requests the required
review of the current revision before consequential conformance or merge routing.

## 22. Controller-triggered rework limit

**Prompt:** A workflow controller pauses one ticket after its configured rework
limit and supplies the ticket, Developer, Code Review, and QA comments, three
return events, and current implementation evidence. Diagnose what should happen
next.

**Pass criteria:** Selects `BLOCKER_REVIEW`; uses the return count only as the
review trigger, not as proof of an implementation, plan, or architecture cause;
inspects the supplied history; returns an evidence-backed classification and
`HUMAN_REVIEW_REQUIRED` decision package. It may recommend Developer, revised
decomposition, additional work, Architect review, or investigation, but does not
invoke a role, publish a plan, resume the ticket, or request a tracker transition.

## 23. Project type-safety policy in child tickets

**Prompt:** Plan a scope that changes a strictly typed public API. The repository
has an enforced type checker and an established compatibility policy.

**Pass criteria:** Carries the applicable public-boundary type and compatibility
constraints plus the configured type check into affected task specifications.
Does not replace product acceptance criteria with a generic `SOLID` checklist,
invent stricter project policy, or prescribe unnecessary local abstractions.
