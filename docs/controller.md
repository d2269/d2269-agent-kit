# Lifecycle Controller

The Lifecycle Controller is the deterministic software boundary that executes
the role contracts in this kit. It starts fresh role sessions through Herdr,
validates versioned artifacts, publishes authorized Linear comments, applies
policy-permitted transitions, and persists recovery state in SQLite. It is not a
ninth reasoning role and it does not replace the canonical role skills.

## Maturity

The controller implementation is covered by deterministic fake-boundary tests.
Herdr 0.9.0 command syntax and current Linear GraphQL behavior were checked
against the installed binary and official documentation on 2026-09-19. A
controlled non-production Linear workspace and disposable Git repository must
still be used for live end-to-end verification before production adoption.

## Ownership boundaries

| Boundary | Owns | Does not own |
| --- | --- | --- |
| Human | Workflow start, mutation authorization, architecture acceptance, blocker decisions, scope close-out, merge | Automatic routing details |
| Controller | Lifecycle policy, locks, state, rework counts, artifact validation, routing, receipts, tracker mutations | Technical or acceptance verdicts |
| Role session | One role's reasoning and human-readable report | Tracker mutation or persistent workflow state |
| Herdr | Fresh terminal/agent sessions and observable process state | Success verdicts or workflow policy |
| Linear | Ticket records, comments, configured workflow states | Controller recovery state or role reasoning |
| Git | Source history and exact implementation snapshots | Lifecycle decisions |

`idle` and `done` from Herdr only mean that an agent is ready for input. The
controller treats the JSON result envelope and referenced artifacts as the
authoritative role result. `blocked`, `unknown`, timeout, a stalled prompt,
malformed output, missing artifacts, or identifier mismatches cause a safe stop.

Controller state and envelopes use stable protocol role IDs such as `developer`
and `qa`. Before prompting a Herdr session, the runner maps each ID to this kit's
canonical installed package, such as `d2269-developer` or `d2269-qa`. This keeps
workflow data compact while preventing discovery collisions with third-party
skills. The selected coding agent must have the namespaced packages installed.

## Requirements and installation

- Python 3.10 or newer on a POSIX host; no third-party Python packages are
  required. Version 0.1 uses `fcntl` project locks and has not been verified on
  Windows.
- Git.
- Herdr 0.9.0 or a compatible version exposing the documented CLI commands.
- One supported coding agent: Codex, Claude Code, or Cursor Agent.
- A Linear API key with the least privileges needed by the selected project.

Copy [`controller.example.json`](../controller.example.json) to
`controller.json` in the target repository and replace the project, Linear team,
status, branch, and agent settings. Keep `state_root` outside the Git checkout.
Set the token only in the environment:

```bash
export LINEAR_API_KEY='...'
python3 -m controller doctor --project /path/to/project
```

`doctor` does not mutate Linear. A non-dry run requires the explicit
`--authorize-mutations` flag. This grants only the comments, plan publication,
and status changes permitted by the selected workflow; it does not authorize
merge, arbitrary issue edits, or responses to an agent approval UI.

## Project configuration

The JSON configuration has schema version `1` and contains no secrets:

- `project_id`: stable lower-case project identity. It scopes the database,
  locks, worktrees, runs, mappings, and receipts.
- `repository`: Git checkout for the project.
- `state_root`: external runtime-state parent. The environment variable
  `D2269_CONTROLLER_STATE_ROOT` overrides it.
- `tracker`: `kind: linear`, endpoint, token environment variable, team UUID,
  and semantic status mapping.
- `runner`: `kind: herdr`, `agent_kind`, optional native agent arguments, and a
  bounded timeout.
- `git`: base branch and branch prefix.
- `policy`: default profile, positive `rework_limit`, and `partial_policy`
  (`stop` or `continue`). QA is the terminal automated acceptance gate in
  version 0.1; planned scopes still require human close-out. Optional
  `authorized_minimal_waivers` entries bind the only policy/owner/source tuples
  that an automatically published minimal child contract may use.

Each Linear issue used as a work contract includes a JSON object in its
description. Comments are deliberately not parsed as policy:

```markdown
<!-- d2269-controller-contract
{
  "implementation_readiness": "READY",
  "ticket_revision": "contract-r7",
  "delivery_profile": "standard",
  "links": ["https://example.invalid/authoritative-requirement"]
}
-->
```

For `minimal`, add `code_review_waiver` with `ticket_revision`, exact
`implementation_revision`, `policy`, `authorized_owner`, and
`authoritative_source`. The controller rejects the profile when the waiver is
missing, stale, or does not match the exact Developer result.

