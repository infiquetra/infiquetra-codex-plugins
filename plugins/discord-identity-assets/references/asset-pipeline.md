# Asset Pipeline

Image generation is skill-guided. Scripts receive image files that already exist.

Post-processing performs these deterministic steps:

1. Open generated originals with Pillow.
2. Preserve originals unchanged.
3. Normalize bot avatar and app icon to square PNG, default `512x512`.
4. Normalize bot profile banner to landscape PNG, default `960x540`.
5. Normalize guild/server icon to square PNG, default `512x512`.
6. Normalize guild/server image banner to landscape PNG, default `960x540`.
7. Compute SHA-256, dimensions, and byte size for every final asset.
8. Write a prompt sidecar with approved prompts, prompt sources, technical outputs, profile color metadata when present, and prompt-consistency state.
9. Refuse to publish unless prompt consistency is present and passed.

Avatar and app icon may intentionally share bytes. Avatar and banner may not point to the same final file.

Guild icon and guild image banner may not point to the same final file. Server Profile banner color is metadata only; the script does not automate Discord's UI color picker.
