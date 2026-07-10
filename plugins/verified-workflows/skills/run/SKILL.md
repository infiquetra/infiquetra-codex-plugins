---
name: run
description: Run an approved Infiquetra workflow as a root-owned Codex DAG with explicit steps, dependencies, logical roles, mutation boundaries, reviewer and validator gates, and evidence. Use for nontrivial approved work that names Verified Workflows or includes a Workflow Structure contract. This unpublished U3 surface defines role and expected-profile policy; runtime dispatch and attestation arrive in U4.
---

# Run Verified Workflow

Use this skill for an approved plan that contains or references `## Workflow Structure`.

## U3 Runtime Boundary

This package is an unpublished development target. U9 established canonical identity and
compatibility. U3 adds the 25 versioned role lenses and five managed profile definitions, with
explicit-isolated render, one-snapshot catalog resolution, partitioned sync/readback, recovery, and
rollback proof. An implicit `$CODEX_HOME` is real, never an isolated test target. Profile presence
proves expected configuration only. Native subagent receipts, workflow dispatch, and gates must be
supplied and proven by U4 before this skill can make an execution claim.

Until then:

- Do not create state, hooks, or receipts under the retired legacy identity.
- Do not install or migrate profiles in the real Codex home before the U8 cutover gate.
- Do not label generic subagent help as a Verified Workflow run.
- Do not claim `verified-workflow-subagent` or `verified-workflow-inline` evidence.
- Route implementation through the approved root-owned Saga work process and record the actual
  backend truthfully.

## Role And Profile Contract

Read `plugins/verified-workflows/config/role-registry.yaml` and the selected file under
`plugins/verified-workflows/roles/`. Select only a class listed in that role's `allowed_classes`.
A workflow step may elevate `preferred` independence to `required`; it may never lower a role whose
minimum is `required`.

```text
logical role + risk
        |
        v
allowed execution class --> immutable catalog --> managed profile digest
        |                                           |
        +--> role boundary may narrow                +--> expected config only
                                                    runtime proof waits for U4
```

All 25 current roles are `agent-lens`. Do not relabel a scanner or tester as deterministic merely
because it can run a tool: a deterministic validator needs one contained pinned command and an
evidence schema that cover its entire behavior without judgment or interpretation. Keep model,
effort, and fallback policy in fleet-core; keep role-specific criteria in the role lens.

## Ownership Contract

The root Codex thread owns the workflow DAG, lifecycle state, scope, integration, Git operations,
mutation gates, barrier waits, result consolidation, remediation routing, and completion decision.
Children are bounded evidence producers. Peer messaging is optional and never a protocol
requirement.

```text
approved plan
    |
    v
root thread -- owns DAG, scope, writes, barriers, and final decision
    |
    +--> bounded role step ------> evidence receipt
    +--> deterministic validator -> evidence receipt
    +--> independent reviewer ---> evidence receipt
    |
    v
root verifies required evidence and adjudicates completion
```

## Canonical Contract

New artifacts use:

- Plugin and skill: `verified-workflows:run`
- Saga workflow mode: `verified-workflow`
- Plan section and anchor: `## Workflow Structure` / `#workflow-structure`
- Repo state root: `.codex/verified-workflows/` only when protected from commits
- User fallback: `~/.codex/verified-workflows/state/<repo>/`
- Git snapshots: `refs/verified-workflows/snapshots/`
- Receipt vehicles: `verified-workflow-subagent` and `verified-workflow-inline`
- Evidence key: `verified_workflow_ref`

Readers may accept the exact legacy aliases through fleet-core's closed `workflow_compat`
registry. Serializers write only canonical values. Unknown aliases fail closed.

## Safety

- Never delegate secrets, credentials, production payloads, or protected operational data.
- A child cannot expand scope, authorize mutation, merge, deploy, or declare completion.
- Required independent review cannot degrade to inline execution.
- Missing required evidence blocks the corresponding gate; it is not converted to a pass.
- Do not install this unpublished package or modify a real Codex profile before the U8 cutover.
