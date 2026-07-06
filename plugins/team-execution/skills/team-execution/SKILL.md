---
name: team-execution
description: |
  Two-phase Codex protocol for Infiquetra work: plan reviewer and validator
  coverage, then execute approved work with reviewer consensus, selected
  validator gates, evidence capture, and guarded nonprod automation.
when_to_use: |
  Use this skill when a task benefits from a team protocol: 3+ steps, 3+ files,
  docs/spec changes, multiple work streams, contracts, deployments, review
  consensus, validator gates, or explicit team-execution requests.
---

# Team Execution

Use this skill to plan and run a structured reviewer and validator protocol for
Infiquetra work.

The Codex port has two runtime modes:

- `delegated`: Codex subagents are available and the work is safe to delegate.
- `serial`: subagents are unavailable, unsafe, or backpressured; the main thread
  runs each reviewer and validator role sequentially and records the limits of
  serial consensus.

Evidence records also carry a gate-facing `vehicle`:

- `team-execution-delegated` — the selected Team Execution role ran through a delegated Codex agent.
- `team-execution-serial` — the selected Team Execution role ran serially in the main thread.
- `generic-subagent` and `inline-assist` — useful assistance categories, but they do not satisfy
  reviewer or validator gates unless converted into selected Team Execution role evidence.

The main thread always owns final verification, state writes, mutation
confirmation, and the completion decision.

## Codex Agent Roster

The plugin ships the full upstream `team-execution` roster as managed Codex
TOML definitions under `plugins/team-execution/agents/*.toml`.

- Reviewer, scanner, tester, and monitor names in the registries map to the
  matching Codex agent name when delegated mode is available.
- Agent TOML records Claude source model lineage and Codex model hints. Use
  `model_reasoning_effort` and `codex_model_hint` as dispatch hints only where
  the active Codex host exposes that control; otherwise use the installed agent
  defaults.
- If a selected named agent is not installed, callable, safe to delegate, or the
  host reports backpressure, switch that role to serial execution in the main
  thread and record the fallback.

## References

Load only the files needed for the request:

- Reviewer selection: `references/reviewer-registry.md`
- Reviewer scoring: `references/review-criteria.md`
- Consensus loop: `references/consensus-protocol.md`
- Validator selection: `references/validator-registry.md`
- Validator gate criteria: `references/validator-criteria.md`
- Validator order: `references/validator-execution-order.md`
- Evidence state: `references/validator-evidence-state.md`
- Validator dispatch behavior: `references/validator-spawn-quirks.md`
- Artifact pointers (receiver contract): `references/artifact-pointers.md`
- Worker exit manifest: `references/worker-manifest.md`
- External-engine workers (chaperone): `references/external-engine-workers.md`
- Delegation safety: `references/delegation-safety.md`

## Phase A: Team Planning

Run Phase A during planning. Do not start implementation from this phase.

1. Inspect the request, repository signals, branch state, tests, workflows,
   contracts, docs, and optional `.team-execution.json`.
2. Classify the work as `code`, `docs/specs`, or `mixed`.
3. Select base reviewers and optional reviewers from
   `references/reviewer-registry.md`.
4. Select only relevant validators from `references/validator-registry.md`.
   Required validators block completion if they cannot run.
5. Choose the state location from `references/validator-evidence-state.md`.
   Prefer `.codex/team-execution/` only when it is ignored or otherwise
   protected from commits; otherwise use the user-local fallback.
6. Decide whether delegation is allowed using `references/delegation-safety.md`.
   Do not delegate secrets, credentials, production payloads, or protected
   operational data.
7. Add a concise `## Team Structure` section to the plan with workers,
   reviewers, validators, gates, state location, and runtime mode expectation.

Suggested plan section:

```markdown
## Team Structure

### Runtime
- Mode: delegated if Codex subagents are available and safe; otherwise serial.
- State root: .codex/team-execution/ when ignored, otherwise user-local fallback.
- Main-thread final verification: required.

### Reviewers
| Role | Required | Selection Reason |
|------|----------|------------------|
| devils-advocate-reviewer | yes | Base reviewer |
| security-reviewer | yes | Base reviewer |
| architecture-reviewer | yes | Base reviewer |

### Validators
| Role | Group | Required | Selection Reason | Blocking Rule |
|------|-------|----------|------------------|---------------|
| security-scanner | scanner | yes/no | [why selected] | hard-fail blocks completion |

### Gates
- Reviewer consensus threshold: overall >= 9.0/10 and no dimension < 7.0.
- Reviewer non-consensus blocks validators unless the user explicitly overrides.
- Selected required validators block completion when hard-failing or blocked.
- Maximum 3 remediation loops before escalation.
```

## Phase B: Orchestration

Run Phase B only after the plan is approved.

1. Parse the approved `## Team Structure`, selected roles, runtime mode, state
   root, and gates.
2. Complete the approved worker tasks. Keep changes scoped to the plan.
3. Run reviewers using `references/consensus-protocol.md`. In delegated mode,
   dispatch the selected named Codex agents when installed and safe; in serial
   mode, run the same role prompts in the main thread and mark evidence with
   `vehicle=team-execution-serial`.
4. If reviewer consensus fails, route fixes, repeat only the affected reviewers,
   and stop after 3 cycles with explicit residual risk.
5. Run selected scanner validators after consensus or explicit override.
6. Coordinate PR, CI, merge, or nonprod automation only when all applicable
   gates pass and the action is clearly allowed.
7. Run testers only after a target exists.
8. Run monitors for CI, workflow, or runtime signals selected in the plan.
9. Report changed files, reviewer scores, validator gate results, evidence
   paths, state location, automation actions, and residual risks.

Do not claim completion while required validators are hard-failing or blocked
unless the user explicitly accepts the residual risk.

### Step B1: Artifact-pointer threshold (pointerize vs inline)

When a spawn prompt would carry a large artifact (a full `git diff`, a changed-files summary),
pass a typed **artifact pointer** instead of inlined bytes once the payload crosses this threshold,
and let the receiver dereference it per `references/artifact-pointers.md`:

- Pointerize when the artifact is `> 4 KB` AND it goes to `>= 2 recipients`.
- Inline when the artifact is `<= 1 KB` or has a single recipient.
- Between those bounds, use judgment; inlining is always the safe fallback.

This is an advisory orchestrator rule applied by judgment, not a runtime-enforced gate. Git-object
(`diff`) pointers only resolve for a receiver that shares the parent repo's `.git/objects`
(same-cwd serial roles, linked-worktree children); when the receiver cannot run `git cat-file`
against the parent repo (e.g. an external-engine disposable clone), fall back to inlined content
for that receiver (capability-keyed KTD7 fallback).

## State And Evidence

Repo-local state uses:

```text
.codex/team-execution/
```

Use this location only when ignored or otherwise protected from commits. If it is
not protected, use:

```text
~/.codex/team-execution/state/<repo>/
```

State records should include selected roles, required tools, commands, evidence
paths, findings, gate result, remediation loop count, `execution_mode`, and
`vehicle`. Redact secrets,
tokens, credentials, production payloads, and protected operational data before
writing state.

## Protocol Probe

For deterministic local proof, run the bundled probe:

```bash
python3 plugins/team-execution/scripts/protocol_probe.py --subagents absent --pretty
```

Use `--subagents present` for simulated delegated-mode characterization and
`--spawn-result backpressure` to prove serial fallback when delegation cannot be
used.
