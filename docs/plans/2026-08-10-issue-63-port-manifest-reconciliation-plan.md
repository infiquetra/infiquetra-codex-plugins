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

Make the existing cycle JSON port manifest account for every behavior-bearing path in its active branch diff, freeze finalized history to one immutable evidence tag, and let evidence select the manifest's one declared source repository when its acceptance harness lives there. Give issue #63 its own schema-r4 runtime-capability snapshot while preserving the accepted shared Codex 0.147 snapshot and runtime proof. Keep focused capability proof and the full repository result separate and visible without adding another manifest, evidence format, attribution subsystem, or control plane.

Before U3 originally resumed, its reviewed authority was prospectively corrected so the runbook content change advanced the complete version contract from 5 to 6, rebound only the two live-authority contracts, and received fresh independent document and code review. After the full source harness halts on an out-of-scope runtime divergence, preserve that failed run as a non-evidence receipt and separately prove that the declared-source command resolves from the pinned companion repository.

---

## Problem Frame

The classification gate currently proves only that rows already present in a manifest are classified. It derives source rows from the pathspecs supplied at initialization, so a behavior-bearing path omitted from those pathspecs can ship while `validate --stage classification` remains green (`docs/engineering-journal/LEARNINGS.md`).

The evidence contract is independently too narrow for one accepted cross-runtime proof. `_validate_evidence_argv` and `validate_manifest` in `scripts/port_contract.py` require `cwd: "."` and reject unsafe absolute or traversing command paths, while the version-1 issue #57 historical record names a harness that exists in the declared source repository rather than this repository. Its evidence tag, `refs/tags/evidence/codex-627-seam-refreeze-20260725`, was intentionally never created.

A version-2 active cycle cannot retain that nonempty historical evidence, and a finalized cycle cannot resolve the missing tag, so this plan must preserve rather than migrate that record.

Issue #54 already shipped and proved lease-registry unknown-field compatibility. Its implementation is historical accepted evidence only; this plan does not reopen its runtime behavior, tests, or port manifest.

Two lifecycle gaps compound the omission. A manifest permanently validated against `HEAD` becomes stale when unrelated work later lands, while an evidence tag cannot anchor the final candidate until that candidate is committed. The new gate also cannot classify its own first implementation.

This plan therefore permits one reviewed Codex-local substrate commit, immediately self-hosts an active version 2 cycle, and changes to tag-bound finalized validation only after evidence is complete.

A reviewed-authority contradiction was confirmed before U3 edits: the canonical runbook requires every content change to advance its version and every active contract, but U3 named a runbook content change without naming the version-contract code, test, or Codex 0.147 live-authority binding. The prospective pre-U3 correction gate fixes that omission without changing completed U1, U2, or repair-review authority.

The pinned full harness run against Claude `b53827bb055e08ccc6aa547cade04aedf4385456` and Codex `e40688b263996dda4170a2cae0ac8be51544b2b3` exited 2 before scenarios because the runtime copies intentionally diverge. Claude commit `b727fa5c8a0418d1fcbff6d67893b3a05683e93c` retired broker settlement and successor handoff across `outcome_compat.py`, `outcome.py`, tests, references, and the outcome skill while Codex retained the earlier broker protocol.

That multi-file behavior port is outside this contract-only cycle. Issue #63 therefore preserves the failed full-harness bundle as a divergence receipt but uses a separate successful `--help` receipt to prove only the declared-source origin, revision, containment, file identity, exact command, and exit status required by issue #57.

---

## Requirements

R1. The reviewed plan may authorize one bounded Codex-local bootstrap before the new gate exists. That bootstrap may change only `scripts/port_contract.py` and focused tests needed for exact version 1/version 2 dispatch, version 2 reconciliation and behavior-path detection, active/finalized target semantics, the optional evidence repository schema, and the contract-only version-policy rule. It must be tested and committed as a distinct subunit.

No companion resolver, change to the issue #57 historical record or its regression test, source-derived change, or unrelated behavior may enter that commit.

R2. Immediately after the bootstrap commit, implementation must capture live authority and initialize the single issue #63 manifest as version 2 from the reviewed plan commit. It must classify every bootstrap behavior path as `codex-local`, render the classification, and pass explicit classification validation before any later behavior change. This is the narrow sequencing exception to runbook requirements R22 and R23: those requirements still prohibit source-derived behavior until the self-hosted gate is green.

R3. Version 2 adds one closed `reconciliation` object with exactly `state`, `expected_count`, `inventory_sha256`, and normalized `rows`. `state` is `active` or `finalized`; the existing safe issue-specific `codex.evidence_ref` remains the sole target authority; and each closed row has exactly `row_id`, `change`, `old_path`, `new_path`, `similarity`, `classification`, `rationale`, and `source_row_refs`. Active classification validation is permitted only while evidence is empty and `codex.evidence_ref` is absent; it compares `codex.execution_base..HEAD` and reads current authority files.

Finalized historical validation must resolve the immutable `codex.evidence_ref` tag, compare `codex.execution_base` to that frozen target, and validate the recorded authority artifacts from digest-bound bytes at that frozen target rather than later live files.

R4. Every behavior-bearing added, modified, deleted, or renamed path in the selected target range must have exactly one reconciliation row using `source-derived`, `codex-local`, `intentionally-divergent`, `deferred`, or `blocked`. A missing, duplicate, stale, or unknown row, or a changed path marked `deferred` or `blocked`, keeps classification nonzero.

The deterministic repository predicate covers root `scripts/`; active plugin manifests, scripts, skills, hooks, configuration, roles, and agents; the whole `plugins/discord-identity-assets/references/`, `plugins/python-toolkit/references/`, and `plugins/saga/references/rubrics/` roots; and `plugins/hermes-profile-evolution/conformance/profile-change-classifier.v1.json`, `plugins/hermes-profile-evolution/conformance/profile-request-cli.v1.json`, `.agents/plugins/marketplace.json`, and `.codex/config.toml`.

It also covers exactly `plugins/saga/references/bridge-signatures.json`, `plugins/saga/references/effort-policy.yaml`, `plugins/saga/references/engine-dispatch.md`, `plugins/saga/references/engine-registry.yaml`, `plugins/saga/references/formatting-style.md`, `plugins/saga/references/model-releases.yaml`, `plugins/saga/references/operator-choice.md`, `plugins/saga/references/outcome-cross-runtime.md`, `plugins/saga/references/outcome-spec.md`, and `plugins/saga/references/saga-spec.md`.

It excludes `plugins/hermes-profile-evolution/conformance/provenance.json`, plans, reviews, classifications, validation receipts, journal prose, tests, fixtures, unreferenced reference prose, and speculative future roots.

R5. Reconciliation is one-way and candidate-bound. A finalized manifest cannot silently return to active, change `codex.evidence_ref`, adopt a non-fast-forward candidate, replace or append evidence, or validate a behavior inventory different from its frozen tag. Finalized version 2 evidence is nonempty.

Across version-2 transitions, `source.repository_id`, `source.base_ref`, `source.target_ref`, `codex.repository_id`, `codex.historical_plan_base`, and `codex.execution_base` are immutable alongside the existing evidence-ref rule. Later unrelated `main` changes must not invalidate a finalized historical cycle.

R6. New initialization and writes emit version 2. Version 1 retains its current exact evidence fields, requires a nonempty version policy, remains byte-readable, and rejects `repository`. The issue #57 version-1 manifest and `tests/test_codex_627_seam_refreeze_port_contract.py` remain byte-for-byte historical regression records.

Version 2 retains those evidence fields and permits only optional `repository: "source"`. An explicit empty version-policy list is valid only when the version 2 cycle is contract-only: source base equals source target, source rows are empty, and every behavior reconciliation row is `codex-local`. All other version 2 manifests require a nonempty version policy.

Issue #63 uses an explicit repository file containing `[]`; it invents no plugin version or release unit.

R7. After the self-host gate passes, one issue #63 evidence entry may select the singular declared source repository. `repo_head` remains the Codex proof subject. Source resolution honors `CODEX_PORT_SOURCE_REPO` first, otherwise derives a Git-common-directory sibling from `source.repository_id`; it verifies normalized origin, exact `HEAD == source.target_ref`, and realpath containment.

