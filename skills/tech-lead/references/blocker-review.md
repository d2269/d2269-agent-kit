# Blocker Review Mode

Use `BLOCKER_REVIEW` when evidence from active implementation indicates that the
task, plan, requirements, or accepted architecture may be insufficient.

## Required context

- Active plan ID and revision plus task specification
- Expected outcome and observed behavior
- Reproduction evidence, failed attempts, tests, logs, and affected components
- Supplied ticket comments, review history, and workflow trigger when available
- Relevant accepted architecture decisions and implementation constraints
- Work already completed and supported intermediate state

Do not classify from difficulty, elapsed time, or retry count alone.

## Procedure

1. Reproduce or inspect the failure where access exists. Separate observations
   from hypotheses and record uninspected areas.
2. Identify the owning layer, violated expectation, and smallest evidence-backed
   cause.
3. Assign exactly one primary classification:
   - `IMPLEMENTATION_DEFECT`: the plan and architecture remain valid; Developer
     must correct the implementation.
   - `PLAN_GAP`: implementation-level sequencing, scope, dependency, interface,
     or verification guidance is missing or incorrect.
   - `SUSPECTED_ARCHITECTURE_ISSUE`: evidence may invalidate an accepted
     architecture assumption, boundary, contract, quality attribute, or
     migration decision. Architect makes the final architecture classification.
   - `REQUIREMENTS_GAP`: product intent or acceptance criteria are missing or
     contradictory.
   - `INSUFFICIENT_EVIDENCE`: a bounded investigation is required before another
     classification is defensible.
4. Prepare the smallest safe proposed resolution and explain its effect on
   completed and pending work. For `PLAN_GAP`, prepare non-published revised plan
   or task specifications without changing product intent or accepted
   architecture. Use a candidate new plan revision and re-run every planning
   validation check against the complete affected plan and task set, not only the
   edited records. If the proposal changes any externally mapped record,
   relation, readiness state, or verification field, mark publication
   `OUT_OF_SYNC` and identify the affected mappings.
5. Set the outcome to `HUMAN_REVIEW_REQUIRED`. Give the human decision owner:
   - the classification, evidence, and preserved completed work;
   - the proposed resolution and material alternatives;
   - any scope, decomposition, architecture, or external-mapping impact;
   - a recommended next role and bounded action; and
   - one exact decision to record.
6. Do not resume Developer, publish a proposed plan, invoke Architect or another
   investigator, or request a tracker transition before the human decision is
   recorded. The human may approve the recommendation or require revised
   decomposition, additional project work, Architect review, investigation, or
   another route. An approved plan change is finalized and published through a
   separate `PLAN` invocation before implementation resumes.

## Completion

Complete when the classification is evidence-backed, completed work that remains
valid is identified, proposed revisions pass the complete planning validation,
external sync impact is explicit, and the human decision package is usable
without prior conversation. Repeated failure may trigger review or strengthen
evidence but never substitutes for identifying the violated layer or expectation.
