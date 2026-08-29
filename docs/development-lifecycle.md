# Development Lifecycle — Split Cycles

Review status: PROPOSED

This document deliberately separates ticket preparation from delivery of one
ticket. Each cycle has its own start condition, explicit role outputs, actions,
decisions, and terminal states.

These diagrams describe the standard and consequential delivery paths. They are
not mandatory for bounded research or every low-risk ticket. Select the
proportional route first in [Execution Profiles](execution-profiles.md); then use
the applicable cycle below without weakening its role gates.

Semantic states such as READY, COMPLETE, and PASS are not tracker workflow
columns. Roles produce verdicts, reports, comments, and requested actions. A
future deterministic Lifecycle Controller or a human workflow owner performs
authorized tracker transitions.

## Cycle 1 — Prepare and publish implementation tickets

Purpose: convert a human task definition into accepted architecture, a validated
Implementation Plan, independently usable child-ticket specifications, and—when
requested and authorized—verified records in the task-management system.

```mermaid
flowchart TD
    START([START — TICKET PREPARATION])
    HUMAN_INPUT[/Human provides the task,<br/>expected result, acceptance criteria,<br/>constraints, and decision authority/]
    ARCHITECT[Architect designs the solution<br/>and produces the Architecture Baseline]
    ARCH_RESULT{Architecture result}
    DECISION_OWNER[/Named decision owner/]
    TECH_LEAD[Tech Lead produces the Implementation Plan<br/>and one specification per child ticket]
    PLAN_STATUS{Plan status}
    PUBLISH_Q{Publish tickets<br/>to task management?}
    END_PLAN([END — Plan DRAFT or BLOCKED;<br/>owner and next action recorded])
    END_LOCAL([END — READY plan and tickets;<br/>publication NOT_REQUESTED])
    PUB_READY{Publication gate passes?}
    PUBLISH[Tech Lead publishes the plan<br/>and tickets through the connector]
    PUB_STATUS{Publication status}
    END_SYNCED([END — SYNCED;<br/>verified IDs, links, mappings, and receipt])
    END_NOT_SYNCED([END — PARTIAL or OUT_OF_SYNC;<br/>failures and next action recorded])
    END_PUB_BLOCKED([END — Publication BLOCKED;<br/>tracker-ready artifacts and missing prerequisite])
    END_REJECTED([END — Architecture decision REJECTED])

    START --> HUMAN_INPUT
    HUMAN_INPUT --> ARCHITECT
    ARCHITECT --> ARCH_RESULT
    ARCH_RESULT -->|Missing or contradictory product input| HUMAN_INPUT
    ARCH_RESULT -->|Required decision PROPOSED| DECISION_OWNER
    ARCH_RESULT -->|Required decisions ACCEPTED| TECH_LEAD
    DECISION_OWNER -->|Accept and record| TECH_LEAD
    DECISION_OWNER -->|Revise| ARCHITECT
    DECISION_OWNER -->|Reject| END_REJECTED
    TECH_LEAD --> PLAN_STATUS
    PLAN_STATUS -->|DRAFT or BLOCKED| END_PLAN
    PLAN_STATUS -->|READY_FOR_IMPLEMENTATION| PUBLISH_Q
    PUBLISH_Q -->|No| END_LOCAL
    PUBLISH_Q -->|Yes| PUB_READY
    PUB_READY -->|No| END_PUB_BLOCKED
    PUB_READY -->|Yes| PUBLISH
    PUBLISH --> PUB_STATUS
    PUB_STATUS -->|SYNCED| END_SYNCED
    PUB_STATUS -->|PARTIAL or OUT_OF_SYNC| END_NOT_SYNCED

    classDef human fill:#fff2cc,stroke:#b58b00,stroke-width:2px;
    classDef architect fill:#d9eaf7,stroke:#2878a5,stroke-width:2px;
    classDef techlead fill:#e2f0d9,stroke:#548235,stroke-width:2px;
    classDef success fill:#d1e7dd,stroke:#146c43,stroke-width:2px;
    classDef blocked fill:#f8d7da,stroke:#b02a37,stroke-width:2px;

    class HUMAN_INPUT,DECISION_OWNER human;
    class ARCHITECT architect;
    class TECH_LEAD,PUBLISH techlead;
    class END_LOCAL,END_SYNCED success;
    class END_PLAN,END_NOT_SYNCED,END_PUB_BLOCKED,END_REJECTED blocked;
```

