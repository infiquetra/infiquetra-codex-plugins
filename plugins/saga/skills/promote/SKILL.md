---
name: promote
description: Promote select cross-repo transcendent learnings into the context-library engineering journal as proposed, gated, idempotent entries.
---

# Promote

`saga:promote` is a journal-promotion workflow, not an outcome orchestration
subcommand. It scans repo-local engineering journals, identifies the few lessons
that deserve org-wide status, and prepares context-library journal changes
behind an explicit approval gate.

Use `plugins/saga/scripts/promote_scan.py` as the deterministic backbone:

```bash
python3 plugins/saga/scripts/promote_scan.py scan --workspace-root ~/workspace/infiquetra --json
python3 plugins/saga/scripts/promote_scan.py key --repo <repo-name> --rule '<rule text>'
```

## Rules

- Scan source repo journals read-only.
- Exclude `infiquetra-context-library` from the candidate pool.
- Skip promoted entries carrying `promote-keys` comments so promotion cannot
  feed itself.
- Promote sparingly. `**Transcendent.**` markers are strong nominees, and exact
  recurrence clusters are deterministic evidence, but final clustering and
  distillation remain operator judgment.
- Use a propose-diff-and-wait gate for every destination change.
- Write only proposed diffs for
  `infiquetra-context-library/docs/engineering-journal/LEARNINGS.md`.
- READ-ONLY on the SDLC: never write back to source repos, SDLC state, issues,
  boards, or Saga state.
- Wait for explicit approval before any context-library write.

## Contract

The single source of truth for markers, key generation, promoted entry shape,
ledger comments, and self-feed behavior is:

- `plugins/saga/skills/promote/references/promotion-contract.md`
