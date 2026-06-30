---
date: 2026-06-30
topic: team-execution-saga-orchestration-repair
maturity: requirements-ready
source: "docs/ideation/2026-06-30-team-execution-saga-orchestration-repair-ideation.md: all six ranked survivors"
---

# Team Execution Saga Orchestration Repair Requirements

## Summary

Repair the Saga and Team Execution bridge so `team-execution` means a concrete two-phase protocol run, not a metadata label. Saga may recommend and record the choice, but work and resume can only execute it when a Team Execution receipt points at `## Team Structure` or a valid evidence root.

The repair keeps Team Execution as an active Codex capability. It adds the missing lifecycle trigger, dispatch contract, provenance, capability gate, and resume repair behavior needed to make the existing intent actually run.

## Problem Frame

Recent sessions show the same failure in several shapes: Saga state or plan frontmatter says `team-execution`, but the plan lacks `## Team Structure`, `orchestration_ref` is empty, and actual work happens inline or through generic subagents. The task may still complete, but reviewer consensus, selected validators, serial fallback evidence, and Team Execution gate reporting never happen.

The low-level pieces already exist. Team Execution defines Phase A planning and Phase B orchestration. Saga records `orchestration_mode` and `orchestration_ref`. The repo has `team_emitter.py`, `outcome_dispatcher.team_execution_artifact()`, and `protocol_probe.py`. The gap is the lifecycle contract that connects these pieces at the point where planning becomes execution.

This is not a reason to remove Team Execution from the Codex plugin. It is also not a full Saga rewrite. The bounded fix is to make Team Execution artifact-backed, phase-aware, and truthful about what actually ran.

## Operating Model

The selected backend becomes executable only after Team Execution has a receipt.

```text
Plan recommendation / operator choice
          |
          v
Team Execution Phase A materializes receipt
  - ## Team Structure or linked artifact
  - runtime expectation
  - selected workers, reviewers, validators, gates
  - evidence/state root
          |
          v
Saga records team-execution + non-empty orchestration_ref
          |
          v
Work / resume dispatches Team Execution Phase B
          |
          +--> delegated roles when callable and safe
          |
          +--> serial roles when delegation is unavailable, unsafe, or backpressured
          |
          v
Reviewer consensus, validators, evidence, gate report
```

## Key Decisions

- **Keep Team Execution active.** The problem is not that Codex has a Team Execution intent; the problem is that Saga can currently preserve the intent without making the Team Execution protocol tangible.
- **Receipt-backed execution is the trigger.** `orchestration_mode: team-execution` is not executable by itself. The executable trigger is a non-empty `orchestration_ref` that resolves to `## Team Structure` or a Team Execution evidence root.
- **Phase A belongs before plan readiness.** When the operator accepts `team-execution`, the plan cannot be considered ready until Team Execution Phase A has selected roles, gates, runtime expectation, and evidence/state location.
- **Phase B owns execution once selected.** If the effective backend is `team-execution`, `saga:work` and `saga:resume` route into Team Execution Phase B rather than selecting their own inline execution strategy.
- **Serial is Team Execution, not a downgrade to inline.** Missing, unsafe, or backpressured subagents select serial Team Execution with the same roles and gates. Inline execution is only valid after an explicit downgrade or operator choice.
- **Generic subagents do not satisfy Team Execution gates.** A spawned helper counts only as generic work unless it is a selected role from `## Team Structure` and its output feeds reviewer, validator, or evidence gates.
- **State must separate intent from reality.** Saga state must distinguish recommendation, operator choice, AI downgrade, actual execution vehicle, and Team Execution role provenance.
- **Resume repairs before continuing.** A restored saga with contradictory Team Execution state must locate the artifact, regenerate Phase A, continue serial Team Execution, or explicitly downgrade with provenance before work proceeds.
- **Outcome dispatch follows the same invariant.** Outcome leaf dispatch does not need a larger redesign for this fix, but any Team Execution leaf must emit or link a Team Execution artifact before being treated as dispatched.

## Actors

- A1. Saga operator: chooses or confirms the execution backend and expects resumed state to match what actually happens.
- A2. Saga planner: recommends `team-execution`, writes the plan, and records lifecycle state.
- A3. Saga worker/resumer: restores a plan or saga tick and must route execution without silently losing the selected protocol.
- A4. Team Execution Phase A materializer: creates or links the `## Team Structure` receipt with roles, gates, runtime expectation, and evidence root.
- A5. Team Execution Phase B runner: executes worker roles, reviewers, validators, remediation loops, evidence writes, and gate reporting.
- A6. Codex agent capability probe: determines whether delegated roles are callable and safe, or whether serial Team Execution is required.
- A7. Reviewer or maintainer: verifies that tests cover metadata-only, generic-subagent, serial fallback, stale-session, and contradictory-state failures.

