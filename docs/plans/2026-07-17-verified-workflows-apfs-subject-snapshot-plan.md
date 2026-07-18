---
title: Fix Verified Workflows APFS Subject Snapshot Continuity
type: fix
status: active
date: 2026-07-17
deepened: 2026-07-17
---

# Fix Verified Workflows APFS Subject Snapshot Continuity

## Summary

Repair the protected outside-scope workspace projection so an authorized new file or directory can advance a subject chain on APFS without weakening detection of unauthorized workspace changes. Ship the correction as a Verified Workflows patch release, install it through the supported plugin path, and use it to restart only the failed workflow run for Claude Plugins issue #357 while preserving the existing outcome leaf and implementation.

## Problem Frame

Verified Workflows records an outside-scope digest by excluding authorized subject paths from a whole-workspace snapshot (`plugins/verified-workflows/scripts/workspace_evidence.py:667`). The snapshot still hashes raw directory `st_nlink` metadata (`plugins/verified-workflows/scripts/workspace_evidence.py:1231`, `plugins/verified-workflows/scripts/workspace_evidence.py:1278`).

On APFS, a directory link count changes when an immediate file is added. Adding an authorized file therefore changes the digest through its parent directory even though the file itself is excluded, and `create_subject_record()` rejects the descendant as outside-scope drift (`plugins/verified-workflows/scripts/workspace_evidence.py:694`). The issue #357 run reproduced this with equal outside-scope file count, byte count, repository identity, and Git-control digest; only the metadata-sensitive tree digest changed.

The active issue #357 parent subject was recorded with the old projection and carries no projection-algorithm version or entry manifest. It cannot be migrated into a new digest chain without inventing evidence. The prior run must remain as failed audit evidence while one replacement workflow run replays the preserved implementation from its clean baseline; this is a workflow-run replacement, not a new outcome dispatch or issue leaf.

## Requirements

R1. A subject that authorizes a missing exact file beneath an existing parent directory must permit that file to be created and recorded in a descendant subject on APFS and Linux when no outside-scope state changes. Missing intermediate parent directories remain outside the exact-file authorization.

R2. A subject that authorizes a missing directory beneath an existing parent directory must permit the directory and its contents to be created and recorded in a descendant subject on APFS and Linux when no outside-scope state changes.

R3. Unauthorized sibling files, sibling directories, mode changes, symlinks, inode replacements, hardlinks, ignored files, and Git-control mutations must continue to change or invalidate the applicable protected evidence.

R4. Link normalization must apply only to the immediate lexical parent directory entry of each excluded subject path, including `.` for a top-level exclusion. Full workspace snapshots, higher ancestors, and unrelated directories must retain raw link metadata.

R5. Existing protected-record schemas remain readable. The fix must not reinterpret an old parent digest as a new digest or claim that the failed issue #357 chain advanced.

R6. Verified Workflows ships as patch version `1.0.2+codex.<release timestamp>` generated from one UTC release timestamp, with all 12 version-bearing release surfaces, generated target inventory/facts, portability status, and engineering-journal truth aligned.

R7. The supported install path must produce source-to-installed-cache parity for the manifest and repaired snapshot implementation. Maintained source is changed in this repository; installed cache files are never edited directly.

R8. The existing `lease-safe-runtime-continuity` outcome keeps its current issue #357 leaf and dispatch identity. Before replacement, the preserved implementation is inventoried with base revision, Git status, object type, mode, size, and SHA-256 or deletion marker. The failed workflow run and original worktree remain audit and recovery evidence until exactly one replacement workflow root receipt seals; no duplicate outcome subplot or GitHub issue is dispatched.

R9. This plugin cannot approve its own implementation. The patch uses the operator-approved manual bootstrap sequence below, with root-owned mutation and independent no-mutation review/validation evidence.

## Key Technical Decisions

