---
name: discord-identity-assets
description: Prepare Discord bot avatar, application icon, and profile banner assets using Codex image generation plus deterministic post-processing, publishing, verification, and receipts.
script: ./scripts/discord_identity_assets.py
---

# Discord Identity Assets

Use this skill when a team repo needs reusable Discord bot visual identity assets.

## Boundary

Codex owns creative image generation through the system `image_gen` tool. The bundled script never invokes image generation. It only validates manifests, normalizes existing image files, builds publish plans, publishes to Discord when explicitly confirmed, verifies API readback, and writes receipts.

Do not use this skill for Discord Developer Portal application creation, token reset, bot invite/guild provisioning, guild/server art, VM creation, Hermes deploy, or broad team bootstrap.

## Workflow

1. Inspect the target repo and read `identity/discord-identity-assets.yml` when it exists.
2. If the manifest is missing, run discovery:
   ```bash
   python3 discord_identity_assets.py discover --repo <team-repo> --persona <persona> --write
   ```
3. Validate before generation:
   ```bash
   python3 discord_identity_assets.py validate --repo <team-repo> --mode generate
   ```
4. Build and present the final avatar and banner prompts plus the preview publish intent before image generation:
   ```bash
   python3 discord_identity_assets.py preview-plan --repo <team-repo> --target <target-id>
   ```
5. Generate images with Codex `image_gen`, preserving originals under the manifest's original paths.
6. Run deterministic post-processing:
   ```bash
   python3 discord_identity_assets.py postprocess --repo <team-repo> --target <target-id>
   ```
7. Ask Codex to inspect prompt consistency for the generated avatar and banner. Record `prompt_consistency: passed` in the prompt sidecar only after that inspection passes.
8. Build a signed publish plan from final asset hashes:
   ```bash
   python3 discord_identity_assets.py plan-publish --repo <team-repo> --target <target-id>
   ```
9. Publish only after the operator has approved the prompt plus publish plan and the needed token environment variable is present:
   ```bash
   python3 discord_identity_assets.py publish --repo <team-repo> --target <target-id> --confirmation-id <id> --publish
   ```

## Safety Rules

- Never put Discord token values in manifests, prompts, receipts, logs, command lines, or runbooks.
- Resolve token material only from the manifest's `token_env` environment variable.
- Reject missing, empty, whitespace-padded, multiline, or non-token-shaped token values before HTTP.
- Verify `GET /users/@me` matches `expected_bot_user_id`.
- Verify `GET /applications/@me` matches `application_id`.
- Stop on the first publish or verification failure and write partial-state evidence. Do not roll back automatically.

## Target Repo Outputs

The manifest chooses exact paths, but the default convention is:

```text
identity/discord-identity-assets.yml
assets/discord/originals/
assets/discord/avatars/
assets/discord/banners/
assets/discord/prompts/
docs/runbooks/discord-identity-assets/
```

## References

- `references/manifest-schema.md`
- `references/asset-pipeline.md`
- `references/discord-api-boundary.md`
- `references/receipt-schema.md`
- `references/runbook-template.md`
