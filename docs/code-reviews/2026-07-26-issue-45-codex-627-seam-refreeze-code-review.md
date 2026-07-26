# Code review — infiquetra-codex-plugins#45

- **Target:** branch `work/45-codex-refreeze-627-seam-cor3`, repo `infiquetra/infiquetra-codex-plugins`
- **Reviewed SHA:** `d9e345d4e21019f8bc7dccb7e1ce02ba3c26f084`
- **Diff base:** `f79f141b391589b413b25dc6775a32ff5e7e2e26` (verified `git merge-base origin/main HEAD` after fetch; `origin/main` == base, unmoved)
- **Plan:** `docs/plans/2026-07-25-codex-refreeze-627-seam-and-cor3-worktree-authority-plan.md`
- **Doc review:** `docs/reviews/doc-review-issue-45-2026-07-25.md` (12 findings, all resolved pre-build)
- **Scope:** 52 files, +6447/−162, 10 commits. Untracked `.claude/` excluded from review per Phase 0.2.
- **Mode:** programmatic / report-only. Zero writes to reviewed code; zero ledger writes.
- **Verdict:** **BLOCKED** — P1 findings remain.
- **Scope Check:** DRIFT DETECTED (one production module ported outside any contract row) + REQUIREMENTS MISSING (R7b(c), R10 for 3 of 4 units).

## Method note

Deterministic questions were answered by direct measurement in the driver rather than delegated:
byte-identity oracles, symbol counts, gate exit codes, tag existence, contract-row coverage. Five
opus lenses (U3 admission, U4 ordering, testing, U5/COR3, evidence integrity) covered the judgment
work, each in a read-only sandbox against a clean detached worktree at the reviewed SHA. Every P0/P1
lens claim was independently re-measured by the driver before inclusion; three lens claims had their
supporting facts corrected (noted inline). Tree integrity verified after the run: codex primary
carries only `?? .claude/`, the review worktree is clean, and the upstream Claude clone is unmoved at
`77e11ac1` with the operator's dirty files untouched.

---

## Built vs planned

**Intent:** re-freeze the cross-runtime seam at Claude `b464d090` and port two lease-authority
mechanisms codex lacks entirely, turning the `port-digest` acceptance leg green.

**Delivered:** exactly that, plus two substantive robustness ports. The core technical objective is
**met and independently proven**. The defects are concentrated in *claims about the work*, not the work.

### Plan-completion audit

| Req | State | Evidence |
|---|---|---|
| R1 pin `b464d090`, record equivalence | **DONE** | manifest rationale states `8882bdc2 == 53cd65f5 == b464d090` |
| R2 `outcome_compat.py` byte-identical | **DONE** | 1700 lines both sides; identical after the harness's own `RUNTIME_LABEL` normalization; exactly 1 differing line (`:83`) |
| R3 `audit_store.py` ancestor walk | **DONE** | `S_ISVTX` 0→2, `is_relative_to` 1→0, `anchor` 0→1, `resolve(` 2→1 |
| R4 contract bootstrap + classification gate | **DONE** | `--stage classification` exit 0; `expected_count` derived (5 rows) |
| R4a inventory rebuild + digest assertion | **DONE** | actual sha256 `307abbde…` matches the value asserted in the cutover summary |
| R4b promote the orphaned COR3 defers | **DONE** | promoted to `codex-adapt` claiming predecessor-U6 (= plan U5); `outcome.py` re-justified as `defer`; unit-id collision navigated correctly |
| R5/R5a/R5b refuse-mode admission | **DONE** | three-arm conjunction verbatim; closed-value gate ahead of the lock; precedence gates unreordered |
| R6 typed transient + shim-safe classify | **DONE** | fails closed on shim load failure |
| R7/R7a re-raise before release/write | **DONE** | zero executable statements between `except` and `raise`; ordering genuinely pinned by a snapshot spy |
| **R7b transient path** | **PARTIAL** | release-lock ✅ + reducer-visible halt ✅ + **settle the attempt ❌ not implemented** |
| R8 COR3 at the processor seam | **DONE** | authority constructed in `production_worktree_processor`; subparsers untouched; dispatcher not forked |
| R9 release surfaces | **DONE** | saga 0.80.0 / fleet-core 0.12.0 match their CHANGELOGs |
| **R10 red-first** | **PARTIAL** | genuine `red_first` block exists for **U5 only**; absent for U2/U3/U4 |
| R11 report the leg matrix verbatim | **DONE** | 15 legs recorded; overall `fail` recorded honestly |
| **R12 / KTD5 no codex-first fix** | **DONE** | codex carries **zero** `isolation` occurrences (Claude: 21 + 6) |

