---
date: 2026-07-11
target: docs/brainstorms/2026-07-11-codex-external-advisory-execution-contract-requirements.md
reviewed_revision: working tree
blocked: false
review_type: requirements-readiness
---

# Codex External Advisory Execution Contract Requirements Review

## Applied Fixes

The requirements now fail closed at the approval, egress, receipt, replay, and promotion-measurement boundaries.

| priority | status | finding | applied fix |
|---|---|---|---|
| P1 | resolved | Approval covered route identity but was not bound to outbound context, sensitivity, or the patch write set. | Expanded the action and approval contracts and made material egress-contract changes invalidate approval. |
| P1 | resolved | Attended approval was specified, but unattended and resumed launch authority was ambiguous. | Required a persisted run-specific approval for the unchanged bundle and made legacy preferences unapproved intent only. |
| P1 | resolved | Receipt and success language claimed stronger remote provider and model proof than an HTTP adapter can establish. | Limited claims to configured-route, supervised-invocation, attestation, and observed-response evidence within the adapter trust model. |
| P2 | resolved | Terminal state vocabulary omitted timeout, interruption, and cancellation despite acceptance flows using those outcomes. | Added the missing outcomes to the state and operator-summary contracts. |
| P2 | resolved | Claim-store failure could leave replay behavior undefined. | Required unavailable claim or status persistence to fail closed without blind redispatch. |
| P2 | resolved | Direct-mutation evidence used undefined qualification, rewrite, and rollback terms. | Required versioned definitions before the first qualifying run and prohibited retroactive changes within an evidence window. |
| P2 | resolved | Continuation without a required action lacked a durable override rationale. | Required the operator decision and rationale in the action status card. |

## Readiness Summary

The document is ready to drive `/plan`; no unresolved P0 or P1 finding remains.

The scope, authority boundary, provider classes, approval model, containment ceiling, failure policy, live proof matrix, and deferred capability-promotion gate are sufficiently explicit for a planner to choose implementation mechanics without inventing product behavior.

## Remaining Findings by Priority

No findings remain after the evidence-backed fixes.

| priority | status | finding |
|---|---|---|
| None | closed | No unresolved readiness finding remains. |

## Review Result Contract

The review is unblocked and the requirements may proceed to planning.

| field | value |
|---|---|
| target path | `docs/brainstorms/2026-07-11-codex-external-advisory-execution-contract-requirements.md` |
| reviewed revision | working tree |
| blocked | false |
| finding priorities and statuses | 3 P1 resolved; 4 P2 resolved; none remaining |
| applied fixes | approval and egress binding; unattended and legacy-preference semantics; receipt claim limits; terminal states; replay fail-closed behavior; promotion metric definitions; override rationale |
| review artifact path | `docs/reviews/2026-07-11-codex-external-advisory-execution-contract-requirements-review.md` |
| override rationale | none |
| linked investigation | `docs/investigations/external-second-opinion-preference-noop-2026-07-11.md` |

## Residual Risk

The review used repository documents and source inspection rather than a working external dispatch, because the current Codex production path does not consume the saved second-opinion preference. Live Claude CLI, `agy`, and Ollama Cloud proof remains a release requirement, not evidence available at requirements-review time.
