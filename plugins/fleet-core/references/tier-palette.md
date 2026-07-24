# Codex execution classes and model catalog

[`models.json`](../scripts/fleet_commons/models.json) is Fleet Core's single static policy
registry. [`codex_model_catalog.py`](../scripts/fleet_commons/codex_model_catalog.py) supplies
immutable runtime capability truth. [`tier_resolver.py`](../scripts/fleet_commons/tier_resolver.py)
joins the two; neither roles nor machine defaults choose an active leaf model.

```text
models.json                         codex debug models
  static class policy                  runtime capability
          |                                    |
          +-------------+----------------------+
                        |
                immutable CatalogSnapshot
                        |
             resolve_execution_class()
                        |
       expected model + effort + boundary + provenance
                        |
          managed profile and U4 execution receipt
```

The resolver output is expected configuration. It becomes execution proof only after the exact
managed-profile digest and hook-observed active model are joined by Verified Workflows. Current
hooks do not observe reasoning effort.

## Leaf execution classes

<!-- BEGIN GENERATED EXECUTION CLASS TABLE (rendered from models.json via render_tier_table.py; do not hand-edit) -->
| Execution class | Purpose | Boundary | Preferred | Ordered fallback |
|---|---|---|---|---|
| `review-max` | Explicit escalation for unusually ambiguous or high-risk review. | workspace=read-only; external=none | `gpt-5.6-sol` / `max` | `gpt-5.6-terra` / `max` -> `gpt-5.5` / `strongest supported scalar` |
| `review-high` | Architecture, security, adversarial, API, privacy, and quality review. | workspace=read-only; external=none | `gpt-5.6-sol` / `high` | `gpt-5.6-terra` / `high` -> `gpt-5.5` / `high` |
| `test-medium` | General workers, testers, and interpretation of ambiguous validator output. | workspace=declared-write; external=none | `gpt-5.6-terra` / `medium` | `gpt-5.6-sol` / `medium` -> `gpt-5.5` / `medium` |
| `scan-low` | Bounded extraction and scanner-result reduction. | workspace=read-only; external=none | `gpt-5.6-terra` / `low` | `gpt-5.6-sol` / `low` |
| `monitor-low` | Network-aware CI, deploy, and runtime observation. | workspace=read-only; external=allowlisted-read | `gpt-5.6-terra` / `low` | `gpt-5.6-sol` / `low` |
<!-- END GENERATED EXECUTION CLASS TABLE -->

Resolution first searches the ordered candidates for the requested effort. Only when no candidate
can preserve it may resolution clamp downward to the strongest supported scalar effort. Upward
clamping, a hidden or API-ineligible model, an absent compatible fallback, and Ultra on a leaf all
fail loud.

`scan-low` and `monitor-low` intentionally share model policy but remain distinct because their
external-read boundaries differ. Codex 0.145.0 exposes Luna only through MultiAgent V1, so the
V2-only cutover selects Terra/low for both profiles.

## Effort and Ultra

`SCALAR_EFFORTS` is ordered `low`, `medium`, `high`, `xhigh`, `max`. It drives leaf profiles,
riders, resolution, and cost policy. Ultra is separate root orchestration behavior because it adds
automatic delegation. `resolve_root_orchestration(..., effort="ultra")` requires both explicit
selection and independently executable fan-out; no leaf API can return it.

Prompt riders are advisory only. Presence of rider text never proves that Codex used the requested
effort.

## Temporary lineage compatibility

`MODELS`, `EFFORTS`, `codex_tier()`, and the legacy work-shape resolver remain available until the
U3/U6 consumers migrate. Their `fable`/`opus`/`sonnet`/`haiku` values describe source lineage and
must not be used for new Codex profile selection. The active policy is `EXECUTION_CLASSES` plus the
runtime catalog snapshot.

## Changing policy

Edit only `models.json`. Keep ranks contiguous, class keys closed, model candidates unique, and
Ultra out of `scalar_efforts` and every leaf row. Then run the catalog, resolver, renderer, effort,
and cost tests. Role defaults and allowed class transitions belong in Verified Workflows; adding
them to Fleet Core is a schema error.
