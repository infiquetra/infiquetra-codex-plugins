# Lease-safe substrate port — pre-PR ceremony record (#33, U1–U4)

Operator-approved cc-workflow six-lens ceremony, anchor
`bc038d414f8807e432bc2ce81abef1eb536b35eb63e044ec2a101cf948d57283` over 6547 section bytes of
`docs/plans/2026-07-15-codex-shared-runtime-substrate-plan.md` (`## Workflow Structure` through the
newline before the standalone `---` rule). The anchor was recomputed byte-exact immediately before
every round launch. Lens table per the approved plan: devils-advocate / security / architecture /
testing reviewers at opus high; concurrency / event-flow validators at sonnet medium; every lens
spawned as `saga:readonly-verifier` with worktree isolation; in-flight pool capped at 3. Subject
reviewed read-only via absolute paths; worktree audited clean after every round.

## Round 1 — full six-lens review

- Run `wf_39b0f49d-56a` at head `ea7f6614617ab4ce1b8698c0569f58d30c9eafd5` (diff `19a3610..ea7f6614`).
- Verdict: P0=0 P1=0 **P2=2 P3=7**. Scores: devils 89, security 88, architecture 92, testing 84,
  concurrency 92 (clean), event-flow 78.
- All six lenses independently byte-diffed the ported modules against frozen source `cf15a09f`:
  verbatim confirmed for `fleet_commons/{lease_broker,orphan_evidence,concurrency_policy}.py` and
  `saga/{lease_broker,dispatch_settlement,run_ledger}.py`; `audit_store.py` differs only by the
  documented runtime-neutral default root and docstring.

### Adjudication and remediation (commit `ec18b324`)

| # | Lens | Sev | Finding | Disposition |
|---|------|-----|---------|-------------|
| 1 | testing | P2 | Lease-graft error/HALT branches untested (halt-with-held-lease, renew-raises, release-returns-False) | **Fixed**: three tests added to `tests/test_outcome_dispatcher.py` |
| 2 | event-flow | P2 | run_ledger wholesale port carries `append_fact_built_atomic` + new fact kinds with no consumer or coverage | **Fixed**: two atomic-builder smoke tests + manifest row rationale names the forward-compat surface |
| 3 | devils | P3 | `STAGED_MARKETPLACE_SHA256` bumped to a wrong value | **Refuted with evidence**: U1 changed `LEGACY_WORKFLOW_HISTORICAL_INVENTORY_SHA256` (actively gated, legitimately recomputed by the inventory rebuild); `STAGED_MARKETPLACE_SHA256` untouched at baseline. Lens misread the git hunk header as the assignment target |
| 4 | security | P3 | `scripts/port_contract.py` fails `ruff format --check` (pre-existing at baseline) | **Moot**: codex CI runs no ruff format gate (verified: no such step in `.github/workflows/`) |
| 5 | security | P3 | audit_store validates only the leaf, not pre-existing ancestors of the deeper default root | **Deferred while dormant**: module is byte-faithful to the frozen source contract and has zero in-tree callers; ancestor-validation hardening is tracked for the unit that first wires a live caller |
| 6 | architecture | P3 | Lease seam inert on the production advance path until #34 wires `default_lease_authority()` | **Accepted scope boundary**: U1–U4 land a capable-but-unwired seam; acceptance language carried into the U5 PR body; runtime enforcement activates in codex-parity (#34) |
| 7 | testing | P3 | Conformance two-process spawn race lacks a start barrier | **Fixed**: fork-context `Event` barrier mirrors the fleet-core broker contention tests |
| 8 | concurrency | P3 | Lease scope (dispatch preparation vs backend execution) undocumented | **Fixed**: `make_dispatcher` docstring states the boundary |
| 9 | event-flow | P3 | No test pairs a real lease authority with a dispatcher HALT result | **Fixed**: `test_make_dispatcher_releases_lease_before_halt_propagates` |

## Round 2 — four affected lenses, delta adjudication

- Run `wf_b11a14c8-d11` at head `ec18b324806ccb018bb7e0627b1556d957e82fb0`
  (delta `ea7f6614..ec18b324`; security/architecture dispositions documented, not re-run).
- Verdict: all six round-1 items resolved — testing **93 clean**, concurrency **92 clean**,
  event-flow **92 clean**; devils accepted its refutation after independent verification.
- One new P3 (devils 80): the amended manifest rationale claimed `teardown` was pinned, but
  `FACT_KINDS` has nine members and the schema test exercised eight — `teardown` appeared in zero
  tests (a false-proof introduced by remediation cycle 1).

### Remediation (commit `7b4459a5`)

Schema test renamed `test_schema_covers_every_fact_kind`, appends a real teardown fact through the
write-locked hash-chained append path, and asserts the exercised kind set equals
`run_ledger.FACT_KINDS` so a future kind cannot join unexercised; manifest rationale corrected to
match.

## Round 3 — devils-advocate delta adjudication

- Run `wf_fa604a2e-545` at head `7b4459a5470717be92027848a6cc0b4354c55210`
  (delta `ec18b324..7b4459a5`, exactly 2 files).
- Verdict: **clean, 95, zero new findings**; teardown remediation adjudicated fixed-adequately,
  including cross-checking that the port's nine fact kinds match source `cf15a09f` exactly.

## Convergence

All six lenses clean across three rounds and two remediation cycles (tripwire threshold: three).
Final ceremony head `7b4459a5470717be92027848a6cc0b4354c55210`; worktree clean at every audit.
Open follow-ups carried forward: audit_store ancestor validation (on first live wiring) and the
#34 lease-seam activation acceptance language (U5 PR body).
