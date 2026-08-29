# Installation

`skills/` is canonical. Installation copies or links each self-contained skill directory, including its bundled references and output assets, into a location an agent runtime actually scans. It does not create platform-specific skill forks.

The installer is idempotent, prefers non-destructive updates, supports `--dry-run`, and refuses to silently overwrite destinations that differ from the canonical source.

```bash
python3 scripts/install_skills.py --help
```

## Global vs project

| Scope | Meaning | Typical use |
| --- | --- | --- |
| User / global | Available across repositories on this machine | Personal default roles |
| Project | Available inside one repository | Team-shared roles for that codebase |

Cursor Cloud Agents, remote SSH workers, and similar hosts do **not** receive your home-directory skills. Use project installation (or an image that already contains the skills) in those environments. Source: [Cursor Agent Skills](https://cursor.com/docs/skills).

For project installation, `--project-root` must name an existing directory. The installer refuses missing paths instead of creating a new project tree after a typo.

## Verified discovery paths

Paths below were checked against official documentation at the time of writing. If a vendor changes discovery, update the adapter and this page together. Do not invent additional roots.

### Cursor

Source: [cursor.com/docs/skills](https://cursor.com/docs/skills).

| Scope | Path |
| --- | --- |
| Project | `<repo>/.cursor/skills/` |
| Project (also discovered) | `<repo>/.agents/skills/` |
| User | `~/.cursor/skills/` |
| User (also discovered) | `~/.agents/skills/` |

Cursor also loads `.claude/skills/`, `.codex/skills/`, `~/.claude/skills/`, and `~/.codex/skills/` for compatibility. Installing the same skill into multiple roots causes duplicate discovery. Default Cursor adapter targets:

- user: `~/.cursor/skills/`
- project: `<repo>/.cursor/skills/`

```bash
python3 scripts/install_skills.py --platform cursor --scope user
python3 scripts/install_skills.py --platform cursor --scope project --project-root /path/to/repo
```

### Codex / ChatGPT Codex CLI

Source: [developers.openai.com/codex/skills](https://developers.openai.com/codex/skills).

| Scope | Path |
| --- | --- |
| Project | `<cwd-or-repo>/.agents/skills` (scanned from CWD up to the repository root) |
| User | `$HOME/.agents/skills` |
| Admin / system | `/etc/codex/skills` |

This kit never installs into `/etc/codex/skills` by default.

Codex's built-in skill installer uses `$CODEX_HOME/skills` (default `~/.codex/skills`). That location is **not** the documented USER discovery root. This kit's Codex adapter installs to the documented USER/REPO paths. Optional install into `$CODEX_HOME/skills` is not enabled until we confirm it is a discovery path rather than only an installer destination.

```bash
python3 scripts/install_skills.py --platform codex --scope user
python3 scripts/install_skills.py --platform codex --scope project --project-root /path/to/repo
```

**TODO (ChatGPT web / workspace plugins):** Official packaging of skills as ChatGPT plugins was not implemented in 0.1. Do not assume a web-only install path.

### Claude Code

Source: [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills).

| Scope | Path |
| --- | --- |
| Project | `<repo>/.claude/skills/` |
| User | `~/.claude/skills/` |

```bash
python3 scripts/install_skills.py --platform claude --scope user
python3 scripts/install_skills.py --platform claude --scope project --project-root /path/to/repo
```

Claude Code is optional. Absence of a Claude subscription does not limit the rest of the kit.

### Herdr

Source: [herdr.dev/docs/agent-skill](https://herdr.dev/docs/agent-skill/).

Herdr is a pane/runtime environment. Official documentation describes installing **Herdr's own** skill (`skills/herdr/SKILL.md` from upstream) into coding agents. It does **not** document a Herdr-owned directory for third-party role skills.

Therefore:

- This kit does not vendor the official Herdr skill. Install that independently from upstream (`npx skills add herdrdev/herdr --skill herdr -g` or `herdr --skill`).
- Role skills remain useful without Herdr. Agents running inside Herdr panes discover this kit through **the agent they are**, using Cursor, Codex, or Claude paths above.
- `python3 scripts/install_skills.py --platform herdr` exits with a documented error rather than guessing a path.

**TODO:** If Herdr later documents a first-party root for third-party Agent Skills, verify it and wire the adapter.

## Installer behavior

- `--mode symlink` (default): destination is a symlink to the canonical skill directory. Best when the kit clone is the long-term source.
- `--mode copy`: recursive copy. Use when the destination cannot follow a symlink.
- Existing destinations with the same content (or a symlink already pointing at the canonical directory) are reported as unchanged.
- Existing destinations with different content are skipped and cause a non-zero exit unless `--force` is passed.
- `--dry-run` prints the plan and writes nothing.
- `--skill name` may be repeated to install a subset.

Review scripts and skills before installing. See [SECURITY.md](../SECURITY.md).
