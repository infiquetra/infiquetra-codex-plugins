---
title: Saga Re-entry and Procedural Stop Plan
type: fix
status: active
date: 2026-08-10
origin: docs/brainstorms/2026-07-26-codex-plugin-lifecycle-simplification-requirements.md
---

# Saga Re-entry and Procedural Stop Plan

## Summary

This plan closes GitHub issue #62 with three bounded changes: support current same-machine Codex session discovery and message extraction, stop after two unchanged repair or validation passes using existing evidence, and protect `.claude/` runtime state with one repository ignore rule.

Committed Saga artifacts, Git, GitHub, and Operations board state remain the normal re-entry authority. The plan adds no archive, monitor, status database, closeout ledger, remediation workflow, new canonical state, or automatic cleanup.

---

## Problem Frame

Same-machine recovery is stale against current Codex storage. Discovery only checks repository-named directories one level below the session root (`plugins/saga/scripts/discover_sessions.py:76-100`), but current sessions are stored under `~/.codex/sessions/YYYY/MM/DD/`; extraction only recognizes legacy top-level `user` and `assistant` events (`plugins/saga/scripts/extract_session_skeleton.py:156-220`), so current `response_item` message records produce zero recovered messages.

Repository hygiene is partly corrected but not durable across checkouts. The validator already excludes `.claude` runtime trees (`scripts/validate_codex_plugins.py:352-361`) and tests that contract (`tests/test_validate_codex_plugins.py:928-949`), but `.gitignore` has no `.claude/` rule. The current checkout is protected only by `.git/info/exclude`, which is machine-local, while Git currently tracks zero `.claude` paths.

The repair loop also needs one consistent stopping procedure. Existing work-session and check evidence can show that two completed passes left the same concrete residue, but `/work`, `/loop`, and `/resume` do not yet state one shared stop-and-classify rule.

Child issue #55 is excluded historical evidence. It is closed as `NOT_PLANNED` and its Operations board item is Done: current Outcome V2 opens no run-ledger attempt around dispatch, silent-no-op remains a threshold-zero casualty, and a correct admission-before-intent redesign is outside this charter. Any future admission redesign requires a separate approved plan.

---

## Requirements

The implementation must satisfy the retained scope from issue #62 and its validation comments.

- R4. Session discovery must support both the legacy repository-directory layout and the current date-based `~/.codex/sessions/YYYY/MM/DD/*.jsonl` layout. For current-layout metadata, `--repo` remains a repository folder name and `payload.cwd` matches only when one complete path component equals that name or its conventional `<name>-worktrees` parent; similarly named components must not match. The legacy repository-directory substring scan remains unchanged. Combined candidates must sort by modification time descending, then session identifier ascending, then path ascending before the five-result cap, and current-session exclusion must accept either the true session identifier or filename.
- R5. Session extraction must recover bounded user and assistant text from current `response_item` message records while excluding developer/system content, reasoning, tool calls, and tool results from the current-record path.
- R6. Compatibility tests must use small synthetic records created in tests. No raw operator transcript or transcript fixture file may enter the repository, and unknown record shapes must be counted rather than normalized into a new event model.
- R7. Transcript forensics must remain an explicitly requested, same-machine, last-resort path used only when durable Saga artifacts and a resolvable issue are absent.
- R8. After two completed repair or validation passes leave the same concrete failing evidence, Saga must stop and classify the residue as a product defect, test-oracle defect, or scope expansion, then request one operator decision.
- R9. The two-pass stop must be derived procedurally from existing check output, work-session records, Saga pointers, Git, and GitHub state. It must add no counter, fingerprint field, persisted projection, retry state machine, monitor, or database.
- R10. The repository must ignore `.claude/` through `.gitignore`, and verification must prove that no `.claude` runtime or session artifact is tracked.
- R11. A current-layout candidate must be a regular readable file whose first record is a complete `session_meta` record no larger than 64 kibibytes (KiB). Discovery must read at most the limit plus one byte and omit oversized, malformed, unreadable, or non-`session_meta` candidates.
- R12. Discovery output must contain only the candidate path, session identifier, and modification time.

