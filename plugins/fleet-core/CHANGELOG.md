# Changelog — fleet-core (Codex adapter)

All notable changes to the Codex `fleet-core` plugin are documented here.

## 0.10.0 — 2026-07-20

### Security - Audit-store ancestor hardening (#43, re-ported from infiquetra-claude-plugins#624)

- `audit_store._ensure_private_dir` now refuses symlinked, world-writable, or uninspectable
  existing path components strictly below the user's home (typed `AuditStoreError`, no silent
  fallback) before creating anything — closing the walk that could previously `mkdir` through a
  symlinked ancestor. The scope test is lexical on the expanded absolute path; home itself and
  out-of-home roots (e.g. sticky system temp directories used by test fixtures) are exempt.
  Group-writable ancestors remain permitted by design, pinned by test.
- Reach differs per branch because `Store.for_root` canonicalizes the root with `resolve()`:
  mode bits survive resolution so the world-writable refusal covers every caller, while symlink
  identity does not, so the symlink refusal covers direct callers and the post-resolve window.
  The docstring states this rather than promising blanket symlink protection.

## 0.9.0 — 2026-07-19

- Port the lease-safe fleet substrate from the frozen Claude source range `a6f3bcff..cf15a09f`
  (#33): `fleet_commons/lease_broker.py` (fleet_lease_registry.v1 protocol 2, TTL/renew/reclaim,
  monotonic epoch and fencing, dead-owner proof), `orphan_evidence.py` (orphan fencing and closing
  fences), `concurrency_policy.py` (admission limits), and `audit_store.py` adapted to a
  runtime-neutral default root (`~/.local/state/infiquetra/delegation-audit`).
- Add the ported broker, orphan-evidence, and audit-store suites plus an authored admission-policy
  contract suite under `plugins/fleet-core/tests/`; cross-runtime state digests are pinned by the
  repo-level conformance matrix.

## 0.8.5 — 2026-07-17

- Add a bounded full-catalog generator that temporarily forces GPT-5.6 Sol and Terra to stable
  MultiAgent V1 while preserving every other model field.
- Add atomic config installation, one-time backup, rollback, readback, UTF-8-without-BOM enforcement,
  and an explicit Ultra compatibility warning.

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
