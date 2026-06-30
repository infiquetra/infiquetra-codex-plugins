---
title: Team Execution And Saga Orchestration Debug Report
date: 2026-06-30
status: DONE_WITH_CONCERNS
scope: codex team-execution and saga plugins
---

# Team Execution And Saga Orchestration Debug Report

## Symptom

Recent Codex sessions record or recommend `team-execution`, but the work often runs as ordinary inline work, generic subagents, or "inline + ultracode assist" instead of the `team-execution` protocol.

The visible failure pattern is:

- Saga state or plan frontmatter says `team-execution`.
- The plan often has no `## Team Structure`.
- `orchestration_ref` is often empty.
- Generic spawned Codex subagents may run, but they are not the selected `team-execution` reviewers, validators, evidence gates, or serial fallback roles.
- Some session notes preserve contradictory state: `orchestration_mode: team-execution` while prose says the real vehicle was inline.

This report is diagnosis only. It is intended as a repair reference for the Codex `saga` and `team-execution` plugins.

## Expected Contract

Current `team-execution` contract:

- `team-execution` is a structured reviewer/validator protocol, not just a label for "use agents".
- It has two valid runtime modes:
  - `delegated`: selected Codex subagents are available and safe.
  - `serial`: subagents are absent, unsafe, or backpressured; the main thread runs the same reviewer/validator roles sequentially and records the serial limitation.
- Phase A must add a `## Team Structure` section to the plan.
- Phase B must parse the approved `## Team Structure`, execute workers, run reviewers, run selected validators, record evidence, and report gate results.

Relevant source:

- `plugins/team-execution/skills/team-execution/SKILL.md`
  - Lines 18-26: delegated and serial runtime modes.
  - Lines 57-75: Phase A must add `## Team Structure`.
  - Lines 106-127: Phase B runs reviewers, validators, automation gates, and reports evidence.
- `plugins/team-execution/scripts/protocol_probe.py`
  - `--subagents absent` proves serial fallback is valid and should not be treated as "skip team-execution".

Current Saga contract:

- `plugins/saga/references/operator-choice.md` names active Codex backends: `inline`, `manual`, `team-execution`.
- `team-execution` is owned by `team-execution`, not the Saga caller.
- For `team-execution`, `orchestration_ref` may point at a `## Team Structure` section or team-execution evidence root.
- `plugins/saga/scripts/team_emitter.py` can emit a `## Team Structure` section from an execution spec.
- `plugins/saga/scripts/outcome_dispatcher.py` exposes `team_execution_artifact()` and treats `team-execution` as an always-available floor backend.

## Evidence

### Local protocol proof

Command:

```bash
python3 plugins/team-execution/scripts/protocol_probe.py --subagents absent --pretty
```

Result observed on 2026-06-30:

- `result: pass`
- `mode: serial`
- `delegation_status: subagents-unavailable`
- reviewer artifacts include:
  - `devils-advocate-reviewer`
  - `security-reviewer`
  - `architecture-reviewer`

Conclusion: lack of delegated subagents is not a valid reason to downgrade or skip team-execution. It should enter serial mode.

### Source tests already cover part of the intended bridge

Targeted command:

```bash
PYTHONPATH=. python3 -m pytest -q tests/test_outcome_dispatcher.py plugins/team-execution/tests/test_protocol_probe.py
```

Observed result:

```text
23 passed
```

Relevant tested behavior:

- `tests/test_outcome_dispatcher.py` asserts `team_execution_artifact()` produces `Team Structure`.
- `plugins/team-execution/tests/test_protocol_probe.py` asserts serial fallback records per-role artifacts and limits.

Conclusion: the low-level pieces exist. The failure is in lifecycle enforcement and user-facing workflow integration.

### Session evidence: CAMPPS context-library

Primary session:

- Thread: `019f13d7-12d4-7f43-8b8d-64b73778219c`
- Rollout: `~/.codex/sessions/2026/06/29/rollout-2026-06-29T10-44-50-019f13d7-12d4-7f43-8b8d-64b73778219c.jsonl`
- Cwd: `campps-context-library`

