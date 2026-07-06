# Discord API Boundary

The script uses Python standard-library HTTP and an injectable transport for tests.

Bot live publish sequence:

1. Resolve token from `token_env`.
2. Reject suspicious token material before HTTP.
3. `GET /users/@me`; verify `id == discord.expected_bot_user_id`.
4. `GET /applications/@me`; verify `id == discord.application_id`.
5. `PATCH /users/@me` with `avatar`.
6. `PATCH /applications/@me` with `icon`; fallback to `/applications/{application_id}` only when configured and the current-application PATCH fails with a compatibility-style status (`403`, `404`, or `405`).
7. `PATCH /users/@me` with `banner`.
8. Verify readback identifiers are non-empty.

Receipts record endpoint paths and returned identifiers, never authorization headers or token values.

Guild live publish sequence:

1. Resolve token from `manage_guild_token_env`.
2. Resolve guild ID from `guild_id_env`; do not write the resolved value to receipts.
3. Reject suspicious token or guild ID material before HTTP.
4. `GET /users/@me`; verify `expected_actor_user_id` when configured.
5. `GET /guilds/{guild_id}`; verify `name == discord.expected_guild_name` and capture `features`.
6. `PATCH /guilds/{guild_id}` with `icon`.
7. `PATCH /guilds/{guild_id}` with `banner` only when the guild reports `BANNER` support.
8. Verify readback identifiers are non-empty for published surfaces.

The script records redacted endpoint paths such as `/guilds/{guild_id}`. Server Profile color is not part of this API path and remains manifest/runbook metadata only.