### Cycle 1 outputs

| Producer | Explicit output | Consumer or action |
| --- | --- | --- |
| Human | Task description, expected result, acceptance criteria, constraints, authority | Architect DESIGN |
| Architect | Architecture baseline, ADRs, workstreams, risks, migration, verification evidence, exact next action | Human decision owner or Tech Lead PLAN |
| Tech Lead | Implementation Plan and one independently usable Implementation Task per child ticket | Connector, Lifecycle Controller, or Developer session |
| Tracker connector | Verified external IDs, links, hierarchy, dependencies, mappings, and publication receipt | Lifecycle Controller |
| Cycle terminal | Plan DRAFT/BLOCKED, architecture decision REJECTED, READY tickets with NOT_REQUESTED or SYNCED publication, or publication PARTIAL/OUT_OF_SYNC/BLOCKED | Cycle 2, decision owner, or named recovery owner |

## Cycle 2 — Deliver one ticket

Purpose: move exactly one current READY ticket through Developer, Code Review,
and QA. The normal successful terminal state is Done. Replanning and architecture
work leave this cycle and return to Cycle 1 instead of being mixed into it.

The diagram shows the default path. A Code Review waiver may skip Code Review
only when it is explicitly authorized and bound to the current ticket revision
as required by the Developer and QA contracts.

```mermaid
flowchart TD
    START([START — ONE TICKET])
    SELECT[/Controller or human selects exactly one<br/>current READY Developer ticket/]
    DEVELOPER[Developer implements and verifies<br/>the ticket outcome]
    DEV_RESULT{Developer result}
    CODE_REVIEW[Code Review evaluates<br/>the exact implementation revision]
    CR_VERDICT{Code Review verdict}
    QA[QA evaluates acceptance criteria<br/>for the same ticket and revision]
    QA_VERDICT{QA verdict}
    LIMIT{Configured rework<br/>limit reached?}
    NEXT_OWNER{Role output requests<br/>Tech Lead BLOCKER_REVIEW?}
    TL_REVIEW[Tech Lead performs BLOCKER_REVIEW]
    HUMAN_REQUIRED[HUMAN_REVIEW_REQUIRED]
    HUMAN{Human records the next action}
    DONE_ACTION[Controller moves the ticket to Done<br/>when QA is the terminal policy gate]
    END_DONE([END — TICKET DONE])
    END_INCOMPLETE([END — PARTIAL or BLOCKED;<br/>named owner and exact next action])
    RETURN_PREP([END — RETURN TO CYCLE 1<br/>FOR REPLAN OR DECOMPOSITION])
    ARCH_EXIT([END — ARCHITECT ESCALATION_REVIEW REQUESTED])
    STOP([END — TICKET STOPPED OR DEFERRED])

    START --> SELECT
    SELECT --> DEVELOPER
    DEVELOPER --> DEV_RESULT
    DEV_RESULT -->|COMPLETE| CODE_REVIEW
    DEV_RESULT -->|PARTIAL or BLOCKED| NEXT_OWNER
    CODE_REVIEW --> CR_VERDICT
    CR_VERDICT -->|PASS| QA
    CR_VERDICT -->|CHANGES_REQUESTED| LIMIT
    CR_VERDICT -->|BLOCKED| NEXT_OWNER
    QA --> QA_VERDICT
    QA_VERDICT -->|PASS| DONE_ACTION
    QA_VERDICT -->|CHANGES_REQUESTED| LIMIT
    QA_VERDICT -->|BLOCKED| NEXT_OWNER
    LIMIT -->|No| DEVELOPER
    LIMIT -->|Yes| TL_REVIEW
    NEXT_OWNER -->|No| END_INCOMPLETE
    NEXT_OWNER -->|Yes| TL_REVIEW
    TL_REVIEW --> HUMAN_REQUIRED
    HUMAN_REQUIRED --> HUMAN
    HUMAN -->|Resume current ticket| DEVELOPER
    HUMAN -->|Replan or decompose| RETURN_PREP
    HUMAN -->|Request Architect review| ARCH_EXIT
    HUMAN -->|Stop or defer| STOP
    DONE_ACTION --> END_DONE

    classDef human fill:#fff2cc,stroke:#b58b00,stroke-width:2px;
    classDef techlead fill:#e2f0d9,stroke:#548235,stroke-width:2px;
    classDef developer fill:#fce4d6,stroke:#c55a11,stroke-width:2px;
    classDef review fill:#e4dfec,stroke:#7030a0,stroke-width:2px;
    classDef qa fill:#d9e1f2,stroke:#2f5597,stroke-width:2px;
    classDef controller fill:#eeeeee,stroke:#555555,stroke-width:2px;
    classDef success fill:#d1e7dd,stroke:#146c43,stroke-width:2px;
    classDef blocked fill:#f8d7da,stroke:#b02a37,stroke-width:2px;

    class HUMAN,HUMAN_REQUIRED human;
    class TL_REVIEW techlead;
    class DEVELOPER developer;
    class CODE_REVIEW review;
    class QA qa;
    class SELECT,DONE_ACTION controller;
    class END_DONE success;
    class END_INCOMPLETE,RETURN_PREP,ARCH_EXIT,STOP blocked;
```