---

## Key Technical Decisions

These decisions constrain implementation without creating another lifecycle subsystem.

- KTD3. Discover current sessions from one bounded record with exact component matching and one shared order: retain the legacy substring matcher unchanged, but require every current-layout candidate to be a regular readable file and read at most 65,537 bytes to establish that its complete first record is a `session_meta` record no larger than 64 KiB. Match `payload.cwd` without Git or a repository registry only when a complete path component equals `--repo` or `<repo>-worktrees`; omit similarly named and otherwise invalid candidates. Combine both layouts and sort by modification time descending, session identifier ascending, and path ascending, then cap at five and emit only path, session identifier, and modification time.
- KTD4. Parse the two supported message shapes directly: retain the legacy user/assistant handler and add a narrow `response_item` message branch for user `input_text` and assistant `output_text`. Ignore other roles and payload types, count unknowns in metadata, preserve the existing per-message text bound, and create only synthetic in-test records rather than a normalization layer or raw transcript fixtures.
- KTD5. Make the stopping rule procedural: `/work` compares the concrete remaining finding or failing-check identifiers and outcomes after each completed pass; on the second unchanged result it classifies the residue and pauses for one operator decision. `/loop` respects that pause and `/resume` reconstructs it from existing artifacts; none of them stores a new pass counter or status field.
- KTD6. Put `.claude/` in the repository ignore file and prove the negative with Git: `.git/info/exclude` remains local convenience, not repository policy. The implementation does not delete, move, archive, or untrack runtime material because live Git inspection currently shows no tracked `.claude` path.

Execution routing is already operator-approved: the destination is `merge`, and the orchestration backend is `inline`.

---

## Implementation Units

The three retained units are independently reviewable. Their identifiers remain U2-U4 because the removed unit's identifier is not renumbered after plan review; U3 depends on U2 only where both update Saga resume guidance.

### U2. Support current Codex session discovery and bounded extraction

Repair only the two observed compatibility gaps in the last-resort, same-machine recovery tools.

**Goal:** Find current date-layout sessions for the requested repository and extract bounded user/assistant text from current `response_item` messages without collecting unrelated payloads.

**Requirements:** R4, R5, R6, R7, R11, R12.

**Dependencies:** None.

**Files:** `plugins/saga/scripts/discover_sessions.py`; `plugins/saga/scripts/extract_session_skeleton.py`; `plugins/saga/skills/resume/SKILL.md`; `plugins/saga/skills/resume/references/session-forensics.md`; `tests/test_saga_session_forensics.py`; `tests/test_saga_session_context.py` if the durable guidance boundary needs a focused assertion.

**Approach:** Preserve the legacy repository-directory scan. For current date-layout candidates, accept only regular readable files, open each defensively, and read at most 65,537 bytes from the beginning. A candidate survives only when that bounded read contains a complete first record of no more than 65,536 bytes, the record parses as `session_meta`, and its `payload.cwd` identifies the requested repository; omit it on an oversized first record, malformed JSON, a missing or different record type, read/stat failure, or a file-type mismatch.

For current-layout matching, keep `--repo` as the requested repository folder name and compare it against complete components of `payload.cwd`; accept a component equal to that name or exactly equal to `<name>-worktrees`. This admits a nested worktree such as `infiquetra-codex-plugins-worktrees/issue-62-plan` for `--repo infiquetra-codex-plugins` while rejecting a component such as `infiquetra-codex-plugins-other`. Do not call Git, resolve a repository registry, or change the legacy repository-directory substring scan.

Use `payload.id` as the current-layout session identifier and retain the filename stem only as an exclusion key. Apply exclusions, combine candidates from both layouts, and sort the combined set by modification time descending, then session identifier ascending, then path ascending before applying the five-result cap. Return only path, session identifier, and modification time; do not emit the working directory, raw metadata, or transcript content.

