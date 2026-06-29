---
date: 2026-06-29
topic: codex-saga-orchestration
origin: docs/brainstorms/2026-06-29-codex-saga-orchestration-requirements.md
status: plan-ready
---

# Codex-Native Saga 0.41 Parity Plan

## Goal

Bring the Codex Saga plugin from the current `0.22.1` surface toward Codex-native
parity with current Claude Saga `0.41.0`, without advertising full parity until
behavior, docs, metadata, validation, and tests agree.

This plan treats Claude Saga as source material, not an active surface to copy.
Codex keeps namespaced skills, bundled scripts, managed Codex agent TOMLs,
explicit capability gates, `.codex/saga` state, and repo-local validation.

## Key Decisions

- Preserve Codex-only Saga skills: `ceo-review`, `implementation-spec`, and
  `product-review`.
- Add `saga:outcome` and `saga:promote` only after their Codex skills, scripts,
  tests, and docs exist.
- Do not copy active Claude `commands`, `.claude-plugin`, `agents`, hooks, or
  host-specific workflow surfaces.
- Required first implementation artifact: a Codex-vs-Claude harness delta table
  mapping Claude primitives and Codex-only affordances to `use`, `defer`, or
  `reject` decisions.
- Active backend floor: `inline`, `manual`, and `team-execution`.
- Conditional backend: Codex subagents or multi-agent tooling only when present
  in the current runtime and safe for the task.
- Inactive unless proven: Workflow, fork, goal, and hooks.
- Mutating actions default to preview/propose-only: GitHub writes, commit, push,
  auto-merge, worktree cleanup, generated state publication, and
  context-library writes.
- Metadata and version bumps happen last.

## Implementation Slices

### 1. Source Truth And Harness Delta

- Refresh Codex and Claude refs. If either moved from Codex `fce697c` or Claude
  `b30e0f2`, update the classification before coding.
- Classify Claude drift windows `80e8731..aad9d6a` and
  `aad9d6a..origin/main`.
- Add the harness delta table to repo docs.
- Preserve baseline green checks.

### 2. Execution Substrate

- Adapt `execution_spec`, `team_emitter`, `override_rate_reader`, and
  execution/operator-choice references.
- Keep `.codex/saga` state and Codex backend truth.
- Add negative and capability-gate tests for inactive Claude backends.

### 3. Outcome Read/Report Core

- Add `saga:outcome` skill plus outcome spec, store, projection, report, and
  read operations.
- Implement terminal-safe start/load/status/report/project/graph behavior.
- Default graph output is ASCII, prose, or status-card, not Mermaid.

### 4. Outcome Dispatch/Reconcile

- Add dispatcher, orchestrator, liveness, merge/worktree modeling, graph edits,
  and economics rollup.
- Implement idempotent advance and visible halt/degrade receipts.
- Keep mutating operations preview/propose-only unless explicitly approved by a
  tested policy.

### 5. Safety And Operator UX

- Add completeness gate with typed failures and self-test.
- Add shared status-card renderer.
- Route outcome status through shared derived-on-read projection.
- Adapt other Saga surfaces only where Codex has real durable evidence.

### 6. Promote

- Add `saga:promote` and `promote_scan`.
- Keep promotion separate from outcome orchestration.
- Scan workspace journals read-only and write only proposed context-library
  journal diffs after explicit approval.

### 7. Docs, Metadata, Final Validation

- Update `docs/saga` in this repo layout, not by copying Claude docs wholesale.
- Update Saga manifest, README, marketplace inventory, validator constants,
  changelog, and portability/provenance together.
- Set Saga to the final parity version only after all skill, script, and test
  surfaces exist.
- Run final full validation.

## Test Plan

Baseline before changes:

```bash
python3 scripts/validate_codex_plugins.py
PYTHONPATH=. python3 -m pytest -q tests/test_validate_codex_plugins.py tests/test_saga_docs_package.py tests/test_team_execution_agents.py
```

Per-slice targeted tests:

- Execution substrate: execution spec, team emitter, operator-choice drift,
  workflow emission, override-rate.
- Outcome core: spec validation, serialization, store replay, projection,
  report, graph/status output.
- Dispatch/reconcile: idempotent advance, backend halt/degrade receipts,
  liveness, merge/worktree proposals, economics.
- Safety/UX: completeness missing/malformed output, self-test, status-card
  traceability and unknown/not-reached behavior.
- Promote: key generation, ledger parsing, self-feed exclusion, idempotency,
  write-surface guardrails.

Final validation:

```bash
python3 scripts/validate_codex_plugins.py
python3 scripts/build_saga_docs_facts.py --check
python3 scripts/render_saga_docs_assets.py --check
PYTHONPATH=. python3 -m pytest -q
```

## Approval Gates

- Do not start implementation until this persisted plan has passed
  `saga:doc-review`.
- Do not advertise `outcome` or `promote` in metadata until their skills,
  scripts, and tests exist.
- Do not merge any slice that breaks current plugin validation.
- Do not enable any Claude-only primitive without a Codex capability proof and
  negative fallback tests.
- Do not perform real GitHub, context-library, or worktree mutations without
  explicit approval or a tested Codex-safe policy.

## Assumptions

- Delivery shape is phased PRs, with an all-or-nothing final parity claim.
- Team-execution's managed Codex agent roster is already landed and reused.
- Codex subagent or multi-agent support is optional runtime capability, not a
  plugin dependency.
- `promote` is included because Option B selected full current Saga parity.
- No deploy, installed-cache replacement, or unrelated plugin activation is part
  of this plan.
