# Develop the Codex adapter

Keep this plugin thin. Changes belong here only when Codex needs a host-specific
transport or advisory adaptation. Classifier policy belongs in Team Mimir, and
dialogue or profile behavior belongs in the Hermes producer.

## Local setup and checks

From the repository root:

```bash
python3 scripts/validate_codex_plugins.py
python3 -m pytest -q \
  tests/test_prove_codex_plugin_profile.py \
  tests/test_hermes_profile_evolution_docs.py \
  tests/test_validate_codex_plugins.py
python3 -m ruff check \
  plugins/hermes-profile-evolution \
  tests/test_prove_codex_plugin_profile.py \
  tests/test_hermes_profile_evolution_docs.py
```

Tests should exercise the documented request shapes with temporary repositories
and fake producer processes. They must not need real credentials or contact a
live profile.

## Compatibility changes

`conformance/` contains pinned bytes from Team Mimir and the Hermes producer.
When either producer changes its schema, update provenance and fixtures from the
released producer source, then test incompatibility and success paths. Do not
invent optional fields or retain an unversioned fallback.

## Release

Update the manifest version and `CHANGELOG.md` only for a real plugin release.
Run repository validation and the focused tests, publish through the normal
Codex marketplace lifecycle, then verify `codex plugin list --json` in a fresh
session. Never edit installed cache bytes as maintained source.

See [usage](usage.md), [architecture](architecture.md), and
[troubleshooting](troubleshooting.md).
