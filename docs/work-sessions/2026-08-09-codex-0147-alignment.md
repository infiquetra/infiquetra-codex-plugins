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

## Phase 4 — U4 complete

The operator answered the open question directly: extending Fleet Core is fine, and cost ordering of
`order` is not a concern. Both new classes were therefore appended at the next free ranks, 5 and 6, so
no existing class rank moved.

### The base moved again first

`origin/main` had advanced two commits (a fix binding the profile-evolution render receipts). Neither
touched anything U4 works on — the change is confined to a docs asset and its test — so the branch was
rebased onto it before any U4 edit. Five commits replayed cleanly.

### What `order` actually means

Audited before assuming. `order` has exactly two consumers: `_derive_ordered` in `tier_palette.py`,
which requires the values be contiguous `0..n-1` and rejects a duplicate or a gap, and one roster
assertion in `plugins/fleet-core/tests/test_tier_resolver.py`. Nothing reads it as a cost or
capability ranking. Appending is therefore correct and renumbering would have changed five existing
ranks to encode a meaning nothing consumes. The semantic is now written down in
`plugins/fleet-core/references/tier-palette.md` so the next reader does not have to re-derive it, and
the decision with its rejected alternative is in `docs/engineering-journal/DECISIONS.md`.

### The collapse

`render_codex_agents.py` no longer states a model or an effort anywhere. It keeps two plugin-local
facts — `PROFILE_EXECUTION_CLASSES`, mapping each profile to exactly one Fleet Core class, and
`PROFILE_DESCRIPTIONS`, the operator-facing text rendered into the profile — and reads the model and
effort from the class through `fleet_commons_shim.load("tier_palette")`.

The renderer asks the palette on every render rather than caching an answer of its own. What that
earns is precise and worth stating exactly, because the first draft of this note overstated it:
there is no second copy in the plugin, and no plugin edit is needed to adopt a Fleet Core policy
change. It is **not** live reload. `tier_palette` reads `models.json` once per process and freezes
the derived policies, so an edit takes effect on the next run. That freeze is correct rather than a
shortcoming — reloading between two profiles of one bundle would let a single render emit two
different policies.

Three failure modes are loud. A profile absent from the mapping fails the roster check in
`render_bundle`. A profile naming a class Fleet Core does not define fails in `profile_policy` with
the class name in the message. And a `ProfileResolution` whose model or effort departs from its class
fails at render unless it names a reason in `PROFILE_POLICY_DEVIATIONS`. None falls back.

### Byte identity holds

All seven rendered profiles are byte-identical to their pre-collapse digests, which are now pinned in
`plugins/verified-workflows/tests/test_agent_tier_sync.py` as `PRE_COLLAPSE_PROFILE_SHA256`:

```
review_max   3bb3abe289a7dbb8   review_high  86b2f2e0f6f1f347   work_high    8eb7257833aceb87
work_medium  a7cd86f520fcb554   test_medium  9b80ca6f220dc685   scan_low     c5aec84ee0e8b3b0
monitor_low  1ffcc126fef9a0f6
```

The runtime proof at `docs/validation/verified-workflows-runtime-proof.json` needed no regeneration,
which is itself the byte-identity claim restated: it records those same seven digests, and
`prove_verified_workflows_runtime.py` still exits clean against them.

### Tests changed, and why each claim moved

- `test_full_catalog_renders_exact_model_pinned_profiles` became
  `test_full_catalog_renders_profiles_bound_to_their_execution_class`. It no longer restates seven
  model/effort pairs as literals; it reads them from the class policy and asserts the rendered TOML
  agrees. Restating them in the test would have recreated the duplication one layer down.
- `test_ultra_is_rejected_as_a_child_profile` used to force Ultra by editing the renderer's own
  policy dictionary. Ultra can now only reach a leaf by way of Fleet Core policy, so the test provokes
  it there instead, through a helper that repoints one class in place. That is a stronger claim than
  the one it replaces.
- Four tests are new: byte identity across all seven profiles; a repointed class moving its own
  profile while the other six stay byte-identical; an unmapped profile failing loudly; and a profile
  naming an undefined class failing loudly.
- The two roster assertions in `plugins/fleet-core/tests/test_tier_resolver.py` were renamed rather
  than edited in place, because their names encoded the now-false claim "exactly five".

### Codex's review found the collapse was only half-enforced

Third round in a row where the cross-engine pass caught something self-review had already signed off
on. No byte-identity defect — Codex independently reconstructed the old literal policy and confirmed
all seven profiles match, under both the normal catalog and a synthetic Luna canary — but three real
gaps, all now closed.

