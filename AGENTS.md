# AGENTS.md

## Purpose

`infiquetra-codex-plugins` is the Codex-native adapter repo for selected Infiquetra
plugins. It is **not** a full mirror of `infiquetra-claude-plugins`; it carries the
Codex-ready plugin surface (`saga`, `deploy`, `mission-control`, `verified-workflows`,
`fleet-core`, `discord-identity-assets`, `home-lab-ops`, `python-toolkit`, `unifi`,
`test-suite`). `mission-control` replaces
the prior SDLC surface and the Saga family replaces the prior document-review surface.
See [README.md](README.md) for the full plugin/version table and layout.

## Commands

```bash
python3 scripts/validate_codex_plugins.py
python3 plugins/test-suite/skills/run-quality-checks/scripts/test_runner.py --dry-run --checks pytest,ruff
python3 -m pytest
```

`scripts/validate_codex_plugins.py` checks manifests, inventory, stale host paths, and
bundled-script boundaries. Run it before opening a PR.

## Repo-Specific Rules

- The Claude-to-Codex port runbook at
  `docs/portability/claude-to-codex-plugin-port-runbook.md` is mandatory for every
  new import or refresh. Bootstrap or load the cycle's JSON port manifest and pass
  its `classification` gate before changing source-derived behavior.
- **This repo is the source of truth after validation and cutover.** Do NOT edit the
  installed Codex cache copies (`.codex/...`) as if they were maintained source — they
  are frozen proof/cache snapshots.
- `plugins/<name>/.codex-plugin/plugin.json` is the Codex manifest; the active skill
  surface lives under `plugins/<name>/skills/`. Keep manifests and `docs/portability/matrix.md`
  in sync when adding, deferring, or blocking a plugin.
- `mission-control` is vendored from `infiquetra-claude-plugins` (canonical). Behavior
  changes to its scripts/config should land in the canonical copy first and stay in sync
  with the other vendored copies; the repo's `test_prompt_alignment.py` guards that
  retired Mount Olympus routing stays out of active surfaces.

## Canon

- Context-audit standard: <https://github.com/infiquetra/infiquetra-context-library/blob/main/docs/ai-context/context-audit-standard.md>
- Instruction surfaces: <https://github.com/infiquetra/infiquetra-context-library/blob/main/docs/ai-context/instruction-surfaces.md>
- SDLC process: <https://github.com/infiquetra/infiquetra-sdlc/blob/main/README.md>