The issue #63 live proof uses a disposable exact-target checkout and never updates the ordinary source checkout. This revalidation supersedes only the old unresolved command-location claim; it neither finalizes nor rewrites issue #57 history.

The successful command-resolution receipt is `docs/validation/issue-63-port-manifest-reconciliation-u3-source-command-resolution.json`. From the verified disposable Claude checkout at detached `HEAD` `b53827bb055e08ccc6aa547cade04aedf4385456`, it records argv exactly as `["python3", "tools/run_cross_runtime_outcome_acceptance.py", "--help"]` and proves normalized origin `infiquetra/infiquetra-claude-plugins`, contained harness path `tools/run_cross_runtime_outcome_acceptance.py`, Git blob `7c6c9aac411ec2a119b45e77558298846e7ee7b5`, size 99,980 bytes, a timezone-aware recorded time, and exit 0. It states that it proves command resolution rather than cross-runtime acceptance.

R8. The evidence ref `refs/tags/evidence/issue-63-port-manifest-reconciliation-20260810` begins absent and must be refused if it already exists at any commit. U1 must not create it. The corrected U3 implementation candidate has received a clean independent Saga code review with every P0-P3 finding closed; after the prospective evidence-scope gate passes and every applicable active-state result remains green, the final manifest records the new issue #63 `repository: "source"` command-resolution evidence from `docs/validation/issue-63-port-manifest-reconciliation-u3-source-command-resolution.json`, with every evidence `repo_head` set exactly to `e40688b263996dda4170a2cae0ac8be51544b2b3`.

The absent tag is then created exactly once at that finalized candidate and must retain the execution base and every evidence commit in its history. After local finalized validation passes and before any PR is created, push only that exact tag ref to `origin` without force, read back that exact remote ref and require it to resolve to the frozen candidate, fetch only that exact ref into a disposable clean checkout, and run finalized-manifest validation there with `CODEX_PORT_SOURCE_REPO` explicitly set to the disposable exact-target Claude checkout.

Any local validation, push, remote readback, fetch, or clean-checkout validation failure stops progression. A remotely published tag is never moved or deleted.

R9. Immediately before merge, the GitHub PR merge ref must have the same normalized reconciliation inventory as the frozen candidate. A read-only Git comparison over every path selected by the deterministic behavior predicate must also prove identical presence, mode, and blob content; documentation-only files may differ. The actual merge commit must pass the same two comparisons against the frozen candidate.

A changed behavior path, merge result, or candidate returns to candidate review and uses a new attempt-suffixed tag rather than moving the old tag. Integration is serialized so issue #63 merges before issue #61 or #62 behavior branches. No stored behavior-tree digest or new evidence format is added.

R10. Focused port-contract and runbook-version proof, both rendered live-authority classifications, `python3 scripts/validate_codex_plugins.py`, and the full `python3 -m pytest -q` result remain separate and truthful. Every active-state result must be green before declared-source command-resolution evidence runs, the issue #63 manifest finalizes, or the first local evidence tag is created. A nonzero result blocks progression.

Restoring the shared snapshot preserves the existing verified-workflows runtime proof; U3 does not regenerate or edit that proof. Only legacy-inventory drift remains assigned to U3, where the full suite must become green.

No checked-in suppression baseline, validation-attribution subsystem, second manifest, compatibility database, evidence-chain format, repository registry, or port control plane is added. The unchanged issue #54 version-1 manifest and test, and the unchanged issue #57 version-1 manifest and `tests/test_codex_627_seam_refreeze_port_contract.py`, remain historical regression evidence only.

R11. The final documentation unit updates the runbook and decision journal for the bootstrap exception, active/finalized lifecycle, absent-then-immutable tag, PR merge-ref proof, and integration serialization. Because that changes canonical runbook content, U3 bumps its metadata from version 5 to version 6.

In `scripts/port_contract.py`, U3 sets `RUNBOOK_VERSION = 6` and `SUPPORTED_RUNBOOK_VERSIONS = {3, 4, 5, RUNBOOK_VERSION}` without changing any other port-contract behavior. In `tests/test_port_runbook.py`, it changes the exact runbook-version expectation to 6 and asserts current version 6 plus historical support `{3, 4, 5, 6}`; it adds neither the optional generic cross-file drift assertion nor other hardening.

U3 rebinds only `docs/portability/ports/2026-08-10-issue-63-port-manifest-reconciliation.json` and `docs/portability/ports/2026-08-08-codex-0147-alignment.json` to runbook version 6 and the new runbook SHA-256, then renders `docs/portability/classifications/2026-08-10-issue-63-port-manifest-reconciliation.md` and `docs/portability/classifications/2026-08-08-codex-0147-alignment.md`. Every finalized or historical version-5 contract and `docs/validation/verified-workflows-runtime-proof.json` remains unchanged.

After the final journal edit, U3 regenerates `docs/validation/verified-workflows-legacy-token-inventory.json`, rotates only `LEGACY_WORKFLOW_HISTORICAL_INVENTORY_SHA256` and its adjacent reason comment, and requires inventory `--check` and full plugin validation.

R12. The evidence-scope correction after the full-harness halt is prospective authority only for U3 finalization. Root first updates and reads back the live issue #63 expected files and acceptance language, then an independent reviewer writes `docs/reviews/2026-08-11-issue-63-u3-evidence-scope-plan-correction-review.md` through the Saga document-review workflow.

After that issue readback and the reviewer reports `blocked=false`, the active issue #63 manifest prospectively binds the corrected plan digest and appends the new review path and digest exactly once. Its document-review authority then contains exactly five entries. It must render and validate while still active before evidence proceeds, while both code-review artifacts remain review provenance and never enter `authority.reviews`.

The existing clean active-state U3 code review at commit `dd9209740656f35831223e8f8652b37bd74de315` remains valid because this correction changes only the plan and later evidence selection. It repeats only if code, tests, or a selected behavior path changes.

R13. Preserve `docs/validation/issue-63-port-manifest-reconciliation-u3-source-harness.json` unchanged as a non-evidence divergence receipt with SHA-256 `1a83196f6c30a784117dff56702328f7243388deb2a060557eb03fc44c7056e1`, `overall_verdict` `halt`, halt code `port-digest`, and no scenarios. The successful command-resolution receipt must reference that path and digest without reclassifying the failed run as green, and the failed receipt must not enter manifest evidence or satisfy cross-runtime acceptance.

No issue #63 requirement makes the full cross-runtime harness pass. Porting Claude commit `b727fa5c8a0418d1fcbff6d67893b3a05683e93c` and its coupled `plugins/saga/scripts/outcome_compat.py`, `plugins/saga/scripts/outcome.py`, tests, references, and outcome-skill behavior requires a separate reviewed cycle.

---

## Key Technical Decisions

KTD1. Use a reviewed bootstrap, then self-host immediately: the minimum version 2 substrate is the only behavior allowed before the new gate exists. Commit it separately, initialize the issue #63 manifest from the reviewed plan commit, classify every bootstrap behavior path as Codex-local, and pass the gate before companion or source-derived work.

KTD2. Keep reconciliation in the existing manifest as one closed version 2 object. Reuse the NUL-delimited rename-aware Git inventory and stable row identity; store only `state`, normalized rows, count, and digest.

The existing `codex.evidence_ref` continues to own the safe absent/finalized tag rather than duplicating it inside reconciliation.

KTD3. Give active and finalized cycles different target authority through the existing `codex.evidence_ref`. Active classification with empty evidence and that ref absent compares `codex.execution_base..HEAD` against live authority files; finalized historical validation resolves the immutable ref and recorded digest-bound authority bytes at that candidate, never later `HEAD` or live files.

Finalized state, evidence, evidence ref, ancestry, inventory, and the pinned source and Codex repository/ref fields cannot be silently rewound or moved.

KTD4. Apply the retained vocabulary to a deterministic repository behavior predicate. Missing or stale rows fail, and changed `deferred` or `blocked` rows remain stop dispositions.

