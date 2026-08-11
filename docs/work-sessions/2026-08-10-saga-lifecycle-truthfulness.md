# 2026-08-10 — GitHub issue 62 Saga re-entry truthfulness

Branch `fix/issue-62-saga-reentry-truthfulness` implements the three retained units from the reviewed
plan. Outcome behavior and historical GitHub issue 55 remain excluded.

## Completed units

| Unit | Result |
|---|---|
| U2 | Added current `YYYY/MM/DD` session discovery from a bounded first metadata record, exact repository-component matching, deterministic mixed-layout ordering, both current-session exclusion keys, and narrow current user/assistant message extraction. Preserved legacy substring discovery and legacy extraction. |
| U3 | Made the two-pass stop a procedure derived from existing finding/check evidence. `/work` owns the comparison, `/loop` stops the current Drive turn, and `/resume` preserves the operator-decision pause on re-entry. No new lifecycle state was added. |
| U4 | Added the repository-owned `.claude/` ignore rule and proved that Git tracks no path beneath it. |

## Key decisions

- Current discovery reads no more than 65,537 bytes and accepts a complete first record no larger than
  65,536 bytes.
- Current repository matching accepts only a complete component equal to the requested repository name
  or its conventional `<repo>-worktrees` parent.
- Both layouts sort by modification time descending, then session identifier and path ascending, before
  the five-result cap.
- The generated legacy-token inventory moved only the two content hashes required by the edited files;
  its historical digest did not change.

## Files changed

- `.gitignore`
- `plugins/saga/scripts/discover_sessions.py`
- `plugins/saga/scripts/extract_session_skeleton.py`
- `plugins/saga/skills/work/SKILL.md` and `references/test-and-gates.md`
- `plugins/saga/skills/loop/SKILL.md` and `references/drive-and-resume.md`
- `plugins/saga/skills/resume/SKILL.md`, `references/session-forensics.md`, and
  `references/forensic-reconstruction.md`
- `tests/test_saga_session_forensics.py`
- `tests/test_saga_session_context.py`
- `docs/validation/verified-workflows-legacy-token-inventory.json`

## Checks

| Check | Result |
|---|---|
| Focused session-forensics and context tests | 21 passed |
| Ruff on changed Python files | passed |
| `git diff --check` | passed |
| `.claude/` Git ignore, tracked-file, and dry-run broad-stage checks | passed |
| Legacy-token inventory check | passed |
| Codex plugin validation | passed |
| Full suite in the frozen `uv.lock` `.venv` | 2,702 passed, 18 multiprocessing deprecation warnings |

The system interpreter could not collect the full suite because it lacked Pillow and resolved a global
`scripts` package before the repository package. The frozen environment resolved both pre-existing
interpreter issues; no source change was made for them.

## Next step

Create the single local independent-finding fix commit after `96db212` and stop without pushing or
mutating GitHub.