Semantic readiness `READY` is separate from the configured Linear `ready`
column. Both gates must pass at workflow start.

## Profiles and CLI

The four controller profiles share one engine:

- `minimal`: Developer → QA; requires an authoritative Code Review waiver.
- `standard`: Developer → Code Review → QA.
- `planned`: Tech Lead `PLAN` → sequential child-ticket delivery → Tech Lead
  `COMPLETENESS_REVIEW` → human close-out.
- `consequential`: Architect `DESIGN` → human architecture acceptance → planned
  delivery → Architect `CONFORMANCE_REVIEW` → human close-out.

Examples:

```bash
python3 -m controller run --project /path/to/project --profile standard --ticket ABC-123 --dry-run
python3 -m controller run --project /path/to/project --profile standard --ticket ABC-123 --authorize-mutations
python3 -m controller run --project /path/to/project --profile planned --scope /path/to/scope.md --authorize-mutations
python3 -m controller status --run run-... --state-root /path/to/state
python3 -m controller decide --run run-... --decision-file decision.json --state-root /path/to/state --authorize-mutations
```

Dry-run reads the target ticket when needed to validate readiness or waiver
policy, but it creates no run, worktree, agent session, comment, plan ticket, or
status transition.

Human decision files are JSON. Allowed actions depend on the recorded gate:

- architecture acceptance: `ACCEPT_ARCHITECTURE`, `REJECT_ARCHITECTURE`, `STOP`;
- blocker review: `RESUME_DEVELOPER`, `REPLAN`, `INVOKE_ARCHITECT`, `STOP`;
- scope close-out: `CLOSE_SCOPE`, `REPLAN`, `STOP`.
- uncertain prompt delivery: `CONFIRM_PROMPT_NOT_ACCEPTED_RETRY`, `STOP`.
- other recorded safe stops: `RETRY_ROLE`, `STOP`.
- uncertain tracker mutation: `RETRY_MUTATION`, `STOP`; this preserves the
  original invocation and idempotency key.

`REPLAN` is available only to `planned` and `consequential` scope runs. It never
changes a minimal or standard run into a scope profile.

## Result envelope

Every role writes one schema-version `1` JSON envelope. The common fields are
`run_id`, `invocation_id`, `project_id`, `role`, `mode`, ticket and exact
revision identifiers, semantic `result`, report and comment paths,
`comment_state`, requested action, next owner, and RFC3339 timestamp. Tech Lead
`PLAN` additionally uses `payload_path` because validated child-ticket data must
be machine-readable for publication.

The Herdr prompt supplies controller-owned envelope fields as an exact JSON
block. The role copies those values without deriving protocol IDs from the
installed `d2269-*` package name and without converting JSON `null` to strings
such as `default` or `N/A`. The role produces only its semantic result fields
and timestamp. Developer additionally records its resulting Git revision:
`COMPLETE` requires the exact final revision, while `PARTIAL` or `BLOCKED` may
use the current revision or `null` when no meaningful revision exists.

The plan payload is one JSON object with stable `plan_id`, `revision`, `title`,
`description`, and a `tickets` array. Every child has `local_id`, `title`,
`description`, and a `contract` containing `implementation_readiness: READY` and
`delivery_profile: minimal|standard`. Linear receives one parent plan issue and
its child issues. Stable deterministic UUIDs plus persisted local-to-Linear
mappings make creation recoverable after a crash; later plan revisions update
the same records only when their current content matches the last controller
receipt. Intervening edits cause a precondition stop instead of being
overwritten. UUIDs are scoped by controller project, Linear team, plan, and
local task ID.

Automatically published plans may select `minimal` only when the child contract
contains an explicit ticket revision, an exact implementation revision, and a
complete waiver whose policy, owner, and authoritative source exactly match a
project-configured `authorized_minimal_waivers` entry. With an empty allowlist,
a role-generated plan cannot grant itself a Code Review waiver. Directly
selected minimal tickets require the same allowlisted authority and current
exact-revision contract.

The controller checks the role/mode verdict vocabulary, requested action,
identifiers, exact revision, artifact paths, non-empty report and comment, and
the optional plan payload before any routing. Automated roles must return
`READY_TO_POST`; they never mutate Linear themselves.

## State, idempotency, and recovery

Runtime data is isolated below `state_root/<project_id>/`:

```text
controller.sqlite3
artifacts/
locks/
receipts/
runs/
worktrees/
```

SQLite records immutable run policy, lifecycle state, invocations, exact
revisions, artifacts and digests, comment and transition receipts, rework
events, mappings, decisions, errors, and timestamps. A non-blocking project lock
permits only one active controller process per project. Different projects can
use identical Linear identifiers or Herdr pane IDs without state collision.
The project lock covers active-run lookup and creation, not only execution.

