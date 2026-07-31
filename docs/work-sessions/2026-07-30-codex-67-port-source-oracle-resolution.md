# 2026-07-30 — codex#67: Frozen-source port-oracle resolution

Branch `fix/67-port-source-oracle-resolution`, based on `12b5f2c`. This work session remains
uncommitted, unpushed, and has no pull request.

## Baseline

Before the code change, a clean detached worktree outside the workspace ran the two affected
contracts as `25 passed, 8 skipped`. The source-dependent checks skipped because their local
`ROOT.parent / "infiquetra-claude-plugins"` lookup pointed beside the disposable worktree rather
than beside the primary Codex clone.

## Completed implementation units

U1 adds a shared resolver in `tests/conftest.py`. It gives `CODEX_PORT_SOURCE_REPO` precedence;
otherwise it reads Git's absolute common directory, derives the source sibling from the manifest
repository identifier, and verifies that the candidate is a Git worktree with a matching normalized
GitHub `origin`. It accepts HTTPS and SSH origin forms and returns a clear, fail-closed pytest
failure containing the override name when it cannot establish that proof.

U2 moves both frozen-source contract modules to the shared pytest fixture. Their local sibling
fallbacks and all `pytest.skip` branches are removed; their frozen ranges, inventories, and oracle
assertions are unchanged. `tests/test_port_source_resolution.py` covers detached-worktree discovery,
override precedence, unavailable and malformed Git results, missing candidates, identity mismatch,
accepted origin forms, and structural use by both contracts.

## Evidence

| Check | Result |
|---|---|
| Pre-change detached-worktree target contracts | `25 passed, 8 skipped` |
| Focused resolver and both contract modules | `43 passed` |
| Focused Ruff check | passed |
| `git diff --check` | passed |
| Post-change external detached-worktree target contracts, no environment override | `33 passed`, no skips |
| Current-port classification validation and render checks | both passed |
| Clean detached-worktree full suite | `2441 passed` |
| Clean detached-worktree repository validation | passed |
| Pre-PR code review | clean; `docs/code-reviews/2026-07-30-fix-67-port-source-oracle-resolution-code-review.md` |

## U3 — authorized contract update

The approved plan required an update to the versioned portability runbook while also forbidding
changes to `scripts/port_contract.py` and all port manifests. The repository's runbook contract
requires a version update and a new digest in every current port contract, so the operator explicitly
authorized the narrow mechanical expansion on 2026-07-30.

The runbook is now version 5 and documents automatic detached-worktree discovery, the
`CODEX_PORT_SOURCE_REPO` override, normalized `origin` verification, and the fail-closed outcome.
`scripts/port_contract.py` accepts historical versions 3 and 4 alongside version 5. The two current
2026-07-29 port manifests and their generated classifications carry the version-5 digest. No frozen
source range, source row, evidence record, or unrelated port manifest changed.
