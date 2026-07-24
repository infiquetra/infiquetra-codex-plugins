# Cache Replacement Cutover

The installed Codex cache is not the maintained source for Infiquetra plugins.
This repo replaces cache-managed usage only after the gates below pass.

## Gates

1. Trusted source: the checkout remote must be `https://github.com/infiquetra/infiquetra-codex-plugins` or the approved SSH equivalent.
2. Allowlisted inventory: `.agents/plugins/marketplace.json` must list exactly
   `saga`, `deploy`, `mission-control`, `verified-workflows`, `home-lab-ops`,
   `python-toolkit`, `unifi`, `test-suite`, `fleet-core`, and `discord-identity-assets`.
3. Version or integrity pins: each `.codex-plugin/plugin.json` version must match the provenance table, or the change must be documented before cutover.
4. Manifest validation: the Codex plugin validator must pass for each plugin.
5. Repo validation: `python3 scripts/validate_codex_plugins.py` must pass.
6. Runtime smoke: `python3 plugins/test-suite/skills/run-quality-checks/scripts/test_runner.py --dry-run --checks pytest,ruff` must pass.
7. Saga-family proof: the isolated clean-install and seeded migration/rollback lanes must pass;
   the committed proof records only relative inventories and hashes.
8. Rollback and split criteria:
   `docs/cutover/saga-family-rollback-and-split.md` must state that partial
   replacement activation is not a successful merge state.

## Local Replacement Procedure

The exact Codex install command may vary with local Codex plugin tooling. The maintained
procedure is:

1. Validate this repo at the intended commit.
2. Capture and validate the protected local rollback bundle under ignored `.codex/cutover/` state.
3. Install the ten target plugins from this repo-managed marketplace using the Codex plugin CLI.
4. Sync exactly six marker-owned V2 profiles with the expected pre-state digest.
5. Start a fresh Codex session and confirm skill discovery plus exact V2 profile, model, effort,
   provider, and effective-permission readback from `session_meta` and `turn_context`.
6. Keep the previous cache bytes in the rollback bundle until all readback gates pass.

Do not edit files under `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins` as source.

## Migration Map

Exact old-invocation replacement rows live in
`docs/portability/saga-family-known-use-inventory.md`. The active owners are:

- SDLC board, issue, label, milestone, metric, rollout, and field operations:
  `mission-control`.
- Lifecycle routing, planning, handoff, document classification, and review
  entrypoints: `saga`.
- Workflow contracts, native V2 execution, typed results, independent review, and concise gates:
  `verified-workflows`.
- Tag promotion, deployment status, hotfix, rollback, and release-note preview:
  `deploy`.

## Rollback

If repo-managed install validation fails:

1. Restore the exact pre-cutover marketplace, project and user config, managed-agent files, model
   catalog state, workflow state, and installed package bytes from the validated local rollback
   bundle.
2. Restore the exact pre-cutover Fleet Core, Saga, and Verified Workflows versions.
3. Restart Codex and verify the complete pre-state hashes exactly.
4. Record the failed gate and fix this repo before retrying.
