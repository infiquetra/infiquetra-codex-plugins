# Code review — PA-2 seam activation + re-port (#43)

- **Branch**: `work/43-pa2-seam-activation` (worktree `.worktrees/work-43-pa2`)
- **REVIEWED_SHA**: `a6d5e51` (diff base `d29e75fd` = origin/main)
- **Remediation SHA**: `ecbdaab` (delta-adjudicated below)
- **Scope**: PA-2 of the cross-runtime-acceptance plan (`docs/plans/2026-07-15-cross-runtime-outcome-acceptance-plan.md`
  on the infiquetra-claude-plugins outcome branch, section "Pre-acceptance production units"):
  KTD8 lease-seam activation at both `make_dispatcher` sites, `outcome_compat.py` re-freeze
  byte-faithful to Claude `794b4da6` (`RUNTIME_LABEL` sole divergence), audit-store ancestor
  hardening re-port, release surfaces at saga `0.78.0+codex.20260720120109` /
  fleet-core `0.10.0+codex.20260720120109`.
- **Mode**: programmatic review (plan right-sizing decision — not the six-lens ceremony), per the
  acceptance plan's PA-unit gate. Upstream-first discipline per plan KTD7.
- **Saga**: no work-thread saga exists in this repo for #43 (Claude-direct execution under
  outcome `lease-safe-runtime-continuity`, leaf `cross-runtime-acceptance`); scan-first,
  never mint — recorded here and harvested leaf-side.

## Process

Stage-A: three parallel review lenses (CORRECTNESS, TESTING, SECURITY) over the full
`d29e75fd..a6d5e51` diff plus the seam's blast radius. 15 findings survived consolidation.

Stage-B: one adversarial validator per survivor (15 total; `saga:readonly-verifier`, worktree
isolation, refute charter, JSON verdicts). **15/15 upheld as valid — zero invalid findings** —
with one fix rejected outright, one severity downgrade, and five fix refinements. Every verdict
was evidence-backed (independent reproduction, base-commit differential runs, or byte-identity
proofs); two validators corrected factual errors in their lens's evidence (T8: 14 not 16 twin
tests, full suite 2589 not 2574 at `a6d5e51`; T7: the failing mechanism is a `PermissionError`
at `os.open`, not a 0o400 file).

## Verdict ledger

