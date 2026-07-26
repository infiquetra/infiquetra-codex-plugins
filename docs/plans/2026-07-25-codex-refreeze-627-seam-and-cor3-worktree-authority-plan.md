---
title: Codex re-freeze of the #627 seam contract + COR3 outcome_worktrees lease-authority port
type: feat
status: active
date: 2026-07-25
origin: infiquetra/infiquetra-codex-plugins#45
---

# Codex re-freeze of the #627 seam contract + COR3 outcome_worktrees lease-authority port

## Summary

Restore codex/claude byte-identity on the frozen cross-runtime seam at Claude `b464d090`, then port
two lease-authority mechanisms that codex does not yet have at all. Grounding measurement reclassifies
the work: the byte re-freeze is ~80 lines across two files, while the two "mirror" items are
**subsystem ports into modules where the target mechanism is entirely absent**, not the
parameter-threading exercise the issue describes.

Six units in one linear chain and **one PR** (KTD2). U1 is the mandatory port-contract classification
gate and writes no production code; U2–U5 claim rows it classified; U6 moves the release surfaces and
runs the cutover gate. Two structural facts drive the shape: the correct frozen source range is
`cf15a09f..b464d090`, chaining exactly off the predecessor contract's target (R4); and COR3's source
rows do not appear in that range at all — they are **orphaned defers** in the predecessor contract,
deferred to codex#34, which closed on 2026-07-20 without treating them (R4b).

## Problem Frame

`infiquetra-claude-plugins#627` (saga 0.107.0 / fleet-core 0.17.0) deliberately broke byte identity
between Claude's `outcome_compat.py` and codex's frozen twin, per the KTD5 upstream-first rule: root
causes land in `infiquetra-claude-plugins` first and codex re-freezes after merge, never the reverse.
Since that merge the cross-runtime acceptance harness's `contract_digests` check has halted at
`port-digest` **by design**. This issue is the re-freeze that clears it.

`infiquetra-claude-plugins#637` (merged `53cd65f5`, saga 0.108.0 / fleet-core 0.18.0) then moved the
refuse-mode and dispatcher-arm semantics again, which the issue's 2026-07-22 sequencing comment
recorded. That comment remains the binding statement of *what shape to mirror*.

### What grounding changed about this frame

Five of the issue's working assumptions were tested against the tree this session. Three held, two
did not, and one predicted risk turned out to be absent entirely.

| Assumption | Verdict | Measurement |
|---|---|---|
| Claude's tree kept moving, so mirror targets drifted | **False** | `git diff 53cd65f5 b464d090` is EMPTY for `outcome_dispatcher.py`, `outcome_reconcile.py`, `outcome_worktrees.py`; `outcome_compat.py` and `audit_store.py` are byte-identical across `8882bdc2` == `53cd65f5` == `b464d090` |
| The COR3 reference count needs a fresh recount | **Held, count unchanged** | 46 `lease_authority` lines in Claude `outcome_worktrees.py` at `b464d090`, matching the "~46 at `794b4da6`" figure |
| COR3 is threading authority through existing parameter surfaces | **False** | codex `outcome_worktrees.py` has **zero** `lease_authority` references and lacks nine functions/classes the Claude module carries |
| Refuse-mode admission is an existing branch to adjust | **False** | codex `fleet_commons/lease_broker.py` has **zero** `on_conflict` and zero `"refuse"` occurrences |
| The codex V2 cutover is the drift risk | **False** | PRs #46/#48 touched **0 of 6** seam files (`git log 74258be~1..f79f141b -- <each>` empty for all six) |

`lease_broker.py` did move upstream (+524/−42, 57 hunks between `53cd65f5` and `b464d090`) but not on
the mirrored surface: `_drop_superseded_resource_lease`, `_owner_state`, and `on_conflict` have zero
changed lines, and the only four changed lines containing `refuse` belong to a corrupt-document repair
path (`status="refused"`). The 2026-07-22 comment's guidance is therefore still exactly correct four
releases later.

## Requirements

**R1.** Pin the frozen source ref at Claude `b464d090` and record in the port manifest the verified
equivalence `8882bdc2 == 53cd65f5 == b464d090` for both byte-frozen files, so the deviation from the
SHA named in the issue comment is evidenced rather than silent.

**R2.** `plugins/saga/scripts/outcome_compat.py` becomes byte-identical to Claude's at `b464d090`
except for `RUNTIME_LABEL = "codex"` (line 83), which is the sole permitted divergence.

**R3.** `plugins/fleet-core/scripts/fleet_commons/audit_store.py` re-ports the universal fail-closed
ancestor walk: no home-scope early return, every component walked from the filesystem anchor down via
`lstat` (never `resolve` inside the walk), and world-writable refused **unless** also sticky
(`S_ISVTX`).

**R4.** A new port contract is bootstrapped with `scripts/port_contract.py init` — the repository's
own contract tooling, not a hand-authored JSON file — pinning `--source-base cf15a09f`
`--source-target b464d090`. That range is not chosen for convenience: `cf15a09f` is the **target_ref**
of the predecessor contract `2026-07-19-lease-safe-substrate.json`, so the two contracts chain exactly
with no gap and no re-freeze of an already-frozen range (the runbook forbids extending one).

`expected_count` is **derived, never asserted**: `port_contract.py:437-450` sets
`expected_count = len(source_rows)` where the rows come from the `base→target` diff, not from
`len(pathspecs)`. Measured over that range, five of the six candidate surfaces produce rows —
`outcome_compat.py`, `audit_store.py`, `lease_broker.py`, `outcome.py`, `outcome_dispatcher.py`. A
sixth, `outcome_worktrees.py`, produces **none** (see R4b).

