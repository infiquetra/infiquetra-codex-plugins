# Discord API Boundary

The script uses Python standard-library HTTP and an injectable transport for tests.

Live publish sequence:

1. Resolve token from `token_env`.
2. Reject suspicious token material before HTTP.
3. `GET /users/@me`; verify `id == discord.expected_bot_user_id`.
4. `GET /applications/@me`; verify `id == discord.application_id`.
5. `PATCH /users/@me` with `avatar`.
6. `PATCH /applications/@me` with `icon`; fallback to `/applications/{application_id}` only when configured and the current-application PATCH fails with a compatibility-style status (`403`, `404`, or `405`).
7. `PATCH /users/@me` with `banner`.
8. Verify readback identifiers are non-empty.

Receipts record endpoint paths and returned identifiers, never authorization headers or token values.
