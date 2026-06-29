# Codex Saga 0.41 Harness Delta

## Baselines

| Surface | Ref | Status |
|---|---|---|
| Codex repo `origin/main` | `fce697c24bd17a49f70897de53d614adc8478947` | Matches plan baseline after refresh on 2026-06-29. |
| Claude repo `origin/main` | `b30e0f2ba7cd0cfdeaf97c1d4510c9a0468e96da` | Matches plan baseline after refresh on 2026-06-29. |
| Historical Claude drift window | `80e8731..aad9d6a` | Outcome orchestration, hook harness, execution backend modeling, workflow authoring, and Saga docs expansion. |
| Newer Claude drift window | `aad9d6a..origin/main` | Completeness gate, shared status-card renderer, team emitter updates, and gate-status routing. |

The sibling Claude checkout had unrelated local changes on
`feat/279-reversibility-certificate`; this classification reads only
`origin/main` refs and does not edit that repo.

## Drift Classification

| Claude surface | Window | Codex treatment | Rationale |
|---|---|---|---|
| `plugins/saga/scripts/outcome*.py` | `80e8731..aad9d6a` | codex-adapt | Use as behavior source for outcome spec, store, projection, read/report, dispatch, liveness, merge/worktree modeling, and economics. Keep write paths gated and terminal output non-Mermaid by default. |
| `plugins/saga/references/outcome-spec.md` | `80e8731..aad9d6a` | codex-adapt | Rewrite as Codex reference material under the active Saga skill/reference surface. |
| `plugins/saga/commands/outcome.md` | `80e8731..aad9d6a` | reject active surface | Convert operator contract into `plugins/saga/skills/outcome/SKILL.md`; do not ship Claude command files. |
| `plugins/saga/scripts/execution_spec.py` | both windows | codex-adapt | Keep script-backed execution modeling, but gate unavailable Claude backends and preserve Codex backend truth: `inline`, `manual`, `team-execution`, conditional subagents. |
| `plugins/saga/scripts/team_emitter.py` | `aad9d6a..origin/main` | codex-adapt | Use for team-execution receipts only where Codex managed agents and serial fallback exist. |
| `plugins/saga/scripts/completeness_gate.py` | `aad9d6a..origin/main` | codex-adapt | Port as a local safety primitive with typed failures and a self-test path. |
| `plugins/saga/scripts/status_card.py` | `aad9d6a..origin/main` | codex-adapt | Port as shared terminal-safe renderer and route status-bearing Saga surfaces through derived-on-read evidence. |
| `plugins/saga/hooks/**` and hook manifest | `80e8731..origin/main` | reject active surface | Claude hook lifecycle is not a Codex plugin surface. Record lessons only; validation must keep hook files out of active Saga roots. |
| `plugins/saga/agents/mechanical-executor.md` | `80e8731..aad9d6a` | defer | Claude markdown agents are lineage only. Codex managed agent TOMLs live under team-execution when explicitly supported. |
| Workflow authoring and workflow emitter tests | `80e8731..origin/main` | defer or negative-gate | Workflow is inactive unless a Codex equivalent is designed and tested. Codex tests should assert unavailable/degraded behavior, not successful Workflow emission. |
| Fork, goal, and hook backends | both windows | reject active backend | No proven Codex runtime equivalent for this parity slice. Emit unavailable/degraded receipts instead of menus that imply support. |
| Auto-merge, push, GitHub write, worktree cleanup paths | both windows | preview/propose-only | Mutating operations require explicit approval or a tested Codex-safe policy. Default implementation must not silently mutate remote or sibling repo state. |
| Claude `.claude-plugin/plugin.json` version and keywords | both windows | test oracle only | Metadata can inform the final parity target but must not be copied. Codex manifest remains `.codex-plugin/plugin.json` and updates last. |
| Claude docs under `plugins/saga/docs` | `80e8731..origin/main` | codex-adapt | Rewrite into `docs/saga` and active skill references; do not wholesale copy Claude docs. |
| Promote workflow references | requirements scope | codex-adapt | Implement separately as `saga:promote` and `promote_scan`; keep journal scanning read-only and context-library writes proposal-only until explicit approval. |

## Codex-Only Affordances

| Codex affordance | Decision | How it is used |
|---|---|---|
| Namespaced skills | use | Add operator surfaces as `saga:outcome` and `saga:promote`; preserve existing Codex-only skills. |
| `.codex/saga` state | use | Outcome and work state must stay Codex-native and reconstructable from durable evidence. |
| Managed team-execution agents | use | Treat as an active delegated backend only through tested team-execution surfaces and fallback receipts. |
| Lazy-loaded tools and optional multi-agent support | use conditionally | Offer only when current runtime exposes callable tools and task boundaries are safe. |
| Plugin validation | use | Keep manifests, inventory, docs, and stale host-path checks as the release gate. |
| `apply_patch` editing and local tests | use | Prefer small, reviewable repo edits and targeted tests before broad validation. |
| Installed cache copies | reject | Cache directories are proof snapshots, not maintained source. |

## Active Backend Matrix

| Backend | Codex state | Operator behavior |
|---|---|---|
| `inline` | active | Default local execution and read/report operations. |
| `manual` | active | Produce receipts and operator instructions where automation is unsafe or unsupported. |
| `team-execution` | active with capability checks | Dispatch only through Codex-managed team-execution surfaces; degrade loudly if unavailable. |
| Codex subagents or multi-agent tools | conditional | Offer only when present in the active runtime and safe for the work unit. |
| Workflow | inactive | Emit unavailable/degraded receipt; do not emit active workflow success. |
| fork | inactive | Emit unavailable/degraded receipt. |
| goal | inactive | Emit unavailable/degraded receipt. |
| hooks | inactive | Keep out of active plugin surface; no Codex hook activation in this slice. |

## Mutation Boundary

Saga parity work may compute proposals, status cards, receipts, and planned
actions. It must not silently perform GitHub writes, context-library writes,
auto-merge, push, generated state publication, or destructive worktree cleanup.
Any later exception needs an explicit policy, tests for the policy, and operator
approval at the action boundary.