`COMPLETION: 13/15 DONE, 2 PARTIAL, 0 NOT-DONE, 0 CHANGED, 0 UNVERIFIABLE`

---

## P1 findings

**#1 — CHANGELOG asserts a requirement half that was never implemented.**
`plugins/saga/CHANGELOG.md:13` — "…appends a reducer-visible `(dispatch, halt)` record, **and settles
the attempt**." Codex `outcome.py` has 3 settlement-family references, all inside an unrelated
`_settled_lookup`; Claude `b464d090` has **67**, including the `dispatch_settlement.settle_attempt(…
SILENT_NOOP)` call at `:1708` this port omits. `_reconcile_once` has no settlement binding at all.
*Three lenses independently agree.* Route: `safe_auto` → release.

**#2 — Port-contract row `state: verified` certifies the same unported behavior.**
`docs/portability/ports/2026-07-25-codex-627-seam-refreeze.json` row `src-3b34fc68149a7c76`, rationale
ends "…and settles the attempt." A future re-freeze chaining off this manifest will treat
settle-on-transient as already landed. Route: `gated_auto` → human.

**#3 — Three new tests fail depending on collection order.**
Reproduced by the driver: `test_outcome_worktrees.py` + `test_outcome_board_sync.py` → **3 failed**;
reversed → **62 passed**; alone → **23 passed**. `_load()` re-execs each script and overwrites
`sys.modules[name]`, so the last loader wins while captured globals point at orphaned modules. The
suite is green by alphabetical accident. With no CI, this lands on a human as a phantom regression.

**#4 — Both CHANGELOGs claim red-first for units that have no red-first artifact.**
`plugins/saga/CHANGELOG.md:26` and `plugins/fleet-core/CHANGELOG.md:24` assert red-first for U2/U3/U4.
Only `docs/validation/lease-safe-substrate-u6.json` carries a `red_first` block (U5: `pre_port
"20 failed, 3 passed"` → `post_port "23 passed"`, with `replayed_with_final_test_file: true`). The
`u2`/`u3`/`u4` artifacts have no such key, and no work-session record for #45 exists.

**#5 — `outcome_decompose.py` ported with a behavior change, in zero contract rows.**
Claude's copy changed +4/−2 inside the frozen range, so it would have produced a row had it been
passed as a pathspec; R4/U1 passed five and omitted it. The codex port adds a fail-closed
`prevalidate_reap_authority` before the graph mutation and a `lease_authority` parameter on `prune()`.
Zero occurrences in the new manifest, zero matching rows in the predecessor. **This is exactly the hole
KTD8 says the gate exists to prevent** — and `--stage classification` exits 0 regardless, because it
validates the rows the contract *has*. The port itself is faithful.

**#6 — WITHDRAWN. The cutover-gate rationale is sound; my earlier characterization of it was wrong.**
I initially recorded this as "U6's stated reason is wrong." Reading the actual DECISIONS entry rather
than relying on recall, that is not defensible and I withdraw it. The entry:
(a) states the check is invoked **unconditionally** — it never claims otherwise;
(b) enumerates its requirements including "a git tag whose tree contains the exact proof file" — so
the missing tag was known, not overlooked;
(c) claims no manifest has ever cleared it — **verified true**, 7/7 exit 1;
(d) claims #45 is the first to reach this check — **verified true**, the other six fail earlier;
(e) declines to fabricate an external-action release run to satisfy it, calling that "gaming the gate,
not passing it" — the correct call;
(f) correctly notes `port_contract.py` has no Claude twin, so this is codex-side, not a KTD5 boundary.
The gate is genuinely blocked, and that is honestly documented. **This belongs in the credit column.**
What survives as findings are two narrow inaccuracies inside that entry — see #32 and #28.

