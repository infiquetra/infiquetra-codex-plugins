# 2026-07-30 — codex#67: Frozen-source port-oracle resolution

Branch `fix/67-port-source-oracle-resolution`, based on `12b5f2c`. Merged 2026-07-31 as #70, merge
commit `0c20724`. Issue 67 was closed 2026-08-01 after the re-verification recorded at the end of
this document.

## Baseline

Before the code change, a clean detached worktree outside the workspace ran the two affected
contracts as `25 passed, 8 skipped`. The source-dependent checks skipped because their local
`ROOT.parent / "infiquetra-claude-plugins"` lookup pointed beside the disposable worktree rather
than beside the primary Codex clone.

This measurement is what stands in for acceptance criterion 3, which asked for the new assertion to
be run against the stashed pre-fix tree via `git stash` and shown failing, with that output pasted
here. That specific run was not performed and no such artifact exists. The property the criterion
exists to establish is nonetheless recorded above — before the change the source-dependent oracles
did not execute — but the evidence differs in form from what was accepted, and the deviation is
stated here rather than left for a reader to discover.

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

## 2026-08-01 closure re-verification

Issue 67 stayed open after #70 merged, because that pull request's body never referenced `#67` and
carried no closing keyword, so nothing auto-closed it. Before closing, the acceptance criteria were
re-run against `main` at `1327c31` rather than trusting the merge-time evidence above.

| Check | Result |
|---|---|
| Both contract modules, detached worktree outside the workspace, `CODEX_PORT_SOURCE_REPO` unset, no sibling clone reachable | `33 passed`, `0 skipped` |
| `-k port_contract` across `tests/` | `111 passed` (69 when the issue was filed; ports added since) |
| `tests/test_port_source_resolution.py` | `10 passed` |
| `scripts/port_contract.py validate --stage classification` | exit `0` |
| `scripts/validate_codex_plugins.py` | exit `0` |
| `grep -c CODEX_PORT_SOURCE_REPO` on the runbook | `2` |
| `ROOT.parent / "infiquetra-claude-plugins"` remaining under `tests/` | none; single shared resolver in `tests/conftest.py` |

The first row is the decisive one: it is the exact condition the defect describes, and the oracles
now resolve unattended instead of skipping silently.
