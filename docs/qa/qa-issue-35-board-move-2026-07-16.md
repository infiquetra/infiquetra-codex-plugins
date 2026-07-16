# QA Report: Mission Control board-move fail-loud port

| Field | Value |
|-------|-------|
| Date | 2026-07-16 |
| Target issue | `infiquetra/infiquetra-codex-plugins#35` |
| Parent onboarding | `infiquetra/team-mimir#108` |
| Source onboarding PR | `infiquetra/team-mimir#192`, merge `e53e9df9451a4cc4ba9eef5ba5472d6ec5c40ea2` |
| Feature PR | #36, merge `2bc27eb60d64090dcc78c4f70d98c9fbe48bd99f` |
| Reviewed feature head | `0575c03126cb17bb59c1dec090bb93470354ffda` |
| Installed release | Mission Control 2.4.2 |
| Canonical run | `8c326812-87db-4148-91ce-635e4a5351ed` |
| Scope | source parity, fail-loud behavior, merge, isolated VM install, no-mutation canary, fresh-process discovery, rollback, cleanup |

## Ship verdict: ship

Mission Control 2.4.2 preserves the Codex adapter boundaries while porting the
released Claude 2.10.1 aggregate failure behavior. The exact reviewed head was
merged, installed from merged main in an isolated Codex home on VM 209, and
proved nonzero invalid-Status behavior without a board mutation. A fresh Codex
process discovered the installed skill. Rollback removed the entire isolated
root and left no host-global package or credential residue.

The VM 209 authoritative run is `nonprod_proven`, promotion eligible with no
denial codes, and has `conflict_count=0`. Coverage disposition is `keep`.

## Build and review evidence

- Exact-source verification accepted all six frozen Claude release rows with
  inventory SHA-256
  `5f989d44300e4630347c36e840cfb6dc9d62d87f72b2690e61b35016dc46167a`.
- The four pre-edit classification cases and all five final port-contract cases
  passed.
- All six adapted behavior cases passed, and the full Mission Control suite
  passed with `211 passed`.
- The default repository suite completed with `2,221 passed` and two unrelated,
  pre-existing HOME-sensitive Saga dry-run failures. Those exact two tests pass
  unchanged with an isolated HOME; the repository-wide suite is not fully
  hermetic because other profile/readiness tests intentionally inspect the
  installed user home.
- Ruff, current and target-fixture plugin validation, generated Saga
  facts/assets, legacy-token inventory, exact-source verification, and diff
  checks passed. Bandit reported no medium or high finding; eight pre-existing
  low findings remain outside this change.
- The code review found no unresolved P0-P2 finding at reviewed head
  `0575c03126cb17bb59c1dec090bb93470354ffda`.
- GitHub reported zero provider check runs and zero commit-status contexts for
  the exact reviewed head, matching the repository-bound empty provider-check
  policy.
- The merge commit tree exactly matches the reviewed head tree.

## Deployment and installed-runtime evidence

| Check | Result |
|-------|--------|
| Nonproduction target | Proxmox VM 209, `hermes.infiquetra.com`, KVM guest |
| Isolation | Codex 0.144.4 and `CODEX_HOME` existed only below `/home/agent/.hermes/canaries/team-mimir-108` |
| Marketplace install | `mission-control@infiquetra-codex-plugins` reported installed and enabled at version 2.4.2 |
| Script parity | Merged, staged, and installed `sdlc_manager.py` SHA-256 values all equal `a9cf078dabafb536e530f7abeb6b334209e4654632b34c38585c3f9a6f20d4b2` |
| Manifest provenance | Staged plugin manifest SHA-256 `a65cffca0307f4c400d519434de64d28ac9f00b1e5232d09d09124e57d613e24` |
| Invalid Status | Installed `board move` listed the live Status choices and exited 1 for `__MIMIR_CANARY_INVALID__` |
| No mutation | Operations item `PVTI_lADODdfJoc4BZLMKzgzFipY` remained `Active`; `updatedAt` stayed `2026-07-16T18:21:12Z` before and after |
| Fresh-process pickup | A separate Codex process reported version 2.4.2 installed/enabled and discovered `mission-control:board` exactly once from the installed cache |
| Credential boundary | No authentication file was copied into the isolated Codex home; the operator token was passed only to the one remote process through standard input |

## Canonical run evidence

Run `8c326812-87db-4148-91ce-635e4a5351ed` correlates parent #108, target #35,
feature PR #36, the exact reviewed head, source and target merge commits, review,
tests, the tiny 45-minute soft/90-minute hard policy, closed breaker, installed
hash parity, no-mutation behavior, fresh-process discovery, rollback, cleanup,
and `keep` disposition.

The authoritative VM 209 store reports:

```text
lifecycle_state=nonprod_proven
promotion_eligible=true
denial_codes=[]
conflict_count=0
reviews_passed=1
tests_passed=1
e2e_passed=1
breaker_state=closed
```

## Rollback and cleanup

Rollback used the plan's allowed remove-root path. The complete
`/home/agent/.hermes/canaries/team-mimir-108` tree was deleted after the
installed and fresh-process proofs. Final readback confirmed:

- the canary root is absent;
- no host-global `codex` command exists;
- no host-global `@openai/codex` npm package exists;
- no canary credential file exists; and
- the real Operations item and the user's existing Codex home were not
  mutated.

## Residual risk

The default full-suite result retains two unrelated HOME-sensitive failures as
described above. The exact failing tests pass in their isolated environment,
all issue-specific and Mission Control gates pass, and the live installed
behavior exercises the changed failure path. No unresolved release or runtime
finding remains for issue #35.