**#7 — The one red-first artifact records a head where its own test file does not exist.**
`lease-safe-substrate-u6.json` records `repo_head: d00b81da`; `git cat-file` reports the test file
"exists on disk, but not in 'd00b81da'" — it is added by `30a37c2` (03:11:38Z). `recorded_at` is
03:02:50Z, between `d00b81d` (02:39:18Z) and `30a37c2`. The run was on an uncommitted tree. The result
reproduces; the provenance field cannot be right. This artifact is the sole evidence for two rows
promoted to `verified`.

**#8 — U6 self-review's suite figures cannot describe the tree it reviewed.** *(confidence 75)*
Claims "2520 passed, 4 deselected"; the suite collects **2731** and runs 2727 passed / 4 skipped.
2520+4 leaves a 207-test gap. The cutover artifact it points at records "2727 passed, 4 failed" — a
different number *and* a different outcome word — and contains no "deselected set" to consult.
*The cause is undetermined; a proposed explanation (mission-control excluded) was tested and refuted —
that path collects zero tests.*

**#9 — The coordinator-lock half of R7a is untested.**
R7a makes three lock claims for the loud abort. Two are pinned. The third — the coordinator lock is
released by the outer `finally`, so a permanent fault never wedges the coordinator — has no test: all
three non-transient tests call `_reconcile_once` directly and bypass `advance()`. The implementation
is correct; the requirement is unpinned, and regressing it would strand the whole outcome.

## P2 findings (abbreviated)

**#10** `u4.json` oracles 26–27 assert settlement properties no test in its own `check.argv` exercises,
paired with `exit_code 0 / "75 passed"` (3-lens agreement).
**#11** The repeated-transient test is a tautology — tick 2 short-circuits on the intent-dedup arm and
never reaches the dispatcher, so append-once is never challenged (2-lens agreement, probe-verified).
**#12** *(pre-existing)* Three sibling halt arms build literal-first/spread-last, so `HaltReceipt`'s
`kind:"halt"` overwrites `kind:"dispatch"` and the reducer at `outcome_store.py:513` never matches.
**The #628 invisibility shape is fixed for the transient arm only.** U4 documented and pinned this
rather than hiding it.
**#13** *(pre-existing)* A foreign-root lease receipt raises out of `reconcile_worktree_leases`, and
`advance()` has `try:`/`finally:` with **no `except`** at that indent — the whole coordinator tick dies.
The sibling drift-detect call at `:1100-1105` *is* guarded (`never tick-fatal`). Relevant to the known
`.claude` / `.claude-company` plugin-tree skew. Byte-identical to Claude → upstream-first.
**#14** `uv run pytest` (the command this repo's own `CLAUDE.md` prescribes) fails collection with 11
import errors; only `python -m pytest` or `PYTHONPATH=.` yields 2731 collected. No root `conftest.py`.
**#15** *(pre-existing)* The four frozen-source oracles skip when the Claude clone is absent — i.e. in
exactly the disposable-worktree isolation this org mandates — and there is no CI backstop.
`CODEX_PORT_SOURCE_REPO=<clone>` already resolves them (36 passed, 0 skipped).
**#16** Cutover evidence says "12/14" three times and claims parity with the #628 baseline; its own
matrix records **13 of 15** (port-digest is the added 15th leg and passes). It understates its result.
**#17** `gates.cutover_stage` records "pending this artifact's own evidence entry, then green" — a
prediction, now falsified.
**#18** `gates.full_suite` records "4 failed"; the reviewed tree is 4 *skipped*, 0 failed.
**#19** `note_on_pre_existing_failures` cites `git stash` as confirmation about an **untracked** file;
plain `git stash` does not touch untracked files.
**#31** The cutover evidence row records `argv: ["python3","tools/run_cross_runtime_outcome_acceptance.py"], cwd: "."`.
There is no `tools/` directory in the codex repo; the harness lives in `infiquetra-claude-plugins`.
Anyone replaying the port's most load-bearing evidence gets "No such file or directory".
**#32** The DECISIONS entry's precedent claim is **refuted by two of its own three citations**. It
states all three prior manifests tag release evidence `"unit": "U8"`. Measured: `2026-07-10-saga-07517`
does; `2026-07-19-lease-safe-substrate` and `2026-07-19-outcome-cross-runtime-parity` both tag **U5**,
and `port_contract.py` itself reports so (five `must reference U8` errors each). The U8 convention has
exactly one precedent, not three — which is a *stronger* argument for following the tool literally.

