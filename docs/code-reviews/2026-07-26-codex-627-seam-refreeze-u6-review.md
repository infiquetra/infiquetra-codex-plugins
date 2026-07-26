# Code review: codex#45 U2–U6 (#627/#637 seam re-freeze + COR3 port)

**Reviewed at:** `30a37c21750bf52111a3278dd6483f8b1c8bfd26` (U5 head) plus the U6 release-surface
diff staged on top of it.
**Scope:** the four production surfaces U2–U5 changed, plus U6's release-surface and
port-contract cutover work.

## What was checked

- Read the full production diffs for U2 (`audit_store.py`, `outcome_compat.py`), U3
  (`fleet_commons/lease_broker.py`), and U4 (`outcome.py`, `outcome_dispatcher.py`) directly
  against the plan's R2/R3/R5/R5a/R5b/R6/R7/R7a/R7b requirements.
- Confirmed byte-identity of `outcome_compat.py` against Claude `b464d090` — a plain `diff`
  shows exactly one differing line, `RUNTIME_LABEL`.
- Re-ran every unit's test module plus the wider repo suite after the U6 release-surface and
  version-drift-guard edits (**recorded at the time as "2520 passed, 4 deselected" — see the
  correction below; that figure is only partly reproducible and its pointer is dead**).

> **Correction (2026-07-26, round-4 code review).** The suite figure above does not describe the
> tree this review covers, and the reader it sends to the cutover artifact finds nothing.
> Re-measured at the reviewed commit in a clean detached worktree: the suite collects **2731** and
> runs **2727 passed, 4 skipped, 0 failed**.
>
> An arithmetic coincidence that is **not** an explanation: `plugins/mission-control/tests`
> collects exactly **211** tests, and 2731 − 211 = **2520**. A round-4 draft of this correction
> read that fit as evidence the figure came from a run excluding that path. Measurement rejects it
> on two independent grounds:
>
> - **The exclusion is not producible that way.** `plugins/*/tests` is an explicit `testpaths`
>   entry in `pyproject.toml:17`, and `--ignore` does not override an explicit testpath — measured
>   at this commit, `pytest --collect-only --ignore=plugins/mission-control/tests` collects
>   **2732**, byte-identical to the unfiltered run.
> - **It conflates collected with passed.** 2520 would be a *collected* total. The passed count
>   under that hypothetical exclusion is 2727 − 211 = **2516**, and "2520 passed" would
>   additionally require the 4 non-passing tests to sit outside the 2520.
>
> The fit is a coincidence. It is recorded here as a rejected hypothesis, not as a mechanism.
>
> What is **not** reproducible, and is not being reconciled by guesswork:
> - **"4 deselected" never happened.** Deselection requires `-k` / `-m` / `--deselect`, and no
>   recorded `argv` in `docs/portability/ports/2026-07-25-codex-627-seam-refreeze.json` carries
>   one. The suite's own 4 non-passing tests are **skipped**, not deselected — the frozen-source
>   oracles in `tests/test_codex_627_seam_refreeze_port_contract.py`, which skip only when the
>   sibling Claude clone is unresolvable. Different word, different mechanism.
> - **The pointer is dead.** `docs/validation/codex-627-seam-refreeze-u8-cutover.json` records
>   "2727 passed, 4 failed" — a different number *and* a different outcome word — and contains no
>   "deselected set" to consult. A reader following this sentence learns nothing.
>
> Treat the original figure as an unverified recollection of a partial run, not as evidence that
> the full suite was green at this commit. The clean-worktree measurement above is the figure that
> reproduces.
- Confirmed U5's already-committed evidence in the predecessor manifest
  (`docs/portability/ports/2026-07-19-lease-safe-substrate.json`, rows `src-b63c5ebf1ea04461` /
  `src-cfa1aa6b86772f6b`) independently: both rows are `state: verified` with a red-first
  20-failed/3-passed → 23-passed replay recorded.

## Findings

**U3 (`lease_broker.py`):** the refuse-mode conjunction matches R5 exactly — missing prior
supersedes, expired prior reclaims in both modes, dead owner supersedes with no TTL wait, only
live/unknown-and-unexpired refuses. `LeaseConflictError` carries `holder_owner_id` (R5a). The
two R5b precedence gates (retained settlement, canonically-closed) sit above the refuse branch,
unreordered. `acquire_agent` rejects any `on_conflict` value outside `{"supersede", "refuse"}`
at the boundary. No blocking finding.

**U4 (`outcome.py` / `outcome_dispatcher.py`):** the head-of-arm type guard
(`if not isinstance(dispatch_error, DispatcherLeaseTransientError): raise`) is placed before the
per-subplot lock release and the ledger append, matching R7. `_lease_conflict_error_type()`
declines to transient on any shim-load exception (`except Exception`), which is the fail-closed
direction R6 requires. The transient-path ledger record is built spread-first / literal-last
(`{**receipt, "receipt_kind": ..., "kind": "dispatch"}`), preserving `receipt["kind"]` under
`receipt_kind` while `"kind": "dispatch"` stays the reducer's routing key — this is exactly the
shape R7b names as the #628 invisibility-shape guard. No blocking finding.

**U2 (`audit_store.py` / `outcome_compat.py`):** both walks drop the home-scope early return and
walk from the filesystem anchor (`Path(candidate.anchor or os.sep)`) down via `lstat`, matching
R3. The world-writable refusal condition changed from `stat.S_ISDIR(mode) and mode & 0o002` to
`(mode & 0o002) and not (mode & S_ISVTX)` — this also drops the directory-only restriction, so a
world-writable non-directory component is now refused too. This is a faithful mirror of Claude's
own `b464d090` change (confirmed by the byte-identity diff on `outcome_compat.py`), not a
codex-side deviation, so it is not a finding against this port.

**One pre-existing stale test found and fixed during this review pass, not by U2's own commit:**
`tests/test_outcome_cross_runtime.py::TestHandoffStorePrivacy::test_walk_exempts_home_itself`
asserted the *old* home-scope exemption (home's own world-writable mode never refuses). U2's
change makes this assertion false under the new universal walk. Retired and replaced with
`test_walk_refuses_world_writable_home_itself` (asserts the new refusal) and
`test_walk_accepts_world_writable_sticky_home_itself` (asserts the sticky exemption still
applies to home itself, mirroring the twin audit-store boundary). This was a stale-test gap in
U2's own commit, surfaced only when the full suite ran at cutover (KTD7's exact risk: a green
suite is not evidence when the module carries no coverage of the changed contract). No
production-code finding.

**One pre-existing stale test found and fixed:**
`tests/test_outcome_dispatcher.py::test_advance_records_lease_refusal_as_halt_and_continues`
raised a bare `DispatcherError` to simulate a lease refusal and expected the halt-and-continue
posture. Under U4's new classification, a bare `DispatcherError` is non-transient and now aborts
the tick loudly (R7) — exactly the intended behavior change. Updated the fixture to raise
`DispatcherLeaseTransientError` so the test keeps exercising the halt-and-continue path it was
written for. No production-code finding.

## Verdict

CLEAN. No blocking findings against the production diffs. Two stale pre-U6 tests were found
and repaired (both testing removed behavior by design, not regressions), and the version-drift
guards (`scripts/validate_codex_plugins.py`, `docs/validation/saga-family-target-inventory.json`,
the legacy-workflow-token inventory, and two `test_codex_627_seam_refreeze_port_contract.py`
assertions written for the pre-cutover state) were brought forward to the post-cutover version
strings in this same pass.
