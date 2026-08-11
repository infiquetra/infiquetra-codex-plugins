---
title: Issue 63 Port Manifest Reconciliation and Companion Harness
type: feat
status: active
date: 2026-08-10
deepened: 2026-08-10
origin: docs/brainstorms/2026-07-26-codex-plugin-lifecycle-simplification-requirements.md
---

# Issue 63 Port Manifest Reconciliation and Companion Harness

## Summary

Make the existing cycle JSON port manifest account for every behavior-bearing path in its active branch diff, freeze finalized history to one immutable evidence tag, and let evidence select the manifest's one declared source repository when its acceptance harness lives there. Keep focused capability proof and the full repository result separate and visible without adding another manifest, evidence format, attribution subsystem, or control plane.

---

## Problem Frame

The classification gate currently proves only that rows already present in a manifest are classified. It derives source rows from the pathspecs supplied at initialization, so a behavior-bearing path omitted from those pathspecs can ship while `validate --stage classification` remains green (`docs/engineering-journal/LEARNINGS.md`).

The evidence contract is independently too narrow for one accepted cross-runtime proof. `_validate_evidence_argv` and `validate_manifest` in `scripts/port_contract.py` require `cwd: "."` and reject unsafe absolute or traversing command paths, while the version-1 issue #57 historical record names a harness that exists in the declared source repository rather than this repository. Its evidence tag, `refs/tags/evidence/codex-627-seam-refreeze-20260725`, was intentionally never created. A version-2 active cycle cannot retain that nonempty historical evidence, and a finalized cycle cannot resolve the missing tag, so this plan must preserve rather than migrate that record.

Issue #54 already shipped and proved lease-registry unknown-field compatibility. Its implementation is historical accepted evidence only; this plan does not reopen its runtime behavior, tests, or port manifest.

Two lifecycle gaps compound the omission. A manifest permanently validated against `HEAD` becomes stale when unrelated work later lands, while an evidence tag cannot anchor the final candidate until that candidate is committed. The new gate also cannot classify its own first implementation. This plan therefore permits one reviewed Codex-local substrate commit, immediately self-hosts an active version 2 cycle, and changes to tag-bound finalized validation only after evidence is complete.

---

## Requirements

R1. The reviewed plan may authorize one bounded Codex-local bootstrap before the new gate exists. That bootstrap may change only `scripts/port_contract.py` and focused tests needed for exact version 1/version 2 dispatch, version 2 reconciliation and behavior-path detection, active/finalized target semantics, the optional evidence repository schema, and the contract-only version-policy rule. It must be tested and committed as a distinct subunit. No companion resolver, change to the issue #57 historical record or its regression test, source-derived change, or unrelated behavior may enter that commit.

R2. Immediately after the bootstrap commit, implementation must capture live authority and initialize the single issue #63 manifest as version 2 from the reviewed plan commit. It must classify every bootstrap behavior path as `codex-local`, render the classification, and pass explicit classification validation before any later behavior change. This is the narrow sequencing exception to runbook requirements R22 and R23: those requirements still prohibit source-derived behavior until the self-hosted gate is green.

R3. Version 2 adds one closed `reconciliation` object with exactly `state`, `expected_count`, `inventory_sha256`, and normalized `rows`. `state` is `active` or `finalized`; the existing safe issue-specific `codex.evidence_ref` remains the sole target authority; and each closed row has exactly `row_id`, `change`, `old_path`, `new_path`, `similarity`, `classification`, `rationale`, and `source_row_refs`. Active classification validation is permitted only while evidence is empty and `codex.evidence_ref` is absent; it compares `codex.execution_base..HEAD`. Finalized historical validation must resolve the immutable `codex.evidence_ref` tag and compare `codex.execution_base` to that frozen target, never to later `HEAD`.

R4. Every behavior-bearing added, modified, deleted, or renamed path in the selected target range must have exactly one reconciliation row using `source-derived`, `codex-local`, `intentionally-divergent`, `deferred`, or `blocked`. A missing, duplicate, stale, or unknown row, or a changed path marked `deferred` or `blocked`, keeps classification nonzero. The deterministic repository predicate covers root `scripts/` and active plugin manifests, scripts, skills, hooks, configuration, and roles, while excluding plans, reviews, classifications, validation receipts, journal prose, tests, and fixtures.

