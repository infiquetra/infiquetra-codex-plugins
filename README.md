# Infiquetra Codex Plugins

Codex-native adapter repo for selected Infiquetra plugins.

This repo is not a full mirror of `infiquetra-claude-plugins`. It carries the
Codex-ready plugin surface, currently:

| Plugin | Version | Status |
|---|---:|---|
| `saga` | 0.75.17 | active |
| `deploy` | 0.1.1 | active |
| `mission-control` | 2.4.0 | active |
| `verified-workflows` | 1.0.1 | active |
| `fleet-core` | 0.8.5 | active (library) |
| `discord-identity-assets` | 0.2.0 | proof port |
| `home-lab-ops` | 1.0.0 | baseline |
| `python-toolkit` | 1.0.0 | baseline |
| `unifi` | 1.1.0 | baseline |
| `test-suite` | 2.0.0 | proof port |

`mission-control` replaces the prior SDLC surface, Saga-family review flows replace the prior
document-review surface, and Verified Workflows replaces the retired Team Execution package.
Exact migration rows live in
`docs/portability/saga-family-capability-map.md` and
`docs/portability/saga-family-known-use-inventory.md`.

The operator-facing Saga family guide lives in `docs/saga/README.md`.

## GPT-5.6 Agent Compatibility

Codex currently assigns Sol and Terra to unfinished MultiAgent V2 through the model catalog. Restore
the stable named-agent model and effort controls with:

```bash
python3 plugins/fleet-core/scripts/codex_v1_catalog.py install
```

Restart Codex and open a fresh session, then invoke `verified-workflows:select-agent` to choose one
of the five maintained profiles. `/agent` switches among threads after an agent is spawned. Re-run
the install command after model-catalog updates; Ultra remains unverified under this override.

## Layout

- `plugins/<name>/.codex-plugin/plugin.json` is the Codex manifest.
- `plugins/<name>/skills/` is the active Codex skill surface.
- `.agents/plugins/marketplace.json` is the repo-local marketplace.
- `docs/portability/matrix.md` records what is included, deferred, blocked, or unsupported.
- `docs/portability/claude-to-codex-plugin-port-runbook.md` is the mandatory human procedure
  for every upstream import; the cycle JSON under `docs/portability/ports/` is the exhaustive
  machine contract and must pass `classification` before source-derived behavior changes.
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

For a Claude-origin import, follow the mandatory
[Claude-to-Codex plugin port runbook](docs/portability/claude-to-codex-plugin-port-runbook.md).
The runbook owns judgment and stop rules; its bound JSON manifest owns exact source and Codex-drift
coverage, staged evidence, and release gates.