**The public render path escaped the policy.** `render_profile` re-read the class policy and then
used it only for the description; it emitted the caller-supplied resolution's own model and effort
and validated them against themselves. Codex demonstrated it by hand-building a resolution and
rendering `work_high` as `gpt-5.4-mini` / `low` while its class says `gpt-5.6-sol` / `high`. The
function is public, so "the class is the single policy source" was true only for resolutions this
module happened to build. Closed by `_reject_off_policy_resolution`, which refuses any model or
effort the class did not state.

That forced a design question the round had not faced: the Luna canary legitimately substitutes a
model. A blanket equality check would have broken it. So a deviation is now *declared* rather than
merely permitted — `ProfileResolution` carries a `policy_deviation` field, `resolve_profile` sets it
to `luna-v2-canary` when it substitutes, and only reasons named in `PROFILE_POLICY_DEVIATIONS` are
accepted. Effort is never deviated from, canary or not. An undeclared substitution and an invented
reason both fail loudly.

**The freshness claim was stronger than the implementation.** Codex traced `tier_palette` reading
`models.json` once at import and freezing the derived policies, which makes `execution_class_policy`
a dictionary lookup. The movement test patches that lookup, so it proves the renderer consults the
palette but not that a real file edit propagates. It offered two honest resolutions: narrow the
claim, or implement reload. Narrowing is the correct one, and the reason is in the decision record —
mid-process reload would let one bundle emit two policies. The claim, the test name, and the
decision entry were all corrected, and a test now pins the other half of the chain: that
`tier_palette`'s registry path is fleet-core's `models.json` and that a different registry file
yields a different policy.

**The README was still a second copy.** Its table listed all seven model and effort pairs directly
above a sentence claiming the plugin does not state them, with nothing binding the two. That is the
exact defect U4 removes from code, left standing in documentation. The model and effort columns are
gone; the table now carries only what the plugin owns — profile, class, write intent, purpose — and
points at the Fleet Core reference for the pairs.

### Two stale counts fixed rather than updated

`tier_resolver.py`'s module docstring and `plugins/fleet-core/PORTABILITY.md` both said "five leaf
execution classes". Writing "seven" would have restated a fact that drifts on the next change, which
is the defect this round exists to remove. Both now name `models.json` as the authority and state no
count. The count that remains is the one pinned test, which fails loudly when it is wrong.

### The engineering-journal classifier conflict fired a second time

Appending the U4 decision to `docs/engineering-journal/DECISIONS.md` moved
`historical_inventory_sha256` again, because the classifier still treats that file as
`historical-evidence` and pins it byte-stable while the repository's standing rule requires appending
a dated entry in the same commit as a decision. Verified the drift before bumping the pin: the
historical set is unchanged at 47 entries, no path added or removed, no token set changed, and exactly
one digest moved — the file appended to.

This is the second bump in one round from the same cause, which strengthens the recommendation
already recorded above: `DECISIONS.md` should carry the `mutable-engineering-journal` classification
that `QUEUED.md` already has, for the same reason. That is a change to a guard rather than to this
round's subject, so it stays an operator decision and was not made here.

### Checks run

- Full suite excluding the plugin blocked by a missing imaging library: **2508 passed**.
- `python3 scripts/validate_codex_plugins.py` — passes.
- `python3 plugins/verified-workflows/scripts/render_codex_agents.py --check --pretty` — passes.
- `python3 scripts/prove_verified_workflows_runtime.py --pretty` — passes.
- `python3 scripts/render_capability_schema.py --check` — capability schema current.
- `ruff` clean on every touched Python file.

One test, `test_orphan_evidence.py::test_two_process_successor_close_fences_stale_writer_and_preserves_bytes`,
fails with `_queue.Empty` under some narrower selections and passes in the full run. Reproduced it
with all U4 changes stashed, so it is pre-existing and load-sensitive rather than caused here.

## Phase 5 — U5, and a negative finding that did not survive

### I was wrong about the tool specification, and the cross-review proved it

Having found no tool list anywhere I looked, I drafted a plan amendment saying Codex 0.147.0 exposes
no model-visible tool specification, and dispatched the claim to be refuted rather than confirmed. It
was refuted, decisively, with tagged source and a working capture.

What I had checked, and why each check was looking in the wrong place:

| Surface | What I concluded | Why it was the wrong place |
| --- | --- | --- |
| `codex debug prompt-input` | Renders messages, byte-invariant to the MultiAgent V2 flag | Correct as far as it goes; it renders prompt messages, and the specification is not one |
| App-server v2 protocol, 246 surfaces | No `tools` property on any thread or turn response | The specification never travels through that protocol |
| `Config.tools` | A configuration toggle set | True, and irrelevant |

