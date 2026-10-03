# Installation

`skills/` is canonical. Installation copies or links each self-contained skill directory, including its bundled references and output assets, into a location an agent runtime actually scans. It does not create platform-specific skill forks.

The installer is idempotent, prefers non-destructive updates, supports `--dry-run`, and refuses to silently overwrite destinations that differ from the canonical source.

```bash
python3 scripts/install_skills.py --help
```

## Canonical skill names

All packages use the `d2269-` namespace so generic role names do not collide
with skills installed by another project. Directory names, `SKILL.md` names,
and explicit invocations are identical:

| Role | Canonical package and Codex invocation |
| --- | --- |
| Architect | `$d2269-architect` |
| Tech Lead | `$d2269-tech-lead` |
| Developer | `$d2269-developer` |
| Code Review | `$d2269-code-review` |
| QA | `$d2269-qa` |
| Researcher | `$d2269-researcher` |
| Technical Documentation | `$d2269-technical-documentation` |
| Orchestrator | `$d2269-orchestrator` |

For example, install only Architect with:

```bash
python3 scripts/install_skills.py --platform codex --scope user --skill d2269-architect
```

Names without the prefix are internal lifecycle role IDs only. They appear in
machine-readable envelopes and controller state, but they do not identify an
installed skill package.

## Global vs project

| Scope | Meaning | Typical use |
| --- | --- | --- |
| User / global | Available across repositories on this machine | Personal default roles |
| Project | Available inside one repository | Team-shared roles for that codebase |

Cursor Cloud Agents, remote SSH workers, and similar hosts do **not** receive your home-directory skills. Use project installation (or an image that already contains the skills) in those environments. Source: [Cursor Agent Skills](https://cursor.com/docs/skills).

For project installation, `--project-root` must name an existing directory. The installer refuses missing paths instead of creating a new project tree after a typo.

## Optional manager-routing policy

The optional project-local manager policy maps each canonical D2269 skill to a
project-selected primary executor and explicitly allowlisted alternatives. A
consuming project may use native subagents, Herdr workers, or both. The policy
has no preselected provider or model, contains no credentials, and the template
defaults to asking a human when no configured executor is available.

To preview and initialize a project policy:

```bash
python3 scripts/init_manager_policy.py --project-root /path/to/repo --dry-run
python3 scripts/init_manager_policy.py --project-root /path/to/repo
```

Use `--add-agents-marker` to create `AGENTS.md` with a bounded pointer when that
file does not exist. Existing `AGENTS.md` files are never rewritten: an exact
existing marker is left unchanged, while a missing or conflicting marker causes
a safe refusal and must be resolved manually. Policy and marker files are
created exclusively through descriptor-relative, no-follow filesystem
operations; initialization fails closed when the platform cannot provide the
required operations. It opens the absolute project path from the filesystem root
one component at a time, rejects symlink components, and checks that opened
components still match their directory entries after traversal. It detects
symlink or directory-entry swaps during that traversal. After a directory
descriptor has been pinned, a same-user process can still rename that directory
elsewhere; Python's portable standard library cannot prevent every such rename.
Avoid running initialization while another process is moving project
directories. If a file creation fails after its pathname is published, an
incomplete destination may remain. The initializer never unlinks or rolls back
a published pathname. If policy creation succeeds but later `AGENTS.md`
creation fails, the policy remains. The error identifies the destination and
asks for manual inspection; inspect and remove any incomplete file before
retrying. Existing files are never removed. Fill in the executor choices and
validate the result:

```bash
python3 scripts/validate_manager_policy.py /path/to/repo/.d2269/manager-policy.json
```

Projects can use the eight role skills without this optional layer. See
[Manager routing](herdr-manager.md) for the contract, safe-stop rules, and
current limitations.

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
- `--skill name` may be repeated to install a subset; use the complete
  canonical name, for example `--skill d2269-architect`.

## Migration from unprefixed skill names

Releases before the namespace change installed generic directories. They map as
follows:

| Earlier D2269 directory name | Current directory |
| --- | --- |
| `architect` | `d2269-architect` |
| `tech-lead` | `d2269-tech-lead` |
| `developer` | `d2269-developer` |
| `code-review` | `d2269-code-review` |
| `qa` | `d2269-qa` |
| `researcher` | `d2269-researcher` |
| `technical-documentation` | `d2269-technical-documentation` |
| `orchestrator` | `d2269-orchestrator` |

The installer reports a matching unprefixed directory as potentially legacy or
unrelated, but does not modify or delete it. An `architect` or `developer` skill
may belong to another project. Install the current packages, open a fresh agent
task, and verify the `D2269 ...` entries. Archive, remove, or disable an
unprefixed directory only after confirming it is an earlier D2269 installation.
Leaving both D2269 versions installed is safe but creates ambiguous duplicate
choices in skill pickers; leaving an unrelated skill installed is expected.

Review scripts and skills before installing. See [SECURITY.md](../SECURITY.md).
