# Codex Operator-Choice Framework

Do not use one backend label to describe unrelated Codex capabilities. A feature flag, installed
file, requested model, or caller boolean is not proof that a workflow or child executed.

## Capability Dimensions

| Dimension | Current choices | Meaning |
|---|---|---|
| Lifecycle and state | `saga` | Saga owns durable lifecycle, outcome state, routing, and handoff pointers. |
| Continuation | `turn`; explicit `goal` | The current turn is default; Goal is opt-in long-running continuation. |
| Workflow mode | `inline`; `manual`; `verified-workflow`; legacy-readable `team-execution` | Root-owned method for steps, roles, checks, and gates. |
| Step vehicle | `inline`; `deterministic-tool`; `named-profile-subagent`; approved external action | How one bounded assignment runs. |
| Role identity | `generic`; `named-profile-selected`; `logical-role-validated` | The level of identity established by V2 readback plus validated role/result contracts. |
| Execution-class control | exact V2 profile, model, effort, and bounded `fork_turns` | Profile selection is provisional until runtime readback agrees. |
| Hooks | none in active workflow execution | Historical hook events are not current identity, state, or gate evidence. |
| External action | Saga registry route | Provider output is approval-bound, contained, root-adjudicated, and non-gating. |

The digest-bound capability snapshot at
`../../../docs/validation/codex-runtime-capability-snapshot.json` records the accepted Codex 0.146.0
contract and preserves native `multi_agent_version` metadata. Current runtime truth still comes from
the active launch schema and combined `session_meta` plus `turn_context` readback.

## Native Questions And Agent Roles

Use `request_user_input` only when it is listed and allowed in the current mode. Otherwise ask one
concise blocking question in the normal response and stop. Never search for a core interaction tool.
In a channel session, inline the choices in the reply. Keep one decision per question, preselect a
recommendation when the workflow calls for one, preserve free-form input, and never silently skip a
required choice.

Subagents remain explicit-only. Never auto-spawn. When the operator and current repository
instructions authorize delegation, use `explorer` for read-only discovery, `worker` for
implementation, and `default` when neither specialization fits. The selected agent still receives
one bounded assignment, write ownership when applicable, and a required result contract.

## Model, Effort, Profile, And Permission Truth

Current profiles configure `model`, `model_reasoning_effort`, and bounded instructions. A V2 launch
selects the exact underscore-form profile and an approved history bound.
Therefore:

- prompts, task labels, and TOML bytes express requested configuration only;
- selected profile, model, effort, provider, permission, and V2 mode require matching runtime
  readback on the canonical agent path;
- child self-report and coordination messages never establish runtime identity;
- Codex 0.146.0 children inherit the parent turn's effective permission profile, so a profile cannot
  independently widen or narrow it;
- a logical role becomes gate-capable only after its role lens, selected profile, runtime identity,
  typed result, workspace audit, and root decision all validate;
- Ultra is a root-only orchestration control, not a child effort tier.

Missing or mismatched readback fails visibly. Do not fall back to another agent mode while claiming
that the approved profile ran.

Inherited permission is the reason a plugin-side capability declaration proves nothing. It is not a
reason to withhold approved work from a child. Scope comes from the operator-approved plan and
contract, and readback reports the permission that actually applied.

## Current Recommendation

`plugins/saga/scripts/lifecycle_state.py recommend-backend` returns `inline`, `manual`, or
`verified-workflow`. Treat that result as a workflow recommendation, not capability attestation.

Use `inline` when the root can safely own the work. Use `manual` when automation is unsafe or
unavailable. A `verified-workflow` run requires an approved three-table contract, successful
`verified-workflows:review-workflow` review, and matching V2 runtime evidence. Existing
`team-execution` values remain readable history and cannot authorize a new run.

## Transitional Saga State

Saga records the effective choice in `orchestration_mode`, its recommendation in
`orchestration_recommended`, the operator choice in `orchestration_operator_choice`, any explicit
downgrade in `orchestration_downgrade`, and the concise run-record pointer in `orchestration_ref`.
An operator choice must not be inferred from the effective mode. A mismatch requires a non-empty
downgrade reason.

## Non-Executors

Goal continuation, messages, waits, profile files, capability snapshots, and external provider
responses are not workflow engines or gate decisions. They may contribute bounded state or evidence,
but the main Codex session remains the sole orchestrator and final authority.
