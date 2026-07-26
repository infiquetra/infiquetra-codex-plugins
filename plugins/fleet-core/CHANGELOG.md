# Changelog — fleet-core (Codex adapter)

All notable changes to the Codex `fleet-core` plugin are documented here.

## 0.13.0 — 2026-07-26

### Added

- Bounded forward-compatibility in the lease registry, ported from Claude `#617` (frozen source
  range `4eb2fe15..1648a21b`). `_tolerant_mapping` returns `(known, extras)` and six container
  boundaries now preserve unrecognized fields instead of raising `RegistryCorruptError`: `leases`,
  `settlements`, `resource_fences`, `session_admission`, `closed_owner_admission`, and the
  top-level `registry` document. This restores cross-runtime handoff from Claude, which had been
  failing on every record because Claude writes an `isolation` field the Codex reader rejected.
- `LeaseBroker.doctor()` — a read-only report naming every preserved unknown field by JSON path,
  with the document's total extras byte count. It reports a corrupt document as *data* rather than
  raising, so an operator diagnostic never aborts on the state it exists to diagnose.
- `LeaseBroker.repair()` — an explicit operator down-migration that strips preserved unknown fields.
  It performs no default action, takes a 0600 backup under the same temp + rename + fsync
  discipline as every other write, strict-revalidates after stripping, and refuses without mutating
  if anything is wrong. That backup is what makes it the rollback path for this feature rather than
  a convenience verb.

### Changed

- The settlement-close CAS now closes the verified live head in place with
  `replace(head, close_receipt=close)` instead of rebuilding a `ResourceFence`. The rebuild dropped
  a newer writer's per-fence extras at exactly the commit that archives the fence — verified by
  restoring the old form and observing `KeyError` on the preserved field.
- Archived closed-fence sidecars are read to EOF under a hard size bound. The previous reader took
  a single 65536-byte `os.read`, so any larger archived record was silently truncated into a JSON
  parse error rather than reported as oversized.

### Notes

- Tolerance is **per-boundary, not file-wide**. Five boundaries stay strictly closed: the four
  retained `_closed_mapping` sites (worktree `resource_ref`, settlement close, legacy settlement
  close, settlement recovery intent) and `FencingToken`, which is pinned by an inline exact-shape
  check at each *embedding* site rather than inside `from_dict`. These are digest-covered
  commitment records and hash-bound resource references: a preserved-then-replayed field there
  would forge a commitment.
- Tolerance is bounded at 64 KiB per document (4x that per archived sidecar, which bypasses the
  document total) and fails closed with a typed error rather than truncating.
- Claude `#616`'s `isolation` surface is deliberately **not** ported —
  `test_isolation_is_not_ported_ktd5` asserts the identifier appears nowhere in either broker.
  Forward-compatibility is the contract; `isolation` is merely the first field to exercise it.

## 0.12.0 — 2026-07-26

### Changed

- Re-port the `audit_store.py` universal fail-closed ancestor walk from Claude `b464d090`: drop the
  home-scope early return, walk every path component from the filesystem anchor down via `lstat`
  (never `resolve` inside the walk), and refuse world-writable components unless also sticky
  (`S_ISVTX`).

### Added

- `on_conflict` admission mode (`"supersede"` default, `"refuse"` new) on
  `_drop_superseded_resource_lease` in `fleet_commons/lease_broker.py`, faithful to Claude
  `b464d090`: refusal is a three-part conjunction (prior lease present, not expired, owner state
  not dead) raising `LeaseConflictError` with `holder_owner_id`, gated below the existing
  retained-settlement and canonically-closed precedence checks.
- Test coverage for the ancestor-guard re-freeze (`test_audit_store.py`) and the refuse-mode
  conjunction, its precedence gates, and closed-value rejection of malformed `on_conflict` input
  (`test_lease_broker.py`) — infiquetra-codex-plugins#45, U2/U3. These artifacts
  (`docs/validation/codex-627-seam-refreeze-u2.json`, `-u3.json`) record post-port results only
  (34 passed, 68 passed); neither carries a `red_first` replay block, so no red-first claim is
  made for U2 or U3.

## 0.11.0 — 2026-07-24

### Changed

- Preserve each native Codex catalog row's `multi_agent_version` in normalized snapshots and
  profile-resolution digests.
- Remove the executable Sol/Terra V1 catalog override; current workflow profiles use native Codex
  V2 selection and runtime readback.

## 0.10.0 — 2026-07-20

### Security - Audit-store ancestor hardening (#43, re-ported from infiquetra-claude-plugins#624)

- `audit_store._ensure_private_dir` now refuses symlinked, world-writable, or uninspectable
  existing path components strictly below the user's home (typed `AuditStoreError`, no silent
  fallback) before creating anything — closing the walk that could previously `mkdir` through a
  symlinked ancestor. The scope test is lexical on the expanded absolute path; home itself and
  out-of-home roots (e.g. sticky system temp directories used by test fixtures) are exempt.
  Group-writable ancestors remain permitted by design, pinned by test.
- Reach differs per branch because `Store.for_root` canonicalizes the root with `resolve()`:
  mode bits survive resolution, so the world-writable refusal covers every caller whose resolved
  root stays lexically below home — resolution that lands the root outside home (a symlinked
  home component onto another volume, an out-of-home clone) skips the walk entirely by the scope
  exemption. Symlink identity does not survive resolution, so the symlink refusal covers direct
  callers and the post-resolve window. The scope boundary is routed upstream for adjudication
  (the guard is byte-identical to its infiquetra-claude-plugins source and stays byte-faithful
  here).

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
