# Herdr adapter

Herdr is a local multi-agent **runtime**. It is not the canonical owner of these role skills.

Verified source: [Agent skill file | herdr](https://herdr.dev/docs/agent-skill/) (retrieved 2026-08-29).

## What official docs cover

Herdr ships **its own** skill at upstream `skills/herdr/SKILL.md`. That skill teaches an agent how to control Herdr panes when `HERDR_ENV=1`. Install it from upstream, not from this repository:

```bash
npx skills add herdrdev/herdr --skill herdr -g
```

Or print the copy bundled with the installed binary:

```bash
herdr --skill
```

Do not vendor that file here. Keep it independently updatable.

## What official docs do not cover

Herdr documentation does not define a Herdr-owned directory for **third-party** role skills such as `architect` or `qa`.

Agents running inside Herdr panes discover this kit through the agent they are (Cursor, Codex, Claude, and so on). Use those adapters.

```bash
python3 scripts/install_skills.py --platform herdr
```

This command exits non-zero with the TODO below rather than inventing a path.

## TODO

If Herdr documents a first-party root for third-party Agent Skills, verify the path against that documentation and then teach `scripts/install_skills.py` the `herdr` platform target.

Until then, role skills in this kit remain usable without Herdr.
