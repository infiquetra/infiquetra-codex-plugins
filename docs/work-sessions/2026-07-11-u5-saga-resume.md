# U5 Saga Resume

## Completed

- Treated commits `2133648` and `61753fc` as authoritative. Host-issued rollout context, not a
  child self-report, confirms `review_max` is `gpt-5.6-sol`/`max` and `scan_low` is
  `gpt-5.6-luna`/`low`.
- Recorded KTD22 as the remaining execution limitation: MultiAgent V2 reapplies the parent
  permission profile after role selection. This workspace-write root therefore owns product-source
  changes; no read-only reviewer, scanner, or monitor profile is dispatched beneath it.
- Fixed Saga's explicit-default scalar merge regression. Every supplied persisted, non-list scalar
  `save` option is now parser-derived and marked explicit, excluding sticky identity fields. A
  literal `--destination plan-only` can now supersede a prior `merge` value.

## Evidence

- Commit: `fa6f72e fix(saga): honor explicit default scalar saves`.
- Check: `UV_CACHE_DIR=/private/tmp/codex-uv-cache PYTHONPATH=. uv run pytest
  plugins/saga/tests/test_saga_state.py -q` — 10 passed.
- The local sandbox denies writes below `.codex/saga`, so the superseding Saga tick could not be
  persisted from this task even though repository source writes are permitted. The next root with
  that local-state permission must save the active U5 tick using this session as its evidence.

## U5 Completion

- Canonical new-write vocabulary now uses `inline`, `manual`, and `verified-workflow`; the legacy
  `team-execution` input is normalized on read/save rather than emitted by new Saga ticks.
- Saga records `continuation_mode`, `continuation_ref`, and `identity_mode`. Goal remains an explicit
  continuation binding, not an outcome backend.
- Outcome reconciliation writes `outcome.dispatch.v2` intents and accepts only a typed launched or
  handed-off acknowledgement as settlement. A legacy synthetic leaf commit remains visible as
  `legacy-unverified` and cannot advance dependent work.
- Added the canonical readiness adapter and a single non-mutating SessionStart hook for startup,
  resume, and compact context.
- Recovered an interrupted intent correctly: only acknowledgement and legacy commit states settle
  deduplication, so an intent without an acknowledgement retries rather than remaining permanently
  hidden. Reconciliation appends a v2 acknowledgement and cannot rewrite history.
- Migrated hierarchy and board-sync fixtures from the synthetic v1 commit to a typed v2 launch
  acknowledgement. The source-only Workflow, fork, subagent, and Goal vehicles now halt visibly
  rather than becoming caller-asserted capabilities.
- Added `docs/validation/codex-plugin-modernization-u5.json`, verified all U5 source and Codex rows
  with its evidence, rendered the classification, and regenerated the legacy-token inventory.

## Checks

- `PYTHONPATH=. uv run pytest -q plugins/saga/tests tests/test_outcome_dispatcher.py
  tests/test_outcome_backends.py tests/test_outcome_dispatch_migration.py
  tests/test_outcome_integration.py tests/test_verified_workflow_readiness.py` — 384 passed.
- `python3 scripts/port_contract.py validate --stage unit --unit U5` — passed.
- `python3 scripts/build_legacy_workflow_inventory.py --check` and
  `python3 scripts/validate_codex_plugins.py` — passed.

## Next Step

Commit the completed U5 source, validation, inventory, and rendered-classification changes. Do not
write ignored `.codex/saga` state from this worktree; `.serena/project.yml` remains user-owned and
unstaged.
