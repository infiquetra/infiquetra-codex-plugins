# Work Session — Codex 0.147.0 Alignment

**Plan:** `docs/plans/2026-08-08-codex-0147-alignment-plan.md`
**Saga:** `task-codex-0147-alignment`
**Branch:** `feat/codex-0147-alignment`
**Base:** `origin/main` at `cd51a29`
**Worktree:** `infiquetra-codex-plugins-worktrees/codex-0147-alignment`
**Started:** 2026-08-09

## Phase 1 — setup, rebase reconciliation, task list

### Why this runs in a worktree

The plan's own risk section called for it, and entry checks confirmed the need. The operator's main
checkout was 6 commits behind its remote, with 14 uncommitted paths belonging to concurrent sessions.
Pull requests 74, 75, and 76 had merged upstream and touched this plan's exact target set:
`render_codex_agents.py`, all seven agent profiles, `role-registry.yaml`, `validate_codex_plugins.py`,
and eight test files.

The worktree is based on `origin/main`, so the main checkout and its uncommitted work are untouched.

### Plan premises re-verified against the new base

The round's thesis survives the rebase intact. Verified directly against `origin/main`:

| Premise | Status |
|---|---|
| `MULTI_AGENT_VERSIONS` rejects the wire value `"disabled"` | Survives, unchanged at `codex_model_catalog.py:26` |
| `selectable` never consults `multi_agent_version` | Survives, unchanged at `codex_model_catalog.py:55` |
| Four hard version pins, already drifted apart | Survive, all four at their cited lines |
| The Luna promotion gate is unreachable | Survives, relocated |
| A digest change cascades across all seven profiles | Confirmed — upstream cascaded `registry_sha256` across all seven |

### Corrections to the plan's own accounting

Recorded here rather than edited into the plan, which stays the decision artifact.

1. **The Luna promotion gate moved.** The plan cites `render_codex_agents.py:984-990` with its
   predicate at `:986`. On this base the gate is at `:976-982` and the predicate at `:978`. The file
   is net 10 lines shorter after the upstream refactor. Affects the U9 description.
2. **The single-sourced version constant has more call sites than budgeted.**
   `scripts/prove_verified_workflows_runtime.py` carries the literal `0.146.0` at `:139`, `:202`, and
   `:614`. The plan's U2 names `:139` and treats `:202` and `:614` as message relabels. All three are
   in scope; only `:139` is a gate.
3. **The tracked-plugin count may no longer be ten.** U10 asserts ten tracked manifests. Pull request
   75 added `plugins/hermes-profile-evolution`. Re-count before asserting.
4. **A vocabulary collision now exists.** Pull request 74 added a logical role named
   `harness-integration-engineer`. The plan's U5 builds a *proof harness* — an unrelated concept.
   Rename one before fourteen units make the ambiguity permanent.

All other line references in the plan were spot-checked and no further drift was confirmed. Several
were checked with loose patterns that matched an earlier occurrence, so the U-owner re-verifies each
reference in their own unit before editing.

### The operator's uncommitted work is superseded

Stated for the reconciliation owed at U14, not acted on. The main checkout holds an uncommitted
`validate_hermes_profile_evolution_port(root, plugin_root, errors)`. `origin/main` already carries
`validate_hermes_profile_evolution(root, errors)` from pull request 75 — the same feature, a different
signature. The local `plugins/hermes-profile-evolution/` has five files that differ from the merged
version and is missing ten the merged version has, including the conformance specs and `hooks.json`.

Comparison was by function name and file inventory, not line by line, so this does not prove nothing
is worth salvaging. Nothing was touched.

### Decisions taken this phase

- **Worktree over stash or reconcile-first**, so a concurrent session keeps its files.
- **One saga thread, not two.** The worktree's `.claude` is a symlink to the main checkout's, so
  `task-codex-0147-alignment` continues rather than forking. Both paths were added to
  `.git/info/exclude` (shared across worktrees, alongside the pre-existing `.worktrees/` entry) so the
  symlink can never be staged.
