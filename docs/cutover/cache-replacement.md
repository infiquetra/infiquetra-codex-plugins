# Cache Replacement Cutover

The installed Codex cache is not the maintained source for Infiquetra plugins.
This repo replaces cache-managed usage only after the gates below pass.

## Gates

1. Trusted source: the checkout remote must be `https://github.com/infiquetra/infiquetra-codex-plugins` or the approved SSH equivalent.
2. Allowlisted inventory: `.agents/plugins/marketplace.json` must list exactly
   `saga`, `deploy`, `mission-control`, `team-execution`, `home-lab-ops`,
   `python-toolkit`, `unifi`, and `test-suite`.
3. Version or integrity pins: each `.codex-plugin/plugin.json` version must match the provenance table, or the change must be documented before cutover.
4. Manifest validation: the Codex plugin validator must pass for each plugin.
5. Repo validation: `python3 scripts/validate_codex_plugins.py` must pass.
6. Runtime smoke: `python3 plugins/test-suite/skills/run-quality-checks/scripts/test_runner.py --dry-run --checks pytest,ruff` must pass.
7. Saga-family proof: `python3 scripts/prove_codex_plugin_profile.py --write-docs`
   must produce `docs/validation/saga-family-codex-proof.md` and
   `docs/validation/saga-family-codex-proof.schema.json` with no default-profile
   mutation.
8. Rollback and split criteria:
   `docs/cutover/saga-family-rollback-and-split.md` must state that partial
   replacement activation is not a successful merge state.

## Local Replacement Procedure

The exact Codex install command may vary with local Codex plugin tooling. The maintained
procedure is:

1. Validate this repo at the intended commit.
2. Install the eight target plugins from this repo-managed marketplace or local paths.
3. Start a fresh Codex session and confirm the expected skills are visible.
4. Keep the previous cache directories intact until the new source is confirmed.

Do not edit files under `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins` as source.

## Migration Map

Exact old-invocation replacement rows live in
`docs/portability/saga-family-known-use-inventory.md`. The active owners are:

- SDLC board, issue, label, milestone, metric, rollout, and field operations:
  `mission-control`.
- Lifecycle routing, planning, handoff, document classification, and review
  entrypoints: `saga`.
- Reviewer consensus, validator protocol, and degraded serial evidence:
  `team-execution`.
- Tag promotion, deployment status, hotfix, rollback, and release-note preview:
  `deploy`.

## Rollback

If repo-managed install validation fails:

1. Remove the repo-managed plugin install entries.
2. Restart Codex.
3. Confirm the previous local cache-backed skills are visible again where they
   still exist in the user's installed state.
4. Record the failed gate and fix this repo before retrying.
