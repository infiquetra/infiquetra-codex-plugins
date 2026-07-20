# Saga Portability Notes

## Source

- Source plugin: `saga`
- Base source commit: `16de95c82ccb2ed80d7f11018e1c2e8247a80a7f`
- Latest imported source commit: `abcc06b16763975d71e483a6dac768f4664d7b63`
- Saga 0.41 parity source commit: `b30e0f2ba7cd0cfdeaf97c1d4510c9a0468e96da`
- Saga 0.64 parity source commit: `9470edc` (window `b30e0f2..9470edc`, 2026-07-06 port cycle)
- Port status: Codex-native proof port

## Current Port Contract

The approved 2026-07-10 cycle freezes Claude
`9470edca65b1db06d2f7562eeb2d5a9e48c34dec..38742ece89880a6b140be237edad6d3f13c97b54`,
Codex historical plan base `788902513e48ea95fd0504ac3c850c8c02e5d920`, and approved execution base
`3f639109b06ed2634d5333a58fb200b06e36dbbe`. The closed per-path contract is
`../../docs/portability/ports/2026-07-10-saga-07517.json`; it preserves current `0.65.0` Codex
behavior while targeting source-lineage version `0.75.17`. U1 does not claim that later import,
workflow, hook, or release units have landed.

Saga remains the maintained Codex authority for lifecycle, continuation, outcome state, routing,
and handoffs. Historical classifications are evidence, not current capability authority.

## 0.64 Parity Additions (Version Is A Label, Not Full Upstream Parity)

The 0.64.0 version tracks upstream lineage numbering (KTD6, same precedent as 0.41); this file
records what actually ported. Landed this cycle: the certificate-gated board-write loop
(reversibility certificate, outcome board-sync, board progression), outcome reconciliation and
direct-sub-issue DAG seeding (now `--from-parent-issue`; legacy `--from-objective` is a hidden alias),
ship ceremony with branch-refresh-on-save and gate-divergence
instrumentation, an append-only run-fact ledger, the provenance manifest stack (verified vs.
adjudicated) with verify-panel dimension-exclusion consensus, and capability-gated engine
routing. Not ported this cycle: PreCompact spore/residency hooks, remote gate approval
transport (deferred to redis-channel), `agy`, marketplace generation, Workflow wave-thunk
retry wrapping.

## Codex Port Shape

This port keeps source skill names behind the `saga` plugin namespace. It does not keep active command, agent, hook, or source manifest directories. Runtime state moves to `.codex/saga/`, protected by repo `.gitignore`.

Persistent issue, deploy, team-execution, and context-library work stays owned by receiving plugins:

- `mission-control` owns issue artifacts, boards, comments, labels, milestones, and project state.
- `deploy` owns tag promotion, rollback, hotfix, deployment status, and deployment mutation.
- `team-execution` owns reviewer consensus, selected validators, subagent delegation, serial fallback, and evidence gates.
- `saga` owns lifecycle routing, local state, outcome receipts, status cards, and promotion proposals.

## Backend Contract

Codex Saga exposes only:

- `inline`
- `manual`
- `team-execution`

Source Workflow, fork, goal, and hook backends are lineage only and not executable in the Codex plugin without a separate capability proof and negative fallback tests.

## Outcome And Promote

Saga 0.41 adds Codex-native `saga:outcome` and `saga:promote` surfaces. Outcome state stays in `docs/outcomes/` and `.codex/saga/`. Promotion scans source journals read-only and prepares context-library journal proposals behind explicit approval.

## Document Formatting Contract

Saga imports the source document-readability contract into `references/formatting-style.md`. It is active Codex skill guidance and test coverage, not a host-specific command or manifest surface.

## Handoff Contract

Saga emits structured handoff envelopes that name the receiving skill. It does not call private APIs in receiving plugins. Handoff payloads are untrusted context: receiving plugins must re-read and re-verify before mutation.

## 2026-07-19 lease-safe substrate port (#33)

- Port manifest: `docs/portability/ports/2026-07-19-lease-safe-substrate.json`; frozen source range
  `a6f3bcff..cf15a09f`; codex release saga 0.76.0 alongside fleet-core 0.9.0 (release unit U5).
- `dispatch_settlement.py` and the saga `lease_broker.py` adapter are verbatim ports;
  `run_ledger.py` is reconciled to the post-range contract; `outcome_dispatcher.py` carries the
  lease-preparation graft on the codex-native record-only `prepared` shape (`outcome.dispatch.v2`
  acknowledgement semantics preserved — a shared settlement can never manufacture a Codex launch).
  Coordinator-level lease enforcement activates with codex-parity (#34).
- Gates: `tests/{test_dispatch_settlement,test_saga_lease_broker,test_outcome_dispatcher,
  test_lease_settlement_conformance,test_lease_safe_substrate_port_contract}.py` plus
  `plugins/saga/tests/test_run_ledger.py`; ceremony + unit evidence under `docs/validation/`.

## 2026-07-19 outcome cross-runtime parity port (#34)

- Port manifest: `docs/portability/ports/2026-07-19-outcome-cross-runtime-parity.json`; frozen
  source `30bde209..97d2fb15` (the infiquetra-claude-plugins#604 squash); codex release saga
  0.77.0 (release unit U5); codex preservation drift empty by construction (plan re-grounded at
  execution base `3723a818`).
- `outcome_compat.py` is byte-faithful except `RUNTIME_LABEL = "codex"`; fixtures byte-verbatim;
  `outcome.py` grafts discover/handoff/attach and retires `outcome-bundle/1` (export aliases
  discover; import refuses with zero writes). `attach --advance` uses the native protected
  launched-acknowledgement dispatcher built WITHOUT lease authority — the #33 note that
  coordinator-level lease enforcement "activates with codex-parity (#34)" is superseded by the
  2026-07-19 operator decision: activation (plus the deferred `audit_store` ancestor hardening)
  belongs to the cross-runtime-acceptance leaf.
- Gates: `tests/test_outcome_cross_runtime.py` (adapted #604 contract suite),
  `tests/test_outcome_dispatch_migration.py` (rejection oracles replace import round-trips),
  `tests/test_outcome_command.py`, and the per-port
  `tests/test_outcome_cross_runtime_parity_port_contract.py` (classification, unit evidence,
  capability-snapshot honesty, KTD6 seam-dormancy pin).