| ID | Finding (short) | Lens sev | Stage-B | Conf | Fix | Disposition |
|------|-----------------------------------------------|----------|-------------|------|---------|-------------|
| COR1 | uncaught DispatcherError wedges reconcile tick | P1 | valid P1 | 92 | modify | codex-local: halt-record arm (never an ack — the reducer's ack catch-all settles) |
| COR2 | attach --advance splits lease registries | P2 | valid P2 | 90 | endorse | codex-local: reuse the handoff broker |
| COR3 | prune lease-authority site unported | advisory | valid P3 | 92 | endorse | record-only → #43 parity-backlog comment (worktree-lease layer port unit) |
| SEC1 | supersede-on-acquire ≠ mutual exclusion | P1 | valid P1 | 90 | endorse | prose de-overclaim codex-local; semantic core upstream (#627 Finding 1) |
| SEC2 | resolve() disarms ancestor walk out-of-home | P2 | valid P2 | 92 | modify | upstream (#627 Finding 3; byte-identical to 794b4da6); NFS/SMB + FAT32/exFAT caveats recorded |
| SEC3 | group-writable ancestors accepted (gid 20) | P3 | valid P3 | 75 | **reject** | accepted-tradeoff advisory: boundary deliberately test-pinned in PA-1 (#624); `& 0o022` would break setgid team dirs. Footnote on #627, no change |
| T1 | activation pin mutation-survivable | P1 | valid P1 | 90 | endorse | codex-local: AST-walk pin |
| T2 | behavioral pin not differential (passes at base)| P2 | valid P2 | 95 | endorse | codex-local: CLI recorder oracles (validator prototyped) |
| T3 | real-lease test escapes sandbox via env prec. | P2 | valid P2 | 95 | endorse | codex-local: pin INFIQUETRA_FLEET_STATE_DIR |
| T4 | pin docstring contradicts its own behavior | P2 | valid P2 | 95 | modify | folded into T1's rewrite |
| T5 | compat guard coverage weaker than its twin | P2 | valid P2 | 90 | modify | codex-local: mirror all six uncovered arms (validator widened the lens's three) |
| T6 | 3 of 6 audit-store tests non-differential | advisory | valid P3 | 95 | modify | scope-guard comments ride T8's merge |
| T7 | 0o600 assertion umask-sensitive | P2 | valid **P3** | 88 | modify | codex-local test-side umask pin only (production chmod frozen; umask only clears bits — no permissive escape) |
| T8 | duplicate audit-store test file | P3 | valid P3 | 80 | endorse | codex-local: merge into plugins/fleet-core/tests/, delete duplicate |
| T9 | eager default_lease_authority() path untested | P3 | valid P3 | 92 | endorse | codex-local: CLI failure-path pin; confirmed distinct from COR1 (construction-time vs mid-loop) |

## Remediation delta (`a6d5e51..ecbdaab`)

All twelve codex-local dispositions repaired in one commit; each verified by the new or
rewritten pins named below, full battery green after.

1. **COR1** — `plugins/saga/scripts/outcome.py` reconcile loop: new
   `except outcome_dispatcher.DispatcherError` arm (release per-subplot lock, durable
   `(dispatch, halt)` record, continue tick). Pin:
   `test_advance_records_lease_refusal_as_halt_and_continues` (also asserts
   `reduce_dispatch_ledger` derives `halted=True, settled=False` — see the reducer-visibility
   note below).
2. **COR2** — attach arm passes `lease_authority=broker` (the `_cli_broker(args.broker_root)`
   instance). Pin: `test_cli_attach_advance_reuses_the_handoff_broker_for_dispatch`
   (identity assertion through the CLI).
3. **T1+T4** — `test_dispatcher_lease_seam_is_active_ktd8` rewritten as an AST walk over
   `make_dispatcher` call nodes requiring the `lease_authority` keyword (`built >= 2`,
   `wired == built`, honest docstring). Kills the M3 mutation (comment-out survives text
   counts; fails the AST pin).
4. **T2** — differential CLI oracle
   `test_cli_advance_wires_default_lease_authority_into_dispatch` (recorder through
   `OUTCOME.main`; fails at `d29e75fd`, passes at HEAD).
5. **T3** — `INFIQUETRA_FLEET_STATE_DIR` pinned to `tmp_path` in
   `test_default_lease_authority_takes_and_releases_a_real_lease` (env-precedence escape
   closed).
6. **T7** — deterministic umask around the `_write_once` 0o600 assertion.
7. **T5** — `TestHandoffStorePrivacy` extended with all six previously uncovered arms:
   uninspectable ancestor (typed halt), group-writable acceptance (scope guard),
   home-itself exemption, relative-path normalization, regular-file-at-store-path,
   foreign-uid store dir.
8. **T8+T6** — `tests/test_audit_store.py` deleted; its six tests merged into
   `plugins/fleet-core/tests/test_audit_store.py` (existing fixture reused, `import os` added,
   scope-guard comments on the three non-differential tests).
9. **T9** — `test_cli_advance_reports_unavailable_lease_authority` (rc 1 + structured
   `{"ok": false}` stderr receipt, no traceback).
10. **SEC1 (surface)** — activation comments at both dispatcher sites and the saga
    CHANGELOG 0.78.0 entry rewritten: the seam is admission accounting plus post-hoc conflict
    detection (supersede-on-acquire surfaces as the loser's renew failure → the new halt arm);
    NOT mutual exclusion; settlement ledger stays per git-common-dir. fleet-core CHANGELOG
    guard-scope claim narrowed per SEC2.

### Reducer-visibility note (new defect found during remediation)

While mirroring the `BackendHaltError` arm it emerged that every receipt-spread halt append
stores `kind="halt"` (the spread overrides the literal's `"kind": "dispatch"`), which **no**
reducer or report consumer matches — `reduce_dispatch_ledger`'s halt arm and the derived
report's halted filter both require `kind == "dispatch"`. Verified present in Claude `794b4da6`
(`outcome.py:1263/:1332/:1501`; `outcome_report.py._halted_subplots`) and mirrored here. The
NEW DispatcherError arm writes its record reducer-visible (`{**receipt, "kind": "dispatch"}`,
with an in-code constraint comment); the three pre-existing sibling sites are ported bytes and
stay byte-faithful — the systemic fix is **Finding 4 of upstream #627**.

## Routings

- **Upstream (KTD7)**: infiquetra/infiquetra-claude-plugins#627 — supersede-on-acquire
  semantics + cross-clone settlement scope + `dispatch_identity` collapse (SEC1 core), the
  missing Claude-side DispatcherError arm (COR1's shape at Claude `outcome.py` ~:1468/:1496),
  resolve-scope guard bypass (SEC2), reducer-invisible halt records (remediation discovery),
  group-writable advisory footnote (SEC3, no action).
- **#43 parity backlog**: COR3 worktree-lease-layer port unit (issue comment recorded).
- **No suppressed findings.** SEC3's fix rejection is a validated adjudication, not a
  suppression; the finding itself is upheld and recorded.

## Gates at `ecbdaab`

- Full suite: `PYTHONPATH=. uv run pytest -q -p no:cacheprovider` → **2599 passed** (net +10
  vs `a6d5e51`'s 2589: +1 reconcile-arm pin, +3 CLI oracles, +6 compat privacy arms,
  +6 merged audit tests, −6 deleted duplicates).
- `uv run ruff check .` → clean.
- `scripts/validate_codex_plugins.py` → passed.
- Compat freeze re-proof: diff vs Claude `794b4da6` = `RUNTIME_LABEL` line 83 only.
- Legacy workflow inventory rebuilt (`build_legacy_workflow_inventory.py --write`) after the
  CHANGELOG digest tripwire fired — routine remediation, digests current.

## Result

**CLEAN** — zero open P0–P3 findings. All validated codex-local findings repaired at
`ecbdaab`; semantic cores discharged upstream (#627) per KTD7; advisories recorded (COR3 on
#43, SEC3 in #627's footnote). PA-2 is ready for PR under the recorded frozen-range deviation
(remediation commits extend the reviewed range; the review binds `a6d5e51` + delta `ecbdaab`).
