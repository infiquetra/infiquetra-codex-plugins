# Retro - task-codex-external-advisory-execution-contract - 2026-07-12

**Scope.** Thread-scoped (`task-codex-external-advisory-execution-contract`).

**Evidence freshness.** Verified against PR #28: the protected feature tree and merged
`origin/main` tree both resolve to `22dc915a9f1ecee82fa689bb8fcffbbb09e28bca`.

## What shipped

- PR [#28](https://github.com/infiquetra/infiquetra-codex-plugins/pull/28) merged the Codex-owned
  external advisory runtime, action store, provider adapters, lifecycle integrations, attended release
  proof, and rollback/cutover contract at merge commit `89ad9d2db6334b2f3df679c59e4710234de1fd91`.
- The final authoritative workflow run passed architecture, security, adversarial, and testing lenses
  with no findings; the post-merge QA gate scored every in-scope class at 100.
- Exact evidence verification exposed a transient `.lock` idempotency defect. Commit `8d225826` fixed
  the verifier and added a regression test before the merge.

## Findings

- **Backend selection was mistaken for informed workflow approval.** The plan named Verified
  Workflows, but the operator was not shown the concrete task graph, dependencies, roles, model and
  effort choices, or per-work-unit upgrade and downgrade recommendations before execution. The run
  began root-inline and the authoritative workflow arrived late. Evidence:
  [work session](../work-sessions/2026-07-11-external-advisory-execution.md) and the Saga trajectory from
  phase 3 directly to phase 8. Promotion: LEARNINGS `#workflow-approval-needs-concrete-preview` and
  QUEUED `#verified-workflow-preview-and-agent-runtime-contract`.
- **The desired approval surface is conversational, not a text editor.** The AI should render the
  complete proposed workflow; the operator asks for changes; the AI renders the complete revised
  workflow again; only explicit approval starts execution. Evidence: operator interview in this retro.
  Promotion: QUEUED `#verified-workflow-preview-and-agent-runtime-contract`.
- **Approved runtime settings are a hard contract.** V2 agents must expose direct thread switching,
  host-issued runtime receipts, and retained named agents. If the approved role, model, effort, or
  permissions cannot be honored, execution must stop and re-preview rather than silently downgrade or
  fall back inline. Evidence: operator interview plus the V2 diagnostic child receipts recorded in the
  [work session](../work-sessions/2026-07-11-external-advisory-execution.md). Promotion: QUEUED
  `#verified-workflow-preview-and-agent-runtime-contract`.
- **The verification mechanisms earned their cost.** Independent lenses, deterministic validator
  evidence, retained real-provider proof, exact evidence tagging, and the final severity gate should
  remain. They caught the `.lock` mutation and supported an evidence-backed ship verdict despite
  orchestration friction. Evidence: [QA report](../qa/qa-task-codex-external-advisory-execution-contract-2026-07-12.md)
  and commit `8d225826`. Promotion: none.
- **Workspace purity needs an explicit preflight.** A user-owned tracked `.serena/project.yml` change
  prevented authoritative no-write evidence in the active checkout, so the final barrier and QA used
  disposable clean clones. Evidence: [work session](../work-sessions/2026-07-11-external-advisory-execution.md).
  Promotion: none; the existing protected-subject and workspace-snapshot contract already addresses
  this correctly.

## Diff vs last retro

- Prior retro: none; this is the repository's first thread retro.
- New compounding signal: the earlier Workflow Contract Studio idea is now backed by a completed run
  and an operator-defined interaction contract, rather than ideation alone.
- New hotspot: orchestration and approval semantics caused more reruns than provider adaptation.
- Provenance manifests: no data yet; no rate was inferred.
- Reconciliation recipe proposal: none; the run ledger contains no reconciliation facts.

## Surfaced follow-ups

- -> QUEUED: implement the complete Verified Workflow preview, approval, runtime-fidelity, switching,
  receipt, and named-agent retention contract.
- -> `$saga:brainstorm`: deepen the existing Workflow Contract Studio idea before planning the
  multi-surface implementation.

## Proposed edits (Tier-2, awaiting operator)

- `plugins/verified-workflows/skills/run/SKILL.md` - refine the lifecycle skill so no work starts before
  a concrete conversational preview is explicitly approved, and runtime mismatch stops for re-preview
  instead of automatically falling back inline. Status: applied by operator approval.

## Refs

- Saga: `task-codex-external-advisory-execution-contract` (read-only).
- Plan: [external advisory execution contract](../plans/2026-07-11-codex-external-advisory-execution-contract-plan.md).
- PR: [#28](https://github.com/infiquetra/infiquetra-codex-plugins/pull/28).
- Journal: LEARNINGS `#workflow-approval-needs-concrete-preview`; QUEUED
  `#verified-workflow-preview-and-agent-runtime-contract`.
