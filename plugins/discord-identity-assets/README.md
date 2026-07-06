# discord-identity-assets

Reusable Codex workflow for Discord bot and guild visual identity assets.

The plugin keeps creative generation in Codex through the system `image_gen` tool. The bundled Python script handles only deterministic work: target-repo manifest discovery and validation, image normalization, publish-plan signing, Discord API upload and readback, receipts, and runbook writeback.

## What It Publishes

The bot identity surface publishes:

- bot avatar through the Discord current-user endpoint;
- Developer Portal application icon through the current-application endpoint, with a tested legacy application-id fallback;
- bot profile banner through the Discord current-user endpoint.

The guild identity surface publishes:

- server icon through the Discord guild endpoint;
- server image banner through the Discord guild endpoint when the guild reports `BANNER` support.

It does not create Discord applications, reset tokens, invite bots, create servers, configure channels or roles, automate Server Profile banner color selection, or decrypt vault files. Server Profile color is recorded as manifest/runbook metadata only.

## CLI

```bash
python3 discord_identity_assets.py discover --repo ../team-mimir --persona mimir
python3 discord_identity_assets.py validate --repo ../team-mimir --mode generate
python3 discord_identity_assets.py preview-plan --repo ../team-mimir --target mimir
python3 discord_identity_assets.py postprocess --repo ../team-mimir --target mimir
python3 discord_identity_assets.py plan-publish --repo ../team-mimir --target mimir
python3 discord_identity_assets.py publish --repo ../team-mimir --target mimir --confirmation-id <id> --publish
```

Guild targets are explicit:

```bash
python3 discord_identity_assets.py scaffold-guild --repo ../team-freya \
  --target asgard \
  --display-name Asgard \
  --expected-guild-name Asgard \
  --guild-id-env ASGARD_GUILD_ID \
  --manage-guild-token-env ASGARD_MANAGE_GUILD_TOKEN \
  --write
python3 discord_identity_assets.py validate --repo ../team-freya --kind guild --mode generate
python3 discord_identity_assets.py preview-plan --repo ../team-freya --kind guild --target asgard
python3 discord_identity_assets.py postprocess --repo ../team-freya --kind guild --target asgard
python3 discord_identity_assets.py plan-publish --repo ../team-freya --kind guild --target asgard
python3 discord_identity_assets.py publish --repo ../team-freya --kind guild --target asgard --confirmation-id <id> --publish
```

`publish` resolves Discord token material only from manifest environment variable names. Guild mode also resolves the guild ID from `guild_id_env`. The script never reads Ansible vaults and never writes token material, authorization headers, or guild ID values to logs or receipts.

## Manifest

Target repositories own `identity/discord-identity-assets.yml`. The manifest stores non-secret identity and artifact paths. See `references/manifest-schema.md`.

## Validation

```bash
python3 scripts/validate_codex_plugins.py
uv run python -m pytest -q plugins/discord-identity-assets/tests
```
