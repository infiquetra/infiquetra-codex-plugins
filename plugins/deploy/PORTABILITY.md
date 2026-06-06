# Portability

Status: proof-port

Lineage:

- Claude: `infiquetra-claude-plugins/plugins/deploy` at `16de95c82ccb2ed80d7f11018e1c2e8247a80a7f`

Codex differences:

- Active surface is `.codex-plugin/plugin.json`, skills, scripts, tests, README,
  and changelog.
- Claude command files and the release-orchestrator agent are intentionally
  omitted.
- Command-origin behavior is represented as Codex skills:
  `deploy`, `deploy-status`, `deploy-notes`, and `deploy-hotfix`.
- `scripts/mint_tag.py` prints a preview and requires `--confirm-plan` matching
  the previewed repo, tag, and ref before any non-dry-run tag push.
- Deploy does not store GitHub tokens. It relies on operator `gh` and git
  credentials and must not log secrets.

Validation:

- Expected skills: `deploy-state`, `deploy`, `deploy-status`, `deploy-notes`,
  `deploy-hotfix`.
- Run `python3 scripts/validate_codex_plugins.py`.
- Run `python3 -m pytest plugins/deploy/tests`.
