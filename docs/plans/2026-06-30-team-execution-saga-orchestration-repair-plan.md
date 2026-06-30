---
title: Team Execution Saga Orchestration Repair Implementation Plan
type: fix
status: active
date: 2026-06-30
origin: docs/brainstorms/2026-06-30-team-execution-saga-orchestration-repair-requirements.md
---

# Team Execution Saga Orchestration Repair Implementation Plan

## Summary

Implement the receipt-backed bridge between Saga and Team Execution so `team-execution` is an executable protocol only when a Team Execution receipt exists and resolves. The repair keeps Team Execution active, but makes Saga planning, work, resume, outcome dispatch, and evidence truthful about whether Team Execution actually ran.

This plan fixes the specific failure where Saga metadata says `team-execution` while the plan lacks `## Team Structure`, `orchestration_ref` is empty, and execution proceeds inline or through generic subagents.

## Problem Frame

The requirements document shows a lifecycle mismatch, not a reason to remove Team Execution. Team Execution already has Phase A planning and Phase B orchestration, while Saga already has `orchestration_mode`, `orchestration_ref`, recommendation, operator choice, and downgrade fields. The gap is the readiness contract between those surfaces.

The implementation must therefore add one shared readiness validator, wire it into the Saga lifecycle boundaries, update the Team Execution evidence vocabulary, and add regressions for the observed failure shapes.

## Requirements

R1. A Saga state with `orchestration_mode=team-execution` is executable only when `orchestration_ref` resolves to a Team Execution receipt.

R2. Valid receipts are a repo-relative markdown document with a `## Team Structure` heading, a markdown heading anchor that resolves to that section, or a protected Team Execution evidence/state root.

R3. Early draft planning may carry an incomplete Team Execution recommendation, but plan-ready, work, resume, outcome dispatch, and QA closeout contexts must block or repair missing receipts.

R4. `saga:plan` must materialize Phase A when Team Execution is selected, including runtime expectation, roles, reviewers, validators, gates, evidence/state location, and main-thread final verification.

R5. `saga:work` and `saga:resume` must route valid Team Execution state into Team Execution Phase B rather than choosing an independent inline or generic-subagent execution strategy.

R6. Lack of useful parallel split, missing delegated subagents, unsafe delegation, or backpressure selects serial Team Execution with the same roles and gates. It does not automatically downgrade to inline.

R7. Generic subagents and inline helpers may be recorded as assistance, but cannot satisfy Team Execution reviewer consensus or validator gates unless they are selected Team Structure roles.

R8. Saga state must keep recommendation, explicit operator choice, actual mode, downgrade/fallback rationale, and Team Execution role vehicle provenance distinct.

R9. `orchestration_operator_choice` must not be inferred from `orchestration_mode` when the operator did not explicitly choose a backend.

R10. Outcome dispatch for a Team Execution leaf must carry an `orchestration_ref` in the dispatch request, dispatch receipt, and durable ledger, or halt visibly before minting metadata-only work.

R11. Resume repair must detect empty refs, missing Team Structure, generic-subagent evidence presented as Team Execution, inline-vs-Team-Execution contradictions, and stale instruction roots before continuing.

R12. Source-only backend protections remain intact. Workflow, fork, goal, and hooks stay inactive unless a separate Codex capability proof and negative fallback tests land.

R13. The implementation must add regression coverage for metadata-only Team Execution, empty refs, invalid refs, generic-subagent non-credit, serial fallback, contradictory state, stale resume, and outcome receipt behavior.

## Key Technical Decisions

KTD1. Add `plugins/saga/scripts/team_execution_readiness.py` as the shared readiness boundary: a single pure helper avoids duplicated string checks across plan, save, work, resume, and outcome dispatch.

KTD2. Use `docs/plans/<plan>.md#team-structure` as the default plan-time `orchestration_ref`: the plan itself is the durable Phase A receipt, while separate artifact paths and protected evidence roots remain valid explicit refs.

KTD3. Enforce readiness at lifecycle write and dispatch boundaries, not during early drafting: this preserves useful recommendations while blocking false executable state at plan-ready, work, resume, outcome dispatch, and QA closeout.

KTD4. Stop defaulting operator choice from actual mode: `orchestration_operator_choice` is explicit provenance, while `orchestration_mode` is the effective mode.

