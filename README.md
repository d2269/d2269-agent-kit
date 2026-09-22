# D2269 Agent Kit

Portable agent skills and tooling for Codex, Cursor, Claude, Herdr, and other coding agents.

D2269 Agent Kit is a canonical toolkit of reusable **role skills**, structured handoffs, validation, and platform adapters. One developer can use it across many repositories and many agent runtimes without rewriting the same operating model each time.

> [!IMPORTANT]
> **Status: early development (v0.1).**
> The core role contracts are usable and structurally validated, but behavioral
> cross-model evaluation and controlled live lifecycle integration are still in
> progress.
> Interfaces and workflow contracts may change before the first stable release.
> External pull requests are not currently accepted; feedback is welcome through
> [LinkedIn](https://www.linkedin.com/in/stanislavd2269/).

## What it is

An **agent engineering toolkit**:

- Agent Skills in the open `SKILL.md` format
- Clear role boundaries (Architect, Tech Lead, Developer, QA, and supporting roles)
- Output contracts that a fresh agent session can consume
- Deterministic validation of skills
- Conservative installers that link or copy canonical skills into agent discovery paths

## What it is not

- Not a prompt collection
- Not a multi-agent operating system
- Not a universal Kanban framework
- Not a Herdr daemon or agent launcher
- Not a model router or quota manager
- Not an automatic ticket-discovery or merge service

The local Lifecycle Controller implements the documented delivery profiles. It
is human-started, sequential within one project, and stops at mandatory human
decisions.

## Why it exists

Coding agents are capable, but they are not interchangeable personalities by default. Without explicit roles and handoffs, the same session will design, implement, self-review, and “QA” its own work.

This kit keeps **reasoning** in skills and **deterministic control** in software.
The local controller implements that control without forking the skills.

## Supported ecosystems

Targeted conceptually:

- OpenAI Codex CLI (and the ChatGPT/Codex skills ecosystem where the same `SKILL.md` format applies)
- Cursor Agent / Cursor CLI
- Anthropic Claude Code (optional; no Claude subscription is required to use the kit)
- Herdr as a local multi-agent runtime (skills remain useful without Herdr)

Skills are **model-independent** and **agent-independent**. Do not encode rules such as “Composer is Developer” or “GPT is QA”. Model assignment lives outside the skills.

The full role chain is not mandatory for every request. Choose the least complex
[execution profile](docs/execution-profiles.md) that covers the task's risk and
required independent judgments. A bounded investigation may remain one
Researcher role across several fresh sessions; a consequential multi-ticket
scope may use the complete lifecycle. Duration and model price alone do not
determine the route.

### Execution profiles at a glance

| Profile | Use when | Route |
| --- | --- | --- |
| Focused investigation | One bounded question needs evidence, not a production change | Researcher → consumer |
| Minimal ticket delivery | One localized `READY` ticket has an authoritative Code Review waiver | Developer → QA |
| Standard ticket delivery | One ticket needs independent engineering and acceptance judgments | Developer → Code Review → QA |
| Planned scope delivery | Several related tickets need decomposition and scope-level completeness | Tech Lead `PLAN` → per-ticket delivery → Tech Lead `COMPLETENESS_REVIEW` → human close-out |
| Consequential scope delivery | Work affects architecture, system boundaries, major contracts, quality attributes, or migration | Architect `DESIGN` → Tech Lead `PLAN` → per-ticket delivery → Tech Lead `COMPLETENESS_REVIEW` → Architect `CONFORMANCE_REVIEW` → human close-out |

## Why Agent Skills

Agent Skills are a portable, version-controlled package: YAML frontmatter for discovery, Markdown for procedure, optional references and scripts. Runtimes load name and description first, then the body, then linked files. That matches progressive disclosure better than a giant always-on prompt.

Canonical skills live only in [`skills/`](skills/). Each skill bundles its runtime references and output assets so it remains self-contained after copy or symlink installation. Adapters install those packages without rewriting them. See [docs/authoring-skills.md](docs/authoring-skills.md) and [agentskills.io/specification](https://agentskills.io/specification).

## How to use the kit

1. Choose the least complex execution profile that covers the work and its risk.
2. Install the canonical skills for the target runtime.
3. Invoke the first required role with its complete input contract.
4. Preserve the role's durable output artifact and required evidence.
5. Give the next role a fresh session and the artifact named by the lifecycle
   contract; do not rely on prior chat history.
6. Let an authorized human or deterministic controller perform workflow-state
   transitions. Roles return verdicts and requested actions.

Start with these contracts:

- [Execution profiles](docs/execution-profiles.md) — select a proportional route.
- [Lifecycle role contracts](docs/lifecycle-role-contracts.md) — follow the
  stage-by-stage inputs, outputs, verdicts, and next actions.
- [Handoff contract](docs/handoff-contract.md) — make outputs usable by a fresh
  agent session.
- [Role model](docs/role-model.md) — resolve authority and boundary questions.

### Skill names and explicit invocation

Every public skill package uses the `d2269-` namespace. This prevents generic
names such as `architect` from colliding with unrelated local or project skills
and makes the selected package visible in agent skill pickers.

In Codex, select the displayed `D2269 ...` entry or mention the canonical skill
name explicitly in the prompt:

```text
$d2269-architect Use DESIGN mode for the supplied product specification.
$d2269-developer Implement ticket ABC-123 and only that ticket.
$d2269-code-review Review the exact implementation revision for ticket ABC-123.
```

The namespace identifies the installed package. Lifecycle artifacts and the
controller deliberately keep stable role IDs such as `architect`, `developer`,
and `qa`; those are protocol values, not alternative skill names.

## Role architecture

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
  └─ Tech Lead COMPLETENESS_REVIEW
       └─ consequential scope → Architect CONFORMANCE_REVIEW
                                  └─ Human review / merge
```

The branches are feedback outcomes, not parallel review stages. A valid Code
Review waiver bound to the current ticket revision in an authoritative contract
source may route the exact Developer revision directly to QA.

**Orchestrator** is an optional reasoning role for ambiguous routing. It is not a
workflow engine. Happy-path transitions (for example QA `PASS` → the
policy-defined next gate) are ordinary controller software.

The Lifecycle Controller owns those transitions and a durable rework
counter for the current ticket-contract revision. At a policy-defined limit
(three return events is a reasonable initial setting), it pauses the ticket and
requests Tech Lead `BLOCKER_REVIEW`. Every such review is then presented to a
human as `HUMAN_REVIEW_REQUIRED`; the controller cannot resume work, publish a
revised plan, invoke Architect, or make another transition until the human
records the next action. That decision may require revised decomposition,
additional project steps, or another role rather than another implementation
pass.

Herdr and Conductor may later serve as interchangeable role-session runners.
They are execution mechanisms, not owners of lifecycle policy or technical
decisions.

During implementation, evidence of a design-level blocker goes to Tech Lead
`BLOCKER_REVIEW`. Tech Lead may recommend Architect `ESCALATION_REVIEW`, but the
mandatory human decision determines whether to invoke it; routine ticket problems
remain with Tech Lead, Developer, Code Review, or QA.

Developer executes one ticket assigned to it whose implementation readiness is
`READY`; this semantic field is separate from tracker workflow status. The ticket
is the sole work contract. Developer may use ticket-linked sources and comments
for context and produces a mandatory history comment for every final result, but
does not change workflow state. The controller or a human workflow owner
publishes ready-to-post comments before routing completed work to Code Review.

Code Review independently evaluates the exact implementation revision for that
ticket in a context that did not implement it. Every verdict produces a mandatory
ticket-history comment. `PASS` admits the same revision to QA; an explicit,
ticket-revision-bound workflow-policy waiver from an authoritative contract
source may replace review. Code Review neither fixes code nor changes tracker
state.

QA evaluates that same one ticket after a matching Code Review `PASS` or
authorized waiver. Every verdict produces a mandatory ticket-history comment
that distinguishes passed, failed, and unverified checks. QA does not change
implementation files or tracker state; ready-to-post comments are published
before routing. `PASS` reaches `Done` only when QA is the final required gate.

Each Architect stage is a separate invocation. Post-scope conformance establishes
its evidence-backed verdict before applying or proposing durable architecture
documentation updates.

Full boundaries: [docs/role-model.md](docs/role-model.md). Stage-by-stage
contracts: [docs/lifecycle-role-contracts.md](docs/lifecycle-role-contracts.md).
Fresh-session handoffs: [docs/handoff-contract.md](docs/handoff-contract.md).
Proportional routes: [docs/execution-profiles.md](docs/execution-profiles.md).
Layout and non-goals: [docs/architecture.md](docs/architecture.md).

### Role responsibilities

| Role | Skill invocation | Owns |
| --- | --- | --- |
| Architect | `$d2269-architect` | Architecture baseline and decisions, technical workstreams, design escalations, architecture conformance |
| Tech Lead | `$d2269-tech-lead` | Spec-driven implementation plan and child tasks, optional authorized tracker publication, blocker triage, technical completeness |
| Developer | `$d2269-developer` | One `READY` ticket: in-scope code, tests, affected docs, and ticket-linked evidence |
| QA | `$d2269-qa` | One eligible ticket with a `COMPLETE` Developer result and Code Review `PASS` or authorized waiver: independent acceptance verdict and requested next action |
| Orchestrator | `$d2269-orchestrator` | Next-role recommendation when routing is ambiguous |
| Researcher | `$d2269-researcher` | Evidence-driven investigation; not implementation |
| Code Review | `$d2269-code-review` | One ticket's exact implementation revision: independent engineering verdict, ticket feedback, and requested next action |
| Technical Documentation | `$d2269-technical-documentation` | Audience-focused durable docs from verified behavior and accepted architecture decisions |

### Skill boundaries

A role must not silently take over another role's primary job. Architect owns the
semantic architecture baseline but not ordinary feature implementation or
file-level planning. Technical Documentation may publish architecture records
but does not choose or reinterpret architecture. Developer does not redefine
architecture. QA does not silently patch the code it evaluates. Researcher does
not ship production changes; explicit implementation requests hand off to
Developer. Orchestrator does not become a universal agent. Tech Lead does not
replace QA. Code Review does not auto-apply fixes.

## Repository layout

```text
skills/          Canonical, self-contained Agent Skills and bundled output assets
controller/      Shared lifecycle engine, SQLite state, Git, Herdr, and Linear adapters
docs/            Architecture, installation, authoring, role model, handoff contract
scripts/         Validator, installer, and controller demonstrations
adapters/        Platform notes and installer entry points
```

## Installation

Global (`user`) installation puts skills in an agent's home discovery path so
they are available across projects on that machine. Project installation puts
them in one target repository so teammates and remote agents can load them.

### Install for all projects

Validate the kit, preview the destination, and install all eight role skills for
Codex:

```bash
python3 scripts/validate_skills.py
python3 scripts/install_skills.py --platform codex --scope user --dry-run
python3 scripts/install_skills.py --platform codex --scope user
```

Omitting `--skill` installs every role. The default `symlink` mode tracks changes
in this repository and requires the clone to remain at the same path. To install
an independent snapshot instead:

```bash
python3 scripts/install_skills.py --platform codex --scope user --mode copy
```

Install one role by its full canonical name:

```bash
python3 scripts/install_skills.py --platform codex --scope user --skill d2269-architect
```

For Codex user scope, the resulting package is
`$HOME/.agents/skills/d2269-architect`. Restart Codex or open a fresh task after
installation so discovery is refreshed.

Copied installations do not update automatically. After reviewing a later kit
revision with `--dry-run`, repeat the copy command with `--force` to replace an
older divergent snapshot.

Versions installed before the `d2269-` namespace may still have unprefixed
folders such as `architect` or `developer`. Because an unprefixed folder may
also belong to another project, the installer reports it as potentially legacy
or unrelated and never deletes it. Verify the new `D2269 ...` entry, then remove
or disable the unprefixed copy only after confirming it is an earlier D2269
installation.
See [the migration instructions](docs/installation.md#migration-from-unprefixed-skill-names).

Use `--platform cursor` or `--platform claude` for those agents. For a
project-local installation, add `--scope project --project-root /path/to/repo`.

For Herdr, install these roles for the coding agent that runs inside Herdr
(Codex, Cursor, or Claude). Herdr does not currently document a separate
third-party role-skill destination, so `--platform herdr` intentionally exits
with an explanatory error. Install Herdr's own control skill independently as
described in the [installation guide](docs/installation.md#herdr).

Full commands and verified discovery paths:
[docs/installation.md](docs/installation.md).

## Lifecycle Controller

The stdlib-only Python controller provides one shared engine for `minimal`,
`standard`, `planned`, and `consequential` delivery. It uses Herdr for fresh
role sessions, Git worktrees for exact-revision isolation, SQLite for durable
project-scoped state, and a production Linear GraphQL adapter for authorized
comments, child-ticket synchronization, and status transitions.

See [Lifecycle Controller](docs/controller.md) for installation, configuration,
CLI usage, security, recovery, troubleshooting, tests, and current limitations.

## Current maturity

**Version 0.1.** Role skills, handoff templates, validator, installer, and the
controller are implemented. Deterministic fake-boundary tests and credential-free
state/receipt demonstrations pass. Herdr 0.9.0 syntax and current official Linear
GraphQL behavior were verified, but a controlled live end-to-end pilot is still
required before production adoption. Automatic model routing remains deferred by
design.

Structural validation checks package shape, metadata, links, and deterministic
repository rules. Behavioral eval cases define repeatable expectations but do
not, by themselves, prove that a particular model or runtime has passed them.

## Security

Skills change agent behavior. Installer scripts write into home and project directories. Treat third-party skills and scripts like executable automation: read them before install. Never put secrets in `SKILL.md`. See [SECURITY.md](SECURITY.md).

## Contributing

Public content is English. Improve existing skills before adding near-duplicates. Deterministic logic belongs in code. See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).

## Contact

For professional inquiries, feedback, or collaboration, connect with the
maintainer on [LinkedIn](https://www.linkedin.com/in/stanislavd2269/).

## License

[MIT](LICENSE)