The predicate includes only present runtime surfaces: plugin agents; the whole `plugins/discord-identity-assets/references/`, `plugins/python-toolkit/references/`, and `plugins/saga/references/rubrics/` roots; and the exact Saga reference files in R4. It also includes the two runtime-read Hermes conformance contracts, the marketplace file, and the Codex configuration file in addition to the already selected paths.

It does not generalize to all reference prose, all conformance files, or future roots; `provenance.json`, documentation, tests, fixtures, generated classifications, validation receipts, and journal prose do not become behavior rows.

KTD5. Dispatch schema and version policy together. Version 1 stays byte-readable, rejects `repository`, and requires nonempty policy.

Version 2 adds only reconciliation plus optional `repository: "source"`; only a source-empty, entirely Codex-local contract cycle may load an explicit `[]` policy file. Issue #63 uses that exception instead of fabricating release metadata.

KTD6. Reuse `source.repository_id` as the sole companion declaration after self-hosting. Resolve `CODEX_PORT_SOURCE_REPO` before the Git-common-directory sibling, then verify origin, exact target `HEAD`, and containment.

`repo_head` remains Codex-local, and the new issue #63 evidence uses a disposable checkout without altering the ordinary source repository. The successful `--help` receipt proves command resolution only; the failed full harness remains a separately preserved divergence receipt. The missing issue #57 evidence tag rules out a schema migration, so that version-1 historical record remains immutable.

KTD7. Freeze and publish final evidence once. The base evidence tag starts absent and is created only after the existing clean independent Saga code review remains applicable, the evidence-scope correction gate passes, and all applicable active-state checks remain green. It points at the committed finalized manifest/evidence candidate whose evidence rows name `e40688b263996dda4170a2cae0ac8be51544b2b3`. After local validation, push only the exact tag ref to `origin` without force, require exact remote readback, and prove finalized validation from that exact ref in a disposable clean checkout before opening a PR.

PR merge-ref and post-merge readback must preserve both the normalized inventory and each selected behavior path's presence, mode, and blob content; documentation-only differences are allowed. Any changed attempt gets a reviewed suffixed tag, never a moved or deleted published tag.

KTD8. Serialize integration and preserve validation truth. Issue #63 merges before issue #61 or #62 behavior work; focused, plugin-validator, and full-suite results remain separate.

The code-review repair restores the shared Codex 0.147 snapshot and leaves its verified-workflows runtime proof unchanged, while U3 alone regenerates the legacy inventory and rotates only its validator digest binding.

KTD9. Advance the entire runbook version contract with its content. U3 changes only the runbook metadata, the two version constants in `scripts/port_contract.py`, the exact expectations in `tests/test_port_runbook.py`, and the two live-authority manifest/classification pairs needed for version 6.

Historical version-5 contracts and the existing Codex 0.147 runtime proof remain immutable. The completed runbook-version correction review is the fourth issue #63 document-review authority entry; the later evidence-scope correction review becomes the fifth, while code-review artifacts remain provenance outside that authority list.

KTD10. Treat command resolution and cross-runtime acceptance as different claims. Preserve the halted full-harness bundle with its original digest and verdict, but bind manifest evidence only to the successful exact-target `--help` receipt that proves the declared repository and command path resolve.

Claude commit `b727fa5c8a0418d1fcbff6d67893b3a05683e93c` deliberately changed the broker protocol across code, tests, references, and skills. Absorbing that behavior to make the harness green would violate this cycle's contract-only boundary.

---

## Implementation Units

### U1. Bootstrap version 2 and immediately self-host the cycle

Use one reviewed Codex-local exception to create the gate that governs all later work.

**Goal:** Land only the minimum version 2 contract substrate, then initialize the issue #63 manifest from the reviewed plan commit and pass its classification gate over every bootstrap behavior path before companion behavior starts.

**Requirements:** R1, R2, R3, R4, R5, R6

**Dependencies:** The independent reviewer must write `docs/reviews/2026-08-10-issue-63-port-manifest-reconciliation-doc-review.md`. The reviewed plan commit must have parent `43b18477906ba9790ef3ca555ecfd993da068a35`. The base evidence tag must be absent; if it exists at any commit, stop rather than reuse or move it.

**Files:** `scripts/port_contract.py`, `tests/test_port_contract.py`, `docs/reviews/2026-08-10-issue-63-port-manifest-reconciliation-doc-review.md` (reviewer-owned input; do not edit in implementation), `docs/validation/issue-63-port-manifest-reconciliation-runtime-capability-snapshot.json`, `docs/validation/codex-runtime-capability-snapshot.schema-r4.json`, `docs/portability/ports/2026-08-10-issue-63-port-manifest-reconciliation-version-policy.json`, `docs/portability/ports/2026-08-10-issue-63-port-manifest-reconciliation.json`, `docs/portability/classifications/2026-08-10-issue-63-port-manifest-reconciliation.md`

**Approach:** U1a is the sole pre-gate behavior exception. Implement exact version 1/version 2 dispatch, the closed reconciliation object and normalized row contract, the repository behavior predicate, active/finalized selection through the existing `codex.evidence_ref`, one-way state/ref/ancestry validation, the optional version 2 evidence repository key, and the contract-only empty-version-policy rule. New writes emit version 2.

Version 1 remains byte-readable, rejects `repository`, and requires nonempty policy. Version 2 accepts an explicit `[]` only when source base equals target, source rows are empty, and every reconciliation row is Codex-local. Cover those boundaries with focused tests and commit U1a alone; no resolver execution, issue #57 migration, source-derived change, tag creation, or unrelated behavior is permitted.

U1b immediately self-hosts that substrate. Capture a live authority snapshot and preserve three distinct source facts: ordinary checkout `HEAD` `7f2b98f2ac61431c98d177c25277d287a111aef4`, stale local `origin/main` `1f6c6df4f080247150f489280836e7f4eda4973d`, and live remote `main` `b53827bb055e08ccc6aa547cade04aedf4385456`. Use a disposable detached checkout or temporary clone with normalized origin `infiquetra/infiquetra-claude-plugins` and exact `HEAD` `b53827bb055e08ccc6aa547cade04aedf4385456`; never fetch, switch, clean, or update the ordinary checkout.

Pin that live commit as both source base and target, name only `tools/run_cross_runtime_outcome_acceptance.py` as the source pathspec, and write `[]` to the explicit issue #63 version-policy file. U1b originally captured the issue #63 capability bytes in the shared snapshot; the post-U2 code-review repair restores that shared file byte-for-byte to its accepted Codex 0.147 pre-U1b bytes and writes the already captured issue #63 bytes to `docs/validation/issue-63-port-manifest-reconciliation-runtime-capability-snapshot.json`.

The active issue #63 manifest and classification then bind only that cycle-specific snapshot with the already committed `docs/validation/codex-runtime-capability-snapshot.schema-r4.json`, not the stale unversioned schema path.

Initialize with no unrelated defaults: explicitly pass `--manifest docs/portability/ports/2026-08-10-issue-63-port-manifest-reconciliation.json`, `--port-id issue-63-port-manifest-reconciliation-2026-08-10`, the disposable path through `--source-repo`, `--source-repository-id infiquetra/infiquetra-claude-plugins`, both source refs, every source pathspec, `--codex-plan-base 43b18477906ba9790ef3ca555ecfd993da068a35`, the exact reviewed plan commit through `--codex-execution-base`, `--codex-evidence-ref refs/tags/evidence/issue-63-port-manifest-reconciliation-20260810`, the plan, reviewer artifact, classification path, runbook, `docs/validation/issue-63-port-manifest-reconciliation-runtime-capability-snapshot.json`, `--capability-schema docs/validation/codex-runtime-capability-snapshot.schema-r4.json`, `--codex-repository-id infiquetra/infiquetra-codex-plugins`, and the explicit `[]` version-policy file. Create an active reconciliation with empty evidence and keep the existing safe `codex.evidence_ref` absent. Inventory `execution_base..HEAD`, record every bootstrap behavior path, classify each Codex-local, render, and pass explicit classification validation.

