# Claude adapter

Installs this kit's canonical skills where Claude Code discovers custom skills.

Verified source: [Extend Claude with skills](https://code.claude.com/docs/en/skills) (retrieved 2026-08-29).

## Paths

| Scope | Installer destination |
| --- | --- |
| User | `~/.claude/skills/<skill>/` |
| Project | `<repo>/.claude/skills/<skill>/` |

Claude Code is optional. You can use the rest of this kit without a Claude subscription.

## Commands

```bash
python3 scripts/install_skills.py --platform claude --scope user --dry-run
python3 scripts/install_skills.py --platform claude --scope user
python3 scripts/install_skills.py --platform claude --scope project --project-root /path/to/repo
```

## Non-goals

This adapter does not install Claude plugins, enterprise managed skills, or the official Herdr skill.
