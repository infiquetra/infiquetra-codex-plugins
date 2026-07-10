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

Fleet-core is the maintained authority for shared Codex model, effort, cost, proof, and workflow
compatibility policy. Consumer shims are synchronized derivatives; installed cache is never source.

## Codex Port Shape

`fleet-core` is a scripts-only library plugin: it has no skills, commands, or agents. It is the
canonical home for cross-plugin shared primitives (model/effort tier palette, tier resolver,
effort rider, retry/backoff) and the canonical copy of `fleet_commons_shim.py`, the resolution
shim consuming plugins (`saga`, `team-execution`, `mission-control`, `unifi`) vendor
byte-identically.

## Codex Differences From Upstream

- **Resolution ladder rewritten for Codex (KTD2):** `FLEET_COMMONS_ROOT` env override → repo
  walk-up (ancestor holding `.agents/plugins/marketplace.json` plus `plugins/fleet-core/`) →
  `~/.codex` plugin cache probe → fail-loud typed error. The Claude-only rungs
  (`~/.claude/.../installed_plugins.json`, `CLAUDE_PLUGIN_ROOT` cache-sibling) are dropped, not
  emulated — Codex has no equivalent registry, so a Claude-shaped rung would be a silent dead
  rung. This divergence is recorded in `docs/portability/codex-saga-064-drift-classification.md`.
- **Catalog-aware classes (KTD2-KTD4):** five leaf execution classes select Sol/Terra/Luna with
  ordered fallbacks against one immutable, allowlisted `codex debug models` snapshot. Scalar
  effort is `low..max`; Ultra is root-only and explicit.
- **Lineage compatibility:** `fable`/`opus`/`sonnet`/`haiku`, the old work-shape resolver, and
  their mappings remain temporary compatibility APIs. They do not select new managed profiles.
- **Proof split:** external-engine bridge receipts and output attestations are shared schemas but
  never attest a Verified Workflows role or effective reasoning effort. Delegation audit/state is
  advisory and writes only contained ignored Codex state.
- No manifest `skills` field, no `interface.defaultPrompt` — validator treats this plugin as a
  library plugin (`scripts/validate_codex_plugins.py`, `TARGET_EXPECTED_PLUGINS["fleet-core"]`).
- No `.claude-plugin`, command files, or agent markdown carried over — scripts and stdlib-only
  reference modules only.

## Consumers

`plugins/{saga,team-execution,mission-control}/scripts/fleet_commons_shim.py` and
`plugins/unifi/skills/unifi-{network,protect}/scripts/fleet_commons_shim.py` are byte-identical
vendored copies of this plugin's shim, guarded by `plugins/fleet-core/tests/test_shim_drift.py`.
