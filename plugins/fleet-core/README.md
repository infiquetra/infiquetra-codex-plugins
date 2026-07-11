# fleet-core (Codex adapter)

Fleet-commons library plugin: the canonical home for cross-plugin shared primitives and the
canonical copy of the vendored resolution shim. **Scripts-only** — no skills, commands, or
agents. Consumer plugins (`saga`, `verified-workflows`, `mission-control`, `unifi`) vendor a
byte-identical copy of `fleet_commons_shim.py` and load the shared modules through it.

## What lives here

| Module | Purpose |
|---|---|
| `scripts/fleet_commons_shim.py` | Codex-native resolution ladder — how a plugin finds fleet-core at run time. Canonical copy; vendored byte-identical into consumers (guarded by `tests/test_shim_drift.py`). |
| `scripts/fleet_commons/codex_model_catalog.py` | Bounded, allowlisted, immutable projection of `codex debug models`. |
| `scripts/fleet_commons/tier_palette.py` | Five Codex execution classes, scalar `low..max`, root-only Ultra policy, plus temporary lineage accessors. |
| `scripts/fleet_commons/tier_resolver.py` | Resolves execution classes against one catalog snapshot; retains the old work-shape API only for migration compatibility. |
| `scripts/fleet_commons/models.json` | Single static source for execution-class and root-orchestration policy. |
| `scripts/fleet_commons/tier_policy.json` | Temporary legacy work-shape registry; not authoritative for new Codex profiles. |
| `scripts/fleet_commons/effort_rider.py` | Advisory rider compatibility seam; never effective-effort proof. |
| `scripts/fleet_commons/cost_weights.py` | Validated ordinal lineage-economics grid over the scalar effort ladder. |
| `scripts/fleet_commons/retry_backoff.py` | Shared 429 retry/backoff + circuit breaker. |
| `scripts/fleet_commons/bridge_receipt.py` / `output_attestation.py` | External-engine execution and output proof schemas. |
| `scripts/fleet_commons/delegation_audit.py` / `delegation_state.py` | Advisory external-engine corroboration and contained liveness state. |
| `scripts/fleet_commons/workflow_compat.py` | Closed Team Execution-to-Verified Workflows reader aliases and canonical-write vocabulary. |
| `scripts/fleet_commons/render_tier_table.py` | Renders static and catalog-resolved execution-class tables. |

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

## Execution classes and lineage compatibility

New Codex profiles select one of `review-max`, `review-high`, `test-medium`, `scan-low`, or
`monitor-low`, then resolve it against the runtime model catalog. The old
`fable`/`opus`/`sonnet`/`haiku` vocabulary and mappings remain only so existing consumers stay
green until their planned migration. See `references/tier-palette.md`.

`verified-workflows` is the active workflow consumer. Historical Team Execution values remain
readable through one compatibility registry, but the retired package is no longer published or
installed alongside it.

## Tests

```bash
python3 -m pytest plugins/fleet-core/tests
```
