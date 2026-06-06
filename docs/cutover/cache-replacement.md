# Cache Replacement Cutover

The installed Codex cache is not the maintained source for Infiquetra plugins. This repo can
replace cache-managed usage only after the gates below pass.

## Gates

1. Trusted source: the checkout remote must be `https://github.com/infiquetra/infiquetra-codex-plugins` or the approved SSH equivalent.
2. Allowlisted inventory: before U8, `.agents/plugins/marketplace.json` may still list the pre-cutover inventory; after U8 it must list exactly `saga`, `deploy`, `mission-control`, `team-execution`, `home-lab-ops`, `python-toolkit`, `unifi`, and `test-suite`.
3. Version or integrity pins: each `.codex-plugin/plugin.json` version must match the provenance table, or the change must be documented before cutover.
4. Manifest validation: the Codex plugin validator must pass for each plugin.
5. Repo validation: `python3 scripts/validate_codex_plugins.py` must pass.
6. Runtime smoke: `python3 plugins/test-suite/skills/run-quality-checks/scripts/test_runner.py --dry-run --checks pytest,ruff` must pass.
7. Saga-family proof: `python3 scripts/prove_codex_plugin_profile.py --write-docs` must produce `docs/validation/saga-family-codex-proof.md` and `docs/validation/saga-family-codex-proof.schema.json` with no default-profile mutation.

## Local Replacement Procedure

The exact Codex install command may vary with local Codex plugin tooling. The maintained
procedure is:

1. Validate this repo at the intended commit.
2. Install the eight target plugins from this repo-managed marketplace or local paths.
3. Start a fresh Codex session and confirm the expected skills are visible.
4. Keep the previous cache directories intact until the new source is confirmed.

Do not edit files under `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins` as source.

## Rollback

If repo-managed install validation fails:

1. Remove the repo-managed plugin install entries.
2. Restart Codex.
3. Confirm the previous cache-backed baseline skills from `docs/baseline/codex-visible-plugins.md` are visible again.
4. Record the failed gate and fix this repo before retrying.