- **Plan body left unedited** per the execution contract; rebase corrections live in this document.
- **Backend: `inline`,** the operator's pick, against a computed recommendation of the paired team
  execution backend. Both recorded on the saga for override telemetry. Paired with Codex per the
  plan's KTD8.
- **A fresh Codex pane rather than the named pairing session.** `update-codex-plugins` (pane `w25:p7`)
  was at 91% of its 258K window and its working directory is the main checkout. The plan anticipated
  this and authorized a fresh session. The new pane `codex-0147` (`w25:pB`) runs `gpt-5.6-sol` in the
  worktree on the work branch. The named session stays live and untouched.

### Task list

Fourteen units with the plan's dependency graph wired. Only U1 is unblocked.

`U2←U1 · U3←U1 · U4←U2 · U5←U2 · U6←U5 · U7←U5 · U8←U7 · U9←U4,U6 · U10←U5 · U11←U9 · U12←U3,U10,U11 · U13←U12 · U14←U13`

### Checks run

- Divergence, commit list, and per-file comparison against `origin/main`.
- All four U1 upstream pins resolved in the surviving clone at `/tmp/codex-0147-analysis.oXEtw0`:
  `95637f70`, `7558bede`, `79b4f03d`, `be6e8eac`.
- No test suite run yet. No repository source modified yet.

### Files modified

`docs/engineering-journal/DECISIONS.md` — the two 2026-08-08 entries grafted onto the upstream version,
which had itself gained two entries. Reverse-chronological order preserved.

## Phase 2 — U1 complete (commit `b01d8f4`)

Codex implemented, Claude reviewed and committed. One blocking finding was returned and fixed before
the commit landed.

### What shipped

A closed `source.topology` object on the port manifest: both tags with their peeled commits, the common
base, and each left-only commit with a disposition. Validation is real rather than shape-only —
`verify-source` peels both tags against the upstream repository, recomputes the merge base, recomputes
the left-only range, and set-compares it against the recorded dispositions. A disposition can neither
be invented for a commit outside the range nor omitted for one inside it.

### The blocking finding

Codex introduced an exemption: a manifest carrying `source.topology` that is not yet in
`CURRENT_PORT_IDS` skips four capability-snapshot reference bindings. The mechanism is sound and solves
a real ordering problem — the committed snapshot still records the previous cycle's references and U2
re-baselines it. But nothing tested it, in either direction.

That was blocked and returned, because it is this round's own defect in a new place: an escape hatch
whose expiry nothing enforces is the same shape as a runtime observation frozen as a permanent
property. Codex's own comment stated the contract; a comment is not a gate.

Three tests now pin it: the staged case validates clean against deliberately mismatched references, the
promoted case asserts **set equality on all four** bindings via a monkeypatched `CURRENT_PORT_IDS`, and
a no-topology control proves the exemption is keyed on topology presence rather than staged-ness. The
control and the staged test are mutually validating — a vacuous fixture would fail the control.

### Codex's three flags, adjudicated

| Flag | Verdict |
|---|---|
| The legacy-token inventory was missing from U1's file list | **Upheld** — plan defect, not implementation |
| `UNIT_IDS` stops at `U10` while the plan runs to `U14` | **Upheld** — bites at `port_contract.py:1121` and `:1431`; routed to U2 |
| Source rows carry `unit: None` | **Dismissed** — both shipped 0146 manifests do the same |

### Infrastructure findings

1. **Codex cannot commit from a linked worktree.** Staging fails with `Unable to create
   '.../.git/worktrees/<name>/index.lock': Operation not permitted`. In a linked worktree `.git` is a
   file pointing at the parent repository, so the index, objects, and refs all sit outside the sandbox
   root. This is not a general Codex limitation. Claude owns every commit this round; each Codex unit
   lands in two steps.