R5. Reconciliation is one-way and candidate-bound. A finalized manifest cannot silently return to active, change `codex.evidence_ref`, adopt a non-fast-forward candidate, or validate a behavior inventory different from its frozen tag. Later unrelated `main` changes must not invalidate a finalized historical cycle.

R6. New initialization and writes emit version 2. Version 1 retains its current exact evidence fields, requires a nonempty version policy, remains byte-readable, and rejects `repository`. The issue #57 version-1 manifest and `tests/test_codex_627_seam_refreeze_port_contract.py` remain byte-for-byte historical regression records. Version 2 retains those evidence fields and permits only optional `repository: "source"`. An explicit empty version-policy list is valid only when the version 2 cycle is contract-only: source base equals source target, source rows are empty, and every behavior reconciliation row is `codex-local`. All other version 2 manifests require a nonempty version policy. Issue #63 uses an explicit repository file containing `[]`; it invents no plugin version or release unit.

R7. After the self-host gate passes, one issue #63 evidence entry may select the singular declared source repository. `repo_head` remains the Codex proof subject. Source resolution honors `CODEX_PORT_SOURCE_REPO` first, otherwise derives a Git-common-directory sibling from `source.repository_id`; it verifies normalized origin, exact `HEAD == source.target_ref`, and realpath containment. The issue #63 live proof uses a disposable exact-target checkout and never updates the ordinary source checkout. This revalidation supersedes only the old unresolved command-location claim; it neither finalizes nor rewrites issue #57 history.

R8. The evidence ref `refs/tags/evidence/issue-63-port-manifest-reconciliation-20260810` begins absent and must be refused if it already exists at any commit. U1 must not create it. After the independent re-review and code-review fixes and focused, plugin, and full checks pass, the final manifest records the new issue #63 `repository: "source"` evidence with every evidence `repo_head` set to the prior final code commit. The absent tag is then created exactly once at that finalized candidate and must retain the execution base and every evidence commit in its history. After local finalized validation passes and before any PR is created, push only that exact tag ref to `origin` without force, read back that exact remote ref and require it to resolve to the frozen candidate, fetch only that exact ref into a disposable clean checkout, and run finalized-manifest validation there with `CODEX_PORT_SOURCE_REPO` explicitly set to the disposable exact-target Claude checkout. Any local validation, push, remote readback, fetch, or clean-checkout validation failure stops progression. A remotely published tag is never moved or deleted.

R9. Immediately before merge, the GitHub PR merge ref must have the same normalized reconciliation inventory as the frozen candidate. A read-only Git comparison over every path selected by the deterministic behavior predicate must also prove identical presence, mode, and blob content; documentation-only files may differ. The actual merge commit must pass the same two comparisons against the frozen candidate. A changed behavior path, merge result, or candidate returns to candidate review and uses a new attempt-suffixed tag rather than moving the old tag. Integration is serialized so issue #63 merges before issue #61 or #62 behavior branches. No stored behavior-tree digest or new evidence format is added.

R10. Focused port-contract proof, `python3 scripts/validate_codex_plugins.py`, and the full `python3 -m pytest -q` result remain separate and truthful. A nonzero result blocks merge. No checked-in suppression baseline, validation-attribution subsystem, second manifest, compatibility database, evidence-chain format, repository registry, or port control plane is added. The unchanged issue #54 version-1 manifest and test, and the unchanged issue #57 version-1 manifest and `tests/test_codex_627_seam_refreeze_port_contract.py`, remain historical regression evidence only.

R11. The final documentation unit updates the runbook and decision journal for the bootstrap exception, active/finalized lifecycle, absent-then-immutable tag, PR merge-ref proof, and integration serialization. After the final journal edit, it regenerates `docs/validation/verified-workflows-legacy-token-inventory.json`, rotates only `LEGACY_WORKFLOW_HISTORICAL_INVENTORY_SHA256` and its adjacent reason comment, and requires inventory `--check` and full plugin validation.

---

## Key Technical Decisions

KTD1. Use a reviewed bootstrap, then self-host immediately: the minimum version 2 substrate is the only behavior allowed before the new gate exists. Commit it separately, initialize the issue #63 manifest from the reviewed plan commit, classify every bootstrap behavior path as Codex-local, and pass the gate before companion or source-derived work.

KTD2. Keep reconciliation in the existing manifest as one closed version 2 object. Reuse the NUL-delimited rename-aware Git inventory and stable row identity; store only `state`, normalized rows, count, and digest. The existing `codex.evidence_ref` continues to own the safe absent/finalized tag rather than duplicating it inside reconciliation.

