# Code review — lease-safe substrate port (#33, U1–U4)

- **Target**: branch `work/33-codex-substrate`, diff base `19a3610e` (branch point; `origin/main` unmoved) → **REVIEWED_SHA `acc0d1dab9fa19fd9ada9461abd82b5e05dac0e4`** (10 commits, 36 files, +17631/−40; worktree clean, no untracked files).
- **Mode**: programmatic (leaf-lifecycle gate, Claude-direct executor); operator merge pre-approval standing.
- **Verdict**: **CLEAN** — zero P0/P1. One finding (validated, downgraded P2→P3, fixed in `b52280ae`, delta re-affirmed by the originating lens).
- **Plan authority**: `docs/plans/2026-07-15-codex-shared-runtime-substrate-plan.md` (manifest-bound; plan and both doc-review digests re-verified MATCH against current bytes at review time).
- **Upstream gate**: six-lens cc-workflow ceremony converged clean across three rounds under approved anchor `bc038d41` — record at `docs/validation/lease-safe-substrate-ceremony.md`. The ceremony discharged the external-engine second-opinion offer.

## Scope check: CLEAN

Intent: port the merged #351/#355/#356 lease-safe substrate (frozen source range `a6f3bcff..cf15a09f`) into codex fleet-core/saga per the classified port manifest. Delivered: exactly that write-set, plus one justified CHANGED item — the capability-snapshot schema revision landed as a new file (`codex-runtime-capability-snapshot.schema-r2.json`) instead of an in-place edit, preserving historical digest seals per the operator's MultiAgent-v1 decision. No unrelated files touched; release surfaces (plugin.json/CHANGELOG/PORTABILITY/matrix) intentionally absent — they are release-unit U5 scope per the manifest version policy.

## Plan-completion audit

| Item | State | Evidence |
|---|---|---|
| R1 freeze-before-behavior | DONE | U1 `96531be` precedes all behavior commits; manifest + classification + per-port gate; plan/review byte-bindings verified MATCH |
| R2 runtime-neutral root | DONE | `resolve_state_root` byte-identical to source; `test_broker_resolves_state_root_from_environment` asserts no `.claude`/`.codex`; conformance digests root- and machine-independent |
| R3 broker/resource behind fleet-core | DONE | U2 modules byte-faithful; 1432-line broker suite + contention tests green |
| R4 guarded writes, no host primitives | DONE | orphan_evidence ported; hooks/emitter classified reject (7 rows); KTD3 treatment test enforces reject/defer carry no units |
| R5 settlement + codex ack preserved | DONE | dispatch_settlement verbatim; graft returns record-only `prepared`; `outcome.py:1326` reconcile confirmed no launch fabrication |
| R6 stale writers fail before effect | DONE (primitives + seam) | fenced release/renew zero-byte-mutation oracles; HALT-before-mint verified; production wiring is #34 scope (documented) |
| R7 production-shaped concurrency proof | DONE | fork-context two-process races (barriered), write-once ledger race, pinned cross-runtime digests `f60fd482`/`34804e26`; migration suite count pin 47→49 verified both-directions |
| R8 release unit | NOT-DONE (by design) | U5 is the next unit; this review is the pre-release gate |
| U1–U4 | DONE | commits `96531be`/`e231770b`+`f6fb0b09`/`3cdae873`+`925f735`/`c1bb35e`+`ea7f661` with per-unit evidence artifacts, digests current |
| U5 | NOT-DONE (sequenced) | release/install/rollback/PR pending |

## Lens results (4 always-on; conditional lenses declined — no deploy/migration executes in this diff, no infra; reliability double-covered by the ceremony's concurrency validator)

| Lens | Model | Verdict | Notes |
|---|---|---|---|
| correctness | opus/high | CLEAN | Enum/value completeness verified OUTSIDE the diff (consumers read via `.get()`/set-membership; no default-less switches); sys.modules collision ruled out (shim mangles its key); graft calls match broker signatures; no swallowed exceptions; 316 tests run |
| security | opus/high | CLEAN | No shell surfaces in new code; fixtures hermetic (real-HOME before/after proof); no secrets/PII in added lines; restrictive modes (0o600/0o700); 45 tests run |
| testing | opus/high | 1 P2 | Finding #1 below; four other charter angles empirically clean (incl. drop-a-classification-entry rebuild-oracle proof) |
| maintainability | sonnet/medium | CLEAN | New tests inside existing convention variance; `_load` boilerplate is the established repo pattern; no TODO/dead code; manifest cross-references all resolve; ruff clean |

## Findings

### #1 — P3 (validated; originally P2, downgraded by independent validator) — FIXED

**v1 capability-snapshot validator branch had happy-path-only coverage; deleting any of its four honesty assertions passed CI silently.**
`scripts/port_contract.py:839-847` (net-new v1 branch) was exercised by exactly one test running the honest committed snapshot (`errors == []`), so branch inversion was caught but branch deletion was not. Independent validator confirmed real / diff-introduced / unhandled elsewhere — probe-proved a fully dishonest snapshot passes the schema-r2 `enum`/`boolean` types with zero errors, so the validator branch is the sole enforcement. Downgraded to P3: three of the four invariants are double-pinned by direct data assertions (`tests/test_lease_safe_substrate_port_contract.py:247-250`); the input is a committed, reviewed artifact; only `available is True` was singly-guarded. Blast radius is mutation-coverage, not shipped behavior.

**Fix (`b52280ae`)**: `test_capability_snapshot_validator_rejects_each_dishonest_v1_claim` — four parametrized cases, each mutating one spawn claim in a tmp-path copy and asserting the specific error surfaces. **Delta adjudication by the originating testing lens: fixed-adequately** — empirically proven by compiling four `port_contract.py` variants with each branch individually deleted and observing each case flip to fail; zero new findings in the fix diff.

## Coverage

- **Suppressed**: 1 (security, below anchor 75 — test-side path construction from the committed manifest JSON; read-only, requires commit access to exploit).
- **Residual risks (accepted/tracked)**: audit_store ancestor-dir validation deferred while the module is dormant (hardening owed to the unit that first wires a live caller); lease seam inert on the production advance path until codex-parity #34 wires `default_lease_authority()` — U5 PR body carries this acceptance language.
- **Testing gaps**: none open — ceremony r1's coverage findings and this review's #1 are all fixed and re-adjudicated.

## Gates at review head (and fix head `b52280ae`)

Affected suites 387 passed (+13 gate tests at fix head); `validate_codex_plugins.py` green; ruff check clean (format clean on all files this port authored/edited); per-port gate 13/13; conformance digests pinned. No saga tick written: no work-thread saga exists in this repo's store for #33 (leaf tracked in the outcome ledger as `leaf-lease-safe-runtime-continuity-codex-substrate`; scan-first, never mint).

Review complete.
