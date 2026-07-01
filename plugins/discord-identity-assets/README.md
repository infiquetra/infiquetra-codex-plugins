# discord-identity-assets

Reusable Codex workflow for Discord bot visual identity assets.

The plugin keeps creative generation in Codex through the system `image_gen` tool. The bundled Python script handles only deterministic work: target-repo manifest discovery and validation, image normalization, publish-plan signing, Discord API upload and readback, receipts, and runbook writeback.

## What It Publishes

The v1 surface is intentionally narrow:

- bot avatar through the Discord current-user endpoint;
- Developer Portal application icon through the current-application endpoint, with a tested legacy application-id fallback;
- bot profile banner through the Discord current-user endpoint.

It does not create Discord applications, reset tokens, invite bots, update guild/server art, or decrypt vault files.

## CLI

```bash
python3 discord_identity_assets.py discover --repo ../team-mimir --persona mimir
python3 discord_identity_assets.py validate --repo ../team-mimir --mode generate
python3 discord_identity_assets.py preview-plan --repo ../team-mimir --target mimir
python3 discord_identity_assets.py postprocess --repo ../team-mimir --target mimir
python3 discord_identity_assets.py plan-publish --repo ../team-mimir --target mimir
python3 discord_identity_assets.py publish --repo ../team-mimir --target mimir --confirmation-id <id> --publish
```

`publish` resolves the Discord bot token only from the manifest's `token_env` environment variable name. The script never reads Ansible vaults and never writes token material to logs or receipts.

## Manifest

Target repositories own `identity/discord-identity-assets.yml`. The manifest stores non-secret identity and artifact paths. See `references/manifest-schema.md`.

## Validation

```bash
python3 scripts/validate_codex_plugins.py
uv run python -m pytest -q plugins/discord-identity-assets/tests
```