Do not create the evidence tag in U1. No other behavior change is allowed before this gate succeeds.

**Patterns to follow:** `parse_name_status_z`, `git_inventory`, and `normalize_inventory` in `scripts/port_contract.py` provide the normalized rename-aware Git inventory; `_exact_keys` enforces closed objects; and `validate_manifest` is the classification boundary.

**Test scenarios:** Happy paths — version 1 remains readable; new writes emit version 2; the exact contract-only version 2 cycle accepts `[]`; an active cycle with empty evidence, absent safe `codex.evidence_ref`, exact bootstrap rows, and only Codex-local classifications validates against `HEAD`. Edge cases — additions, deletions, and either side of a rename enter the behavior inventory; unloaded planning documentation and tests do not; ordinary source checkout refs remain unchanged. Error paths — version 1 `repository`, version 1 empty policy, non-contract-only version 2 empty policy, a reconciliation `target_ref` or any other unknown field, stale row/digest/count, missing behavior path, active evidence, unsafe or existing evidence ref, finalized-to-active transition, `codex.evidence_ref` change, non-fast-forward candidate, `deferred`/`blocked` changed row, source-checkout mismatch, omitted explicit authority input, or any pre-gate non-bootstrap behavior fails.

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

**Approach:** Implement source-checkout resolution only after U1 passes. Use `CODEX_PORT_SOURCE_REPO` first, otherwise derive the repository-name sibling of the Codex Git common directory from the singular `source.repository_id`. Verify normalized origin and exact `HEAD == source.target_ref` before resolving `cwd: "."` and relative harness paths through realpath containment.

Keep `repo_head` bound to the Codex proof commit. Commit this bounded resolver and its focused tests before changing the active issue #63 reconciliation; immediately update that manifest's reconciliation rows, render its classification, and pass classification validation. That gate must be green before any further behavior, review, evidence recording, or publication.

Do not add evidence in the active cycle, migrate `docs/portability/ports/2026-07-25-codex-627-seam-refreeze.json`, or change `tests/test_codex_627_seam_refreeze_port_contract.py` or any issue #54 record.

**Patterns to follow:** `resolve_port_source_repo` in `tests/conftest.py` contains the established Git-common-directory and normalized-origin source-checkout pattern; `contained_file` in `scripts/port_contract.py` rejects a contained-file symlink escape; `validate_repo_path` and `_validate_evidence_argv` enforce repository-path and evidence-argument safety; and `validate_manifest` is the closed evidence boundary.

**Test scenarios:** Happy path — a version-2 issue #63 evidence selector resolves `python3 tools/run_cross_runtime_outcome_acceptance.py` beneath a Git-verified `infiquetra/infiquetra-claude-plugins` source checkout at the manifest target; both explicit-environment and Git-common-directory sibling resolution work. Edge cases — an omitted selector continues to validate Codex-local evidence unchanged, and a temporary detached worktree at the target commit is accepted. Error paths — `repository` in version 1, an unknown version-2 selector, missing source declaration, missing checkout, origin mismatch, checkout `HEAD` mismatch, absent harness, absolute argument, `..`, cache path, symlink escape, non-root `cwd`, and any other unknown evidence key all fail.

Historical regression scenario — the issue #57 manifest and `tests/test_codex_627_seam_refreeze_port_contract.py` remain byte-for-byte unchanged; the issue #54 manifest and test remain unchanged.

**Verification:** The resolver verifies the source checkout's origin and target commit before the harness resolves inside it, `repo_head` remains the Codex proof subject, and all focused negative revision, containment, and declaration cases fail. Immediately after its behavior commit, the active issue #63 reconciliation represents the resolver and its generated classification passes; no further behavior, review, evidence recording, or publication occurs before that green result. The issue #57 manifest and regression test, and every issue #54 historical record, are byte-for-byte unchanged.

### Post-U2 code-review plan-correction gate

Apply this correction after completed U2 and before any code-review repair work. It is prospective authority for the repair and U3; it does not rewrite U1a, U1b, the post-U1b correction, or U2 history.

**Goal:** Bind the amended plan and one new independent document review to the active issue #63 authority before repairs, while retaining the original review and first re-review exactly once each.

**Dependencies:** The blocked U2 code-review artifact `docs/reviews/2026-08-11-issue-63-port-manifest-reconciliation-code-review.md` is committed provenance. Its findings #1 through #7 are the repair input, but it is not a document-review authority entry.

**Files:** `docs/plans/2026-08-10-issue-63-port-manifest-reconciliation-plan.md`, `docs/reviews/2026-08-11-issue-63-port-manifest-reconciliation-code-review-plan-correction-review.md` (new independent Saga document review; reviewer-owned input; do not create or edit in implementation), `docs/portability/ports/2026-08-10-issue-63-port-manifest-reconciliation.json`, and `docs/portability/classifications/2026-08-10-issue-63-port-manifest-reconciliation.md`

**Approach:** This amended plan must first receive the new independent Saga document review at `docs/reviews/2026-08-11-issue-63-port-manifest-reconciliation-code-review-plan-correction-review.md`. Only after that review is complete may the active issue #63 manifest replace its plan digest with the amended plan digest and append that new review path and digest exactly once. Preserve the original document review and the first plan re-review exactly once each.

Render the classification and pass explicit classification validation before any code fix. Do not append the blocked code-review artifact to `authority.reviews`.

**Verification:** Before repair work begins, the active issue #63 manifest has the amended plan digest and the original review, first re-review, and code-review plan-correction review each once. The blocked code-review artifact is committed provenance only, no classification input is stale, and explicit classification validation exits zero.

### Post-U2 code-review repairs

Repair the independently reviewed U2 branch only after the post-U2 code-review plan-correction gate is green.

**Goal:** Correct the shared-snapshot overwrite, complete the existing behavior and finalized-lifecycle contract, add the missing integrated proof, and remove formatter-only churn without expanding the issue #63 design.

**Requirements:** R3, R4, R5, R8, R10

**Files:** `scripts/port_contract.py`, `tests/test_port_contract.py`, `docs/validation/codex-runtime-capability-snapshot.json`, `docs/validation/issue-63-port-manifest-reconciliation-runtime-capability-snapshot.json`, `docs/portability/ports/2026-08-10-issue-63-port-manifest-reconciliation.json`, and `docs/portability/classifications/2026-08-10-issue-63-port-manifest-reconciliation.md`

**Approach:** Restore `docs/validation/codex-runtime-capability-snapshot.json` byte-for-byte to its accepted Codex 0.147 pre-U1b bytes. Leave `docs/validation/verified-workflows-runtime-proof.json` unchanged. Write the already captured issue #63 bytes to `docs/validation/issue-63-port-manifest-reconciliation-runtime-capability-snapshot.json` using the existing schema-r4 file, then rebind only the issue #63 manifest and classification to that dedicated artifact.

Do not rewrite the Codex 0.147 manifest, tests, or proof, and do not rewrite any issue #54 or issue #57 history.

Extend the existing behavior predicate and its focused tests for every current concrete surface from finding #2: plugin agents; the whole `plugins/discord-identity-assets/references/`, `plugins/python-toolkit/references/`, and `plugins/saga/references/rubrics/` roots; `plugins/hermes-profile-evolution/conformance/profile-change-classifier.v1.json`; `plugins/hermes-profile-evolution/conformance/profile-request-cli.v1.json`; `.agents/plugins/marketplace.json`; and `.codex/config.toml`.

Also select exactly `plugins/saga/references/bridge-signatures.json`, `plugins/saga/references/effort-policy.yaml`, `plugins/saga/references/engine-dispatch.md`, `plugins/saga/references/engine-registry.yaml`, `plugins/saga/references/formatting-style.md`, `plugins/saga/references/model-releases.yaml`, `plugins/saga/references/operator-choice.md`, `plugins/saga/references/outcome-cross-runtime.md`, `plugins/saga/references/outcome-spec.md`, and `plugins/saga/references/saga-spec.md`. Preserve the existing add, delete, and rename coverage for those categories.

Do not select `plugins/hermes-profile-evolution/conformance/provenance.json`, every directory named `references`, all conformance files, unreferenced reference prose, or speculative roots.