KTD5. Store Team Execution role vehicle provenance in Team Execution evidence: Saga owns lifecycle-level orchestration fields, and Team Execution owns per-role evidence such as `team-execution-delegated` or `team-execution-serial`.

KTD6. Treat serial Team Execution as the fallback for unavailable delegation: `inline` is allowed only when the operator chose it or when a downgrade is explicit and recorded.

KTD7. Fix active-backend wording to `inline`, `manual`, and `team-execution`: source-only backends remain excluded, while the existing manual backend remains a valid handoff choice.

KTD8. Outcome dispatch must not synthesize fake Team Structures: Team Execution leaves must pass through a real ref from the node evidence/spec or halt with a receipt that explains the missing ref.

## High-Level Technical Design

The repair is a receipt gate between lifecycle intent and executable Team Execution.

```text
Saga recommendation or operator choice
          |
          v
Phase A receipt materialized by plan
  docs/plans/...md#team-structure
          |
          v
Saga save/readiness boundary
  recommendation != operator choice != actual mode
          |
          v
Work, resume, or outcome dispatch
          |
          +-- valid ref -> Team Execution Phase B
          |
          +-- missing or invalid ref -> repair or halt
```

The shared helper returns structured status, not only a boolean, so each caller can produce an actionable error or repair path without inventing its own wording.

```text
ReadinessResult
  status: not-team-execution | draft | ready | blocked
  reason: short machine-readable reason
  repair_hint: operator-facing next action
  resolved_ref: normalized path or heading target when available
```

## Team Structure

Team Execution is selected for this implementation because the work spans Saga state, Saga skills, outcome dispatch, Team Execution evidence, and cross-surface regression tests.

| field | value |
|-------|-------|
| orchestration_ref | `docs/plans/2026-06-30-team-execution-saga-orchestration-repair-plan.md#team-structure` |
| runtime expectation | delegated Team Execution when Codex subagents are callable and safe; serial Team Execution otherwise |
| state root | `.codex/team-execution/` protected by `.gitignore`, with user-local fallback only when repo-local state is not protected |
| final verifier | main thread verifies role outputs, tests, diffs, and gate evidence before PR-ready |
| max remediation loops | 3 |

| role | units | vehicle | reason |
|------|-------|---------|--------|
| saga-state-worker | U1, U2 | team-execution-delegated or team-execution-serial | readiness and Saga state changes are the central behavioral boundary |
| saga-lifecycle-worker | U3, U4 | team-execution-delegated or team-execution-serial | plan/work/resume instructions must agree with the new invariant |
| evidence-worker | U5 | team-execution-delegated or team-execution-serial | role provenance must be proven in Team Execution evidence |
| outcome-worker | U6 | team-execution-delegated or team-execution-serial | outcome leaf dispatch must obey the same receipt invariant |
| regression-worker | U7, U8 | team-execution-delegated or team-execution-serial | cross-surface regressions and docs checks close the original failure shapes |

| reviewer | required | focus |
|----------|----------|-------|
| devils-advocate-reviewer | yes | false-positive readiness, downgrade loopholes, overbroad state coupling |
| security-reviewer | yes | path trust boundaries, local state roots, stale or untrusted evidence |
| architecture-reviewer | yes | Saga vs Team Execution ownership and lifecycle sequencing |

| validator | required | blocks completion when |
|-----------|----------|------------------------|
| security-scanner | yes | path/evidence handling introduces unsafe absolute-path or untrusted-root behavior |
| smoke-tester | yes | Saga CLI entrypoints or plugin validation fail their smoke checks |
| scenario-tester | yes | lifecycle scenarios for plan, work, resume, and outcome dispatch do not match the receipt invariant |

Gate rule: reviewer consensus must have no blocking finding and no consensus dimension below 7/10. Required validators block completion unless the operator explicitly records a residual-risk acceptance. Repo checks such as `python3 scripts/validate_codex_plugins.py`, targeted pytest, full pytest, and docs drift assertions are automation gates attached to the validators; they are not invented validator role names.

## Implementation Units

### U1. Add Shared Team Execution Readiness Validation

Create the central readiness helper that every lifecycle boundary can call.

**Goal:** Provide one deterministic validator for Team Execution executable state so callers no longer infer readiness from metadata alone.