2. **The `historical-evidence` classifier sweeps live documents into a frozen set.**
   `expected_legacy_workflow_classification` classifies any `docs/work-sessions/` or
   `docs/engineering-journal/` file containing a legacy workflow token as `historical-evidence`, whose
   digests are pinned by `LEGACY_WORKFLOW_HISTORICAL_INVENTORY_SHA256`. This document would have been
   conscripted into that frozen set over one incidental mention, re-drifting a pinned audit digest on
   every edit across a fourteen-unit round. One word was reworded to keep it out.

   The unresolved half is real and is **not** fixed here: `DECISIONS.md` is frozen as
   `historical-evidence`, yet the standing engineering-journal rule requires appending to it in the same
   commit as any pattern decision. The guard and the rule are in direct conflict. `QUEUED.md` already
   has a `mutable-engineering-journal` carve-out, so the precedent for a mutable journal file exists.
   Extending it to `DECISIONS.md` would weaken an audit guard and is the operator's call, not a
   unilateral one. The pin was bumped deliberately instead, with the drift proven minimal: exactly one
   entry digest plus the recomputed roll-up.

### Checks run

- `pytest tests/test_port_contract.py tests/test_codex_0147_alignment_port_contract.py` — 41 passed.
- `pytest tests/test_validate_codex_plugins.py` — 51 passed.
- `python3 scripts/validate_codex_plugins.py` — passed.
- Baseline established: pristine `origin/main` passes the validator, and fails
  `plugins/discord-identity-assets/` collection identically with `ModuleNotFoundError: No module named
  'PIL'`. That is a pre-existing missing optional dependency, out of scope, and excluded from the
  round's green bar.

## Phase 2 — U2 in progress (Claude owns; Codex reviews)

### The round's thesis is now confirmed from the live runtime, not from source

Codex CLI 0.147.0 is installed locally, so the capability snapshot was re-baselined from a real
capture rather than relabelled. Every claim below is a live observation.

**`gpt-5.6-luna` raw catalog facts are byte-identical between 0.146 and 0.147** — still
`multi_agent_version: "v1"`, `visibility: "list"`, `supported_in_api: true`. Luna did not change; the
gate did. That is the whole round in one line, and it is now evidence rather than inference.

### Two genuine 0.147.0 catalog changes nobody had flagged

Neither appears in the brainstorm, the requirements, or the plan. Both were found by diffing the live
capture against the committed snapshot.

1. **`gpt-5.6-sol-wm` is new.** `multi_agent_version: "v2"`, but `visibility: "hide"` and
   `supported_in_api: false`, so `selectable` is false and no execution class can resolve to it. It
   enters the snapshot as a catalog row and changes the normalized digest; it does not change policy.
2. **`codex-auto-review.visibility` moved `list` → `hide`.** It was selectable in 0.146 and is not in
   0.147. `supported_in_api` stays true, so only visibility withdrew it. Nothing in this repository
   resolves to it today, but the change is real and is recorded rather than absorbed silently.

### Everything else in the runtime section is unchanged

Verified field by field against the live capture: `configured_max_threads` (6), its source and key,
`configured_v2_total_threads` (7), `configured_max_depth` (1), both depth/thread sources, and the
whole `multi_agent_v2_config` object. No drift. The 0.147 upgrade did not move the threading or depth
contract.

### What U2 has changed so far

- `MULTI_AGENT_VERSIONS` now accepts `"disabled"` in **both** independent normalizers —
  `codex_model_catalog.py` and `capture_codex_runtime_capabilities.py`. The plan named only the first.
  Codex serializes `MultiAgentVersion` with `rename_all = "snake_case"`, so `Disabled` arrives as
  `"disabled"` and both normalizers rejected the exact value the new projection must test.
- Two derived projections on `CatalogModel`, with versioned rule identifiers so a later upstream gate
  change lands as a new rule rather than a silent redefinition:
  `passes_multi_agent_v2_override_filter` (a property of the model) and `multi_agent_v2_collaboration`
  (carrying `as_root` and `as_child` explicitly, because the answer depends on session position).
- `tier_resolver._catalog_model` consults the override filter and deliberately not the collaboration
  projection — the single chokepoint both selection paths already used.
- `scripts/codex_target_version.py`: `CODEX_TARGET_VERSION`, import-free, an expectation and never an
  observation.
- `scripts/render_capability_schema.py` generates the r4 schema so its `const` cannot drift from that
  constant. The r3 revision stays on disk unmodified, so artifacts already validated against it keep
  validating.
