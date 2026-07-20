# Code review — #34 outcome cross-runtime parity port

- **REVIEWED_SHA:** `aef1dea` (branch `work/34-codex-parity`; code SHA `eb36744` = ceremony r2
  remediation, `aef1dea` adds only the ceremony record doc)
- **Diff base:** `3723a8183e3ea9c372ad9f34fd18f4170c36d26f` (branch point off codex `main`);
  37 files, +5568/−375, 7 commits at review time
- **Remediation SHA:** `39a9ed4` (this review's fixes; full battery re-run strictly after the
  last edit: **2572 passed**, ruff clean, `validate_codex_plugins` green)
- **Plan authority:** `docs/plans/2026-07-15-codex-cross-runtime-outcome-parity-plan.md`
  (Requirements R1–R9, KTD1–KTD6); frozen source `30bde209..97d2fb15` of
  infiquetra-claude-plugins (#604 squash, PR #622)
- **Mode:** programmatic saga:code-review — 4 always-on lenses (correctness, security, testing,
  maintainability/conventions; no conditional lens fired), Stage A dedup + confidence gate,
  Stage B one independent validator per survivor. All lens/validator agents ran read-only
  (`saga:readonly-verifier`) in disposable worktrees.

## Built-vs-planned audit

R1 (freeze/classify: port manifest, 25 source rows, zero-drift codex inventory), R2 (exact
schemas/fixtures byte-verbatim), R3 (repository identity), R4 (honest read-only cross-clone
status), R5 (protected handoff), R6 (advance-one through the native protected launched-ack
dispatcher, lease seam dormant per KTD6 — pinned by
`test_dispatcher_lease_seam_stays_dormant_ktd6`), R7 (legacy `outcome-bundle/1` retirement:
export aliases discovery, import refuses with zero writes), R8 (order-independence + no-mutation
suites): **DONE** with evidence (per-port gate 21/21, ceremony record
`docs/validation/outcome-cross-runtime-parity-ceremony.md`). R9 (release through full cutover):
**PARTIAL by sequencing** — release surfaces + gates done at `0.77.0+codex.20260720023112`;
isolated-install / fresh-session / rollback / cutover proofs are the integrate stage after QA,
exactly as the plan's workflow table orders them. Scope: CLEAN, one justified addition (the #33
cutover-gate pin converted to historical-floor form so sealed gates stay true after the 0.77.0
bump).

## Stage A — merge, dedup, confidence gate

11 raw findings across 4 lenses → 1 cross-lens duplicate merged (dead code, raised independently
by testing + correctness) → confidence gate (<75 suppressed; no P0 present):

| Suppressed | Lens | Conf | Why |
|---|---|---|---|
| Handoff dir default umask (0o755 not 0o700) | security | 50 | Pre-existing store-wide convention (`outcome_store.ensure` also default-mode); sealed records themselves are 0o600; a leaked 32-hex filename authorizes nothing. Defense-in-depth advisory → cross-runtime-acceptance owns audit/store ancestor hardening. |
| `except _cli_broker_error()` can raise RuntimeError if fleet-core unresolvable | correctness | 50 | Byte-identical to the shipped Claude source; reachable only on a non-halt exception with fleet-core absent (this repo resolves via shim rung 2). |
| Vestigial one-element loop `for flag_parser in (p_handoff,):` | maintainability | 68 | Likely faithful graft shape; harmless. |

**7 survivors** entered Stage B.

## Stage B — independent validation + resolution

