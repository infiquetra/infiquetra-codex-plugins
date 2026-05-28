# Portability

Status: included

Lineage:

- Claude: `infiquetra-claude-plugins/plugins/sdlc-manager`
- Antigravity: `infiquetra-antigravity-plugins/plugins/sdlc-manager`
- Codex cache baseline: `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins/sdlc-manager/1.4.0`

Codex differences:

- Active surface is skills, config, `scripts/sdlc_manager.py`, and script tests.
- Claude command files and the top-level operator agent are intentionally omitted.
- Skill script locations point to the packaged plugin path.
- Per-user defaults now use `~/.codex/sdlc-defaults.json`.
- The rollout field name `claude_md` is retained as an existing SDLC data-model key, not as a Codex host dependency.

Validation:

- Expected skills: `sdlc-board`, `sdlc-flow`, `sdlc-issues`, `sdlc-labels`, `sdlc-metrics`, `sdlc-milestones`, `sdlc-rollout`.
- Run `python3 scripts/validate_codex_plugins.py`.