KTD3. Give active and finalized cycles different target authority through the existing `codex.evidence_ref`. Active classification with empty evidence and that ref absent compares `codex.execution_base..HEAD`; finalized historical validation resolves the immutable ref and never follows later `HEAD`. Finalized state, evidence ref, ancestry, and inventory cannot be silently rewound or moved.

KTD4. Apply the retained vocabulary to a deterministic repository behavior predicate. Missing or stale rows fail, and changed `deferred` or `blocked` rows remain stop dispositions. Documentation, tests, fixtures, generated classifications, validation receipts, and journal prose do not become behavior rows.

KTD5. Dispatch schema and version policy together. Version 1 stays byte-readable, rejects `repository`, and requires nonempty policy. Version 2 adds only reconciliation plus optional `repository: "source"`; only a source-empty, entirely Codex-local contract cycle may load an explicit `[]` policy file. Issue #63 uses that exception instead of fabricating release metadata.

KTD6. Reuse `source.repository_id` as the sole companion declaration after self-hosting. Resolve `CODEX_PORT_SOURCE_REPO` before the Git-common-directory sibling, then verify origin, exact target `HEAD`, and containment. `repo_head` remains Codex-local, and the new issue #63 evidence uses a disposable checkout without altering the ordinary source repository. The missing issue #57 evidence tag rules out a schema migration, so that version-1 historical record remains immutable.

KTD7. Freeze and publish final evidence once. The base evidence tag starts absent, is created only after final code review and all checks, and points at the committed finalized manifest/evidence candidate whose evidence rows name the prior final code commit. After local validation, push only the exact tag ref to `origin` without force, require exact remote readback, and prove finalized validation from that exact ref in a disposable clean checkout before opening a PR. PR merge-ref and post-merge readback must preserve both the normalized inventory and each selected behavior path's presence, mode, and blob content; documentation-only differences are allowed. Any changed attempt gets a reviewed suffixed tag, never a moved or deleted published tag.

KTD8. Serialize integration and preserve validation truth. Issue #63 merges before issue #61 or #62 behavior work; focused, plugin-validator, and full-suite results remain separate. The final documentation unit updates the runbook and journal, regenerates the historical inventory, and rotates only its validator digest binding.

---

## Implementation Units

### U1. Bootstrap version 2 and immediately self-host the cycle

Use one reviewed Codex-local exception to create the gate that governs all later work.

**Goal:** Land only the minimum version 2 contract substrate, then initialize the issue #63 manifest from the reviewed plan commit and pass its classification gate over every bootstrap behavior path before companion behavior starts.

**Requirements:** R1, R2, R3, R4, R5, R6

**Dependencies:** The independent reviewer must write `docs/reviews/2026-08-10-issue-63-port-manifest-reconciliation-doc-review.md`. The reviewed plan commit must have parent `43b18477906ba9790ef3ca555ecfd993da068a35`. The base evidence tag must be absent; if it exists at any commit, stop rather than reuse or move it.

**Files:** `scripts/port_contract.py`, `tests/test_port_contract.py`, `docs/reviews/2026-08-10-issue-63-port-manifest-reconciliation-doc-review.md` (reviewer-owned input; do not edit in implementation), `docs/validation/codex-runtime-capability-snapshot.json`, `docs/validation/codex-runtime-capability-snapshot.schema-r4.json`, `docs/portability/ports/2026-08-10-issue-63-port-manifest-reconciliation-version-policy.json`, `docs/portability/ports/2026-08-10-issue-63-port-manifest-reconciliation.json`, `docs/portability/classifications/2026-08-10-issue-63-port-manifest-reconciliation.md`

**Approach:** U1a is the sole pre-gate behavior exception. Implement exact version 1/version 2 dispatch, the closed reconciliation object and normalized row contract, the repository behavior predicate, active/finalized selection through the existing `codex.evidence_ref`, one-way state/ref/ancestry validation, the optional version 2 evidence repository key, and the contract-only empty-version-policy rule. New writes emit version 2. Version 1 remains byte-readable, rejects `repository`, and requires nonempty policy. Version 2 accepts an explicit `[]` only when source base equals target, source rows are empty, and every reconciliation row is Codex-local. Cover those boundaries with focused tests and commit U1a alone; no resolver execution, issue #57 migration, source-derived change, tag creation, or unrelated behavior is permitted.