Add direct extraction handling for `response_item` records whose payload is a `message` with role `user` or `assistant`. Accept only the corresponding text block types, run them through the existing text cleaner and per-message limit, ignore developer/system, reasoning, tool, and result payloads, and increment an unknown-record count for unsupported shapes. Do not add an intermediate event schema or any repository transcript files.

Update the resume guidance so its documented path and identifier examples describe both layouts, while preserving explicit operator authorization, current-session exclusion, file-mediated scratch extraction, and durable-artifact-first routing.

**Patterns to follow:** `plugins/saga/scripts/discover_sessions.py:35-100` for recency, cap, exclusion, and metadata-only output; `plugins/saga/scripts/extract_session_skeleton.py:50-67` for bounded stats and text cleaning; `plugins/saga/skills/resume/references/session-forensics.md:9-63` for the last-resort and privacy boundary.

**Test scenarios:**

- Happy path: create a temporary `YYYY/MM/DD` session tree whose first synthetic record is a `session_meta` record within 64 KiB and whose `payload.cwd` contains a complete component equal to the requested repository folder name; run discovery and expect only its path, true session identifier, and modification time.
- Worktree match: use `--repo infiquetra-codex-plugins` with a synthetic `payload.cwd` nested under an `infiquetra-codex-plugins-worktrees` component and expect the candidate to match without a Git call or repository registry.
- Boundary: create a synthetic first `session_meta` record exactly 65,536 bytes long, run discovery, and expect the candidate to remain eligible without reading more than 65,537 bytes.
- Omission: create small synthetic candidates with a 65,537-byte first record, malformed JSON, a first record other than `session_meta`, an unreadable file, and a non-regular file; run discovery and expect every invalid candidate to be absent without an exception.
- Compatibility: create a temporary legacy repository-named session directory and expect the existing substring-based discovery behavior to remain unchanged.
- Ordering and cap: create more than five mixed-layout candidates, including a newer `zeta-new` candidate and same-time candidates identified as `alpha`, `beta`, and `beta` whose two `beta` paths sort differently. Assert the exact returned sequence: newer modification time first; at the tied time, `alpha` before both `beta` candidates; between the two `beta` candidates, ascending path; then apply the five-result cap.
- Edge case: exclude one current session by `payload.id` and another by filename stem and expect neither candidate to survive.
- Repository mismatch: use `--repo infiquetra-codex-plugins` with bounded valid metadata whose `payload.cwd` contains only the similarly named component `infiquetra-codex-plugins-other`; expect the candidate to be omitted without exposing that directory in output.
- Extraction happy path: pipe synthetic current user `input_text` and assistant `output_text` records through extraction and expect non-empty bounded user and assistant entries.
- Extraction privacy path: include developer messages, reasoning records, function/tool calls, and tool results and expect none of their content in the current-record extract.
- Extraction compatibility: pass small synthetic legacy user and assistant records and expect the existing bounded extraction behavior to remain.

**Verification:** Focused tests prove both storage layouts and both message shapes, the 64 KiB first-record ceiling and limit-plus-one read, exact current-layout component matching including the conventional worktree parent, rejection of similar names, the shared three-key ordering and cap, omission of invalid candidates, current-session exclusion with real and filename identifiers, and the three-field output boundary. No raw transcript fixture exists in the diff, and the resume documentation still identifies transcript recovery as explicitly authorized last resort.

### U3. Add the derived two-pass stopping procedure

Stop an unchanged repair loop at the existing operator-decision boundary without adding lifecycle state.

**Goal:** Make `/work`, `/loop`, and `/resume` consistently stop after two completed passes leave the same concrete evidence and ask the operator to choose the next scope disposition.

**Requirements:** R8, R9.

**Dependencies:** U2 for the final combined edit to resume guidance.

