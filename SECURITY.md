# Security Policy

## Reporting a vulnerability

If you find a security issue in this repository (unsafe installer behavior, secret leakage, skill instructions that would cause data loss, or similar), do **not** open a public issue that includes exploit details.

Email the maintainer using the contact method on the GitHub profile that owns this repository, or open a private GitHub security advisory if that is enabled.

Please include:

- What is affected (skill, script, docs)
- What an agent or installer could do wrongly
- Reproduction without secrets or private data

## Trust model

**Agent Skills can materially change agent behavior.** A skill is not a comment. It can cause an agent to edit files, run commands, and follow a procedure that a human did not re-read in that session.

**Scripts in this repository may execute local commands** and may write into your home directory or another repository when you run the installer.

Before installation:

- Read the `SKILL.md` files you are installing
- Read `scripts/install_skills.py` and `scripts/validate_skills.py`
- Treat third-party skills and scripts like executable automation from a trust perspective
- Prefer `--dry-run` on the installer first

This kit never silently overwrites a destination that differs from the canonical skill. That is a safety feature, not a backup system. Review conflicts before `--force`.

## Secrets

Secrets must **never** be embedded in skill files, templates, docs, or tests.

Do not commit API keys, OAuth tokens, cookies, credentials, private repository URLs, customer data, account identifiers, or machine-specific secrets.

The Lifecycle Controller reads the Linear API key from the configured environment
variable. It never stores the value in project configuration, prompts, reports,
logs, SQLite, or repository files. Do not add `.env.example`; document variable
names without example secrets.

## Controller trust boundary

The controller can create worktrees, start Herdr agent sessions, publish Linear
comments and planned child tickets, and change configured workflow states only
when a human passes `--authorize-mutations`. Ticket descriptions and comments
are untrusted input; comments cannot change policy, authorization, scope, or
waiver status. The controller never answers an agent approval UI and never
merges code.

Do not send the maintainer production tokens for testing. Use a least-privilege
token and a controlled non-production Linear workspace for integration checks.