**R4a — the harness records the inventory digest but never compares it, so no acceptance assertion
can rest on it.** `contract_digests` reads `docs/validation/saga-family-target-inventory.json` via
`_sha256_file` (Claude `tools/run_cross_runtime_outcome_acceptance.py:262-267`) and returns the digest
as reported context. The only condition that raises the `port-digest` `HarnessError` is the normalized
`outcome_compat.py` comparison at `:256-261`. A stale inventory therefore does **not** fail the
harness — it silently reports a stale hash.

The inventory still gets rebuilt, but the freshness proof belongs to this repository, not the harness:
regenerate it after the release surfaces move and validate it through
`port_contract.py validate` plus the repo's own generated-file check. Comparing the acceptance
bundle's recorded digest against the file is an assertion for the acceptance unit (U6), after the
bundle exists — asserting it in the manifest unit would compare the file against a bundle that has not
been produced yet.

**R4b — COR3's source rows already exist, deferred, in the predecessor contract, and must be promoted
rather than re-derived.** `plugins/saga/scripts/outcome_worktrees.py` has **zero** changed lines
across `cf15a09f..b464d090`, so a new contract over that range yields no row for it and nothing to
classify. Its row lives in `2026-07-19-lease-safe-substrate.json` at `state: classified`,
`treatment: defer`, with the rationale *"Worktree reconciliation consumes the guard at Claude seams;
Codex worktree parity is #34 scope."* Two sibling rows carry the same deferral:
`plugins/saga/scripts/outcome.py` and `tests/test_outcome_worktrees.py`.

Codex **#34 closed on 2026-07-20 without treating them**, so all three are orphaned defers pointing at
a discharged issue. #45 is their correct home. `refresh` cannot do this — `refresh_manifest`
(`port_contract.py:1548-1578`) recomputes observations and records added/removed row ids but never
touches `state` or `treatment`. The promotion is an operator edit to the existing manifest, which the
tool then validates; `verify-source` still passes because the frozen inventory is unchanged.

**R5.** Codex `fleet_commons/lease_broker.py` gains refuse-mode admission on
`_drop_superseded_resource_lease`, faithful to Claude's implementation at
`plugins/fleet-core/scripts/fleet_commons/lease_broker.py:2375-2425`. The signature gains
`on_conflict: OnConflict = "supersede"` — the default preserves byte-for-byte prior behavior for
every other consumer. The refusal is a **three-part conjunction**, not one test:

```python
if prior is not None:
    if on_conflict == "refuse":
        prior_lease = registry.leases.get(prior.lease_id)
        if (
            prior_lease is not None
            and not self._expired(prior_lease, monotonic=monotonic, boot_id=boot_id)
            and self._owner_state(prior_lease) != "dead"
        ):
            raise LeaseConflictError(
                "resource is held by a live lease owned by "
                f"{prior_lease.owner_id!r}; refuse-mode admission will not supersede it",
                holder_owner_id=prior_lease.owner_id,
            )
    registry.leases.pop(prior.lease_id, None)
```

All three arms are load-bearing and each has its own fall-through-to-supersede case: a **missing**
`prior_lease` supersedes; an **expired** prior is reclaimed in *both* modes (the TTL + boot-id check
precedes the liveness probe); and a provably **dead** owner (crash orphan, stale boot id, reused pid)
supersedes with no TTL wait, closing the crash-orphan self-refusal window. Only `"live"` and
`"unknown"` on an unexpired prior refuse — fail-closed, so an identity-blind or cross-host peer is
never superseded while possibly alive.

**R5a.** The refusal raises `LeaseConflictError` carrying `holder_owner_id=prior_lease.owner_id` —
not a bare exception and not `LeaseOwnershipError`.