KTD1. Normalize raw link counts only on subject-exclusion parent directories: derive the immediate lexical parent of each already validated repo-relative subject path and encode a stable sentinel for those directory entries. Authorized direct children can legitimately change those counts, while higher ancestors and all device, inode, mode, path, visible-entry, symlink, and file-content evidence remain authoritative.

KTD2. Preserve filesystem path semantics: do not add unconditional case folding, Unicode normalization, `resolve()`-based authorization, or broader prefix matching. `_subject_path()` and descriptor-relative, no-follow traversal remain the trust boundary.

KTD3. Keep whole-workspace audits strict: snapshots without subject exclusions and directory entries unrelated to exclusions continue hashing raw `st_nlink`. The existing same-content hardlink-replacement and Git-control tests remain mandatory regression controls.

KTD4. Prove the bug on every CI filesystem: test an authorized newly created directory because it changes parent link metadata on APFS and Linux, test an authorized newly created file for the observed APFS case, and negative-test unauthorized siblings. A focused helper assertion proves direct-parent normalization and higher-ancestor strictness even where file creation does not change directory links.

KTD5. Treat this as a native post-cutover patch, not a Claude refresh: the repository is the maintained source after cutover (`AGENTS.md:30`). Existing classification validation remains a regression gate, but historical port manifests and classifications are not rewritten.

KTD6. Use a manual bootstrap workflow: Verified Workflows explicitly refuses its own implementation paths as a subject and forbids its receipts from approving its own changes (`plugins/verified-workflows/skills/run/SKILL.md:129`, `plugins/verified-workflows/skills/run/SKILL.md:163`). Root implements and integrates; independent agents return advisory evidence only.

KTD7. Do not retrofit the failed issue #357 chain: its v1 subject stores only the old aggregate digest, so no evidence-preserving conversion exists. Before replacement, record a deterministic preservation manifest for every changed, untracked, and deleted authorized path. After install, create one replacement run in a fresh worktree at the original `c9cdc992f123b19872b36b4559b7b57f5419e8e7` baseline, reproduce and verify those exact bytes and deletion markers, and retain the old worktree and failed run until the replacement root receipt seals.

## Implementation Units

### U1. Normalize subject-exclusion parent metadata

Make the outside-scope projection stable across authorized child creation while preserving all visible-state checks.

**Goal:** Allow exact-file and directory subject scopes to advance on APFS and Linux without broadening authorization.

**Requirements:** R1, R2, R3, R4, R5.

**Dependencies:** None.

**Files:** Modify `plugins/verified-workflows/scripts/workspace_evidence.py`. Add focused behavior coverage to `plugins/verified-workflows/tests/test_workspace_evidence.py` and protected subject-chain coverage to `plugins/verified-workflows/tests/test_dispatch_receipt.py`.

**Approach:** Derive the immediate lexical parent directory for each `normalized_exclusions` entry, mapping a top-level path's parent to `.`. When `_workspace_snapshot()` hashes a directory in that set, replace only its raw link-count value with a stable sentinel; leave the rest of the entry unchanged. Do not normalize higher ancestors. Keep current exact-path and descendant exclusion matching, descriptor-relative traversal, symlink rejection, byte/file ceilings, and Git-control snapshot behavior.

**Patterns to follow:** Preserve the closed, bounded traversal in `plugins/verified-workflows/scripts/workspace_evidence.py:1207`, the parent continuity checks in `plugins/verified-workflows/scripts/workspace_evidence.py:685`, and existing replacement detection in `plugins/verified-workflows/tests/test_dispatch_receipt.py:1598`.

**Test scenarios:** Happy path: given a subject whose exact file path is initially missing beneath an existing parent, create that file and record a descendant; expect continuity with the file included in subject content. Cross-platform path: given a missing authorized directory beneath an existing parent, create it with a nested file; expect continuity on APFS and Linux. Authorization boundary: authorize an exact file beneath a missing intermediate directory, create both, and expect the intermediate directory to remain detected as outside-scope drift. Negative siblings: add a file and a directory beside an authorized path; expect descendant creation or readback to reject outside-scope drift. Metadata controls: replace an outside-scope file with identical bytes through a new inode or hardlink, change a mode, introduce a symlink, or mutate Git controls; expect existing evidence checks to fail. Scope control: mutate only a higher ancestor's or unrelated directory's link topology; expect the outside-scope digest to change.