Observed:

- Session started with stale Saga root `saga/0.22.1`.
- Later commands invoked `saga/0.41.0` scripts directly, but active instructions had older guidance.
- Saga recorded `orchestration_mode: team-execution`.
- Leaf work later recorded `orchestration_recommended: inline` and `orchestration_operator_choice: team-execution`.
- Downgrade notes said leaves were executed inline while preserving the prior `team-execution` choice.
- The main plan `docs/plans/2026-06-29-campps-e2e-outcome-close-registry-plan.md` did not contain:
  - `## Team Structure`
  - base reviewer roster
  - consensus threshold
  - selected validators

Conclusion: this is metadata-only team-execution. The protocol was not materialized.

### Session evidence: team-norns

Primary session:

- Thread: `019f1184-7eeb-7620-a13b-79917b1f31ea`
- Rollout: `~/.codex/sessions/2026/06/28/rollout-2026-06-28T23-55-23-019f1184-7eeb-7620-a13b-79917b1f31ea.jsonl`
- Cwd: `team-norns`

Observed:

- Early session used `saga/0.22.1`; later resumed windows showed `saga/0.41.0`.
- Saga metadata included `orchestration_recommended: team-execution`.
- Later state recorded `orchestration_operator_choice: inline`.
- Summary text stated `team-execution` was recorded, but a callable backend was not available and policy prevented subagents, so continue inline.
- Plan `docs/plans/2026-06-29-norns-three-sisters-first-launch-plan.md` did not contain `## Team Structure`.

Conclusion: some of this was recorded as an inline operator choice, but the "backend unavailable" rationale is wrong under the current team-execution serial fallback contract.

### Session evidence: infiquetra-claude-plugins

Primary current parent:

- Thread: `019f15a6-8fe8-78a2-91ab-fbbdc717c365`
- Cwd: `infiquetra-claude-plugins`
- Provider: `openai`
- Current workers:
  - `019f16da-7f4b-77b3-9988-09e9623788e6`, U1 worker Harvey
  - `019f16de-cffa-7de0-8a43-d9b86715f0f5`, U2 worker Confucius

Observed:

- This session uses `saga/0.41.0`.
- It does use real spawned Codex subagent worker threads.
- Plan `docs/plans/2026-06-30-antigravity-teammate-plugin-plan.md` has `recommended_backend: team-execution`.
- The same plan does not contain `## Team Structure`.
- Saga prose in `.claude/saga/sagas/task-outcome-orchestration/*` says the real build vehicle is `inline + ultracode assist`, while `orchestration_mode` remains pinned to `team-execution`.

Conclusion: this is not the stale `0.22.1` failure. It shows a newer failure mode: real Codex subagents can exist, but they are generic workers, not the team-execution protocol. `recommended_backend` also does not force Phase A materialization.

### Session evidence: home-lab

Primary current parent:

- Thread: `019f0fb0-f02f-71c2-9b29-82b0453a3b00`
- Cwd: `home-lab`
- Provider: `openai`

Recent child agents:

- `019f159d-0523-7c91-a6ff-2ff809372262`
- `019f159d-0593-7cc2-9072-f2fa96a4ed77`
- `019f159d-0616-7752-9004-381d8fc6ec76`
- `019f159d-0696-7cc2-8ddd-59e95e495ba5`
- `019f159d-0733-7731-b154-22cbcb871fe3`
- `019f159d-0812-7433-bffc-62c19ea5de8d`

Observed:

- Recent home-lab child agents were raw ideation/lens workers, provider `headroom`.
- They were not team-execution reviewers or validators.
- Current plan `docs/plans/2026-06-29-detached-ceph-bulk-model-vault-plan.md` does not record team-execution.
- Older saga state for `headroom-service-vm` records `orchestration_mode: team-execution` with empty `orchestration_ref`.
- `docs/plans/2026-06-27-headroom-service-vm-plan.md` does not contain `## Team Structure`.

Conclusion: current model-vault work is not a team-execution case. Older Headroom work has the same metadata-only risk: `team-execution` state without a protocol artifact pointer.