- `port_contract.py`: capability schema versions widened to `{1, 2, 3}`, and `UNIT_IDS` widened from
  `U1..U10` to `U1..U14` — the gap Codex found during U1 review, routed here as planned.

### A mistake worth recording

The first attempt added the two projection keys to the renderer's closed-key set as **required**,
which broke 135 tests: every hand-written catalog fixture lacks them, because they are derived. The
correct layer is to drop derived keys before the closed check and let `normalize_catalog` recompute
them. Forwarding a stored copy would let a stale projection outlive the rule that produced it.

### The snapshot re-baseline forces a port rotation the plan did not anticipate

Re-baselining `docs/validation/codex-runtime-capability-snapshot.json` breaks both shipped 0146 port
manifests, which pin it by digest under `authority.capability_snapshot`. That digest check is
**unconditional** — it is an authority-entry check, not gated on `CURRENT_PORT_IDS` — so a port cannot
be exempted from it by retiring.

This looked like a structural defect until the precedent settled it. Two facts, both verified:

1. **Purpose-scoped ports archive their own snapshot.** `mission-control-2100`, `mission-control-2101`,
   `lease-safe-substrate`, `outcome-cross-runtime-parity`, `codex-627-seam-refreeze`, and
   `lease-registry-forward-compat` each pin a distinctly named snapshot file. Only the Codex
   *alignment* lineage shares the live one.
2. **Retired alignment ports are already stale on `origin/main`, and that is accepted.** Validating
   the pristine base directly: `2026-07-10-saga-07517` carries 3 errors and
   `2026-07-24-codex-v2-orchestration` carries 1, while both 0146 ports — the two in
   `CURRENT_PORT_IDS` — carry none. The 0146 round did not repair its predecessors; commit `45890ae`
   touched no earlier manifest.

So the established convention is that each alignment round rotates `CURRENT_PORT_IDS` to its own port
and lets its predecessors go stale. This round follows it: promote `codex-0147-alignment-2026-08-08`,
retire the two 0146 identifiers.

Promotion also closes U1's exemption exactly as designed. The staged manifest was exempt from
capability-snapshot reference binding while the snapshot still described 0146; U2 re-pointed the
snapshot's `refs` at the manifest, so when the port becomes current the binding applies **and holds**.
The three tests Codex added in U1 review are what prove that transition rather than assuming it.

One consequence, recorded rather than hidden: `test_pre_extension_contracts_still_validate` asserted
the 0146 manifests validate cleanly. That claim was true of the *contract extension* — U1 broke
nothing — but is not true after the *snapshot re-baseline*. The test is being narrowed to the claim it
was actually written to make, not deleted.

### Codex found a real defect in the implementation and refused to hide it

The most valuable return of the round so far. Handed the failing tests to update, Codex instead
stopped with zero edits and reported that `capture_codex_runtime_capabilities.py` accepted
`"disabled"` but still **emitted** the old six-field catalog row — so the capture path could never
reproduce the committed r4 snapshot. Its digest was `98fa01ee…` against the committed `7a8eaa7f…`.

Its sharpest observation: *the existing capture test still expects six fields, so it passes while
masking this defect.* A green test standing guard over a broken contract.

The fix derives both projections **through** `CatalogModel.to_jsonable` using the `fleet_commons`
shim, mirroring `scripts/validate_codex_plugins.py:30`. Writing a second copy of the derivation rule
in the capture script would have been precisely the defect this round exists to remove. The capture
path now reproduces `7a8eaa7fc65492c2c0e0689304972eea17fec2ba4f39d06fa5d8a905f3e40868` exactly.

This is the second time in two units that cross-engine review caught something self-review did not.
KTD8's independence requirement is earning its cost.

### A false failure from the Codex sandbox, and its shared root cause

Codex reported `test_advance_persist_commits_the_spec_on_the_outcome_branch` failing with
`UnsafeAuthorityError` on reopening `registry.lock`. It does not reproduce: the test passes in
isolation in this worktree **and** on pristine `origin/main`, and it sits in `tests/`, which the
scoped run covers with zero failures. U2 modifies nothing under `plugins/saga`.

