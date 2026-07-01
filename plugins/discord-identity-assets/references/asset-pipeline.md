# Asset Pipeline

Image generation is skill-guided. Scripts receive image files that already exist.

Post-processing performs these deterministic steps:

1. Open generated originals with Pillow.
2. Preserve originals unchanged.
3. Normalize avatar and app icon to square PNG, default `512x512`.
4. Normalize profile banner to landscape PNG, default `960x540`.
5. Compute SHA-256, dimensions, and byte size for every final asset.
6. Write a prompt sidecar with approved prompts, prompt sources, technical outputs, and prompt-consistency state.
7. Refuse to publish unless prompt consistency is present and passed.

Avatar and app icon may intentionally share bytes. Avatar and banner may not point to the same final file.