## Root Cause

The root cause is a contract split across Saga and team-execution:

1. Saga can recommend or record `team-execution` without requiring a concrete team-execution artifact.
2. Plan artifacts can carry `recommended_backend: team-execution` without carrying `## Team Structure`.
3. `orchestration_ref` is optional in practice, even though team-execution needs a plan section or evidence root to run.
4. Generic Codex subagent spawning is being treated as adjacent to, or sometimes a substitute for, team-execution.
5. Some lifecycle text still reasons as if `team-execution` were a missing backend or a parallel-only mechanism, despite the current serial fallback contract.
6. Saga state merge/provenance behavior can preserve stale `orchestration_mode: team-execution` even when prose records inline execution, producing contradictory durable state.

The likely architectural mistake is treating `team-execution` as a backend label rather than a two-phase protocol with an explicit artifact and gate state.

## Causal Chain

1. A plan is large, risky, cross-repo, deployment-sensitive, or validator-heavy.
2. Saga correctly recommends `team-execution`.
3. The plan records that recommendation or Saga records `orchestration_mode: team-execution`.
4. No code path reliably forces Phase A to append `## Team Structure`, select reviewers/validators, and save a non-empty `orchestration_ref`.
5. Work or resume starts from the plan.
6. The agent sees no concrete team-execution artifact to parse.
7. Depending on session age and prompt wording, the agent either:
   - downgrades leaf work to inline because it sees no useful parallel split,
   - records inline execution while preserving `team-execution` metadata,
   - spawns generic subagents unrelated to the reviewer/validator roster,
   - or treats lack of a direct backend/tool as reason to continue inline.
8. The task may still complete, but team-execution's reviewer consensus, selected validator gates, serial fallback evidence, and automation boundaries never run.

## High-Confidence Defects

### D1. Saga lacks an invariant tying `team-execution` to an artifact

`orchestration_mode: team-execution` should not be considered executable without either:

- a plan section containing `## Team Structure`, or
- an evidence/state root in `orchestration_ref`.

Current state allows `team-execution` with empty `orchestration_ref`, which is how metadata-only runs happen.

Candidate fix:

- Add a validation layer in `saga.py save` or the lifecycle phase entrypoints:
  - Permit empty `orchestration_ref` only during early plan drafting.
  - Before `work`, `outcome advance`, or `resume` execution, require a non-empty `orchestration_ref` for `team-execution`.
  - If missing, stop with a repair instruction: emit or append `## Team Structure`, then save the ref.

### D2. `recommended_backend: team-execution` does not trigger Phase A

The `infiquetra-claude-plugins` plan shows `recommended_backend: team-execution`, but lacks `## Team Structure`.

Candidate fix:

- In `saga:plan`, when the backend recommendation is accepted as `team-execution`, Phase A must:
  - load team-execution references,
  - select reviewers/validators,
  - append `## Team Structure`,
  - save `orchestration_mode=team-execution`,
  - save `orchestration_ref=<plan_path>#team-structure` or a generated artifact path.

### D3. Work/resume treats team-execution as optional execution style

Earlier sessions used statements like "no useful parallel split" or "backend not directly available" to continue inline.

Candidate fix:

- In `saga:work` and `saga:resume`, if effective backend is `team-execution`:
  - parse `## Team Structure`;
  - run Phase B;
  - use serial mode when delegation is unavailable;
  - never downgrade solely because the leaf is small or has no useful parallel split.

Small leaf size may change reviewer/validator selection, but it does not automatically convert a selected team-execution backend into inline execution.

### D4. Generic subagents are conflated with team-execution

Recent `infiquetra-claude-plugins` and `home-lab` sessions use real subagents, but they are not team-execution unless they are selected roles from `## Team Structure` and their outputs feed the consensus/validator gates.

Candidate fix:

- Add explicit vocabulary:
  - `generic-subagent`: ordinary spawned worker/lens.
  - `team-execution-delegated`: selected team-execution role dispatched as a subagent.
  - `team-execution-serial`: selected team-execution role run by main thread.
  - `inline-assist`: ad hoc helper or ultracode workflow, not team-execution.
