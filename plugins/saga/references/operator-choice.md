# Operator-Choice Framework

**Status:** Codex port contract
**Companion:** [`saga-spec.md`](./saga-spec.md)

Saga chooses how work should proceed; it does not execute another plugin's
private API. The operator/model invokes the selected skill, and the receiving
plugin owns its own state, confirmation, validation, and proof boundary.

## Backends

Codex Saga exposes exactly two execution choices:

| Backend | Use When | Owner |
|---|---|---|
| `inline` | The current Codex thread can safely perform the work directly. | Saga caller |
| `team-execution` | The work needs reviewer consensus, validators, broad fan-out, cross-repo coordination, security/infra scrutiny, or deployment-sensitive gates. | `team-execution` |

The source workflow fan-out backend is lineage only and is not executable in this
Codex plugin.

## Recommendation Rule

Recommend `team-execution` when any of these are true:

- `file_count >= 8`
- `phase_count >= 4`
- security-sensitive work
- infrastructure-sensitive work
- cross-repository work
- deployment-sensitive work
- explicit consensus or validator-gate need
- broad independent fan-out

Otherwise recommend `inline`.

Always present the recommendation as a choice. If the question can be answered
through Codex's structured input UI, use it; otherwise ask directly in chat with
the recommended option first.

## Recording

Store the chosen value in the saga envelope as `orchestration_mode`.

Allowed values:

- `inline`
- `team-execution`

`orchestration_ref` is empty for `inline`. For `team-execution`, it may point to
the plan's `## Team Structure` section or the team-execution state/evidence
root. Saga records the pointer; team-execution owns the run.

## Boundaries

- Saga may emit a handoff envelope or recommend a namespaced skill.
- Saga must not import or call private implementation surfaces from
  `deploy`, `mission-control`, or `team-execution`.
- Subagents or delegated outputs cannot authorize mutation.
- Receiving plugins must re-read and re-verify handoff content before mutation.
