# Fleet effort convention (Codex adapter)

The single reference for how `effort` is authored, validated, resolved, and honored across the
Infiquetra Codex plugin fleet. Any plugin's agent metadata or the team-execution worker table
may declare an `effort:` value — this one place explains what happens with it. Do not re-declare
the convention per-plugin; link here instead.

## Vocabulary

The canonical vocabulary is
`fleet_commons.tier_palette.EFFORTS = ("low", "medium", "high", "xhigh")`. Never hand-copy the
tuple — resolve it via `fleet_commons_shim.load("tier_palette")`.

## Resolution: three-layer cascade

Most-specific wins, in order:

1. Plan-authored per-unit tier (from `/plan`'s per-unit tier authoring).
2. Team-level default (an optional team-wide effort override; absent today).
3. Per-teammate default (agent-metadata `effort:`).

The cascade wraps `fleet_commons.tier_resolver.resolve(role_kind, work_shape, envelope_ceiling,
operator_override)` — it is not a fourth standalone resolver. A plan-unit tier maps onto
`operator_override={"effort": …}` when present. Chaperone workers (intent `offload` /
`second-opinion`) are excluded from the cascade — their effort is intent-driven
(`sonnet/medium` for offload, `opus/high` for second-opinion), never resolved or overridden.

## Honoring: one seam, three spawn kinds

`fleet_commons.effort_rider.inject_effort(prompt, effort, spawn_kind)` is the single seam that
decides *how* a resolved effort is honored:

| `spawn_kind` | Mechanism | Real knob? |
|---|---|---|
| `workflow` | Pass-through — effort already rides in `agent(prompt, {effort})` | Yes |
| `external-engine` | Pass-through — effort already passed `effort=resolution.effort` | Yes |
| `agent` | `EFFORT_RIDER[effort]` directive prepended to the prompt (native Agent-tool teammate) | No — labeled proxy |

The `agent` branch exists because the native Agent-tool teammate path has no harness-level
reasoning-effort knob; the `EFFORT_RIDER` prompt-preamble is a labeled proxy. Routing all three
kinds through one seam means the day the harness ships a native subagent-effort parameter, only
the `agent` branch changes — nothing upstream (authoring, lint, cascade, reconcile) moves.

## Post-run reconciliation

`effort_rider.reconcile_effort(...)` compares the cascade-resolved effort against what the worker
manifest recorded — honestly per path: real-knob paths compare the recorded effort value; the
`agent` path can only confirm the rider text reached the constructed prompt, so its drift line
names the compared quantity as `rider-text`, never "reasoning spend".
