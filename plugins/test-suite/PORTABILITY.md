# Portability

Status: proof-port

Lineage:

- Claude: `infiquetra-claude-plugins/plugins/test-suite`
- Antigravity: `infiquetra-antigravity-plugins/plugins/test-suite`

Codex differences:

- Active surface is `skills/run-quality-checks` and its bundled runner script.
- Added runner `--dry-run` for safe package-boundary smoke checks.
- `--checks` now selects requested checks instead of being ignored.
- Skill docs describe implemented flags only.

Validation:

- Expected skill: `run-quality-checks`.
- Smoke check: `python3 plugins/test-suite/skills/run-quality-checks/scripts/test_runner.py --dry-run --checks pytest,ruff`.
- Run `python3 scripts/validate_codex_plugins.py`.
