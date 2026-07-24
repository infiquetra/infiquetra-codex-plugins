# Infiquetra Codex Plugins

Codex-native adapter repo for selected Infiquetra plugins.

This repo is not a full mirror of `infiquetra-claude-plugins`. It carries the
Codex-ready plugin surface, currently:

| Plugin | Version | Status |
|---|---:|---|
| `saga` | 0.79.0+codex.20260724175626 | active |
| `deploy` | 0.1.1 | active |
| `mission-control` | 2.4.2 | active |
| `verified-workflows` | 2.0.0+codex.20260724175626 | active |
| `fleet-core` | 0.11.0+codex.20260724175626 | active (library) |
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

## Codex V2 Agents

Verified Workflows uses Codex V2 directly. The main session orchestrates the live DAG, and six
maintained profiles provide explicit model, effort, permission intent, and role-lens defaults:
`review_max`, `review_high`, `work_high`, `test_medium`, `scan_low`, and `monitor_low`.

Use `verified-workflows:select-agent` for a direct named-agent launch. Approved workflow runs use
`verified-workflows:review-workflow` followed by `verified-workflows:run`. Runtime identity is
accepted only from matching V2 `session_meta` and `turn_context` readback; profile files and prompts
are configuration, not execution proof. `/agent` switches among the root and spawned threads.

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