**R5b.** Refuse-mode admission is gated **below** two existing precedence checks that must keep firing
first and must not be reordered: a resource with a retained settlement raises `LeaseOwnershipError`
("resource has retained settlement authority and cannot be superseded"), and a canonically-closed
resource whose lease is absent from the registry raises `LeaseOwnershipError` ("canonically closed
resource requires acquire_successor with predecessor receipt").

**R6.** Codex's dispatcher gains a typed `DispatcherLeaseTransientError(DispatcherError)` raised at
lease-conflict admission sites, classified through a shim-safe `_lease_conflict_error_type()` that
**declines to transient** when the shim fails to load.

**R7.** Codex's reconcile hot path re-raises any **non-transient** `DispatcherError` before any
lease-release or ledger write in that arm, aborting the tick loudly with zero new state. The guard is
a single type test — `if not isinstance(dispatch_error, DispatcherLeaseTransientError): raise` —
placed at the head of the `except DispatcherError` arm (Claude `plugins/saga/scripts/outcome.py:1664`).

**R7a — the three locks behave differently, and a test must not conflate them.** At the moment the
non-transient re-raise fires:

| Lock | State | Why |
|---|---|---|
| 300 s broker dispatch lease | **already released** | `make_dispatcher`'s own `finally` runs before this arm |
| per-subplot `dispatch-{sid}` store lock | **still held** | deliberate; self-heals via `acquire_lease` stale-reclaim after the 900 s `DEFAULT_LEASE_TTL` |
| coordinator lock | **released** | by the outer `finally`, so a loud abort never wedges the coordinator |

A test asserting "the lease is still held" is therefore ambiguous and, read as the broker lease,
**false**. Assert on the per-subplot store lock specifically.

**"No ledger write" is also wrong as stated, and asserting it would drive a real regression.** A
correct implementation has *already* appended the `outcome.dispatch.v2` intent by the time dispatch
raises — codex `plugins/saga/scripts/outcome.py:1270-1281` appends it, `dispatch(request)` is called
at `:1308`, and the `DispatcherError` arm begins at `:1319`. A test demanding an empty ledger is
therefore either unsatisfiable or satisfiable only by deleting required intent state. Assert instead:

- snapshot the ledger immediately **before** `dispatch(request)`;
- after the re-raise, assert **no record beyond that snapshot** — specifically no halt, no
  acknowledgement, and no settlement;
- separately spy that the per-subplot lock release was **not** called, and confirm the lock is still
  held.

The pre-dispatch intent is required state, not leakage; the loud abort's contract is that nothing
*further* is written.

**R7b — the transient path is not merely "continue".** A `DispatcherLeaseTransientError` must:
release the lock; append a reducer-**visible** `(dispatch, halt)` record paired to the intent's `key`,
built spread-first / literal-last so `kind` survives as `"dispatch"` for both
`reduce_dispatch_ledger`'s halt arm and `outcome_report._halted_subplots`, preserving the receipt's
own kind under `receipt_kind`; and settle the attempt. Omitting the halt record is the #628 failure
shape — the orphaned intent matches no reducer branch, so it is invisible, the store lock leaks to
its TTL, and the leaf silently re-dispatches with no operator page.

**R8.** COR3: codex `outcome_worktrees.py` gains the lease-authority subsystem — the authority error
type, the reap preflight, the lease binding, and the authority-carrying `reap_worktree` signature —
wired at the `production_worktree_processor` seam. It is **not** threaded through the `prune` and
`advance` CLI surfaces: those subparsers take no authority argument, and the processor factory is
where the authority is constructed and injected. Codex already carries
`default_lease_authority()` at `plugins/saga/scripts/outcome_dispatcher.py:192`, so U5 consumes that
existing factory read-only rather than declaring or redefining one.

**R9.** Every changed plugin moves its release surfaces in the same PR, at the paths this repo actually
uses: `plugins/<plugin>/.codex-plugin/plugin.json`, the single codex marketplace at
`.agents/plugins/marketplace.json`, and `plugins/<plugin>/CHANGELOG.md`. There is no
`.claude-plugin/marketplace.json` in this repository and none is to be created — that is the Claude
repo's path, and minting it here would create a second, wrongly-shaped registry beside the real one.

**R10.** Red-first for every behavioral test: each new assertion is shown failing against the pre-port
tree before the port lands, with the failing output captured in the work-session record.

**R11.** The `contract_digests` / `port-digest` acceptance leg is run and its result reported verbatim.
A red leg is documented truth, never worked around or silently reframed.

**R12.** No codex-first fix. If the port surfaces a new defect in the shared mechanism, it is filed
upstream against `infiquetra-claude-plugins` and this work stops at the boundary (KTD5).

## Key Technical Decisions

**KTD1 — Pin `b464d090`, not `53cd65f5`.** The two byte-frozen files are provably identical at
`8882bdc2`, `53cd65f5`, and `b464d090`, so all three produce the same bytes. Pinning current
`origin/main` yields a single-SHA manifest at head and avoids a second `STOP-FROZEN-REF`
reconciliation the next time the manifest is read. The cost is a documented deviation from the SHA the
issue comment names; R1 pays it by recording the equivalence proof in the manifest itself.

**KTD2 — One PR, not three. This reverses an earlier draft of this plan.** An earlier revision
proposed PR-A (byte re-freeze) / PR-B (broker + dispatcher) / PR-C (COR3), justified by blast radius
and by PR-A turning the `port-digest` acceptance leg green early. Both halves of that justification
failed verification:

1. *`/work` has exactly one PR-ready boundary per execution contract.* It executes every unit through
   Phase 5 and only then offers a PR (`plugins/saga/skills/work/SKILL.md:684-728`). There is no
   "open a PR at each unit boundary" behavior. Three PRs would require three separate execution
   contracts and three operator runs — the earlier draft asserted a mechanism that does not exist.
2. *Early `port-digest` green buys nothing automated.* `run_cross_runtime_outcome_acceptance.py` is
   referenced by **none** of the four workflows in `.github/workflows/`; it is an operator-run harness
   with explicit revision pins on both runtimes. Landing its green signal one PR earlier unblocks no
   pipeline.

Against that, the runbook wants manifest, marketplace, inventory, changelog, portability notes, and
install proof moved "as one release unit," and three PRs would mean three partial release units and
three version sequences — the exact release-surface drift this repo family keeps re-learning.

The blast-radius concern is real and is answered without splitting the PR: the units stay distinct
commits, and the port contract's own per-unit gate
(`port_contract.py validate --stage unit --unit U<n>`) gives per-unit proof inside the single PR. The
`--stage cutover` gate then runs once, at the end, where it belongs.

*What survives from the old KTD2:* the `port-digest` surface really is narrow. `contract_digests`
(`tools/run_cross_runtime_outcome_acceptance.py:245-267`) raises its `HarnessError` on exactly one
condition — the two `outcome_compat.py` copies differing after
`codex_text.replace('RUNTIME_LABEL = "codex"', 'RUNTIME_LABEL = "claude"', 1)`. It does **not** compare
`audit_store.py` and does not touch the codex-native trio. That remains true; it is simply no longer a
reason to split.

**KTD3 — Byte-faithful and semantic-mirror are opposite mechanics; never mix them.** `outcome_compat.py`
and `audit_store.py` are byte-frozen twins where "pull the merged Claude bytes forward" is literally
correct. `outcome_dispatcher.py`, `outcome.py`, and `outcome_worktrees.py` are codex-native
implementations that deliberately diverge; for that group the deliverable is mirrored *semantics*
under codex's own `outcome.dispatch.v2` intent and acknowledgement contract.

*The proof is a semantic diff of the actual target modules, not a line count.* An earlier revision
argued this from `outcome_reconcile.py` being larger in codex (532 vs 494 lines). The count is true
but proves nothing here, because `_reconcile_once` — the function U4 actually ports — is defined in
`outcome.py` in **both** repos (codex `:1148`, Claude `:1097`) and in neither `outcome_reconcile.py`.
The real evidence is per-module and per-symbol: codex `outcome_dispatcher.py` (542 lines vs Claude
879) has `DispatcherError` ×11 but zero `DispatcherLeaseTransientError` and zero
`_lease_conflict_error_type`; codex `outcome_worktrees.py` (505 vs 980) lacks all nine authority
symbols in KTD4; codex `fleet_commons/lease_broker.py` has zero `on_conflict` and zero `"refuse"`.
Each is a missing-symbol finding against the specific module the port targets.

**KTD4 — COR3 is a subsystem port, reclassified from the issue's "threading" framing.** Codex
`outcome_worktrees.py` (505 lines) lacks all nine of: `WorktreeAuthorityError`, `ReapPreflight`,
`read_registry_strict`, `_lease_binding`, `prevalidate_reap_authority`, `_arm_worktree`,
`stale_worktree_debits`, `_reap_prevalidated`, and `reconcile_worktree_leases`. Its `reap_worktree` at
`:254` has signature `(store, subplot_id, ops, *, at="")` — no `lease_authority`, no
`release_authority`. Claude's equivalent module is 980 lines. This unit sizes as a port of ~475 net
lines, not a signature change.

**KTD5 — Upstream-first is absolute and bounds this plan.** Root causes land in
`infiquetra-claude-plugins` first; codex re-freezes after merge, never the reverse. A new defect found
during this work becomes an upstream issue and a documented stop, not a codex-side repair.

**KTD6 — The authoritative broker is the fleet-core copy.** Codex carries two `lease_broker.py` files:
`plugins/saga/scripts/lease_broker.py` (542 lines) and
`plugins/fleet-core/scripts/fleet_commons/lease_broker.py` (4183 lines). Only the fleet-core copy
carries `_drop_superseded_resource_lease` (2 refs) and `_owner_state` (3 refs); the saga copy carries
neither. R5 targets the fleet-core copy. U3 must first determine whether the saga copy is a vendored
shim, a stale duplicate, or a deliberate narrow subset, and state the finding — porting into the wrong
one is a silent no-op.

**KTD7 — The frozen seam ships with no codex test coverage today, so a green suite is not evidence.**
`plugins/saga/tests/` contains no `test_outcome_compat.py`, no `test_outcome_worktrees.py`, and no
`test_outcome_dispatcher.py`. `outcome_compat.py` is 1686 lines and untested codex-side. Every unit
below therefore creates its test module rather than extending one, and "the suite passed after the
re-freeze" is explicitly rejected as an acceptance signal for U1.

**KTD8 — Classification is a gate, not paperwork, and it runs before any source behavior lands.** The
runbook's staged workflow puts `port_contract.py init` at step 3 and "classify every source and
Codex-drift row, then pass `validate --stage classification`" at step 4 — *before* step 5 claims rows
by unit and advances them to `implemented`. Step 4 is explicit that "the classification gate proves
complete treatment before source behavior work." An earlier revision of this plan ordered the byte
re-freeze first and scoped the manifest to two files, which both inverted that order and left the four
other ported modules in no contract at all. U1 below is that gate; every implementation unit claims
rows it has already classified.

## Implementation Units

Dependency order: `U1 → U2 → U3 → U4 → U5 → U6`, one linear chain, one execution contract, one PR
(KTD2). U1 is the classification gate; U6 carries the release surfaces and the `--stage cutover` gate.

### U1. Port contract bootstrap and classification gate

Establish the contract that every later unit claims rows from, and pass
`validate --stage classification` before any behavior changes. This unit writes **no** production code.

**Scope — two manifest operations, because the ported surfaces live in two ranges:**

*(a) A new contract* for the five surfaces that changed in `cf15a09f..b464d090`:

```
python3 scripts/port_contract.py init \
  --source-repo /Users/jefcox/workspace/infiquetra/infiquetra-claude-plugins \
  --source-base cf15a09f --source-target b464d090 \
  --source-pathspec plugins/saga/scripts/outcome_compat.py \
  --source-pathspec plugins/fleet-core/scripts/fleet_commons/audit_store.py \
  --source-pathspec plugins/fleet-core/scripts/fleet_commons/lease_broker.py \
  --source-pathspec plugins/saga/scripts/outcome.py \
  --source-pathspec plugins/saga/scripts/outcome_dispatcher.py
```

`init` derives the rows; do not hand-write `expected_count` or `inventory_sha256`. Measured, that
range yields five `M` rows. Classify each with `state`, `treatment`, `rationale`, `units`,
`planned_targets`, and `planned_tests` — `_validate_source_rows` (`port_contract.py:750-786`) rejects
a `direct-port`/`codex-adapt` row that lacks targets and tests, and rejects a `defer`/`reject` row that
claims a unit.

*(b) Promotion of the three orphaned defers* in `2026-07-19-lease-safe-substrate.json` (R4b):
`outcome_worktrees.py` and `tests/test_outcome_worktrees.py` move `defer → codex-adapt` claiming U5,
with a rationale naming #45 as the discharge of the closed-#34 deferral; `outcome.py`'s row is
re-justified with a current rationale if it stays deferred there. **Units U2–U5 are already claimed in
that contract** — the promoted rows must claim a free id from `UNIT_IDS` (`U1`–`U9`), so use `U6` or
`U7` there and record the mapping to this plan's U5 in the rationale. Do not reuse a claimed id.

**Substance:** `refresh` is the wrong tool for (b) — `refresh_manifest` (`:1548-1578`) recomputes
observations and records added/removed row ids but never touches `state` or `treatment`. Promotion is
an operator edit that the validator then checks. Run
`port_contract.py verify-source --source-repo <claude-clone>` on **both** manifests afterward; the
frozen inventory is unchanged by a classification edit, so both must still pass.

**Gate:** `validate --stage classification` exits 0 on both manifests. This is U1's completion
condition — not "the files were written."

**Test scenarios** — new `tests/test_codex_627_seam_refreeze_port_contract.py`, following the shape of
the five existing `tests/test_*_port_contract.py` modules (**not** `test_provenance_manifest.py`,
which governs a different artifact family):

- the new manifest passes `validate --stage classification` with exit 0
- `verify-source` passes against the pinned Claude clone at `b464d090`
- `expected_count` equals `len(source.rows)` — the derived value, explicitly **not** `len(pathspecs)`,
  which differs here (5 rows over 5 pathspecs only by coincidence; the invariant is row-derived)
- `inventory_sha256` recomputes to the recorded value
- every `planned_target` path exists in the codex tree (guards KTD6's two-same-named-files trap)
- no row remains `state: unclassified` or `treatment: null`
- the promoted `outcome_worktrees.py` row in the predecessor manifest claims a unit id not already
  claimed by another row in that manifest
- **failure modes:** `init` refuses to overwrite an existing manifest; a `codex-adapt` row missing
  `planned_tests` fails validation; a `defer` row carrying a `units` entry fails validation

### U2. Byte re-freeze of the two frozen twins at `b464d090`

Copy Claude's `outcome_compat.py` and re-port `audit_store.py`'s ancestor guard, preserving
`RUNTIME_LABEL = "codex"` as the only divergence.

**Scope:** `plugins/saga/scripts/outcome_compat.py` (codex 1686 → Claude 1700 lines, measured
+40/−26); `plugins/fleet-core/scripts/fleet_commons/audit_store.py` (codex 355 → Claude 366, measured
+42/−31).

**Substance:** the entire `outcome_compat.py` divergence is `RUNTIME_LABEL` (`:83`), the
`_handoff_store_halt` `supported=` / `next_action=` strings, and the body plus docstring of
`_refuse_unsafe_handoff_ancestors()`. The semantic change is #627's universal fail-closed walk: drop
the `is_relative_to(home)` early return, build the component list from `candidate.anchor` down, walk
every component with `lstat`, refuse a symlink anywhere, and refuse world-writable **unless** sticky.
The `next_action` string gains the NFS/SMB and FAT32/exFAT relocate guidance.

**Test scenarios** — new file `plugins/saga/tests/test_outcome_compat.py` and additions to
`plugins/fleet-core/tests/test_audit_store.py`:

- a symlinked component **above** the user's home is refused (fails pre-port — the old guard exempts
  everything outside home)
- a world-writable non-sticky component above home is refused (fails pre-port)
- a world-writable **and sticky** component, the `/tmp` 1777 shape, is accepted (must pass before and
  after — this is the exemption, not a regression)
- a group-writable component is accepted (the #624 boundary, unchanged)
- a `PermissionError` on a component raises the typed halt, not a bare exception
- `FileNotFoundError` short-circuits and returns cleanly
- `RUNTIME_LABEL == "codex"` after the re-freeze — the guard against copying Claude's label

**Verification of byte-identity:** diff the ported file against Claude's at `b464d090` and assert the
only differing line is `RUNTIME_LABEL`. Write the diff to a file and parse it — do not pipe
`git diff` into `grep`, which this environment blanks.

### U3. Refuse-mode admission in the codex fleet-core broker

Add `on_conflict` admission with the `"refuse"` branch to `_drop_superseded_resource_lease`.

**Scope:** `plugins/fleet-core/scripts/fleet_commons/lease_broker.py` (4183 lines).

**Substance:** codex has the superseding machinery (`_drop_superseded_resource_lease` ×2,
`_owner_state` ×3) but **zero** `on_conflict` and zero `"refuse"` occurrences, so this adds the mode
rather than adjusting it. Claude's copy carries `on_conflict` ×9, `_owner_state` ×5, `"refuse"` ×6.

Implement R5 exactly as quoted there — a three-part conjunction, not the one-part paraphrase the issue
comment gives. Port R5a's `LeaseConflictError` with `holder_owner_id=`, and preserve R5b's two
precedence gates above the refuse branch. Reference implementation: Claude
`plugins/fleet-core/scripts/fleet_commons/lease_broker.py:2375-2425`; read it rather than working from
the issue comment's summary. Unknown-refuses-with-live is the safe direction and is not an oversight
to optimize away.

**First task, before any edit:** resolve KTD6 — determine what `plugins/saga/scripts/lease_broker.py`
(542 lines) is relative to the fleet-core copy, and record the finding. If it turns out to be a
vendored shim that also needs the mode, that is a scope change to surface, not to absorb silently.

**Test scenarios** — `plugins/fleet-core/tests/test_lease_broker.py` (exists, 53.6K):

One scenario per arm of R5's conjunction, plus the precedence gates and the failure modes:

- `on_conflict="refuse"` against a **live unexpired** prior refuses with `LeaseConflictError`, the
  raised error carries `holder_owner_id == prior_lease.owner_id`, and the prior lease's registry bytes
  are byte-for-byte untouched (red-first)
- an **unknown** owner state on an unexpired prior refuses, matching the live case, not the dead case
- a provably **dead** prior (crash orphan) supersedes immediately with no TTL wait (red-first)
- each of the three death shapes — crash orphan, stale boot id, reused pid — classifies as dead
- **an EXPIRED prior is reclaimed in refuse mode**, because `_expired` precedes the liveness probe;
  this is the arm most likely to be dropped by a one-part reading of the guard (red-first)
- **`prior_lease is None`** (fence present, lease absent from the registry) falls through to supersede
  rather than refusing
- **precedence, R5b:** a resource with a retained settlement raises `LeaseOwnershipError` even under
  `on_conflict="refuse"` — the settlement gate fires first and is not reordered
- **precedence, R5b:** a canonically-closed resource whose lease is absent raises `LeaseOwnershipError`
  ("requires acquire_successor with predecessor receipt"), also ahead of the refuse branch
- default-mode (`on_conflict="supersede"`) call sites produce byte-identical behavior to pre-port, and
  the parameter's default is `"supersede"` so untouched callers need no edit (characterization; must
  pass before and after)
- **malformed input:** an unknown `on_conflict` string is rejected at the public boundary rather than
  silently falling through to supersede. Upstream carries
  `test_acquire_agent_rejects_unknown_on_conflict` for exactly this; port it. Cover `None` and `""`
  alongside the unknown-string case — a closed-value check that admits `None` fails open, which on a
  fail-closed admission path is the worst possible direction (red-first)

### U4. Dispatcher transient-error arm and reconcile re-raise ordering

Add the typed transient subclass and make permanent faults abort the tick before any release or write.

**Scope:** `plugins/saga/scripts/outcome_dispatcher.py` (542 lines, carries `DispatcherError` ×11 but
neither `DispatcherLeaseTransientError` nor `_lease_conflict_error_type`); and the reconcile hot path
in `plugins/saga/scripts/outcome.py`, where `_reconcile_once` is defined at `:1148`.

**There is no layout divergence here** — an earlier draft of this plan claimed one and was wrong.
Claude defines `_reconcile_once` in `outcome.py` as well, at `:1097`; `outcome_reconcile.py` defines
it in neither repo. Claude's reference implementation of this arm is `outcome.py:1650-1690` — read
that, not `outcome_reconcile.py`.

**Substance:** add `DispatcherLeaseTransientError(DispatcherError)` (Claude
`outcome_dispatcher.py:66`, subclassing `DispatcherError` at `:62`) raised at lease-conflict admission
sites, classified via the shim-safe `_lease_conflict_error_type()` (`:79`, returning
`type[BaseException] | None`) that declines to transient when the shim fails to load. Implement R7's
head-of-arm type guard, R7a's lock semantics, and R7b's full transient path — the transient branch is
release-lock + reducer-visible `(dispatch, halt)` record + settle-attempt, not a bare `continue`.

Preserve codex's own `outcome.dispatch.v2` intent/acknowledgement contract — that string lives in
`plugins/saga/references/outcome-cross-runtime.md`, `run-fact-ledger.md`, and
`plugins/saga/tests/test_outcome_board_sync.py`, and is the contract this port must not disturb.

**Test scenarios** — new file `plugins/saga/tests/test_outcome_dispatcher.py`, plus additions to the
existing `plugins/saga/tests/test_outcome_reconcile.py`:

- a lease conflict raises the transient subclass and the tick continues (red-first)
- **the ordering test, load-bearing.** A non-transient `DispatcherError` aborts the tick without
  writing anything *further*. Assert per R7a: snapshot the ledger immediately before
  `dispatch(request)`, then assert no record beyond that snapshot — no halt, no acknowledgement, no
  settlement — and that the per-subplot `dispatch-{sid}` **store lock** is still held at the moment of
  the raise. Two assertions that look right and are not: do **not** assert the broker dispatch lease is
  held (`make_dispatcher`'s own `finally` released it before this arm), and do **not** assert an empty
  ledger — the `outcome.dispatch.v2` intent is appended at `outcome.py:1270-1281`, before
  `dispatch(request)` at `:1308`, so demanding an empty ledger is satisfiable only by deleting required
  state. A test that only checks the exception type passes against an implementation that writes first,
  which is the defect R7 exists to prevent (red-first)
- the transient path writes a reducer-visible halt: assert the appended record has `kind == "dispatch"`
  (spread-first / literal-last ordering), is paired to the intent's `key`, preserves the receipt's own
  kind under `receipt_kind`, and that `reduce_dispatch_ledger`'s halt arm matches it (red-first — this
  is the #628 invisibility shape)
- a failed shim load classifies as **non-transient**, i.e. declines to transient rather than assuming
  it (red-first)
- the `outcome.dispatch.v2` intent/ack contract is unchanged — `test_outcome_board_sync.py` passes
  unmodified
- **repeated transient, append-once:** two consecutive transient failures for the same intent `key`
  append exactly one halt record per attempt and never duplicate a settlement for an
  already-settled attempt. A re-run that double-appends is the silent-duplicate shape the ledger
  reducer cannot distinguish from two real halts (red-first)
- **settlement idempotency:** settling an attempt twice is a no-op rather than a second record or a
  raise

### U5. COR3 — the worktree lease-authority subsystem port

Port the authority subsystem into codex `outcome_worktrees.py` and thread it out to the CLI.

**Scope:** `plugins/saga/scripts/outcome_worktrees.py` (codex 505 → Claude 980 lines) and
`plugins/saga/scripts/outcome.py` (codex 2309 lines).

**The `outcome.py` seam is a processor factory, not a verb parameter** — an earlier draft of this plan
said "thread it into `prune` and `advance`", which would send an implementer looking for parameters
that do not exist. Claude's 6 `lease_authority` lines sit in `production_worktree_processor` (`:2256`,
with the parameter at `:2262`/`:2273` and its nested `processor` closure at `:2284`/`:2292`). `main()`
(`:2359`) then wires the authority in two places: `lease_authority=default_lease_authority()` into
`make_dispatcher` at `:2689`, and `worktree_processor=production_worktree_processor(root)` at `:2693`.
The `advance` (`:2426`) and `prune` (`:2567`) subparsers *consume* those wired processors; they take no
authority argument of their own. Port the factory and the wiring, not a verb signature.

**Substance:** codex lacks the entire mechanism — nine absent functions and classes per KTD4. The full
Claude surface is 55 `lease_authority` lines across three modules: `outcome_worktrees.py` (46),
`outcome.py` (6), `outcome_dispatcher.py` (3); `outcome_reconcile.py` carries none. Port the authority
error type, the reap preflight, the lease binding, and the authority-carrying `reap_worktree` and
`harvest_worktrees` signatures, then port the `production_worktree_processor` factory and its `main()`
wiring so the `advance` and `prune` verbs receive an authority-carrying processor.

**There is no U4/U5 dispatcher overlap — an earlier draft claimed one and was wrong.** Codex
**already has** `default_lease_authority()` at `plugins/saga/scripts/outcome_dispatcher.py:192`. U4 is
the sole owner of `outcome_dispatcher.py` edits; U5 is a **read-only consumer** of that existing
factory and declares no dispatcher file of its own. U5's job is to wire the authority the factory
already produces into `production_worktree_processor` and its `main()` call site — nothing in the
dispatcher moves for U5.

**Test scenarios** — new file `plugins/saga/tests/test_outcome_worktrees.py`:

- `reap_worktree` with `lease_authority=None` preserves today's behavior exactly (characterization;
  must pass before and after — this is the compatibility floor for existing callers)
