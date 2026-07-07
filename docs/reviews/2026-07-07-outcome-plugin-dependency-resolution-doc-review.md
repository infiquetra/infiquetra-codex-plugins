# Doc Review: Outcome Plugin Dependency Resolution Plan

## Review Result

The plan is ready to drive implementation.

| field | value |
|-------|-------|
| target path | `docs/plans/2026-07-07-outcome-plugin-dependency-resolution-plan.md` |
| reviewed revision | working tree |
| linked issue | `infiquetra/infiquetra-codex-plugins#18` |
| blocked | no |
| finding priorities | P0: 0, P1: 0, P2: 0, P3: 0 |
| review artifact path | `docs/reviews/2026-07-07-outcome-plugin-dependency-resolution-doc-review.md` |

## Applied Fixes

One safe readiness fix was applied before this artifact was written: U3 now names the cache-installed consumer case precisely. The original wording implied that a direct local marketplace sibling was missing, but `fleet_commons_shim.py` already handles scripts executing from a source or marketplace tree. The actual failing evidence is a cache-installed Saga shim that cannot find `fleet-core` unless it is cache-installed or `FLEET_COMMONS_ROOT` is set.

## Readiness Checks

The requirements map cleanly to implementation units: R1/R2 through U1 and U2, R3 through U3, and R4 safety preservation through U2's explicit non-change to board authorization and retry.

The plan is grounded in repo evidence. `outcome_board_sync.py` derives the mission-control schema path from the Saga module path, `board_progression.py` derives the writer script path from the consumer repo root, and the fleet shim currently lacks a `CODEX_HOME/.tmp/marketplaces` scan for cache-installed consumers.

The sequencing is executable. U1 creates the shared resolver, U2 consumes it in board-sync paths, and U3 updates the existing byte-identical fleet shim plus drift guard independently.

## Residual Risk

The implementation must avoid broadening the autonomous write envelope. Code review should verify that `authorize_write`, idempotency key creation, retry behavior, and the board-sync ledger remain unchanged.
