# Code Review: Issue #62 Saga Re-entry Truthfulness

This report records the independent, report-only review of the issue #62
implementation branch after the one confirmed review finding was repaired.

## Review-result contract

| Field | Value |
|---|---|
| target | branch `fix/issue-62-saga-reentry-truthfulness` against `origin/main` |
| reviewed revision | `0c40bd0f8315d7a341e770c1e2288feba598d62e` (`fix(saga): count unsupported session records`) |
| merge base | `ed8d74f260f029e41ee4e6e44975f9d70522697a` (`origin/main`) |
| mode | report-only, inline review; no subagent dispatch |
| reviewer session | `019feefa-1a63-7901-a713-cf9bce49608b` |
| reviewer | Codex `gpt-5.6-terra`, high reasoning effort |
| linked issue | `infiquetra/infiquetra-codex-plugins#62` |
| plan | `docs/plans/2026-08-10-saga-lifecycle-truthfulness-plan.md` |
| doc review | `docs/reviews/2026-08-10-saga-lifecycle-truthfulness-doc-review.md` |
| implementation commit | `96db2123b2baea1b83b771f27b447592b1c591ae` (`fix(saga): make re-entry recovery truthful`) |
| repair commit | `0c40bd0f8315d7a341e770c1e2288feba598d62e` |
| blocked | no |
| scope check | CLEAN |

## Original P2 finding and repair

The original review found one P2 defect in the implementation commit's explicit
unknown-record-shape contract. It had two manifestations in
`plugins/saga/scripts/extract_session_skeleton.py`:

1. `handle_codex()` called `.get()` before confirming that parsed JSON was an
   object. Direct probes using a valid top-level JSON list (`[]`) and string
   raised `AttributeError` instead of returning an unsupported record for the
   main loop to count.
2. `handle_response_item()` marked an expected `input_text` or `output_text`
   block as recognized before confirming that its `text` value was a string.
   A current user `input_text` record with `"text": null` completed with
   `unknown: 0`, although it was not a supported message shape.

The repair commit resolves both cases. `handle_codex()` now returns `False`
for a non-dictionary parsed value, and `handle_response_item()` sets
`recognized` only after its expected block has a string `text` value. The three
focused regressions at `tests/test_saga_session_forensics.py:286-316` prove the
list, string, and non-string expected-text cases: each subprocess completes,
emits only its metadata line, and reports `unknown: 1`.

Direct post-repair re-probing sent a top-level list, a top-level string, and an
assistant `output_text` block with `null` text through the extractor. It
completed without a traceback and returned:

```json
{"_meta": true, "lines": 3, "parse_errors": 0, "unknown": 3, "user": 0, "assistant": 0, "tool": 0}
```

The original P2 is resolved. It is not a remaining finding.

## Plan-completion audit

| Unit / requirements | Verdict | Evidence |
|---|---|---|
| U2 / R4-R7, R11-R12 | DONE | `discover_sessions.py` supports both layouts with the 65,537-byte probe, exact component matching, deterministic combined ordering, both exclusion keys, and metadata-only output. `extract_session_skeleton.py` accepts only the current user `input_text` and assistant `output_text` shapes while counting unsupported records. Synthetic tests cover the current and legacy paths. |
| U3 / R8-R9 | DONE | The canonical two-pass procedure is in `plugins/saga/skills/work/references/test-and-gates.md`; `/loop` preserves its terminal pause and `/resume` reconstructs it from ordinary evidence. `tests/test_saga_session_context.py:66-93` pins the shared procedure. |
| U4 / R10 | DONE | `.gitignore` contains `.claude/`; Git reports the probe path ignored and no tracked `.claude/**` path. |

The implementation remains within the reviewed scope. Outcome code and issue #55 remain outside the
diff.

## Final findings

| Priority | Count | Status |
|---|---:|---|
| P0 | 0 | none |
| P1 | 0 | none |
| P2 | 0 | original P2 resolved by `0c40bd0` |
| P3 | 0 | none |

## Evidence and checks

| Check | Result |
|---|---|
| Direct list, string, and assistant-null re-probe | PASS; completed without a traceback and counted all three as unknown |
| Focused session-forensics and Saga context tests | PASS; 21 passed |
| Ruff on changed Python files | PASS |
| Saga document package tests | PASS |
| Saga document formatting tests | PASS |
| `python3 scripts/build_legacy_workflow_inventory.py --check` | PASS; generated inventory is current |
| `python3 scripts/validate_codex_plugins.py` | PASS |
| `git diff --check` | PASS |
| `.claude/` proof | PASS; ignored by `.gitignore`, with no tracked matching path |
| Full suite in the frozen `uv.lock` environment | implementer-recorded: 2,702 passed with 18 existing multiprocessing deprecation warnings; not independently rerun in this review |

## Coverage and remaining risk

Current-layout discovery, extraction privacy boundaries, legacy extraction compatibility, procedural
two-pass guidance, generated inventory, and repository ignore protection were reviewed. The remaining
post-merge check is live orchestration proof that the installed Saga plugin discovers current-layout
sessions; it is not a code finding and requires a separately authorized installed-plugin verification.

> CODE REVIEW COMPLETE — no actionable P0, P1, P2, or P3 findings remain.
