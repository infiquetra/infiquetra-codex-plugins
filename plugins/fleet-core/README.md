# fleet-core (Codex adapter)

Fleet Core is the scripts-only shared-library plugin for Infiquetra Codex plugins. It owns common
model-catalog, profile-resolution, effort, retry, compatibility, and audit primitives. It exposes no
skills, commands, or agents.

Consumer plugins (`saga`, `verified-workflows`, `mission-control`, and `unifi`) load Fleet Core
through byte-identical copies of `fleet_commons_shim.py`; `tests/test_shim_drift.py` guards those
copies.

## Maintained Modules

| Module | Purpose |
|---|---|
| `scripts/fleet_commons_shim.py` | Canonical Codex-native Fleet Core resolution ladder. |
| `scripts/fleet_commons/codex_model_catalog.py` | Bounded immutable projection of `codex debug models`, including native `multi_agent_version` metadata. |
| `scripts/fleet_commons/tier_palette.py` | Legacy execution-class compatibility plus the scalar effort and root-only Ultra policies. |
| `scripts/fleet_commons/tier_resolver.py` | Resolves compatibility execution classes against one catalog snapshot. |
| `scripts/fleet_commons/models.json` | Static compatibility-class and root-orchestration policy. |
| `scripts/fleet_commons/tier_policy.json` | Legacy work-shape registry; not the authority for current V2 profiles. |
| `scripts/fleet_commons/effort_rider.py` | Advisory effort compatibility seam; never runtime proof. |
| `scripts/fleet_commons/cost_weights.py` | Validated ordinal lineage-economics grid. |
| `scripts/fleet_commons/retry_backoff.py` | Shared 429 retry/backoff and circuit breaker. |
| `scripts/fleet_commons/bridge_receipt.py` / `output_attestation.py` | External-engine execution and output schemas. |
| `scripts/fleet_commons/delegation_audit.py` / `delegation_state.py` | External-engine corroboration and contained liveness state. |
| `scripts/fleet_commons/workflow_compat.py` | Closed historical Team Execution reader aliases and canonical Verified Workflows writer vocabulary. |
| `scripts/fleet_commons/render_tier_table.py` | Renders compatibility execution-class tables. |

## Codex Resolution Ladder

The shim uses the first valid source:

1. `FLEET_COMMONS_ROOT`; an invalid explicit override fails rather than falling through.
2. A repository ancestor containing `.agents/plugins/marketplace.json` and `plugins/fleet-core/`.
3. The highest semantic version under `$CODEX_HOME/plugins/cache/<marketplace>/fleet-core/`.
4. A clear failure with remediation guidance.

Claude-only registry and cache rungs are intentionally absent. The divergence is documented in
`docs/portability/codex-saga-064-drift-classification.md`.

## Native V2 Catalog Contract

`codex_model_catalog.py` preserves the runtime catalog's native `multi_agent_version` value for
each model as `v1`, `v2`, or `null`; it does not rewrite model rows. The normalized catalog digest
therefore binds the runtime's V2 eligibility alongside slug, effort, visibility, and API support.
Unknown versions fail validation.

Verified Workflows owns the six current V2 profiles and their role mapping. Fleet Core's older
kebab-case execution classes remain readable only for callers that have not yet migrated; they do
not select the active workflow profile set and cannot override the runtime catalog.

## Tests

```bash
python3 -m pytest plugins/fleet-core/tests
```
