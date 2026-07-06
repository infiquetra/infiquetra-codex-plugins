# Codex Saga 0.64 Drift Classification

## Baselines

| Surface | Ref | Status |
|---|---|---|
| Codex repo `origin/main` | `966cdc9c4380b2da44805ada9470ac397fdb0093` | Discord identity assets 0.2.0 (`b0223a8`) and this plan/spec/workflow (`966cdc9`) landed; classification is written against this commit. |
| Claude repo commit-bounded window (KTD1) | `b30e0f2ba7cd0cfdeaf97c1d4510c9a0468e96da..9470edca65b1db06d2f7562eeb2d5a9e48c34dec` | Frozen per KTD1: this is the delta the plan is scoped to, regardless of further upstream movement. |
| Claude repo `origin/main` (observed 2026-07-06) | `43646b3e1b57979ce6e144c59bef2de9f88e09c8` | **Upstream has moved past `9470edc`.** Per KTD1 and the plan's stated failure path, the window is not extended in this unit. Implementation units U2-U9 must read only up to `9470edc`; any decision to chase `43646b3` requires a deliberate plan revision, not a silent pickup during this cycle. |

Delta size confirmed directly (`git diff --stat b30e0f2..9470edc -- plugins`): 31
commits, 141 files changed, 16,103 insertions(+), 359 deletions(-) — matches the
plan's stated shape.

## Per-Plugin Version Lineage (source side)

| Plugin | `b30e0f2` version | `9470edc` version | Files touched |
|---|---|---|---|
| `saga` | 0.41.0 | 0.64.0 | 60 |
| `team-execution` | 2.4.0 | 2.11.0 | 39 |
| `mission-control` | 2.3.1 | 2.5.1 | 6 |
| `unifi` | 1.1.0 | 1.2.0 | 6 |
| `deploy` | 0.1.2 | 0.1.4 | 3 |
| `redis-channel` | — | — | 3 (manifest/changelog/protocol doc only) |
| `fleet-core` (new) | n/a | 0.5.0 | 13 |
| `agy` (new) | n/a | 0.1.1 | 11 |

Codex-side pre-port baselines recorded in KTD1 differ from these source
versions — team-execution lineage 2.2.0, mission-control 2.1.0, unifi 1.0.0,
deploy 0.1.1 — because Codex tracks its own parity-labeled version history,
not a byte-mirror of Claude's.

## Drift Classification