- Record this in evidence state, not just prose.

### D5. State provenance permits contradictions

Some saga history records `orchestration_mode: team-execution` while prose says "real vehicle inline + ultracode assist".

Candidate fix:

- Make `orchestration_mode` mean the actual effective owner for the current tick.
- Make `orchestration_operator_choice` mean only an actual operator choice, never AI-generated fallback.
- If the AI changes execution mode, record it only in `orchestration_downgrade` with AI provenance.
- If merge rules prevent de-escalating from `team-execution`, add an explicit field such as `execution_vehicle_actual` or fix merge semantics so the state can reflect reality.

## Proposed Repair Plan

### 1. Define the hard invariant

Add a central helper, for example:

```python
def validate_team_execution_ready(
    *,
    orchestration_mode: str,
    orchestration_ref: str,
    plan_path: str,
    lifecycle_phase: str,
) -> list[str]:
    ...
```

Rules:

- If `orchestration_mode != "team-execution"`, no-op.
- If phase is only draft/plan-before-routing, allow missing ref.
- If phase is work/resume/outcome-dispatch/qa-closeout, require:
  - `orchestration_ref` non-empty, and
  - ref resolves to a `## Team Structure` section or `.codex/team-execution/` state root.

### 2. Make Phase A explicit in `saga:plan`

When operator accepts `team-execution`, the plan should not stop at `recommended_backend: team-execution`.

It should write one of:

- inline plan section:

```markdown
## Team Structure
...
```

- or separate generated artifact:

```text
docs/team-execution/<slug>-team-structure.md
```

Then Saga should save:

```text
orchestration_mode=team-execution
orchestration_ref=<path or anchor>
orchestration_recommended=team-execution
orchestration_operator_choice=team-execution
```

### 3. Make Phase B explicit in `saga:work` and `saga:resume`

When restored saga state says `team-execution`, do not "just work the plan".

Required sequence:

1. Load `team-execution` skill.
2. Load relevant team-execution references.
3. Parse `## Team Structure`.
4. Decide runtime mode:
   - delegated if selected agents are callable and safe;
   - serial otherwise.
5. Execute the work.
6. Run reviewer consensus.
7. Run selected validators.
8. Save evidence and gate result.
9. Only then report PR/merge/deploy readiness.

### 4. Integrate `protocol_probe.py` into lifecycle checks

Use the probe as a cheap deterministic guard:

- If selected mode is `team-execution` and no subagents are available, probe should still produce `mode: serial`.
- A failed probe should block team-execution readiness and tell the operator why.
- A passed serial probe should prevent the "backend unavailable, continue inline" path.

### 5. Repair outcome dispatch semantics

`outcome_dispatcher.dispatch()` mints a leaf saga id for `team-execution`, and `team_execution_artifact()` can emit `## Team Structure`, but the user-facing outcome advance still needs to persist and surface the artifact.

Candidate requirements:

- On dispatch of a team-execution leaf:
  - emit a team-execution artifact or require pre-existing `orchestration_ref`;
  - include artifact path in the leaf saga;
  - include return channel plus `orchestration_ref` in the dispatch receipt.
- If the artifact cannot be emitted, HALT. Do not silently dispatch metadata-only.

### 6. Add stale-session protection

The CAMPPS and Norns sessions started with `saga/0.22.1` but later used `0.41.0` scripts.

Candidate fix:

- On resume, compare loaded skill root/version against installed plugin version.
- If the session has stale Saga instructions and the restored saga uses `team-execution`, print a hard warning and re-read current `saga:work`, `saga:resume`, and `team-execution` skill files before proceeding.
- Treat stale instructions as a capability drift condition, not harmless context.

## Test Plan

Add or harden tests in `infiquetra-codex-plugins`:

### Saga plan tests

- A plan with `recommended_backend: team-execution` must contain `## Team Structure` before plan-ready status.
- If the operator picks inline, the plan must not claim `orchestration_operator_choice: team-execution`.

### Saga save/state tests