The cause is the same one that blocks Codex from committing: its sandbox root cannot reopen certain
files outside the working directory. Treat lock-file and git-metadata failures reported by a
worktree-hosted Codex as environmental until reproduced independently.

### U2 landed

Gates, all verified independently rather than taken on report:

- `pytest plugins/fleet-core/tests plugins/verified-workflows/tests tests/` — **1893 passed**.
- `scripts/validate_codex_plugins.py` — passed.
- `scripts/render_capability_schema.py --check` — current.
- `ruff check scripts/ plugins/fleet-core/scripts/ plugins/verified-workflows/scripts/` — passed.

Thirty files in one commit, which the plan intended: the normalized digest cascades through the
catalog, both normalizers, the renderer, the validator, the schema, the snapshot, the runtime proof,
and all seven profiles. Splitting it yields a repository that does not validate at the split point.

## Phase 3 — U3 complete (commit `7356ee5`)

The setting was absent by luck rather than by contract, and nothing asserted the profiles still
carried instructions of their own. `validate_developer_instruction_contract` now enforces both halves.

The design choice worth naming: the check binds the **whole surface set**, not one remembered file. A
`config.toml` that exists without being registered in `CODEX_CONFIG_SURFACES` fails. Guarding only
`.codex/config.toml` would have passed forever while a new plugin shipped an unchecked surface, which
is the failure mode actually worth catching. There is exactly one surface today.

Each branch was probed against a mutated copy before any test was written, and the tests include an
explicit clean-baseline assertion so a negative case cannot pass for the wrong reason. Six tests
added; suite at 1899.

## U4 is analysed but NOT started — one decision is owed first

Nothing has been modified for U4. The pre-collapse profile digests are recorded as the byte-identity
oracle KTD4 requires, so the collapse can be proven to change nothing:

```
review_max   3bb3abe289a7dbb8   review_high  86b2f2e0f6f1f347   work_high    8eb7257833aceb87
work_medium  a7cd86f520fcb554   test_medium  9b80ca6f220dc685   scan_low     c5aec84ee0e8b3b0
monitor_low  1ffcc126fef9a0f6
```

**The plan presupposed a mapping that does not exist.** U4 says to map each managed profile to its
Fleet execution class, but there are seven profiles and only five classes:

| Profile | Renderer literal | Fleet execution class |
| --- | --- | --- |
| `review_max` | `gpt-5.6-sol` / max | `review-max` (order 0) |
| `review_high` | `gpt-5.6-sol` / high | `review-high` (order 1) |
| `test_medium` | `gpt-5.6-terra` / medium | `test-medium` (order 2) |
| `scan_low` | `gpt-5.6-terra` / low | `scan-low` (order 3) |
| `monitor_low` | `gpt-5.6-terra` / low | `monitor-low` (order 4) |
| `work_high` | `gpt-5.6-sol` / high | **none** |
| `work_medium` | `gpt-5.6-terra` / medium | **none** |

Collapsing to one source therefore requires *adding* `work-high` and `work-medium` to
`execution_classes` in `plugins/fleet-core/scripts/fleet_commons/models.json`. That file describes
itself as "Canonical Fleet Core policy", and `execution_classes` is read by `tier_resolver.py` and
`tier_palette.py` — so this extends a shared vocabulary beyond Verified Workflows rather than
refactoring within it.

The open question is narrow but real: **`order` currently encodes 0–4 with no gaps and nothing pins
the set to five.** Appending `work-high` and `work-medium` as 5 and 6 would place an expensive
`gpt-5.6-sol` / high class *after* the cheap `monitor-low`, which contradicts the apparent
cost-ordering semantic. Renumbering to insert them in cost order changes existing class orders, whose
consumers were not audited. Which of those is correct depends on what `order` is actually for, and
that is a call about shared Fleet policy rather than about this round.

Everything else in U4 is settled and mechanical once that is decided: have the renderer consume class
policy instead of its `PROFILE_POLICY` literals, replace the hardcoded expectation in
`test_agent_tier_sync.py` with an assertion against the class policy, and prove all seven rendered
profiles are byte-identical to the digests above.

## Next step

Decide the `order` semantics for the two new execution classes, then execute U4. U5 through U14 remain
untouched.