**Requirements:** R1, R2, R3, R11, R13.

**Dependencies:** None.

**Files:** Create `plugins/saga/scripts/team_execution_readiness.py`. Create `tests/test_team_execution_readiness.py`.

**Approach:** Implement a pure helper with a narrow API: `validate_team_execution_ready(repo_root: Path, *, orchestration_mode: str, orchestration_ref: str, context: str, plan_path: str = "") -> ReadinessResult`. Context values are `draft-plan`, `plan-ready`, `work`, `resume`, `outcome-dispatch`, and `qa-closeout`. Non-Team-Execution modes return `not-team-execution`; draft plans may return `draft`; executable contexts require a resolvable ref.

Add a small CLI wrapper in the same module so skill docs can call the same validator at non-Python boundaries: `python3 plugins/saga/scripts/team_execution_readiness.py validate --mode team-execution --ref <ref> --context <context> [--plan-path <path>]`.

Refs resolve as repo-relative markdown paths, repo-relative markdown paths with a case-insensitive `#team-structure` heading anchor, repo-relative protected evidence roots under `.codex/team-execution/`, or explicit user-local fallback roots under `~/.codex/team-execution/state/<repo>/`. Reject unrelated absolute paths and unprotected repo-local state roots.

**Patterns to follow:** Use the repo-local state protection already modeled by `plugins/team-execution/scripts/protocol_probe.py:78`. Keep import behavior standalone like other Saga scripts.

**Test scenarios:** In `tests/test_team_execution_readiness.py`, create a markdown plan with `## Team Structure`, call the helper for `work`, and expect `status=ready` with a normalized resolved ref.

In the same file, pass an empty `orchestration_ref` in `draft-plan` context and expect `status=draft`, then pass the same empty ref in `work` and expect `status=blocked` with a repair hint.

In the same file, pass a missing file, a markdown file without `## Team Structure`, an unprotected `.codex/team-execution/` root, and an unrelated absolute path; each must block with a specific reason.

In the same file, pass `orchestration_mode=inline` and `orchestration_mode=manual`; both must return `not-team-execution` and must not inspect the filesystem.

**Verification:** The helper has no side effects, all valid and invalid ref shapes are covered, and no Saga caller or skill instruction needs to duplicate readiness parsing.

### U2. Correct Saga Save-Time Provenance And Readiness

Make Saga state truthful at the point it is written.

**Goal:** Prevent new saga ticks from recording executable Team Execution without a receipt, and stop fabricating operator choice from actual mode.

**Requirements:** R1, R3, R8, R9, R11, R13.

**Dependencies:** U1.

**Files:** Modify `plugins/saga/scripts/saga.py`. Modify `plugins/saga/tests/test_saga_state.py`. Modify `tests/test_capability_degrade.py`. Modify `tests/test_override_rate.py` if needed for operator-choice semantics.

**Approach:** Remove the `_build_save_saga` fallback at `plugins/saga/scripts/saga.py:1081`, where `args.orchestration_operator_choice or args.orchestration_mode` currently collapses operator choice and actual mode. Preserve an empty operator-choice field unless the CLI flag is explicitly present.

Call the U1 readiness helper inside the save path before writing an envelope for contexts Saga can derive from its own fields. Derive `plan-ready` when `lifecycle_phase=plan` and `phase_status=complete`, `draft-plan` for other plan ticks, `work` for work ticks, and `qa-closeout` for QA-complete ticks. Do not infer `resume` inside `saga.py`; `saga:resume` validates with the U1 CLI before writing its re-entry tick, then saves the repaired or explicitly downgraded state.

Reject a mismatch between explicit operator choice and actual mode unless `orchestration_downgrade` is non-empty.

**Patterns to follow:** Preserve the active mode enum checked by `plugins/saga/tests/test_saga_state.py`. Preserve source-only rejection and downgrade receipt tests in `tests/test_capability_degrade.py`.

**Test scenarios:** In `plugins/saga/tests/test_saga_state.py`, save `team-execution` with explicit `--orchestration-ref docs/plans/x.md#team-structure` against a fixture plan and expect success.

In `plugins/saga/tests/test_saga_state.py`, save `team-execution` with an empty ref for `lifecycle_phase=work` and expect the CLI to return non-zero without writing a saga.

