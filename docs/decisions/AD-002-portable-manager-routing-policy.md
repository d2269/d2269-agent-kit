# AD-002: Optional Portable Manager-Routing Policy

- Status: `ACCEPTED`
- Decision owner: Repository owner
- Authority / status evidence: Explicit confirmation of the portable optional
  policy direction and implementation request on 2026-09-29
- Date: 2026-09-29
- Supersedes: The manager-integration scope of the 2026-09-28 AD-002 draft
- Superseded by: N/A

## Context

The earlier AD-002 draft proposed project-scoped Lifecycle Controller worker
profiles and persisted Developer worker identity as the general
manager-integration layer. That scope is too narrow for an open-source kit used
by different projects and runtimes: Controller configuration is available only
to Controller-managed workflows, while a project may want a human-directed
manager that delegates through native subagents without installing the
Controller or Herdr.

The kit's durable reusable contract is the eight canonical D2269 role skills.
Any manager-routing support should be an additional opt-in layer for consuming
projects, with only the executor choices that cannot be inferred from those
role contracts.

## Decision

Add an optional, project-local manager-routing policy template and an
initializer that a consumer project can choose to use. The policy maps each
canonical D2269 skill to a project-selected primary executor and a bounded,
explicit allowlist of alternatives. Supported executor styles are the chosen
manager runtime's native subagents and Herdr workers; a project may use either
or mix them. Every configured executor names an opaque, project-selected model
identifier; a Herdr executor also names its upstream agent kind and optional
native arguments.

The template contains no concrete provider or model defaults, no credentials,
and no required dependency on Herdr or the Lifecycle Controller. When a primary
is missing or unavailable, the manager asks the human. It uses an alternative
only when that executor is listed for the skill and the human explicitly
chooses it; it never silently switches or selects an unlisted worker.

The policy selects executors; it does not define role behavior. Lifecycle
semantics, authority, inputs, outputs, exact-revision requirements, and verdicts
remain in the eight canonical role skills and their accepted contracts. The
optional manager guidance requires bounded handoffs containing the task
contract, exact revision, relevant evidence, acceptance criteria, and expected
role output rather than the manager's full conversation.

Session continuity, context independence, exact-revision binding, and rework
routing remain governed by the canonical lifecycle role and handoff contracts.
A manager surfaces blocked workers, approval prompts, uncertain prompt
delivery, and unavailable executors to a human; it does not answer approval
prompts, blindly retry uncertain prompts, or silently replace a worker.

Herdr and the Lifecycle Controller remain independent optional layers. Herdr
provides a worker runtime when selected. The Lifecycle Controller retains its
existing project-local runner configuration, SQLite state, worktrees, and
lifecycle routing for controller-managed runs. It does not consume or
substitute for the portable manager-routing policy.

## Consequences

- Benefits: projects may reuse D2269 roles with their chosen manager runtime
  without adopting a specific provider, Herdr, or controller; role boundaries
  remain canonical and portable.
- Costs and limitations: a static policy cannot prove a runtime supports model
  selection or session continuity; managers must follow the handoff and human
  stop rules; each consumer project must supply its own executor choices.
- Implementation status: the template, JSON schema, validator, and
  non-destructive opt-in initializer are present. They validate and install
  policy files but do not launch or supervise managers or enforce runtime
  behavior.
- Compatibility: the Controller's existing runner configuration and behavior
  remain unchanged. Existing manual role-skill use remains supported.

## Alternatives considered

| Alternative | Disposition |
| --- | --- |
| Extend the Controller with worker profiles as the general manager policy | Rejected: only Controller runs could consume them, and its SQLite state is an implementation detail of that optional layer. |
| Require Herdr for every manager | Rejected: native manager subagents are a valid executor and Herdr is optional. |
| Add a ninth manager role skill or general agent launcher | Rejected: executor choice is project configuration; launching, polling, retries, and persistent orchestration require software beyond this policy layer. |
| Put provider/model defaults in the kit | Rejected: choices depend on each consumer's runtime, access, and budget and would reduce portability. |

## Validation and follow-up

This decision is accepted and the static policy artifacts are implemented.
Validate the template and examples, exercise initializer preservation and
conflict behavior, and confirm the public docs distinguish the policy from
Controller configuration. Runtime compatibility, session continuity, live
native-subagent behavior, and manager-directed Herdr execution are not verified
by the presence of these files and are not claimed by this ADR.

## References

- [Manager routing guide](../herdr-manager.md)
- [Lifecycle Controller](../controller.md)
- [Architecture](../architecture.md)
- [Lifecycle role contracts](../lifecycle-role-contracts.md)
- [Handoff contract](../handoff-contract.md)
- [AD-001: Deterministic Lifecycle Controller Runtime](AD-001-lifecycle-controller-runtime.md)
