# Portability

Status: included

Lineage:

- Claude: `infiquetra-claude-plugins/plugins/blueprint-reviewer`
- Antigravity: `infiquetra-antigravity-plugins/plugins/blueprint-reviewer`
- Codex cache baseline: `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins/blueprint-reviewer/0.1.0`

Codex differences:

- Active surface is `skills/`, `rubrics/`, and `scripts/lifecycle_review.py`.
- Claude command files are intentionally omitted.
- Skill script locations point to the packaged plugin path.

Validation:

- Expected skills: `blueprint-review`, `issue-review`, `spec-review`.
- Run `python3 scripts/validate_codex_plugins.py`.
