---
date: 2026-06-29
target: docs/brainstorms/2026-06-29-codex-saga-orchestration-requirements.md
reviewed_revision: working tree
blocked: false
---

# Codex Saga Orchestration Requirements Doc Review

## Readiness Summary

Ready to drive `/plan` after one in-place readiness fix. The original requirements correctly rejected Claude-only active surfaces, but it did not sufficiently require a positive Codex harness inventory; that would have let a planner treat Codex as "Claude minus unavailable primitives" instead of a distinct implementation harness.

No P0 or P1 findings remain after the safe fix.

## Applied Fixes

| Priority | Status | Fix |
|---|---|---|
| P1 | fixed | Added a key decision and R42-R47 requiring a Codex-vs-Claude harness delta table, explicit mapping of Claude primitives, explicit mapping of Codex-only affordances, mutation approval boundaries, and negative/capability-gate tests for inactive Claude primitives. |
| P1 | fixed | Added acceptance examples AE8-AE10 to prove lift-and-shift blocking, deliberate use/defer/reject of Codex-only affordances, and operator-gated mutation behavior. |
| P2 | fixed | Added success/scope/outstanding-question language requiring Codex-only harness affordances to be used, deferred, or rejected intentionally. |

## Remaining Findings

| Priority | Status | Finding | Impact |
|---|---|---|---|
| None | closed | No remaining readiness findings. | `/plan` can use the document without inventing the Codex-vs-Claude harness boundary. |

## Residual Risk

The implementation plan must still refresh live refs before building. The document names current evidence (`Codex fce697c`, `Claude b30e0f2`) but already requires refresh if either repo advances.

Formal SDLC rubric review was not run because this target is a single brainstorm requirements document, not a blueprint/ADR, issue-derived artifact, or spec owned by `/spec`.
