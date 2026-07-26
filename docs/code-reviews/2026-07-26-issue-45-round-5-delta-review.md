# 2026-07-26 — codex#45 round-5 delta code review

**Scope.** Delta re-review of PR [#53](https://github.com/infiquetra/infiquetra-codex-plugins/pull/53),
branch `work/45-codex-refreeze-627-seam-cor3`, reviewed at `60c74de` against base `f79f141b`. This
reviews the **repair commit only** (`60c74de`, 34 files, +1158/−74) and adjudicates the prior
round's findings. The prior review is
`docs/code-reviews/2026-07-26-issue-45-codex-627-seam-refreeze-code-review.md` (verdict **BLOCKED**,
0 P0 / 8 P1 / 12 P2 / 11 P3).

**Verdict: CLEAN.** All 8 prior P1s adjudicated RESOLVED, none REGRESSED. One new P2 was found in
the repair commit itself and repaired during this review; one P3 was found and repaired. No P0.

## Part A — adjudication of the prior P1s

| ID | Claim under repair | Adjudication | How it was verified |
|---|---|---|---|
| P1 #1 | CHANGELOG claimed the transient path "settles the attempt" | **RESOLVED** | String absent from `plugins/saga/CHANGELOG.md`; a `### Deferred` section now names the boundary |
| P1 #2 | Same claim in port row `src-3b34fc68149a7c76` at `state: verified` | **RESOLVED** | Rationale now states the deferral. `settle_attempt(` has **0** call sites in codex `outcome.py`; the 3 settlement-family references are the unrelated `_settled_lookup`. The behavior was **not** ported, which is correct — porting it would have been the P1 #5 defect class |
| P1 #3 | Three tests decided by collection order | **RESOLVED** | See below — verified by permutation *and* by removing the fix |
| P1 #4 | Both CHANGELOGs claimed red-first for units with no such artifact | **RESOLVED** | Exactly one `docs/validation/*.json` carries a `red_first` block (`lease-safe-substrate-u6.json`, at `/check/red_first`: pre_port "20 failed, 3 passed" → post_port "23 passed", `replayed_with_final_test_file: true`). Both CHANGELOGs now state "post-port results only" for U2/U3/U4 |
| P1 #5 | `outcome_decompose.py` in zero contract rows | **RESOLVED** | pathspecs 6, `expected_count` 6, rows 6; `base_ref` still `cf15a09f…` so the frozen range did **not** move; all five prior `row_id`s preserved byte-identical, none lost; the new row is `codex-adapt` / `["U5"]` / `verified` backed by `u5-codex-627-seam-refreeze-decompose-check-20260726` |
| P1 #6 | — | **WITHDRAWN by the prior reviewer**; not resurrected | — |
| P1 #7 | `repo_head` names a tree lacking its own test file | **RESOLVED** | `repo_head` `d00b81da` retained (it *is* the head the run executed against), `replayable_from: 30a37c21` added, and a 769-char `note_on_provenance` states plainly that the tree did not contain the module under test. Honest rather than merely different |
| P1 #8 | "2520 passed, 4 deselected" cannot describe a 2731-test suite | **RESOLVED**, but the repair carried a new defect — see finding R5-1 | — |
| P1 #9 | R7a's coordinator-lock claim untested | **RESOLVED** | See below |

### P1 #3 — verified in both directions

Permutations at `60c74de`: worktrees→board_sync **62 passed**, board_sync→worktrees **62 passed**,
worktrees alone **23**, board_sync alone **39** (23 + 39 = 62). Order-independent.

Passing permutations alone would not prove the fixture is what does the work, so the fix was
removed in a disposable worktree and the suite re-run: **3 failed, 59 passed**, and the three
failures are exactly the three originally reported
(`test_production_worktree_processor_resolves_the_default_broker`,
`test_main_advance_wires_an_authority_carrying_worktree_processor`,
`test_main_prune_wires_the_default_lease_authority`). The fixture is load-bearing, not a no-op that
passes by luck.

The "identity without sharing" claim holds: `monkeypatch.setitem` restores the prior binding on
teardown, each module keeps its own `_LOADED` generation, and the full suite runs all 18 modules in
one process at 2728 passed / 0 failed. Nothing shares a module object the way the rejected
memoization attempt did.

### P1 #9 — the test pins what it claims to

`test_non_transient_abort_releases_the_coordinator_lock` enters through `OUTCOME.advance()`, not
`_reconcile_once` (that name appears only in the docstring, explaining why the sibling tests are
insufficient). It asserts the coordinator lease record is gone, then — correctly recognizing that
this is necessary but not sufficient — re-enters `advance()` under a **different holder** and
asserts the tick actually ran (`skipped_busy is False`, `ticks >= 1`), which a lease left in an
unacquirable state would fail. The docstring is explicit that the second tick deliberately does not
assert a re-raise, and why: the intent-dedup arm short-circuits before the dispatcher.

## Part B — defects found in the repair commit

### R5-1 (P2, repaired during this review) — a refuted hypothesis presented as reproducible

`docs/code-reviews/2026-07-26-codex-627-seam-refreeze-u6-review.md` stated, under the heading
"What *is* reproducible", that `2731 − 211 = 2520` and therefore "the passed-count almost certainly
came from a run with that one path excluded."

Measurement rejects that on two independent grounds:

1. **The exclusion is not producible that way.** `plugins/*/tests` is an explicit `testpaths` entry
   (`pyproject.toml:17`), and `--ignore` does not override an explicit testpath. Measured at this
   commit: `pytest --collect-only --ignore=plugins/mission-control/tests` collects **2732**,
   identical to the unfiltered run.
2. **It conflates collected with passed.** 2520 would be a *collected* total; the passed count
   under that hypothetical exclusion is 2727 − 211 = **2516**.

This is the marginal-fabrication pattern the whole PR exists to remove — an arithmetic fit promoted
to a mechanism — and it had survived into the committed record under a heading asserting
reproducibility. Repaired: the coincidence is now recorded as an explicitly **rejected hypothesis**
with both refutations, and the coupled `u8-review-20260726.artifact_sha256` was refreshed.

### R5-2 (P3, repaired during this review) — two variants of a fixture claimed byte-identical

`_load` was byte-identical across all 18 modules, but `_pin_script_modules` had **two** distinct
bodies (8 files / 10 files). The divergence was docstring prose only — the executable body was
identical, so there was no behavioral risk — but the weaker variant omitted the "this pins identity,
it does not share it" clause, which is the load-bearing rationale a future reader needs. Unified;
now 1 distinct body across 18 files.

## Verified-not-defects

- **The manifest renormalization is semantically inert.** `2026-07-25-codex-627-seam-refreeze.json`
  was re-emitted at `indent=2, sort_keys=True` (the repo convention, which both manifests round-trip
  exactly) after a tool writeback had emitted 1-space. Parsed-object comparison against `d9e345d4`
  shows exactly the intended delta and nothing else: +1 row, changed rationale on one row,
  +1 evidence entry, two refreshed artifact digests, pathspecs 5→6, `expected_count` 5→6, refreshed
  `inventory_sha256`.
- **The predecessor manifest carries a one-line change.** `2026-07-19-lease-safe-substrate.json`
  differs from `HEAD` by exactly one line — `evidence[9].artifact_sha256` for
  `u6-cor3-worktree-authority-check-20260726` — required because `lease-safe-substrate-u6.json` was
  edited by the P1 #7 repair. Nothing else rode along.
- **Every digest matches disk.** All evidence `artifact_sha256` and all authority `sha256` values in
  both manifests were recomputed against the working tree: **0 stale**.
- **The corrected cutover explanation is true.** This was its third revision, so it was checked
  directly rather than read. `external_action_release_matrix.py:697-701` reads the proof's own
  `content_sha256`, pops it, rehashes and compares; the artifact is a cross-runtime acceptance
  record with no such field, so the verifier raises there and `_validate_expected_ref` (`:716-720`)
  never runs. The tag `refs/tags/evidence/codex-627-seam-refreeze-20260725` is also absent, but that
  is an unreached second blocker. Running the verifier against the artifact's pre-repair `HEAD`
  version yields a byte-identical error, proving the round-4 edits neither caused nor changed it.
- **The inventory coupling holds.** `LEGACY_WORKFLOW_HISTORICAL_INVENTORY_SHA256`
  (`scripts/validate_codex_plugins.py:286-288`, a parenthesized multi-line literal) equals
  `historical_inventory_sha256` in the inventory JSON; 135 entries.

## Gates at review time

| Gate | Result |
|---|---|
| Full suite, clean detached worktree @ `60c74de` | **2728 passed, 4 skipped, 0 failed** (baseline 2727/4/0; +1 is the new coordinator-lock test) |
| Affected modules after the review repairs | 654 passed |
| Collection-order permutations | 62 / 62 / 23 / 39 |
| Fix-removed control | 3 failed, 59 passed — the original three |
| `ruff check` | clean |
| `ruff format --check` | 124 at head and at base, identical sets — not this branch's |
| `mypy plugins/ scripts/ tests/` | 1 error, byte-identical to base |
| `validate --stage classification` | valid |
| `validate --stage unit` U2/U3/U4/U5 | valid |
| `validate --stage cutover` | **BLOCKED**, pre-existing and correctly not cleared |
| Digest audit, both manifests | 0 stale |

## Standing blockers, deliberately not cleared

- **`--stage cutover`.** Structural: the gate only fits external-action ports. Clearing it would
  require fabricating an external-action release run. Documented in `DECISIONS.md`.
- **R7b(c) "settle the attempt"** is an explicit named deferral, not an implied capability.
- **No claim that #45 fixes #628.** The two race legs that flipped are reported with hedged
  causation, correctly not strengthened.

## Note on the review environment

This repo has **no CI** — `.github` exists, `.github/workflows` does not. Every gate above is
local-only; nothing catches a regression after merge.

This session has `INFIQUETRA_FLEET_LEASE_ENFORCEMENT=off` set (a deliberate operator kill-switch).
Any full-suite run in the sibling Claude repo shows 17 failures in `tests/test_saga_hooks.py` caused
solely by that variable — with it unset the same file is 44 passed. Those are neither this branch's
nor this repo's, and are excluded from this review.
