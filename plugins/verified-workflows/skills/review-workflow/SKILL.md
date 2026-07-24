---
name: review-workflow
description: Review an approved Workflow Contract for Codex V2 profile, graph, context, write, check, reviewer, fallback, and external-action feasibility without launching work.
---

# Review Workflow Feasibility

Validate the operator-visible `## Workflow Contract` before execution. The main Codex session remains the sole orchestrator and owns dependency release, integration, Git, gate, and completion decisions.

Run the read-only compiler and capability review:

```bash
python3 plugins/verified-workflows/scripts/workflow_feasibility.py \
  --plan docs/plans/YYYY-MM-DD-topic-plan.md \
  --plan-revision <approved-git-revision> \
  --snapshot docs/validation/codex-runtime-capability-snapshot.json \
  --pretty
```

`outcome=ready` means the three compact tables compile, their roles and profiles agree with the maintained six-profile contract, the graph and write ownership are safe, required independent review is present, and the U1 snapshot exposes the necessary Codex V2 request and readback fields.

The result includes one canonical contract digest and one approval binding over that digest plus the explicit plan revision. Any material graph, role, profile, model, effort, context, write, completion, check, fallback, external-action, or authority edit requires a new preview and approval.

This review does not launch an agent, write a run record, mutate Codex configuration, or prove runtime identity. Requested profile, model, effort, provider, permission, context isolation, path, and restoration remain provisional until the root validates Codex V2 `session_meta` plus `turn_context` readback.
