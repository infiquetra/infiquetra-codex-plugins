---
title: Make lifecycle state, re-entry, and closeout truthful
repo: infiquetra-codex-plugins
type: capability
team: asgard
project: operations
status: Shaping
labels: capability, hermes-task, needs-plan
risk: medium
handoff_maturity: requirements-ready
approval_state: approved
---

# Make lifecycle state, re-entry, and closeout truthful

### Objective

`improve-codex-plugins` — make Saga reject, recover, report, and close work from existing truth without adding another status system.

### Intent

Make admission fail before attempt or halt mutation, and ensure every admitted dispatch settles without contradictory durable state. After two passes with the same remaining evidence, classify the residue and ask for one operator decision instead of extending the repair loop.

Keep durable Saga artifacts and GitHub state as normal re-entry authority. Repair current Codex transcript discovery and bounded extraction only as a same-machine last resort, then derive progress and closeout from those artifacts, checks, Git, and board state without a new monitor or state store.

Reuse defects #55 and #56 as independently verifiable children.

### Out-of-scope / non-goals

- A general transcript archive, analytics system, or normalized event model.
- A new progress database, background monitor, closeout ledger, or remediation workflow.
- Automatic deletion of branches, runtime artifacts, or transcript-like files.
- Making local cache or raw transcripts authoritative over committed artifacts and verified GitHub state.
- Redesigning Outcome as a product.

### Files expected to change

- `plugins/saga/scripts/outcome_dispatcher.py`
- `plugins/saga/scripts/discover_sessions.py`
- `plugins/saga/scripts/extract_session_skeleton.py`
- `plugins/saga/skills/loop/`
- `plugins/saga/skills/resume/`
- `plugins/saga/skills/work/`
- `plugins/saga/skills/qa/`
- `.gitignore`
- `tests/test_dispatch_settlement.py`
- `tests/test_saga_session_forensics.py`
- `tests/test_saga_operator_snapshot.py`

### Tests to add or update

- Admission regression proving a rejected dispatch leaves neither an open attempt nor a persistent halt.
- Settlement coverage proving admitted success, failure, interruption, and retry have one coherent disposition.
- Current and legacy transcript fixtures covering date-based session directories, `response_item` messages, unknown event types, and current-session exclusion.
- Derived progress and closeout fixtures covering active work, blocked work, merged branches, local-main drift, scoped validation failures, and untracked transcript-like artifacts.
- Two-pass stopping-rule coverage for product-defect, test-oracle, and scope-expansion classifications.

### Context library links

- `docs/brainstorms/2026-07-26-codex-plugin-lifecycle-simplification-requirements.md`
- `plugins/saga/skills/resume/references/session-forensics.md`
- `docs/saga/README.md`
- https://github.com/infiquetra/infiquetra-context-library/blob/main/docs/ai-context/context-audit-standard.md

### Inputs inventory

- Issue #55 documents a transient admission failure that persists a halt while leaving the attempt open.
- Issue #56 documents `.claude/` runtime state in a committable path.
- The current validator fails because `.claude/.../transcript.jsonl` enters the legacy token inventory.
- Current Codex sessions use date-based directories and `response_item` user and assistant records that the existing tools do not reliably recover.
- Durable artifacts, Git, GitHub, and Operations fields already contain the facts needed for progress and closeout.

### Failure modes / pre-mortem

- Moving the mutation later but still writing partial state before all admission checks pass.
- Treating transcript extraction as the normal resume path.
- Persisting a new status projection that can drift from Git or GitHub.
- Silently deleting sensitive or useful recovery artifacts during closeout.
- Turning a two-pass stopping rule into another retry state machine.

### Stop conditions

- Stop if rejected admission can still leave a durable attempt or halt.
- Stop if transcript support requires retaining raw user transcripts as fixtures or reading hidden reasoning/tool payloads.
- Stop if progress or closeout requires a new canonical state store.
- Stop before automatic cleanup, branch deletion, issue closure, or settlement repair.

### Acceptance criteria

- [ ] `python3 -m pytest tests/test_dispatch_settlement.py plugins/saga/tests/test_outcome_dispatcher.py -q` passes rejection-before-mutation and coherent attempt-settlement cases.
- [ ] `python3 -m pytest tests/test_saga_session_forensics.py -q` passes date-based discovery, non-empty `response_item` extraction, sanitized old/current fixtures, unknown-event reporting, and current-session exclusion.
- [ ] `python3 -m pytest tests/test_saga_operator_snapshot.py -q` passes derived progress, validation-scope, board-sync, branch, drift, and closeout-dirt scenarios without persisted projection state.
- [ ] `git check-ignore .claude/` exits 0 and `git ls-files '.claude/**'` prints no tracked runtime or transcript artifact.
- [ ] `python3 scripts/validate_codex_plugins.py` exits 0 without treating ignored `.claude/` session material as an active legacy token path.
- [ ] `python3 -m pytest -q` exits 0 after the focused proofs pass.

### Verification

```bash
python3 -m pytest \
  tests/test_dispatch_settlement.py \
  plugins/saga/tests/test_outcome_dispatcher.py \
  tests/test_saga_session_forensics.py \
  tests/test_saga_operator_snapshot.py \
  -q
git check-ignore .claude/
git ls-files '.claude/**'
python3 scripts/validate_codex_plugins.py
python3 -m pytest -q
```

### Handoff maturity

requirements-ready

### Suggested next action

Use `saga:plan <issue>` to define the admission boundary, derived snapshot contract, and child dependency order.

### Source context

- Source: `docs/brainstorms/2026-07-26-codex-plugin-lifecycle-simplification-requirements.md`
- Existing children: #55, #56

## Created Issue

- URL: https://github.com/infiquetra/infiquetra-codex-plugins/issues/62
- Number: 62
- Created at: 2026-07-27T00:31:11.271197+00:00