- `reap_worktree` with an authority whose token fails `classify_token` refuses and does **not** remove
  the worktree (red-first)
- `prevalidate_reap_authority` refuses before any filesystem mutation — assert on ordering, not just
  on the raise
- the ported `production_worktree_processor` resolves an authority and passes it to the reap path, and
  `main()`'s `advance` and `prune` wiring reaches it end to end (red-first)
- `release_authority=False` retains the lease across a successful reap
- an entry with no lease binding degrades to the documented path rather than raising
- **second reap is idempotent:** `reap_worktree` called twice on the same subplot is a clean no-op on
  the second call, not a raise and not a double release. Upstream treats `reap_worktree` as explicitly
  idempotent and its tests call it twice — port that shape rather than assuming single-shot
- **malformed receipt:** a null or structurally invalid reap receipt refuses at preflight rather than
  proceeding to removal on partial data
- **registry mutated after preflight:** a registry that changes between `prevalidate_reap_authority`
  and the removal takes the re-validation path rather than acting on the stale prevalidation — this is
  the TOCTOU window the preflight exists to close, so a test that only exercises the happy sequence
  proves nothing about it (red-first)
- **removal failure:** a filesystem removal error leaves the lease authority unreleased and surfaces
  the error, rather than releasing authority for a worktree that still exists