Keep active authority checks against current files, but for finalized version 2 validation read the plan, reviews, runbook, capability snapshot, and other recorded authority artifacts as digest-bound historical bytes at the immutable evidence candidate. Require finalized evidence to be nonempty, and once finalized require every evidence entry to remain byte-equivalent. Freeze `source.repository_id`, `source.base_ref`, `source.target_ref`, `codex.repository_id`, `codex.historical_plan_base`, and `codex.execution_base` across every version-2 transition.

Add the integrated active-to-finalized/source-evidence/stability test: it must prove active initialization, a committed Codex evidence subject, finalization with explicit declared-source evidence, tag-selected validation through `validate_manifest`, rejection of each pinned-authority mutation, and continued validity after an unrelated later `HEAD` commit.

Restore pre-existing formatting for definitions whose syntax is unchanged. Retain formatting changes only where a semantic edit requires them. Keep the root-level command concern without a slash suppressed, and add no root registry, speculative path rule, hardening, or other new machinery.

Immediately after the repair commit or commits, update the active issue #63 reconciliation for every newly selected behavior path, render the classification, and pass explicit classification validation before independent code re-review. Run focused contract and affected Codex 0.147 checks separately. Restoring the shared snapshot must make the existing verified-workflows runtime proof current without regenerating it.

At this boundary, legacy-inventory drift alone may remain; U3 owns that regeneration and must make the full suite green before candidate freeze.

**Verification:** The shared snapshot exactly matches its accepted Codex 0.147 pre-U1b bytes; the verified-workflows runtime proof is unchanged and valid again; the new issue #63 snapshot contains the already captured issue #63 bytes and uses schema r4; and only the issue #63 manifest and classification are rebound. All selected concrete runtime paths appear exactly once in the active reconciliation, finalized validation uses frozen digest-bound authority bytes, evidence is nonempty and immutable after finalization, and all six pinned source/Codex fields reject mutation. The integrated test proves the active-to-finalized declared-source path and later-`HEAD` stability.

The post-repair active manifest/classification reconciliation is rendered and validates before an independent code re-review. No Codex 0.147 manifest/test/proof or issue #54/#57 historical record changes. The repair review sees no formatter-only churn in unchanged definitions.

### Pre-U3 runbook-version correction gate

Correct the reviewed U3 authority prospectively before any U3 file changes.

**Goal:** Bind the corrected U3 file, version, review, and acceptance contract without changing completed U1, U2, repair work, or the completed repair review.

**Requirements:** R8, R10, R11, R12

**Dependencies:** The post-U2 repair is complete at code commit `e40688b263996dda4170a2cae0ac8be51544b2b3`, and its completed independent code review remains provenance at `docs/reviews/2026-08-11-issue-63-port-manifest-reconciliation-code-review.md`. Root must update the live issue #63 expected-files and acceptance language for runbook version 6, the exact contract/test changes, both live-authority bindings, the four-review authority count, the all-green pre-evidence gate, the fresh U3 code review, and the fixed evidence `repo_head` before the manifest rebind.

**Files:** `docs/plans/2026-08-10-issue-63-port-manifest-reconciliation-plan.md`, `docs/reviews/2026-08-11-issue-63-u3-runbook-version-plan-correction-review.md` (new independent Saga document review; reviewer-owned input; do not create or edit in implementation), `docs/portability/ports/2026-08-10-issue-63-port-manifest-reconciliation.json`, and `docs/portability/classifications/2026-08-10-issue-63-port-manifest-reconciliation.md`; live GitHub issue #63 (Root-owned external authority; Root performs this mutation separately)

**Approach:** This plan-only correction does not alter the authority that governed U1, U2, the post-U2 repair, or its completed code review. After Root updates and reads back the live issue, an independent reviewer must review this corrected plan through the Saga document-review workflow and write `docs/reviews/2026-08-11-issue-63-u3-runbook-version-plan-correction-review.md`.

Only after both gates pass may the active issue #63 manifest replace its plan digest with this corrected plan digest and append the new document-review path and digest exactly once. Render the issue #63 classification and pass explicit active classification validation before U3 resumes.

At this completed boundary, the four document-review authority entries are the original review, the first plan re-review, the post-U2 code-review plan-correction review, and the new U3 runbook-version plan-correction review. Preserve each exactly once, and keep both the completed U2 code-review artifact and the future U3 code-review artifact out of `authority.reviews`; the later evidence-scope correction gate adds the fifth document review prospectively.

**Verification:** Live issue #63 readback contains the corrected expected files and acceptance language before the authority rebind. At this completed boundary, the active issue #63 manifest binds the corrected plan digest, contains exactly four document-review authority entries at their exact digests, and produces a current classification that passes explicit active classification validation before U3 begins.

### Pre-finalization evidence-scope correction gate

Correct the U3 evidence claim after the pinned full harness halts, without reopening the reviewed code candidate.

**Goal:** Preserve the failed full-harness run as a non-evidence divergence receipt, authorize a separate declared-source command-resolution receipt, and bind that narrower claim before finalization.

**Requirements:** R7, R8, R10, R12, R13

**Dependencies:** The active U3 code candidate remains commit `bece5ab`, and its clean independent code review remains commit `dd9209740656f35831223e8f8652b37bd74de315`. The untracked failed bundle at `docs/validation/issue-63-port-manifest-reconciliation-u3-source-harness.json` retains SHA-256 `1a83196f6c30a784117dff56702328f7243388deb2a060557eb03fc44c7056e1` and `overall_verdict` `halt`.

**Files:** `docs/plans/2026-08-10-issue-63-port-manifest-reconciliation-plan.md`, `docs/reviews/2026-08-11-issue-63-u3-evidence-scope-plan-correction-review.md` (new independent Saga document review; reviewer-owned output), `docs/portability/ports/2026-08-10-issue-63-port-manifest-reconciliation.json`, and `docs/portability/classifications/2026-08-10-issue-63-port-manifest-reconciliation.md`; live GitHub issue #63 (Root-owned external authority; Root performs this mutation separately)

**Approach:** Root first updates and reads back live issue #63 so its expected artifacts and acceptance language distinguish the failed divergence receipt from the successful declared-source command-resolution receipt. The update must retain declared-source origin, exact-target, containment, fixed evidence `repo_head` `e40688b263996dda4170a2cae0ac8be51544b2b3`, issue #57 historical immutability, and the absence of any byte-for-byte Claude-mirroring requirement.

An independent reviewer then reviews this corrected plan through the Saga document-review workflow and writes `docs/reviews/2026-08-11-issue-63-u3-evidence-scope-plan-correction-review.md`. Only after the review reports `blocked=false` may the active issue #63 manifest bind this corrected plan digest and append that fifth document-review path and digest exactly once.

Render the issue #63 classification and pass explicit active classification validation before any command-resolution evidence or finalization. Keep both code-review artifacts out of `authority.reviews`; the existing active-state U3 code review does not repeat unless code, tests, or a selected behavior path changes.

**Verification:** Live issue #63 readback contains the corrected evidence scope; the new reviewer artifact reports `blocked=false`; and the active manifest binds the corrected plan digest with exactly five document-review entries, each once. The rendered classification validates while active, both code-review artifacts remain provenance only, and no code, test, behavior-path, evidence, manifest, or tag mutation precedes this gate.

### U3. Document, finalize, and prove the frozen candidate

Finish the contract change with durable procedure, immutable evidence, and merge-time proof.

**Goal:** Advance the complete runbook version contract, document the bootstrap and lifecycle, produce the reviewed final candidate, create and narrowly publish its evidence tag exactly once, prove finalized validation from a clean checkout, and prove the PR merge ref and actual merge retain the frozen behavior inventory.

**Requirements:** R3, R5, R7, R8, R9, R10, R11, R12, R13

