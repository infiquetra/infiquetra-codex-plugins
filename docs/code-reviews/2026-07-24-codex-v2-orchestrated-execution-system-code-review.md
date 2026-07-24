# Code review — Codex V2 orchestrated execution system

- **Branch:** `feat/codex-v2-orchestration`
- **Base:** `f3e1af75d06ac4c64a499f05e99c54903d978f35` (`origin/main`)
- **Reviewed implementation:** `b49c728`
- **Testing follow-up:** `e41d778`
- **Plan:** `docs/plans/2026-07-24-codex-v2-orchestrated-execution-system-plan.md`
- **Mode:** three independent fresh-root Codex V2 reviews with testing-only focused revalidation

## Result

**CLEAN.** Testing, architecture, and security reviewers accepted the full merge-base diff. No
P0-P3 finding remains open, no reviewer declared a hard stop, and all applicable reviewer dimensions
met the plan's minimum and average thresholds.

## Accepted reviewer results

| role | fresh V2 child | profile / runtime | score | verdict |
|---|---|---|---:|---|
| architecture-reviewer | `019f959a-0080-71c0-98f3-5e0599ca22f6` | `review_high`, Sol/high, read-only | 10.0 | accept |
| security-reviewer | `019f9599-ef03-7350-910f-4b2b9885738d` | `review_high`, Sol/high, read-only | 10.0 | accept |
| testing-reviewer | `019f95a5-5b59-7c40-b2b0-8b7bd448ed80` | `review_high`, Sol/high, read-only | 9.8 | accept |

Each child was launched by a separate Sol/max read-only V2 root under the current authenticated Codex
home and project configuration. The roots were independent of the implementation session, child
paths matched their task names, and no alternate authentication home, feature flag, or Hermes
operation was used.

## Remediation ledger

| finding | disposition | validation |
|---|---|---|
| TR2-001: non-profile receipts were under-validated | fixed | exact case runtime tuples, closed receipt fields, parser test, and mutation matrix |
| ARCH-R2-001: ignored nested-repository directory records failed audit capture | fixed | trailing-slash normalization, nested `.git` exclusion, real-worktree capture, regression fixture |
| SEC-R2-01: scoped-context secret detector missed common forms | fixed | shared egress detector, Slack/JWT/ASIA/Bearer/password and undecodable-content cases |
| TR3-001: required capability markers were not case-bound | fixed | per-case positive and negative marker contract plus table-driven mutations |
| ARCH-R3-001: symmetric overlap could authorize an aggregate ancestor | fixed | directional changed-path containment with undeclared-sibling regression |
| SEC-R3-01: HTTP endpoint and authentication were caller-substitutable | fixed | exact canonical registry invocation and executable-host egress derivation |
| SEC-R3-02: GitHub and prefixed credential forms were incomplete | fixed | full maintained GitHub prefix family and prefixed mapping/assignment cases |
| TR3-RV-001: endpoint and auth mutations shared one test | fixed | independent endpoint-only and auth-only parameterized cases |
| TR3-RV-002: `ghp_` and `github_pat_` lacked explicit tests | fixed | payload and scoped-workspace cases for all six maintained prefixes |

## Quality gates

- Full repository: `PYTHONPATH=. uv run python -m pytest -q` — **2,633 passed**.
- Focused final credential-boundary tests — **41 passed**.
- Focused documentation, matrix, and workflow tests — **73 passed**.
- `uv run ruff check .` — passed.
- `python3 scripts/validate_codex_plugins.py` — passed.
- `git diff --check` — passed.
- Live current-auth V2 matrix — six exact profiles, nested delegation, lifecycle operations, bounded
  and no-history context, typed result, Terra/low Luna fallback, and root-only Ultra behavior passed.

## Residual release gates

- GitHub PR checks and merge-SHA verification.
- Supported current-Codex installation and exact source-to-installed readback.
- Fresh-session installed V2/profile smoke proof.
- Pre-state rollback from post-migration state, followed by deliberate V2 reapply and repeated smoke
  proof.

The testing reviewer noted that no numeric line or branch coverage percentage was supplied. It
accepted the behavioral coverage and did not classify that note as an actionable finding.
