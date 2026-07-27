---
title: Simplify lifecycle internals and external harness execution
repo: infiquetra-codex-plugins
type: capability
team: asgard
project: operations
status: Shaping
labels: capability, hermes-task, needs-plan
risk: high
handoff_maturity: requirements-ready
approval_state: approved
---

# Simplify lifecycle internals and external harness execution

### Objective

`improve-codex-plugins` — preserve the public plugin lifecycle while reducing the internal machinery required to use it.

### Intent

Perform a contract-preserving simplification of Saga, Fleet Core, Mission Control, and Deploy, using the current Verified Workflows V2 behavior as a preserve-unless-broken baseline. Trace each named operator path to its active callers and authority owner, then keep, simplify, or retire underlying machinery based on current evidence.

Replace the active external-action lifecycle with a small extensible harness capability owned by its caller. Saga may make direct read-only calls; Verified Workflows may assign bounded reads, reviews, or non-overlapping workspace writes while Codex root retains Git authority and verifies the resulting diff.

Reuse defects #49, #50, #51, #52, and #58 as independently verifiable children. Issue #59 remains the `improve-antigravity-plugins` companion and is not repurposed.

### Out-of-scope / non-goals

- Removing or semantically consolidating a public skill without separate operator approval.
- Building another workflow engine, action store, approval-fingerprint system, provider-promotion lifecycle, claim/replay layer, or cost-control plane.
- Weakening Mission Control, Deploy, credential, secret-egress, workspace-ownership, or Git safety boundaries.
- Redesigning Verified Workflows merely to make every plugin change uniformly.
- Giving raw external output independent check or reviewer-gate authority.

### Files expected to change

- `plugins/saga/scripts/`
- `plugins/saga/skills/`
- `plugins/fleet-core/scripts/`
- `plugins/verified-workflows/`
- `plugins/mission-control/`
- `plugins/deploy/`
- `tests/`
- `docs/saga/`
- `docs/engineering-journal/`

### Tests to add or update

- Reachability and active-consumer coverage for retained lifecycle and Fleet Core machinery.
- Direct external-harness canaries for model, effort, `USER`, noninteractive execution, secrets, unavailable routes, and requested-versus-observed truth.
- Verified Workflow coverage for bounded external writes, changed-path auditing, Git-authority violations, native verification, and non-gating external results.
- Regression coverage proving unchanged authorized calls do not traverse a second approval or dedicated external-action state lifecycle.
- Current V2 proof and all affected plugin inventory, documentation, packaging, and migration checks.

### Context library links

- `docs/brainstorms/2026-07-26-codex-plugin-lifecycle-simplification-requirements.md`
- `docs/brainstorms/2026-07-24-codex-v2-orchestrated-execution-system-requirements.md`
- `docs/brainstorms/2026-07-11-codex-external-advisory-execution-contract-requirements.md`
- `docs/reviews/2026-07-12-codex-plugins-improvement-review.md`
- https://github.com/infiquetra/infiquetra-context-library/blob/main/docs/ai-context/context-audit-standard.md
- https://github.com/infiquetra/infiquetra-codex-plugins/issues/59

### Inputs inventory

- 23 active `external_action_*` and `engine_*` scripts totaling 11,122 lines.
- Six Saga skills repeat the external-action operating section.
- Existing route and environment defects: #49, #50, #51, and #52.
- Existing portable-V2 defect: #58.
- Current Verified Workflows V2 QA and runtime-readback proof.

### Failure modes / pre-mortem

- Renaming current concepts without deleting states, branches, prompts, or duplicated ownership.
- Deleting a public capability because its internal implementation is expensive.
- Replacing the current provider machinery with a nominally smaller but still independent framework.
- Allowing an external writer to exceed assigned paths or mutate Git metadata.
- Breaking the recently simplified V2 path while attempting to standardize external execution.

### Stop conditions

- Stop before any public skill or distinct promised capability removal and return for explicit operator approval.
- Stop if a proposed capability cannot identify both a net complexity reduction and a before-and-after operator-path proof.
- Stop if external direct writes cannot preserve V2 ownership, root Git authority, changed-path auditing, and native verification.
- Stop if a new durable state or approval mechanism is proposed without showing which requirement cannot be met by caller-owned state.

### Acceptance criteria

- [ ] The active external-action/engine footprint reported by `rg --files plugins/saga/scripts | rg '/(external_action_|engine_).*\.py$' | xargs wc -l` is lower than the 23-file, 11,122-line baseline, and every retained component has a named active caller or safety reason.
- [ ] `python3 -m pytest plugins/saga/tests/test_external_action_adapters.py tests/test_external_action_adapters.py tests/test_external_action_integration.py -q` passes focused direct-harness canaries for requested model and effort, required environment preservation, secrets, truthful unavailability, and observed identity.
- [ ] `python3 -m pytest tests/test_verified_workflow_external_actions.py tests/test_verified_workflows_orchestration_regressions.py -q` passes bounded external-write, root-audit, native-gate, and V2-regression coverage.
- [ ] `rg -n 'approval fingerprint|claim/replay|provider promotion|consumption state' plugins/saga/skills plugins/saga/scripts` finds no active normal-path dependency on a dedicated external-action lifecycle; any historical or compatibility match is explicitly classified.
- [ ] `python3 scripts/validate_codex_plugins.py` exits 0 with manifests, active skill surfaces, inventories, and documentation aligned.
- [ ] `python3 -m pytest -q` exits 0 after the focused proofs pass.

### Verification

```bash
rg --files plugins/saga/scripts |
  rg '/(external_action_|engine_).*\.py$' |
  xargs wc -l
python3 -m pytest \
  plugins/saga/tests/test_external_action_adapters.py \
  tests/test_external_action_adapters.py \
  tests/test_external_action_integration.py \
  tests/test_verified_workflow_external_actions.py \
  tests/test_verified_workflows_orchestration_regressions.py \
  -q
rg -n \
  'approval fingerprint|claim/replay|provider promotion|consumption state' \
  plugins/saga/skills plugins/saga/scripts
python3 scripts/validate_codex_plugins.py
python3 -m pytest -q
```

### Handoff maturity

requirements-ready

### Suggested next action

Use `saga:plan <issue>` to produce the keep/simplify/retire inventory, child dependency order, and implementation proof.

### Source context

- Source: `docs/brainstorms/2026-07-26-codex-plugin-lifecycle-simplification-requirements.md`
- Existing children: #49, #50, #51, #52, #58
- Cross-objective companion: #59

## Created Issue

- URL: https://github.com/infiquetra/infiquetra-codex-plugins/issues/61
- Number: 61
- Created at: 2026-07-27T00:30:52.055358+00:00