- **authority-release failure:** a release that itself fails is surfaced, not swallowed, and does not
  mark the reap successful

### U6. Release surfaces, inventory rebuild, and the cutover gate

Move the release surfaces, rebuild the harness-digested inventory, pass `--stage cutover`, then run
and report the cross-runtime acceptance leg.

**Scope — the codex release surfaces, whose real paths were verified, not assumed:**
`plugins/saga/.codex-plugin/plugin.json` and `plugins/fleet-core/.codex-plugin/plugin.json` (the
manifests are `.codex-plugin/`, not `.claude-plugin/`); `.agents/plugins/marketplace.json`, which
`README.md:44` identifies as **the** codex marketplace and is the only `marketplace.json` in the tree
(`find . -maxdepth 3 -name marketplace.json` returns exactly one). **Never create
`.claude-plugin/marketplace.json` in this repo** — an earlier draft named that path, and creating it
would mint a second, Claude-shaped registry beside the real one. Also: both `CHANGELOG.md` files, and
`docs/engineering-journal/DECISIONS.md` + `LEARNINGS.md`.

**Versions:** current codex values are saga `0.79.0+…` and fleet-core `0.11.0+…`. Both carry
behavior in this PR, so both bump; select the exact target versions when the diff is final and move
manifest, marketplace, and CHANGELOG together as one release unit per the runbook. The
`-version-policy.json` sibling of the U1 contract records the policy.

