# Tier palette — adding a model or effort (Codex adapter)

The fleet's model/effort vocabulary is **single-source**: it lives in
[`scripts/fleet_commons/models.json`](../scripts/fleet_commons/models.json) and is derived into
the ordered `MODELS` / `EFFORTS` tuples by
[`tier_palette.py`](../scripts/fleet_commons/tier_palette.py) at import. Every other surface —
`execution_spec.py`, the `/plan` tier table, the team-execution worker table, the ladder ops —
reads from there. Grow the vocabulary **here**, never with a second bare literal elsewhere.

## Codex dual palette (KTD3)

Unlike the upstream Claude registry, this Codex copy keeps the Claude tier names
(`fable`/`opus`/`sonnet`/`haiku`) as the **lineage vocabulary** — so `tier_palette.py`,
`tier_policy.json`, and the upstream ladder ops stay byte-identical and diff cleanly against
upstream — while each `models.json` row also carries the **active Codex mapping** it dispatches:

| Lineage tier | `codex_model` | `codex_effort` |
|---|---|---|
| `fable` | `gpt-5.5` | `xhigh` |
| `opus` | `gpt-5.5` | `high` |
| `sonnet` | `gpt-5.4` | `medium` |
| `haiku` | `gpt-5.4-mini` | `low` |

`tier_palette.codex_model()` / `codex_effort()` / `codex_tier()` read these fields.
`TEAM_EXECUTION_MODEL_HINTS` in `scripts/validate_codex_plugins.py` is derived from these pairs,
not hand-maintained — a single registry drives both the lineage tier and the Codex model.

## The load-bearing rule (`{#tier-vocab-ordering}`)

Tuple **membership** and **ordering** are two contracts. `MODELS` is **strongest-first** (rank 0
strongest); `EFFORTS` is **weakest-first** (rung 0 weakest) — the two run in opposite directions.
Callers must use `model_rank()` / `effort_rank()` and the `escalate` / `downgrade` / `clamp` /
`stronger` ladder ops, and reason in **strength**, never hand-roll `.index(...)` arithmetic.

## Add a model

1. Add a row to `models.json` under `"models"` with an explicit integer `rank`, an
   `effort_ceiling` (the strongest effort the model actually runs), and its `codex_model` +
   `codex_effort` mapping. **Ranks must stay contiguous `0..n-1`** — inserting a new strongest
   model means renumbering, not squeezing in a duplicate or a gap. Import-time validation
   (`_derive_ordered`, `_derive_codex_mapping`) rejects a duplicate/gapped/non-int rank or a
   missing/out-of-vocabulary Codex mapping loudly.
2. Run the fleet-core tests: registry-order, ladder-monotonicity, effort-ceiling, and
   Codex-mapping coverage.

## Add an effort

Add a row under `"efforts"` with a contiguous integer `rung`, then extend
`effort_rider.EFFORT_RIDER` with a matching directive (an import-time assertion guards parity).
