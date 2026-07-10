# Codex Operator-Choice Framework

**Status:** U1 runtime characterization and migration contract.

Do not use one backend menu to describe unrelated Codex capabilities. A feature flag, installed
file, requested model, or caller boolean is not proof that a workflow or child executed.

## Capability Dimensions

| Dimension | Current choices | Meaning |
|---|---|---|
| Lifecycle and state | `saga` | Saga owns durable lifecycle, outcome state, routing, and handoff receipts. |
| Continuation | `turn`; explicit `goal` | The current task is the default. Goal is opt-in long-running continuation and requires a stable tool result before binding. |
| Workflow mode | `inline`; `manual`; legacy-current `team-execution`; planned-unproved `verified-workflow` | A root-owned method for steps, roles, gates, and receipts. Claude Workflow is unsupported. |
| Step vehicle | `inline`; `deterministic-tool`; `generic-subagent`; planned-unproved `named-profile-subagent` | How one workflow step actually runs. A subagent is a vehicle, not a Saga backend. |
| Role identity | `generic`; planned-unproved `logical-role-attested` | Whether evidence proves a selected logical role/lens rather than only a child task. |
| Execution-class control | prompt steering is advisory; custom-agent TOML is configurable; per-spawn override is unavailable | Model, effort, sandbox, and tool policy belong to a reusable profile, but effectiveness still needs readback. |
| Hooks | observe is configurable; persistence is planned; guarding is deferred | Hooks extend events. They are not workflow modes, continuation modes, or leaf executors. |

The canonical live snapshot is
`../../../docs/validation/codex-runtime-capability-snapshot.json`. Historical classifications are
evidence only.

## Model, Effort, And Profile Truth

Current custom-agent files may configure `model`, `model_reasoning_effort`, and `sandbox_mode`. The
direct spawn interface available to this repository accepts only `task_name`, `message`, and
`fork_turns`; it does not expose per-child profile, model, effort, or sandbox selection and returns
no such readback.

Therefore:

- a prompt may request a class but cannot attest the selected model or effort;
- an installed TOML proves configuration bytes, not that a child used the profile;
- generic subagent output remains generic evidence;
- named workflow evidence requires a later receipt joining logical role, selected profile, active
  hook-reported model, installed-profile digest, child identity, and result vehicle;
- hook model readback does not prove reasoning effort. The exact profile digest binds expected effort.

Ultra is a root orchestration control because it adds automatic delegation. It is not the next leaf
effort above `max` and cannot satisfy a workflow role by itself.

## Current Transitional Recommendation

Until U5 lands the canonical workflow vocabulary, the existing
`plugins/saga/scripts/lifecycle_state.py recommend-backend` helper continues to return the accepted v1
values `inline`, `manual`, or legacy `team-execution`. Treat that result as a workflow recommendation,
not a capability attestation. It must not activate source Workflow, fork, Goal, hooks, or a subagent
as an executor solely from caller-supplied booleans.

Use `inline` when the root can safely own the work. Use `manual` when automation is unsafe or
unavailable. Existing `team-execution` values remain readable during migration, but new
`verified-workflow` claims stay planned-unproved until the package, runtime receipt, and cutover gates
land.

## Transitional Saga State

Saga v1 currently records the effective workflow recommendation in `orchestration_mode`, the
recommendation in `orchestration_recommended`, the operator choice in
`orchestration_operator_choice`, any downgrade in `orchestration_downgrade`, and the receipt pointer
in `orchestration_ref`.

These fields remain parser-compatible through the migration. An explicit operator choice must not be
inferred from the effective mode. A mismatch requires a non-empty downgrade reason. Legacy
`team-execution` and `## Team Structure` receipts remain read-only history; U5 introduces canonical
workflow, continuation, vehicle, and identity fields and emits only new vocabulary.

## Non-Executors

Source `cc-workflows-ultracode`, fork, Goal, hooks, and generic subagents must never be advertised as
active workflow backends. Goal may bind continuation, hooks may observe events, and subagents may run
steps, but each needs its own typed adapter and evidence. Unsupported choices halt or remain explicit
legacy evidence; they do not silently fall back while claiming the unavailable capability ran.
