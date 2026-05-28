# Cache Replacement Cutover

The installed Codex cache is not the maintained source for Infiquetra plugins. This repo can
replace cache-managed usage only after the gates below pass.

## Gates

1. Trusted source: the checkout remote must be `https://github.com/infiquetra/infiquetra-codex-plugins` or the approved SSH equivalent.
2. Allowlisted inventory: `.agents/plugins/marketplace.json` must list exactly the six MVP plugins unless the portability matrix was intentionally updated first.
3. Version or integrity pins: each `.codex-plugin/plugin.json` version must match the provenance table, or the change must be documented before cutover.
4. Manifest validation: the Codex plugin validator must pass for each plugin.
5. Repo validation: `python3 scripts/validate_codex_plugins.py` must pass.
6. Runtime smoke: `python3 plugins/test-suite/skills/run-quality-checks/scripts/test_runner.py --dry-run --checks pytest,ruff` must pass.

## Local Replacement Procedure

The exact Codex install command may vary with local Codex plugin tooling. The maintained
procedure is:

1. Validate this repo at the intended commit.
2. Install the six plugins from this repo-managed marketplace or local paths.
3. Start a fresh Codex session and confirm the expected skills are visible.
4. Keep the previous cache directories intact until the new source is confirmed.

Do not edit files under `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins` as source.

## Rollback

If repo-managed install validation fails:

1. Remove the repo-managed plugin install entries.
2. Restart Codex.
3. Confirm the cache-backed baseline skills from `docs/baseline/codex-visible-plugins.md` are visible again.
4. Record the failed gate and fix this repo before retrying.