**Inventory rebuild (R4a):** regenerate `docs/validation/saga-family-target-inventory.json` after the
release surfaces move, and assert its recomputed sha256 against what the acceptance bundle records —
this is the unit where that comparison is meaningful, because the bundle now exists. Remember the
harness only *records* this digest; the freshness proof is this repo's own generated-file check, not
`contract_digests`.

**Cutover gate:** `port_contract.py validate --stage cutover` on the U1 contract, and
`--stage unit --unit U<n>` per implementation unit before it. Cutover additionally requires every
non-deferred row `verified` with evidence, current rationales on any surviving `defer`/`reject`, and
the `release_evidence` keys populated — `_validate_cutover_release_proof` (`:1405`) rejects a null.

**Acceptance:** the harness is `tools/run_cross_runtime_outcome_acceptance.py` in
`infiquetra-claude-plugins`, revision-pinned on both runtimes. Run it with **absolute** pin paths (the
shell cwd resets between commands in this environment) and `export TMPDIR=$(mktemp -d)` first, since
failing runs retain their workdirs.

**State the expectation honestly and do not overclaim.** `contract_digests` / `port-digest` has been
halting by design since the #627 merge, and U2's `outcome_compat.py` re-freeze is what addresses it
(`contract_digests` compares only that file — see KTD2). Separately, `#628`
(cross-runtime double dispatch) was already documenting **12/14** with `race-codex-first` and
`race-simultaneous` red. This plan does **not** claim to change those two legs. Report the leg matrix
verbatim; a leg that stays red is documented truth per R11.

