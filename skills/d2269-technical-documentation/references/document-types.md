# Document types

Choose the smallest document that matches the request. Do not mix types without
labeling sections.

| Type | Reader | Contains | Avoid |
| --- | --- | --- | --- |
| Architecture overview | Future Architect / Tech Lead | Architect-owned baseline: boundaries, components, data flow, decision links | Changing system shape or presenting target behavior as current |
| ADR / architecture decision | Implementers and reviewers | Architect-owned context, decision, consequences, owner, and status | Inventing, accepting, or reinterpreting the decision |
| Developer guide | Contributors | How to build, test, and change the system | Product marketing |
| API documentation | API consumers | Contracts, errors, compatibility | Internal refactor notes |
| Operational documentation | Operators | Run, observe, recover | Design history |
| Feature documentation | Implementers and QA | Intended behavior, edge cases | Unverified roadmap |
| Implementation notes | The next Developer | What changed and why, locally | Restating the whole architecture |
| Migration documentation | Operators / Tech Lead | Steps, compatibility, rollback | Open-ended redesign |

Mark each statement as **current behavior**, **planned behavior**, or **verified
implemented behavior**. Planned behavior must not read as if the system already
works that way.

For architecture documents, preserve stable decision IDs and the Architect's
semantic content. Technical Documentation may improve audience fit, wording,
structure, cross-links, and publication quality, but architecture changes return
to Architect.
