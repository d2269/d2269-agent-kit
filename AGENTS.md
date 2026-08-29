# AGENTS.md

Instructions for agents **maintaining this repository**. These are not the runtime role skills. Role procedures live in `skills/*/SKILL.md` and must stay separate from kit-maintenance rules.

## Language

All public content is English: documentation, skills, templates, script comments, examples, and commit messages intended for the public history.

## Portability

Portability beats platform-specific convenience. Canonical skills stay in `skills/`. Do not maintain edited duplicates for Cursor, Codex, Claude, or Herdr. Adapters install, copy, or link; they do not fork instructions.

Each skill must be a self-contained installable package. Keep runtime references and output assets inside that skill's directory; do not link a `SKILL.md` to repository-level docs or sibling skills.

Do not hardcode model names or “Composer vs GPT vs Claude” role assignments.

## Role boundaries

Preserve the eight-role model. Do not add overlapping skills such as `implementation-plan`, `dev`, `developer-lead`, `manager`, `epic-manager`, `linear-task`, `debugging`, `planning`, `research`, or `reviewer` unless a later redesign explicitly replaces an existing skill.

A role skill must not silently absorb another role’s primary responsibility.

## When to add a skill

Create a new skill only if the capability is:

1. **Reusable** across repositories and tasks
2. **Meaningfully distinct** from existing skills (descriptions must not be ambiguous)
3. **Procedural** — a workflow an agent should follow, not a one-line reminder
4. **Likely to be invoked independently**
5. **A poor fit for a simple project rule** (`AGENTS.md` or a repo rule)

Prefer improving an existing skill, or adding a `references/` file, over a near-duplicate skill. Do not add skills for one-off tasks.

Keep descriptions discriminative and third person. Keep `SKILL.md` reasonably small. Use progressive disclosure. References must support a skill, not copy it.

## Reasoning vs code

Procedural reasoning belongs in skills. Deterministic logic belongs in code: retries, locks, queues, polling, webhooks, status mutation, worktrees, process supervision, timeouts, persistent workflow state, scheduling, model selection, and quota.

Never encode a state machine as natural-language instructions when it can be implemented as software. Do not implement Linear integration, lifecycle automation, or agent launchers unless a human explicitly expands version 0.1 scope.

## Scripts and adapters

Scripts must be testable and must not require extra runtime dependencies without a strong reason. Validator failures must exit non-zero.

Never introduce secrets, credentials, private URLs, customer data, or machine-specific home paths in committed files.

Do not claim compatibility you did not verify. Check platform adapters against current official documentation. If verification is unavailable, add a documented TODO and refuse to guess paths.

## Validation before finishing kit changes

```bash
python3 scripts/validate_skills.py
python3 -m unittest discover -s scripts/tests -v
```

Confirm relative links, English public content, and that README, AGENTS.md, docs, and skills still agree.