**Test expectation:** none for the release-surface edits themselves (non-feature); the acceptance leg
is the evidence and is reported, not asserted green in advance.

## Risk Analysis & Mitigation

**Porting into the wrong `lease_broker.py`** is the highest-likelihood silent failure: two files share
the name, only one carries the target symbols, and a port into the 542-line saga copy would pass its
own tests while changing nothing. Mitigated by KTD6 making the determination U3's first task and by
U1's contract test asserting every `planned_target` path exists.

**A green suite read as re-freeze evidence.** Per KTD7, `outcome_compat.py` has no codex test module at
all, so the existing suite cannot detect a bad re-freeze. Mitigated by U2 creating the module and by
the explicit byte-identity diff assertion, which is the real oracle.

**Ordering-blind tests on the U4 re-raise.** A test asserting only that a non-transient error raises
will pass against an implementation that releases the lease first — precisely the defect R7 exists to
prevent. Mitigated by specifying the assertion as "per-subplot store lock still held, and no record
beyond the pre-dispatch snapshot, at the moment of raise" (R7a).

**Classification skipped or scoped too narrowly.** The runbook's gate exists to prove complete
treatment before behavior lands; a contract pinned to only the two frozen files would leave four
ported modules untreated and still pass `--stage classification`, because the gate validates the rows
the contract *has*. Mitigated by U1 pinning all five changed surfaces and by R4b promoting the
COR3 rows that no new range can produce.

