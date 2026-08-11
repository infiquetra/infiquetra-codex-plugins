# Code Review — Issue #63 Port Manifest Reconciliation Through U2

The `infiquetra-codex-plugins` branch implements most of the issue #63 contract through Unit U2, but five P1 contract defects block Unit U3.

## Review-result contract

| Field | Value |
|---|---|
| Target | `fix/issue-63-port-manifest-reconciliation`; reviewed plan commit `9f4c8d41fb14ed098bd6a7dab9f0f3f9d06c8653..ae0e4f9fcb11e9490f0a87931f82e6e85f2e7f65` |
| Reviewed revision | `ae0e4f9fcb11e9490f0a87931f82e6e85f2e7f65` |
| Linked issue | `infiquetra/infiquetra-codex-plugins#63` |
| Plan | `docs/plans/2026-08-10-issue-63-port-manifest-reconciliation-plan.md` |
| Document reviews | `docs/reviews/2026-08-10-issue-63-port-manifest-reconciliation-doc-review.md`; `docs/reviews/2026-08-11-issue-63-port-manifest-reconciliation-plan-re-review.md` |
| Work session | `docs/work-sessions/2026-08-11-issue-63-port-manifest-reconciliation-u2.md` |
| Review mode | Inline independent Saga code review; no subagents or external harness |
| Blocked | `true` |
| U3 blocked | `true` — findings #1 through #5 must be fixed and independently re-reviewed before U3 starts |

## Findings

### P0

No P0 finding.

### P1

| # | File | Issue | Reviewer | Confidence | Route |
|---|---|---|---|---|---|
| 1 | `docs/validation/codex-runtime-capability-snapshot.json:2` | U1b overwrites the shared Codex 0.147 authority snapshot | correctness + testing + API-contract | 100 | `gated_auto -> human` |
| 2 | `scripts/port_contract.py:288` | Tracked runtime surfaces escape behavior reconciliation | correctness + adversarial + testing | 100 | `gated_auto -> review-fixer` |
| 3 | `scripts/port_contract.py:1192` | Finalized version-2 contracts still depend on live authority files | correctness + reliability + API-contract | 100 | `gated_auto -> review-fixer` |
| 4 | `scripts/port_contract.py:1220` | Finalized state accepts empty and later-mutable evidence | correctness + reliability + testing | 100 | `gated_auto -> review-fixer` |
| 5 | `scripts/port_contract.py:1345` | Version-2 source and execution authority can move | correctness + adversarial + API-contract | 100 | `gated_auto -> review-fixer` |

### P2

| # | File | Issue | Reviewer | Confidence | Route |
|---|---|---|---|---|---|
| 6 | `tests/test_port_contract.py:687` | Tests do not exercise the integrated finalized evidence path | testing + reliability | 100 | `safe_auto -> review-fixer` |

### P3

| # | File | Issue | Reviewer | Confidence | Route |
|---|---|---|---|---|---|
| 7 | `scripts/port_contract.py:259` | Bootstrap commit mixes contract work with broad formatter churn | maintainability/conventions | 100 | `safe_auto -> review-fixer` |

## Finding details

### #1 — U1b overwrites the shared Codex 0.147 authority snapshot

- **Why it matters:** The shared snapshot now carries issue #63 Git refs, while the still-current Codex 0.147 manifest, tests, and runtime proof require the accepted Codex 0.147 bytes. Three focused Codex 0.147 tests fail, and the overwrite also makes five tests in the six-test validator group observe a stale runtime proof. These are current defects, not planned U3 regeneration work.
- **Evidence:** `docs/validation/codex-runtime-capability-snapshot.json:2-15` changes the capture and all Codex/Claude refs to issue #63. `docs/portability/ports/2026-08-08-codex-0147-alignment.json:3-8` and `docs/validation/verified-workflows-runtime-proof.json:1` both bind `a9576e...`, which is exactly the SHA-256 digest of the pre-U1b snapshot at commit `3f7c7a5`; the current shared snapshot is `2901bc4...`. The proof's recorded harness digest `a3a8ed5...` exactly matches the current harness. Regenerating the proof against the overwritten snapshot changes only `snapshot_sha256`.
- **Suggested fix:** Restore the shared snapshot to its Codex 0.147 bytes and give issue #63 one cycle-specific capability-snapshot file using the same schema-r4 format. Amend the plan's U1 authority file list, then rebind only the issue #63 manifest and classification to that dedicated artifact. Preserve `docs/validation/verified-workflows-runtime-proof.json` unchanged: restoring the shared snapshot makes its existing snapshot and harness bindings current again. Do not rewrite the Codex 0.147 manifest, tests, or runtime proof to describe issue #63.
- **Metadata:** `pre_existing=false`; `requires_verification=true`.

