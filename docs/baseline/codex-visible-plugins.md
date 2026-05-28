# Codex-Visible Plugin Baseline

Verified: 2026-05-27

Source catalogs:

- Claude source repo: `infiquetra-claude-plugins` at `8f5baebb35bb865e3680a457ef02aba5cb418ac4`
- Antigravity source repo: `infiquetra-antigravity-plugins` at `c0c4d04a253e7ee4a6b5407600c8144eea3d781f`
- Codex installed cache root: `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins`

The five baseline plugins below were visible to Codex from cache before this repo was created.
They define the initial replacement baseline, but the cache remains installed state only.

| Plugin | Cache Version | Cache Path | Expected Skills |
|---|---:|---|---|
| `blueprint-reviewer` | 0.1.0 | `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins/blueprint-reviewer/0.1.0` | `blueprint-review`, `issue-review`, `spec-review` |
| `home-lab-ops` | 1.0.0 | `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins/home-lab-ops/1.0.0` | `ansible-preflight`, `inventory-sync`, `monitoring-guard`, `proxmox-operations`, `vault-helper` |
| `python-toolkit` | 1.0.0 | `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins/python-toolkit/1.0.0` | `python-patterns`, `python-project-setup`, `python-testing-patterns` |
| `sdlc-manager` | 1.4.0 | `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins/sdlc-manager/1.4.0` | `sdlc-board`, `sdlc-flow`, `sdlc-issues`, `sdlc-labels`, `sdlc-metrics`, `sdlc-milestones`, `sdlc-rollout` |
| `unifi` | 1.0.0 | `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins/unifi/1.0.0` | `unifi-network`, `unifi-protect` |

## Replacement Rule

Repo-managed content supersedes the cache only after:

1. All Codex manifests pass plugin validation.
2. `scripts/validate_codex_plugins.py` passes.
3. The `test-suite` dry-run smoke check passes inside this repo.
4. The allowlisted marketplace inventory still contains exactly the six MVP plugins.
5. Rollback instructions in `docs/cutover/cache-replacement.md` are still current.

Do not edit the cache paths above as source.