In `plugins/saga/tests/test_saga_state.py`, save `team-execution` with an empty ref for `lifecycle_phase=plan` and `phase_status=pending` and expect success as a draft; repeat with `phase_status=complete` and expect rejection.

In `tests/test_capability_degrade.py`, save a Team Execution mode with no `--orchestration-operator-choice` and expect the restored operator-choice field to remain empty.

In `tests/test_capability_degrade.py`, save `orchestration_operator_choice=team-execution`, `orchestration_mode=inline`, and no downgrade note; expect rejection. Repeat with a downgrade note and expect success.

In `tests/test_override_rate.py`, confirm override-rate calculations still ignore sagas where either recommendation or operator choice is empty.

**Verification:** Saga write behavior rejects false executable state, preserves explicit provenance, and keeps source-only backend protections unchanged.

### U3. Materialize Phase A In Saga Planning

Update Saga planning so accepting Team Execution produces a receipt before the plan is called ready.

**Goal:** Make the plan artifact itself carry the Team Execution Phase A contract by default.

**Requirements:** R1, R2, R4, R8, R12, R13.

**Dependencies:** U1, U2.

**Files:** Modify `plugins/saga/skills/plan/SKILL.md`. Modify `plugins/saga/skills/plan/references/plan-sections.md`. Modify `plugins/saga/references/operator-choice.md`. Modify or create `tests/test_team_execution_lifecycle_text.py`.

**Approach:** Add a plan-phase rule: when Team Execution is selected, the plan must include `## Team Structure` or link a separate Team Execution artifact, and the saga save command must include `--orchestration-ref <plan-path>#team-structure`, `--orchestration-recommended`, and explicit `--orchestration-operator-choice` when the operator picked it.

Keep active Codex choices aligned with `inline`, `manual`, and `team-execution`. Do not advertise Workflow, fork, goal, or hooks as active choices.

**Patterns to follow:** Follow the plan frontmatter and section contract in `plugins/saga/skills/plan/references/plan-sections.md`. Reuse `plugins/saga/scripts/team_emitter.py` concepts rather than creating a second Team Structure format.

**Test scenarios:** In `tests/test_team_execution_lifecycle_text.py`, assert the plan skill requires `## Team Structure` or a linked artifact when Team Execution is selected.

In the same file, assert the plan skill save example includes `--orchestration-ref`, `--orchestration-recommended`, and `--orchestration-operator-choice`.

In `tests/test_operator_choice_drift.py`, update active backend wording expectations so `manual` is acknowledged while source-only Workflow remains excluded.

**Verification:** A new Team Execution plan has a concrete receipt and a runnable Saga save command with all relevant provenance fields.

### U4. Route Work And Resume Through Phase B

Make the execution and resume skills consume Team Execution receipts instead of independently choosing inline execution.

**Goal:** When restored state is executable Team Execution, `saga:work` and `saga:resume` enter Team Execution Phase B or repair/halt; they do not silently run inline.

**Requirements:** R3, R5, R6, R7, R11, R12, R13.

**Dependencies:** U1, U2, U3.

**Files:** Modify `plugins/saga/skills/work/SKILL.md`. Modify `plugins/saga/skills/resume/SKILL.md`. Modify `plugins/saga/skills/work/references/execution-strategy.md`. Modify or create `tests/test_team_execution_lifecycle_text.py`.

**Approach:** In work Phase 1.4, validate Team Execution readiness after restore and before saving the work tick or mutating code. If ready, read the Team Structure and follow the Team Execution skill for Phase B. If blocked, repair Phase A or halt before code mutation.

In resume Phase 3a, add Team Execution contradiction checks: empty ref, missing Team Structure, generic-subagent evidence presented as Team Execution, inline prose with Team Execution metadata, and stale instruction roots. Route repaired executable state to work/Team Execution; route unrepaired state to explicit downgrade or operator halt.

Treat stale instruction-root detection conservatively. Flag stale roots only when the restored tick chain or durable artifacts name an installed cache root such as `.codex/plugins/cache/...`, name a Saga or Team Execution version older than the repo source being read, or otherwise point to non-repo instructions. If no durable stale signal exists, resume still rereads the current repo skill files before routing but does not invent a stale-context finding.

