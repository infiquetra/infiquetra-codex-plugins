# Code Review: Outcome Plugin Dependency Resolution

## Review Result

No blocking findings.

| field | value |
|-------|-------|
| target | branch diff `origin/main...HEAD` |
| reviewed revision | `c9f9fc646b24e9048b6e482575d73640783dd782` |
| linked issue | `infiquetra/infiquetra-codex-plugins#18` |
| plan | `docs/plans/2026-07-07-outcome-plugin-dependency-resolution-plan.md` |
| work session | `docs/work-sessions/2026-07-07-outcome-plugin-dependency-resolution.md` |
| blocked | no |
| finding priorities | P0: 0, P1: 0, P2: 0, P3: 0 |

## Scope Check

CLEAN.

Intent: fix Saga outcome dependency resolution for installed Codex plugin layouts.

Delivered: added a Saga sibling-plugin resolver, routed mission-control schema/script lookup through it, extended the byte-identical fleet-core shim for `CODEX_HOME/.tmp` marketplace sources, and added offline regression tests for source, marketplace, and installed-cache layouts.

## Plan Completion

| item | state | evidence |
|------|-------|----------|
| U1 add Saga plugin dependency resolver | DONE | `plugins/saga/scripts/plugin_dependency_resolver.py` resolves source/marketplace siblings, installed-cache siblings, `CODEX_HOME/.tmp` marketplace sources, and cache roots. |
| U1 resolver regression tests | DONE | `plugins/saga/tests/test_plugin_dependency_resolver.py` covers source checkout, installed cache, `CODEX_HOME/.tmp`, and missing dependency failure. |
| U2 route board-sync schema lookup through resolver | DONE | `plugins/saga/scripts/outcome_board_sync.py` calls `resolve_plugin_file("mission-control", "config/sdlc-schema.json", from_file=__file__)`. |
| U2 route board writer through resolver | CHANGED | `plugins/saga/scripts/board_progression.py` resolves mission-control lazily on first write and caches the path, preserving the existing per-op failure path more safely than factory-time resolution. |
| U2 board-sync/progression tests | DONE | `plugins/saga/tests/test_outcome_board_sync.py` and `plugins/saga/tests/test_board_progression.py` cover installed-cache sibling schema/script paths. |
| U3 extend fleet-core shim | DONE | `plugins/fleet-core/scripts/fleet_commons_shim.py` adds rung `codex-marketplace-source`; all registered vendored shim copies were updated. |
| U3 fleet shim tests | DONE | `plugins/fleet-core/tests/test_fleet_commons_resolution.py` covers cache-installed consumer -> `CODEX_HOME/.tmp/marketplaces` resolution; `test_shim_drift.py` passed. |

COMPLETION: 6 DONE, 1 CHANGED, 0 PARTIAL, 0 NOT-DONE, 0 UNVERIFIABLE.

## Lenses

| lens | result |
|------|--------|
| correctness | clean; resolver order matches the plan and tests cover the failing installed-cache shape. |
| security | clean; no shell interpolation was introduced, subprocess invocation remains argv-list based, and env-driven paths are local operator trust boundaries. |
| testing | clean; regression coverage exercises source, installed-cache, and marketplace-source layouts plus drift guard. |
| maintainability / conventions | clean; helper is stdlib-only and keeps path logic out of board-sync call sites. |
| reliability | clean; lazy board-writer resolution keeps missing-dependency failures inside the existing retry/fail-record path. |

## Coverage

Suppressed findings: 0.

Residual risks: full `python3 -m pytest -q` under system Python still cannot collect Discord identity asset tests because Pillow is not installed in this shell. Full-repo Ruff has pre-existing unrelated failures, filed separately as `infiquetra/infiquetra-codex-plugins#20`.

Checks reviewed:

- `python3 -m pytest -q plugins/saga/tests/test_plugin_dependency_resolver.py plugins/saga/tests/test_outcome_board_sync.py plugins/saga/tests/test_board_progression.py` -> 55 passed
- `python3 -m pytest -q plugins/fleet-core/tests/test_fleet_commons_resolution.py plugins/fleet-core/tests/test_shim_drift.py` -> 13 passed
- `rtk proxy python3 -m pytest -q tests plugins/saga/tests plugins/fleet-core/tests plugins/mission-control/tests plugins/team-execution/tests plugins/unifi/tests plugins/deploy/tests` -> 1236 passed
- `python3 -m ruff check <touched Python files>` -> passed
- `python3 scripts/validate_codex_plugins.py` -> passed
- `git diff --check -- <touched paths>` -> passed

## Verdict

The branch is PR-ready for #18. No P0/P1 findings remain, and the one implementation change from the plan is safer than the planned factory-time resolution because it preserves existing board-write retry/failure recording.