U1b immediately self-hosts that substrate. Capture a live authority snapshot and preserve three distinct source facts: ordinary checkout `HEAD` `7f2b98f2ac61431c98d177c25277d287a111aef4`, stale local `origin/main` `1f6c6df4f080247150f489280836e7f4eda4973d`, and live remote `main` `b53827bb055e08ccc6aa547cade04aedf4385456`. Use a disposable detached checkout or temporary clone with normalized origin `infiquetra/infiquetra-claude-plugins` and exact `HEAD` `b53827bb055e08ccc6aa547cade04aedf4385456`; never fetch, switch, clean, or update the ordinary checkout. Pin that live commit as both source base and target, name only `tools/run_cross_runtime_outcome_acceptance.py` as the source pathspec, and write `[]` to the explicit issue #63 version-policy file. Pass the already committed `docs/validation/codex-runtime-capability-snapshot.schema-r4.json`, not the stale unversioned schema path: the active issue #63 manifest and classification already bind the current capability snapshot to schema r4.

Initialize with no unrelated defaults: explicitly pass `--manifest docs/portability/ports/2026-08-10-issue-63-port-manifest-reconciliation.json`, `--port-id issue-63-port-manifest-reconciliation-2026-08-10`, the disposable path through `--source-repo`, `--source-repository-id infiquetra/infiquetra-claude-plugins`, both source refs, every source pathspec, `--codex-plan-base 43b18477906ba9790ef3ca555ecfd993da068a35`, the exact reviewed plan commit through `--codex-execution-base`, `--codex-evidence-ref refs/tags/evidence/issue-63-port-manifest-reconciliation-20260810`, the plan, reviewer artifact, classification path, runbook, live capability snapshot, `--capability-schema docs/validation/codex-runtime-capability-snapshot.schema-r4.json`, `--codex-repository-id infiquetra/infiquetra-codex-plugins`, and the explicit `[]` version-policy file. Create an active reconciliation with empty evidence and keep the existing safe `codex.evidence_ref` absent. Inventory `execution_base..HEAD`, record every bootstrap behavior path, classify each Codex-local, render, and pass explicit classification validation. Do not create the evidence tag in U1. No other behavior change is allowed before this gate succeeds.

**Patterns to follow:** `parse_name_status_z`, `git_inventory`, and `normalize_inventory` in `scripts/port_contract.py` provide the normalized rename-aware Git inventory; `_exact_keys` enforces closed objects; and `validate_manifest` is the classification boundary.

**Test scenarios:** Happy paths — version 1 remains readable; new writes emit version 2; the exact contract-only version 2 cycle accepts `[]`; an active cycle with empty evidence, absent safe `codex.evidence_ref`, exact bootstrap rows, and only Codex-local classifications validates against `HEAD`. Edge cases — additions, deletions, and either side of a rename enter the behavior inventory; excluded documentation/tests do not; ordinary source checkout refs remain unchanged. Error paths — version 1 `repository`, version 1 empty policy, non-contract-only version 2 empty policy, a reconciliation `target_ref` or any other unknown field, stale row/digest/count, missing behavior path, active evidence, unsafe or existing evidence ref, finalized-to-active transition, `codex.evidence_ref` change, non-fast-forward candidate, `deferred`/`blocked` changed row, source-checkout mismatch, omitted explicit authority input, or any pre-gate non-bootstrap behavior fails.

**Verification:** The U1a commit contains only the minimum contract substrate and focused tests. The issue #63 version 2 manifest then records the reviewed plan commit as `codex.execution_base`, the source inventory is empty, every bootstrap behavior path is represented and Codex-local, the generated classification is current, the evidence tag is still absent, and explicit classification validation exits zero before U2 begins.

### Post-U1b correction gate

Apply this narrow correction only after U1b has completed under its original review and before U2 resumes.

**Goal:** Prospectively rebind the active issue #63 authority for U2 and U3 without retroactively changing the authority that governed completed U1a/U1b.

**Files:** `docs/plans/2026-08-10-issue-63-port-manifest-reconciliation-plan.md`, `docs/reviews/2026-08-11-issue-63-port-manifest-reconciliation-plan-re-review.md` (reviewer-owned input; do not create or edit in implementation), `docs/portability/ports/2026-08-10-issue-63-port-manifest-reconciliation.json`, `docs/portability/classifications/2026-08-10-issue-63-port-manifest-reconciliation.md`; live GitHub issue #63 and its comments (Root-owned external authority; Root performs this mutation separately); `docs/engineering-journal/DECISIONS.md` (preserved until U3)

