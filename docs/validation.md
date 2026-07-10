# Validation

Run from the repo root.

```bash
python3 scripts/validate_codex_plugins.py
python3 scripts/validate_codex_plugins.py --mode target-fixture
python3 scripts/build_legacy_workflow_inventory.py --check
python3 scripts/prove_codex_plugin_profile.py --write-docs
python3 plugins/test-suite/skills/run-quality-checks/scripts/test_runner.py --dry-run --checks pytest,ruff
uv run python -m pytest
```

Validation modes:

| Mode | Purpose | Expected timing |
|---|---|---|
| `current` | Validate the live pre-cutover inventory and marketplace. During U9-U7 it requires Team Execution as the sole active workflow package, permits Verified Workflows only as unpublished source, and checks the frozen marketplace and legacy-source digests. This is the default mode. | Development before U8; after U8 the constants move atomically to the released inventory. |
| `target-fixture` | Validate the actual target source and `docs/validation/saga-family-target-inventory.json`: Verified Workflows `1.0.0`, its two namespaces, canonical state root, legacy-read root, and unpublished development lock. It does not install or activate the target. | U9 through the pre-cutover units. |
| `cutover` | Validate source and marketplace against the target inventory, reject the legacy source identity, and require complete cutover proof evidence. | U8 only, after isolated install and rollback proof. |

For Codex manifest contract validation:

```bash
for plugin in plugins/*; do
  python3 /Users/jefcox/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py "$plugin"
done
```

The custom validator checks:

- Separate current and target plugin inventories and expected skills.
- U9 dual-source staging: byte-stable Team Execution source and marketplace activity, plus an
  unpublished Verified Workflows target that is absent from the marketplace.
- Exact legacy-vocabulary classification in
  `docs/validation/verified-workflows-legacy-token-inventory.json`: every surviving path, token
  set, and content digest is bound; known Saga writers are distinct from readers and historical
  evidence cannot be globally renamed without failing validation.
- Codex manifests and repo marketplace entries.
- Absence of active `.claude-plugin` manifests, top-level Claude command directories, and top-level agent directories.
- Active README, skill docs, skill references, package references, and portability docs for stale host cache/source paths, with lineage-only allowlists for provenance material.
- Bundled script references stay inside the packaged plugin boundary.
- Portability matrix coverage and allowed statuses.
- Baseline provenance, source-baseline docs, capability-map docs, known-use inventory, target fixture, and cutover gates.
- Target and cutover validation retain the unblocked `team-execution` portability row as Claude
  lineage while requiring Verified Workflows as the Codex target identity.
- Cutover validation requires proof and rollback/split evidence before the old active plugins are considered removable.

Saga-family proof:

- `scripts/prove_codex_plugin_profile.py` writes ignored raw proof JSON under `.codex/proofs/saga-family/<run-id>/`.
- The tracked summary is `docs/validation/saga-family-codex-proof.md`.
- The tracked schema is `docs/validation/saga-family-codex-proof.schema.json`.
- Default mode is deterministic static proof. Use `--install-mode codex-cli` only for an isolated local install proof; it sets `CODEX_HOME` under the ignored proof directory and refuses non-empty profiles.
