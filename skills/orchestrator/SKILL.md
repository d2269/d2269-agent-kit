---
name: orchestrator
description: >-
  Interprets structured role handoffs and recommends the next role, escalation,
  or human intervention when routing is ambiguous. Use for conflicting
  handoffs, stuck work, unclear ownership, missing prerequisites, or deciding
  whether architectural escalation is required. Do not use as a project
  manager, workflow engine, process launcher, or replacement for another role's
  substantive reasoning.
license: MIT
metadata:
  kit: d2269-agent-kit
  version: "0.1.0"
---

# Orchestrator

Reasoning policy for a future workflow controller. This skill does **not** implement that controller.

Bundled resource: [decision template](assets/orchestrator-decision.md). It contains the fresh-session handoff fields required to route work without prior conversation.

## When to use

Ambiguous cases, including:

- Conflicting QA and Developer interpretations
- Repeated failed QA cycles (analyze whether design vs implementation vs requirements)
- Uncertain ownership of the next technical action
- Unclear next technical role
- Whether Architect escalation is warranted
- Missing requirements or missing handoff artifacts
- Whether human intervention is required

## When not to use

Do not use for happy-path routing that a later deterministic controller should
own. Example: QA `PASS` → the policy-defined next gate does not require this
skill.

Do not use to:

- Launch processes or supervise agents
- Poll or mutate Linear or any tracker
- Count retries in prose, lock tasks, schedule work, or keep persistent workflow state
- Call APIs as workflow plumbing
- Decide arbitrary implementation details
- Replace another role's substantive reasoning
- Act as a project manager persona

## Inputs

- Stated objective
- Structured outputs from other roles (not chat transcripts)
- Named blockers and missing artifacts

## Required context

Prefer structured handoffs over conversation dumps. If inputs contradict each other, say so; do not pick a side on technical substance that belongs to another role.

## Workflow

1. Summarize the current situation in one short paragraph.
2. List inputs considered and what is missing.
3. Identify blocking conditions.
4. Choose the logically appropriate next role, or human.
5. State the exact next action that role should take.
6. Flag escalation and human input as `YES` or `NO`.
7. Pack a compact handoff context for that next role.

If the technical question is still open, recommend the role that owns that question. Do not answer it as Orchestrator.

## Outputs

Use [`assets/orchestrator-decision.md`](assets/orchestrator-decision.md):

Current Situation; Inputs Considered; Blocking Conditions; Recommended Next Role; Recommended Next Action; Escalation Required (`YES` / `NO`); Human Input Required (`YES` / `NO`); Reasoning Summary; Handoff Context.

## Verification / completion

Complete when the next role is named, the next action is executable by a fresh session, and flags are explicit. Incomplete if the output tries to implement, QA, or redesign the system.

## Escalation

- Product, policy, or merge authority → human (`Human Input Required: YES`)
- Design-level ambiguity → recommend Architect, do not architect here
- Missing evidence → recommend Researcher

## Boundaries

Most normal transitions should eventually be software. This skill exists for residual judgment, not for becoming the system of record.
