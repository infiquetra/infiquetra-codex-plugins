---
date: 2026-07-18
task: verified-workflows-apfs-subject-snapshot
plan: docs/plans/2026-07-17-verified-workflows-apfs-subject-snapshot-plan.md
status: review-complete
---

# Verified Workflows APFS Subject Snapshot Work Session

## Completed

- U1: normalized only the immediate lexical parent directory link count for authorized subject
  exclusions, including `.` for top-level subjects.
- U1: added APFS and cross-platform subject-chain coverage for authorized missing files and
  directories, missing intermediate parents, unauthorized file/directory siblings, and strict
  hardlink, mode, and Git-control evidence.
- U2: advanced Verified Workflows to `1.0.2+codex.20260718004419` across the complete release unit.
- U2: corrected stale portability status and regenerated lifecycle facts plus the digest-bound legacy
  workflow inventory after validation proved those generated dependencies.
- U3: completed registry-bound advisory security review and APFS scenario validation with no P0-P3
  findings and identical before/after worktree audits.
- U3: passed the full detached repository suite and recorded durable code-review and QA evidence.

## Decisions

- The effective backend is manual because Verified Workflows refuses its own implementation as a
  subject. Root owns every mutation; `review_high` and `test_medium` attempts are advisory only.
- Existing protected-record schemas and the failed issue #357 chain remain untouched. The installed
  repair will start one replacement run after exact preservation-manifest replay.

## Commits

- `b8fec52` — plan, doc-review artifact, and self-hosting decision.
- `98f667f` — U1 implementation and regression coverage.
- `ee1cf82` — U2 release, generated, portability, test, and journal surfaces.

## Checks

- Red proof: 3 expected failures and 2 negative controls passed before U1 implementation.
- Focused subject and trust-boundary tests: 15 passed, then 7 passed after sibling-directory coverage.
- Verified Workflows plugin suite: 209 passed.
- Direct release and document tests: 103 passed.
- Replacement platform attempt: 12 passed on APFS; Linux semantics inspected but not executed.
- Advisory trust review: accepted with no P0-P3 findings; 210 plugin and 74 release/document tests passed.
- Full detached repository suite: 2,247 passed.
- Ruff: changed Python implementation and release/test surfaces passed with `--no-cache`.
- Repository validation: current, cutover, and target-fixture modes passed.
- Generated checks: Saga lifecycle facts and legacy workflow inventory passed.
- `git diff --check`: passed.

## Next Step

Commit the U3 evidence artifacts, then rerun report-only code review at the new HEAD and confirm the
review has zero commits of staleness before offering the PR-open mutation.