## Requirements

**Receipt And Readiness Contract**

- R1. Saga must not treat `team-execution` as executable unless a Team Execution receipt exists.
- R2. The receipt must resolve to either a `## Team Structure` section or a Team Execution evidence/state root.
- R3. The receipt must identify runtime expectation, role roster, reviewer and validator gates, evidence/state location, and main-thread final verification.
- R4. Empty `orchestration_ref` may be allowed during early drafting, but must block or trigger repair before work, resume, outcome dispatch, QA closeout, or any phase that claims Team Execution execution.
- R5. A plan or saga tick may recommend `team-execution` without being executable, but must label that state as recommendation or pending materialization rather than actual execution.

**Phase A Materialization**

- R6. When the operator accepts `team-execution` in `saga:plan`, Phase A must append or link a Team Execution artifact before the plan is called ready.
- R7. Phase A must select base reviewers, relevant validators, blocking gates, runtime expectation, and evidence/state location.
- R8. Phase A must save `orchestration_mode=team-execution` together with a non-empty `orchestration_ref`, while preserving distinct recommendation and operator-choice provenance.
- R9. Phase A should reuse existing Team Execution emission machinery where it fits instead of inventing a parallel artifact format.
- R10. If Phase A cannot materialize a receipt, the plan must remain blocked or explicitly choose a different backend; it must not publish metadata-only Team Execution.

**Phase B Dispatch**

- R11. `saga:work` must dispatch to Team Execution Phase B whenever the effective executable backend is `team-execution`.
- R12. `saga:resume` must dispatch to Team Execution Phase B after restoring a valid Team Execution receipt.
- R13. Phase B must parse the approved Team Structure or evidence root before mutating work.
- R14. Phase B must run selected worker roles, required reviewers, selected validators, automation gates, evidence writes, and gate reporting.
- R15. A small leaf, no useful parallel split, or unavailable delegated subagents must not by itself downgrade selected Team Execution to inline.
- R16. Inline execution remains allowed when the operator chose inline, or when a Team Execution downgrade is explicit and recorded with rationale and provenance.

**Role And Vehicle Provenance**

- R17. Saga and Team Execution evidence must record what actually ran using typed vehicle provenance.
- R18. Provenance vocabulary must distinguish at least `generic-subagent`, `team-execution-delegated`, `team-execution-serial`, and `inline-assist`.
- R19. A Team Execution role entry must bind to a role declared in the Team Structure.
- R20. Generic subagents and ad hoc helpers may be recorded as assistance, but must not satisfy reviewer consensus or validator gates.
- R21. Saga state must keep recommendation, actual operator choice, AI downgrade or fallback, and actual execution vehicle distinct; operator choice must not be inferred from mode when the operator did not explicitly choose it.
- R22. State merge or resume behavior must not preserve `orchestration_mode: team-execution` as the actual vehicle while prose or evidence says the work ran inline.

**Capability Probe And Runtime Selection**

- R23. Team Execution must prove or characterize the current Codex delegation surface before dispatching selected roles as subagents.
- R24. Missing, unsafe, stale, or backpressured delegation must select serial Team Execution rather than inline fallback.
- R25. Serial Team Execution must run the same selected roles and record serial limitations in evidence.
- R26. Required validator tools or capabilities that are missing must block completion unless the operator explicitly accepts the residual risk.
- R27. The deterministic protocol probe must remain usable as a local proof path, while planning may define the exact host-capability boundary for real sessions.

**Resume Repair And Stale-State Quarantine**

- R28. `saga:resume` must detect `team-execution` state with empty `orchestration_ref`.
- R29. `saga:resume` must detect plans that recommend or record `team-execution` without `## Team Structure` or a linked artifact.
- R30. `saga:resume` must detect generic-subagent traces being presented as Team Execution evidence.
- R31. `saga:resume` must detect contradictions where metadata says Team Execution but prose or evidence says inline execution.
- R32. `saga:resume` must detect stale Saga or Team Execution instruction roots when restored state depends on Team Execution semantics.
- R33. A detected stale or contradictory Team Execution state must resolve by locating the artifact, regenerating Phase A, continuing serial Team Execution, or explicitly downgrading with provenance.
- R34. Resume repair must be conservative: it must not silently invent a Team Structure for work whose plan never really selected Team Execution.

**Tests And Regression Coverage**

