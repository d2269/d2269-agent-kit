# Execution Profiles

Execution profiles let a human or deterministic controller apply the role skills
in proportion to the work. They are deployment policy, not new roles and not a
workflow engine. Select the least complex profile whose entry conditions and
quality gates cover the actual risk.

## Selection rules

- Select by task shape, uncertainty, blast radius, reversibility, required
  independent judgment, and available verification—not by elapsed time, token
  count, model name, or model price.
- Keep one coherent objective with one role while its instructions, tools,
  authority, and output contract remain appropriate. Add another role only when
  one of those contracts materially changes.
- A role may continue across multiple fresh sessions. Session count is not role
  count; use a durable checkpoint so the next session does not reconstruct prior
  conversation.
- The human or authoritative workflow policy selects the profile and required
  gates. Orchestrator may advise only when routing is genuinely ambiguous.
- Deterministic routing, retries, counters, tracker transitions, and model
  assignment belong in a controller or other execution software.

## Profiles

| Profile | Entry conditions | Route | Required artifact and exit |
| --- | --- | --- | --- |
| **Focused investigation** | One bounded research question; no production change is authorized; the result is evidence for a later decision | Human or requesting role → Researcher → consumer | `Research Report`; exit when answered, explicitly unanswerable, or blocked with one next action |
| **Lean ticket delivery** | One current `READY` ticket; localized and reversible change; strong automated verification; authoritative policy already grants a Code Review waiver for this ticket revision | Developer `COMPLETE` → QA → policy-defined next gate or `Done` | Implementation Report and QA Report, both bound to the exact ticket revision; Developer does not self-approve acceptance |
| **Standard ticket delivery** | One current `READY` ticket; independent engineering and acceptance judgments are required | Developer `COMPLETE` → Code Review `PASS` → QA `PASS` → policy-defined next gate or `Done` | Ticket-bound implementation, review, and acceptance evidence with mandatory history comments |
| **Planned scope delivery** | Several related or dependent tickets require decomposition and scope-level completeness, but no consequential architecture condition applies | Tech Lead `PLAN` → lean or standard delivery per ticket → Tech Lead `COMPLETENESS_REVIEW` → human close-out | Implementation Plan, independently usable child tickets, per-ticket evidence, scope-completeness verdict, and human decision |
| **Consequential scope delivery** | The scope implements an accepted architecture decision or workstream, or affects a named system boundary, public or cross-component contract, quality attribute, or migration decision | Architect `DESIGN` when the baseline is missing or must change → Tech Lead `PLAN` → lean or standard delivery per ticket → Tech Lead `COMPLETENESS_REVIEW` → Architect `CONFORMANCE_REVIEW` → human close-out | Accepted architecture baseline, plan and child tickets, per-ticket evidence, scope-completeness verdict, conformance verdict, and human decision |

Researcher may precede any profile when a bounded evidence gap prevents the
owning role from proceeding. Research does not silently become implementation:
if it discovers a required production change, it closes with a report and hands
the evidence to Architect, Tech Lead, or a separately authorized Developer
ticket.

The lean profile is not an implicit permission to skip Code Review. Its waiver
must come from an authoritative contract source, name the permitting policy and
owner, and apply to the current ticket and exact implementation target. If those
conditions are absent, use standard ticket delivery. QA remains independent.

## Long-running single-role work

A long investigation can remain one Researcher role even when it spans hours,
days, or several context windows. Before a session or context boundary, update
the owning Research Report with:

- report status (`IN_PROGRESS`, `COMPLETE`, or `BLOCKED`);
- completion and stopping conditions, including what remains unsatisfied;
- evidence inspected and work completed;
- confirmed findings, assumptions, and unresolved questions;
- failed approaches that should not be repeated;
- the next bounded probe or exact unblock action.

The next fresh session resumes the same research objective from that artifact.
Duration alone does not justify Architect, Tech Lead, Developer, Code Review, or
QA. Add a role only when the output is ready for a different kind of decision or
authorized action.

## Recovery shared by delivery profiles

`PARTIAL`, `BLOCKED`, and `CHANGES_REQUESTED` follow the owning role contracts.
A deterministic rework limit may pause a ticket and request Tech Lead
`BLOCKER_REVIEW`. Every such review produces `HUMAN_REVIEW_REQUIRED`; the human
then records whether to resume, revise the ticket or plan, request Architect or
Researcher work, or stop. The failure count is a trigger, not a diagnosis.

## Model assignment and evaluation

Keep model selection outside role skills and profile definitions. Choose a model
for a profile from representative evaluations of outcome quality, instruction
following, tool use, latency, and cost. A cost-efficient model may be the best
choice for a long, bounded investigation when it meets the evidence and stopping
criteria; duration alone is not a reason to escalate. Escalate when measured
quality, unresolved uncertainty, risk, or required capability demands it.

Evaluate the profiles as workflows as well as individual role outputs. Include
cases that test correct profile selection, unjustified gate skipping, role-scope
leakage, fresh-session continuation, exact artifact handoff, and the final state
of the repository or tracker. Prefer deterministic outcome checks where
possible, with calibrated model or human grading for judgment-heavy results.

## Basis

- [OpenAI orchestration and handoffs](https://developers.openai.com/api/docs/guides/agents/orchestration)
  recommends starting with one agent and adding specialists only when a changed
  contract materially benefits from isolation.
- [OpenAI agent workflow evaluation](https://developers.openai.com/api/docs/guides/agent-evals)
  recommends inspecting traces while debugging and using repeatable datasets and
  eval runs for workflow comparisons.
- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
  recommends simple, composable patterns and adding complexity only when it
  demonstrably improves outcomes.
- [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
  shows incremental work and durable progress artifacts across fresh context
  windows, while leaving the best single-agent versus multi-agent split open.
