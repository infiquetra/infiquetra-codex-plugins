---
name: run
description: Run an approved Infiquetra workflow as a root-owned Codex DAG with explicit steps, dependencies, logical roles, mutation boundaries, reviewer and validator gates, and evidence. Use for nontrivial approved work that names Verified Workflows or includes a Workflow Structure contract. This unpublished U9 surface defines identity and ownership only; runtime dispatch and attestation arrive in U4.
---

# Run Verified Workflow

Use this skill for an approved plan that contains or references `## Workflow Structure`.

## U9 Runtime Boundary

This package is an unpublished development target. U9 establishes the canonical package,
skill, state, receipt, and compatibility vocabulary. It does not yet claim that managed
profiles, native subagent receipts, workflow dispatch, or gates exist. Those runtime surfaces
must be supplied and proven by U3 and U4 before this skill can make an execution claim.

Until then:

- Do not create state, profiles, hooks, or receipts under the retired legacy identity.
- Do not label generic subagent help as a Verified Workflow run.
- Do not claim `verified-workflow-subagent` or `verified-workflow-inline` evidence.
- Route implementation through the approved root-owned Saga work process and record the actual
  backend truthfully.

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
