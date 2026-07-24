---
date: 2026-07-24
task: codex-v2-orchestrated-execution-system
reviewed_revision: 4fbbd3e
merged_revision: 74258be
verdict: PASS
evidence_mode: native-v2-current-auth
---

# QA: Codex V2 orchestrated execution system

## Verdict

PASS. The reviewed source is merged, the three aligned plugin releases are installed in the current
Codex home, six managed profiles match merged source, and fresh Codex 0.145.0 sessions report the
expected V2 root and child runtime identity. The attended rollback restored the exact predecessor
repository, marketplace, package, profile, user-config, workflow-data, and model-catalog state; V2
was then reapplied and the fresh-session smoke passed again. Existing authentication was reused and
was not changed.

## Acceptance matrix

| scenario | evidence | result |
|---|---|---|
| Six configured profiles select exact model and effort | receipt-derived runtime matrix | pass |
| Read-only and workspace-write ceilings are observed | child `turn_context` receipts | pass |
| Nested V2 delegation reaches depth two | `/root/nested_parent/nested_leaf` receipt chain | pass |
| Messaging, list, wait, interrupt, follow-up, and restoration work | lifecycle root and restored child receipts | pass |
| No-history excludes root-only context | required negative marker | pass |
| Bounded history exposes the approved marker | required positive markers | pass |
| Typed result matches the closed assignment schema | exact terminal JSON parse | pass |
| Luna V1 incompatibility selects approved Terra/low fallback | native model-cache and profile receipts | pass |
| Ultra is effective at root and capped to Max for a child | root and child receipts | pass |
| Dirty, ignored, nested-repository, Git-control, and write ownership drift fail closed | workspace-audit suite | pass |
| External actions remain non-gating and secret-safe | policy, adapter, egress, and workspace suites | pass |
| HTTP endpoint, auth environment, and executable egress are registry-bound | independent mutation tests | pass |
| All independent reviewers accept | architecture 10.0, security 10.0, testing 9.8 | pass |
| Reviewed release is merged to `main` | PR #46 merge commit `74258be` | pass |
| Installed plugin bytes match merged source | checksum-only source/cache comparison | pass |
| Six current-home profiles match merged source | transactional sync and byte readback | pass |
| Fresh installed-state V2 execution works | `/root/installed_v2_smoke` runtime receipts | pass |
| Exact predecessor rollback works | protected rollback bundle and direct byte/version readback | pass |
| Reapplied V2 execution works | `/root/reapplied_v2_smoke` runtime receipts | pass |

## Root quality gates

| check | result |
|---|---|
| Full repository pytest | 2,633 passed |
| Final focused credential-boundary pytest | 41 passed |
| Focused docs, matrix, and workflow pytest | 73 passed |
| Ruff | pass |
| Repository plugin validator | pass |
| Matrix regeneration and check | pass |
| Real-worktree workspace audit capture | pass |
| `git diff --check` | pass |

## Installed releases

| plugin | installed version |
|---|---|
| `fleet-core` | `0.11.0+codex.20260724175626` |
| `saga` | `0.79.0+codex.20260724175626` |
| `verified-workflows` | `2.0.0+codex.20260724175626` |

## Delivery evidence

- PR #46 merged reviewed head `4fbbd3e` to `main` as `74258be`; the repository has no PR checks
  configured, and GitHub reported the PR mergeable before merge.
- The protected ignored rollback bundle under `.codex/cutover/` captured predecessor `f3e1af`, merged
  `74258be`, exact user/project config, native and V1 catalogs, all agent files, workflow data, the
  prior marketplace snapshot, and the three prior package caches. Its hashes, archives, modes, and
  Git bundle verified before mutation. Authentication files were deliberately excluded because
  authentication was unchanged.
- `codex plugin marketplace upgrade infiquetra-codex-plugins` moved the marketplace and installed
  caches to `74258be`; `codex plugin list --json` reports all three installed releases enabled.
- The validated profile synchronizer installed six reviewed profiles while preserving four unmanaged
  profiles. An initial invocation omitted the committed catalog snapshot and changed only generated
  catalog-digest comments; byte readback caught the drift, and a second journaled transaction using
  `docs/validation/codex-runtime-capability-snapshot.json` restored exact reviewed bytes before the
  first live smoke.
- The obsolete V1 catalog pointer and two inert Verified Workflows V1 hook-state rows were removed;
  the native model cache remained byte-identical throughout the cutover.
- The first fresh smoke observed a V2 Sol/max root, a V2 Sol/high `review_high` child at
  `/root/installed_v2_smoke`, OpenAI provider, managed read-only permission, and spawn/list/wait.
- Rollback restored repository and marketplace `f3e1af`, Fleet Core `0.10.0`, Saga `0.78.0`, Verified
  Workflows `1.0.3`, exact captured config/catalog bytes, five prior managed profiles, four unmanaged
  profiles, and prior workflow data. Direct archive comparison verified the restored agent bytes.
- Reapply returned repository and marketplace to `74258be`, restored the three installed releases and
  six reviewed profiles, removed V1 residues, and repeated the same receipt proof at
  `/root/reapplied_v2_smoke`.
