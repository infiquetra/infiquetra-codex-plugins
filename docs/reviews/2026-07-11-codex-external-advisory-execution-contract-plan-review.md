---
date: 2026-07-11
target: docs/plans/2026-07-11-codex-external-advisory-execution-contract-plan.md
reviewed_revision: working tree
blocked: false
review_type: plan-readiness
---

# Codex External Advisory Execution Contract Plan Review

## Applied Fixes

The plan now binds every implementation and review boundary needed for `/work` to start without inventing architecture or workflow behavior.

| priority | status | finding | applied fix |
|---|---|---|---|
| P1 | resolved | The Workflow Structure was a descriptive six-column table rather than the exact machine-checked contract, used unregistered builder roles, and assigned mutation ownership to evidence-only agent lenses. | Replaced it with the canonical 18-column table, root-owned U1-U8 steps, registered role IDs, current lens/profile/model/effort bindings, all base reviewers, two required validators, a barrier, and a no-mutation final gate. |
| P1 | resolved | Credential scanning was required but had no owned implementation or test file. | Added `external_action_egress.py`, its focused test file, and dispatch-before-adapter behavior and scenarios to U3. |
| P1 | resolved | Origin requirements were grouped, but the supplied flows and acceptance examples were not mapped into the implementation checklist. | Added flow and acceptance traceability for every plan requirement. |
| P2 | resolved | Action-store, policy, and overlay locations and precedence were not exact enough for independent implementers. | Pinned the Git-common action layout, machine-local policy and overlay paths, policy precedence, additive overlay composition, and duplicate-key halt behavior. |
| P2 | resolved | Lifecycle states were named but the legal transition and requiredness behavior was not explicit. | Added a closed action-lifecycle transition table and immutable override semantics. |
| P2 | resolved | Disposable-clone behavior did not say whether dirty and untracked bytes enter the provider workspace. | Pinned committed `HEAD`, excluded dirty/untracked bytes, and required preview and approval of write-set overlap risk. |
| P2 | resolved | The plan claimed a signed release artifact without defining a signing mechanism. | Replaced the claim with schema-valid, content-addressed evidence supported by existing repository patterns. |

## Readiness Summary

The plan is ready for `/work`; no unresolved P0 or P1 finding remains.

The implementation units, origin mappings, state model, provider boundaries, failure modes, file ownership, test scenarios, workflow roles, validators, and release gates are sufficiently closed for an unfamiliar implementer.

## Remaining Findings by Priority

No findings remain after the evidence-backed fixes.

| priority | status | finding |
|---|---|---|
| None | closed | No unresolved readiness finding remains. |

## Review Result Contract

The review is unblocked and the plan may proceed to execution.

| field | value |
|---|---|
| target path | `docs/plans/2026-07-11-codex-external-advisory-execution-contract-plan.md` |
| reviewed revision | working tree |
| blocked | false |
| finding priorities and statuses | 3 P1 resolved; 4 P2 resolved; none remaining |
| applied fixes | workflow contract; root ownership; origin mapping; egress ownership; store/policy/overlay paths; state transitions; dirty-base behavior; release evidence wording |
| review artifact path | `docs/reviews/2026-07-11-codex-external-advisory-execution-contract-plan-review.md` |
| override rationale | none |
| linked requirements review | `docs/reviews/2026-07-11-codex-external-advisory-execution-contract-requirements-review.md` |
| linked Saga | `task-codex-external-advisory-execution-contract` |

## Residual Risk

The table binds committed role and profile digests; production execution must rebind against installed profile bytes and halt on drift. Real Claude CLI, `agy`, Ollama Cloud, isolated-install, fresh-session, and rollback evidence remain U8 implementation gates rather than proof available during document review.
