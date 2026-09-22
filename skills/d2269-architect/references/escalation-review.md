# Escalation Review Mode

Use `ESCALATION_REVIEW` only when evidence from an active scope may invalidate an
architecture assumption, boundary, contract, quality attribute, migration path,
or consequential decision.

## Required context

- Blocked outcome and expected behavior
- Reproduction evidence, failed attempts, test or QA findings, and affected
  components
- Accepted architecture baseline and relevant decision IDs
- Current implementation state and scope already completed

Do not infer a design problem merely because a ticket is difficult or has failed
once.

## Classify before redesigning

Assign exactly one primary classification:

- `DESIGN_ISSUE`: the accepted system shape or decision is insufficient or
  incorrect.
- `IMPLEMENTATION_ISSUE`: the architecture remains valid; Tech Lead or Developer
  should resolve the execution problem.
- `REQUIREMENTS_GAP`: product intent or acceptance expectations are missing or
  contradictory; route to the human owner.
- `INSUFFICIENT_EVIDENCE`: obtain a bounded investigation or additional
  reproduction evidence before deciding.

Only `DESIGN_ISSUE` authorizes an architecture revision.

## Design-issue procedure

1. State the verified failure and the architecture assumption or decision it
   contradicts.
2. Identify the affected contracts, completed work, pending work, migration
   path, and compatibility guarantees.
3. Compare materially viable resolutions and recommend or bind one within the
   available authority.
4. Preserve decision history: create the replacement record as `PROPOSED`. Keep
   the old accepted decision active until the replacement is `ACCEPTED`; only
   then mark the old decision `SUPERSEDED`. Never rewrite its original rationale.
5. While the replacement is `PROPOSED`, keep the accepted target architecture
   active. A proposed target delta may be documented only when it is clearly
   labeled non-authoritative and linked to the proposed record. After the
   replacement becomes `ACCEPTED`, update the authoritative target architecture,
   mark the old decision `SUPERSEDED`, and name the workstreams that must change.
6. Return one exact action to Tech Lead or the decision owner. Do not route
   dependent implementation to Tech Lead while its replacement decision remains
   `PROPOSED`.

## Completion

Complete when the classification is evidence-backed, the responsible role is
clear, architecture history remains traceable, and the effect on completed and
pending work is explicit. Any proposed target is distinguishable from the active
accepted target.