**Approach:** Before U2, Root must update the live issue #63 intent, test scope, and acceptance criterion 3 to require only the new issue #63 `repository: "source"` evidence in U3, not an issue #57 migration. Root must also add a superseding comment that marks the earlier issue #57-migration comment as historical. The existing issue #57-migration entry in `docs/engineering-journal/DECISIONS.md` and the original review statement are preserved U1-era history, but the corrected plan and this re-review prospectively supersede them for U2 and U3; U3 retains responsibility for the final journal rewrite and generated-inventory binding.

After the corrected plan is independently re-reviewed and Root's issue readback is current, replace only the active issue #63 manifest authority plan digest with the corrected plan digest, append the re-review path and digest to `authority.reviews`, render the classification, and pass explicit classification validation. This gate prospectively rebinds active authority for U2 and U3; it adds no behavior and does not retroactively alter the U1a/U1b commits, authority, or evidence.

**Verification:** Live issue #63 readback shows the corrected intent, test scope, acceptance criterion 3, and a superseding historical comment before U2 begins. The active issue #63 manifest records the corrected plan and both review artifacts at their exact digests, each review path appears exactly once, its generated classification is current, and classification validation exits zero before U2 begins.

### U2. Resolve one declared companion-repository harness safely

Add the bounded resolver that the later issue #63 proof will use, without migrating historical records.

**Goal:** Permit one future issue #63 evidence entry to select the manifest's declared source repository and verify that repository and its contained harness path.

**Requirements:** R2, R4, R6, R7, R10

**Dependencies:** U1's self-hosted classification gate and the post-U1b correction gate are green.

**Files:** `scripts/port_contract.py`, `tests/test_port_contract.py`, `docs/portability/ports/2026-08-10-issue-63-port-manifest-reconciliation.json`, `docs/portability/classifications/2026-08-10-issue-63-port-manifest-reconciliation.md`

**Approach:** Implement source-checkout resolution only after U1 passes. Use `CODEX_PORT_SOURCE_REPO` first, otherwise derive the repository-name sibling of the Codex Git common directory from the singular `source.repository_id`. Verify normalized origin and exact `HEAD == source.target_ref` before resolving `cwd: "."` and relative harness paths through realpath containment. Keep `repo_head` bound to the Codex proof commit. Commit this bounded resolver and its focused tests before changing the active issue #63 reconciliation; immediately update that manifest's reconciliation rows, render its classification, and pass classification validation. That gate must be green before any further behavior, review, evidence recording, or publication. Do not add evidence in the active cycle, migrate `docs/portability/ports/2026-07-25-codex-627-seam-refreeze.json`, or change `tests/test_codex_627_seam_refreeze_port_contract.py` or any issue #54 record.

**Patterns to follow:** `resolve_port_source_repo` in `tests/conftest.py` contains the established Git-common-directory and normalized-origin source-checkout pattern; `contained_file` in `scripts/port_contract.py` rejects a contained-file symlink escape; `validate_repo_path` and `_validate_evidence_argv` enforce repository-path and evidence-argument safety; and `validate_manifest` is the closed evidence boundary.

**Test scenarios:** Happy path — a version-2 issue #63 evidence selector resolves `python3 tools/run_cross_runtime_outcome_acceptance.py` beneath a Git-verified `infiquetra/infiquetra-claude-plugins` source checkout at the manifest target; both explicit-environment and Git-common-directory sibling resolution work. Edge cases — an omitted selector continues to validate Codex-local evidence unchanged, and a temporary detached worktree at the target commit is accepted. Error paths — `repository` in version 1, an unknown version-2 selector, missing source declaration, missing checkout, origin mismatch, checkout `HEAD` mismatch, absent harness, absolute argument, `..`, cache path, symlink escape, non-root `cwd`, and any other unknown evidence key all fail. Historical regression scenario — the issue #57 manifest and `tests/test_codex_627_seam_refreeze_port_contract.py` remain byte-for-byte unchanged; the issue #54 manifest and test remain unchanged.

**Verification:** The resolver verifies the source checkout's origin and target commit before the harness resolves inside it, `repo_head` remains the Codex proof subject, and all focused negative revision, containment, and declaration cases fail. Immediately after its behavior commit, the active issue #63 reconciliation represents the resolver and its generated classification passes; no further behavior, review, evidence recording, or publication occurs before that green result. The issue #57 manifest and regression test, and every issue #54 historical record, are byte-for-byte unchanged.

