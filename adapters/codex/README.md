# Codex adapter

Installs this kit's canonical skills where Codex CLI documents skill discovery.

Verified source: [Build skills — Codex](https://developers.openai.com/codex/skills) (retrieved 2026-08-29).

## Paths

| Scope | Installer destination |
| --- | --- |
| User | `$HOME/.agents/skills/<skill>/` |
| Project | `<repo>/.agents/skills/<skill>/` |

Codex scans `.agents/skills` from the current working directory up to the repository root. Project install uses the repository root you pass as `--project-root`.

This adapter does **not** install into `/etc/codex/skills`.

Codex's bundled skill installer writes `$CODEX_HOME/skills` (default `~/.codex/skills`). That is not the documented USER discovery table. **TODO:** confirm whether `$CODEX_HOME/skills` is also scanned at runtime; do not enable it here until verified.

## Commands

```bash
python3 scripts/install_skills.py --platform codex --scope user --dry-run
python3 scripts/install_skills.py --platform codex --scope user
python3 scripts/install_skills.py --platform codex --scope project --project-root /path/to/repo
```

## ChatGPT

**TODO:** ChatGPT workspace plugin packaging is not implemented in 0.1. The same `SKILL.md` files are the intended payload when that path is verified.

## Non-goals

This adapter does not edit `~/.codex/config.toml` or disable built-in skills.
