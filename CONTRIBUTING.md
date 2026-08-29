# Contributing

D2269 Agent Kit is currently in early development. External pull requests are
temporarily not accepted while the role contracts and behavioral evaluation
baseline are being stabilized.

Feedback and audit reports are welcome through the maintainer's
[LinkedIn](https://www.linkedin.com/in/stanislavd2269/).

For security vulnerabilities, follow [SECURITY.md](SECURITY.md) and do not
publish sensitive details publicly.

The guidance below applies to maintainer work and will also apply when external
contributions reopen. Public content must be English.

## Maintainer guidance

### Before you start

Read [AGENTS.md](AGENTS.md), [docs/architecture.md](docs/architecture.md), and [docs/authoring-skills.md](docs/authoring-skills.md).

### Typical changes

| Change | Where |
| --- | --- |
| Role procedure | `skills/<name>/SKILL.md` and optional `references/` |
| Output shape | `skills/<name>/assets/` (structure only; do not paste full skill text) |
| Kit docs | `README.md`, `docs/` |
| Validator / installer | `scripts/` plus tests in `scripts/tests/` |
| Discovery paths | `adapters/` and [docs/installation.md](docs/installation.md) together |

Do not copy a skill into `.cursor/skills`, `.agents/skills`, or `.claude/skills` inside this repository. Those directories are gitignored so local installs cannot fork the canonical tree.

### New skills

Use the test in AGENTS.md. If the capability belongs in an existing role, update that role instead.

Keep frontmatter `name` equal to the directory name. Write a discriminative description. Stay model-neutral.

Keep every runtime dependency inside its skill directory. A `SKILL.md` must not link to repository-level docs or another skill because standalone copy installation would break that link.

### Tests

From the repository root:

```bash
python3 scripts/validate_skills.py
python3 -m unittest discover -s scripts/tests -v
```

There are no required third-party packages. The scripts are stdlib-only and verified on Python 3.10. Older interpreters are not tested; if you rely on one, run the tests before trusting it.

### Pull requests when contributions reopen

- Explain why the change belongs in a shared toolkit
- Note any official documentation you used to verify adapter paths
- Do not commit secrets, `.env` files, or private paths