The specification is assembled by `router.model_visible_specs`
(`codex-rs/core/src/session/turn.rs:1223-1239` at tag `rust-v0.147.0`) and, under Responses Lite,
serialized as an `additional_tools` **developer input item** while the request's top-level `tools`
property is left empty (`codex-rs/core/src/client.rs:820-848`). I had searched for a property named
`tools`. It was in an input item the whole time.

There is also a hidden installed subcommand, `codex responses-api-proxy --dump-dir`, which writes
structured request dumps (`codex-rs/responses-api-proxy/src/lib.rs:181-194`). It does not appear in
`codex --help`.

**The cost of not checking would have been high.** A false absence written into a plan amendment is
worse than the gap it claims to describe: six downstream units would have inherited a substitute for
evidence, and nothing later in the round would have contradicted it.

### What the capture actually shows

The harness now stands up a local unauthenticated Responses API stand-in on `127.0.0.1`, points Codex
at it through `model_providers.offlineprobe`, scripts the root to spawn a named child profile and
wait, and records every outbound request body. No provider is reached, no model call is made, no
quota is spent.

Running it against `scan_low` captures the child turn directly: `gpt-5.6-terra` at `low` effort —
exactly what the `scan-low` execution class says after U4 — offered nine tool definitions across two
namespaces. `functions` carries `exec`, `wait`, `request_user_input`; `collaboration` carries
`followup_task`, `interrupt_agent`, `list_agents`, `send_message`, `spawn_agent`, `wait_agent`. Each
definition arrives with its description and parameter schema, which is what makes this a
specification rather than a list of names.

The digest over those canonical definitions is `88de1982…`. The cross-review engine's independent
capture, taken with a different rig that shares no code with this one, produces the same digest. That
agreement is the reason to trust the number.

### Two candidates rejected on evidence

`codex debug prompt-input` is not merely unused; it is rejected. Its collaboration prose is present
even when the collaboration tools are not offered, so presenting it as a tool-plan substitute would
mislead a later reader into thinking a capability was proven. It was deleted rather than left in the
module for someone to reach for.

`codex features list` is retained but scoped. It genuinely reports effective feature state — it is
how this session learned that `multi_agent_v2` is `stable` yet **off by default**, and that
`executor_capability_discovery` is still under development — but it is not evidence about tools, and
its docstring now says so.

### What U5 built

- **Frozen harness identity.** A composite digest over a declared file set, binding each file's
  repository-relative path to its bytes so a rename counts as a change. The pin lives in
  `scripts/proof_harness_pin.py`, outside the files it hashes, because a constant stored inside a
  hashed file cannot be updated without changing the value it pins. A receipt carrying no digest, or
  one that is not the pin, is refused.
- **A closed case registry.** Nine behavioural claims, each named. A receipt declares which one it is
  evidence for; an absent or unknown case is refused rather than folded into whichever matrix row
  came next.
- **Observed version on every receipt.** `codex --version` from the installed binary, supplied by the
  caller and validated as a version string. KTD2 forbids the target version standing in for an
  observation, so the two never share a field and a test asserts they differ.
- **Execution-environment fixtures** in `tests/conftest.py` for the two skill mechanisms this
  repository has previously conflated: a host-installed plugin skill, and an executor-backed
  `skill://` resource placed outside the Codex home so the permission boundary is observable.

### The harness review: eight findings, three of them Priority 0

The verdict was "not sound enough to freeze", which is the whole reason the plan sequences U5 as
built, then cross-reviewed, then frozen. All eight are fixed.

**Priority 0 — an allowlist is not sanitisation.** The reduced projection copied `model` and
`reasoning.effort` through unexamined. Authorization-shaped objects injected into those two fields
came out verbatim. They are the only request-body values a caller controls, so they were the only
place to look. Both are now validated as identifier-shaped strings, and the whole projection passes a
secret-shaped check before it is returned.

**Priority 0 — any non-null object could become a supported live proof.** `build_proof(live=True,
runtime_receipt={"not_a_receipt": True})` returned `capability_outcome: supported` with
`live_invocation_performed: true`. The existing test only rejected `None`, so it masked the boundary
rather than guarding it: "is not absent" was standing in for "is evidence". A live receipt is now
shape-checked against every required field and then validated for harness, case and observed version.

**Priority 0 — the disposable-home guard could be bypassed.** It derived "the real home" from
`CODEX_HOME`, which is mutable, so anything that pointed that variable at a temporary directory could
hand the operator's actual `~/.codex` to a probe. The default location is now protected
unconditionally, the environment variable only adds to the protected set, and containment is checked
in both directions rather than equality alone.

