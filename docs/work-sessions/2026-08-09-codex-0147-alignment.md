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

## Next step

U2 and U3 both unblock on U1. Claude owns both.
