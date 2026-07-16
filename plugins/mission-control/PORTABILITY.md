# Portability

Status: proof-port

Lineage:

- Claude Mission Control 2.10.1 fail-loud board-move behavior:
  `infiquetra-claude-plugins/plugins/mission-control` at
  `5d4dfb2e1d0be5abbe9f3a693e33d152ba7cfcba`
- Codex adapter Mission Control 2.4.0 port contract:
  `docs/portability/ports/2026-07-14-mission-control-2100.json`
- Codex adapter Mission Control 2.4.2 focused port contract:
  `docs/portability/ports/2026-07-16-mission-control-2101.json`
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
- `flow assign-mimir` keeps the canonical command's exact live-coverage, authority, existing-label,
  one-mutation, and readback semantics. It adds no Codex-only credential, label, or coverage path.
- `board move` preserves provider-read option output and multi-project
  continuation, then returns failure after all results when any selected move
  cannot complete. The CLI propagates that aggregate as exit 1.
- The rollout field name `claude_md` is retained as an existing SDLC data-model
  key, not as a Codex host dependency.

Validation:

- Expected skills: `board`, `flow`, `issues`, `labels`, `metrics`,
  `milestones`, `rollout`.
- Run `python3 scripts/validate_codex_plugins.py`.
- Run `python3 -m pytest plugins/mission-control/tests`.
