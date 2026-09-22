# Architecture Documentation Contract

Architect owns architecture decisions and the semantic content of the minimal
durable architecture baseline. Technical Documentation may improve structure,
language, navigation, and synchronization without inventing or changing those
decisions.

## Discover before creating

Use the repository's existing architecture and decision-record conventions. If
none exist, a reasonable default is:

```text
docs/
`-- architecture/
    |-- overview.md
    `-- decisions/
        `-- AD-NNN-short-title.md
```

Update an existing authoritative overview instead of creating a similar file
for each scope.

## Minimal durable baseline

Include only information needed by future Architects, Tech Leads, implementers,
and maintainers:

- Purpose, scope, and non-goals
- Current and target architecture
- Components, responsibilities, boundaries, and ownership
- Data and control flow
- Public and cross-component contracts
- Applicable quality attributes and trust boundaries
- External dependencies
- Migration, intermediate states, and rollback
- Risks, unresolved questions, and architecture debt
- Links to decision records and authoritative code, schemas, or API definitions

Do not turn the architecture overview into a file-level implementation plan.
Use a diagram only when it materially clarifies a relationship or sequence, and
keep its editable source with the document.

## Decision records

Preserve the repository's existing ID scheme. Before allocating an ID, inspect
the authoritative decision directory and select the next unused ID under that
scheme. If no scheme exists, use `AD-NNN-short-title.md`, choose one greater than
the highest existing numeric ID, preserve zero padding, and recheck availability
before writing. Never reuse or renumber an existing ID; surface a possible
concurrent allocation instead of silently overwriting it.

Use one of these decision statuses:

- `PROPOSED`: recommended but not approved
- `ACCEPTED`: approved by the named decision owner or bound under explicit
  delegated authority
- `IMPLEMENTED`: conformance evidence verifies the accepted decision in the
  system
- `SUPERSEDED`: replaced by a newer `ACCEPTED` decision record; a proposed
  replacement does not supersede the active decision
- `REJECTED`: explicitly declined by the named decision owner; Architect may
  record but not infer the rejection

Do not rewrite accepted history when a decision changes. Link the old and new
records, and keep the old accepted decision active until its replacement is
accepted. A record should contain context, the decision, material alternatives,
consequences, validation evidence, owner, authority or status evidence, status,
and related sources.

Architecture-overview status and decision-record status are distinct. Overview
labels (`TARGET`, `CURRENT`, `PARTIALLY_IMPLEMENTED`) summarize the relationship
between the accepted target and verified implementation. Decision statuses
describe approval and lifecycle state; there is no one-to-one mapping between
the two vocabularies.

## Truth and lifecycle

- Before implementation, label target behavior as planned.
- During an architecture escalation, update documents only when the architecture
  changes.
- A `PROPOSED` replacement must not replace the accepted target architecture. It
  may appear only as a clearly labeled non-authoritative proposed delta linked to
  its decision record. Update the accepted target and mark the old decision
  `SUPERSEDED` only after the replacement is `ACCEPTED`.
- After conformance review, move planned descriptions to current only when
  implementation evidence supports the change.
- Close every conformance review with durable repository updates when writes are
  authorized, or file-ready changes with exact target paths when they are not.
- Mark partial implementation and stale areas explicitly.
- Treat code, executable tests, schemas, and API definitions as authoritative
  for implemented behavior; architecture documents are authoritative for
  accepted intent and rationale.