## P3 findings (abbreviated)

**#20** U5 added a docstring claiming "every tick reconciles, reaps, and provisions under a proven
lease"; `attached_advance` calls `advance()` with no worktree processor. *(A lens attributed this to a
codex-native surface — measured, both runtimes have `attached_advance` and both bypass; only the
claim is codex-added.)*
**#21–23** *(pre-existing)* Lenient reader quarantines the registry before the strict reader sees it
(measured: corrupt registry silently `os.replace`d, harvest returns clean-empty); lease-release failure
discards its cause (`except … LeaseBrokerError:` binds no name); the transient comment promises a
re-attempt the intent-dedup arm makes impossible.
**#24–27** Module-global `request_store` couples six tests; signature-gated assertions can vanish
silently; the second-reap test cannot detect a double release; a vacuous directory loop in the
planned-artifacts guard.
**#28** The DECISIONS entry attributes the hard-coded `"U8"` literal to `_validate_cutover_release_proof`.
`port_contract.py` has five `U8` occurrences: `:398/:408/:418` seed new manifests with `release_unit: "U8"`
(a *different* field), and `:1379-1380` is the validating check `if evidence_by_id[…].get("unit") != "U8"`,
inside `validate_manifest`, which runs at **every** stage. `_validate_cutover_release_proof` (`:1405-1458`)
contains none. This matters because the entry's own "Revisit when" tells a future reader to grep that
function — the instructed check returns empty and reads as "constraint removed". *(Note: the `:398/:408/:418`
scaffolding defaults make the entry's "fixed evidence-label convention baked into the shared tool" framing
more defensible than the precedent error in #32 suggests.)*
**#29** `target_reachable: false` is recorded honestly, but the test asserting that invariant
(`test_codex_runtime_capability_snapshot.py:57`) is pinned to a *different* snapshot file, so nothing
guards the value for this port.
**#30** `acceptance_bundle_sha256` has no preimage anywhere in either repo — one grep hit, the line
itself. It reads as a verifiable anchor and cannot be recomputed.

---

## Verified correct — recorded so a later pass does not re-derive

- **`outcome_compat.py` byte re-freeze is exact.** The `port-digest` green leg is genuine: the check
  has exactly one failure condition and the file satisfies it with one permitted divergence.
- **KTD5 holds.** Codex was not patched to accept Claude's `isolation` field to make the run greener.
- **`outcome_worktrees.py` is byte-identical to Claude except 7 added comment lines.** All nine COR3
  symbols are semantically identical; codex is nowhere more permissive on the authority-proving path.
- **U3 is clean on all seven audited contract elements**, including closed-value rejection of `None`
  and `""` (a check admitting `None` would fail open on a fail-closed path) and single-clock threading.
- **The TOCTOU window is genuinely tested** — the registry is mutated *between* prevalidation and
  removal, not merely in a happy sequence.
- **The R7 ordering test really pins ordering**, and the ledger-assertion trap the plan warned about
  was avoided: it asserts snapshot-equality, not emptiness, and a sibling test asserts the pre-dispatch
  intent *survives*.
- **`important_finding_not_worked_around` is honest work.** It hedges the race-leg causation with
  "plausibly" rather than claiming #628 was fixed, root-causes the new red legs to Claude #616,
  confirms by grep against both pinned clones, and routes upstream per KTD5/R12. Every factual claim
  in it reproduces under independent measurement.
- **U5's red-first record is rigorous** where it exists — it names which three tests were expected to
  pass pre-port and records `replayed_with_final_test_file: true`, guarding the "wrote the test after
  the fix" failure mode.

## Additional verified-correct (lens-evidence, all recomputed at the reviewed SHA)

- **All 13 recorded digests in the manifest recompute exactly** — 8 evidence `artifact_sha256` values,
  `authority.plan`, `authority.runbook`, both capability-snapshot digests, and the doc-review sha256.
  Zero mismatches.
- **All four recorded pytest results reproduce exactly**: U2 34 passed, U3 68 passed, U4 75 passed,
  COR3 23 passed.
- **Every line-count and symbol claim in the five row rationales is accurate** — including the quoted
  saga-side `lease_broker.py` docstring, the `DispatcherError ×11` count, and `_reconcile_once` at
  codex `:1148` / Claude `:1097`.
- **The COR3 promotion premise is structurally correct**: `outcome_worktrees.py` has zero changed lines
  across `cf15a09f..b464d090`, so promotion really is the only available treatment. codex#34 closed
  2026-07-20 (confirmed via `gh`), matching the rationale.
- **The isolated-install evidence is corroborated by a tracked artifact** — `saga-family-codex-proof.md`
  carries the same `run_id 20260726T032219Z` and "Codex CLI commands executed: true".
- **The version-policy sibling is clean** and enforced by a shipped test asserting
  `target_codex_version == installed.split("+codex.")[0]` for both plugins.
- **The four frozen-source oracles all pass when actually run** (`CODEX_PORT_SOURCE_REPO=<clone>` →
  21 passed, 0 skipped).

## Coverage

- 31 findings after fingerprint dedup; **0 P0, 8 P1, 12 P2, 11 P3**. 8 marked `pre_existing`.
  One finding (#6) was **withdrawn by the driver** after re-reading the source it challenged.
- Cross-reviewer agreement: the settle-the-attempt cluster was found independently by three lenses;
  the repeat-transient tautology by two.
- Three lens findings had incorrect supporting facts corrected by driver re-measurement (a "no
  conftest.py anywhere" that is false, a "Claude has no `attached_advance`" that is false, and a
  mission-control exclusion hypothesis that is refuted). All three conclusions survived; their
  evidence did not.
- **Declared gap:** the pre-port red-first split for U5 was not independently replayed — doing so
  requires mutating git commands the read-only sandbox correctly refuses. The post-port figure
  (23 passed) was reproduced.
- Residual risk: this repo has **no CI**. Every gate here is local-only and nothing catches a
  regression after merge.

## Routing

Back to `/work` for P1 repair, then re-review the delta. Nothing pushed, no PR, no merge at the time
of writing.

**Repair status.** Routed to `/work` round 4 the same day. All eight P1s are dispositioned and the
non-gating P2s in the same artifacts were swept — see
`docs/work-sessions/2026-07-26-issue-45-code-review-p1-repairs.md` for the per-finding table, the
gate deltas, and two corrections to *this* review: **#18 is withdrawn** (its target figure was
correct for the tree it was measured in — this review compared it against a clean-worktree number),
and **#31 is recorded rather than repaired** (the fix was rejected by the validator; the harness's
real path is inexpressible in that evidence schema).

The verdict above is deliberately left as **BLOCKED**: it is the finding of the review at
`d9e345d4` and is not retroactively edited to reflect later repairs. Re-review the repaired tree to
change it — which is the same provenance discipline finding #7 is about.
