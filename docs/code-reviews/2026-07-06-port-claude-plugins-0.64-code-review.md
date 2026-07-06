# Code Review: port/claude-plugins-0.64

- Target: branch `port/claude-plugins-0.64` vs merge-base `3de7bc1` (origin/main, fetched)
- Reviewed revision: `979993c65c6d74fd484ffba7c181d158316a953f`
- Diff: 160 files, +22,357 / -414
- Mode: programmatic / report-only (called by `/work` as its pre-PR gate)
- Blocked status: **NOT blocked** — no P0/P1 findings
- Plan: `docs/plans/2026-07-06-port-claude-plugin-updates-to-0.64-plan.md`
- Work session: `docs/work-sessions/2026-07-06-port-claude-plugin-updates-to-0.64.md`
- Saga: `task-port-claude-plugin-updates-0-64`

## Lenses run

correctness, security, testing, maintainability/conventions (always-on); reliability (diff adds
retry/backoff and gated GitHub write paths), parity-drift (vendored mission-control sync-by-behavior,
shim byte-identity, Claude-ism leak check). Correctness, security, and parity-drift returned clean
with evidence trails (no shell=True anywhere; argv-list subprocess calls throughout; yaml.safe_load
everywhere; manifest root containment enforced; all six shim copies sha-identical with
`test_shim_drift.py` enforcing it; no `.claude/` leaks; model hints palette-derived by construction).

## Findings (validated)

P2
| # | File | Issue | Reviewer | Confidence | Route |
|---|---|---|---|---|---|
| 1 | plugins/fleet-core/scripts/fleet_commons/render_tier_table.py:76 | Feature-bearing tier-table renderer shipped with zero test coverage; upstream exercises it via test_tier_resolver.py:260-294 and test_tier_vocab_single_source.py:384-386 — coverage the port dropped | testing | 75 | manual |

P3
| # | File | Issue | Reviewer | Confidence | Route |
|---|---|---|---|---|---|
| 2 | plugins/saga/scripts/board_progression.py:135 | Bounded board-write retry loop sleeps zero between attempts (no backoff/jitter); newly authored Codex-side logic (upstream has no such loop) and does not use the fleet_commons retry_backoff primitive this change set standardizes on | reliability | 75 | gated_auto |

> Verdict: **PASS — PR-ready.** No P0/P1. Two validated findings (1×P2 test-coverage, 1×P3 reliability polish), both non-blocking.

## Validator-rejected (inherited upstream, reclassified advisory)

- `retry_backoff.py:73-74` — server-supplied Retry-After hint bypasses the max_delay clamp
  (Retry-After: 999999 → ~11-day synchronous sleep; Retry-After: 0 → tight loop). Byte-identical to
  upstream fleet-commons; inherited by design. **Feed back to infiquetra-claude-plugins (canonical).**
- `board_progression.py:138→168` + `outcome_board_sync.py:299` — crash between the GitHub comment
  POST and the idempotency-ledger write re-posts the comment on resume; `outcome_reconcile.py`
  DRIFT_KINDS covers status/close/reopen only, never comments. Upstream lines 132-177 identical;
  inherited by design. **Feed back to canonical repo.**

## Suppressed (confidence < 75, non-P0): 2

- test_consensus_hardening.py asserts doc prose, not behavior (anchor 50, advisory).
- Inconsistent stderr error prefixes across new saga CLIs (anchor 50).

Also noted, not a finding: `pyproject.toml` line-length=100 without `[tool.ruff.lint]` select means
E501 is never enforced (pre-existing repo-wide condition, advisory).

## Built-vs-planned

- Scope Check: **CLEAN.** Intent: re-implement the Claude `b30e0f2..9470edc` window into Codex
  surfaces per plan U1–U10. Delivered: all 20 named deliverables present (fleet-core uses the
  upstream `scripts/fleet_commons/` package layout); saga at 0.64.0; mission-control `operations`
  rename in config; fleet-core registered in the validator.
- Plan completion: U1–U10 **DONE** (DIFF-verified deliverable presence + orchestrator-run checks).
  R1–R11 covered; no PARTIAL/NOT-DONE items.

## Coverage

- Checks: `python3 scripts/validate_codex_plugins.py` exit 0; `uv run --group dev python -m pytest`
  1258 passed (both run by the orchestrator, not taken from unit self-reports).
- Staleness: `git rev-list 979993c..HEAD --count` = 0 at report time.
- Residual risks: consensus-protocol behavior lives in agent prompts (text drift-guards only);
  the two inherited upstream defects remain live behavior in both repos until fixed canonically.
