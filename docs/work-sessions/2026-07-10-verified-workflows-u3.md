# Work Session: U3 Verified Workflows Role Profiles

Date: 2026-07-10. Branch: `work/verified-workflows-modernization`. Plan:
`docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`. Saga:
`task-port-recent-claude-plugin-updates`. Effective orchestration: `inline`.

## Outcome

U3 is complete. Verified Workflows now separates 25 versioned logical role lenses from five
catalog-aware Codex execution profiles.

- Preserved all 25 logical roles as `agent-lens` contracts. None qualified as a deterministic
  validator because each still requires judgment or result interpretation.
- Defined closed role, category, independence, boundary, execution-class, behavior, and evidence
  mappings in one registry.
- Rendered exactly `review-max`, `review-high`, `test-medium`, `scan-low`, and `monitor-low` with
  active model and reasoning-effort configuration derived from fleet-core.
- Bound the three frozen reviewer and validator source contracts with exact digests and behavioral
  equivalence tests.
- Added transactional profile rendering and synchronization with explicit isolated targets,
  persistent locking, no-follow filesystem access, pre-state validation, exact readback, recovery,
  stale cleanup controls, rollback, and manual-conflict preservation.
- Proved a first isolated apply installs five profiles, a second apply is unchanged, unrelated bytes
  remain identical, and no cleanup remains pending.
- Characterized the real profile with a live catalog dry run only. Its digest remained
  `1bbcde157bd952f8ec3a8fac54515d543e72ca720611a72ca1e5bcff80e78fdf`; no lock, transaction,
  profile, plugin, or cache state was mutated.

Implementation commit: `5d984680efd5df19843fd5eafaa556b995a5907e`.
Evidence commit: `7e11784ecb2345e34116f832bc25fda7bdc65a69`.
Evidence artifact: `docs/validation/codex-plugin-modernization-u3.json`.

## Review

Independent security and contract reviews covered registry closure, behavior preservation,
catalog use, target resolution, locking, transaction recovery, replacement and removal races,
rollback, special-node substitution, readback, and truthful mutation receipts. All actionable
P0-P3 findings were fixed; both final reviews were clean.

## Checks

- Full configured suite on the implementation SHA: `1554 passed`.
- Focused U3 suite: `114 passed`.
- Port-contract U3 unit gate: passed.
- Current and target-fixture repository validators: passed.
- Generated profile renderer and classification checks: current.
- Scoped Ruff and diff checks: passed.
- Frozen source-window verification: 156 rows reproduced; newer source head remained drift-only.
- Legacy vocabulary inventory: 154 exact entries, 45 historical-evidence entries, and three
  immutable history sentinels.

The unrelated `.serena/project.yml` modification and ignored `.codex/worktrees/` content remained
outside all commits.

## Next Step

Execute U4: add the root-owned workflow DAG interpreter, bounded dispatch intents, start/stop hook
receipts, logical-role and profile attestation, truthful inline fallback, and severity-first gate
evaluation. Installed configuration remains expected policy only until U4 proves the execution
chain.