| # | Finding | Lens verdict | Validator verdict | Resolution |
|---|---|---|---|---|
| 1 | `attended_handoff` zero tests (`outcome.py:1602`) | P2 conf 100 | **Reclassify P3** conf 92 — Claude shipped the identical function with identical zero coverage (checked at `97d2fb15`); inherited gap, not port-dropped | **FIXED** `39a9ed4`: `test_cli_attach_attend_prints_the_native_resume_command` drives CLI `attach --attend` end-to-end against a sealed attend offer after a real protected-launch dispatch; asserts the printed `/resume leaf-sub-2` |
| 2 | Production `_settled_lookup` + fail-closed except branch never executed (`outcome.py:1503`) | P2 conf 100 | **Confirm P2** conf 100 — full-suite branch-coverage run proved lines 1505–1524 unexecuted by any of 1442 tests; fail-direction is closed (False = refuse), hence P2 not P0/P1; inherited from Claude but real at HEAD | **FIXED** `39a9ed4`: `TestSettledLookupFactory` (4 tests) — empty dispatch-id, unprovable settlement on a real empty ledger, forced `DispatchSettlementError` → False, settled terminal attempt → True |
| 3 | Stale export/import `--help` still describes the retired bundle flow (`outcome.py:1934/1937`) | P2 conf 80 | **Reclassify P3** conf 90 — byte-identical stale strings in the frozen Claude source (its lines 2281/2284); the codex diff never touched those lines; runtime warning + refusal + CHANGELOG/SKILL docs are correct | **ROUTED UPSTREAM-FIRST**: fix in infiquetra-claude-plugins, then re-port the one-line change; patching codex alone would create deliberate drift |
| 4 | Orphaned dead code `DISPATCH_AUDIT_KIND` / `_dispatch_audit_digest` (`outcome.py:63/1678`) | P3 (testing conf 100 + correctness conf 90, merged) | **Confirm P3** conf 100 — codex-only symbols **never present upstream** (zero hits at `97d2fb15` repo-wide); callers removed by `fe063e1`; refuted the stale "live uses at 1809/1817" note (unrelated code) | **FIXED** `39a9ed4`: both deleted; `git grep` at the remediated HEAD returns zero `.py` hits; CHANGELOG Removed entry added |
| 5 | `_cli_admission` never-defaulted guard has no negative test (`outcome.py:1486`) | P3 conf 75 | **Confirm P3** conf 85 — guard is live only on the attach path (flags default None; handoff path is argparse-required); inherited identically from Claude | **FIXED** `39a9ed4`: `test_cli_attach_advance_missing_admission_flags_fails_closed` — exit 1, names `--session-id`, asserts the never-defaulted message |
| 6 | Unreachable success-print after unconditional `import_bundle` raise (`outcome.py:2209`) | P3 conf 88 | **Reclassify P3** conf 90 — identical dead print in the frozen Claude source (its lines 2624–2627); codex handler lines are unchanged carry-over | **ROUTED UPSTREAM-FIRST** (same rule as #3) |
| 7 | Weak string oracle in `test_export_is_a_discovery_envelope_alias` (`test_outcome_command.py:342`) | P3 conf 75 | **Confirm P3** conf 85 — live repro: any exception lacking the literal satisfies it; the test itself is codex-authored (no Claude equivalent), so strengthening is drift-free | **FIXED** `39a9ed4`: asserts `CompatibilityHaltError` type + `repo-identity*` halt code, keeping the substring-absence check |

## Delta adjudication of the remediation

Every applied fix is the validator-prescribed remediation, verified at `39a9ed4`:
new tests pass in-suite (127 in the two edited files; **2572 full**), the deletion is proven by
zero `git grep` hits, ruff is clean repo-wide, and the legacy-token inventory was rebuilt (the
two edited files are active-classified entries; the pinned internal historical digest
`42c16a25…` is unchanged, so no pin re-bind). No behavior of the ported surface changed: edits
are test additions, a docs entry, and the removal of provably unreferenced symbols. Zero new
findings introduced.

## Verdict

**CLEAN.** No open P0–P2. Open P3 dispositions: #3/#6 routed upstream-first (byte-identical in
the frozen Claude source — codex-only patches would violate port fidelity), plus the three
sub-threshold advisories recorded in Stage A. Cross-runtime-acceptance already owns the
directory-mode/audit-store hardening seam (KTD6 deferral).

## Saga

No active work-thread saga exists in this repo's store for #34 (scan-first, never mint — the
leaf is tracked as `leaf-lease-safe-runtime-continuity-codex-parity` in the outcome ledger of
infiquetra-claude-plugins); the `review_paths` append is therefore recorded at harvest, not
here.
