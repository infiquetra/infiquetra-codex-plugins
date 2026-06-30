---
date: 2026-06-30
topic: team-execution-saga-orchestration-repair
focus: Fix the pain point where Saga records or recommends team-execution but Codex executes inline or with generic subagents instead of the Team Execution protocol
scope: standard
repo: infiquetra-codex-plugins
maturity: idea-ready
---

# Ideation: Team Execution Saga Orchestration Repair

## Grounding Context

**Repo:** `infiquetra-codex-plugins` is the Codex-native adapter repo for selected Infiquetra plugins. The active surface is Codex manifests, skills, references, scripts, tests, docs, and marketplace metadata, not installed cache copies or Claude command surfaces. The relevant plugins are `saga` and `team-execution`.

**Debug report:** `docs/investigations/2026-06-30-team-execution-saga-orchestration-debug-report.md` identifies metadata-only Team Execution as the current pain point: Saga state or plan frontmatter can say `team-execution`, while the plan lacks `## Team Structure`, `orchestration_ref` is empty, and actual work runs inline or through generic subagents.

**Current contracts:** `plugins/team-execution/skills/team-execution/SKILL.md` defines Team Execution as a two-phase reviewer/validator protocol. Phase A adds `## Team Structure`; Phase B parses it, executes roles, runs reviewers and selected validators, records evidence, and reports gate results. Delegated and serial modes are both valid; lack of delegated subagents should trigger serial Team Execution, not inline fallback.

**Current gap:** `plugins/saga/skills/plan/SKILL.md` currently records only `--orchestration-mode <inline|team-execution>` when the backend is selected. `plugins/saga/skills/work/SKILL.md` similarly records the mode and then proceeds through Saga's own inline/serial/parallel execution strategy. `plugins/saga/scripts/saga.py` accepts `orchestration_mode=team-execution` with empty `orchestration_ref`.

**Existing leverage:** The repo already has `plugins/saga/scripts/team_emitter.py`, `plugins/saga/scripts/outcome_dispatcher.py::team_execution_artifact()`, managed Codex agent TOML for Team Execution, `plugins/team-execution/scripts/sync_codex_agents.py`, and `plugins/team-execution/scripts/protocol_probe.py`. The low-level pieces exist; the missing layer is lifecycle enforcement and workflow integration.

**Context-libraries:** None consulted. This is a repo-local Saga/team-execution integration pain point.

## Topic Axes

- Artifact readiness: tying `team-execution` to a concrete `## Team Structure` or evidence root.
- Phase A materialization: making plan and outcome dispatch create or link the protocol artifact.
- Phase B execution and resume: making work and resume parse and run Team Execution rather than inline strategy.
- Delegation semantics: distinguishing generic subagents, delegated team roles, serial team roles, and inline assist.
- Capability and staleness guardrails: proving agent availability, preserving serial fallback, and detecting stale instructions.

## Ranked Survivors

### 1. Team Execution Receipt Lease

Make `team-execution` executable only when Saga holds a concrete receipt that points to `## Team Structure` or a Team Execution evidence root.

Saga may still recommend `team-execution` during planning, but work, resume, and outcome execution cannot treat it as the active vehicle unless the ref resolves and declares runtime mode, role roster, and evidence root. This combines the receipt, lease, and artifact-first derivation ideas into one enforceable contract.

The rationale is direct: the observed failure is `orchestration_mode: team-execution` with no `## Team Structure` and empty `orchestration_ref`. The downside is that save or entrypoint validation needs phase-aware rules so early drafting is not blocked prematurely.

| field | value |
|-------|-------|
| basis | direct: `docs/investigations/2026-06-30-team-execution-saga-orchestration-debug-report.md` says empty `orchestration_ref` enables metadata-only Team Execution |
| confidence | 94 |
| complexity | Med |
| axis | Artifact readiness |
| status | Unexplored |

### 2. Phase A Materializer In `saga:plan`

When the operator selects `team-execution`, `saga:plan` should emit or link the Team Execution Phase A artifact before the plan can be called ready.

The implementation should use existing machinery first: `team_emitter.py` and `outcome_dispatcher.team_execution_artifact()` already know how to produce `## Team Structure`. The plan should save `orchestration_mode=team-execution` together with `orchestration_ref=<plan>#team-structure` or a generated Team Execution artifact path.

The rationale is that plan-time intent is where the protocol should become tangible. The downside is that Phase A role and validator selection must stay concise enough not to bloat every plan.

| field | value |
|-------|-------|
| basis | direct: Team Execution Phase A requires `## Team Structure`, while current `saga:plan` records only `--orchestration-mode` |
| confidence | 91 |
| complexity | Med |
| axis | Phase A materialization |
| status | Unexplored |

### 3. Phase B Dispatcher Contract

If the effective backend is `team-execution`, `saga:work` and `saga:resume` should dispatch to Team Execution Phase B instead of choosing their own execution strategy.

Phase B parses the receipt or `## Team Structure`, runs implementation roles, then reviewer consensus, selected validators, evidence writes, and gate reporting. Inline work remains possible only as a serial implementation of a selected Team Execution role, not as a silent downgrade out of the protocol.

The rationale is ownership: Saga routes and records, while Team Execution owns reviewers, validators, and evidence. The downside is that this creates a real integration seam that needs clear tests for missing, stale, and partially complete artifacts.