### #2 — Tracked runtime surfaces escape behavior reconciliation

- **Why it matters:** The new gate can stay green while current installed behavior changes outside its narrow plugin-directory allowlist. Live issue #63 acceptance criterion 1 requires every behavior-bearing changed path to be classified exactly once; this is not limited to Python entry points or future files.
- **Evidence:** `scripts/port_contract.py:302-306` selects only plugin manifests and top-level `scripts`, `skills`, `hooks`, `config`, and `roles`. It therefore returns false for all of these current tracked behavior surfaces:
  - generated profiles such as `plugins/verified-workflows/agents/work_high.toml`, although `scripts/validate_codex_plugins.py:1160-1165` treats the `agents` directory as a required runtime surface;
  - top-level plugin reference assets explicitly loaded by installed skills, including `plugins/saga/references/operator-choice.md` from `plugins/saga/skills/code-review/SKILL.md:61` and `plugins/python-toolkit/references/lambda-patterns.md` from `plugins/python-toolkit/skills/python-patterns/SKILL.md:695`;
  - `plugins/hermes-profile-evolution/conformance/profile-change-classifier.v1.json` and `profile-request-cli.v1.json`, which `plugins/hermes-profile-evolution/scripts/profile_request.py:17-19,45-55,75-86,240-246` reads to determine runtime validation and command behavior;
  - `.agents/plugins/marketplace.json`, which declares available local plugins and installation policy and is consumed by repository discovery and active-workflow validation at `scripts/validate_codex_plugins.py:717-745,1393-1428`; and
  - `.codex/config.toml`, which directly sets approval policy, agent depth, and multi-agent feature flags and is the repository's named Codex configuration surface at `scripts/validate_codex_plugins.py:1740-1745`.
  `plugins/hermes-profile-evolution/conformance/provenance.json` is different: the runtime adapter does not read it, and `scripts/validate_codex_plugins.py:1823-1862` uses it only to validate producer provenance. It is not a required behavior-path addition on this evidence. `tests/test_port_contract.py:609-632` has no positive case for any omitted surface.
- **Suggested fix:** Extend `is_behavior_path` only for present repository behavior: top-level plugin `agents`; the current top-level reference roots or exact assets that installed skills load; the two exact Hermes conformance contracts read by `profile_request.py`; and the exact root files `.agents/plugins/marketplace.json` and `.codex/config.toml`. Add positive tests for each category, including the existing rename/delete patterns. Do not treat every directory named `references` as behavior, include unreferenced lineage prose such as the Fleet reference documents on this evidence, or broaden to all documentation, all conformance files, or hypothetical future roots.
- **Metadata:** `pre_existing=false`; `requires_verification=true`.

### #3 — Finalized version-2 contracts still depend on live authority files

- **Why it matters:** A later change to the shared runbook or capability snapshot invalidates a finalized historical cycle even though its reconciliation target is frozen at the immutable evidence tag. That contradicts the plan's requirement that later unrelated `main` changes not invalidate finalized history.
- **Evidence:** `scripts/port_contract.py:1192-1193` treats every schema-version-2 manifest as live authority. `scripts/port_contract.py:1630` applies that result before `scripts/port_contract.py:1663-1724` reads runbook and capability bytes from the current worktree. Only the reconciliation inventory switches to the evidence tag at `scripts/port_contract.py:1220-1225`.
- **Suggested fix:** Keep current-worktree authority checks for active version-2 cycles, but make finalized cycles validate their recorded authority bytes from the frozen evidence candidate, reusing the existing historical-preimage machinery rather than adding a new evidence format.
- **Metadata:** `pre_existing=false`; `requires_verification=true`.

### #4 — Finalized state accepts empty and later-mutable evidence

- **Why it matters:** A version-2 manifest can claim `finalized` with an existing evidence tag and no evidence entries, and a later commit can replace or append evidence without the transition guard objecting. The issue #63 acceptance contract requires finalized source-harness evidence, so this is a fail-open finalization path.
- **Evidence:** `scripts/port_contract.py:1210-1214` requires empty evidence only for active state. The finalized branch at `scripts/port_contract.py:1220-1225` checks only that the tag resolves. `scripts/port_contract.py:1345-1355` freezes the evidence ref and finalized reconciliation fields but never the `evidence` list. A direct function check returned a finalized target with `evidence=[]` and no error.
- **Suggested fix:** Require finalized version-2 manifests to contain evidence, and once a previous manifest is finalized, require its evidence entries to remain byte-equivalent. Add issue #63's expected `repository: "source"` evidence requirement at the cycle level in U3 rather than generalizing the schema to a registry.
- **Metadata:** `pre_existing=false`; `requires_verification=true`.