**Files:** `plugins/saga/skills/work/SKILL.md`; `plugins/saga/skills/work/references/test-and-gates.md`; `plugins/saga/skills/loop/SKILL.md`; `plugins/saga/skills/loop/references/drive-and-resume.md`; `plugins/saga/skills/resume/SKILL.md`; `plugins/saga/skills/resume/references/forensic-reconstruction.md`; `tests/test_saga_session_context.py` or a narrowly named Saga skill-contract test under `tests/`.

**Approach:** Make `test-and-gates.md` the canonical procedure. A pass is complete only when its intended repair or validation ran and produced concrete finding/check identifiers plus outcomes. Compare the current remaining set with the immediately preceding completed pass from the current run or the existing work-session/check evidence; if the same set remains after the second pass, stop before another repair attempt.

Classify the residue as a product defect, test-oracle defect, or scope expansion and ask for one operator decision. Record the ordinary work-session summary and imperative `next_step` already owned by `/work`; do not add a pass counter, evidence fingerprint, status enum, or closeout record. `/loop` must treat that operator-decision pause as terminal for the current Drive turn, and `/resume` must reconstruct it from durable work-session/check evidence rather than infer permission to restart.

**Patterns to follow:** `plugins/saga/skills/work/references/test-and-gates.md:110-137` for existing stop/pause policy; `plugins/saga/skills/loop/references/drive-and-resume.md:24-42` for the across-phase versus within-work boundary; `plugins/saga/skills/resume/references/forensic-reconstruction.md:69-100` for durable precedence and reconstructed-state output.

**Test scenarios:**

- Happy path: one completed pass changes the remaining evidence and the documented procedure allows the bounded repair loop to continue.
- Edge case: two completed passes retain the same finding/check identifiers and outcomes and the contract requires a stop, one of the three classifications, and one operator decision.
- Error / failure path: an interrupted or incomplete pass does not count toward the two-pass threshold.
- Re-entry: existing work-session and check evidence already show two unchanged completed passes; `/resume` preserves the pause and `/loop` does not redispatch `/work` automatically.
- Scope boundary: contract tests prove the changed guidance contains no new persisted counter, fingerprint, monitor, status store, ledger, remediation workflow, or automatic cleanup instruction.

**Verification:** The three skills agree that `/work` owns the comparison, `/loop` stops sequencing, and `/resume` reconstructs the pause, all from existing artifacts and fields.

### U4. Add repository-owned `.claude/` ignore protection

Replace a machine-local safeguard with one portable repository rule.

**Goal:** Ensure runtime/session material under `.claude/` cannot be staged from any checkout and prove that no such material is already tracked.

**Requirements:** R10.

**Dependencies:** None.

**Files:** `.gitignore`.

**Approach:** Add one top-level `.claude/` rule beside the existing `.codex` runtime-state ignores. Do not change `.git/info/exclude`, the validator exclusion set, runtime write locations, or any tracked-file index entry.

**Patterns to follow:** `.gitignore:12-16` for repository-owned runtime-state exclusions; `scripts/validate_codex_plugins.py:352-361` for the already-correct validator treatment of `.claude` as runtime scratch.

**Test scenarios:** Test expectation: none -- this is a repository configuration-only unit; Git's own ignore and tracked-file queries are the behavior oracle.

**Verification:** Git reports `.claude/` as ignored by `.gitignore`, a dry-run broad stage contains no `.claude` path, `git ls-files '.claude/**'` is empty, and repository validation remains green without changing validator behavior.

---

## Risks and Mitigations

The retained risks are bounded to private local data, procedural drift, and repository hygiene.

| risk | mitigation |
|---|---|
| Current-layout discovery reads excessive or private transcript content while determining repository identity | Require a regular readable file, cap the first-record probe at 64 KiB plus one byte, accept only a complete `session_meta` first record, and emit only path, identifier, and modification time |
| File type, permissions, or contents change between validation and read | Treat stat/open/read/parse failures as candidate omission and prove the behavior with small synthetic tests |
| Extraction leaks developer instructions, tool content, or reasoning | Accept only user/assistant message roles and their text block types in the new `response_item` branch; test forbidden payloads with synthetic content |
| The two-pass rule becomes hidden state that can drift | Derive it from two completed evidence sets and existing durable artifacts; prohibit new fields, counters, fingerprints, and stores |
| Adding `.claude/` hides a tracked problem | Prove `git ls-files` is empty before relying on the ignore rule; stop rather than silently untracking anything if that premise changes |