### U3. Document, finalize, and prove the frozen candidate

Finish the contract change with durable procedure, immutable evidence, and merge-time proof.

**Goal:** Document the bootstrap and lifecycle, produce the reviewed final candidate, create and narrowly publish its evidence tag exactly once, prove finalized validation from a clean checkout, and prove the PR merge ref and actual merge retain the frozen behavior inventory.

**Requirements:** R3, R5, R8, R9, R10, R11

**Dependencies:** U2; the independent re-review artifact `docs/reviews/2026-08-11-issue-63-port-manifest-reconciliation-plan-re-review.md` and all independent code-review findings are complete and fixed; the active classification gate, focused tests, plugin validator, and full suite pass separately.

**Files:** `docs/portability/claude-to-codex-plugin-port-runbook.md`, `docs/portability/ports/2026-08-10-issue-63-port-manifest-reconciliation.json`, `docs/portability/classifications/2026-08-10-issue-63-port-manifest-reconciliation.md`, `docs/validation/issue-63-port-manifest-reconciliation-u3-source-harness.json`, `docs/reviews/2026-08-11-issue-63-port-manifest-reconciliation-plan-re-review.md` (reviewer-owned input; do not edit in implementation), `docs/engineering-journal/DECISIONS.md`, `docs/validation/verified-workflows-legacy-token-inventory.json`, `scripts/validate_codex_plugins.py`

**Approach:** Update the runbook and journal to explain the reviewed bootstrap exception, immediate self-host gate, active `HEAD` versus finalized tag target, narrow `[]` policy, absent-then-immutable tag, candidate attempts, PR merge-ref proof, and issue #63-before-#61/#62 serialization. Rebind the active manifest/classification to the new runbook digest. Preserve and verify the re-review entry already bound by the post-U1b correction gate exactly once; do not append or otherwise add it again. After the final journal edit, regenerate the historical inventory, rotate only its expected digest constant and adjacent reason comment, and run focused tests, plugin validation, and the full suite as separate results.

Before freezing, compare current `main` with `43b18477906ba9790ef3ca555ecfd993da068a35`. The newly merged reusable-bootstrap document is documentation-only, is excluded from behavior reconciliation, and does not require this cycle to rebase beyond `43b1847`; the reviewed plan commit must retain that exact parent. If later `main` gains any behavior-bearing path, stop and return to candidate review. If integration requires a rebase and the intervening changes are documentation-only, perform it only before candidate freeze, repeat review and all gates, and do not silently replace the manifest's reviewed execution base. Serialize integration so issue #63 lands before issue #61 or #62 behavior branches.

Use the disposable Claude checkout at the declared exact target to run `python3 tools/run_cross_runtime_outcome_acceptance.py`. Record its result in `docs/validation/issue-63-port-manifest-reconciliation-u3-source-harness.json`, then add one issue #63 evidence entry with `repository: "source"`, `cwd: "."`, that artifact, and the prior final code commit as `repo_head`. For each disposable clean-checkout validation, explicitly set `CODEX_PORT_SOURCE_REPO` to that exact-target Claude checkout; do not rely on sibling discovery. This truthful revalidation supersedes only the old issue #57 command-location claim. It must not add evidence to, migrate, finalize, or otherwise rewrite the issue #57 version-1 manifest or its regression test.

Let the last code commit after review fixes be the evidence subject. Populate every issue #63 evidence row's `repo_head` with that prior final code commit. Change the issue #63 reconciliation from active to finalized without changing `codex.execution_base`; commit the finalized manifest, classification, evidence, runbook, journal, generated inventory, and digest binding as the candidate. Confirm the base evidence tag is still absent, create it exactly once at that candidate, and validate that the tagged history contains the execution base and every evidence `repo_head`. Finalized validation resolves the tag and remains stable when later `HEAD` changes.

After local finalized validation succeeds, push only `refs/tags/evidence/issue-63-port-manifest-reconciliation-20260810` to the same exact ref on `origin`, without force and without pushing a branch or any other tag. Read `origin` back using that exact ref and require its object ID to equal the frozen candidate. Fetch only that exact remote ref into a disposable clean checkout and run finalized-manifest validation there, proving a fresh clone or CI can resolve all frozen history without local-only refs. Stop before PR creation if local validation, the non-force push, exact-ref remote readback, exact-ref fetch, or clean-checkout validation fails. Once published remotely, never move or delete the tag. A changed candidate repeats this sequence only with a reviewed `-attempt-N` evidence ref; do not add a release workflow, generic tag manager, or other publication machinery.