**The honest path was dropping the identities it promised.** The parser stamps the case, the harness
digest and the observed version onto a receipt; the projection `run_live_probe` returns was
discarding all three, so the published proof promised fields no reader could find. They now travel.

**The pin did not cover the harness contract.** The case registry lived un-hashed in the pin module,
so a case's meaning could change without moving the digest, and the renderer, profile synchroniser
and target-version module all influence proof output while being unbound. The digest constant now
lives alone in `scripts/proof_harness_sha256.py` — a pin cannot sit inside the set of files it hashes
— which frees `proof_harness_pin.py` and the four influencing modules to be hashed like any other
part of the instrument.

**The nine cases were the wrong granularity, not ceremony.** The plan asks for a stable identifier
per matrix row and for missing or duplicate rows to be rejected; a single `turn-permission` case
folded seven rows the plan enumerates by name, and one `skill-resource` case folded both mechanisms
and five outcomes. The registry is now per row: seven permission cases and five skill cases.

**The stub answered by arrival order.** Codex starts a child asynchronously after the scripted spawn,
so a global request counter makes the reply a child receives depend on the scheduler. Fifty offline
repetitions produced the expected order, so the race was never reproduced — but it was not prevented
either. Dispatch is now by whether the request carries a parent thread in its client metadata, and a
test drives the interleaving that an arrival-order stub gets wrong.

### Executor-backed skills are real, and my fixture was fiction

This is the second time in one unit that a "does it exist" question came back the other way. They do
exist in 0.147.0. The client names one at thread start as a `SelectedCapabilityRoot` — `{id,
location}` where the location is `{type: "environment", environmentId, path}` — and the model reaches
it through `skills.list` and `skills.read` over the app server. Restricted filesystem discovery runs
even with `executor_capability_discovery` off.

My fixture wrote an ordinary file and invented a `skill://` address, which is not how the resource is
addressed at all. The permission profile writer emitted `workspace_write` and `permitted_roots`, which
are not fields in this version; a profile is `{fileSystem, network}` with `fileSystem` carrying
`entries`, `read`, `write` and `globScanMaxDepth`. I verified both shapes against the protocol schema
the installed binary generates rather than taking either account on trust. The fixtures are rewritten
against the real shapes.

The fixtures being unused is why nothing failed. That is worth stating plainly: an unused fixture
modelling a mechanism incorrectly is a trap set for the unit that eventually picks it up.

### Checks after the fixes

- Full suite excluding the plugin blocked by a missing imaging library: **2534 passed**.
- Validator, runtime proof, capability schema, ruff — all clean.
- Harness digest recomputed and re-pinned; the pin and the files agree.

### Checks run

- Full suite excluding the plugin blocked by a missing imaging library: **2530 passed**.
- Validator, renderer check, runtime proof, capability schema, ruff — all clean.

## Phase 5 — six review rounds, and the correction that ended them

The harness was cross-reviewed by Codex six times. Every round returned "do not freeze". The rounds
that stayed on subject found real defects; the rounds after that did not, and the loop was stopped
by the operator rather than by convergence.

### What was kept

- **A requested child capture could silently return root turns.** With an unreadable child profile,
  `capture_tool_specification` returned three root turns and reported success. Any proof unit asking
  about a child's tool specification would have been handed the root's and told it was fine. Split
  out as `_require_requested_child` so it is testable without driving Codex into the failure.
- **An inverted subset check.** `set(observed) < REQUIRED` is false for a disjoint list, so an
  arbitrary operation list passed. Now `REQUIRED.issubset(observed)`, plus a closed-set check that
  every observed operation is one the snapshot records.
- **Three fixture shapes that do not exist in Codex 0.147**, each corrected against tagged source at
  `rust-v0.147.0` rather than either engine's account:
  - `deny` is canonical; `none` is a `#[serde(alias)]` marked *legacy, retained temporarily*
    (`codex-rs/protocol/src/permissions.rs:110-118`). The fixture rejected the canonical spelling
    and emitted the temporary one.
  - The authority **is** the root identifier — `SkillAuthority::new(SkillSourceKind::Executor,
    selected_root_id)` (`codex-rs/ext/skills/src/provider/executor.rs:189-225`). The fixture used
    two different values, which cannot resolve.
  - A capability root must be a plugin tree: `.codex-plugin/plugin.json` plus
    `skills/<name>/SKILL.md` (`codex-rs/app-server/tests/suite/v2/executor_skills.rs:145-200`). The
    fixture wrote one Markdown file that discovery would never find. The `skill://` handle also
    embeds the environment path, so its segment count varies with depth — an earlier assertion that
    it had exactly three segments was wrong in principle.
