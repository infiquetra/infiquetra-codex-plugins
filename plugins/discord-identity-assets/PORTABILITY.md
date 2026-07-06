# Portability

Status: proof-port

Lineage:

- Claude: none; this is a Codex-born plugin extracted from home-lab and team-norns operating evidence.
- Antigravity: none.
- Legacy references: `home-lab/scripts/setup_bot_assets.py`, `home-lab/scripts/upload_ai_icons.py`, and Norns runbook evidence.

Codex differences:

- Codex-native `image_gen` remains the generation mechanism; scripts do not call Replicate, OpenAI, or any image model.
- Target repositories own `identity/discord-identity-assets.yml`; home-lab vault paths and hard-coded prompt dictionaries are not reusable state.
- Discord tokens resolve from environment variables only at publish time.
- Discord guild IDs also resolve from environment variables only at publish time, and receipts redact the resolved value.
- Discord publish requires ownership preflight, signed publish-plan confirmation, API readback, redaction, and receipt writeback for bot and guild surfaces.
- Guided Developer Portal provisioning, server creation, channel/role setup, Server Profile color automation, and broad team bootstrap orchestration are deferred.

Validation:

- Expected skill: `discord-identity-assets`.
- Run `python3 scripts/validate_codex_plugins.py`.
- Run `uv run python -m pytest -q plugins/discord-identity-assets/tests`.
