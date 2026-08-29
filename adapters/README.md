# Adapters

Adapters install canonical skills from `skills/` into an agent runtime's discovery path. They do not rewrite skill bodies.

| Adapter | Default user path | Default project path | Status |
| --- | --- | --- | --- |
| [cursor](cursor/) | `~/.cursor/skills/` | `<repo>/.cursor/skills/` | Verified |
| [codex](codex/) | `$HOME/.agents/skills` | `<repo>/.agents/skills` | Verified |
| [claude](claude/) | `~/.claude/skills/` | `<repo>/.claude/skills/` | Verified |
| [herdr](herdr/) | — | — | Documented TODO; installer refuses |

Use the shared installer:

```bash
python3 scripts/install_skills.py --platform <cursor|codex|claude> --scope <user|project> [--project-root PATH] [--dry-run]
```

Details: [docs/installation.md](../docs/installation.md).