**Scope creep from a discovered upstream defect.** The mirror work reads Claude's implementation
closely, which is how upstream defects surface. KTD5 and R12 make the response a stop plus an upstream
filing, not a codex-side repair.

**The saga tick sits in a committable path.** This repo's `.gitignore` covers `.codex/saga/` but not
`.claude/`, so the plan saga written by Claude's saga tooling shows as untracked and would be swept up
by `git add -A`. (`infiquetra-claude-plugins` ignores `.claude/` at `.gitignore:55`; this repo has no
equivalent line.) Mitigated for now by never using `git add -A` and staging explicit paths only. The
durable fix — adding `.claude/` to this repo's `.gitignore` — is a one-line change deliberately left
out of scope here, since it is repo configuration rather than part of the port.

## Alternatives Considered

**Three sequenced PRs (PR-A re-freeze / PR-B broker+dispatcher / PR-C COR3).** Proposed in an earlier
revision of this plan and **rejected** under KTD2 after verification: `/work` has one PR-ready boundary
per execution contract, so three PRs need three contracts and three operator runs; and the claimed
early-`port-digest`-green benefit unblocks nothing, since the acceptance harness appears in none of the
four `.github/workflows/` files. The blast-radius concern it was built on is answered by per-unit
commits plus `validate --stage unit`.

**Pin `53cd65f5` as the issue comment names.** Rejected under KTD1. It produces identical bytes, so
the only difference is that a head-pinned manifest needs no later reconciliation. Recorded as a
documented deviation rather than a silent one.

**Byte-copy every ported file from Claude.** Rejected under KTD3, and it would be actively
destructive: the codex-native modules carry behavior Claude's do not, so a copy would delete it and
`outcome.dispatch.v2` would not survive. Only `outcome_compat.py` and `audit_store.py` are byte-frozen
twins where copying is the correct mechanic.

**Defer COR3 to a separate issue.** Tempting given KTD4's resizing, and defensible. Not proposed
because #45 explicitly carries COR3 and it is the last leaf of outcome `governed-execution-integrity`;
splitting the issue would leave the outcome open on a bookkeeping technicality. R4b also settles it:
COR3's rows were already deferred once, to codex#34, which **closed without treating them** — a second
deferral would orphan them again.

## Scope Boundaries

**Out of scope — do not fix here:**

- Any further change to the Claude-side seam. This issue re-freezes and ports what
  `infiquetra-claude-plugins#627` and `#637` already merged (KTD5).
- Redesigning the refuse-mode admission contract, the `DispatcherError` halt-visibility shape, or the
  ancestor-guard exemption predicate — settled by #627's KTD1–KTD4; this issue ports them.
- `infiquetra-claude-plugins` #642 (`installed_plugins.json` staleness), #661 (lease refusal remedy
  text), #657 / #658 / #659, and the #646 / #645 / #647 lease-family defects.
- `#628` (cross-runtime double dispatch) itself — documented upstream, and its two red acceptance legs
  are expected to stay red through this work.
- Cross-clone settlement coordination (shared ledger, fleet-doctor cross-clone probe) — `#627` R7
  documents the per-clone boundary; coordination across clones stays future work.
- Any acceptance-harness redesign. The existing harness is run, not modified.

**Deferred to follow-up work:**

- Test coverage for codex `outcome_compat.py` beyond the ancestor-guard paths U2 adds. The module is
  1686 lines and this plan brings only the re-frozen surface under test.
- Reconciling the two `lease_broker.py` copies, if KTD6 finds the saga-side one is stale duplication
  rather than a deliberate subset. That is a separate cleanup with its own blast radius.
