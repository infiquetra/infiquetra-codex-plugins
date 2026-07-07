# Work Session: Outcome Plugin Dependency Resolution

## Summary

Implemented `infiquetra/infiquetra-codex-plugins#18` by resolving Saga's sibling plugin dependencies from the Codex plugin environment instead of from the consumer repository or a broken cache-relative path.

## Built

U1 added `plugins/saga/scripts/plugin_dependency_resolver.py` with source-checkout, local marketplace, installed-cache sibling, `CODEX_HOME/.tmp` marketplace, and `CODEX_HOME/plugins/cache` lookup support.

U2 routed `outcome_board_sync._default_schema_path()` and `board_progression.default_board_writer()` through that resolver for mission-control schema and script resolution. Board authorization, idempotency, retry, and ledger logic were not changed.

U3 extended the canonical fleet-core shim to let cache-installed consumer plugins find `fleet-core` from `CODEX_HOME/.tmp/marketplaces` when the library plugin is available but not cache-installed, then copied the canonical shim to all registered vendored locations.

## Files Modified

- `docs/engineering-journal/DECISIONS.md`
- `docs/plans/2026-07-07-outcome-plugin-dependency-resolution-plan.md`
- `docs/reviews/2026-07-07-outcome-plugin-dependency-resolution-doc-review.md`
- `plugins/saga/scripts/plugin_dependency_resolver.py`
- `plugins/saga/scripts/outcome_board_sync.py`
- `plugins/saga/scripts/board_progression.py`
- `plugins/fleet-core/scripts/fleet_commons_shim.py`
- `plugins/saga/scripts/fleet_commons_shim.py`
- `plugins/mission-control/scripts/fleet_commons_shim.py`
- `plugins/team-execution/scripts/fleet_commons_shim.py`
- `plugins/unifi/skills/unifi-network/scripts/fleet_commons_shim.py`
- `plugins/unifi/skills/unifi-protect/scripts/fleet_commons_shim.py`
- `plugins/saga/tests/test_plugin_dependency_resolver.py`
- `plugins/saga/tests/test_outcome_board_sync.py`
- `plugins/saga/tests/test_board_progression.py`
- `plugins/fleet-core/tests/test_fleet_commons_resolution.py`

## Checks Run

- `python3 -m pytest -q plugins/saga/tests/test_plugin_dependency_resolver.py plugins/saga/tests/test_outcome_board_sync.py plugins/saga/tests/test_board_progression.py` -> 55 passed
- `python3 -m pytest -q plugins/fleet-core/tests/test_fleet_commons_resolution.py plugins/fleet-core/tests/test_shim_drift.py` -> 13 passed
- `rtk proxy python3 -m pytest -q tests plugins/saga/tests plugins/fleet-core/tests plugins/mission-control/tests plugins/team-execution/tests plugins/unifi/tests plugins/deploy/tests` -> 1236 passed
- `python3 -m ruff check <touched Python files>` -> passed
- `python3 scripts/validate_codex_plugins.py` -> passed
- `git diff --check -- <touched paths>` -> passed

## Broad Check Notes

Plain `python3 -m pytest -q` with system Python fails during collection because the Discord identity asset tests require `PIL`/Pillow and this shell does not have the dev dependency environment active. `uv.lock` exists, but `uv` is not on PATH here.

Full-repo `python3 -m ruff check .` found pre-existing unrelated lint failures outside this change. Filed follow-up defect `infiquetra/infiquetra-codex-plugins#20` on Operations/Shaping rather than expanding #18.

## Next Step

Run the code-review gate, open the PR, and merge if checks remain clean.