Open the PR only after the tagged candidate is valid. Fetch and inspect GitHub's PR merge ref immediately before merge. Require its normalized reconciliation inventory to match the frozen candidate, then use a read-only Git comparison over the deterministic behavior-path selection to prove identical presence, mode, and blob content for every selected path; allow documentation-only paths to differ. If any behavior path, merge ref, or candidate changes, return to candidate review, rerun all checks, and freeze a new `-attempt-N` tag without moving or deleting any published tag. After merge, read back the actual merge commit and repeat both the inventory and selected-path content comparisons against the frozen candidate before closeout. Historical validation continues to use the frozen `codex.evidence_ref`, never merge-time or later `HEAD`. Do not store a behavior-tree digest or add another evidence format.

**Patterns to follow:** `build_manifest` in `scripts/port_contract.py` binds authority artifact bytes; `validate_port_contract` in `scripts/validate_codex_plugins.py` delegates repository port validation; and `main` in that validator returns the process result.

**Test scenarios:** Happy path — the finalized issue #63 manifest resolves the immutable `codex.evidence_ref`, reproduces the frozen behavior rows/digest, contains the execution base and every evidence commit, and validates the `repository: "source"` harness from a disposable clean checkout with `CODEX_PORT_SOURCE_REPO` explicitly set; it survives exact non-force publication/readback and remains valid after unrelated later `HEAD` changes. The PR merge ref and actual merge have identical selected-path presence, mode, and blobs despite allowed documentation differences; focused, plugin, and full checks pass and are reported separately. Edge cases — documentation-only main changes remain excluded; the known reusable-bootstrap document does not force a rebase beyond `43b1847`; issue #54 and issue #57 historical records remain unchanged. Error paths — pre-existing base tag, missing finalized tag, tag/candidate mismatch, finalized-to-active transition, evidence-ref change, non-fast-forward candidate, missing or wrong `CODEX_PORT_SOURCE_REPO`, local finalized-validation failure, rejected push, remote ref mismatch, exact-ref fetch failure, clean-checkout validation failure, changed behavior inventory, selected behavior path missing or changed in mode/blob, evidence `repo_head` outside tagged history, stale runbook/classification/inventory digest, behavior-bearing main drift, or any nonzero validation result blocks progression. Retry path — preserve every published tag and require a reviewed attempt-suffixed tag after renewed review.

**Verification:** The runbook, finalized tagged issue #63 manifest, classification, source-harness evidence, decision journal, generated inventory, and digest binding agree. The already-bound re-review authority entry is present exactly once, and each manifest review path appears exactly once. The exact remote evidence ref resolves to the frozen candidate and finalized-manifest validation passes from a disposable clean checkout with `CODEX_PORT_SOURCE_REPO` explicitly set before PR creation. The PR merge ref and actual merge readback preserve the normalized inventory and every selected behavior path's presence, mode, and blob content while permitting documentation-only differences. Focused, plugin-validator, and full-suite exit codes remain separate. No release workflow, generic tag manager, behavior-tree digest, second manifest, attribution/suppression system, compatibility database, repository registry, evidence-chain format, or control plane appears.

---

## Risks and Dependencies

The bootstrap exception is the main sequencing risk. U1a is restricted to the version 2 substrate and focused tests, lands as its own commit, and is immediately inventoried by U1b from the reviewed plan execution base. Any companion, source-derived, or unrelated behavior in that pre-gate commit invalidates the exception.

This plan depends on a Git-verifiable disposable source checkout for the issue #63 companion-harness proof. The validator must fail with one actionable repository-identity, revision, or containment error when that checkout is unavailable; clean-checkout validation explicitly sets `CODEX_PORT_SOURCE_REPO` and must not fall back to the preserved ordinary source checkout.

The behavior-path predicate is the main completeness risk. U1 pins every active runtime root and rename direction with negative fixtures so a future root addition requires an explicit predicate/test change rather than silently escaping the gate.

The active-to-finalized transition crosses an intentionally absent `codex.evidence_ref`. U3 commits the finalized candidate before creating that tag, so final historical validation cannot succeed until the one-time tag exists; any failure after publication preserves that tag and starts a reviewed attempt with a new suffix.

