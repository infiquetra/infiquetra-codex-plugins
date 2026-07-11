# Work Session: Codex Plugin Model And Workflow Modernization

Date: 2026-07-10. Branch: `work/verified-workflows-modernization`. Plan:
`docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`. Saga:
`task-port-recent-claude-plugin-updates`. Destination: PR.

## Execution

Saga records `orchestration_mode=inline`; the root thread owns lifecycle state, edits, integration,
Git, and gates. U1 used three bounded read-only grounding lanes for the port contract, runbook, and
runtime capability snapshot, followed by one fresh-context read-only reviewer. The root was the sole
writer. Pre/post worktree checks kept the unrelated `.serena/project.yml` change untouched.

The current parent ran with effective `danger-full-access`/`never` permissions rather than the
plan-preferred workspace-write posture. Child work was requested read-only and accepted only as
advisory input; repository diff checks confirmed no child mutation.

## U1 Complete: Freeze Source And Capability Truth

- Frozen Claude range:
  `9470edca65b1db06d2f7562eeb2d5a9e48c34dec..38742ece89880a6b140be237edad6d3f13c97b54`
  under the four exact pathspecs, with 156 rows and inventory SHA-256
  `a481fa9cee40ed9bd3a70800475d0511fbbe0d92926334e847e0dae4756a723d`.
- Frozen Codex historical plan/execution range:
  `788902513e48ea95fd0504ac3c850c8c02e5d920..3f639109b06ed2634d5333a58fb200b06e36dbbe`,
  with 35 preservation rows and inventory SHA-256
  `845d04095184fe2612a05dbf8c17d482a5cbdcb9d467d4b4eeb2b6ba446195a8`.
- Added the mandatory human runbook, closed staged JSON manifest, deterministic renderer, source
  verifier, validator integration, and generated classification. Classification now covers all 156
  source rows and all 35 Codex rows; U2-U9 each have at least one claimed source row.
- Captured Codex CLI `0.144.1`, explicit config/default provenance, four host slots versus six
  configured threads, current permissions, collaboration fields, hook facts, managed-agent counts,
  and eight allowlisted model rows. Live catalog drift replaced the review-time `gpt-5.2` assumption
  with `gpt-5.3-codex-spark`; the frozen Claude range did not change.
- Recorded the key execution limitation precisely: custom-agent TOMLs can configure model, effort,
  and sandbox, while the current direct spawn schema cannot select or read those values. Named-role
  execution remains planned-unproved until a later profile/hook/child receipt chain exists.
- Reframed Saga documentation around separate lifecycle, continuation, workflow, step-vehicle,
  identity, execution-class, and hook dimensions without prematurely changing the v1 runtime parser.
- Refreshed source authority and portability documentation. Team Execution remains the sole active
  workflow package; Verified Workflows remains an unpublished target until the U8 cutover gate.

## U1 Independent Review

The first U1 review found two P1 enforcement gaps and one P2 recapture gap:

- self-consistent manifest edits could shift frozen refs or drop Codex rows;
- failed, vacuous, misattributed, or unsafe evidence could satisfy later gates;
- recapture did not distinguish configured/default limits or require session-only readback.

All were fixed. The re-review reported no remaining P0-P3 findings: active refs and fixed digests are
bound and Codex Git inventory is recomputed; evidence is non-vacuous, successful, unit-bound,
kind-bound, path-safe, timestamped, and attached to approved history; capability checks include
config provenance, managed counts, and explicit allowlisted session facts.

## U2 Complete: Fleet Core Model, Effort, Cost, And Proof Policy

- Corrected the staged classification before implementation: U2 now claims 15 Fleet Core source
  and source-test rows rather than 26 mixed Fleet Core/Saga/release rows. Release metadata moved to
  U8, engine model releases to U6, effort escrow to U7, and bridge-emitter drift proof to U6. The
  Claude `/tier`, work-shape policy delta, committed tier pins, and singleton session override were
  rejected with Codex-specific rationales rather than emulated.
