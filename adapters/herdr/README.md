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

Herdr documentation does not define a Herdr-owned directory for **third-party** role skills such as `d2269-architect` or `d2269-qa`.

Agents running inside Herdr panes discover this kit through the agent they are (Cursor, Codex, Claude, and so on). Use those adapters.

```bash
python3 scripts/install_skills.py --platform herdr
```

This command exits non-zero with the TODO below rather than inventing a path.

## TODO

If Herdr documents a first-party root for third-party Agent Skills, verify the path against that documentation and then teach `scripts/install_skills.py` the `herdr` platform target.

Until then, role skills in this kit remain usable without Herdr.

## Lifecycle Controller

The controller uses the installed Herdr CLI as a role-session runner; it does
not install role skills into a Herdr-owned directory. Install the role skills for
the selected coding agent, then configure `runner.agent_kind` as `codex`,
`claude`, or `cursor`. See [Lifecycle Controller](../../docs/controller.md).

The adapter follows the official automation contract: parse returned JSON IDs,
start the agent in an existing shell pane, use a bounded `agent prompt --wait`,
and treat `blocked`, `unknown`, timeout, or stalled submission as safe-stop
conditions. It never treats Herdr `idle` or `done` as the role verdict.