Replace the current fallback wording in `plugins/saga/skills/work/references/execution-strategy.md:140`, which says unavailable Team Execution falls back to inline, with serial Team Execution or explicit recorded downgrade.

**Patterns to follow:** Preserve U-ID task list handling and generic `Explore`/`Task` usage for non-Team-Execution mechanical execution. Keep source-only backend exclusions from `tests/test_operator_choice_drift.py`.

**Test scenarios:** In `tests/test_team_execution_lifecycle_text.py`, assert work says a valid Team Execution ref routes to Phase B before normal inline/subagent strategy.

In the same file, assert work and resume both mention serial Team Execution for unavailable or backpressured delegation.

In the same file, assert resume names the five repair detections from R11 and does not route back to `/loop`.

In the same file, assert resume validates Team Execution before writing its re-entry tick and says it rereads current repo skill files when stale instruction roots are suspected.

In `tests/test_operator_choice_drift.py`, assert no active surface says Team Execution unavailability silently falls back to inline.

**Verification:** Work and resume instructions cannot preserve Team Execution metadata while executing through an unrelated inline path.

### U5. Add Role Vehicle Provenance To Team Execution Evidence

Make Team Execution evidence distinguish selected-role execution from generic help.

**Goal:** Record what actually ran per reviewer and validator role with a vocabulary that gates can trust.

**Requirements:** R6, R7, R8, R13.

**Dependencies:** U1.

**Files:** Modify `plugins/team-execution/scripts/protocol_probe.py`. Modify `plugins/team-execution/tests/test_protocol_probe.py`. Modify `plugins/team-execution/skills/team-execution/SKILL.md`. Modify `plugins/team-execution/skills/team-execution/references/validator-evidence-state.md` if the evidence schema is documented there.

**Approach:** Add a `vehicle` field to reviewer and validator artifact records. Use `team-execution-delegated` when subagents are present and available, `team-execution-serial` when subagents are absent or backpressured, and document `generic-subagent` plus `inline-assist` as non-gate assistance categories.

Keep the existing `execution_mode` field for backward compatibility while adding `vehicle`; do not remove current payload keys.

**Patterns to follow:** `plugins/team-execution/scripts/protocol_probe.py:95` and `plugins/team-execution/scripts/protocol_probe.py:126` are the current artifact creation points. Existing tests already cover serial fallback and validator blocking in `plugins/team-execution/tests/test_protocol_probe.py`.

**Test scenarios:** In `plugins/team-execution/tests/test_protocol_probe.py`, absent subagents should produce `execution_mode=serial` and `vehicle=team-execution-serial` for reviewers and validators.

In the same file, present subagents with available spawn should produce `vehicle=team-execution-delegated`.

In the same file, backpressure should preserve `subagent_capability=present` while setting `vehicle=team-execution-serial`.

In the same file or a docs drift test, assert generic helpers are documented as assistance that cannot satisfy reviewer or validator gates.

**Verification:** Team Execution artifacts distinguish selected-role evidence from generic assistance without breaking existing `execution_mode` consumers.

### U6. Carry Team Execution Refs Through Outcome Dispatch

Make outcome leaf dispatch obey the same receipt invariant as plan/work/resume.

**Goal:** Prevent Team Execution outcome leaves from minting metadata-only leaf sagas.

**Requirements:** R1, R2, R10, R12, R13.

**Dependencies:** U1.

**Files:** Modify `plugins/saga/scripts/outcome.py`. Modify `plugins/saga/scripts/outcome_dispatcher.py`. Modify `tests/test_outcome_dispatcher.py`. Modify `tests/test_outcome_backends.py` if existing backend tests need fixture updates.

**Approach:** Extend `DispatchRequest` in `plugins/saga/scripts/outcome.py:73` with `orchestration_ref: str = ""`. Populate it before calling dispatch at `plugins/saga/scripts/outcome.py:657` from `node.evidence["orchestration_ref"]` first, then `node.evidence["team_execution_ref"]` for backward-compatible aliases. Do not add a top-level node field; `plugins/saga/scripts/outcome_spec.py:118` already defines `evidence` as the open pass-through map for backend-specific details.

In `outcome_dispatcher.dispatch`, require a non-empty ref for backend `team-execution`. Include the ref in successful dispatch results. Return or raise a visible halt receipt when the ref is missing. In `_reconcile_once`, append `orchestration_ref` to the durable `commit` ledger record when the request contains one.

