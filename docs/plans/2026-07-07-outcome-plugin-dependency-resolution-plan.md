---
title: Fix Outcome Plugin Dependency Resolution For Installed Codex Layouts
type: fix
status: active
date: 2026-07-07
origin: infiquetra/infiquetra-codex-plugins#18
---

# Fix Outcome Plugin Dependency Resolution For Installed Codex Layouts

## Summary

Fix the Saga outcome runtime so autonomous board-sync and fleet-core-backed imports resolve sibling plugins from the Codex plugin environment instead of assuming the consumer repo contains `plugins/mission-control` or that `fleet-core` is already installed into the versioned cache.

## Problem Frame

Issue #18 was filed from the Team Freya outcome: `outcome.py advance ... --autonomous` attempted to execute a mission-control script under the consumer repo, while schema lookup in the installed cache pointed at `saga/mission-control/config/sdlc-schema.json`. The same run required a manual `FLEET_COMMONS_ROOT` for report/attend-adjacent surfaces because the current Codex plugin list exposes `fleet-core` as present in the marketplace source but not installed into the cache.

The source repo already records the desired direction: fleet-core is a Codex `plugins/fleet-core` library plugin, the shim ladder is env -> repo walk-up -> Codex layout -> fail loud, and Saga board autonomy must resolve board status from mission-control schema without hardcoded literals.

## Requirements

R1. `outcome_board_sync` must resolve `mission-control/config/sdlc-schema.json` from source checkout, installed cache, or local marketplace sibling layouts, never from `saga/mission-control`.

R2. `board_progression.default_board_writer()` must resolve `mission-control/scripts/sdlc_manager.py` from the same plugin-environment layouts and must not assume the caller repo owns `plugins/mission-control`.

R3. The fleet-commons shim must support a cache-installed consumer plugin finding `fleet-core` from the local Codex marketplace source when `fleet-core` is available there but not installed into `~/.codex/plugins/cache`, while preserving env override, source checkout walk-up, installed-cache semver selection, and fail-loud behavior.

R4. Autonomous board writes must keep the existing reversibility certificate, idempotency ledger, bounded retry, and fail-loud semantics unchanged.

R5. Regression tests must cover the failing installed-cache path shape, the marketplace sibling path shape, and the existing source-checkout path.

R6. The fix must not edit installed cache copies or hardcode this machine's checkout path.

## Key Technical Decisions

KTD1. Add a Saga-local plugin dependency resolver: mission-control is a sibling plugin dependency of Saga, not a child of the consumer repo. A small stdlib resolver keeps this rule explicit and keeps board-sync code from open-coding path ladders.

KTD2. Resolve from script location first, then Codex homes: source checkouts and local marketplaces are sibling `plugins/<name>` trees, while installed cache is `plugins/cache/<marketplace>/<name>/<version>`. This covers both active Codex layouts observed locally without requiring every library plugin to be installed.

KTD3. Keep fleet-core resolution in the vendored shim: fleet-core is consumed by several plugins, so the marketplace-sibling rung belongs in the byte-identical shim rather than a Saga-only helper.

KTD4. Preserve write safety: path resolution may change which `sdlc_manager.py` is invoked, but `authorize_write`, idempotency keys, bounded retry, and autonomous op allowlisting stay untouched.

## Implementation Units

### U1. Add Saga plugin dependency resolver

Create a small resolver that can locate sibling plugin roots for source, local marketplace, and installed-cache layouts.

**Goal:** Provide one tested API for Saga code to resolve `mission-control` roots without knowing the caller repository.

**Requirements:** R1, R2, R5, R6.

**Dependencies:** none.

**Files:** `plugins/saga/scripts/plugin_dependency_resolver.py`, `plugins/saga/tests/test_plugin_dependency_resolver.py`.

**Approach:** Implement a stdlib-only resolver that starts from a script file path and returns a validated plugin root. Source and local marketplace layouts resolve via an ancestor containing `.agents/plugins/marketplace.json` and `plugins/<plugin>`. Installed-cache layouts resolve from an ancestor shaped as `<marketplace>/<current-plugin>/<version>` by scanning `<marketplace>/<plugin>/<semver>` and selecting the highest valid version. Failures raise a typed, actionable error listing the searched dependency and current file.

**Patterns to follow:** `plugins/saga/scripts/fleet_commons_shim.py` for semver selection and fail-loud style; `plugins/fleet-core/tests/test_fleet_commons_resolution.py` for isolated copied-script fixtures.

**Test scenarios:** Source checkout path from a fake `plugins/saga/scripts` tree resolves a fake `plugins/mission-control`; installed cache path `cache/market/saga/0.64.0/scripts` resolves highest valid `cache/market/mission-control/<version>`; local marketplace path `market/plugins/saga/scripts` resolves `market/plugins/mission-control`; missing dependency raises a message naming the plugin and source file.

**Verification:** The resolver tests pass offline and do not touch GitHub or the real Codex home.

### U2. Route outcome board-sync through the resolver