**Verification:** The focused Verified Workflows tests pass on macOS, the new directory case is portable to Linux CI, and existing hardlink/Git-control tests remain green.

### U2. Publish one aligned patch-release surface

Make every maintained and generated version surface describe the repaired behavior consistently.

**Goal:** Release Verified Workflows `1.0.2+codex.<release timestamp>` without stale source, inventory, or documentation claims.

**Requirements:** R6, R7.

**Dependencies:** U1.

**Files:** Modify `plugins/verified-workflows/.codex-plugin/plugin.json`, `plugins/verified-workflows/CHANGELOG.md`, `plugins/verified-workflows/PORTABILITY.md`, `README.md`, `scripts/validate_codex_plugins.py`, `tests/test_validate_codex_plugins.py`, `tests/test_verified_workflows_migration.py`, `tests/test_saga_docs_package.py`, `tests/test_prove_codex_plugin_profile.py`, `docs/validation/saga-family-target-inventory.json`, `docs/saga/generated/lifecycle-facts.json`, `docs/portability/matrix.md`, `docs/engineering-journal/DECISIONS.md`, and `docs/engineering-journal/LEARNINGS.md`.

**Approach:** Compute one UTC build timestamp and apply the exact resulting `1.0.2+codex.<timestamp>` version across all 12 version-bearing release surfaces: the plugin manifest, changelog, portability note, root README, validator script, four direct version tests, target inventory, generated lifecycle facts, and portability matrix. Correct the stale unpublished/`1.0.0` status in both portability documents, regenerate target inventory/facts through repository tooling where available, and document the APFS metadata lesson and narrow normalization decision. Preserve `.agents/plugins/marketplace.json` because it has no plugin version field and already exposes exactly one active workflow identity. Preserve historical cutover, runtime-proof, port-manifest, and classification receipts unless a validation tool demonstrates a real generated dependency.

**Patterns to follow:** Use the release-unit policy in `plugins/verified-workflows/PORTABILITY.md` and the target inventory projection consumed by `tests/test_verified_workflows_migration.py:54` and `tests/test_saga_docs_package.py:44`.

**Test scenarios:** Version parity: load all 12 maintained version-bearing surfaces and expect one exact version and current released status. Generated parity: rebuild Saga lifecycle facts and expect byte-identical checked-in output. Historical evidence: run classification and legacy-token validation and expect no historical receipt rewrite. Marketplace identity: expect `verified-workflows` active and `team-execution` absent from active entries.

**Verification:** Repository validation reports no manifest, inventory, generated-fact, marketplace, or historical-evidence drift.

### U3. Run the manual bootstrap review and validation gate

Independently challenge the trust-boundary change without allowing the plugin to self-approve.

**Goal:** Produce advisory review and platform-test evidence, resolve all P0-P3 findings in root, and prove the release from source.

**Requirements:** R3, R4, R5, R6, R9.

**Dependencies:** U1, U2.

**Files:** Review the complete branch diff. Modify only declared U1/U2 paths when resolving implementation findings, plus the U3 code-review artifact under `docs/code-reviews/` and QA artifact under `docs/qa/` after evidence is complete.

**Approach:** Launch the two no-mutation attempts defined in the Manual Bootstrap Workflow after root implementation is quiescent. Root adjudicates findings, applies fixes, and reruns only an affected reviewer or validator when needed. Root then runs focused plugin tests, release-surface tests, repository validation, classification validation, scoped Ruff with `--no-cache`, `uv run bandit -q -ll <changed Python source files>`, and `PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider` for the full suite. Pin `UV_PROJECT_ENVIRONMENT` and `UV_CACHE_DIR` to predeclared temporary directories outside the worktree for child and final evidence runs; disable or redirect every other tool cache likewise. MyPy is an optional diagnostic only unless a clean scoped baseline is first established; unrelated pre-existing typing failures are not a substitute for the required gates.

