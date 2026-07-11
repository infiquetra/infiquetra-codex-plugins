# Codex Operator-Choice Framework

**Status:** U5 canonical workflow boundary; installed cutover remains gated by U8.

Do not use one backend menu to describe unrelated Codex capabilities. A feature flag, installed
file, requested model, or caller boolean is not proof that a workflow or child executed.

## Capability Dimensions

| Dimension | Current choices | Meaning |
|---|---|---|
| Lifecycle and state | `saga` | Saga owns durable lifecycle, outcome state, routing, and handoff receipts. |
| Continuation | `turn`; explicit `goal` | The current task is the default. Goal is opt-in long-running continuation and requires a stable tool result before binding. |
| Workflow mode | `inline`; `manual`; `verified-workflow`; legacy-readable `team-execution` | A root-owned method for steps, roles, gates, and receipts. Claude Workflow is unsupported. |
| Step vehicle | `inline`; `deterministic-tool`; `generic-subagent`; runtime-selected `named-profile-subagent` | How one workflow step actually runs. A subagent is a vehicle, not a Saga backend. |
| Role identity | `generic`; `named-profile-selected`; planned-unproved `logical-role-attested` | Whether evidence proves only a child, a selected profile, or the complete logical role/lens binding. |
| Execution-class control | prompt steering is advisory; V2 `agent_type` selects custom-agent TOML; direct model/effort overrides are not workflow policy | Model, effort, sandbox, instructions, and tool policy belong to a reusable profile; effectiveness still needs child readback. |
| Hooks | observe and bounded persistence are implemented; guarding is deferred | Hooks extend events. They are not workflow modes, continuation modes, or leaf executors. |

The canonical live snapshot is
`../../../docs/validation/codex-runtime-capability-snapshot.json`. Historical classifications are
evidence only.

## Model, Effort, And Profile Truth

Current custom-agent files configure `model`, `model_reasoning_effort`, `sandbox_mode`, and bounded
instructions. Sol/Terra MultiAgent V2 exposes named selection only after effective configuration
sets `hide_spawn_agent_metadata=false` and moves the expanded schema to the non-reserved
`tool_namespace="agents"`. A fresh task can then dispatch `agent_type=<runtime_agent_name>` with
`fork_turns="none"` or a positive bounded turn count. Omitted or `all` inherits the parent agent
type, model, and effort and therefore cannot select a different profile.

Therefore:

- a prompt or `task_name` may request a class but cannot attest selection;
- an installed TOML proves configuration bytes, not that a child used the profile;
- generic subagent output remains generic evidence;
- profile selection requires the parent launch plus matching host-issued child role/model/effort
  readback;
- current V2 reapplies the parent permission profile after role selection, so a profile cannot
  narrow a more-powerful parent; enforce read-only and write-capable work through separate
  permission-homogeneous parent tasks and verify effective permission independently;
- gate-authoritative named workflow evidence additionally requires a receipt joining logical role,
  selected profile, active hook-reported model, installed-profile digest, child identity, and result
  vehicle;
- hook model readback does not prove reasoning effort. The exact profile digest binds expected effort.

Ultra is a root orchestration control because it adds automatic delegation. It is not the next leaf
effort above `max` and cannot satisfy a workflow role by itself.

## Current Recommendation

`plugins/saga/scripts/lifecycle_state.py recommend-backend` returns canonical `inline`, `manual`, or
`verified-workflow`. Treat that result as a workflow recommendation, not capability attestation. It
must not activate source Workflow, fork, Goal, hooks, or a subagent as an executor solely from
caller-supplied booleans.

Use `inline` when the root can safely own the work. Use `manual` when automation is unsafe or
unavailable. Existing `team-execution` values remain readable but cannot authorize a new run. A new
`verified-workflow` run requires canonical readiness plus matching runtime evidence; U8 still owns
installed cutover. The U4 fresh-task proof establishes named profile selection only; it does not grant
an unjoined logical-role result gate authority.

## Transitional Saga State

Saga v1 currently records the effective workflow recommendation in `orchestration_mode`, the
recommendation in `orchestration_recommended`, the operator choice in
`orchestration_operator_choice`, any downgrade in `orchestration_downgrade`, and the receipt pointer
in `orchestration_ref`.

These fields remain parser-compatible through the migration. An explicit operator choice must not be
inferred from the effective mode. A mismatch requires a non-empty downgrade reason. Legacy
`team-execution` and `## Team Structure` receipts remain read-only history; new writes use canonical
workflow, continuation, vehicle, and identity vocabulary only.

## Non-Executors

Source `cc-workflows-ultracode`, fork, Goal, hooks, and generic subagents must never be advertised as
active workflow backends. Goal may bind continuation, hooks may observe events, and subagents may run
steps, but each needs its own typed adapter and evidence. Unsupported choices halt or remain explicit
legacy evidence; they do not silently fall back while claiming the unavailable capability ran.
