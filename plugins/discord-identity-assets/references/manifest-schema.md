# Manifest Schema

Target repos store Discord visual identity state in `identity/discord-identity-assets.yml`.

Required top-level fields:

| field | meaning |
|---|---|
| `schema_version` | integer, `1` for bot-only manifests or `2` for manifests with guild targets |
| `targets[]` | publishable bot identity targets |
| `guild_targets[]` | optional publishable guild/server identity targets, schema version `2` |

Bot target fields:

| field | meaning |
|---|---|
| `id` | stable target id, usually the persona name |
| `display_name` | human label |
| `persona` | team persona id |
| `profile` | source profile name when discovered from `deploy/team_profiles.yml` |
| `prompt_sources[]` | repo-relative source references used to draft prompts |
| `prompts.avatar` | approved avatar prompt |
| `prompts.banner` | approved profile-banner prompt |
| `asset_paths.originals.avatar` | preserved generated avatar original |
| `asset_paths.originals.banner` | preserved generated banner original |
| `asset_paths.finals.avatar` | upload-ready bot avatar PNG |
| `asset_paths.finals.app_icon` | upload-ready app icon PNG; may equal avatar |
| `asset_paths.finals.banner` | upload-ready profile banner PNG |
| `asset_paths.prompt_record` | prompt sidecar written by post-processing |
| `discord.application_id` | Discord application id confirmed before publish |
| `discord.expected_bot_user_id` | bot user id expected from `GET /users/@me` |
| `discord.application_id_candidate` | draft-only candidate discovered from local state |
| `token_env` | environment variable name that will hold the bot token at publish time |
| `evidence.receipt_dir` | receipt and runbook output directory |
| `mode_defaults` | optional mode defaults, such as `generate_only` |

Secret values are forbidden. `token_env` is a name, not a value.

Publish mode requires `discord.application_id`, `discord.expected_bot_user_id`, `token_env`, final paths, prompt record path, and receipt directory.

Guild target fields:

| field | meaning |
|---|---|
| `id` | stable guild target id, such as `asgard` |
| `display_name` | human label |
| `prompt_sources[]` | repo-relative source references used to draft prompts |
| `prompts.icon` | approved server icon prompt |
| `prompts.banner` | approved server image banner prompt |
| `profile_banner_color` | optional Server Profile color recommendation, metadata only |
| `asset_paths.originals.icon` | preserved generated server icon original |
| `asset_paths.originals.banner` | preserved generated server image banner original |
| `asset_paths.finals.icon` | upload-ready server icon PNG |
| `asset_paths.finals.banner` | upload-ready server image banner PNG |
| `asset_paths.prompt_record` | prompt sidecar written by post-processing |
| `discord.expected_guild_name` | guild name confirmed before publish |
| `guild_id_env` | environment variable name that will hold the Discord guild ID at publish time |
| `manage_guild_token_env` | environment variable name that will hold a bot token with Manage Guild permission |
| `expected_actor_user_id` | optional bot user ID expected from `GET /users/@me` |
| `evidence.receipt_dir` | receipt and runbook output directory |
| `mode_defaults` | optional mode defaults, such as `generate_only` |

Secret values are forbidden. `guild_id_env` and `manage_guild_token_env` are names, not values. Publish mode requires `discord.expected_guild_name`, `guild_id_env`, `manage_guild_token_env`, final paths, prompt record path, and receipt directory.