**Patterns to follow:** Preserve root mutation ownership and evidence-only children from `plugins/verified-workflows/skills/run/SKILL.md`. Follow the repository commands in `AGENTS.md` and do not treat installed cache bytes as source.

**Test scenarios:** Reviewer challenge: inspect over-exclusion, inode/hardlink blind spots, symlink/TOCTOU regressions, old-record readability, and release drift. Platform validator: exercise new file/new directory continuity and unauthorized sibling cases, then verify existing mutation-audit controls. Failure handling: any P0-P3 finding blocks integration until fixed and independently rechecked; inability to run a required check remains an explicit blocker.

**Verification:** Both advisory attempts are clean after any follow-up, all focused and full checks pass, and root records the residual self-verification limitation explicitly.

### U4. Merge, install, and resume issue #357 without duplicate dispatch

Put the repaired package into supported installed state, then replace only the non-migratable workflow run.

**Goal:** Restore the blocked `lease-safe-runtime-continuity` path while preserving outcome, issue identity, and every byte of the approved implementation.

**Requirements:** R7, R8.

**Dependencies:** U3.

**Files:** No maintained cache files. Installation writes only through the supported Codex plugin mechanism. In `infiquetra-claude-plugins`, reuse the approved issue #357 plan and implementation paths; retain old protected plugin data as audit residue and create a separate replacement-run evidence root.

**Approach:** Before replacement, capture the old worktree's base revision and a bounded preservation manifest for every changed, untracked, and deleted authorized #357 path, recording Git status, object type, mode, size, and SHA-256 or deletion marker. Merge the patch release, run `codex plugin marketplace upgrade infiquetra-codex-plugins --json`, confirm the available version with `codex plugin list --available --json`, install it with `codex plugin add verified-workflows@infiquetra-codex-plugins --json`, and verify installed state with `codex plugin list --json`. Compare the installed manifest and `scripts/workspace_evidence.py` SHA-256 values with merged source. Create one fresh issue #357 worktree at the original clean baseline, initialize one replacement run with the already approved 45-path subject, reproduce the preservation manifest exactly, verify source-to-replacement byte and deletion parity, and continue the previously approved six-attempt review/validator graph. Retain the old worktree and old protected plugin data until the replacement root receipt seals. Do not dispatch another outcome subplot, issue, or leaf.

**Patterns to follow:** Use installed-state readback from repository validation and the existing issue #357 plan at `docs/plans/2026-07-15-issue-357-fleet-shared-liveness-engine-plan.md` in `infiquetra-claude-plugins`.

**Test scenarios:** Install parity: compare merged source and installed manifest/implementation bytes. Preservation parity: compare every replacement path and deletion marker with the old-worktree manifest before retiring any recovery surface. Workflow continuity: create a descendant after adding authorized files and expect the repaired projection to remain stable. Audit retention: confirm the old run and worktree remain untouched until the replacement run has a distinct sealed evidence root. Outcome identity: confirm `sub-357` remains the only dispatched issue #357 leaf.

**Verification:** Installed version `1.0.2+codex.<release timestamp>` is readable, the replacement issue #357 root receipt seals, and outcome status shows no duplicate dispatch.

## Manual Bootstrap Workflow

This sequence is the approval surface for the self-hosting patch; it is deliberately not a canonical Verified Workflow receipt.

