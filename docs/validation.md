# Validation

Run from the repo root.

```bash
python3 scripts/validate_codex_plugins.py
python3 scripts/validate_codex_plugins.py --mode target-fixture
python3 scripts/prove_codex_plugin_profile.py --write-docs
python3 plugins/test-suite/skills/run-quality-checks/scripts/test_runner.py --dry-run --checks pytest,ruff
python3 -m pytest
```

Validation modes:

| Mode | Purpose | Expected timing |
|---|---|---|
| `current` | Validate the active Saga-family repository inventory, active marketplace, proof evidence, migration map, and rollback/split evidence. This is the default mode. | U8 onward and normal CI after cutover. |
| `target-fixture` | Validate `docs/validation/saga-family-target-inventory.json`, source-baseline docs, capability mapping, known-use dispositions, state roots, namespace-proof requirements, and mutation-gate requirements without depending on the active marketplace. | U2 onward. |
| `cutover` | Validate the active tree against the Saga-family target inventory and require cutover proof evidence. | U8-U9 after new plugin roots and marketplace entries are active. |

For Codex manifest contract validation:

```bash
for plugin in plugins/*; do
  python3 /Users/jefcox/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py "$plugin"
done
```

The custom validator checks:

- Current or Saga-family target plugin inventory and expected skills, depending on mode.
- Codex manifests and repo marketplace entries.
- Absence of active `.claude-plugin` manifests, top-level Claude command directories, and top-level agent directories.
- Active README, skill docs, skill references, package references, and portability docs for stale host cache/source paths, with lineage-only allowlists for provenance material.
- Bundled script references stay inside the packaged plugin boundary.
- Portability matrix coverage and allowed statuses.
- Baseline provenance, source-baseline docs, capability-map docs, known-use inventory, target fixture, and cutover gates.
- Target and cutover validation require `team-execution` to be unblocked in the portability matrix.
- Cutover validation requires proof and rollback/split evidence before the old active plugins are considered removable.

Saga-family proof:

- `scripts/prove_codex_plugin_profile.py` writes ignored raw proof JSON under `.codex/proofs/saga-family/<run-id>/`.
- The tracked summary is `docs/validation/saga-family-codex-proof.md`.
- The tracked schema is `docs/validation/saga-family-codex-proof.schema.json`.
- Default mode is deterministic static proof. Use `--install-mode codex-cli` only for an isolated local install proof; it sets `CODEX_HOME` under the ignored proof directory and refuses non-empty profiles.
