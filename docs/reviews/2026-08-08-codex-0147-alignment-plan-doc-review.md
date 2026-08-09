# Doc Review — Codex 0.147.0 Alignment Plan

**Target:** `docs/plans/2026-08-08-codex-0147-alignment-plan.md`
**Reviewed revision:** working tree, digest `8aae8afb4a82b097b090e89d872f0ca8a4ca0300d0693878fe1caf2f915453a3`
**Date:** 2026-08-08
**Reviewers:** Claude (host, owns the verdict) + Codex `gpt-5.6-sol` max (advisory second opinion)
**Blocked status:** not blocked — all findings applied; the plan was restructured rather than patched

## Verdict

The reviewed revision was **not implementation-ready**. Twenty-three findings across both passes, nine
of them blocking, and the corrections were structural rather than editorial — so the plan was rewritten
from 13 units to 14 with a corrected critical path, rather than amended in place.

Three defects were fatal to the original approach and each was independently verified against source
before adoption:

**The isolation procedure was factually wrong.** U13 claimed "an absolute `CODEX_HOME` or
`--target-dir`, with `--isolated-target`". `sync_codex_agents.py:155` requires `--isolated-target` to
accompany an explicit `--target-dir`; an absolute `CODEX_HOME` alone yields `kind="codex-home"` and
raises, and if `CODEX_HOME` names the same directory the resolver refuses to mark it isolated. The plan
also called `--recover` "the documented undo"; `recover_sync` repairs an incomplete transaction or
cleans a committed one — it does not undo a successful apply.

**The evidence mechanism did not exist.** KTD7 required proving collaboration-tool absence from the
model-visible tool plan, but `prove_verified_workflows_runtime.py:257` infers observed tool calls from
rollout rows and cannot read a tool specification. The plan asserted a proof no code could produce.

**A latent bug blocked the central projection.** `codex_model_catalog.py:26` accepts
`{None, "v1", "v2"}`. Codex serializes `MultiAgentVersion` with `rename_all = "snake_case"`
(`codex-rs/protocol/src/protocol.rs:3044-3051`), so `Disabled` is the wire value `"disabled"` — which
catalog normalization rejects. The override-filter projection must test exactly that value, so it was
unimplementable until the normalizer is fixed.

## Findings

| ID | Priority | Source | Location | Status |
|---|---|---|---|---|
| D1 | P1 | Codex | plan lifecycle | Fixed — U14 added; destination is `merge`, plan stopped at source-ready |
| D2 | P1 | Codex | U1 manifest shape | Fixed — contract extension for divergent topology precedes the manifest |
| D3 | P1 | Codex | U12/U13 ordering | Fixed — candidate packaging moved before acceptance |
| D4 | P1 | Codex | U3/U4 atomicity | Fixed — merged into one atomic U2 with every consumer named |
| D5 | P1 | Codex | KTD5 pair-wide flag | Fixed — per-profile receipt artifact replaces the boolean |
| D6 | P1 | Codex | target vs observed version | Fixed — KTD2 separates them; matrix not relabelled |
| D7 | P1 | Codex | U13 isolation/rollback | Fixed — exact invocation and real rollback stated |
| D8 | P1 | Codex | U13 baseline control | Fixed — seeded upgrade path, neutral cwd, workspace-shadow guard |
| D9 | P1 | Codex | KTD7 evidence mechanism | Fixed — U5 harness unit names and builds the tool-plan route |
| D10 | P1 | Claude | two policy surfaces | Fixed — KTD4 collapses to one source (superseded my own first fix) |
| D11 | P1 | Claude | U13 dependencies | Fixed — U8, U10 added |
| D12 | P1 | Claude | R11 mis-mapped | Fixed — moved to U7 alongside R12 |
| D13 | P2 | Codex | Luna oracle undefined | Fixed — oracle fixed before the run, per-profile table |
| D14 | P2 | Codex | U7/U8 partial matrices | Fixed — stable case IDs, one test per row, negative controls |
| D15 | P2 | Codex | U10 tests wrong target | Fixed — dedicated discovery/routing module |
| D16 | P2 | Codex | U11 historical ambiguity | Fixed — `matrix.md:45` is inside a dated note; preserved |
| D17 | P2 | Codex | R25 version rule deferred | Fixed — pinned 0.14→0.15 and 3.0→3.1 with a stop gate |
| D18 | P2 | Codex | U5 test target misdescribed | Fixed — config fixture, not profile fixture |
| D19 | P2 | Codex | KTD8 independence | Fixed — harness frozen before receipts; Claude adjudicates |
| D20 | P2 | Codex | line references | Fixed — `config.toml:8`, `matrix.json:45`, builder `:71`/`:520`, predicate `:986` |
| D21 | P2 | Claude | U2 constant had no home | Fixed — `scripts/codex_target_version.py` with rationale |
| D22 | P2 | Claude | U3 schema had no generator | Fixed — `scripts/render_capability_schema.py` + drift test |
| D23 | P2 | Claude | U9 success branch untested | Fixed — scenarios cover the never-run branch |

## Claude adjudication of advisory findings

Every Codex finding was verified against source or this repository before adoption. **All sixteen were
adopted; none were downgraded or dismissed.** That is a different outcome from the requirements review,
where one finding's file list did not survive checking.

Independently verified: `sync_codex_agents.py:155` isolation semantics and `:1533` recover scope; the
`"disabled"` serialization against `protocol.rs:3044-3051` versus `codex_model_catalog.py:26`;
`prove_verified_workflows_runtime.py:257` inferring calls rather than reading a specification; all seven
profiles embedding `catalog_sha256`; `.codex/config.toml:8` versus the `[features]` header at `:6`;
`codex-v2-orchestration-matrix.json:45` versus the object open at `:41`; builder Terra entries at
`:71-72`; `tesing-codex` running Full Access inside this repository; and `build_codex_v2_orchestration_matrix.py:509`
emitting an observed `0.145.0`.

**One Codex finding superseded a Claude fix made earlier in the same review.** Claude's D10 identified
the two policy surfaces and proposed a cross-assertion between them. Codex correctly showed the
cross-assertion cannot hold: the canary gate makes the rendered value differ from the class value in the
ungated state by design, so asserting equality fails in exactly the state the gate exists to express.
KTD4 now collapses the two sources to one instead.

## Applied fixes

The plan was restructured, not patched. Unit count 13 → 14, with a corrected critical path:

```
classification+contract → atomic contract migration → policy collapse → frozen harness
  → {Luna, permission, resource, discovery proofs} → promotion → corrections
  → candidate packaging → seeded-upgrade acceptance → integration and merge
```

Structural changes beyond the individual findings: the proof harness became its own unit built and
frozen before any receipt, so the engine producing evidence is not also changing the instrument; policy
collapse (U4) lands before any model change with a byte-identical assertion, proving the collapse
changed nothing; and packaging precedes acceptance so the bytes accepted are the bytes shipped.

Verified after rewrite: dependency graph acyclic, all of R1–R26 covered, plan section markers intact.

## Residual risk

The live proofs remain unrun; every claim about 0.147.0 runtime behavior is source-derived. That is the
intended state for a plan, and U5–U8, U10, and U13 exist to convert it into evidence.

U2's atomicity is a real cost: it touches the catalog, renderer, capture script, validator, schema,
committed snapshot, and all seven profiles in one change, because the normalized digest cascades. The
plan accepts this because splitting it produces a repository that does not validate at the split point.

Neither reviewer executed a test suite or modified repository source outside the plan document.