- R35. Tests must cover plans that recommend `team-execution` but lack Team Structure or a linked artifact.
- R36. Tests must cover `team-execution` with empty `orchestration_ref` entering work or resume.
- R37. Tests must cover absent delegated subagents selecting serial Team Execution.
- R38. Tests must cover generic subagents failing to satisfy Team Execution reviewer or validator gates.
- R39. Tests must cover contradictory state where `orchestration_mode` and actual execution vehicle diverge.
- R40. Tests must cover stale or old-session resume behavior when Team Execution semantics changed.
- R41. Tests must cover outcome dispatch of a Team Execution leaf emitting or linking a Team Execution artifact and surfacing its `orchestration_ref` before dispatch is considered successful.

## Key Flows

- F1. **Plan chooses Team Execution.** **Trigger:** `saga:plan` recommends Team Execution and the operator accepts it. Phase A creates or links the Team Structure receipt, records a non-empty ref, and only then allows the plan to become ready. **Covers R1, R2, R6, R7, R8, R10.**
- F2. **Work starts from a valid receipt.** **Trigger:** `saga:work` starts with executable `team-execution` state. Work parses the receipt, loads the Team Execution protocol, runs Phase B, records evidence, and reports gates. **Covers R11, R13, R14, R17.**
- F3. **Delegation is unavailable.** **Trigger:** selected Team Execution roles cannot be delegated. The capability gate selects serial Team Execution, records serial limits, and keeps reviewer and validator gates active. **Covers R23, R24, R25, R26.**
- F4. **Generic subagents helped but were not selected roles.** **Trigger:** a session contains spawned helper threads or lens agents. Evidence records them as generic assistance, but reviewer consensus and validator gates remain unsatisfied until selected Team Execution roles run. **Covers R18, R19, R20.**
- F5. **Resume restores contradictory state.** **Trigger:** `saga:resume` finds Team Execution metadata with missing receipt, inline prose, stale instruction roots, or generic-subagent evidence. Resume performs repair or explicit downgrade before continuing. **Covers R28, R29, R30, R31, R32, R33, R34.**
- F6. **Outcome dispatch selects a Team Execution leaf.** **Trigger:** an outcome leaf uses the Team Execution backend. Dispatch emits or links a Team Execution artifact, records the ref, and returns it in the dispatch receipt; otherwise it halts rather than dispatching metadata-only work. **Covers R1, R2, R8, R41.**

## Acceptance Examples

- AE1. **Metadata-only plan is not ready.** **Given:** a plan says `recommended_backend: team-execution` but lacks `## Team Structure` or a linked artifact. **When:** the plan is marked ready or routed to work. **Then:** the lifecycle reports missing Phase A materialization and does not claim executable Team Execution. **Covers R1, R5, R6, R10, R35.**
- AE2. **Team Execution work has a receipt.** **Given:** saga state has `orchestration_mode: team-execution` and a ref to Team Structure. **When:** `saga:work` starts. **Then:** it parses the Team Structure and enters Team Execution Phase B instead of choosing an inline strategy. **Covers R11, R12, R13.**
- AE3. **Empty ref blocks execution.** **Given:** a restored saga has `orchestration_mode: team-execution` and empty `orchestration_ref`. **When:** `saga:resume` runs. **Then:** it locates or regenerates Phase A, or records an explicit downgrade before work proceeds. **Covers R4, R28, R33, R36.**
- AE4. **Absent subagents run serial Team Execution.** **Given:** selected reviewers exist but delegated subagents are unavailable. **When:** the capability gate runs. **Then:** the run records serial Team Execution and executes the same selected roles sequentially rather than inline. **Covers R23, R24, R25, R37.**
- AE5. **Generic helper does not count as a reviewer.** **Given:** a generic spawned subagent writes useful analysis. **When:** Team Execution gates are evaluated. **Then:** the helper may appear in assistance provenance, but it does not satisfy reviewer consensus unless it was a selected Team Execution reviewer. **Covers R18, R19, R20, R38.**
- AE6. **Contradictory state is not preserved.** **Given:** metadata says Team Execution and prose says the real vehicle was inline. **When:** state is saved or resumed. **Then:** the lifecycle records the actual vehicle and downgrade provenance, or repairs into Team Execution before proceeding. **Covers R21, R22, R31, R39.**
- AE7. **Stale instructions trigger repair mode.** **Given:** a session started with old Saga instructions and later resumes Team Execution work. **When:** `saga:resume` reconstructs the run. **Then:** it rereads current Saga and Team Execution contracts before dispatching, and records stale-context repair evidence. **Covers R32, R33, R40.**
- AE8. **Outcome leaf cannot dispatch metadata-only Team Execution.** **Given:** an outcome leaf chooses Team Execution. **When:** dispatch cannot emit or link a Team Execution artifact. **Then:** dispatch halts visibly instead of minting a leaf saga with no executable Team Execution ref; when dispatch succeeds, the receipt includes the ref. **Covers R1, R2, R8, R41.**