| field | value |
|-------|-------|
| basis | direct: `plugins/saga/references/operator-choice.md` says Team Execution owns the run, while current `saga:work` records the mode and then follows Saga's strategy picker |
| confidence | 90 |
| complexity | High |
| axis | Phase B execution and resume |
| status | Unexplored |

### 4. Role And Vehicle Provenance Ledger

Record what actually ran with typed provenance, not just whether some agent activity happened.

Use explicit categories such as `generic-subagent`, `team-execution-delegated`, `team-execution-serial`, and `inline-assist`, and bind Team Execution entries to roles from the Team Structure. Generic helper agents can still be useful, but they cannot satisfy reviewer consensus or validator gates unless they are role-bound.

The rationale is that the debug report found generic subagents being confused with Team Execution. The downside is schema churn: Saga state, evidence records, and docs need to agree on the names.

| field | value |
|-------|-------|
| basis | direct: the debug report lists generic spawned Codex subagents not tied to reviewers, validators, evidence gates, or serial fallback roles |
| confidence | 86 |
| complexity | Med |
| axis | Delegation semantics |
| status | Unexplored |

### 5. Capability Probe As Lifecycle Gate

Turn Codex agent availability into a deterministic Team Execution runtime decision: delegated when proved, serial otherwise.

Before delegating, probe the real callable Codex agent surface and record the result in the receipt. Missing, unsafe, stale, or backpressured agents select `serial` Team Execution with the same roles; they do not trigger inline fallback.

The rationale is direct: `protocol_probe.py --subagents absent` already proves serial mode is valid. The downside is that the current probe is deterministic simulation; the implementation needs a real host-capability check or a documented host-interface boundary.

| field | value |
|-------|-------|
| basis | direct: Team Execution supports delegated and serial modes, and the local protocol probe passes with absent subagents |
| confidence | 84 |
| complexity | Med |
| axis | Capability and staleness guardrails |
| status | Unexplored |

### 6. Resume Repair And Stale-State Quarantine

Make `saga:resume` repair or quarantine contradictory Team Execution state before it routes back into work.

On restore, detect `team-execution` with empty ref, missing `## Team Structure`, inline-only evidence, generic subagent traces, stale instruction roots, or prose that contradicts the frontmatter. The allowed outcomes are: locate the artifact, regenerate Phase A, continue serial Team Execution, or explicitly downgrade with provenance.

The rationale is that resume is where bad metadata gets replayed into new work. The downside is that repair heuristics must be conservative so they do not silently invent a Team Structure for work whose plan never really selected it.

| field | value |
|-------|-------|
| basis | direct: the debug report documents stale-session, empty-ref, and contradictory durable-state failures |
| confidence | 81 |
| complexity | Med |
| axis | Capability and staleness guardrails |
| status | Unexplored |

## Did not survive (revivable)

Explicit rejection is the quality mechanism. Cut ideas keep stable ids so they can be revived with new evidence.

| id | title | summary | reason | status |
|----|-------|---------|--------|--------|
| R1 | Orchestration Contract Compiler | Compile Saga intent into a normalized contract artifact plus human `## Team Structure`. | Valuable but absorbed by Receipt Lease and Phase A Materializer; too much abstraction for the first fix. | rejected |
| R2 | Evidence Index Under Receipt | Add a machine-readable index of role artifacts, gate outputs, and evidence. | Strong implementation detail, but should follow after the receipt and Phase B seam exists. | rejected |
| R3 | Orchestration State Machine | Model Team Execution as selected, materialized, checked, executing, reviewed, validated, and closed. | Too broad for this pain point; revive if receipt fields prove insufficient. | rejected |
| R4 | Dispatch Receipt Becomes The Handoff | Make outcome advance return a full Team Execution receipt. | Outcome-specific extension; defer until the plan, work, and resume path is fixed. | rejected |
| R5 | Stale Artifact Invalidates Execution | Version or hash Team Execution artifacts and refuse stale ones. | Useful but narrower than Resume Repair and Stale-State Quarantine. | rejected |
| R6 | Saga Strategy Removal For Team Execution | Remove Saga's strategy picker when Team Execution is selected. | Duplicates Phase B Dispatcher Contract. | rejected |

No topic axis has zero survivors. The strongest cut ideas should be revived only after the core receipt, Phase A materializer, and Phase B dispatcher contract are settled.

## Co-ideation log

The operator supplied five seeds. They were passed into the frame agents, merged into the candidate pool, and critiqued under the same rubric as generated ideas.

| source | entered | idea / seed | outcome |
|--------|---------|-------------|---------|
| user-seed | Phase 0 | Make `team-execution` non-recordable without an artifact once execution starts. | survived as #1 |
| user-seed | Phase 0 | Make `saga:plan` run Team Execution Phase A when selected. | survived as #2 |
| user-seed | Phase 0 | Make `saga:work` and `saga:resume` treat selected `team-execution` as Phase B. | survived as #3 |
| user-seed | Phase 0 | Separate generic subagents from Team Execution roles. | survived as #4 |
| user-seed | Phase 0 | Verify real Codex agent surface and fall back to serial roles. | survived as #5 |
| frame-agent | Phase 2 | Resume repair / stale-state quarantine. | survived as #6 |
| frame-agent | Phase 2 | Evidence index under receipt. | cut -> R2 |
| frame-agent | Phase 2 | Orchestration state machine. | cut -> R3 |
