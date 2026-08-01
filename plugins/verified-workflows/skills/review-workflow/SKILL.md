---
name: review-workflow
description: Compile and review an approved Workflow Contract for Codex V2 graph, profile, write, check, reviewer, fallback, and external-action consistency without launching work.
---

# Review Workflow Contract

Validate the operator-visible `## Workflow Contract` before execution. The main Codex session remains the sole orchestrator and owns dependency release, gate, and completion decisions. Every executable action, including integration and Git, belongs to an approved assignment.

Run the read-only compiler:

```bash
python3 plugins/verified-workflows/scripts/workflow_dispatch.py \
  --plan docs/plans/YYYY-MM-DD-topic-plan.md \
  --plan-revision <approved-git-revision> \
  --pretty
```

A successful result means the three compact tables compile, roles and profiles agree with the
maintained seven-profile contract, graph and write ownership are valid, and direct-sibling
independent review is present. Runtime capability proof belongs to the release validation snapshot,
not to every workflow preview.

The result includes one canonical contract digest and one approval binding over that digest plus
the explicit plan revision. Any material graph, role, profile, write, completion, check, fallback,
external-action, or authority edit requires a new preview and approval.

This review does not launch an agent, write a run record, mutate Codex configuration, or prove runtime identity. Requested profile, model, effort, provider, permission, context isolation, path, and restoration remain provisional until the root validates Codex V2 `session_meta` plus `turn_context` readback.
