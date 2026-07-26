# Doc review — codex#54 lease-registry forward-compatibility plan

**Target:** `docs/plans/2026-07-26-codex-54-lease-registry-forward-compat-plan.md`
**Reviewed revision:** working tree (plan untracked) at repo head `d0982fe`, branch `main`
**Classification:** plan (content-shape signals + `docs/plans/` tie-breaker); readiness-skeptic pass, no
idea/issue rubric engine
**Status:** **not blocked** — every P0/P1 was fixed in place
**Engine offer:** `prompt_required: false` (stored preference, advisory-only); no external panel run
**Linked issue:** infiquetra/infiquetra-codex-plugins#54 · **Saga:** `issue-54`

## Readiness summary

The plan can drive implementation. Its central technical claim held up under adversarial re-measurement,
but seven findings were fixed in place — three of them P1 — and every one came from a claim the plan
*carried forward from an earlier session* rather than measured at `d0982fe`.

That is the pattern worth naming: the newly-measured content (the divergence analysis, the six-site
conversion table, the commit-path trap) survived scrutiny intact. The defects clustered entirely in
inherited assertions. Two of the three P1s would have been discovered only after the implementer had
already written tests in the wrong module or declared a false green.

## Findings

| ID | Pri | Finding | Status |
|---|---|---|---|
| D1 | P1 | U3's test home was `tests/test_lease_settlement_conformance.py`, which does not exercise the settlement-close path | fixed |
| D2 | P1 | The stated gate command fails; the baseline is not reproducible as written | fixed |
| D3 | P1 | KTD7's "annotation in the evidence entry" is impossible — `evidence_keys` is closed | fixed |
| D4 | P1 | U6 would pin a branch-head SHA that is never what ships (merge-commit convention) | fixed |
| D5 | P2 | U4's test module has no CLI-invocation harness to extend | fixed |
| D6 | P2 | U2 asked for six per-type record tests without pointing at existing fixtures | fixed |
| D7 | P2 | No rollback path stated | fixed |
| D8 | P2 | U5 leaves the registry-parity check to be resolved at execution time | open, accepted |
| D9 | P3 | The `#616` line attribution (~21–30) is approximate | open, accepted |

### D1 — U3's test home did not cover the path it tests (P1)

The plan sent U3's archive-retention tests to `tests/test_lease_settlement_conformance.py`. That module
is a cross-runtime conformance *matrix* (`#33 U4`) over digest root-independence, read-view projection,
and zero-byte-mutation properties. It carries **zero** `close_receipt` references.

The only modules referencing `close_receipt` are `plugins/fleet-core/tests/test_lease_broker.py` (4),
`plugins/fleet-core/tests/test_orphan_evidence.py` (4), and `tests/test_outcome_cross_runtime.py` (1).

Following the plan literally would have produced archive-retention tests inside a `FakeRuntime` harness
built for a different purpose — tests that could pass without touching the commit path they exist to
pin. **Fixed:** U3 retargeted to `test_lease_broker.py`, with the substrate table rewritten to explain
why the conformance matrix is not a home for it.

### D2 — The gate command fails and the baseline was unreproducible (P1)

The plan asserted "`uv run pytest` fails collection; use `python3 -m pytest` or `PYTHONPATH=.`; baseline
at `d0982fe` is 2728 passed, 4 skipped, 0 failed." Measured at `d0982fe`:

| Invocation | Result |
|---|---|
| `uv run pytest` | 2546 collected, 11 collection errors |
| `python3 -m pytest` | 16 collection errors, incl. `ModuleNotFoundError: No module named 'PIL'` |
| `PYTHONPATH=. uv run pytest` | 2728 passed, **4 failed** (178s) |

Both commands the plan offered fail. The one that works reports 4 failures, not 0.

The 4 are environmental. Proven by re-running the failing module in a clean detached worktree at the
same SHA: `tests/test_verified_workflows_migration.py` → **14 passed** clean vs **4 failed** in the
primary tree. Cause is codex#56 — `build_legacy_workflow_inventory.py` refuses to run while the
untracked `.claude/` is present, so the digest-bound inventory assertions fail.

**Fixed:** the measured table, the proof, and the instruction to run full-suite gates in a clean detached
worktree. The Verification section was rewritten to split targeted runs (working tree, fine) from the
full-suite gate (clean worktree, mandatory).

### D3 — KTD7 prescribed something the schema rejects (P1)

KTD7 said to record the acceptance evidence "with an explicit annotation that it executes in the
companion repo." Read directly from `scripts/port_contract.py`, `evidence_keys` (`:1196`) is a closed
set of ten keys plus two optional ones, and `cwd` is pinned to `"."` (`:1236`). There is no field to
hold an annotation, and an invented key fails validation — so U5's gate would have failed on U6's own
evidence entry.

