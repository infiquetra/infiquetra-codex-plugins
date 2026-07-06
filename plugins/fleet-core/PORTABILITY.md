# fleet-core Portability Notes

## Source

- Source plugin: `fleet-core` (upstream `infiquetra-claude-plugins`, fleet-commons substrate)
- Source commit window: Claude `b30e0f2..9470edc` (2026-07-06 port cycle)
- Upstream version at window close: 0.5.0
- Port status: Codex-native proof port (new Codex plugin, no prior baseline)

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
- **Dual palette (KTD3):** upstream Claude tier names (`fable`/`opus`/`sonnet`/`haiku`) are kept
  as the lineage vocabulary so upstream diffs still apply cleanly; each `models.json` row also
  carries the Codex model mapping (`gpt-5.5`/`gpt-5.4`/`gpt-5.4-mini`) actually dispatched.
- No manifest `skills` field, no `interface.defaultPrompt` — validator treats this plugin as a
  library plugin (`scripts/validate_codex_plugins.py`, `TARGET_EXPECTED_PLUGINS["fleet-core"]`).
- No `.claude-plugin`, command files, or agent markdown carried over — scripts and stdlib-only
  reference modules only.

## Consumers

`plugins/{saga,team-execution,mission-control}/scripts/fleet_commons_shim.py` and
`plugins/unifi/skills/unifi-{network,protect}/scripts/fleet_commons_shim.py` are byte-identical
vendored copies of this plugin's shim, guarded by `plugins/fleet-core/tests/test_shim_drift.py`.
