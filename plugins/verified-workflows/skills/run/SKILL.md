---
name: run
description: Run an approved Infiquetra Workflow Contract as a root-owned Codex V2 DAG with exact named profiles, bounded context, typed results, independent review, deterministic checks, and one concise run record.
---

# Run Verified Workflow

Use this skill only after the operator approves the complete `## Workflow Contract` defined in [workflow-protocol.md](references/workflow-protocol.md). The main Codex session is the sole orchestrator and Git owner. Codex V2 owns the live hierarchy, liveness, messaging, waiting, interruption, and restoration.

## Approval Gate

Render all three contract tables, the explicit plan revision, canonical contract digest, and approval binding. Do not launch work before explicit approval. Any material assignment, check, fallback, write, context, external-action, or authority edit requires a complete new preview and approval.

Run the read-only feasibility gate:

```bash
python3 plugins/verified-workflows/scripts/workflow_feasibility.py \
  --plan <plan> \
  --plan-revision <approved-revision> \
  --snapshot docs/validation/codex-runtime-capability-snapshot.json
```

Compile the exact approved launch envelope with `workflow_dispatch.py` and validate its three approved binding values. The compiler emits launch specifications only; it does not schedule or persist live state.

## Root Execution Loop

For each dependency-ready assignment:

1. Resolve its exact launch specification. Root rows run inline. Delegated rows launch through Codex V2 `spawn_agent` with `agent_type=<profile>` and `fork_turns="none"` or the approved positive turn count. Do not substitute another profile, model, effort, or history mode.
2. Before a writable attempt, capture `workspace_audit.py` state. Keep the root and all other writers quiescent. Writable attempts are sequential unless V2 supplies per-agent mutation attribution.
3. Give the agent only its bounded context, declared parent/descendant paths, write ownership, completion rule, role lens, and typed result schema. Never send secrets or unrelated workspace content.
4. Before strict work counts, validate `session_meta` plus `turn_context` through `protocol_probe.py`: canonical agent path, profile or agent type, model, effort, provider, effective permission, sandbox, and V2 mode must match. Requested launch fields, TOML bytes, prompt claims, and hooks are not runtime proof.
5. Treat `send_message` as coordination only. Use `followup_task` on the same canonical path only to resume the same nonterminal attempt. A retry, remediation, or revalidation gets a fresh attempt ID and fresh canonical path; classify partial edits as cleanup or carry-forward first.
6. Wait for a terminal typed object and validate it with `result_contract.py`. A final chat message, mailbox notice, or terminal event without the typed result is not completion.
7. Capture the post-attempt workspace audit. Reject out-of-scope paths, pre-existing dirty overlap, worker Git commands, or any HEAD, branch, index, ref, config, or hook divergence. Root Git starts only after the attempt audit closes.
8. Atomically replace the one bounded run record under `~/.codex/verified-workflows/state/<repo>/workflow-runs/<run-id>.json`. Store the approved binding, validated runtime identity, typed outcome, checks, findings, remediation count, and root decision. Do not copy V2 events, messages, or raw model output. Use the git-ignored project fallback only after its focused write probe passes.
9. Release dependencies only from validated typed results, deterministic check outcomes, adopted root findings, and the assurance reducer. Messages and external output never release a gate.

## Independent Review

At least one authority-bearing reviewer starts under a separately launched fresh V2 review root with no implementation turns and then launches the exact approved review profile. The implementer and its descendants cannot review their own work. Additional reviewers are selected only for concrete architecture, security, privacy, API, infrastructure, or testing risk.

## External Actions

Saga owns external preview, approval fingerprint, provider execution, egress sanitization, status, and root adjudication. External results remain `non-gating`. Verified Workflows consumes only the validated advisory result or bounded root-imported patch described by the approved external-action row.

## Boundaries

- Root owns dependency release, integration, Git, remediation, PR, merge, installation, and completion.
- Ultra is root-only.
- Child permissions inherit the parent turn in Codex 0.145.0; named profiles cannot independently widen or narrow that effective permission.
- There is no active V1 catalog, hook-attestation, protected-evidence, snapshot-chain, intent-chain, or inline downgrade in normal V2 execution.
- Missing required V2 readback blocks the run and cutover.