| step | depends on | owner / vehicle | model / effort | configured permission and live requirement | mutation | required evidence |
|---|---|---|---|---|---|---|
| implement | - | root | root session | current root permission; writes restricted to declared U1/U2 paths | declared U1/U2 paths | scoped diff, focused tests, release parity |
| review-trust-boundary | implement | `review_high` child | `gpt-5.6-sol` / high | configured read-only; host readback must agree | none | typed security, correctness, and compatibility findings |
| validate-apfs-and-linux | implement | `test_medium` child | `gpt-5.6-terra` / medium | configured workspace-write; attempt contract and before/after audit require zero mutation | none | scenario matrix and captured root command evidence |
| integrate | review-trust-boundary, validate-apfs-and-linux | root | root session | current root permission; finding-scoped writes only | finding-scoped U1/U2 paths plus U3 evidence artifacts | resolved findings, focused and full checks |
| release-install | integrate | root | root session | explicit Git/release authority plus pinned marketplace upgrade/add commands | Git/release plus supported plugin install | merge SHA, installed manifest, exact source/cache SHA-256 parity |
| resume-issue-357 | release-install | root | root session | existing issue #357 scope only | existing issue #357 scope only | preservation parity, one replacement run, sealed root receipt, no duplicate outcome dispatch |

The two child attempts are advisory because the subject includes Verified Workflows implementation. Root remains accountable for every mutation, finding decision, test command, release action, install readback, and issue #357 restart.

## Risks and Mitigations

| risk | impact | mitigation |
|---|---|---|
| Parent normalization hides unrelated mutations | Outside-scope writes could evade the gate | Normalize only the immediate parent's link-count scalar; keep higher ancestors strict and continue hashing parent inode/device/mode and every visible child entry, with unauthorized sibling tests. |
| Platform-specific tests pass only on macOS | Linux CI misses the structural regression | Include a newly authorized directory case that changes directory links on both APFS and Linux plus a direct-parent-normalization unit assertion. |
| Old records are silently reinterpreted | Evidence ancestry becomes untruthful | Keep schemas readable but never migrate the failed digest; retain it and create one replacement run. |
| Self-review is mistaken for independent authority | The plugin approves its own trust-boundary change | Use the explicit manual bootstrap workflow and label child evidence advisory. |
| Release metadata drifts | Installed behavior and advertised version disagree | Treat the manifest, expected-version assertions, target inventory, generated facts, README, changelog, and install readback as one patch-release unit. |
| Replacement workflow is mistaken for a duplicate outcome dispatch | Outcome state forks | Reuse `sub-357`, its issue and plan; create no new subplot or GitHub issue and verify outcome status before and after. |
| Replacement replay loses or changes approved implementation bytes | Review evidence no longer applies to the replacement | Manifest every changed, untracked, and deleted authorized path; require byte/deletion parity; retain the old worktree until the new root receipt seals. |

## Scope Boundaries

The patch does not remove inode or link metadata from full workspace snapshots, normalize links for higher ancestors or unrelated directories, authorize missing intermediate parents for an exact-file subject, broaden subject path matching, add APFS-specific case folding, relax symlink handling, change protected-record schemas, rewrite historical port/cutover evidence, or edit installed cache files directly.

The patch does not change the issue #357 liveness implementation or its approved six-attempt workflow. It changes only the workflow substrate required to verify that work, then replays the preserved implementation in one replacement run because the old aggregate digest is not migratable.

### Deferred to Follow-Up Work

Versioned workspace-projection algorithms and first-class migration receipts would make future projection changes migratable. They are separate protocol design work and are not required for this bounded correction.

## Sources

- `plugins/verified-workflows/scripts/workspace_evidence.py:638`
- `plugins/verified-workflows/scripts/workspace_evidence.py:667`
- `plugins/verified-workflows/scripts/workspace_evidence.py:694`
- `plugins/verified-workflows/scripts/workspace_evidence.py:1207`
- `plugins/verified-workflows/tests/test_dispatch_receipt.py:1598`
- `plugins/verified-workflows/skills/run/SKILL.md:129`
- `plugins/verified-workflows/skills/run/SKILL.md:163`
- `plugins/verified-workflows/PORTABILITY.md`
- `AGENTS.md:28`
- `AGENTS.md:30`