### #5 — Version-2 source and execution authority can move

- **Why it matters:** An active manifest can replace `codex.execution_base`, source repository identity, or source base/target refs and recompute its rows. Earlier bootstrap behavior can then disappear from reconciliation, or the future source proof can run against a different checkout than the reviewed pin, while transition validation remains green.
- **Evidence:** `scripts/port_contract.py:1345-1359` compares only `codex.evidence_ref`, finalized state/rows, and candidate ancestry. It does not compare the source declaration or Codex historical/execution bases. A direct transition check changing `codex.execution_base` from one full commit value to another returned `[]`. The plan pins the source target in U1b and explicitly says U3 finalizes without changing `codex.execution_base` at `docs/plans/2026-08-10-issue-63-port-manifest-reconciliation-plan.md:152-154`.
- **Suggested fix:** Freeze `source.repository_id`, `source.base_ref`, `source.target_ref`, `codex.repository_id`, `codex.historical_plan_base`, and `codex.execution_base` across version-2 transitions, alongside the existing evidence-ref check. The prospective plan/review rebinding remains allowed because it does not change these repository/ref fields.
- **Metadata:** `pre_existing=false`; `requires_verification=true`.

### #6 — Tests do not exercise the integrated finalized evidence path

- **Why it matters:** The resolver helpers pass their direct tests, but the `validate_manifest` branch that selects a declared source checkout, checks the harness, keeps the artifact Codex-owned, and binds `repo_head` to Codex history has no successful end-to-end test. The lifecycle tests also miss the normal active-to-finalized path and therefore did not catch findings #3 through #5.
- **Evidence:** `tests/test_port_contract.py:687-706` checks key admission while using an invalid active manifest that already contains evidence. `tests/test_port_contract.py:709-874` tests helpers directly. `tests/test_port_contract.py:890-908` checks only evidence-ref replacement and finalized-to-active rejection on partial dictionaries. No test finalizes an isolated manifest, resolves the source evidence through `validate_manifest`, validates the tag-selected inventory, or proves later unrelated `HEAD` stability.
- **Suggested fix:** Add one isolated-repository happy-path test covering active initialization, committed evidence subject, finalized manifest/tag, explicit source checkout, and `validate_manifest`; then mutate each pinned authority and add an unrelated commit to cover the required negative and stability cases.
- **Metadata:** `pre_existing=false`; `requires_verification=true`.

### #7 — Bootstrap commit mixes contract work with broad formatter churn

- **Why it matters:** Commit `3f7c7a5` is materially harder to audit and blame than the contract change requires. The churn also did not establish a maintained formatting gate: Ruff still reports three formatting changes in the later U2 additions to `scripts/port_contract.py`.
- **Evidence:** The commit reports a 799-line production diff and a 245-line test diff. Abstract-syntax comparison found 17 existing production functions and six existing test functions whose syntax trees are identical before and after the commit but whose source formatting changed. Examples include `git_inventory` at `scripts/port_contract.py:259` and the pre-existing inventory test at `tests/test_port_contract.py:40`.
- **Suggested fix:** Before PR review, restore the pre-commit formatting for unchanged definitions and retain formatting changes only where semantic edits require them. If repository-wide Ruff formatting is desired later, make it a separate explicitly reviewed maintenance change.
- **Metadata:** `pre_existing=false`; `requires_verification=true`.

## Built versus planned

**Scope Check: REQUIREMENTS MISSING**

**Intent:** Add a version-2 same-manifest reconciliation gate, self-host it, and add one bounded declared-source resolver while preserving issue #54 and issue #57 history.

**Delivered:** The branch self-hosts one active issue #63 manifest and implements the resolver, but behavior coverage, version-2 lifecycle invariants, finalized authority stability, and shared snapshot isolation are incomplete. Commit `3f7c7a5` also includes unrelated formatter-only edits within the allowed files.