Do not synthesize a Team Structure inside the dispatcher. Existing `team_execution_artifact()` remains a helper for callers that already have an execution spec and can write/link the artifact before dispatch.

**Patterns to follow:** Preserve HALT-not-degrade behavior from `plugins/saga/scripts/outcome_dispatcher.py:112` and the existing per-leaf halt handling in outcome reconcile.

**Test scenarios:** In `tests/test_outcome_dispatcher.py`, dispatch a Team Execution request with `orchestration_ref="docs/plans/x.md#team-structure"` and expect `status=dispatched` plus the same ref in the result.

In the same file, dispatch a Team Execution request with an empty ref and expect `status=halt` or `BackendHaltError` with reason `missing orchestration_ref`.

In the same file, advance a Team Execution outcome node whose `evidence.orchestration_ref` contains a ref and expect the ledger dispatch commit to include that ref.

In the same file, advance a Team Execution outcome node whose `evidence.team_execution_ref` contains a ref and expect the alias to populate the dispatch request and ledger record.

In the same file, advance a Team Execution outcome node with no ref and expect it to halt, not dispatch, while unrelated runnable leaves still proceed.

**Verification:** Outcome dispatch never records successful Team Execution without a receipt pointer.

### U7. Add Cross-Surface Regression Fixtures

Capture the investigation's observed failure shapes as runnable tests.

**Goal:** Prove the exact pain point cannot regress across Saga state, skills, outcome dispatch, and Team Execution evidence.

**Requirements:** R1 through R13.

**Dependencies:** U1, U2, U3, U4, U5, U6.

**Files:** Create `tests/test_team_execution_orchestration_regressions.py`. Reuse fixtures from `plugins/saga/tests/test_saga_state.py`, `tests/test_outcome_dispatcher.py`, and `plugins/team-execution/tests/test_protocol_probe.py` where practical.

**Approach:** Use small local fixtures instead of replaying real session JSONL. Model the known shapes directly: metadata-only plan, empty ref at work, invalid ref at resume, generic-subagent evidence, serial fallback, operator choice divergence, stale instruction warning, and outcome leaf dispatch.

**Patterns to follow:** Tests in this repo load plugin scripts by file path to avoid package assumptions. Match that style and run with `PYTHONPATH=. python3 -m pytest -q`.

**Test scenarios:** Metadata-only plan input: write a plan with `recommended_backend: team-execution` prose but no `## Team Structure`; action: validate as `plan-ready`; expected: blocked.

Empty ref work input: save or validate `orchestration_mode=team-execution` with no ref; action: enter `work`; expected: blocked before mutation.

Serial fallback input: run the protocol probe with absent subagents and selected validators; action: inspect evidence; expected: serial Team Execution vehicle records, same selected roles, and no inline downgrade.

Generic-subagent input: evidence contains `vehicle=generic-subagent`; action: evaluate Team Execution gate fixture; expected: reviewer and validator gates remain unsatisfied.

Contradictory state input: `orchestration_mode=team-execution` plus actual vehicle `inline-assist`; action: resume repair fixture; expected: explicit downgrade required or Team Execution repair path selected.

Stale instruction input: restored tick chain references an installed cache instruction root or older Saga/Team Execution version; action: resume repair fixture; expected: current repo skill files are reread and stale-context repair evidence is recorded.

Outcome input: Team Execution leaf without ref; action: advance outcome; expected: visible halt and no dispatched subplot.

**Verification:** Every acceptance example from the requirements has at least one direct test.

### U8. Documentation, Journal, And Validation Closeout

Keep the active docs and validation surfaces aligned with the new invariant.

**Goal:** Ensure the implementation is not only code-correct but also durable for future Saga runs.

**Requirements:** R4, R8, R12, R13.

**Dependencies:** U1 through U7.

**Files:** Modify `docs/engineering-journal/DECISIONS.md`. Modify `docs/saga/` files only if active operator guidance drifts. Modify `plugins/saga/CHANGELOG.md` and `plugins/team-execution/CHANGELOG.md` only if the repo's release convention requires it for this patch. Update manifest/version metadata only if validation requires visible behavior versioning.