**Dependencies:** U2; the post-U2 code-review plan-correction and repair gates; the pre-U3 runbook-version correction gate; the pre-finalization evidence-scope correction gate; and the independent document reviews at `docs/reviews/2026-08-11-issue-63-port-manifest-reconciliation-plan-re-review.md`, `docs/reviews/2026-08-11-issue-63-port-manifest-reconciliation-code-review-plan-correction-review.md`, `docs/reviews/2026-08-11-issue-63-u3-runbook-version-plan-correction-review.md`, and `docs/reviews/2026-08-11-issue-63-u3-evidence-scope-plan-correction-review.md`. Root's corrected live issue #63 readback, the corrected plan binding, all five document-review authority entries, the active issue #63 classification, focused repair tests including affected Codex 0.147 checks, and the completed repair re-review must be current before finalization proceeds.

Only the already-attributed legacy-workflow inventory and digest drift may remain at entry. U3 must regenerate that inventory, rotate its digest binding, and make the plugin validator and full suite green as separate results before candidate freeze, evidence candidate capture or finalization, tag creation, or any PR.

**Files:** `docs/portability/claude-to-codex-plugin-port-runbook.md`, `scripts/port_contract.py`, `tests/test_port_runbook.py`, `docs/portability/ports/2026-08-10-issue-63-port-manifest-reconciliation.json`, `docs/portability/classifications/2026-08-10-issue-63-port-manifest-reconciliation.md`, `docs/portability/ports/2026-08-08-codex-0147-alignment.json`, `docs/portability/classifications/2026-08-08-codex-0147-alignment.md`, `docs/validation/issue-63-port-manifest-reconciliation-u3-source-harness.json`, `docs/validation/issue-63-port-manifest-reconciliation-u3-source-command-resolution.json`, `docs/reviews/2026-08-11-issue-63-port-manifest-reconciliation-plan-re-review.md`, `docs/reviews/2026-08-11-issue-63-port-manifest-reconciliation-code-review-plan-correction-review.md`, `docs/reviews/2026-08-11-issue-63-u3-runbook-version-plan-correction-review.md`, and `docs/reviews/2026-08-11-issue-63-u3-evidence-scope-plan-correction-review.md` (reviewer-owned inputs; do not edit in implementation), `docs/reviews/2026-08-11-issue-63-port-manifest-reconciliation-u3-code-review.md` (completed independent Saga code review; reviewer-owned input), `docs/engineering-journal/DECISIONS.md`, `docs/validation/verified-workflows-legacy-token-inventory.json`, and `scripts/validate_codex_plugins.py`

**Approach:** Update the runbook and journal to explain the reviewed bootstrap exception, immediate self-host gate, active `HEAD` versus finalized tag target, narrow `[]` policy, absent-then-immutable tag, candidate attempts, PR merge-ref proof, and issue #63-before-#61/#62 serialization. Bump the runbook metadata from 5 to 6 because U3 changes its content.

In `scripts/port_contract.py`, make only `RUNBOOK_VERSION = 6` and `SUPPORTED_RUNBOOK_VERSIONS = {3, 4, 5, RUNBOOK_VERSION}`. In `tests/test_port_runbook.py`, update the exact version expectation to 6 and assert current version 6 with historical support `{3, 4, 5, 6}`; do not add the optional generic cross-file drift assertion or any other hardening.

Rebind only the issue #63 and Codex 0.147 alignment manifests to runbook version 6 and the new SHA-256, then render `docs/portability/classifications/2026-08-10-issue-63-port-manifest-reconciliation.md` and `docs/portability/classifications/2026-08-08-codex-0147-alignment.md`. Preserve every finalized or historical version-5 contract and leave `docs/validation/verified-workflows-runtime-proof.json` unchanged.

Preserve the original review, first re-review, post-U2 code-review plan-correction review, U3 runbook-version plan-correction review, and U3 evidence-scope plan-correction review exactly once each in the issue #63 document-review authority. Do not append any of them again during U3.

The completed U2 code-review artifact remains committed provenance and never becomes a document-review authority entry. The completed U3 code-review artifact is also review provenance rather than document-review authority.

After the final journal edit, regenerate the historical inventory and rotate only its expected digest constant and adjacent reason comment. While the issue #63 manifest is still active and evidence is empty, run the focused port-contract and runbook-version tests, inventory check, both active/live-authority classification validations, plugin validation, and the full suite as separate results.

All those active-state gates must be green before declared-source command-resolution evidence or finalization. The completed independent Saga code review of active-state U3 candidate `bece5ab` remains valid at `docs/reviews/2026-08-11-issue-63-port-manifest-reconciliation-u3-code-review.md`, with clean review commit `dd9209740656f35831223e8f8652b37bd74de315`. Do not repeat that code review unless code, tests, or a selected behavior path changes; if one does, close every P0-P3 finding, rerender both classifications, rerun every affected check, and repeat independent review until no finding remains.

Before freezing, compare current `main` with `43b18477906ba9790ef3ca555ecfd993da068a35`. The newly merged reusable-bootstrap document is documentation-only, is excluded from behavior reconciliation, and does not require this cycle to rebase beyond `43b1847`; the reviewed plan commit must retain that exact parent. If later `main` gains any behavior-bearing path, stop and return to candidate review.

If integration requires a rebase and the intervening changes are documentation-only, perform it only before candidate freeze, repeat review and all gates, and do not silently replace the manifest's reviewed execution base. Serialize integration so issue #63 lands before issue #61 or #62 behavior branches.

Preserve `docs/validation/issue-63-port-manifest-reconciliation-u3-source-harness.json` unchanged with SHA-256 `1a83196f6c30a784117dff56702328f7243388deb2a060557eb03fc44c7056e1`. It is a non-evidence divergence receipt: the pinned full harness exited 2 before scenarios with `overall_verdict` `halt` and halt code `port-digest` because Claude and Codex intentionally implement different broker protocols. Do not reclassify it as green, add it to manifest evidence, or require this issue to make that harness pass.

Only after the evidence-scope correction gate and active-state checks pass, use the verified disposable Claude checkout at detached `HEAD` `b53827bb055e08ccc6aa547cade04aedf4385456` to run exactly `python3 tools/run_cross_runtime_outcome_acceptance.py --help`. Write `docs/validation/issue-63-port-manifest-reconciliation-u3-source-command-resolution.json` with normalized origin `infiquetra/infiquetra-claude-plugins`, the exact detached `HEAD`, the contained harness path, Git blob `7c6c9aac411ec2a119b45e77558298846e7ee7b5`, size 99,980 bytes, argv exactly `["python3", "tools/run_cross_runtime_outcome_acceptance.py", "--help"]`, a timezone-aware recorded time, and exit 0.

The successful receipt must state that it is command-resolution evidence rather than cross-runtime acceptance and must reference the failed receipt path and SHA-256 without changing its verdict. Add one issue #63 evidence entry with `repository: "source"`, `cwd: "."`, argv exactly `["python3", "tools/run_cross_runtime_outcome_acceptance.py", "--help"]`, the successful receipt, and exactly `e40688b263996dda4170a2cae0ac8be51544b2b3` as `repo_head`. For each disposable clean-checkout validation, explicitly set `CODEX_PORT_SOURCE_REPO` to that exact-target Claude checkout; do not rely on sibling discovery.

This truthful revalidation supersedes only the old issue #57 command-location claim. It must not add evidence to, migrate, finalize, or otherwise rewrite the issue #57 version-1 manifest or its regression test.

Keep the completed repair code commit `e40688b263996dda4170a2cae0ac8be51544b2b3` as the evidence subject; do not substitute a U3 version-contract, documentation, review, or binding commit. Populate every issue #63 evidence row's `repo_head` with that exact commit. Change the issue #63 reconciliation from active to finalized without changing `codex.execution_base`; commit the finalized manifest, classification, both U3 receipts, runbook, journal, generated inventory, and digest binding as the candidate.

Confirm the base evidence tag is still absent only after the existing clean U3 code review remains applicable, the evidence-scope correction gate passes, and all applicable checks are green. Create the first local evidence tag exactly once at that candidate, and validate that the tagged history contains the execution base and `e40688b263996dda4170a2cae0ac8be51544b2b3`. Finalized validation resolves the tag and remains stable when later `HEAD` changes.

