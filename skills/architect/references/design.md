# Design Mode

Use `DESIGN` before implementation when a consequential change needs a system
shape, architecture decisions, or workstream decomposition.

## Required context

- Objective, scope, non-goals, and system-level definition of done
- Constraints that can invalidate an approach
- Existing architecture, contracts, decision records, and relevant code when
  accessible
- Decision owner and the source and scope of any delegated Architect authority

If product intent is missing or contradictory, stop at explicit questions for
the human owner. Use Researcher for a bounded investigation that is too broad or
external to resolve through ordinary repository inspection.

If a consequential binding decision has no named owner and the Architect has no
explicit delegated authority, continue only far enough to produce a clearly
`PROPOSED` design. Make owner assignment and decision acceptance blocking actions;
do not present the dependent work as ready for implementation.

## Procedure

1. Establish current architecture from evidence and identify uninspected areas.
2. Define the target behavior, quality attributes, boundaries, ownership, and
   major contracts required by the objective.
3. Compare materially viable approaches against constraints, migration cost,
   operational impact, reversibility, and failure modes. Prefer the least complex
   architecture that satisfies the known requirements and quality attributes;
   justify every consequential new boundary, service, shared abstraction, or
   technology by a current material need rather than hypothetical reuse.
4. Record consequential choices as architecture decisions. Keep them
   `PROPOSED` until accepted by the decision owner or under explicit delegated
   authority.
5. Decompose the target into outcome-oriented workstreams with dependencies,
   interface owners, and verification evidence. Leave implementation-task
   specifications and their file-level detail to Tech Lead; do not imply one
   task per file.
6. Define migration, compatibility, rollback, risks, unresolved questions, and
   the evidence needed to verify implementation.
7. Create or update the actual repository architecture files under the shared
   write-authorization rule, and prepare the appropriate handoff. Without write
   authorization, return file-ready artifacts with exact intended target paths.
   If a required decision remains `PROPOSED`, hand off to its decision owner
   rather than presenting an implementation-ready Tech Lead handoff.

## Completion

`DESIGN` is complete when:

- Current and target behavior are distinguishable.
- The architecture is specific enough for Tech Lead to plan without inventing
  system boundaries or reopening accepted decisions.
- Consequential decisions have stable IDs, owners, and accurate statuses.
- The durable baseline exists in the repository, or file-ready content and exact
  target paths are provided when writes were not authorized.
- Workstreams name outcomes, dependencies, interfaces, and validation evidence.
- Migration and material risks are explicit.
- Added architectural complexity is tied to an explicit requirement, quality
  attribute, constraint, or evidenced risk.
- Blocking decisions remain visible rather than being silently assumed.
- Work that depends on a binding choice is handed to Tech Lead only after that
  choice is `ACCEPTED`.
