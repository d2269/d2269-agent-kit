# Role Model

This document defines the collaboration model for D2269 Agent Kit. It exists so multiple agents can work on the same task without silently taking over each other's responsibilities.

Roles are **reasoning procedures**, not process supervisors and not model assignments. Any compatible agent runtime may invoke any role. Model selection is outside this kit.

Installed packages use namespaced names such as `d2269-architect`; lifecycle
records use stable role IDs such as `architect`. The package name selects the
skill, while the role ID identifies the protocol participant. See
[Installation](installation.md#canonical-skill-names) for the complete mapping.

Not every request uses the complete role chain. The
[execution profiles](execution-profiles.md) select a proportional route without
changing these role boundaries. One coherent role may span multiple fresh
sessions when its durable artifact preserves progress and the objective,
authority, tools, and output contract have not changed.

The role chain is implemented by the optional local Lifecycle Controller. The
role boundaries remain valid for manual execution without the controller.

```text
Researcher (optional)
        ↓
Architect DESIGN
        ↓
    Tech Lead
        ↓
Developer
  └─ COMPLETE → Code Review
                  ├─ CHANGES_REQUESTED → Developer
                  └─ PASS → QA
                              ├─ CHANGES_REQUESTED → Developer
                              └─ PASS → policy-defined next gate / Done

Completed scope, when policy requires it
  └─ Tech Lead COMPLETENESS
       └─ consequential scope → Architect CONFORMANCE
                                  └─ Human review / merge
```

The branches are feedback outcomes, not parallel review stages. A valid Code
Review waiver bound to the current ticket revision in an authoritative contract
source may route the exact Developer revision directly to QA.

Failures may return work to an earlier role. The controller pauses repeated
rework at a policy-defined limit and requests Tech Lead `BLOCKER_REVIEW`; the
count is a trigger, not a diagnosis. Evidence of a design-level issue may lead to
Architect `ESCALATION_REVIEW`, but only after the blocker review is presented to
the mandatory human decision gate. Orchestrator may recommend routing when the
next role is ambiguous. Humans remain the merge authority.

Architect lifecycle stages are separate invocations. In particular, `DESIGN` and
`CONFORMANCE_REVIEW` for the same scope must not be combined into one invocation;
post-scope conformance should preferably use a fresh context.

## Shared rules

- A role must not silently perform another role's primary job.
- Cross-role collaboration is expected; ownership stays explicit.
- Outputs follow the [handoff contract](handoff-contract.md).
- Deterministic workflow plumbing (retries, locks, queues, status mutation, process spawning) does not belong in these roles.
- Do not encode model-family preferences inside a role.

## Architect

**Primary responsibility:** System-level technical reasoning across three modes:
pre-implementation `DESIGN`, evidence-driven `ESCALATION_REVIEW`, and
post-scope `CONFORMANCE_REVIEW`.

**Inputs:** Business/technical objective, system-level definition of done,
constraints, explicit decision authority, existing architecture and decision
records, research findings, escalation evidence, or completed-scope
implementation evidence.

**Outputs:** A minimal durable architecture baseline, semantic decision records,
outcome-oriented technical workstreams, interface and ownership boundaries,
risks, migration strategy, and a mode-specific handoff or verdict. Templates:
[`design handoff`](../skills/d2269-architect/assets/architecture-handoff.md),
[`escalation review`](../skills/d2269-architect/assets/architecture-escalation-review.md),
and
[`conformance review`](../skills/d2269-architect/assets/architecture-conformance-review.md).
Conformance also closes the durable baseline by applying supported
architecture-documentation changes when writes are authorized, or by returning
file-ready changes with exact paths.

**Authority:** Propose architecture decisions and bind them only within explicit
delegated authority documented in the current request, input handoff, or
applicable repository policy; otherwise the named decision owner accepts them.
Only the named decision owner may reject a proposal. Define system boundaries
and epic-level technical structure using the least complex architecture that
satisfies current requirements and quality attributes. Request Researcher work
for broad missing evidence. Require Tech Lead to plan implementation against
accepted decisions.
Architect may always produce proposed, file-ready artifacts; repository writes
require an explicit create/update request or applicable repository policy.

**Prohibited:** Routine feature implementation, minor bug fixes, ordinary code
review, file-level task planning, routine QA, or changing an architecture verdict
while editing documentation after the assessment.

**Typical escalation target:** Human operator when product intent, decision
authority, or approval is missing or conflicting. Researcher for a bounded broad
investigation. Tech Lead when an apparent escalation is implementation-level.

## Tech Lead

**Primary responsibility:** Implementation-level technical leadership across
three modes: spec-driven `PLAN`, evidence-driven `BLOCKER_REVIEW`, and post-scope
`COMPLETENESS_REVIEW`.

**Inputs:** Objective, unchanged product acceptance criteria, system-level
definition of done, accepted Architect decisions, workstreams, and required
verification evidence when applicable, repository code, active task and blocker
evidence, supplied ticket history and workflow trigger, or completed-scope
implementation evidence and independent review outputs.

**Outputs:** A traceable
[`implementation plan`](../skills/d2269-tech-lead/assets/implementation-plan.md), one
[`implementation task specification`](../skills/d2269-tech-lead/assets/implementation-task.md)
per child task, an evidence-backed
[`blocker review`](../skills/d2269-tech-lead/assets/blocker-review.md), or a
[`technical completeness review`](../skills/d2269-tech-lead/assets/technical-completeness-review.md).
A consequential technically complete scope includes an evidence pack for
Architect `CONFORMANCE_REVIEW`. When explicitly authorized and an appropriate
connector is available, Tech Lead may also publish the validated plan and child
tasks and return a provider-neutral receipt with verified local-to-external ID
and plan-revision mappings. `BLOCKER_REVIEW` instead returns
`HUMAN_REVIEW_REQUIRED`: an evidence-backed classification, proposed resolution,
material alternatives, scope impact, recommended next role, and one exact human
decision request.

**Authority:** Define implementation-level scope, sequencing, dependencies,
parallelization, technical completion criteria, applicable repository engineering
constraints, and tracker-ready task semantics.
After the plan is ready, publish or update those artifacts in a named tracker
when external mutation is explicitly authorized. Judge technical completeness
and recommend that evidence of a suspected architecture issue be sent to
Architect, which owns the final architecture classification. A blocker-review
recommendation is not binding until a human records the decision.

**Prohibited:** Project management, choosing priority, assignments, schedules, or
workflow state without authoritative input, unauthorized external mutation,
implementing connector retry or lifecycle logic in prose, routine implementation
when Developer is sufficient, independent acceptance QA, ordinary diff review,
changing product acceptance criteria, or reopening accepted architecture. Tech
Lead must not resume work, publish a blocker-driven plan revision, invoke a
recommended role, or request a tracker transition directly from
`BLOCKER_REVIEW` before the mandatory human decision.

**Typical escalation target:** Every `BLOCKER_REVIEW` goes first to its named
human decision owner. Tech Lead may recommend Architect `ESCALATION_REVIEW` for
an evidenced suspected architecture issue, not for failure count alone;
Developer for implementation; QA for acceptance verification; or another
bounded investigation. The human may instead require revised decomposition,
additional project work, or another route.

## Developer

**Primary responsibility:** Implement exactly one ticket whose implementation
readiness is `READY`. This is a semantic contract field, not tracker workflow
state. The ticket is the sole work contract.

**Inputs:** One provider-native or portable implementation ticket assigned to
Developer and containing or authoritatively linking its requirements, acceptance
criteria, recorded parent plan revision, accepted decisions, dependencies,
technical completion criteria, verification obligations, and any QA or
code-review findings. Repository
instructions, inspected code and tests, and ticket comments are supporting
context rather than additional work orders.

**Outputs:** In-scope code, tests, directly affected documentation, ticket-linked
implementation report, verification evidence, deviations, a mandatory
ticket-history comment with a verified receipt or `READY_TO_POST` text, and a
next-owner handoff. Code Review receives only a `COMPLETE` implementation and its
exact diff; QA may receive it directly only under a recorded authorized Code
Review waiver. Blockers go to Tech Lead. Template:
[`skills/d2269-developer/assets/implementation-report.md`](../skills/d2269-developer/assets/implementation-report.md).

**Authority:** Change production code and tests in ticket scope. Update
documentation directly affected by the change. Choose local implementation
details that do not reopen architecture, using the simplest sufficient design
and preserving applicable type safety on the changed surface. Read accessible
ticket comments and, when external mutation is explicitly authorized, post
necessary context or handoff comments through an available connector and verify
their receipts.

**Prohibited:** Starting without one `READY` Developer ticket, combining tickets,
treating plans or comments as separate work orders, allowing comments to change
scope without an authorized ticket revision, changing tracker workflow state,
declaring QA success, silently making major architecture decisions, hiding
failing tests, or speculative unrelated refactors.

**Typical escalation target:** Tech Lead `BLOCKER_REVIEW` for an invalid, stale,
incomplete, or conflicting ticket, dependency failure, implementation-level
disagreement, or evidence of a possible architecture or requirements issue. Tech
Lead presents its classification and proposed route to the mandatory human
decision gate. Developer may contribute ticket context to Architect only if the
recorded decision requests that review.

## QA

**Primary responsibility:** Independently determine whether one Developer ticket
with a `COMPLETE` implementation result and matching Code Review `PASS` or
authorized waiver satisfies its bound acceptance criteria and is safe to
progress. The ticket is the sole evaluation contract.

**Inputs:** One ticket, its matching `COMPLETE` Developer implementation report,
the exact diff or implementation revision, a Code Review `PASS` and durable
history comment for that exact target or an explicit ticket-revision-bound waiver
from an authoritative contract source, applicable to the evaluation target and
naming the permitting policy and authorized owner,
surrounding code, available tests and actual results, accessible comments, and
required ticket-linked evidence.

**Outputs:** Ticket identity, evaluation target, acceptance matrix, verification
evidence, actionable findings, exactly one verdict (`PASS`,
`CHANGES_REQUESTED`, or `BLOCKED`), a mandatory ticket-history comment with a
verified receipt or `READY_TO_POST` text, and a requested workflow action. The
comment distinguishes passed, failed, and unverified checks. Template:
[`skills/d2269-qa/assets/qa-report.md`](../skills/d2269-qa/assets/qa-report.md).

**Authority:** Own the semantic acceptance verdict, ticket-bound finding and
comment content, and requested next action. State what was not verified. Request
`Done` only when authoritative workflow policy makes QA the terminal gate.

**Prohibited:** Combining tickets, reconstructing scope from plans or chat,
silently implementing fixes, redefining requirements, changing tracker workflow
state, approving with a required unverified criterion, failing solely for style,
or replacing Code Review.

**Typical escalation target:** Developer for `CHANGES_REQUESTED`, after actionable
findings are durable. Tech Lead when artifacts disagree, technical completeness
is disputed, or material evidence suggests the ticket's technical contract or
accepted design may be wrong; Tech Lead may recommend Architect
`ESCALATION_REVIEW`, subject to the mandatory human decision. Human when
requirements are missing or conflicting. The named owner handles access,
environment, authorization, or workflow-policy blockers.

## Researcher

**Primary responsibility:** Evidence-driven investigation that supports later decisions.

**Inputs:** Research question, completion or stopping conditions, known
constraints, repository access, optional web access, and the current Research
Report when continuing a long-running investigation.

**Outputs:** Report status, findings, evidence, alternatives, trade-offs,
unknowns, recommendation, confidence, source references when external sources
were used, and a continuation checkpoint when the investigation is still in
progress. Template:
[`skills/d2269-researcher/assets/research-report.md`](../skills/d2269-researcher/assets/research-report.md).

**Authority:** Report facts, conflicts, and recommendations. Work offline when the network is unavailable.

**Prohibited:** Production implementation while operating as Researcher. An
explicit implementation request becomes a Developer handoff after the report,
not an in-place role change. Treating a recommendation as an Architect decision.
Fabricating citations.

**Typical escalation target:** Architect or Tech Lead, depending on who asked for the research. Human when the question is product-level rather than technical.

## Orchestrator

**Primary responsibility:** Reasoning policy for ambiguous routing, handoff interpretation, and escalation decisions.

**Inputs:** Structured role outputs, stated objective, known blockers, missing artifacts.

**Outputs:** Recommended next role and action, escalation and human-input flags, compact handoff context. Template: [`skills/d2269-orchestrator/assets/orchestrator-decision.md`](../skills/d2269-orchestrator/assets/orchestrator-decision.md).

**Authority:** Recommend a next role. Identify contradictions, missing prerequisites, and stuck work. Recommend human intervention.

**Prohibited:** Launching processes, polling or mutating trackers, counting retries in prose, scheduling, locking, supervising processes, maintaining persistent workflow state, replacing other roles' technical reasoning, acting as a project manager.

**Typical escalation target:** Human operator. Architect when the ambiguity is a design problem rather than a routing problem.

## Code Review

**Primary responsibility:** Independently judge the exact implementation revision
for one ticket with a matching `COMPLETE` Developer result. Code Review is the
ticket-level lifecycle gate between Developer and QA unless authoritative
workflow policy explicitly waives it. The ticket is the sole review contract.

**Inputs:** One ticket, its matching `COMPLETE` Developer report and verified
history-comment publication receipt, exact diff or implementation revision,
reviewer provenance proving the current context did not implement that target,
relevant code and tests, actual results, accessible comments, and required
ticket-linked evidence.

**Outputs:** Review target and scope, evidenced must-fix and non-blocking findings,
questions, verification evidence, exactly one verdict (`PASS`,
`CHANGES_REQUESTED`, or `BLOCKED`), a mandatory ticket-history comment with a
verified receipt or `READY_TO_POST` text, and a requested workflow action.
Template:
[`skills/d2269-code-review/assets/code-review-report.md`](../skills/d2269-code-review/assets/code-review-report.md).

**Authority:** Own the engineering verdict, ticket-bound findings and comment
content, and requested next action. `PASS` requests progression of the exact
reviewed revision to QA.

**Prohibited:** Combining tickets, reconstructing scope from plans or chat,
modifying code or tests, product acceptance QA, architecture approval, tracker
workflow mutation, merge, or review by the context that implemented the target.

**Typical escalation target:** Developer for evidenced must-fix findings. Tech
Lead for artifact mismatch, disputed completeness, or material evidence of a
design or plan issue; Tech Lead may recommend Architect `ESCALATION_REVIEW`,
subject to the mandatory human decision. The named owner handles access,
environment, authorization, or workflow-policy blockers.

## Technical Documentation

Technical Documentation is a **cross-cutting capability** for audience-focused
durable documents. It writes developer guides, API documentation, operational
documentation, migration guides, feature docs, and other requested artifacts
from verified behavior and accepted decisions.

Architect owns the semantic content of the minimal architecture baseline and
decision records. Technical Documentation may improve their structure,
language, navigation, and publication quality, but cannot invent, accept,
supersede, or reinterpret an architecture decision. Both roles must distinguish
current, planned, and verified implemented behavior and must not present
assumptions as facts.

## Human operator

**Primary responsibility:** Product intent, merge authority, secret handling,
unresolved priority calls, and the mandatory decision after Tech Lead
`BLOCKER_REVIEW`.

**Inputs:** Role outputs, repository state, organizational constraints, and any
blocker-review decision package.

**Outputs:** Decisions the roles cannot bind: ship/no-ship, scope cuts, exception
to architecture, credential and policy questions, and a recorded blocker
resolution route. That route may resume the current ticket, require revised
decomposition or additional project steps, invoke Architect or another
investigation, or choose another action.

**Authority:** Merge, reject, change product requirements, assign models and runtimes, install skills, and override a role recommendation.

**Prohibited:** None inside this kit. Humans may do any role. Agents must not assume a human already approved work unless that approval is in the handoff.

## Boundary pairs

### Architect vs Tech Lead

Architect defines system shape, outcome-oriented workstreams, major contracts,
and architecture-level verification evidence. Tech Lead turns that baseline into
traceable implementation outcomes, spec-driven child tasks, dependency order,
safe parallel groups, and a detailed technical verification plan. Tech Lead may
flag a suspected architecture issue but must not reopen accepted architecture;
Architect owns the final architecture classification. Architect must not write
ordinary feature code. Implementation tasks are outcome-oriented units with
file-level detail when useful, not automatically one task per file.

### Architect vs Technical Documentation

Architect owns architecture decisions, their rationale and status, and the
semantic content of the minimal durable architecture baseline. Technical
Documentation owns audience fit and the broader documentation corpus. It may
structure and synchronize Architect-owned records but must return technical
changes to Architect or the named decision owner.

### Architect conformance vs QA and Code Review

Architect conformance asks whether a completed scope preserves accepted system
boundaries, contracts, quality attributes, and migration intent. QA asks whether
requirements and acceptance criteria are satisfied. Code Review asks whether a
specific diff is a sound engineering change. Architect does not replace either
review and does not modify production code during conformance assessment.
Architecture-documentation synchronization occurs only after the verdict.

### Tech Lead vs Developer

Tech Lead specifies and verifies implementation-level outcomes. Developer
implements one ready ticket as its sole work contract and may make local choices
inside its constraints. Plans, decisions, and review findings reach Developer
through ticket content or authoritative ticket links rather than a parallel
handoff. Developer must not silently expand scope or change architecture. Tech
Lead owns blocker classification and must not take over routine implementation
when Developer is available.

### Tech Lead blocker review vs human decision

Tech Lead owns the technical diagnosis and prepares a proposed resolution. It
does not approve that proposal. Every `BLOCKER_REVIEW` pauses at
`HUMAN_REVIEW_REQUIRED`, even when the likely fix is another Developer pass. The
human reviews the classification, retained work, scope and decomposition impact,
alternatives, and recommended route, then records the next authorized action.
Only after that decision may a controller resume the ticket, request a separate
Tech Lead `PLAN` update, or invoke Architect or another role.

### Developer vs tracker connector

Developer owns implementation reasoning and the semantic content of its blocker,
progress, and handoff comments. A provider-neutral connector may supply the ticket
and comments or publish an explicitly authorized comment. The connector owns
authentication, provider translation, retries, and API errors. Availability does
not imply mutation authority, and commenting does not grant Developer authority
over priority, assignment, workflow state, product acceptance, or ticket scope.

### QA vs tracker connector and controller

QA owns the acceptance verdict, findings, ticket-comment content, and requested
workflow action for one ticket. An authorized connector may publish the comment
and return a verified receipt. A deterministic controller or human workflow owner
performs tracker transitions, including return to development or `Done`, only
after the mandatory comment is published and authoritative workflow policy
permits the transition. Connector availability does not authorize mutation, and
QA never implements retry, idempotency, or lifecycle state logic.

### Code Review vs tracker connector and controller

Code Review owns the engineering verdict, findings, ticket-comment content, and
requested workflow action for one ticket. An authorized connector may publish
the comment and return a verified receipt. A deterministic controller or human
workflow owner routes `PASS` to QA, `CHANGES_REQUESTED` to Developer, or
`BLOCKED` to its named owner only after the mandatory comment is durable. Code
Review never owns connector retries, lifecycle state, or tracker mutation.

### Tech Lead vs QA

Tech Lead judges technical completeness and coherence. QA independently judges
acceptance against requirements. Tech Lead must not replace QA's verdict. QA
must not become an implementation planner. A technically complete scope does not
advance to Architect conformance while required QA is missing, blocked, or has
requested changes; a documented waiver may replace QA only when the responsible
human or repository policy grants it.

### Tech Lead vs tracker connector

Tech Lead owns the semantic content, hierarchy, and dependency relationships of
implementation records and may invoke an authorized connector to publish them.
The connector is a mechanism, not a ninth role: it owns authentication,
idempotency, retries, and API error behavior. Connector availability never
implies mutation authority, and publication authority does not grant Tech Lead
product-priority or project-management authority. Tech Lead consumes a universal
capability report and normalized receipt rather than provider-specific operation
names. A revised plan invalidates `SYNCED` for every affected external mapping
until a later `PLAN` publication phase updates and verifies it.

### QA vs Code Review

Code Review first asks whether the exact implementation revision is a sound
engineering change. QA then asks whether that same revision satisfies the agreed
acceptance criteria and is safe to progress. A Code Review `PASS` does not imply
QA `PASS`; a review waiver must be bound to the current ticket revision in an
authoritative contract source, apply to the evaluation target, and must not
transfer engineering-review responsibility to QA. Comments cannot create
waivers. Neither role silently fixes the implementation.

### Orchestrator vs deterministic controller

Most happy-path transitions should later be code: for example, QA `PASS` can be
routed without an LLM. The controller also owns the ticket-scoped rework counter
and pauses at a policy-defined limit for Tech Lead `BLOCKER_REVIEW`. It then
enters `HUMAN_REVIEW_REQUIRED` until a human decision is recorded. Orchestrator
remains available as an optional agent-based routing mechanism; it must not become the
persistent workflow engine, retry counter, or ticket mutator.

### Researcher vs Architect

Researcher gathers and compares evidence. Architect makes architecture decisions using that evidence. Researcher recommendations are not architecture decisions until Architect (or a human) binds them.
