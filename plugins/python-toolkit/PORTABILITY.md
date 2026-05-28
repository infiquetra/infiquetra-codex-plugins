# Portability

Status: included

Lineage:

- Claude: `infiquetra-claude-plugins/plugins/python-toolkit`
- Antigravity: `infiquetra-antigravity-plugins/plugins/python-toolkit`
- Codex cache baseline: `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins/python-toolkit/1.0.0`

Codex differences:

- Active surface is the three Python skills and shared references.
- The Claude top-level agent file is intentionally omitted.
- README install and support language points at this Codex repo.

Validation:

- Expected skills: `python-patterns`, `python-project-setup`, `python-testing-patterns`.
- Run `python3 scripts/validate_codex_plugins.py`.