Local tag validation is not portable proof. U3 treats exact non-force publication, remote object-ID readback, exact-ref fetch, and disposable clean-checkout finalized validation as a single fail-closed boundary before PR creation. A partial failure stops; it never broadens the push, force-updates the ref, or substitutes local state for remote resolvability.

Concurrent mainline behavior is an integration risk. The known reusable-bootstrap document is excluded and does not move the cycle beyond `43b1847`; any later behavior-bearing change stops candidate preparation. Issue #63 lands before issue #61 or #62 behavior branches so the PR merge-ref comparison is not racing another port-contract change.

Changing the canonical runbook invalidates its active digest binding. U3 updates the runbook version, cycle manifest, and generated classification together; finalized historical validation thereafter uses its immutable tag and recorded runbook bytes.

`docs/engineering-journal/DECISIONS.md` is part of the generated legacy-workflow inventory. Planning regenerates and checks that inventory so the required KTD record does not leave document validation stale.

---

## Scope Boundaries

The implementation is limited to same-manifest branch-diff completeness and one source-repository evidence selector.

**Non-goals:** A second port manifest for the same cycle; a validation-attribution subsystem; `tests/test_validation_attribution.py`; a checked-in suppression baseline; automatic semantic classification; a repository registry; arbitrary absolute or traversing evidence paths; a compatibility database; an evidence-chain format; a port control plane; byte-for-byte Claude mirroring; a new cutover release-proof path; or an exhaustive provider/model/role/platform matrix.

**Historical evidence only:** Issue #54, its merged lease-registry implementation, its acceptance artifacts, `docs/portability/ports/2026-07-26-lease-registry-forward-compat.json`, and unknown-field compatibility behavior remain unchanged. The version-1 issue #57 manifest `docs/portability/ports/2026-07-25-codex-627-seam-refreeze.json` and `tests/test_codex_627_seam_refreeze_port_contract.py` remain byte-for-byte unchanged; the intentionally absent `refs/tags/evidence/codex-627-seam-refreeze-20260725` is not backfilled.

**Deferred to follow-up work:** Any general multi-repository evidence model, more than one companion repository, redesign of the existing cutover release-proof verifier, or changed-versus-unchanged failure attribution.

---

## Sources and Grounding

The plan follows the capability-first port requirements and acceptance examples in `docs/brainstorms/2026-07-26-codex-plugin-lifecycle-simplification-requirements.md`, and the mandatory gate ordering in `docs/portability/claude-to-codex-plugin-port-runbook.md`.

Current code derives inventories only over declared pathspecs through `git_inventory`, accepts the existing source and Codex treatment sets through `SOURCE_TREATMENTS` and `CODEX_TREATMENTS`, rejects unsafe argument paths through `_validate_evidence_argv`, and fixes evidence execution to the local root through `validate_manifest` in `scripts/port_contract.py`. The missed `outcome_decompose.py` path and its mechanism are recorded in `docs/engineering-journal/LEARNINGS.md`.

The issue #57 historical manifest records `tools/run_cross_runtime_outcome_acceptance.py` with local `cwd: "."` in `docs/portability/ports/2026-07-25-codex-627-seam-refreeze.json`. Its evidence ref `refs/tags/evidence/codex-627-seam-refreeze-20260725` was intentionally never created, so the record remains a byte-for-byte version-1 regression artifact rather than a version-2 migration target. The new issue #63 evidence revalidates only that command-location claim from the declared source checkout. The issue #54 port and its 14-of-14 follow-up acceptance landed in commits `ec523cc` and `f63ee82`; those commits establish accepted history, not current implementation scope.

Live read-only verification at source commit `b53827bb055e08ccc6aa547cade04aedf4385456` confirms that `tools/run_cross_runtime_outcome_acceptance.py` remains present with Git blob `7c6c9aac411ec2a119b45e77558298846e7ee7b5` and size 99,980 bytes. The three commits after stale local `origin/main` change only Hermes profile-evolution documentation, metadata, timeout behavior, and their tests; none changes the harness. This confirms continued desirability of the retained companion boundary without turning those unrelated source commits into refresh scope.

Read-only local ref inspection during planning confirmed that `refs/tags/evidence/issue-63-port-manifest-reconciliation-20260810` is absent. That observation is not durable authority: U1 and U3 each recheck absence at their own boundary and fail if any commit has acquired the ref.
