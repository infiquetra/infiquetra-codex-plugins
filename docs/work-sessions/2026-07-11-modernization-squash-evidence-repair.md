# Modernization Squash Evidence Repair

## Goal

Make the completed modernization cutover reproducible after GitHub squash merge and from a fresh
clone, without weakening the frozen source or reviewed-tree checks.

## Root cause

PR #26 squash-merged the reviewed branch into `e27c6f9`. The port contract still referenced commit
objects that existed only on the deleted branch, while the cutover record's `source_head` required an
ancestor of current `HEAD`. Local validation passed only because stale local refs retained those
objects; a fresh clone could not reproduce the Codex drift inventory or resolve any evidence head.

## Repair

- Added `codex.evidence_ref`, pinned to
  `refs/tags/evidence/verified-workflows-modernization-20260711`.
- Required the tag to retain the approved execution base and every evidence commit.
- Joined the original reviewed history into the repair branch with a tree-identical merge commit so
  the tag retains both the modernization and repair receipts after another squash merge.
- Rebound the cutover record to merged commit `e27c6f9` and refreshed its dependent evidence digests.
- Added a regression test that rejects an evidence commit not retained by the durable ref.

## Checks

- U5 locked suite: 543 passed.
- Full repository suite: 2,104 passed.
- Port-contract tests: 25 passed.
- Current, target-fixture, and cutover repository validators passed.
- Cutover-stage port contract passed.
- Ruff and `git diff --check` passed.
- A synthetic squash repository containing only the new `main` commit and the evidence tag passed
  current validation, cutover validation, and the cutover-stage port contract after unreachable
  objects were pruned.

## Next step

Push the evidence tag and repair branch, merge the follow-up PR, then repeat validation from a clean
GitHub clone before deleting the protected rollback bundle.
