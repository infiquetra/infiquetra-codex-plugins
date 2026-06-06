# Portability

Status: proof-port

Lineage:

- Claude: `infiquetra-claude-plugins/plugins/mission-control` at `16de95c82ccb2ed80d7f11018e1c2e8247a80a7f`
- Codex replacement target: `sdlc-manager` successor in the Saga-family cutover

Codex differences:

- Active surface is `.codex-plugin/plugin.json`, skills, skill references,
  config, `scripts/sdlc_manager.py`, and script tests.
- Claude command files and the top-level `sdlc-operator` agent are intentionally
  omitted.
- Skill script locations point to the packaged plugin path.
- Per-user defaults use `~/.codex/sdlc-defaults.json`.
- Saga handoff source lookup uses `.codex/saga/` rather than `.claude/saga/`.
- GitHub write paths must present a mutation plan or dry-run first and require
  confirmation before mutation.
- Prepared issue mutation checks `config/target-allowlist.json` before preview
  and before mutation.
- The rollout field name `claude_md` is retained as an existing SDLC data-model
  key, not as a Codex host dependency.

Validation:

- Expected skills: `board`, `flow`, `issues`, `labels`, `metrics`,
  `milestones`, `rollout`.
- Run `python3 scripts/validate_codex_plugins.py`.
- Run `python3 -m pytest plugins/mission-control/tests`.