After local finalized validation succeeds, push only `refs/tags/evidence/issue-63-port-manifest-reconciliation-20260810` to the same exact ref on `origin`, without force and without pushing a branch or any other tag. Read `origin` back using that exact ref and require its object ID to equal the frozen candidate. Fetch only that exact remote ref into a disposable clean checkout and run finalized-manifest validation there, proving a fresh clone or CI can resolve all frozen history without local-only refs.

Stop before PR creation if local validation, the non-force push, exact-ref remote readback, exact-ref fetch, or clean-checkout validation fails. Once published remotely, never move or delete the tag. A changed candidate repeats this sequence only with a reviewed `-attempt-N` evidence ref; do not add a release workflow, generic tag manager, or other publication machinery.

Open the PR only after the tagged candidate is valid. Fetch and inspect GitHub's PR merge ref immediately before merge. Require its normalized reconciliation inventory to match the frozen candidate, then use a read-only Git comparison over the deterministic behavior-path selection to prove identical presence, mode, and blob content for every selected path; allow documentation-only paths to differ.

If any behavior path, merge ref, or candidate changes, return to candidate review, rerun all checks, and freeze a new `-attempt-N` tag without moving or deleting any published tag. After merge, read back the actual merge commit and repeat both the inventory and selected-path content comparisons against the frozen candidate before closeout. Historical validation continues to use the frozen `codex.evidence_ref`, never merge-time or later `HEAD`.

Do not store a behavior-tree digest or add another evidence format.

**Patterns to follow:** `build_manifest` in `scripts/port_contract.py` binds authority artifact bytes; `validate_port_contract` in `scripts/validate_codex_plugins.py` delegates repository port validation; and `main` in that validator returns the process result.

**Test scenarios:** Happy path — the runbook reports version 6; the contract reports current version 6 and supports exactly `{3, 4, 5, 6}`; and the focused test asserts both facts. Only the issue #63 and Codex 0.147 alignment manifests bind version 6 and the new digest, both classifications are rendered, every finalized or historical version-5 contract remains unchanged, and the existing Codex 0.147 runtime proof remains unchanged.

The corrected active issue #63 authority contains exactly five document reviews, while both code-review artifacts remain provenance only. The existing clean independent Saga code review remains valid because the correction changes no code, tests, or selected behavior path, and every active-state check passes before command-resolution evidence or finalization.

The failed full-harness receipt retains its exact halt verdict and digest as non-evidence. The separate successful receipt proves normalized declared-source origin, detached exact target, contained harness path, pinned blob and size, exact `--help` argv, timezone-aware time, and exit 0; it identifies itself as command-resolution evidence rather than cross-runtime acceptance and references the failed receipt without reclassifying it.

The finalized issue #63 manifest resolves the immutable `codex.evidence_ref`, reproduces the frozen behavior rows and digest, contains the execution base and evidence commit `e40688b263996dda4170a2cae0ac8be51544b2b3`, validates digest-bound historical authority bytes and only the successful `repository: "source"` command-resolution evidence from a disposable clean checkout with `CODEX_PORT_SOURCE_REPO` explicitly set, and survives exact non-force publication/readback and unrelated later `HEAD` changes. The PR merge ref and actual merge have identical selected-path presence, mode, and blobs despite allowed documentation differences; focused, plugin, and full checks pass and are reported separately, with the full suite green.

Edge cases — documentation-only main changes remain excluded; the known reusable-bootstrap document does not force a rebase beyond `43b1847`; issue #54 and issue #57 historical records remain unchanged. Historical runbook versions 3, 4, and 5 remain accepted without rebinding their finalized or historical contracts. Claude commit `b727fa5c8a0418d1fcbff6d67893b3a05683e93c` and its coupled `outcome_compat.py`, `outcome.py`, test, reference, and skill behavior remain outside this cycle.

Error paths — a runbook version other than 6, a support set other than `{3, 4, 5, 6}`, an extra port-contract behavior change, optional generic drift hardening, a missed or extra version-6 manifest rebind, stale classification, changed historical contract, changed runtime proof, fewer or more than five document-review authority entries, a code-review artifact in `authority.reviews`, unresolved P0-P3 finding, or nonzero active-state result blocks command-resolution evidence and finalization. A changed or missing failed-receipt digest, a failed receipt presented as green or manifest evidence, a successful receipt that omits the declared origin, detached exact target, containment, pinned blob or size, exact argv, timezone-aware time, exit 0, command-resolution disclaimer, or failed-receipt reference also blocks progression. A pre-existing base tag, missing finalized tag, tag/candidate mismatch, finalized-to-active transition, evidence-ref change, evidence mutation or emptiness, pinned source/Codex authority mutation, non-fast-forward candidate, wrong evidence `repo_head`, missing or wrong `CODEX_PORT_SOURCE_REPO`, local finalized-validation failure, rejected push, remote ref mismatch, exact-ref fetch failure, clean-checkout validation failure, changed behavior inventory, selected behavior path missing or changed in mode/blob, behavior-bearing main drift, or any other nonzero validation result blocks progression.

Retry path — close every document-review finding, rerender the issue #63 classification, and repeat affected active checks before command-resolution evidence proceeds. Repeat code review only if code, tests, or a selected behavior path changes. Preserve every published tag and require a reviewed attempt-suffixed tag after a changed finalization candidate.

**Verification:** The runbook metadata is 6; `scripts/port_contract.py` contains only the required version-constant change; and `tests/test_port_runbook.py` proves current version 6 with historical support `{3, 4, 5, 6}`. The issue #63 and Codex 0.147 alignment manifests alone bind the new runbook digest and version, both classifications are current, finalized and historical version-5 contracts are unchanged, and the existing Codex 0.147 runtime proof is unchanged.

The original review, first re-review, post-U2 code-review plan-correction review, U3 runbook-version plan-correction review, and U3 evidence-scope plan-correction review authority entries are each present exactly once. The completed U2 and U3 code-review artifacts are not authority entries, the existing U3 review remains clean, and every applicable active-state gate is green before command-resolution evidence and finalization.

The runbook, finalized tagged issue #63 manifest, classification, failed divergence receipt, successful command-resolution receipt, decision journal, generated inventory, and digest binding agree. The failed receipt retains SHA-256 `1a83196f6c30a784117dff56702328f7243388deb2a060557eb03fc44c7056e1` and its halt verdict outside manifest evidence; the successful receipt carries the exact `--help` proof and references that failure without reclassification. Every evidence `repo_head` equals `e40688b263996dda4170a2cae0ac8be51544b2b3`. The exact remote evidence ref resolves to the frozen candidate and finalized-manifest validation passes from a disposable clean checkout with `CODEX_PORT_SOURCE_REPO` explicitly set before PR creation.

The PR merge ref and actual merge readback preserve the normalized inventory and every selected behavior path's presence, mode, and blob content while permitting documentation-only differences. Focused, plugin-validator, and full-suite exit codes remain separate, and the full suite is green. No release workflow, generic tag manager, behavior-tree digest, second manifest, attribution/suppression system, compatibility database, repository registry, evidence-chain format, or control plane appears.

---

## Risks and Dependencies

The bootstrap exception is the main sequencing risk. U1a is restricted to the version 2 substrate and focused tests, lands as its own commit, and is immediately inventoried by U1b from the reviewed plan execution base. Any companion, source-derived, or unrelated behavior in that pre-gate commit invalidates the exception.

This plan depends on a Git-verifiable disposable source checkout for the issue #63 command-resolution proof. The validator must fail with one actionable repository-identity, revision, or containment error when that checkout is unavailable; clean-checkout validation explicitly sets `CODEX_PORT_SOURCE_REPO` and must not fall back to the preserved ordinary source checkout.

The failed full harness can be mistaken for an issue #63 defect or a green acceptance artifact. Preserve its exact bytes, digest, halt verdict, and zero-scenario result as a non-evidence divergence receipt; use only the separate exact-target `--help` receipt as manifest evidence, and never describe that narrower proof as cross-runtime acceptance.

The behavior-path predicate is the main completeness risk. The repair pins every currently selected runtime category and rename direction with negative fixtures so a future root addition requires an explicit reviewed predicate/test change rather than silently escaping the gate. It does not preselect speculative roots.

