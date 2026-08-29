# Cursor adapter

Installs this kit's canonical skills where Cursor discovers Agent Skills.

Verified source: [Cursor Agent Skills](https://cursor.com/docs/skills) (retrieved 2026-08-29).

## Paths

| Scope | Installer destination |
| --- | --- |
| User | `~/.cursor/skills/<skill>/` |
| Project | `<repo>/.cursor/skills/<skill>/` |

Cursor also discovers `.agents/skills/`, `~/.agents/skills/`, and Claude/Codex skill directories. This adapter uses the Cursor-native roots so a single install does not appear twice. If you already installed the Codex adapter into `~/.agents/skills`, do not also install Cursor user skills unless you accept duplicate discovery.

Cloud Agents and remote workers do not receive `~/.cursor/skills/`. Use `--scope project` in those environments.

## Commands

```bash
python3 scripts/install_skills.py --platform cursor --scope user --dry-run
python3 scripts/install_skills.py --platform cursor --scope user
python3 scripts/install_skills.py --platform cursor --scope project --project-root /path/to/repo
```

Prefer `--mode symlink` while this clone remains the source of truth.

## Non-goals

This adapter does not create Cursor Rules, Custom Modes, or model assignments.