**Fixed:** the caveat moves to the `artifact_path` document the entry references, which is unconstrained
prose. Both schema line references are now quoted in the plan so the constraint is checkable.

### D4 — U6 would have pinned a SHA that never shipped (P1)

`require_clean_pinned` pins an exact SHA. This repo merges with merge commits — `d0982fe`, `f79f141`,
and `74258be` are all `Merge pull request …` — so the branch head is never what lands on `main`. A
bundle produced pre-merge describes a commit that is not the shipped state, while objective #639's
clause 3 requires the shipped state proven.

**Fixed:** U6 now states it runs against the post-merge `main` SHA, with the sequencing consequence
spelled out (merge on the targeted gates, then U6's bundle lands as follow-up evidence) and an explicit
prohibition on claiming clause 3 from a pre-merge run.

### D5–D7 — fixed, lower severity

**D5:** `tests/test_saga_lease_broker.py` tests the adapter's *library* surface and contains no CLI
invocation at all (zero `main` / `argv` / `SystemExit` / `capsys`). U4's exit-code scenarios need a new
harness; `tests/test_capability_degrade.py` is now named as the in-repo pattern.

**D6:** U2 now points at `broker`/`runtime` (`:72-78`), `_raw_registry` (`:120`), `_agent` (`:86`),
`_worktree_resource` (`:112`), `_recovery_intent` (`:1029`).

**D7:** the rollback is the feature's own `repair --strip-unknown`, which is why it takes a backup and
refuses to act without the flag. Now stated.

### D8–D9 — open, accepted

**D8 (P2):** U5 says to verify the repo's registry-parity check rather than assuming a claude-style
`marketplace.json`. This is an unresolved choice, but it is shaped as an explicit evidence-gathering
task rather than a silent assumption, which is the correct form. Accepted.

**D9 (P3):** the `#616` isolation attribution is given as "~21–30 lines" from keyword bucketing. The
plan labels it approximate and no decision depends on the exact figure. Refining it is not worth the
measurement. Accepted.

## Hypotheses tested and refuted

Recorded so a later reader does not re-open them:

**`_all_keys` (`test_lease_broker.py:208`) is not a closed-schema assertion.** Its only use is a
*negative* check at `:270` — `assert not ({"status", "expired", "expires_at", "stale"} & _all_keys(raw))`
— pinning that derived fields are not persisted. Tolerance adds none of those keys, so the port does not
break it.

**Codex carries no content claude lacks.** Re-verified independently of the plan: every tested symbol is
present in both brokers and the two class lists are identical (25 classes, same order). The `−46` lines
in the diff are all halves of modification pairs. The plan's KTD1 rests on this and it holds.

## Verified-as-stated

Carried claims that survived re-measurement at `d0982fe` / `b464d090`: `expected_count` and
`inventory_sha256` are genuinely derived (`port_contract.py:448-449`); `evidence_keys` closed at `:1196`
and `cwd` pinned at `:1236`; `require_clean_pinned` at harness `:218` with the clean-and-exact-SHA
docstring; `external_action_release_matrix.py` raising on the proof's own `content_sha256` before
anything else, confirming the cutover scope-out.

## Applied fixes

Eight in-place edits to the plan: U3 test home (D1); the substrate table rewritten with both test-module
gotchas (D1, D5); the measured invocation table, environmental-failure proof, and clean-worktree
instruction (D2); the Verification section split into targeted vs full-suite (D2); KTD7 rewritten around
the closed key set (D3); U6's merged-SHA sequencing (D4); U2's fixture pointers (D6); the rollback
paragraph (D7).

One further correction was applied during the plan's own confidence pass before this review: the fourth
strict `_closed_mapping` boundary is the settlement recovery intent, not `FencingToken` — the latter is
a fifth strict boundary reached by its own inline path (claude `:664`).

## Residual risk

**No CI in this repo.** `.github` exists, `.github/workflows` does not. Every gate is local-only and
nothing catches a regression after merge. The clean-worktree requirement from D2 is load-bearing
precisely because there is no second chance.

**The acceptance harness has not been run against a fixed codex tree.** The plan's cheap inner-loop
substitute is well-grounded — the two failing legs reduce to a single read-back assertion — but the
claim that the fix turns the harness green stays a hypothesis until U6 executes.

**Self-review limitation.** This review was performed by the same author as the plan. It was run
adversarially against carried-forward claims and found four P1s, but a same-author review cannot rule
out a shared blind spot in the newly-measured content. The engine offer reported no prompt required, so
no external second opinion was dispatched; one remains available if the operator wants cross-family
depth before `/work`.