The active-to-finalized transition crosses an intentionally absent `codex.evidence_ref`. U3 commits the finalized candidate before creating that tag, so final historical validation cannot succeed until the one-time tag exists; any failure after publication preserves that tag and starts a reviewed attempt with a new suffix.

Local tag validation is not portable proof. U3 treats exact non-force publication, remote object-ID readback, exact-ref fetch, and disposable clean-checkout finalized validation as a single fail-closed boundary before PR creation. A partial failure stops; it never broadens the push, force-updates the ref, or substitutes local state for remote resolvability.

Concurrent mainline behavior is an integration risk. The known reusable-bootstrap document is excluded and does not move the cycle beyond `43b1847`; any later behavior-bearing change stops candidate preparation. Issue #63 lands before issue #61 or #62 behavior branches so the PR merge-ref comparison is not racing another port-contract change.

Changing the canonical runbook invalidates its live digest bindings. U3 updates the runbook version and both live manifest/classification pairs together; finalized historical validation thereafter uses its immutable tag and recorded runbook bytes.

The runbook content change also invalidates the Codex 0.147 live-authority binding. U3 advances the version constants and exact test expectations, rebinds only the issue #63 and Codex 0.147 manifests, renders both classifications, and leaves every finalized or historical version-5 contract and the existing runtime proof unchanged.

The prospective evidence-scope authority correction is an ordering risk. Root's live issue update and readback, the independent Saga document review with `blocked=false`, the corrected plan digest, the fifth document-review authority entry, and green active issue #63 classification must all exist before command-resolution evidence or finalization; neither code-review artifact may enter document-review authority.

The U3 version-contract edits created a code-review boundary that is already clean at review commit `dd9209740656f35831223e8f8652b37bd74de315`. This plan-only evidence-scope correction does not reopen it; a fresh independent Saga code review is required only if code, tests, or a selected behavior path changes before command-resolution evidence, finalization, or the first local evidence tag.

`docs/engineering-journal/DECISIONS.md` is part of the generated legacy-workflow inventory. Planning regenerates and checks that inventory so the required KTD record does not leave document validation stale.

---

## Scope Boundaries

The implementation is limited to same-manifest branch-diff completeness and one source-repository evidence selector.

**Non-goals:** A second port manifest for the same cycle; a validation-attribution subsystem; `tests/test_validation_attribution.py`; a checked-in suppression baseline; automatic semantic classification; a repository registry; arbitrary absolute or traversing evidence paths; a compatibility database; an evidence-chain format; a port control plane; byte-for-byte Claude mirroring; a requirement that the full cross-runtime harness pass; a new cutover release-proof path; or an exhaustive provider/model/role/platform matrix.

Porting Claude commit `b727fa5c8a0418d1fcbff6d67893b3a05683e93c` is explicitly out of scope. That includes its coupled changes to `plugins/saga/scripts/outcome_compat.py`, `plugins/saga/scripts/outcome.py`, `tests/test_cross_runtime_acceptance.py`, `tests/test_outcome_cross_runtime_contract.py`, `tests/test_saga_outcome_compat.py`, `plugins/saga/references/outcome-cross-runtime.md`, `plugins/saga/skills/outcome/SKILL.md`, and the associated journal and work-session behavior.

**Historical evidence only:** Issue #54, its merged lease-registry implementation, its acceptance artifacts, `docs/portability/ports/2026-07-26-lease-registry-forward-compat.json`, and unknown-field compatibility behavior remain unchanged. The version-1 issue #57 manifest `docs/portability/ports/2026-07-25-codex-627-seam-refreeze.json` and `tests/test_codex_627_seam_refreeze_port_contract.py` remain byte-for-byte unchanged; the intentionally absent `refs/tags/evidence/codex-627-seam-refreeze-20260725` is not backfilled.

Every finalized or historical contract that records runbook version 5 keeps version 5 and its recorded digest. Only the issue #63 and Codex 0.147 live-authority contracts advance to version 6, and the existing Codex 0.147 runtime proof remains unchanged.

**Deferred to follow-up work:** Any general multi-repository evidence model, more than one companion repository, redesign of the existing cutover release-proof verifier, changed-versus-unchanged failure attribution, or a separately reviewed port of the broker-settlement and successor-handoff retirement needed to restore cross-runtime behavioral parity.

---

## Sources and Grounding

The plan follows the capability-first port requirements and acceptance examples in `docs/brainstorms/2026-07-26-codex-plugin-lifecycle-simplification-requirements.md`, and the mandatory gate ordering in `docs/portability/claude-to-codex-plugin-port-runbook.md`.

The canonical runbook currently declares version 5 and requires a content change to update its version and every active contract. `scripts/port_contract.py` currently sets version 5 with historical support for versions 3 and 4, while `tests/test_port_runbook.py` expects version 5; U3 advances those exact surfaces to current version 6 with historical support for versions 3, 4, and 5.

Current code derives inventories only over declared pathspecs through `git_inventory`, accepts the existing source and Codex treatment sets through `SOURCE_TREATMENTS` and `CODEX_TREATMENTS`, rejects unsafe argument paths through `_validate_evidence_argv`, and fixes evidence execution to the local root through `validate_manifest` in `scripts/port_contract.py`. The missed `outcome_decompose.py` path and its mechanism are recorded in `docs/engineering-journal/LEARNINGS.md`.

Live issue #57 requires a declared companion repository and a recorded command path that resolves instead of producing `ENOENT`. It does not require issue #63 to prove current cross-runtime behavioral acceptance. Its historical manifest records `tools/run_cross_runtime_outcome_acceptance.py` with local `cwd: "."` in `docs/portability/ports/2026-07-25-codex-627-seam-refreeze.json`; its evidence ref `refs/tags/evidence/codex-627-seam-refreeze-20260725` was intentionally never created, so the record remains a byte-for-byte version-1 regression artifact rather than a version-2 migration target.

The issue #54 port and its 14-of-14 follow-up acceptance landed in commits `ec523cc` and `f63ee82`; those commits establish accepted history, not current implementation scope.

Live issue #63 requires declared-source origin, exact target, containment, and fixed evidence `repo_head` `e40688b263996dda4170a2cae0ac8be51544b2b3`; it explicitly excludes byte-for-byte Claude mirroring. Read-only verification at source commit `b53827bb055e08ccc6aa547cade04aedf4385456` confirms that `tools/run_cross_runtime_outcome_acceptance.py` remains present with Git blob `7c6c9aac411ec2a119b45e77558298846e7ee7b5` and size 99,980 bytes. The three commits after stale local `origin/main` change only Hermes profile-evolution documentation, metadata, timeout behavior, and their tests; none changes the harness.

The pinned full harness run against Claude `b53827bb055e08ccc6aa547cade04aedf4385456` and Codex `e40688b263996dda4170a2cae0ac8be51544b2b3` exited 2 before scenarios. Its preserved bundle has SHA-256 `1a83196f6c30a784117dff56702328f7243388deb2a060557eb03fc44c7056e1`, `overall_verdict` `halt`, and halt code `port-digest` because `outcome_compat.py` copies diverge beyond `RUNTIME_LABEL`.

Claude commit `b727fa5c8a0418d1fcbff6d67893b3a05683e93c` deliberately retired broker settlement and successor handoff across `outcome_compat.py`, `outcome.py`, tests, `plugins/saga/references/outcome-cross-runtime.md`, and `plugins/saga/skills/outcome/SKILL.md`. Codex retains the earlier broker protocol. That explains the divergence receipt but does not expand this contract-only cycle into a multi-file behavior port.

The reviewed active U3 code candidate remains `bece5ab`, and clean code-review commit `dd9209740656f35831223e8f8652b37bd74de315` remains valid for that code. The prospective correction changes only the evidence claim and authority chain; code review repeats only if code, tests, or a selected behavior path changes.

Read-only local ref inspection during planning confirmed that `refs/tags/evidence/issue-63-port-manifest-reconciliation-20260810` is absent. That observation is not durable authority: U1 and U3 each recheck absence at their own boundary and fail if any commit has acquired the ref.