- Split the registry into temporary lineage compatibility plus authoritative Codex policy. Existing
  `MODELS`, `EFFORTS`, `codex_tier()`, and work-shape consumers remain green; new APIs expose
  `SCALAR_EFFORTS=low..max`, five execution classes, and a separate explicit root-only Ultra policy.
- Added one bounded argv-only catalog reader: refreshed then bundled once, 15-second timeout,
  combined 16 MiB ceiling, closed allowlisted projection, immutable snapshot, raw-input and
  normalized hashes, and no model-instruction leakage. The live reader reproduced the U1 catalog
  hash and resolved all five classes to the expected Sol/Terra/Luna profiles.
- Resolution preserves requested effort across ordered model candidates before any downward clamp.
  It retains distinct `scan-low` and `monitor-low` permission boundaries, fails on upward clamps or
  incompatible catalogs, and cannot return Ultra for a leaf.
- Ported ordinal cost weights through scalar `max`, bounded retry hints, bridge receipts, output
  attestation, advisory transcript/bundle audit, and contained atomic liveness state. External-engine
  proof remains separate from Verified Workflows role/profile proof.
- Kept all five consumer shim copies byte-identical and smoke-loaded the new palette and catalog
  through Saga, Team Execution, Mission Control, and both UniFi consumers.

## U2 Independent Review

The first pass found two P1 and nine distinct P2 issues across its review rounds. All were fixed:
same-run validated receipt joins; symlink/hardlink-safe owned lock files; explicit empty-effort
rejection; closed receipt, runner, and nested-attestation schemas; receipt/attestation byte binding;
positive-only weights; engine/run identity binding; finite-number handling without large-integer
overflow; and negative tests for each boundary. Two independent re-reviews reported no remaining
P0-P3 code findings.

The staged U2 evidence is `docs/validation/codex-plugin-modernization-u2.json`. All 15 claimed rows
are verified against it, the generated classification is current, and the U2 unit-stage contract
gate passes. The exact implementation commit is `c773186f53b20c2825f347c049c9014ae8736643`;
the focused suite, full suite, validator, and scoped Ruff checks were rerun after that commit before
the evidence record was rebound to its SHA.

## Checks Run

- `python3 scripts/port_contract.py verify-source --source-repo ../infiquetra-claude-plugins` —
  156 rows reproduced; frozen target reachable; newer upstream is drift only.
- `python3 scripts/port_contract.py validate --stage classification` — passed.
- `python3 scripts/port_contract.py refresh ... --check` — no refresh changes; classifications
  preserved.
- `python3 scripts/capture_codex_runtime_capabilities.py --check --session-facts-json ...` — live
  projection and explicit session facts matched; the same command without facts failed closed.
- `python3 scripts/validate_codex_plugins.py` — passed in current mode.
- `uv run ruff check ...` — passed for U1 Python and tests.
- `PYTHONPATH=. uv run pytest -q` — 1336 passed.
- `git diff --check` — passed.
- U2 focused Fleet Core suite — 95 passed.
- U2 full `PYTHONPATH=. uv run pytest -q` — 1407 passed.
- U2 scoped `uv run ruff check` over Fleet Core and port-contract surfaces — passed.
- U2 live catalog resolution — eight rows, committed normalized hash reproduced, five class
  selections matched policy.
- `python3 scripts/port_contract.py validate --stage unit --unit U2` — passed.
- Repository-wide `ruff check .` is not a U2 gate and remains red on four pre-existing unrelated
  findings in `tests/test_typed_exceptions.py`, `scripts/build_saga_docs_facts.py`, and
  `scripts/render_saga_docs_assets.py`; no unrelated files were changed.

## Next Step

Commit U2 and record its Saga checkpoint, then execute U9: establish the unpublished
`verified-workflows` package identity and compatibility vocabulary without activating cutover.
