# fleet-core (Codex adapter)

Fleet-commons library plugin: the canonical home for cross-plugin shared primitives and the
canonical copy of the vendored resolution shim. **Scripts-only** — no skills, commands, or
agents. Consumer plugins (`saga`, `team-execution`, `mission-control`, `unifi`) vendor a
byte-identical copy of `fleet_commons_shim.py` and load the shared modules through it.

## What lives here

| Module | Purpose |
|---|---|
| `scripts/fleet_commons_shim.py` | Codex-native resolution ladder — how a plugin finds fleet-core at run time. Canonical copy; vendored byte-identical into consumers (guarded by `tests/test_shim_drift.py`). |
| `scripts/fleet_commons/tier_palette.py` | The model/effort vocabulary (`MODELS`/`EFFORTS`), ladder ops, and the Codex dual-palette accessors (`codex_model`/`codex_effort`/`codex_tier`). |
| `scripts/fleet_commons/tier_resolver.py` | Maps a work shape (or role-tier alias) to a `{model, effort}` tier from `tier_policy.json`. |
| `scripts/fleet_commons/models.json` | Single-source model/effort registry (dual palette). |
| `scripts/fleet_commons/tier_policy.json` | Work-shape → default tier registry. |
| `scripts/fleet_commons/effort_rider.py` | The one seam that decides *how* a resolved effort is honored per spawn kind. |
| `scripts/fleet_commons/retry_backoff.py` | Shared 429 retry/backoff + circuit breaker. |
| `scripts/fleet_commons/render_tier_table.py` | Renders the `/plan` tier table straight from the registry. |

## Codex resolution ladder

The shim resolves fleet-core, first rung wins (provenance rides in the return value):

1. `FLEET_COMMONS_ROOT` env override (an invalid value raises, never falls through).
2. Repo walk-up: an ancestor holding both `.agents/plugins/marketplace.json` (the Codex repo
   marker) and `plugins/fleet-core/`.
3. `~/.codex` plugin cache: `$CODEX_HOME/plugins/cache/<marketplace>/fleet-core/<highest semver>/`.
4. Fail loud with an actionable message.

The Claude host rungs (`~/.claude/.../installed_plugins.json`, `CLAUDE_PLUGIN_ROOT` cache-sibling)
are deliberately dropped — Codex does not maintain that registry, so emulating it would be a
silent dead rung. The divergence from upstream's byte-identical shim is recorded in
`docs/portability/codex-saga-064-drift-classification.md`.

## Dual palette (KTD3)

The Claude tier names (`fable`/`opus`/`sonnet`/`haiku`) remain the lineage vocabulary so upstream
code diffs cleanly; each `models.json` row also carries the active Codex mapping it dispatches
(`gpt-5.5`/`gpt-5.4`/`gpt-5.4-mini`). See `references/tier-palette.md`.

## Tests

```bash
python3 -m pytest plugins/fleet-core/tests
```
