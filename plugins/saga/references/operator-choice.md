# Operator-Choice Framework

**Status:** Codex port contract.

Codex Saga exposes exactly three execution choices:

| Backend | Use when | Owner |
|---|---|---|
| `inline` | Current Codex thread can safely perform the work directly. | Saga caller |
| `manual` | Automation is unsafe or unavailable; produce receipts and operator handoff. | Operator |
| `team-execution` | Work needs reviewer consensus, validators, broad fan-out, cross-repo coordination, security/infra scrutiny, adversarial confidence, or deployment-sensitive gates. | `team-execution` |

Source Workflow (`cc-workflows-ultracode`), fork, goal, and hook backends are lineage-only in this Codex plugin. They may appear in provenance, tests, or degradation receipts, but they are not active choices unless a future Codex capability proof and negative fallback tests land.

## Recommendation Rule

Recommend `team-execution` when any signal is true:

- file count is at least 8
- phase count is at least 4
- security, infra, deployment-sensitive, cross-repo, consensus, broad fan-out, or adversarial-confidence signal exists

Recommend `manual` when the next safe action is a proposal or operator handoff rather than an automated dispatch.

Otherwise recommend `inline`.

`plugins/saga/scripts/lifecycle_state.py recommend-backend` is the runnable helper. It reports unsupported source backends explicitly with `source_workflow_excluded=true`.

## State Fields

Saga records the effective backend in `orchestration_mode`, the recommendation in `orchestration_recommended`, the operator pick in `orchestration_operator_choice`, and any capability downgrade in `orchestration_downgrade`.

`orchestration_ref` stays empty for `inline` and `manual`. For `team-execution`, it may point at a `## Team Structure` section or team-execution evidence root. Saga records the pointer; team-execution owns the run.