Replace the two mission-control path assumptions with the resolver while preserving board-sync behavior.

**Goal:** Make autonomous outcome board-sync use the resolved mission-control schema and script in installed Codex layouts.

**Requirements:** R1, R2, R4, R5, R6.

**Dependencies:** U1.

**Files:** `plugins/saga/scripts/outcome_board_sync.py`, `plugins/saga/scripts/board_progression.py`, `plugins/saga/tests/test_outcome_board_sync.py`, `plugins/saga/tests/test_board_progression.py`.

**Approach:** Change `_default_schema_path()` to use the dependency resolver for `mission-control/config/sdlc-schema.json`. Change `default_board_writer()` to resolve `mission-control/scripts/sdlc_manager.py` once when the writer factory is created. Keep the existing injected `schema_path`, `board_writer`, and `runner` seams so tests and callers can still bypass filesystem resolution.

**Patterns to follow:** `outcome_board_sync.reconcile_board()` already converts schema resolution failures into failed records for ready/dispatched leaves; `board_progression.authorize_and_write()` owns safety and retry and must remain unchanged.

**Test scenarios:** Default schema path from an isolated installed-cache Saga copy points at the sibling mission-control schema, not `saga/mission-control`; default board writer from an isolated installed-cache Saga copy invokes the sibling mission-control `sdlc_manager.py`; existing injected-schema and injected-writer tests still pass.

**Verification:** Targeted Saga board-sync/progression tests prove the command paths before running broader Saga tests.

### U3. Extend fleet-core shim for local marketplace source lookup

Teach the byte-identical fleet-commons shim to find `fleet-core` in Codex's local marketplace source when the executing consumer is cache-installed and `fleet-core` is available but not cache-installed.

**Goal:** Remove the need for manual `FLEET_COMMONS_ROOT` when the active Codex marketplace source contains `plugins/fleet-core`.

**Requirements:** R3, R5, R6.

**Dependencies:** none.

**Files:** `plugins/fleet-core/scripts/fleet_commons_shim.py`, vendored `fleet_commons_shim.py` copies, `plugins/fleet-core/tests/test_fleet_commons_resolution.py`.

**Approach:** Add a Codex marketplace-source rung after direct source/marketplace walk-up and before installed-cache lookup. The existing walk-up already handles a script executing inside a source checkout or local marketplace tree; the new rung handles cache-installed scripts by scanning `CODEX_HOME/.tmp/marketplaces/*/plugins/fleet-core` for valid roots. Preserve explicit env override failure behavior and installed-cache highest-semver behavior. Copy the canonical shim to each registered vendored location so the drift guard remains meaningful.

**Patterns to follow:** Existing `test_codex_cache_rung_picks_highest_semver()` isolated shim-copy pattern; `plugins/fleet-core/tests/test_shim_drift.py` explicit vendored copy list.

**Test scenarios:** An isolated cache-installed Saga shim resolves `fleet-core` from a fake `CODEX_HOME/.tmp/marketplaces/<market>/plugins/fleet-core` tree; installed cache still selects highest semver when a cache-installed fleet-core exists; a broken explicit env override still raises immediately; drift guard proves every vendored shim is byte-identical.

**Verification:** Fleet-core resolution tests and shim drift tests pass.

## Scope Boundaries

This fixes dependency resolution only. It does not change outcome DAG semantics, board-sync authorization, mission-control issue verbs, Team Freya outcome content, or the Codex plugin installer itself.

## Deferred to Follow-Up Work

If Codex supports plugin dependency declarations in manifests, declare `fleet-core` as an install dependency for Saga/team-execution/mission-control/unifi in a separate issue. This plan keeps runtime resolution robust without depending on a manifest feature not present in the current plugin metadata.

## Risks & Dependencies

Path ladders can accidentally pick a stale sibling plugin. Mitigation: validate the root by required file path, prefer the nearest source/marketplace sibling before cache, and pick highest semver only inside the same marketplace cache root.

Board writes are externally mutating. Mitigation: this plan does not change authorization or retry logic; tests patch `runner`/writers and never drive live `gh`.

## Sources

- `plugins/saga/scripts/outcome_board_sync.py:116` currently derives schema path from `Path(__file__).parents[2]`, which becomes `saga/mission-control` in installed cache.
- `plugins/saga/scripts/board_progression.py:206` currently builds `repo_root/plugins/mission-control/scripts/sdlc_manager.py`, which points into the consumer repo during `/outcome advance`.
- `plugins/saga/scripts/fleet_commons_shim.py:63` and `plugins/fleet-core/tests/test_fleet_commons_resolution.py:105` cover installed cache but not a cache-installed consumer resolving `fleet-core` from `CODEX_HOME/.tmp/marketplaces`.
- `.agents/plugins/marketplace.json:105` and `README.md` list `fleet-core` as an available library plugin.
- `docs/engineering-journal/DECISIONS.md:3` records fleet-core as the shared Codex library plugin and rejects scattering fleet_commons into every consumer.