| Requirement | State | Evidence |
|---|---|---|
| R1 — bounded version-2 bootstrap | PARTIAL | The distinct `3f7c7a5` commit changes only the permitted code/test files, but findings #2 through #5 show incomplete substrate behavior and lifecycle enforcement. |
| R2 — immediate self-host gate | DONE | `99cfdf3` initializes the manifest; the current explicit classification validation exits zero. |
| R3 — closed reconciliation and active/finalized target semantics | PARTIAL | Shape and tag selection exist; findings #3 and #4 leave finalized semantics fail-open. |
| R4 — complete behavior inventory | PARTIAL | Current issue #63 inventory reproduces one `scripts/port_contract.py` row, but generated profiles, loaded top-level references, two runtime conformance contracts, the marketplace, and the root Codex configuration are excluded by finding #2. |
| R5 — one-way candidate-bound lifecycle | PARTIAL | Finalized rows/ref are guarded; source/execution authority and finalized evidence are not. |
| R6 — version dispatch, historical readability, narrow empty policy | DONE | Focused tests pass; issue #54 and issue #57 historical bytes are unchanged. |
| R7 — one safe declared-source resolver | DONE | Override, sibling discovery, normalized GitHub origin, exact `HEAD`, and containment checks are implemented and focused tests pass. |
| R8 — final evidence tag and clean-checkout proof | NOT-DONE | Explicitly assigned to U3; no tag or evidence was created. |
| R9 — PR merge-ref and post-merge proof | NOT-DONE | Explicitly assigned to U3; no PR exists. |
| R10 — separate focused, plugin, and full results | PARTIAL | Results are reported separately, but the shared-snapshot defect causes both the three Codex 0.147 failures and stale-runtime-proof failures. Only the legacy inventory drift is planned U3 regeneration. |
| R11 — final runbook, journal, and inventory binding | NOT-DONE | U3 owns the runbook, journal, legacy inventory regeneration, and only its adjacent digest rotation; it does not own a runtime-proof refresh. |

**COMPLETION:** 3 DONE, 5 PARTIAL, 3 NOT-DONE.

## Explicit contract assessments

### Declared-source resolver

The resolver is proportionate and correct for the issue #63 harness. `CODEX_PORT_SOURCE_REPO` wins over sibling discovery; the sibling comes from the Git common directory; accepted GitHub URL forms normalize to one repository identity; `HEAD` must equal the exact source target; and slash-bearing command paths must resolve to contained regular files. The focused remote readback confirms commit `b53827bb055e08ccc6aa547cade04aedf4385456` and harness blob `7c6c9aac411ec2a119b45e77558298846e7ee7b5` at 99,980 bytes. No rare-edge resolver hardening is recommended beyond the integrated test in finding #6.

### Behavior-path scope

The current repository evidence supports the following narrow classification under live issue #63 acceptance criterion 1:

| Surface | Behavior-bearing | Selected now | Disposition |
|---|---|---|---|
| Top-level `plugins/*/references/` files explicitly loaded by installed skills | Yes | No | Select the current loaded assets or their established runtime-reference roots; these files supply required routing, policy, templates, and executable guidance. Do not select unrelated reference prose merely because it shares the directory name. |
| `plugins/hermes-profile-evolution/conformance/profile-change-classifier.v1.json` and `profile-request-cli.v1.json` | Yes | No | Add these two exact runtime contracts. Do not include `provenance.json` on this basis because the adapter does not read it at runtime. |
| `.agents/plugins/marketplace.json` | Yes | No | Add this exact root file; it controls plugin discovery, local sources, installation policy, and staged active-workflow identity. |
| `.codex/config.toml` | Yes | No | Add this exact root file; it controls approval, agent depth, and active multi-agent features. |

These are concrete tracked surfaces. No general documentation root, all-purpose conformance directory, or speculative future configuration root is recommended.

### Historical issue #54 and issue #57 records

Both historical pairs are byte-for-byte preserved from the reviewed-plan commit through `HEAD`:

| Record | Git blob at plan commit and `HEAD` | SHA-256 |
|---|---|---|
| `docs/portability/ports/2026-07-26-lease-registry-forward-compat.json` | `74c14f07a4a262b4cb24a124948e29c9a4788f08` | `8950d53e9fdd2f63fb5d90349b77311a6e5c7dea71bb74e63144a6439b739915` |
| `tests/test_lease_registry_forward_compat_port_contract.py` | `b03b51f0bf3c9f6d093a608c484872986d4bb7b7` | `ab12fa0c2d9accff9e727a00e22f1bd327f070fdb0dcbecbf8fa207bf579983e` |
| `docs/portability/ports/2026-07-25-codex-627-seam-refreeze.json` | `59e4c1eb47fb3a37fd242620a0a7b690cd45dd81` | `dbc0a5361b470e169895c024e792dd3e6847bd9c51fc58b3989e82b8b3658d49` |
| `tests/test_codex_627_seam_refreeze_port_contract.py` | `a565f61129dfc6a1ae3d3492038a6c07ae49e00a` | `9133d3a204dc403fc44a2b5b9e91d92a933ef831cfdd48c8655ed1507e55cd72` |

The issue #57 evidence tag and issue #63 evidence tag are absent locally and remotely, as required through U2.

