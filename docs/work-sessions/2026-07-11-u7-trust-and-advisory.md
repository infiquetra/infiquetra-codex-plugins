# Work Session: U7 Trust, Economics, And Advisory Reconciliation

Date: 2026-07-11. Branch: `work/verified-workflows-modernization`. Plan:
`docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`. Saga:
`task-port-recent-claude-plugin-updates`.

## Result

U7 is complete. All 60 frozen source rows assigned to U7 are verified against
`docs/validation/codex-plugin-modernization-u7.json`; the generated classification, frozen-source
verification, U5/U6 overlap evidence, legacy-token inventory, unit-stage port contracts, and plugin
validator are current. The implementation commits are `aea9d65`, `33bd249`, `7cdf67c`, and
`35f6f4b`.

## Behavior Landed

- Added external-engine economics, spend authority, effort accounting, onboarding, recommendation,
  promotion assessment, empty-delivery checks, liveness, output attestation, and typed ordered
  reconciliation.
- Bound successful dispatch to exact engine, variant, transport, invocation, model, effort,
  external-token, liveness, and output-digest evidence. Native Codex agents cannot masquerade as an
  external engine.
- Kept recommendation, offer, and promotion read-only. Repo preference mutation now has the
  separate explicit `engine_preference.py` boundary; onboarding remains dry-run unless an exact
  expected digest authorizes a contained atomic apply.
- Added a bounded external-advisory projection to Verified Workflows. It is persisted in protected
  content-addressed storage, reloaded at gate evaluation, and carries `gate_authority=none`.
  Numeric advisory scores, raw external text, severity, required-role, and validator arithmetic
  cannot pass or block the canonical gate.
- Preserved the persisted v1 names `verified_by_claude`, `FELL_BACK_TO_CLAUDE`, and
  `fell-back-to-claude` with fixture-backed read compatibility, including the retired workflow
  producer-kind value.

## Review And Remediation

The completed architecture and security-scan passes found a competing score-based gate path,
unverified advisory references, mutation inside the offer helper, duplicated intent vocabularies,
open schemas, non-finite economics, Markdown injection, and a public-host DNS trust gap. All were
fixed and covered by negative tests. The proposed v2 manifest migration was rejected for this cycle
because the approved U7 contract explicitly requires preserving `saga.manifest.v1`; fixture tests
now prove the required historical values load unchanged.

A bounded integration child, thread `019f5157-2e6d-7fb2-b60f-68ea32771fd3`, produced a runtime
`turn_context` receipt for `gpt-5.6-terra`, effort `medium`, `read-only`, and the repository cwd. Its
inspection passed. Pytest could not initialize a temp directory inside the host read-only sandbox,
so the root reran the exact surface successfully. The two earlier unbounded Sol review processes
were interrupted after excessive tool exploration and are not treated as review evidence.

## Checks

- U7 focused suite: 368 passed.
- U6 overlap suite: 488 passed before the circular port-contract assertions; 503 passed after the
  evidence refresh.
- U5 overlap suite: 547 passed.
- U6 ten-module branch measurement after U7 HTTP hardening: 488 passed, 88% aggregate branch-aware
  coverage.
- Port-contract tests: 24 passed.
- U5, U6, and U7 unit-stage port contracts: passed.
- Frozen Claude source verification: 156 rows reproduced; frozen target reachable; newer upstream
  remains drift only.
- Changed-path Ruff, legacy-token inventory check, plugin validator, and `git diff --check`: passed.

The unrelated `.serena/project.yml` change remains user-owned and unstaged.

## Next Step

Execute U8 in the root thread: use the plugin-creator cachebuster/reinstall flow, add raw-hook
maintenance, finalize versions and inventories, prove isolated clean install plus seeded
migration/rollback, validate cutover readiness, apply the real-profile transaction, prove a fresh
session, run the formal Saga code-review gate, then commit, open the PR, monitor CI, merge, QA, and
clean up.
