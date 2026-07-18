---
date: 2026-07-17
target: docs/plans/2026-07-17-verified-workflows-apfs-subject-snapshot-plan.md
reviewed_revision: working tree at 4c96e87ee5efd680348cfe95710972117e9d1532
blocked: false
review_type: plan-readiness
---

# Verified Workflows APFS Subject Snapshot Plan Review

## Applied Fixes

Five readiness findings were resolved in place. No P0-P3 finding remains.

| id | priority | status | finding | applied fix |
|---|---|---|---|---|
| DR1 | P1 | resolved | Normalizing every lexical ancestor of an exclusion was broader than the APFS behavior required and weakened evidence unnecessarily. | Narrowed normalization to the immediate lexical parent directory only, kept higher ancestors strict, and added exact-file missing-parent and higher-ancestor negative scenarios. |
| DR2 | P1 | resolved | The release/install gate named a supported mechanism but did not provide an executable path or exact installed-state proof. | Pinned the marketplace upgrade, available-version readback, plugin add, installed-list readback, and merged-source-to-cache SHA-256 checks. |
| DR3 | P1 | resolved | The #357 replacement run said to reapply preserved work without a deterministic inventory, parity gate, or recovery-retention rule. | Added a base-bound status/type/mode/size/SHA-256 or deletion manifest, exact replay comparison, and retention of the old worktree and protected run until the replacement root receipt seals. |
| DR4 | P2 | resolved | The release unit omitted the portability matrix, retained stale unpublished/`1.0.0` claims, and understated the number of version-bearing surfaces. | Added the matrix, required one UTC timestamp across all 12 version surfaces, and required current released-status parity. |
| DR5 | P2 | resolved | U3 both restricted fixes to U1/U2 paths and required new review artifacts, while its quality gate did not pin security or no-cache commands tightly enough for a snapshot-sensitive change. | Allowed the two U3 evidence artifacts explicitly and pinned scoped no-cache Ruff, `bandit -q -ll`, external uv environment/cache paths, and full no-bytecode/no-pytest-cache execution. |

## Readiness Summary

The plan is ready for operator approval. It now limits the trust-boundary change to the metadata proven unstable, preserves strict evidence elsewhere, defines an executable self-hosting bootstrap, and closes release, installation, and #357 replay boundaries.

This is a single implementation plan for a diagnosed defect. It is not an idea, issue, requirements specification, or ADR, so no lifecycle phase rubric applies.

## Remaining Findings by Priority

No findings remain after the evidence-backed fixes.

| priority | status | finding |
|---|---|---|
| None | closed | No unresolved P0-P3 readiness finding remains. |

## Review Result Contract

| field | value |
|---|---|
| target path | `docs/plans/2026-07-17-verified-workflows-apfs-subject-snapshot-plan.md` |
| reviewed revision | working tree at `4c96e87ee5efd680348cfe95710972117e9d1532` |
| blocked | false |
| classification | implementation plan for a diagnosed defect |
| finding priorities and statuses | 3 P1 resolved; 2 P2 resolved; none remaining |
| applied fixes | direct-parent normalization; exact install proof; deterministic #357 preservation; complete release surfaces; executable validation and write scope |
| review artifact path | `docs/reviews/2026-07-17-verified-workflows-apfs-subject-snapshot-plan-doc-review.md` |
| override rationale | none |

## Residual Risk

Actual APFS and Linux behavior, source-to-installed parity, and the replacement #357 receipt remain implementation and release gates rather than proof available during document review. Because Verified Workflows cannot approve changes to itself, the plan correctly keeps the two independent attempts advisory and leaves all mutation, adjudication, release, and restart authority with root.
