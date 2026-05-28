# Validation

Run from the repo root.

```bash
python3 scripts/validate_codex_plugins.py
python3 plugins/test-suite/skills/run-quality-checks/scripts/test_runner.py --dry-run --checks pytest,ruff
python3 -m pytest
```

For Codex manifest contract validation:

```bash
for plugin in plugins/*; do
  python3 /Users/jefcox/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py "$plugin"
done
```

The custom validator checks:

- MVP plugin inventory and expected skills.
- Codex manifests and repo marketplace entries.
- Absence of active `.claude-plugin` manifests, top-level Claude command directories, and top-level agent directories.
- Active README and skill docs for stale host cache/source paths.
- Bundled script references stay inside the packaged plugin boundary.
- Portability matrix coverage and allowed statuses.
- Baseline provenance and cutover gates.
