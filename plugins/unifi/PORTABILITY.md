# Portability

Status: included

Lineage:

- Claude: `infiquetra-claude-plugins/plugins/unifi`
- Antigravity: `infiquetra-antigravity-plugins/plugins/unifi`
- Codex cache baseline: `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins/unifi/1.0.0`

Codex differences:

- Active surface is the two skills, their references, and bundled client scripts.
- Claude command and top-level agent files are intentionally omitted.
- Mutating CLI operations still require explicit `--confirm`.

Validation:

- Expected skills: `unifi-network`, `unifi-protect`.
- Run `python3 scripts/validate_codex_plugins.py`.
