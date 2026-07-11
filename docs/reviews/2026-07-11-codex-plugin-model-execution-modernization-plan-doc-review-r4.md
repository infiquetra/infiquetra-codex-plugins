# Doc Review Round 4: Codex Plugin Model, Execution, and Upstream Modernization Plan

The U4 inline/workflow-handoff amendment is ready to drive implementation after five findings were fixed in place.

## Applied Fixes

Every actionable P0-P3 finding from this amendment review is resolved.

| ID | Priority | Status | Finding | Applied fix |
|---|---|---|---|---|
| DR4-01 | P1 | FIXED | The amendment moved prepared normalization-transaction recovery to U8 while U4C still promised crash-safe normalized replay and consumption markers. A crash between normalized persistence and the committed marker could strand valid U4 evidence until cutover. | Kept exact-readback recovery of prepared normalization transactions in U4C; U8 now owns only raw abandonment, digest-bound prune, and verified deletion. |
| DR4-02 | P1 | FIXED | The U5-U8 table assigned `test-medium` as a general implementation worker, but `role-registry.yaml` contains exactly 25 reviewer, scanner, tester, and monitor roles and no general implementer lens. Following the table would invent an unregistered role or misuse a tester to write product code. | Made the root the sole product-source writer and assigned exact registered logical roles and execution classes for review, scanning, testing, and monitoring. Registered testers may write only declared test/fixture paths consistent with their lens. |
| DR4-03 | P2 | FIXED | U4E did not say which component performs native named-profile selection and could be read as authorizing `prove_verified_workflows_runtime.py` to spawn a child. | Required the root to inspect and invoke the host-native selector when exposed; the proof script only validates supplied launch/result evidence and records `diagnostic` when the selector is absent. |
| DR4-04 | P2 | FIXED | The mandatory pause required a durable `## Workflow Structure` but did not name its exact artifact location or Saga handoff pointer. | Required the root to append the structure to the existing plan at `#workflow-structure`, record that path/anchor in the Saga handoff, and pause before U5. |
| DR4-05 | P1 | FIXED | The existing U4 draft advanced the canonical port runbook from v1 to v2, but U4 did not claim the runbook, contract-version check, authority digests, generated classification, legacy-token inventory, or their tests. Current validation therefore reported an unexplained runbook-version and digest mismatch. | Added the runbook v2 transaction to U4E, including the supported-version check, exact authority refresh, generated classification, legacy inventory, failure cases, tests, and byte-current verification gate. |

## Readiness Summary

PASS: the amended plan can drive U4A-U4E inline without deleting U4 functionality, inventing an execution role, or confusing hook-data maintenance with named-profile proof.

The reviewed control flow is explicit:

```text
root completes U4A-U4E inline
             |
   focused checks + commits
             |
 integrated U4 verification
             |
 append ## Workflow Structure
             |
      operator pause
             |
 named selector + attestation?
       |                 |
      yes                no
       |                 |
 U5-U8 named roles    remain paused
```

## Review-Result Contract

The durable verdict supersedes round three only for the 2026-07-11 amendment.

- Target: `docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`
- Reviewed revision: working tree at repository `HEAD` `a64ea3efc9793f8f253d09be4f45b8d190443706`; reviewed plan blob `c7ded816db930db5e667df0fc4fa34bef63d973a`
- Blocked status: NOT BLOCKED by document findings; operator approval remains required before U4A resumes
- Classification: implementation plan
- Review type: readiness-skeptic plus model-selection, receipt-integrity, security, operations, migration, release, and deployment/cutover scrutiny
- Formal rubric phase: none; plan artifacts do not map to the idea, issue, or spec rubric phases
- Linked origin: `docs/plans/2026-06-27-port-recent-claude-plugin-updates.md`
- Linked Saga: `task-port-recent-claude-plugin-updates`
- Prior review: round three remains the settled full-plan review and is superseded only where this amendment changed U4 and the execution strategy
- Review artifact: `docs/reviews/2026-07-11-codex-plugin-model-execution-modernization-plan-doc-review-r4.md`
- External review panel: not requested; skipped
- Operator override: none

## Verification Evidence

The review checked the amendment against live repository and runtime evidence.

- `plugins/verified-workflows/scripts/dispatch_receipt.py` is 6,440 lines. Its prepared/committed consumption-marker protocol and `recover_normalization_commit` prove that transaction recovery belongs with U4 normalized persistence, while abandonment, prune, and raw-pair deletion are separable maintenance operations.
- `plugins/verified-workflows/config/role-registry.yaml` defines exactly 25 logical roles and no general implementation-worker role. Base reviewers are `devils-advocate-reviewer`, `security-reviewer`, and `architecture-reviewer`; the amended U5-U8 table now uses registered conditional tester, scanner, and monitor roles.
- The current collaboration spawn schema exposes `task_name`, `message`, and `fork_turns`, but no named profile, model, effort, sandbox selector, or selection readback. U4E therefore has an executable `attested|diagnostic|inline-only|auth-unavailable` outcome instead of an assumed success path.
- Requirements R21-R22 map to U4, the U4A-U4E subunits retain stable U-IDs, new feature-bearing modules have named test paths, and the U5-U8 workflow handoff has a durable target anchor and stop rule.
- The existing U4 draft intentionally changes the canonical runbook to v2. The amended plan now claims the corresponding `port_contract.py`, manifest/classification, legacy-inventory, and test updates instead of leaving that contract change outside every implementation unit.
- `git diff --check` passed for the amended plan, decision journal, and prior-review supersession marker.
- `PYTHONPATH=. uv run pytest -q tests/test_saga_doc_formatting.py`: 29 passed.
- The broader document/package check currently reports 79 passed and 3 failed because the in-progress U4 draft has not yet updated the runbook-version validator or refreshed plan/review/legacy-inventory digests. DR4-05 makes those exact failures U4E acceptance work; they are not treated as passing evidence.

## Remaining Findings by Priority

No P0, P1, P2, or P3 finding remains after the safe fixes.

## Review Artifact Path

Round four is the current readiness verdict for the amended execution sequence.

`docs/reviews/2026-07-11-codex-plugin-model-execution-modernization-plan-doc-review-r4.md`

## Residual Risk / Limited Evidence

The remaining risks are implementation and runtime gates rather than missing plan decisions.

- This session cannot currently select a named custom profile through its spawn schema. U4 can still finish with a truthful `diagnostic` result, but the model-pinned U5-U8 workflow must remain paused unless the runtime boundary changes or the operator explicitly accepts a less precise fallback.
- U4 is already a large uncommitted working-tree change spanning the future U4A-U4E boundaries. `/work` must inventory ownership and split the existing behavior into the planned atomic commits without discarding or falsely reclassifying current work.
- The module extraction is review-ready, not executed. U4B must prove the `dispatch_receipt.py` compatibility facade and all public receipt references remain stable before later modules or callers move.
- Current repository validation remains red on the known U4 runbook-version and authority/inventory digest work. U4E must make those checks green before the U4 unit-stage gate or pause handoff can pass.
- Real plugin installation, hook trust, isolated authentication, marketplace cutover, raw maintenance, rollback, PR, and merge remain later implementation gates.
