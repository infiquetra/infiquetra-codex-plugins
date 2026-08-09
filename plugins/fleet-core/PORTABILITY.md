# fleet-core Portability Notes

## Source

- Source plugin: `fleet-core` (upstream `infiquetra-claude-plugins`, fleet-commons substrate)
- Source commit window: Claude `b30e0f2..9470edc` (2026-07-06 port cycle)
- Upstream version at window close: 0.5.0
- Port status: Codex-native proof port (new Codex plugin, no prior baseline)

## Current Port Contract

The approved 2026-07-10 cycle freezes the next source window at
`9470edca65b1db06d2f7562eeb2d5a9e48c34dec..38742ece89880a6b140be237edad6d3f13c97b54`
and targets fleet-core `0.8.4`. The per-path treatment and preservation obligations live in
`../../docs/portability/ports/2026-07-10-saga-07517.json`. U2 behavior may land before the U8
version and installed-state cutover; the staged contract records that distinction explicitly.

Fleet-core is the maintained authority for shared Codex model/profile resolution, bridge proof,
leases, concurrency, orphan evidence, and workflow compatibility policy. Consumer shims are
synchronized derivatives; installed cache is never source.

## Codex Port Shape

`fleet-core` is a scripts-only library plugin: it has no skills, commands, or agents. It is the
canonical home for cross-plugin shared primitives (model/effort tier palette, tier resolver,
bridge/output proof, leases, and stateless retry/backoff) and the canonical copy of
`fleet_commons_shim.py`, the resolution
shim consuming plugins (`saga`, temporary legacy `team-execution`, staged `verified-workflows`,
`mission-control`, `unifi`) vendor
byte-identically.

## Codex Differences From Upstream

- **Resolution ladder rewritten for Codex (KTD2):** `FLEET_COMMONS_ROOT` env override → repo
  walk-up (ancestor holding `.agents/plugins/marketplace.json` plus `plugins/fleet-core/`) →
  `~/.codex` plugin cache probe → fail-loud typed error. The Claude-only rungs
  (`~/.claude/.../installed_plugins.json`, `CLAUDE_PLUGIN_ROOT` cache-sibling) are dropped, not
  emulated — Codex has no equivalent registry, so a Claude-shaped rung would be a silent dead
  rung. This divergence is recorded in `docs/portability/codex-saga-064-drift-classification.md`.
- **Catalog-aware classes (KTD2-KTD4):** the leaf execution classes `models.json` defines select
  Sol/Terra/Luna with ordered fallbacks against one immutable, allowlisted `codex debug models`
  snapshot. Scalar effort is `low..max`; Ultra is root-only and explicit.
- **Lineage compatibility:** `fable`/`opus`/`sonnet`/`haiku`, the old work-shape resolver, and
  their mappings remain temporary compatibility APIs. They do not select new managed profiles.
- **Workflow identity compatibility:** `workflow_compat.py` owns the closed old-read/new-write
  mapping for the Team Execution-to-Verified Workflows migration. Unknown values fail closed;
  consumers load the registry only through their own fleet-core shim. Surviving old tokens are
  exact-path and digest bound by the generated legacy-workflow inventory.
- **Proof split:** external-engine bridge receipts and output attestations are shared schemas but
  never attest a Verified Workflows role or effective reasoning effort.
- **Native-harness alignment:** Codex 0.146 owns agent lifecycle and liveness. Fleet no longer
  carries delegation/audit state, effort or cost riders, circuit-breaker state, or the tier-table
  renderer. The stateless retry helper remains because UniFi consumes it directly.
- No manifest `skills` field, no `interface.defaultPrompt` — validator treats this plugin as a
  library plugin (`scripts/validate_codex_plugins.py`, `TARGET_EXPECTED_PLUGINS["fleet-core"]`).
- No `.claude-plugin`, command files, or agent markdown carried over — scripts and stdlib-only
  reference modules only.

## Consumers

`plugins/{saga,team-execution,verified-workflows,mission-control}/scripts/fleet_commons_shim.py` and
`plugins/unifi/skills/unifi-{network,protect}/scripts/fleet_commons_shim.py` are byte-identical
vendored copies of this plugin's shim, guarded by `plugins/fleet-core/tests/test_shim_drift.py`.

## 2026-07-19 lease-safe substrate port (#33)

- Port manifest: `docs/portability/ports/2026-07-19-lease-safe-substrate.json` (v3 runbook);
  frozen source range `a6f3bcff..cf15a09f` of `infiquetra-claude-plugins` (#351 dispatch
  settlement, #356 TTL lease broker, #355 resource guard); source versions fleet-core 0.15.0 /
  saga 0.104.0; codex release fleet-core 0.9.0 / saga 0.76.0 (release unit U5).
- `fleet_commons/{lease_broker,orphan_evidence,concurrency_policy}.py` are byte-faithful to the
  frozen source; `audit_store.py` differs only by the runtime-neutral default root. The fleet state
  root resolves via `INFIQUETRA_FLEET_STATE_DIR` → `$XDG_STATE_HOME/infiquetra/fleet-leases` →
  `~/.local/state/infiquetra/fleet-leases` — never `~/.claude`, `~/.codex`, or installed caches.
- Gates: per-port pytest contract `tests/test_lease_safe_substrate_port_contract.py`; six-lens
  ceremony record `docs/validation/lease-safe-substrate-ceremony.md`; unit evidence
  `docs/validation/lease-safe-substrate-u{2,3,4}.json`.
