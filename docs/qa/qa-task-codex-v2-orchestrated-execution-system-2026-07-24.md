---
date: 2026-07-24
task: codex-v2-orchestrated-execution-system
reviewed_revision: e41d778
verdict: PASS
evidence_mode: native-v2-current-auth
---

# QA: Codex V2 orchestrated execution system

## Verdict

PASS for PR readiness. Repository behavior, current-auth V2 runtime evidence, independent review,
candidate versions, and rollback design satisfy the pre-merge gates. Installation, rollback, reapply,
and fresh-session readback remain post-merge gates and are not claimed here.

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

## Candidate releases

| plugin | candidate version |
|---|---|
| `fleet-core` | `0.11.0+codex.20260724175626` |
| `saga` | `0.79.0+codex.20260724175626` |
| `verified-workflows` | `2.0.0+codex.20260724175626` |

## Delivery gates still open

- Push the reviewed branch and open the PR.
- Require successful PR checks before merge.
- Verify the merge commit is contained by `origin/main`.
- Capture the exact current Codex pre-state immediately before host mutation.
- Install the merged candidate versions through supported plugin commands, synchronize profiles,
  remove the obsolete user-level V1 catalog override, and prove fresh-session V2 readback.
- Restore the captured post-migration predecessor state, prove restoration, reapply V2, and repeat the
  fresh-session smoke proof.
