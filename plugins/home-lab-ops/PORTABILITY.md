# Portability

Status: included

Lineage:

- Claude: `infiquetra-claude-plugins/plugins/home-lab-ops`
- Antigravity: `infiquetra-antigravity-plugins/plugins/home-lab-ops`
- Codex cache baseline: `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins/home-lab-ops/1.0.0`

Codex differences:

- Active surface is the five skills and their references.
- The Claude top-level agent file is intentionally omitted.
- README describes combined Codex skill usage instead of a host-specific agent.

Validation:

- Expected skills: `ansible-preflight`, `inventory-sync`, `monitoring-guard`, `proxmox-operations`, `vault-helper`.
- Run `python3 scripts/validate_codex_plugins.py`.