### Cycle 2 outputs

| Producer | Explicit output | Controller or human action |
| --- | --- | --- |
| Developer | Code, tests, affected docs, exact revision, implementation report, mandatory ticket comment, COMPLETE/PARTIAL/BLOCKED | Route COMPLETE to Code Review; for PARTIAL/BLOCKED follow the recorded next owner and action |
| Code Review | Findings, verification, exact target, mandatory ticket comment, PASS/CHANGES_REQUESTED/BLOCKED | PASS → QA; CHANGES_REQUESTED → rework counter and Developer; BLOCKED → named owner or Tech Lead |
| QA | Acceptance matrix, evidence, mandatory ticket comment, PASS/CHANGES_REQUESTED/BLOCKED | PASS → Done when policy permits; CHANGES_REQUESTED → rework counter and Developer; BLOCKED → named owner or Tech Lead |
| Tech Lead BLOCKER_REVIEW | Classification, evidence, retained work, proposal, alternatives, scope impact, recommended role, HUMAN_REVIEW_REQUIRED | Always present the package to a human; do not execute the recommendation |
| Human | Recorded decision to resume, replan or decompose, request Architect review, or stop or defer | Controller performs only the authorized next transition |
| Cycle terminal | Ticket Done, PARTIAL/BLOCKED with a named next owner, return to Cycle 1, Architect escalation request, or stopped/deferred ticket | Start the indicated separate cycle or end processing |

## Shared invariants

1. Human input is the first operation after the preparation START.
2. Cycle 1 ends before Cycle 2 starts. Cycle 2 receives exactly one current READY
   ticket; it does not reconstruct a plan or architecture scope.
3. Developer, Code Review, and QA each operate on exactly one ticket per
   invocation. Code Review and QA evaluate one exact implementation revision;
   Developer records the exact revision it produced.
4. The successful sequence is Developer COMPLETE → Code Review PASS → QA PASS.
5. The only permitted shortcut is an authorized Code Review waiver bound to the
   current ticket revision.
6. Every final Developer result and every Code Review or QA verdict requires a
   durable ticket-history comment before routing.
7. Developer, Code Review, and QA do not mutate tracker workflow state.
8. PARTIAL or BLOCKED work never enters a later gate as ready.
9. A rework count can trigger BLOCKER_REVIEW but cannot establish the cause.
10. Every BLOCKER_REVIEW ends in HUMAN_REVIEW_REQUIRED. The ticket remains paused
    until the human decision is recorded.

## Deliberately separate future cycle

Scope-level Tech Lead COMPLETENESS_REVIEW and Architect CONFORMANCE_REVIEW are not
embedded in either diagram. They should be documented as a third, independent
scope-completion cycle after the preparation and single-ticket cycles are
approved.
