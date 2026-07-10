# Infiquetra Codex Plugins

Codex-native adapter repo for selected Infiquetra plugins.

This repo is not a full mirror of `infiquetra-claude-plugins`. It carries the
Codex-ready plugin surface, currently:

| Plugin | Version | Status |
|---|---:|---|
| `saga` | 0.65.0 | active |
| `deploy` | 0.1.1 | active |
| `mission-control` | 2.3.0 | active |
| `team-execution` | 2.3.0 | active |
| `fleet-core` | 0.5.0 | active (library) |
| `discord-identity-assets` | 0.2.0 | proof port |
| `home-lab-ops` | 1.0.0 | baseline |
| `python-toolkit` | 1.0.0 | baseline |
| `unifi` | 1.1.0 | baseline |
| `test-suite` | 2.0.0 | proof port |

`mission-control` replaces the prior SDLC surface, and Saga-family review flows
replace the prior document-review surface. Exact migration rows live in
`docs/portability/saga-family-capability-map.md` and
`docs/portability/saga-family-known-use-inventory.md`.

The operator-facing Saga family guide lives in `docs/saga/README.md`.

## Layout

- `plugins/<name>/.codex-plugin/plugin.json` is the Codex manifest.
- `plugins/<name>/skills/` is the active Codex skill surface.
- `.agents/plugins/marketplace.json` is the repo-local marketplace.
- `docs/portability/matrix.md` records what is included, deferred, blocked, or unsupported.
- `docs/cutover/cache-replacement.md` records the gates before repo-managed installs replace cached copies.
- `scripts/validate_codex_plugins.py` checks manifests, inventory, stale host paths, and bundled script boundaries.

## Validate

```bash
python3 scripts/validate_codex_plugins.py
python3 plugins/test-suite/skills/run-quality-checks/scripts/test_runner.py --dry-run --checks pytest,ruff
uv run python -m pytest
```

## Source Policy

Treat this repo as the source of truth after validation and cutover. Do not edit
installed Codex cache copies as maintained source.