**Approach:** Record the receipt-backed Team Execution lifecycle decision in `docs/engineering-journal/DECISIONS.md`. Keep docs changes scoped to active surfaces and avoid installed cache edits. Run plugin validation plus the focused test set before broader pytest.

**Patterns to follow:** The repo already treats `docs/engineering-journal/DECISIONS.md` as the canonical KTD journal. The root `AGENTS.md` forbids treating installed Codex cache copies as maintained source.

**Test scenarios:** `python3 scripts/validate_codex_plugins.py` must pass.

`PYTHONPATH=. python3 -m pytest -q tests/test_team_execution_readiness.py tests/test_team_execution_lifecycle_text.py tests/test_team_execution_orchestration_regressions.py plugins/saga/tests/test_saga_state.py plugins/team-execution/tests/test_protocol_probe.py tests/test_outcome_dispatcher.py tests/test_operator_choice_drift.py tests/test_capability_degrade.py tests/test_override_rate.py` must pass before PR-ready.

`PYTHONPATH=. python3 -m pytest -q` should run after focused tests pass unless the operator explicitly scopes the PR smaller.

**Verification:** The KTDs are journaled, docs do not advertise metadata-only Team Execution, and validation passes from a clean checkout state.

## Scope Boundaries

Do not remove Team Execution from the active Codex plugin set.

Do not port Claude-only commands, agents, hooks, Workflow, fork, goal, or host-specific mechanisms as active Codex surfaces.

Do not make generic multi-agent or generic subagent usage equivalent to Team Execution gates.

Do not introduce a new orchestration state machine or evidence index unless U1 proves the receipt contract cannot represent a required executable state.

Do not edit installed Codex cache copies. This repo is the maintained source.

Do not implement a broader OutcomeOrchestrator redesign. This slice only enforces the Team Execution receipt invariant on Team Execution leaves.

## Risks & Dependencies

Risk: readiness validation may become too strict and block legitimate draft planning. Mitigation: U1 separates `draft-plan` from executable contexts and tests both.

Risk: adding `orchestration_ref` to outcome dispatch can break injected dispatcher tests. Mitigation: default the dataclass field to `""` and update tests around the production Team Execution path first.

Risk: role vehicle vocabulary could duplicate existing `execution_mode`. Mitigation: keep `execution_mode` for compatibility and add `vehicle` as the gate-facing provenance field.

Risk: docs-only skill changes could drift from script behavior. Mitigation: U7 adds cross-surface tests and U8 runs plugin validation.

Dependency: `.codex/team-execution/` must remain git-ignored for repo-local evidence roots. This repo already ignores it in `.gitignore`.

## Success Metrics

SM1. Saving or dispatching executable Team Execution with an empty or invalid ref fails before claiming work ran.

SM2. A Team Execution plan created by Saga includes or links a `## Team Structure` receipt and records a non-empty `orchestration_ref`.

SM3. Work and resume instructions route valid Team Execution state to Phase B and describe serial Team Execution rather than inline fallback for unavailable delegation.

SM4. Outcome dispatch receipts and ledger records include `orchestration_ref` for Team Execution leaves.

SM5. Focused regression tests cover all eight acceptance examples from the requirements.

## Sources / Research

`docs/brainstorms/2026-06-30-team-execution-saga-orchestration-repair-requirements.md`: source requirements, flows, acceptance examples, and deferred planning questions.

`plugins/saga/scripts/saga.py:1079`: current Saga save builder records orchestration fields and defaults operator choice from mode.

`plugins/saga/scripts/outcome.py:73`: `DispatchRequest` currently lacks `orchestration_ref`.

`plugins/saga/scripts/outcome.py:657`: outcome reconcile builds dispatch requests without passing a Team Execution ref.

`plugins/saga/scripts/outcome_dispatcher.py:100`: dispatcher is the single backend seam and can enforce Team Execution dispatch readiness.

`plugins/team-execution/scripts/protocol_probe.py:95`: reviewer artifacts currently record role, artifact, and execution mode but not vehicle provenance.

`plugins/team-execution/scripts/protocol_probe.py:126`: validator artifacts currently record execution mode but not vehicle provenance.

`plugins/saga/skills/work/references/execution-strategy.md:140`: current wording falls back from unavailable Team Execution to inline, which this plan replaces with serial Team Execution or explicit downgrade.
