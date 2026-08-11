# Doc Review: Saga Re-entry and Procedural Stop Plan

The issue #62 plan is implementation-ready after an independent, three-pass readiness review that removed stale Outcome work and resolved the remaining session-discovery decisions.

## Review Result Contract

| field | value |
|---|---|
| target path | `docs/plans/2026-08-10-saga-lifecycle-truthfulness-plan.md` |
| linked issue | `infiquetra/infiquetra-codex-plugins#62` |
| retained child | #56, repository-owned `.claude/` ignore protection |
| excluded child | #55, closed `NOT_PLANNED`; Outcome settlement is historical/stale scope only |
| reviewed revision | working tree at `HEAD` `0db153bf2ae24156c301708c9a6139eb3d3878d9`; merge base with `origin/main` is the same revision |
| reviewer session | `019feec6-30db-7600-83ea-0f0138930900` |
| reviewer | Codex `gpt-5.6-terra`, high reasoning effort |
| classification | issue-derived implementation plan; issue-phase rubrics plus readiness-skeptic review |
| blocked | false |
| override rationale | none |
| review artifact path | `docs/reviews/2026-08-10-saga-lifecycle-truthfulness-doc-review.md` |

## Initial Review: REVIEW BLOCKED

The first pass found three blocking Outcome contradictions and two implementation-readiness gaps.

| ID | priority | status | finding and disposition |
|---|---|---|---|
| D1 | P1 | resolved by exclusion | U1 relied on `outcome_dispatch_bindings()` to create a first settlement binding even though it only recovers an existing manifest. Root closed #55 `NOT_PLANNED` and removed all Outcome implementation rather than inventing admission machinery. |
| D2 | P1 | resolved by exclusion | U1 prescribed `SILENT_NOOP`, which remains a threshold-zero casualty and could retain `halt_required`. Removing the stale Outcome unit resolved the contradiction without changing settlement semantics. |
| D3 | P1 | resolved by exclusion | U1 risked conflating the Outcome reducer's retry-visible halt with run-ledger settlement. The plan now excludes Outcome intent, acknowledgement, reducer, casualty, and settlement code. |
| D4 | P2 | reclassified non-actionable | The claimed missing precedent exists: `docs/plans/2026-07-25-codex-refreeze-627-seam-and-cor3-worktree-authority-plan.md` U4 at lines 450-501 documents the historical transient path, `settle_attempt`, intent-before-dispatch ordering, and preservation requirements. The repaired plan no longer relies on it. |
| D5 | P2 | resolved | Date-layout discovery called metadata bounded without defining a byte ceiling or omission behavior. The repaired plan requires a regular readable file, a complete `session_meta` first record no larger than 64 KiB, and a 65,537-byte limit-plus-one probe; oversized, malformed, unreadable, non-regular, and non-`session_meta` candidates are omitted. |

## Root Scope Decision

Root closed child issue #55 as `NOT_PLANNED` and retained only three units: current date-layout session discovery and extraction, the procedural two-pass stop, and repository-owned `.claude/` ignore protection. Outcome is historical scope only; a future admission-before-intent redesign requires a separately approved plan.

## Second Review: REVIEW BLOCKED

The second pass found two P2 gaps in the current-layout discovery contract.

| ID | priority | status | finding and repair |
|---|---|---|---|
| D6 | P2 | resolved | Tied modification times lacked a specified deterministic order. Both layouts now sort together by modification time descending, session identifier ascending, then path ascending before the five-result cap; the mixed-layout test asserts the exact tied order. |
| D7 | P2 | resolved | `payload.cwd` matching was ambiguous for worktrees. Current layout now accepts only a complete component equal to `--repo` or exactly `<repo>-worktrees`; a nested worktree succeeds, a similarly named `-other` component fails, and the legacy directory substring scan remains unchanged. |

## Final Review: REVIEW COMPLETE

No actionable P0, P1, P2, or P3 findings remain. The plan is ready to route to repository Saga work under its recorded inline, merge-destination contract.

## Checks

| command | result |
|---|---|
| `git diff --check` | PASS |
| `python3 -m pytest -q tests/test_saga_docs_package.py` | PASS |
| `python3 -m pytest -q tests/test_saga_doc_formatting.py` | PASS |
| `python3 scripts/build_legacy_workflow_inventory.py --check` | PASS |
| `python3 scripts/validate_codex_plugins.py` | PASS |

## Residual Risk

The retained implementation risk is limited to the three planned units. Session discovery must preserve the stated 64 KiB-plus-one read bound and output boundary, the two-pass guidance must remain procedural across `/work`, `/loop`, and `/resume`, and the `.claude/` rule must be verified against Git rather than assumed from local excludes. Outcome behavior remains outside this work and requires separate approval if reconsidered.