---

## Alternatives Considered

The bounded implementation deliberately rejects broader mechanisms.

| alternative | disposition |
|---|---|
| Build a transcript index, archive, or normalized event layer | Rejected; direct support for two layouts and two message shapes is sufficient for the same-machine fallback |
| Persist pass counts or evidence fingerprints | Rejected; two-pass behavior can be derived from ordinary work-session and check evidence |
| Add progress, closeout, monitoring, or cleanup state | Rejected; committed artifacts, Git, GitHub, and board state already own those facts, and cleanup remains an explicit operator action |
| Treat `.git/info/exclude` as the fix | Rejected; it is local to one shared checkout and provides no protection to other clones or worktrees |

---

## Scope Boundaries

The plan changes only the three retained issue #62 capabilities.

**In scope:** direct support for current date-layout session discovery and `response_item` user/assistant messages; a 64 KiB first-record discovery bound; procedural two-pass stopping; one repository `.claude/` ignore rule; focused tests and guidance needed to keep those behaviors coherent.

**Outside this work's identity:** Outcome dispatch, admission, intent, acknowledgement, casualty, settlement, or reducer code; transcript archives; raw transcript fixtures; event normalization; progress or status databases; monitors; closeout ledgers; remediation workflows; new canonical state; automated branch, artifact, transcript, issue, or runtime cleanup; cross-repository parity work; deployment or runtime activation.

**Deferred to follow-up work:** Any Outcome admission-before-intent redesign requires a separate approved plan. A newly discovered requirement that needs any other excluded mechanism is a scope-expansion classification under U3 and requires a separate operator decision.

---

## Sources

The plan is grounded in current repository and live issue evidence.

- `docs/brainstorms/2026-07-26-codex-plugin-lifecycle-simplification-requirements.md`: the upstream requirements, narrowed by the root-approved issue #62 validation decision.
- GitHub issue #62 and its validation comments: current retained scope.
- GitHub issue #55: closed `NOT_PLANNED` and moved to Done; retained only as excluded historical/stale evidence, not as an implementation source.
- `plugins/saga/scripts/discover_sessions.py:76-100` and `plugins/saga/scripts/extract_session_skeleton.py:156-220`: current layout and record-shape gaps.
- `plugins/saga/skills/resume/references/session-forensics.md:9-102`: same-machine, last-resort, file-mediated recovery boundary.
- `plugins/saga/skills/work/references/test-and-gates.md:110-137`, `plugins/saga/skills/loop/references/drive-and-resume.md:24-42`, and `plugins/saga/skills/resume/references/forensic-reconstruction.md:69-100`: existing stop, ownership, and durable re-entry patterns.
- `.gitignore:12-16`, `scripts/validate_codex_plugins.py:352-361`, and `tests/test_validate_codex_plugins.py:928-949`: repository ignore gap and already-correct validator exclusion.

---

## Validation Strategy

Implementation validation should proceed from the smallest behavior proofs outward.

1. Run the focused synthetic session-discovery/extraction tests, including the 64 KiB first-record boundary, omission cases, approved output fields, and the Saga skill-contract tests for last-resort recovery.
2. Run the focused Saga skill-contract tests for procedural two-pass stopping and durable re-entry.
3. Prove `.claude/` ignore source, broad-stage exclusion, and zero tracked paths directly with Git.
4. Run `python3 scripts/validate_codex_plugins.py` and the complete Python test suite after focused checks pass.

Plan confidence check passed. The plan is Standard, has three bounded units, and is grounded in more than three existing local patterns; no deepening pass is warranted.
