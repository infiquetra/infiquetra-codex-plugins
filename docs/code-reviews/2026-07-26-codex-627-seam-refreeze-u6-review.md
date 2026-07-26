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
  version-drift-guard edits (2520 passed, 4 deselected — see the cutover artifact for the
  deselected set and why each is pre-existing and out of this unit's scope).
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