| Claude surface | Codex treatment | Rationale |
|---|---|---|
| `plugins/fleet-core/**` (new plugin: tier palette/resolver, `tier_policy.json`, `models.json`, effort rider, retry/backoff, render helpers) | codex-adapt | Land as new Codex `fleet-core` scripts-only plugin (KTD2); rewrite the shim resolution ladder for Codex paths (env override -> repo walk-up -> `~/.codex` plugin layout -> fail-loud), no Claude `installed_plugins.json` rung. |
| `plugins/*/scripts/fleet_commons_shim.py` (saga, team-execution, mission-control, unifi-network, unifi-protect) | codex-adapt | Vendor Codex-modified shim copies (not upstream's byte-identical rung); guard with a drift test per plugin per KTD2. |
| `plugins/saga/scripts/board_progression.py`, `outcome_board_sync.py`, `reversibility_certificate.py` | codex-adapt, certificate-gated | Port the allow-listed autonomous board-write loop only; everything else stays propose-only behind operator confirmation (KTD5). |
| `plugins/saga/scripts/outcome_reconcile.py`, `outcome_edges.py` (new) | codex-adapt | Direct-port drift reconciliation and from-objective DAG seeding; reconciliation stays read-only/propose-repair. |
| `plugins/saga/scripts/outcome_gate_transport.py` (#379 remote gate over redis-channel) | reject / defer | Out of scope this cycle per operator decision 2026-07-06; redis-channel activation deferred. Record as deferred matrix row only. |
| `plugins/saga/scripts/ship_ceremony.py` (new), branch-refresh-on-save, `gate_divergence_reader.py` (new), `run_ledger.py` (new) | codex-adapt | Port ceremony state machine, branch refresh with default-branch gate-divergence checks, and append-only hash-chained run-fact ledger (telemetry-only, derive-on-read). |
| `plugins/saga/scripts/provenance_manifest.py`, `manifest_store.py`, `manifest_reader.py` (new) | codex-adapt | Port verified-vs-adjudicated manifest trio; wire into `completeness_gate.py` and verify-panel consensus recomputation (excludes non-reporting verifiers rather than fabricating N/A). |
| `plugins/saga/scripts/engine_registry.py`, `engine_resolver.py`, `engine_dispatch.py` (new), `references/engine-registry.yaml` | codex-adapt | Port capability-gated engine routing; explicit-engine-unavailable halts rather than silently substituting a backend. |
| `plugins/saga/scripts/execution_spec.py`, `team_emitter.py` | codex-adapt | Port tier/effort integration (`Tier.validate()` HALT semantics, effort cascade) replacing the Codex validator's hard-coded `TEAM_EXECUTION_MODEL_HINTS`; shared-file collision with U7/U8 — sequence serially per KTD6 mitigation. |
| `plugins/saga/agents/readonly-verifier.md` | reject active surface | Claude markdown agent; contract-text mining only into Codex-managed TOML if a corresponding team-execution role exists. |
| `plugins/saga/hooks/compact_spore_session_hook.py`, `precompact_spore_hook.py`, `team_spawn_residency_hook.py` | reject active surface | Claude hook lifecycle is not a Codex plugin surface. Deferred follow-up: `saga_spore.py` compaction/session behavior may inform a future Codex-native session-state primitive, not now. |
| `plugins/saga/scripts/saga_spore.py` | reject active surface (source only) | Backs the rejected hooks above; no Codex consumer this cycle. |
| `plugins/saga/references/sandbox-spawn-sites.md` | defer | Sandbox spawn-site enforcement mechanism deferred per R11. |
| `plugins/team-execution/skills/team-execution/scripts/artifact_pointer.py`, `references/{artifact-pointers.md, external-engine-workers.md, worker-manifest.md}` | codex-adapt | Port artifact-pointer indirection and resident-worker required-evidence-absence fallback (`missing-output`, `skipped-by-config`); negative-gate Workflow/TeamCreate paths per KTD4. |
| `plugins/team-execution/agents/*.toml` (25 files) | codex-adapt | Regenerate role-tier metadata through `sync_codex_agents.py` dry-run; roster stays palette-derived via fleet-core, not a second hand-maintained copy. |
| `plugins/mission-control/scripts/sdlc_manager.py` | codex-adapt (behavioral sync, KTD8) | Port `jeff-intent`->`operations` project rename, `issue create-prepared` recovery fix, issue-write verbs (close/reopen/comment/label-add/label-remove), contents-API PUT fix. Preserve intentional Codex divergences (allowlists, exact-plan confirmation) behind guard tests. |
| `plugins/mission-control/scripts/executor_profile_lint.py` (new) | codex-adapt | Port lint, validate against fleet-core tier palette. |
| `plugins/mission-control/tests/test_prompt_alignment.py` | codex-adapt (test-adaptation) | Adapt into `plugins/mission-control/tests/` layout per KTD7; do not copy Claude-specific prompt fixtures verbatim. |
| `plugins/unifi/skills/unifi-{network,protect}/scripts/unifi_{network,protect}_client.py` | codex-adapt | Adopt shared fleet-core retry/backoff (upstream 1.2.0) in place of any bespoke retry logic. |
| `plugins/deploy/agents/release-orchestrator.md`, `plugins/deploy/.claude-plugin/plugin.json` version bump | reject active surface / no bump | Claude agent markdown; deploy delta is agent-metadata-only, no Codex-visible behavior changed. Per KTD6, `deploy` does not bump this cycle. |
| `plugins/redis-channel/**` | out of scope | Not adopted this cycle (deferred plugin, matrix row only); no Codex `redis-channel` plugin is active. |
| `plugins/agy/**` (new plugin, agents/commands) | reject / out of scope | Operator decision 2026-07-06: Antigravity ecosystem lives in its own repo. Recorded as deferred matrix row only, no Codex surface. |
| Upstream repo-root `tests/**` | codex-adapt (structural) | Confirmed: upstream tests live at repo-root `tests/`, not per-plugin. Adapt into this repo's `plugins/<name>/tests/` layout in the same unit as the behavior (KTD7); missing tests block the unit. |

## Codex-Only Affordances (unchanged from 0.41 cycle)

Carried forward from `docs/portability/codex-saga-041-harness-delta.md`:
namespaced skills, `.codex/saga` state, managed team-execution agents with
serial fallback, lazy-loaded tools used conditionally, plugin validation as
release gate, `apply_patch` editing with local tests, installed cache copies
rejected as maintained source. No changes to this list identified in the
`b30e0f2..9470edc` window.

## Mutation Boundary (unchanged, KTD5)

The board-autonomy and ship-ceremony work in this window still computes
proposals, status cards, receipts, and planned actions only for allow-listed
board operations. It must not silently perform GitHub writes beyond that
allow-list, auto-merge, push, or destructive worktree cleanup. PR-open/merge
in the ship ceremony stays behind explicit operator confirmation.

## Deferred / Rejected Set (R11)

- `agy` plugin, in any form (operator decision 2026-07-06).
- PreCompact spore hook, compact-spore-session hook, team-spawn residency hook.
- Remote gate approval transport (#379) over redis-channel — deferred until a
  server-boundary proof exists; terminal-prompted approval remains the active
  path.
- Sandbox spawn-site enforcement mechanism.
- Workflow/fork/goal backends, `.workflow.js` wave-thunk retry wrapping,
  TeamCreate chaperone emission.
- `marketplace.json` generation and marketplace publishing.
- Claude agent markdown command files (contract-text mining only, not shipped).
- Chasing upstream past `9470edc` (see baseline table above — deliberately not
  extended this cycle).

## Failure Path Triggered

`git ls-remote`-equivalent check (`git log -1 --format=%H origin/main` against
the sibling Claude checkout) shows upstream at `43646b3`, past the plan's
`9470edc` boundary. Per KTD1 and the plan's stated failure path, this
classification stops at `9470edc` and does not extend the window. Any
implementation unit that wants the newer commits requires a deliberate plan
amendment, not an in-flight scope creep during U2-U9.
