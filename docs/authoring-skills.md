# Authoring Skills

Follow the open Agent Skills format: a directory containing `SKILL.md` with YAML frontmatter plus Markdown instructions. Specification: [agentskills.io/specification](https://agentskills.io/specification).

## Canonical location

Create skills only under `skills/<name>/SKILL.md`. `<name>` must match the frontmatter `name` field and must be lowercase kebab-case.

Do not add Cursor-only, Codex-only, Claude-only, or Herdr-only copies.

## Frontmatter

Required:

- `name` — 1–64 characters, `a-z`, `0-9`, hyphens; no leading, trailing, or consecutive hyphens
- `description` — 1–1024 characters; what the skill does **and** when to use it; third person; discriminative against the other skills in this kit

Recommended:

- `license: MIT`
- `metadata.kit: d2269-agent-kit`
- `metadata.version` — kit version string

The dependency-free validator intentionally accepts a strict YAML subset: top-level string fields and one-level mappings of string values. Quote values that begin with a number or YAML indicator. Lists, nested mappings, duplicate keys, tabs, and ambiguous plain scalars are rejected.

Do not put model names, platform lock-in, or custom top-level fields that the spec does not define. Extra portable facts go under `metadata` as string values.

Omit Cursor-specific fields (`paths`, `disable-model-invocation`, `icon`, `color`) from canonical skills so other runtimes can load them.

## Body

Every kit skill must state:

- when to use it
- when not to use it
- expected inputs
- required context
- workflow
- expected outputs
- verification / completion criteria
- escalation conditions

Keep `SKILL.md` under 500 lines. Put runtime detail in the skill's own `references/` or `assets/` directory. Repository-level `docs/` are for maintainers and must not be runtime dependencies because skills are installed independently. Link one level from `SKILL.md`; do not nest reference chains or link outside the skill root.

Write English only. Prefer procedures over essays. Do not implement retries,
locks, queues, scheduling, idempotency, or tracker lifecycle state machines in
prose. A role may invoke an external connector for explicitly authorized
mutation when that action belongs to the role, but the connector must own those
deterministic mechanics.

## Descriptions

Agents discover skills from descriptions. If two descriptions could match the same request, rewrite them.

Improve an existing skill before adding a near-duplicate. Create a new skill only when the capability is reusable, meaningfully distinct, procedural, likely to be invoked on its own, and a poor fit for a project rule.

## Validation

From the repository root:

```bash
python3 scripts/validate_skills.py
python3 -m unittest discover -s scripts/tests -v
```

The validator must exit non-zero when skills are invalid. Do not merge failing skills.

Structural validation does not prove correct role behavior. For consequential
role changes, add or update package-local `evals/` scenarios with realistic
prompts and observable pass criteria. Give only the prompt and named raw
artifacts to the evaluated fresh context; keep the pass criteria with the
grader. Retain human review for external side effects.