- **The fixture is validated by the binary's own schema.** `codex app-server generate-json-schema`
  emits `v2/ThreadStartParams.json` in 41ms with no model call, so `SelectedCapabilityRoot` is
  checked against Codex's definition rather than against this repository's opinion of it.
- **A fail-open fixture now fails.** An installed Codex that stops emitting its schema is protocol
  drift, not a reason to skip.

### What was removed, and why it should never have been built

Four defences were added across rounds three to six and then stripped:

| Removed | Threat it addressed |
| --- | --- |
| Ownership and mode-bit walk over every resolved path component | Another unprivileged user racing a rename |
| Access control list inspection via `/bin/ls -lde` | A shared ancestor granting `everyone` rename authority |
| `os.execv` re-exec into `python -I`, plus an isolation gate on live proofs | A hostile `sitecustomize.py` on PYTHONPATH |
| Object-identity mint registry for projections | A caller assembling a projection by hand |

None of those actors exists for a single-operator local plugin repository, and each made the harness
worse for its actual job: the re-exec is surprising machinery in the import path, the identity gate
made the validator untestable without a private seam, and the ACL check spawned a subprocess per
probe. The reasoning is recorded in `docs/engineering-journal/LEARNINGS.md` under
*An Adversarial Review Loop Without A Threat Model Never Terminates*.

The `_assert_disposable_home` guard was kept and re-scoped in its own docstring as what it actually
is: an accident guard that stops a probe writing into the operator's real Codex home through a wrong
path or a stale environment variable. Not a security boundary — anything running as this user can
reach that directory anyway.

### Checks

- Full suite excluding the plugin blocked by a missing imaging library: **2569 passed**. The count
  is lower than the peak of 2580 because eleven tests covering the removed defences went with them.
- Validator, runtime proof, ruff — all clean.
- Harness digest recomputed and re-pinned after the removal; the pin and the files agree.

## Phase 6 — U6 Luna canary, answered without spending a model call

The decisive evidence came from the U5 harness rather than from a live run, and it cost nothing.

**Codex 0.147.0 spawns `gpt-5.6-luna` as a child and honours the requested model and effort, but
offers that child no collaboration namespace at all** — only `exec`, `request_user_input` and
`wait`. `gpt-5.6-terra`, captured by the same instrument in the same run, is offered all six
collaboration operations. That side-by-side is what makes the absence a finding rather than a null
result, and it satisfies KTD7 directly: the absence comes from the tool plan, not from behaviour.

### The catalog field everyone was reading is not the one that governs

Luna's catalog row says `multi_agent_version: "v1"`, and the renderer's promotion gate refuses on
exactly that (`render_codex_agents.py:1012`). But a child's backend version is derived from the
parent thread and configuration, never from the child's model row —
`effective_multi_agent_version_for_spawn` at `codex-rs/core/src/thread_manager.rs:1314-1333`,
tag `rust-v0.147.0`. So the gate refuses on a property that does not decide the question. What
actually decides it is whether the child is offered collaboration tools, which is observable and
now observed. This is the round's own thesis appearing again: a field read once and frozen as
policy on a surface that cannot notice it was never the right field. U9 repairs the gate.

### Per-profile answer

Both promotion targets are leaf profiles — their developer instructions say to follow the bounded
role from the root thread and return a typed result, and neither spawns, messages, nor waits on
another agent. The missing collaboration namespace therefore does not disqualify them. Any profile
that *does* collaborate is disqualified outright by the observation above, with no run needed.

### What was deliberately not measured

Instruction adherence, typed-result schema validity, and cold-resume identity all need live model
calls. The operator scoped them out of this round. The receipt records each as
`measured: false` with a reason, and `validate_luna_canary` refuses any profile that claims a pass
on a criterion the receipt does not record as measured — so "we did not test this" cannot later be
read as "this passed". The verdict wording carries the same caution: `eligible-on-measured-criteria`
rather than `eligible`.

### Checks

- Full suite excluding the plugin blocked by a missing imaging library: **2575 passed**.
- Validator, runtime proof, ruff — all clean. Harness digest re-pinned after the validator was added.
- Zero model calls, zero quota. Every probe ran against a disposable `CODEX_HOME` and a local
  Responses API stand-in.

## Next step

U7 — the turn-environment permission proof, which the plan marks as a blocking gate. U8 through U14
remain untouched.
