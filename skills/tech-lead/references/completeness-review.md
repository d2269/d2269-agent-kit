# Completeness Review Mode

Use `COMPLETENESS_REVIEW` after implementation of a defined plan or task set. It
judges implementation-level technical completeness, not product acceptance,
diff quality, architecture conformance, or merge readiness.

## Required context

- Approved implementation plan and task specifications
- System-level definition of done and Architect-required verification evidence
  when the scope has an accepted architecture baseline
- Current implementation and Developer evidence
- Tests, schemas, contracts, migrations, documentation, and operational evidence
- Declared deviations and their approval source
- QA and Code Review outputs or their authorized waivers, treated as independent
  verdicts and bound to each task's current exact implementation revision

Return `NOT_VERIFIABLE` when evidence is insufficient for a defensible judgment.

## Procedure

1. Map every required plan item and task completion criterion to inspected
   implementation evidence.
2. Verify dependency completion, supported intermediate states, interfaces,
   schemas, migrations, compatibility, tests, documentation impact, and material
   operational requirements.
3. Classify deviations as approved implementation-level variation, plan gap,
   incomplete implementation, suspected architecture issue, or undocumented
   scope change.
4. Set exactly one technical verdict:
   - `TECHNICALLY_COMPLETE`: required technical work and evidence are complete.
   - `CHANGES_REQUIRED`: named implementation or plan work remains.
   - `NOT_VERIFIABLE`: evidence or access is insufficient.
5. Record QA and Code Review verdicts with the exact implementation revision each
   covers, without replacing or overruling them. A later implementation change
   invalidates earlier passes for the changed task. A technical verdict does not
   grant product acceptance, architecture conformance, or merge authority.
6. Choose exactly one next action in this order; stop at the first applicable
   condition:
   - `NOT_VERIFIABLE` -> the owner of the missing bounded evidence;
   - suspected architecture issue -> Architect `ESCALATION_REVIEW`;
   - missing or contradictory product decision -> human owner;
   - `CHANGES_REQUIRED` -> Developer with named remaining work;
   - Code Review `CHANGES_REQUESTED` for the current implementation revision ->
     Developer;
   - Code Review `BLOCKED` for the current implementation revision -> the owner
     of its blocking prerequisite;
   - required Code Review has no `PASS` or authorized waiver applicable to the
     current implementation revision -> Code Review;
   - QA `CHANGES_REQUESTED` for the current implementation revision -> Developer
     or the owner named by QA;
   - QA `BLOCKED` for the current implementation revision -> the owner of QA's
     blocking prerequisite;
   - product acceptance required but no QA `PASS` or authorized waiver applicable
     to the current implementation revision -> QA;
   - unresolved diff-local defect -> Developer, followed by Code Review of the
     resulting exact revision;
   - `TECHNICALLY_COMPLETE` consequential scope -> Architect
     `CONFORMANCE_REVIEW`;
   - otherwise -> the human merge or release authority.
7. For `CONFORMANCE_REVIEW`, package decision IDs, implemented task IDs, affected
   boundaries and contracts, code and schema paths, migrations, tests, metrics,
   deviations, and unverified areas. Before handoff, verify every evidence-pack
   field is populated or explicitly marked not applicable with a reason.

A scope is consequential for conformance when its plan implements an accepted
architecture decision or workstream, or when implementation affects a named
system boundary, cross-component or public contract, quality attribute, or
migration decision. Otherwise Architect conformance is optional unless the
repository or human owner requires it.

## Completion

Complete when every required task is accounted for, the verdict is traceable to
named evidence, deviations and gaps are classified, external verdicts retain
their owners, and the next role receives a fresh-session handoff.