### Existing full-suite failures

The work-session record has nine distinct failing tests, but the causes within the six-test validator group overlap and must not be added as separate failure counts:

| Cause | Tests affected | Disposition |
|---|---|---|
| U1b shared-snapshot overwrite | All 3 Codex 0.147 snapshot/manifest tests, plus 5 of the 6 tests in the validator group | Current defect under finding #1. The five are the two combined repository-validation tests and three runtime-proof-specific tests. Restore the shared snapshot; do not refresh the runtime proof. |
| Legacy workflow inventory drift | 3 of the 6 tests in the validator group | Planned U3 work under corrected-plan R11: one legacy-inventory test plus the same two combined repository-validation tests. Regenerate the legacy inventory and rotate only its adjacent digest binding. |

The two repository-validation tests contain both errors, so the five runtime-proof-affected tests and three legacy-affected tests describe overlapping sets within the same six failures. `docs/validation/verified-workflows-runtime-proof.json` records `snapshot_sha256` `a9576e...`, exactly matching the pre-U1b shared snapshot, and its `harness_sha256` `a3a8ed5...` matches the current harness. A current dry-run generation differs only at `snapshot_sha256`. Restoring the shared snapshot therefore preserves the existing proof; refreshing it would incorrectly bind accepted Codex 0.147 evidence to issue #63 and is absent from both corrected-plan R11/U3 and the live issue's expected-file list.

After finding #1 is fixed, the remaining failures expected from this group are the legacy-inventory test and the two combined repository-validation tests. U3 owns that legacy regeneration and making all checks green before candidate freeze, but it does not own repairing the current shared-snapshot defect or regenerating the runtime proof.

### Issue #63 sequencing

Live GitHub issue #63 matches the corrected plan: new source evidence belongs to issue #63, issue #57 remains historical, and no retroactive tag or migration is allowed. Live `origin/main` is `ed8d74f260f029e41ee4e6e44975f9d70522697a`; its only change after the reviewed base is the documented reusable-bootstrap file, and no open PR exists. Issues #61 and #62 remain open, so issue #63-first integration has not been violated. U3 must retain that serialization.

## Checks

| Check | Result |
|---|---|
| Branch and revision | Clean branch at `ae0e4f9fcb11e9490f0a87931f82e6e85f2e7f65` |
| Live issue #63 and #57 readback | Corrected intent and superseding comments present |
| Focused port-contract, issue #54, issue #57, and source-resolution tests | 90 passed |
| Codex 0.147 capability-snapshot and port-contract group | 3 failed, 65 passed; finding #1 |
| Six-test legacy/runtime-proof validator group | 6 failed; runtime-proof staleness affects 5, legacy drift affects 3, with 2 combined tests in both sets |
| Issue #63 active classification | Passed |
| Issue #63 generated classification check | Passed |
| Ruff lint for changed Python files | Passed |
| Ruff formatter check | `tests/test_port_contract.py` formatted; `scripts/port_contract.py` would change in three U2 locations |
| Runtime-proof digest probe | Tracked snapshot digest equals pre-U1b snapshot; tracked harness digest equals current harness; current dry-run differs only at `snapshot_sha256` |
| Repository plugin validator | Failed with two legacy-workflow digest drifts plus stale runtime proof; only the legacy inventory and adjacent digest rotation are planned U3 work |
| Corrected plan R11/U3 and live issue file scope | Runtime-proof refresh is not assigned or authorized; legacy inventory regeneration is assigned to U3 |
| Behavior-path surface audit | Confirmed all four named surface groups are currently omitted; `provenance.json` is validation-only and not added |
| Historical byte comparison | All four issue #54/#57 records unchanged |
| Evidence tags | Issue #57 and issue #63 tags absent locally and remotely |
| Diff whitespace | Passed |

## Coverage

Three candidate concerns were suppressed below confidence 75: the 64-commit previous-manifest search bound, case-sensitive GitHub repository identity, and root-level command arguments without a slash. They are narrow or outside the approved issue #63 harness and do not warrant hardening in this ordinary plugin repository.

Residual U3 risks remain external and intentionally unverified: the live harness execution, final evidence creation, exact non-force tag publication/readback, disposable clean-checkout validation, PR merge-ref comparison, and post-merge comparison have not started. No Saga state was scanned or written because the operator expressly prohibited local Saga mutation.

> **Verdict:** Do not start U3. Fix findings #1 through #5, add the focused coverage in #6, resolve the proportional formatting cleanup in #7, rerun the independent code review, and only then enter U3's evidence and publication sequence.

CODE REVIEW COMPLETE
