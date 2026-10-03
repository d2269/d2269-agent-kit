# Optional Manager Routing Policy

This guide describes an optional project-local layer for managers that delegate
D2269 roles to native subagents, Herdr workers, or both. It is a consumer-project
configuration pattern, not a ninth D2269 role and not a workflow engine. Projects
that do not need delegated workers can use the eight role skills on their own.

The kit provides a neutral policy template, validator, opt-in initializer, and
concise manager instructions. The policy belongs in the consuming repository
because executor and model choices depend on that project's runtime, access
rules, and budget. The initializer creates the file and may add a bounded note
to `AGENTS.md`; it does not select models or configure an executor for you.

## Boundaries

- The eight canonical role skills remain the source of role semantics,
  authority, inputs, outputs, and lifecycle requirements.
- The optional policy selects a primary executor for each D2269 skill and an
  allowlist of alternatives. It contains no provider or model defaults.
- A consumer project may use its manager runtime's native subagents, Herdr
  workers, or a combination. Herdr is optional.
- The Lifecycle Controller is a separate optional product layer. Its runner
  configuration, SQLite lifecycle state, tracker state, and worktree behavior
  are not the portable manager policy and do not configure a free-standing
  manager.
- The policy does not grant tracker mutations, answer agent approval prompts,
  select delivery profiles, or change lifecycle gates.

## Consumer project setup

To opt in, initialize the consumer project. Preview first, then create the
template; add the bounded manager note to `AGENTS.md` only if wanted:

```bash
python3 scripts/init_manager_policy.py --project-root /path/to/repo --dry-run
python3 scripts/init_manager_policy.py --project-root /path/to/repo
python3 scripts/init_manager_policy.py --project-root /path/to/repo --add-agents-marker
```

The initializer preserves existing policy files. With the opt-in flag, it
creates `AGENTS.md` only when that file is absent. An existing file with the
exact marker stays unchanged; an existing file with a missing, partial, or
conflicting marker is refused for manual resolution. The initializer uses
descriptor-relative exclusive creation with no-follow checks and fails closed
when the platform lacks those filesystem operations. For each role you want to
route, add its `primary` and any alternatives selected by the consumer project.
Project paths are opened component by component from the filesystem root;
symlink components and entry swaps detected during traversal are refused. A
same-user process may still rename an already pinned directory elsewhere; the
portable standard library cannot prevent every such rename, so do not move the
project concurrently with initialization. If writing fails after a pathname is
created, the file may remain incomplete. The initializer never unlinks or rolls
back published pathnames; if policy creation succeeds but later `AGENTS.md`
creation fails, the policy remains. The error requests manual inspection and
removal of any incomplete file before retrying.
Validate later edits with:

```bash
python3 scripts/validate_manager_policy.py /path/to/repo/.d2269/manager-policy.json
```

The policy should name the canonical `d2269-*` skill, the executor kind, and
only the runtime-specific selector or arguments required by that executor.
Project owners choose model identifiers and, for Herdr, optional agent CLI
arguments. Keep secrets in the runtime's credential store or environment,
never in the policy. A Herdr route must identify both the upstream Herdr agent
kind and the requested model; any additional agent CLI arguments pass through
Herdr's documented argument separator. A model selection is valid only where
the chosen runtime documents support for it. If the runtime cannot honor it,
the executor is unavailable and the manager asks the human.

### Fill in executor values

Use exact runtime identifiers; do not copy the placeholder strings below.

1. For `native`, copy the model ID accepted by the manager runtime's model
   selector.
