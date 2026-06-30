# Doc Review - Team Execution Saga Orchestration Repair Plan

## Review Result Contract

The reviewed plan is implementation-ready after safe in-place fixes.

| field | value |
|-------|-------|
| target path | `docs/plans/2026-06-30-team-execution-saga-orchestration-repair-plan.md` |
| reviewed revision | working tree at `59ef01d` with uncommitted plan edits |
| classification | plan |
| blocked status | not blocked |
| review artifact path | `docs/reviews/2026-06-30-team-execution-saga-orchestration-repair-plan-doc-review.md` |
| linked source | `docs/brainstorms/2026-06-30-team-execution-saga-orchestration-repair-requirements.md` |
| override rationale | none |

## Applied Fixes

Safe fixes were applied directly to the plan because the requirements document and repository evidence supported them.

| fix | evidence | target |
|-----|----------|--------|
| Replaced invented validator role names with roster-backed Team Execution validators and moved repo checks into automation gates. | `plugins/team-execution/skills/team-execution/references/validator-registry.md` lists `security-scanner`, `smoke-tester`, and `scenario-tester`; it does not list `test-runner` or `docs-drift-checker`. | `## Team Structure` |
| Added the `team_execution_readiness.py validate` CLI shape so Saga skill docs can call the same readiness validator outside Python. | The plan already required one shared readiness helper and work/resume skills operate from markdown instructions. | U1 |
| Clarified save-time context derivation and moved resume validation out of implicit `saga.py` inference. | `saga:resume` writes re-entry ticks while carrying lifecycle phase forward, so `saga.py` cannot reliably infer a distinct resume context from existing fields alone. | U2, U4 |
| Reordered work validation to run after restore and before saving the work tick or mutating code. | The receipt invariant must block false executable state before work begins. | U4 |
| Pinned exact outcome ref source fields to `node.evidence["orchestration_ref"]` and alias `node.evidence["team_execution_ref"]`. | `plugins/saga/scripts/outcome_spec.py` defines `evidence` as the open pass-through map for backend-specific details. | U6 |
| Added explicit stale-instruction and serial-fallback regression scenarios. | The source requirements require stale resume and serial fallback coverage. | U4, U7 |

## Readiness Summary

The plan can now drive implementation without the builder inventing missing lifecycle decisions.

It has stable R-IDs, KTDs, a concrete `## Team Structure`, U1-U8 implementation units, repo-relative file paths, per-unit test scenarios, explicit validation commands, and a clear split between Saga lifecycle state and Team Execution role evidence.

## Findings By Priority

All review findings were fixed in place.

| priority | status | finding | resolution |
|----------|--------|---------|------------|
| P1 | fixed | The plan used non-roster validator names, which would make Phase A invent Team Execution roles. | Replaced them with `smoke-tester` and `scenario-tester`, and documented repo checks as automation gates rather than validators. |
| P1 | fixed | Resume readiness context was underspecified because `saga.py` cannot infer a `resume` context from existing lifecycle fields. | Specified save-time derived contexts and required `saga:resume` to call the readiness CLI before its re-entry tick. |
| P1 | fixed | Work validation was ordered after restore or save, leaving room for an invalid work tick before the readiness gate. | Changed work sequencing to validate after restore and before saving the work tick or mutating code. |
| P1 | fixed | Outcome dispatch did not name exact ref source fields, leaving implementers to invent where `orchestration_ref` comes from. | Pinned `node.evidence["orchestration_ref"]` first and `node.evidence["team_execution_ref"]` as the alias. |
| P2 | fixed | The regression list claimed full acceptance-example coverage but omitted explicit serial-fallback and stale-instruction scenarios. | Added direct test scenarios for both cases. |

## Remaining Findings

No unresolved P0, P1, P2, or P3 findings remain.

## Residual Risk

This was a document-readiness review, not implementation. The remaining risk is normal execution risk: the future code changes still need the focused pytest set, plugin validation, and full pytest run named in U8 before PR-ready.
