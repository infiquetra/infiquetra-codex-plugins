# Changelog — fleet-core (Codex adapter)

All notable changes to the Codex `fleet-core` plugin are documented here.

## 0.8.4 — 2026-07-11

- Add Codex 5.6 model-catalog projection, five execution classes, scalar effort through `max`,
  root-only Ultra policy, receipt and output-attestation primitives, liveness state, and the closed
  workflow compatibility registry.
- Cut the active workflow consumer from Team Execution to Verified Workflows while retaining
  byte-stable historical reader vocabulary.

## 0.5.0 — 2026-07-06

Initial Codex-native port of the fleet-commons substrate (upstream Claude `fleet-core` 0.5.0,
window `b30e0f2..9470edc`).

### Added

- Scripts-only `fleet-core` plugin: `tier_palette.py`, `tier_resolver.py`, `effort_rider.py`,
  `retry_backoff.py`, `render_tier_table.py`, and the `tier_policy.json` / `models.json`
  registries (ported stdlib-only from upstream).
- **Codex-native resolution ladder** in `fleet_commons_shim.py`: env override → repo walk-up
  (keyed off `.agents/plugins/marketplace.json`) → `~/.codex` plugin-cache probe → fail-loud.
  The Claude host rungs (`installed_plugins.json`, `CLAUDE_PLUGIN_ROOT` cache-sibling) are
  dropped rather than emulated.
- **Codex dual palette (KTD3)**: `models.json` retains the Claude lineage tier names while each
  row carries its active Codex mapping (`codex_model` + `codex_effort`); `tier_palette` exposes
  `codex_model()` / `codex_effort()` / `codex_tier()`.
- Byte-identical vendored `fleet_commons_shim.py` copies in `saga`, the historical workflow package,
  `mission-control`, and both `unifi` skills, guarded by `tests/test_shim_drift.py`.
- Tests: resolution ladder, tier palette + resolver + dual-palette mapping, retry/backoff, and
  the vendored-shim drift guard.