2. For `herdr`, choose a `kind` supported by the installed Herdr release. Check
   `herdr agent start --help` or the current
   [Herdr CLI reference](https://herdr.dev/docs/cli-reference/). Common kinds
   include `codex`, `claude`, and `cursor`.
3. Copy the exact model ID from that agent's own CLI help or documentation.
   Herdr does not define or translate model IDs.
4. Put the model ID in `model`. Put only other agent-specific launch options in
   `args`; never put credentials in either field.
5. Run the validator, then smoke-test the selected agent in a spare Herdr pane.
   Validation checks policy shape and safety, not whether the runtime supports
   the requested kind or model.

The policy is declarative. At launch, the manager translates `model` to the
selected agent's documented model option. The equivalent Herdr command has this
shape:

```bash
herdr agent start <name> --kind <kind> --pane <pane-id> -- \
  <documented-model-option> <model-id> <args...>
```

The checked-in template has this shape; see
[`manager-policy/schema.json`](../manager-policy/schema.json) for its schema:

```json
{
  "schema_version": "1",
  "routes": {}
}
```

The empty template avoids creating unused role settings. A route is added only
when the consumer project chooses to configure that skill. Its `primary` is
required and alternatives are explicitly listed:

```json
{
  "schema_version": "1",
  "routes": {
    "d2269-developer": {
      "primary": {"executor": "native", "model": "<exact-native-model-id>"},
      "alternatives": [
        {
          "executor": "herdr",
          "kind": "codex",
          "model": "<exact-model-id-from-the-codex-cli>",
          "args": []
        }
      ]
    }
  }
}
```

There are no concrete model defaults. A skill without a configured route means
the manager asks the human rather than guess. Alternatives are an explicit
allowlist, not a general permission to switch providers. The manager uses the
primary when available. If it is unavailable, the manager asks the human and
may use only a listed alternative that the human explicitly selects; it never
switches executors automatically or uses an unlisted worker.

## Manager procedure

For each delegated stage, the manager:

1. Determines the required D2269 role from the task and the lifecycle contract.
2. Reads the project's policy and selects that skill's configured primary.
3. Uses the primary. If it is missing or unavailable, asks the human; it may
   use a listed alternative only after the human explicitly chooses it.
4. Starts the worker with a bounded handoff: the ticket or task contract, exact
   revision, required references or prior reports, acceptance criteria, and the
   expected role output. Do not forward the manager's full conversation history.
5. Explicitly invokes the canonical role skill, for example
   `$d2269-code-review`, in the worker's native agent environment.
6. Checks that the result satisfies that skill's output contract before routing
   it to the next stage.

Executor choice never changes which role owns the judgment. Session continuity,
freshness, exact-revision binding, and rework routing follow the canonical
[lifecycle role contracts](lifecycle-role-contracts.md) and
[handoff contract](handoff-contract.md). If the selected runtime cannot satisfy
one of those requirements, the manager records the limitation and asks the
human rather than claiming compliance.

Managers may delegate independent work in parallel only when the role contracts
and task dependencies permit it. Each handoff remains bounded to one role's
responsibility and has a clear expected artifact or verdict. Do not ask a
Developer to self-review, a Reviewer to patch, or QA to implement a fix.

## Human decisions and safe stops

A worker approval or question prompt is a human interaction boundary. The
manager surfaces it and waits for a human decision; it never sends an approval
response automatically. A blocked or unknown worker, timeout, stalled prompt,
missing required context, or unavailable primary is a safe stop. The manager
does not blindly resubmit an uncertain prompt and does not silently replace a
worker. It uses the primary when available. Otherwise it asks the human and may
use only a specific alternative that the human explicitly selects from that
role's allowlist. It never selects an unlisted worker.

The optional routing policy does not authorize issue updates, comments, merges,
deployment, or other external mutations. Those remain governed by the consumer
project's workflow authority and any separately configured controller.

## Herdr execution

Herdr is one optional executor for projects whose manager operates in a Herdr
workspace. Install Herdr's own control skill from upstream; this kit does not
vendor it. Install D2269 role skills for the native agent running in each Herdr
worker. Herdr currently does not document a separate third-party role-skill
directory; see [Installation](installation.md#herdr) and the
[Herdr adapter](../adapters/herdr/README.md).

The manager uses the installed official Herdr skill and the release-matched CLI
instructions to create, prompt, inspect, and wait for workers. Do not add an
MCP/socket wrapper or infer undocumented commands. Native subagents need no
Herdr installation and follow the same D2269 role contracts.

## Current limitations

- The validator checks the static JSON shape, rejects common credential fields,
  assignments, and token families without echoing user-controlled values. It
  cannot guarantee detection of every secret format or prove that runtime model
  names, Herdr agent kinds, CLI arguments, or manager capabilities are valid.
- This guide defines expected manager behavior; the kit does not currently
  enforce session freshness, bounded handoffs, fallback choices, or human gates
  for arbitrary native managers.
- The Lifecycle Controller keeps its existing single-runner configuration and
  does not consume this policy. A future integration would require a separate
  accepted design and deterministic implementation.
- Herdr worker restoration, provider interruption detection, and cross-provider
  model equivalence have not been verified as portable behavior.

See [AD-002](decisions/AD-002-portable-manager-routing-policy.md) for the accepted
optional policy-layer decision and its separation from the controller.