- `saga.py save --orchestration-mode team-execution --lifecycle-phase work` with empty `--orchestration-ref` should fail or produce a blocking validation warning.
- `orchestration_operator_choice` should not default to `orchestration_mode` unless the operator actually chose it.
- If `orchestration_mode != orchestration_operator_choice`, require non-empty `orchestration_downgrade` or equivalent provenance field.

### Work/resume tests

- A restored `team-execution` saga with no `## Team Structure` must stop and request Phase A repair.
- A restored `team-execution` saga with valid `## Team Structure` and no subagents must run serial role prompts, not inline.
- A "no useful parallel split" condition must not downgrade team-execution.

### Outcome dispatch tests

- Dispatching a `team-execution` node emits or links a team-execution artifact.
- Dispatch receipt includes `orchestration_ref`.
- Missing artifact emission HALTs visibly.

### Team-execution tests

- `protocol_probe.py --subagents absent` remains a passing serial fallback.
- `protocol_probe.py --subagents present --spawn-result backpressure` remains a passing serial fallback.
- Required missing validator tools still block completion.

### Regression tests against observed failures

Use fixtures modeled on the observed sessions:

- CAMPPS-style: saga says team-execution, leaf tries to record inline downgrade because "no useful parallel split". Expected: reject or require explicit operator override with downgrade provenance.
- Norns-style: restored saga says team-execution but current run says inline. Expected: either actual operator choice inline is recorded cleanly, or team-execution Phase B proceeds.
- infiquetra-claude-plugins-style: plan frontmatter says `recommended_backend: team-execution` but no `## Team Structure`. Expected: plan is not approval-ready.
- home-lab-style: existing saga has `orchestration_mode: team-execution` and empty `orchestration_ref`. Expected: resume reports incomplete team-execution setup.

## Quick Reproduction Commands

Find recent metadata-only team-execution traces:

```bash
/opt/homebrew/bin/rg -n \
  "orchestration_mode|orchestration_ref|orchestration_recommended|orchestration_operator_choice|orchestration_downgrade|Team Structure|backend not directly available|no useful parallel split|executed inline" \
  ~/.codex/sessions/2026/06/28 ~/.codex/sessions/2026/06/29 ~/.codex/sessions/2026/06/30
```

Check active session/provider state:

```bash
sqlite3 -separator ' | ' ~/.codex/state_5.sqlite \
  "select id, datetime(updated_at,'unixepoch'), model_provider, thread_source, cwd, git_branch, substr(title,1,100), rollout_path from threads order by updated_at desc limit 30;"
```

Check plans that recommend team-execution but lack the protocol section:

```bash
/opt/homebrew/bin/rg -n "recommended_backend: team-execution|^## Team Structure|devils-advocate-reviewer|security-reviewer|architecture-reviewer" docs/plans
```

Run current low-level proof:

```bash
python3 plugins/team-execution/scripts/protocol_probe.py --subagents absent --pretty
PYTHONPATH=. python3 -m pytest -q tests/test_outcome_dispatcher.py plugins/team-execution/tests/test_protocol_probe.py
```

## Fix Acceptance Criteria

Consider this fixed only when all are true:

- A plan cannot be considered team-execution-ready without `## Team Structure` or a linked team-execution artifact.
- `orchestration_mode: team-execution` cannot enter work/resume execution with empty `orchestration_ref` unless a repair step runs first.
- Generic spawned subagents are never counted as team-execution unless selected from `## Team Structure` and included in reviewer/validator evidence.
- Lack of delegated subagents triggers serial mode, not inline fallback.
- Saga state distinguishes:
  - recommendation,
  - actual operator choice,
  - AI downgrade/fallback,
  - actual execution vehicle.
- Old sessions with stale Saga instructions are detected before continuing team-execution work.
- The observed CAMPPS, Norns, infiquetra-claude-plugins, and home-lab failure shapes are covered by tests.

## Status

DONE_WITH_CONCERNS.

The current source has enough pieces to support correct behavior, but the lifecycle contract is not enforced end to end. The highest-value repair is to make `team-execution` impossible to record as a bare backend label once execution starts.
