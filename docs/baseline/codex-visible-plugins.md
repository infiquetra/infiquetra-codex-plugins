# Codex-Visible Plugin Baseline

Verified: 2026-06-06

Source catalogs:

- Saga-family source snapshot: `infiquetra-claude-plugins` at
  `16de95c82ccb2ed80d7f11018e1c2e8247a80a7f`
- Original Codex cache evidence: `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins`
- Repo-managed marketplace: `.agents/plugins/marketplace.json`

The active repo-managed Codex inventory is the eight-plugin Saga-family cutover
set below. Installed cache copies are local state only; this repo is the
maintained source after validation.

| Plugin | Version | Expected Namespaced Skills |
|---|---:|---|
| `saga` | 0.21.0 | `saga:office-hours`, `saga:ideate`, `saga:product-review`, `saga:brainstorm`, `saga:spec`, `saga:implementation-spec`, `saga:strategy`, `saga:plan`, `saga:work`, `saga:qa`, `saga:investigate`, `saga:retro`, `saga:resume`, `saga:handoff`, `saga:founder-review`, `saga:ceo-review`, `saga:doc-review`, `saga:code-review`, `saga:optimize`, `saga:loop` |
| `deploy` | 0.1.1 | `deploy:deploy-state`, `deploy:deploy`, `deploy:deploy-status`, `deploy:deploy-notes`, `deploy:deploy-hotfix` |
| `mission-control` | 2.0.0 | `mission-control:board`, `mission-control:flow`, `mission-control:issues`, `mission-control:labels`, `mission-control:metrics`, `mission-control:milestones`, `mission-control:rollout` |
| `team-execution` | 2.2.0 | `team-execution:team-execution`, `team-execution:appsec-audit` |
| `home-lab-ops` | 1.0.0 | `home-lab-ops:ansible-preflight`, `home-lab-ops:inventory-sync`, `home-lab-ops:monitoring-guard`, `home-lab-ops:proxmox-operations`, `home-lab-ops:vault-helper` |
| `python-toolkit` | 1.0.0 | `python-toolkit:python-patterns`, `python-toolkit:python-project-setup`, `python-toolkit:python-testing-patterns` |
| `unifi` | 1.0.0 | `unifi:unifi-network`, `unifi:unifi-protect` |
| `test-suite` | 2.0.0 | `test-suite:run-quality-checks` |

## Replacement Rule

Repo-managed content supersedes the cache only after:

1. All Codex manifests pass plugin validation.
2. `scripts/validate_codex_plugins.py` passes in default, `target-fixture`, and
   `cutover` modes.
3. The `test-suite` dry-run smoke check passes inside this repo.
4. The allowlisted marketplace inventory contains exactly the eight plugins in
   this document.
5. `docs/cutover/cache-replacement.md` and
   `docs/cutover/saga-family-rollback-and-split.md` remain current.

Prior SDLC and document-review invocations are not active aliases in this repo.
Use `docs/portability/saga-family-capability-map.md` and
`docs/portability/saga-family-known-use-inventory.md` for exact replacements.
