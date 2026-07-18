---
name: review-workflow
description: Review an approved Workflow Structure for attainable root-inline, advisory-child, or strict-child evidence before workflow execution. Use when a plan contains `## Workflow Structure`, a workflow gate blocks unexpectedly, or the operator wants to confirm that named subagent profiles are not being mistaken for observed runtime proof.
---

# Review Workflow Feasibility

Review the evidence contract before treating a Workflow Structure as executable. The root Codex session remains the orchestrator and retains all mutation, integration, Git, gate, and completion authority.

Run the deterministic review against the approved plan and capability snapshot:

```bash
python3 plugins/verified-workflows/scripts/workflow_feasibility.py \
  --plan docs/plans/YYYY-MM-DD-topic-plan.md \
  --snapshot docs/validation/codex-runtime-capability-snapshot.json \
  --pretty
```

Interpret the result before asking for execution approval:

- `ready`: every gate-authoritative agent lens is root-inline, and root/deterministic rows are attainable. Profile fields remain requested configuration, not observed child facts.
- `requires-inline`: one or more preferred-independence `auto` or `subagent` rows may produce advisory child evidence but cannot satisfy the gate. Re-render those rows as `inline`, then obtain approval for the amended workflow.
- `strict-unavailable`: a required-independence row needs host-issued child attestation unavailable in the current runtime. Do not downgrade it silently; either supply the required capability or amend the workflow and obtain new approval.

The review is read-only. It does not spawn a child, install a profile, modify Codex configuration, or claim an observed child model, effort, sandbox, or permission boundary. Use `verified-workflows:select-agent` for ordinary native delegation after this review; that separate capability remains advisory unless an approved workflow has the attestation evidence it requires.