## Success Criteria

- A plan cannot be considered Team Execution ready without `## Team Structure` or a linked Team Execution artifact.
- `orchestration_mode: team-execution` cannot enter work or resume with empty `orchestration_ref` unless repair runs first.
- Lack of delegated subagents selects serial Team Execution, not inline fallback.
- Generic spawned subagents are never counted as Team Execution reviewers or validators unless they are selected Team Structure roles.
- Saga state cleanly distinguishes recommendation, operator choice, downgrade or fallback, actual execution vehicle, and role provenance.
- Resume detects stale and contradictory Team Execution state before continuing.
- The observed metadata-only, generic-subagent, serial-fallback, stale-session, and contradictory-state failure shapes have tests.

## Scope Boundaries

- Do not remove Team Execution from the active Codex plugin set.
- Do not port Claude-only command, hook, or workflow mechanisms as active Codex surfaces.
- Do not make generic multi-agent usage equivalent to Team Execution.
- Do not require delegated subagents for Team Execution; serial mode is part of the protocol.
- Do not turn this into a full Saga rewrite or general OutcomeOrchestrator redesign.
- Do not introduce a separate evidence index or orchestration state machine in this slice unless planning proves the receipt contract cannot work without it.
- Do not edit installed Codex cache copies; this repo remains the maintained source.

## Dependencies / Assumptions

- Team Execution's two-phase contract remains the authority for reviewer and validator behavior.
- Saga remains the owner of lifecycle routing, recommendation, local saga state, and operator-choice recording.
- Team Execution remains the owner of selected roles, consensus, validators, evidence, and gate reporting once selected.
- `protocol_probe.py` is sufficient as deterministic local proof for serial fallback, but a real host-capability check may require additional planning.
- The exact ref syntax may be a plan anchor, a separate artifact path, or an evidence root, as long as it resolves deterministically.
- Outcome dispatch only needs to obey the same Team Execution artifact invariant for this slice; broader outcome handoff changes are deferred.

## Outstanding Questions

**Resolve before planning**

- None. The selected scope is all six surviving ideas combined into one lifecycle repair.

**Deferred to planning**

- Exact location and API shape for the central Team Execution readiness validator.
- Exact `orchestration_ref` format for plan anchors versus separate artifacts versus evidence roots.
- Exact durable schema or frontmatter fields for actual execution vehicle and role provenance.
- Exact real-session capability probe boundary beyond the deterministic `protocol_probe.py` helper.
- Exact sequencing between plan materialization, work/resume dispatch, and outcome-leaf enforcement.
- Whether the existing `saga:plan` and `saga:work` two-backend wording conflicts with `operator-choice.md`'s `manual` backend for this repair; keep it out of scope unless it affects Team Execution readiness or downgrade semantics.

## Sources / Research

- `docs/ideation/2026-06-30-team-execution-saga-orchestration-repair-ideation.md`: survivor set combined into this document.
- `docs/investigations/2026-06-30-team-execution-saga-orchestration-debug-report.md`: observed failures, root cause, proposed repair shape, and acceptance criteria.
- `plugins/team-execution/skills/team-execution/SKILL.md`: Team Execution Phase A, Phase B, serial fallback, state, and protocol probe contract.
- `plugins/team-execution/scripts/protocol_probe.py`: deterministic proof that absent or backpressured subagents select serial Team Execution.
- `plugins/saga/references/operator-choice.md`: Saga backend vocabulary and ownership split between Saga and Team Execution.
- `plugins/saga/skills/plan/SKILL.md`: current plan flow records `--orchestration-mode` but does not require Phase A materialization.
- `plugins/saga/skills/work/SKILL.md`: current work flow records `--orchestration-mode` before executing Saga's normal strategy.
- `plugins/saga/skills/resume/SKILL.md`: restore flow surfaces the orchestration pointer and is the natural repair/quarantine boundary.
- `plugins/saga/scripts/saga.py`: Saga state includes `orchestration_mode`, `orchestration_ref`, recommendation, operator choice, and downgrade fields.
- `plugins/saga/scripts/team_emitter.py`: existing emitter for `## Team Structure`.
- `plugins/saga/scripts/outcome_dispatcher.py`: existing outcome helper for Team Execution artifact emission.
- `docs/engineering-journal/DECISIONS.md`: active Codex backend and Saga-family boundary decisions.
- `docs/portability/matrix.md`: Team Execution Codex treatment requires managed Codex agents when available and serial fallback otherwise.