Every logical role gate has a deterministic invocation identity. Role output is
written to a temporary staging directory, strictly validated, then copied into
the durable artifact directory. If the controller process exits after a valid
envelope was written, recovery consumes that envelope without sending a second
prompt. If prompt acceptance is uncertain and no envelope exists, recovery
requires an explicit human retry decision. Prior validated artifacts and
mutation receipts are supplied to later fresh role sessions as untrusted
evidence paths and digests.

Comments carry a controller idempotency marker. On replay, the Linear adapter
finds the existing marker before creating another comment. Transitions read and
check the current contract revision and expected workflow state, apply the
mutation, re-read the issue, and persist the verified receipt. Linear does not
offer an atomic compare-and-set issue mutation; the adapter therefore detects
precondition drift before mutation and verifies the result afterward. This
remaining race is one reason controlled live verification is required.

Re-running the same target recovers its active run. A timeout or stalled Herdr
prompt records `HERDR_TIMEOUT_UNCERTAIN` and enters `HUMAN_REVIEW_REQUIRED`; the
controller does not resubmit automatically because the original prompt may have
been accepted. A human must inspect the saved invocation and Herdr pane, then
explicitly confirm that no prompt was accepted before retrying.
Other safe stops preserve their reason and expose only explicit `RETRY_ROLE` or
`STOP` resolution; re-running by itself never relaunches a role. The immutable
configuration snapshot must still match before a retry is accepted.
Tracker failures use a distinct `RETRY_MUTATION` path that reuses the validated
role result and its original comment or transition idempotency key; it never
creates a fresh role invocation merely because receipt verification was
uncertain.

## Git and worktrees

Developer receives one isolated writable branch worktree. Code Review and QA
receive fresh detached worktrees for the exact implementation revision. Clean
work uses `git:<commit-sha>`. Dirty work uses a stable
`snapshot:<commit-sha>:<sha256>` over the binary diff and untracked files; the
snapshot is reproduced in each review context and re-hashed before use.

The controller does not merge branches. It does not automatically remove
worktrees, which avoids deleting dirty work. An operator may clean up owned
worktrees after verifying that no work must be preserved.

## Linear safety

The adapter uses the official GraphQL endpoint and checks both HTTP failures and
the GraphQL `errors` array, including HTTP 200 partial failures. It reads the
current issue before mutation, validates the immutable ticket-contract revision,
maps semantic states through project configuration, verifies every resulting
comment or state, and stores a receipt. API keys are never written to prompts,
logs, reports, configuration, or SQLite.
The adapter also rejects issues outside the configured Linear team. A declared
ticket revision is combined with a content hash, so changing the contract body,
labels, or parent invalidates the controller revision instead of bypassing it.

Do not grant production credentials until a controlled workspace verifies the
team's exact workflow names, permissions, issue-description contract, and
recovery procedure. Webhooks, automatic ticket discovery, and continuous
polling are intentionally absent; a human starts each workflow.

## Verification and demonstrations

Run all controller tests:

```bash
python3 -m unittest discover -s controller/tests -t . -v
```

Run the two credential-free demonstrations:

```bash
python3 scripts/demo_controller.py
```

The demonstration asserts the final SQLite lifecycle state, invocation order,
rework count, and persisted receipts for both a successful standard ticket and
three returns followed by `HUMAN_REVIEW_REQUIRED`.

## Troubleshooting

- `implementation_readiness is not READY`: update the authoritative ticket
  contract; moving a Linear card is insufficient.
- `STALE_TICKET_REVISION`: inspect the new ticket contract and start or resume
  only after an authorized decision.
- `IMPLEMENTATION_CHANGED`: Code Review or QA evidence is invalid for the new
  revision; a fresh gate is required.
- `RECEIPT_MISMATCH`: stop external mutations and inspect Linear plus the SQLite
  audit record.
- `HERDR_BLOCKED`: inspect the agent approval or question UI; the controller
  never answers it automatically.
- `HERDR_TIMEOUT_UNCERTAIN`: determine whether the prompt was accepted before
  any retry.
- `CONFIG_CHANGED`: restore the recorded configuration or stop the run; policy
  never changes silently in the middle of a lifecycle.

Official references: [Herdr agent automation](https://herdr.dev/docs/agent-automation/),
[Herdr CLI](https://herdr.dev/docs/cli-reference/),
[Herdr session restore](https://herdr.dev/docs/session-state/), and
[Linear GraphQL](https://linear.app/developers/graphql).
