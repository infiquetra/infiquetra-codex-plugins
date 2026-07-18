---
date: 2026-07-18
task: verified-workflows-apfs-subject-snapshot
reviewed_revision: fe93073db66877df79dff3d69d6dde95f4410535
verdict: PASS
evidence_mode: manual-bootstrap-advisory
---

# QA: Verified Workflows APFS Subject Snapshot

## Verdict

PASS for PR readiness. The corrected projection advances authorized missing-file and missing-directory
subjects on APFS while all requested outside-scope controls remain strict.

## Advisory Attempts

| attempt | role / requested profile | result | mutation audit |
|---|---|---|---|
| initial platform attempt | no role packet / `test_medium` | Failed closed before commands because logical role, lens digest, and schema were absent; discarded. | No commands or mutations. |
| platform replacement | `scenario-tester` / `test_medium` | 12 scenarios passed on APFS; Linux semantics inspected, not executed. | Before and after porcelain output empty and identical. |
| trust-boundary review | `security-reviewer` / `review_high` | Accept, 10.0 applicable score, no P0-P3 findings. | Before and after porcelain SHA-256 identical. |

The requested profile mappings were `test_medium` to Terra/medium and `review_high` to Sol/high. No
model, effort, or effective sandbox claim is made beyond the host's selected profile metadata because
the manual advisory path does not mint the complete canonical attestation join.

## Scenario Matrix

| scenario | evidence | result |
|---|---|---|
| Authorized missing exact file beneath existing parent | Focused subject-chain test on APFS | pass |
| Authorized missing directory beneath existing parent | Focused subject-chain test on APFS | pass |
| Missing intermediate parent for exact file | Outside-scope rejection test | pass |
| Unauthorized sibling file | Outside-scope rejection test | pass |
| Unauthorized sibling directory | Outside-scope rejection test | pass |
| Same-content hardlink/inode replacement | Existing mutation-audit regression | pass |
| Executable mode drift | Existing subject-readback regression | pass |
| Git-control drift | Existing workspace-audit regressions | pass |
| Top-level and nested parent derivation | Direct-parent helper assertion | pass |

## Root Quality Gates

| check | result |
|---|---|
| Focused platform replacement | 12 passed in 5.43s |
| Verified Workflows plugin review run | 210 passed |
| Release/document review run | 74 passed |
| Full detached repository suite | 2,247 passed in 180.11s |
| Ruff `--no-cache` | pass |
| Bandit `-q -ll` on changed Python source | pass |
| Current/cutover/target-fixture validation | pass |
| Generated lifecycle facts and legacy inventory | pass |
| `git diff --check` | pass |

## Mutation and Platform Evidence

The focused child run identified the worktree filesystem as APFS and left the implementation worktree
unchanged. The full suite ran in a detached disposable worktree because repository validation creates six
zero-byte release-matrix lock files; the disposable worktree was removed after the clean run.

Linux was not executed locally. Portability rests on the directory-creation regression, which changes
the immediate parent link count on Linux, plus CI execution after the PR opens.

## Remaining Gates

- Confirm a fresh report-only code-review SHA after this evidence commit.
- Open and merge the PR only under explicit operator confirmation.
- After merge, install `1.0.2+codex.20260718004419`, prove source/cache parity, and resume the existing
  issue #357 leaf with one preservation-verified replacement run.
