# Doc review — codex#45 re-freeze + COR3 plan

**Target:** `docs/plans/2026-07-25-codex-refreeze-627-seam-and-cor3-worktree-authority-plan.md`
**Companions in scope:** `...-spec.json`, `...workflow.js`
**Reviewed revision:** working tree (repo `main` at `f79f141b`; all four artifacts untracked)
**Upstream reference:** `infiquetra-claude-plugins` `origin/main` `b464d090`
**Reviewer:** Claude (host, owns the verdict) · external second opinion: codex `gpt-5.6-sol` xhigh, adversarial lens
**Blocked:** **NO** as of the 2026-07-26 resolution pass. All eleven external findings (C1–C11) are
resolved, plus one further structural defect (**C12**) that neither review leg found. Zero unresolved
P0/P1. See "Resolution pass" at the end.

## Verdict

Nine findings, all evidence-backed against source rather than against the issue's prose. **Two were
P0** and both came from the same root cause: the plan had paraphrased a load-bearing mechanism from
the issue's summary instead of reading Claude's implementation. All nine are fixed in place; the spec
and workflow were re-validated (`--require-receipts`, exit 0) and re-emitted so the three artifacts
agree.

The single most useful outcome: the plan's biggest *unverified* claim turned out to be true and
stronger than stated, while two claims it presented confidently were wrong.

## Findings

| # | Pri | Finding | Status |
|---|---|---|---|
| D1 | **P0** | R5/U3 stated the refuse-mode guard as a one-part test; it is a three-part conjunction | fixed |
| D2 | **P0** | U4's named ordering test asserts a postcondition that is false | fixed |
| D3 | P1 | U2 omits the inventory file the acceptance harness actually digests | fixed |
| D4 | P1 | Plan asserted a `_reconcile_once` layout divergence that does not exist | fixed |
| D5 | P1 | R7's transient path specified as "halt-and-continue"; it is materially more | fixed |
| D6 | P2 | KTD2's port-digest independence claim was unverified | verified, strengthened |
| D7 | P2 | Linear `depends_on` vs three-PR structure read as a contradiction | fixed (KTD2a) |
| D8 | P2 | U5's "thread into `prune`/`advance`" names a seam that does not exist | fixed |
| D9 | P2 | `.claude/` is not git-ignored in this repo; the saga tick is committable | documented |

### D1 (P0) — the refuse guard is a three-part conjunction

**Where:** plan R5, U3 substance and test scenarios.

**Evidence:** Claude `plugins/fleet-core/scripts/fleet_commons/lease_broker.py:2412-2425`. The guard is
`prior_lease is not None` **AND** `not self._expired(prior_lease, monotonic=..., boot_id=...)` **AND**
`self._owner_state(prior_lease) != "dead"`. The plan named only the third arm.

**Why it matters:** each dropped arm is a distinct wrong behavior. Omitting the `_expired` check makes
refuse-mode reject leases it must reclaim — the docstring is explicit that "an expired prior is
reclaimed in both modes." Omitting the `prior_lease is None` case refuses where it should supersede.
Also missed: the raise is `LeaseConflictError` carrying `holder_owner_id=` (not a bare exception), and
two `LeaseOwnershipError` precedence gates — retained settlement, and canonically-closed-requires-
`acquire_successor` — sit *above* the refuse branch and must not be reordered.

**Fix:** R5 now quotes the implementation verbatim, adds R5a (exception type and payload) and R5b
(precedence gates), and U3's scenarios went from 5 to 10 — one per conjunction arm, both fall-through
cases, and both precedence gates. The expired-prior-is-reclaimed case is called out as the one most
likely to be dropped.

### D2 (P0) — the ordering test asserted something false

**Where:** plan U4 test scenarios.

**Evidence:** Claude `plugins/saga/scripts/outcome.py:1657-1663`. At the moment of the non-transient
re-raise, the 300 s **broker dispatch lease is already released** by `make_dispatcher`'s own `finally`;
what stays held is the per-subplot `dispatch-{sid}` **store lock** (self-healing after the 900 s
`DEFAULT_LEASE_TTL`); the coordinator lock is released by the outer `finally`.

**Why it matters:** the plan told the implementer to assert "the lease is still held." Read as the
broker lease that is false, so the test either fails or — worse — gets "fixed" by making the
implementation hold a lease it is supposed to have released.

**Fix:** new R7a table distinguishing all three locks, and U4's scenario now names the store lock
explicitly and states in terms why the broker lease must *not* be asserted held.

### D3 (P1) — the harness digests a file the plan never names

**Evidence:** `contract_digests` reads `codex.repo / "docs/validation/saga-family-target-inventory.json"`
through `_sha256_file` (`tools/run_cross_runtime_outcome_acceptance.py:263`). The plan and spec
referenced that path **zero** times; U2 said only "rebuild the port inventory," which reads as the
`docs/portability/ports/` manifests. The file exists (4.5 KB).

**Fix:** new R4a; U2's scope, prompt, `files` array, and test scenarios all name it, with the two
inventories explicitly distinguished.

### D4 (P1) — a divergence that isn't there

**Evidence:** `def _reconcile_once` is defined in `outcome.py` in **both** repos — Claude `:1097`,
codex `:1148`. `outcome_reconcile.py` defines it in neither. The plan claimed codex diverged from
Claude here and told the implementer to "confirm the layout."

**Fix:** U4 now states there is no divergence, corrects the record, and points at Claude
`outcome.py:1650-1690` as the reference implementation.

### D5 (P1) — the transient path is not a bare `continue`

**Evidence:** Claude `outcome.py:1666-1682`. The transient branch must release the lock, append a
reducer-**visible** `(dispatch, halt)` record paired to the intent's `key` — built spread-first /
literal-last so `kind` survives as `"dispatch"` for `reduce_dispatch_ledger`'s halt arm and
`outcome_report._halted_subplots`, preserving the receipt's own kind under `receipt_kind` — and settle
the attempt. Omitting the halt record is the #628 invisibility shape: the orphaned intent matches no
reducer branch, the store lock leaks to TTL, and the leaf silently re-dispatches with no operator page.

**Fix:** new R7b, plus a dedicated U4 test scenario asserting the record's shape and reducer match.

### D6 (P2) — the unverified claim was true, and stronger than stated

**Evidence:** `contract_digests` (`run_cross_runtime_outcome_acceptance.py:245-267`) raises the
`port-digest` `HarnessError` on exactly one condition — the two `outcome_compat.py` copies differing
after `codex_text.replace('RUNTIME_LABEL = "codex"', 'RUNTIME_LABEL = "claude"', 1)`. It does not
compare `audit_store.py` and does not touch the codex-native trio.

**Fix:** KTD2 now records the verified coverage. PR-A clears `port-digest` on the strength of U1's
`outcome_compat.py` half plus R4a — so the three-PR split is better justified than the original
blast-radius argument alone.

### D7 (P2) — build order vs merge boundaries

The spec runs one linear chain `U1→…→U6` while the plan proposes three PRs; nothing said these
describe different axes. **Fix:** KTD2a states the chain is build order and the PRs are
review-and-merge boundaries, and forbids "reconciling" one to the other.

### D8 (P2) — the COR3 seam is a factory, not a verb

**Evidence:** Claude's 6 `outcome.py` `lease_authority` lines are in `production_worktree_processor`
(`:2256`, param `:2262`/`:2273`, nested closure `:2284`/`:2292`). `main()` (`:2359`) wires authority at
`:2689` (`make_dispatcher`) and `:2693` (`worktree_processor`). The `advance` (`:2426`) and `prune`
(`:2567`) subparsers take no authority argument.

**Why it matters:** "thread `lease_authority` into `prune` and `advance`" sends the implementer looking
for parameters that do not exist. **Fix:** U5 scope, substance, and its test scenario now describe the
factory-and-wiring seam. The U4/U5 overlap on `outcome_dispatcher.py` is also now explicit about which
symbols each unit adds.

### D9 (P2) — the saga tick sits in a committable path

This repo's `.gitignore` covers `.codex/saga/` but not `.claude/`; `infiquetra-claude-plugins` ignores
`.claude/` at `.gitignore:55`. Documented in Risk Analysis with the mitigation (explicit staging paths,
never `git add -A`). The durable one-line `.gitignore` fix is deliberately left out of scope as repo
configuration rather than part of the port.

## Applied fixes

Plan: R4a, R5 (rewritten with verbatim source), R5a, R5b, R7 (rewritten), R7a, R7b, KTD2 (verified
coverage), KTD2a, U2 scope + tests, U3 substance + tests (5 → 10 scenarios), U4 scope + substance +
tests, U5 scope + substance + tests, Risk Analysis (+1 risk).

Spec: U2 prompt + `files`; U3 prompt; U4 prompt; U5 prompt. Re-validated with `--require-receipts`
(exit 0) and re-emitted to `...workflow.js`. Spend unchanged at 120; 6 units, linear `depends_on`,
peak fan-out 1.

## Residual risk

Tier assignments were reviewed and left as authored (U1 `sonnet/high`, U2/U6 `sonnet/medium`,
U3/U4/U5 `opus/high`). U1 ports a security guard at a sonnet tier, which is defensible only because
D6 established that its oracle is a mechanical byte-identity diff rather than a judgment call; if that
oracle is weakened the tier should rise.

Codex's port-manifest schema was inferred from two existing examples, not from a published schema
document. If `docs/portability/claude-to-codex-plugin-port-runbook.md` specifies required fields those
examples happen to omit, U2 will discover it at build time.

The external second-opinion leg is recorded separately below once returned; every external finding is
advisory and is verified against source before adoption. The readiness verdict above is Claude's.

---

## External second opinion — codex `gpt-5.6-sol`, xhigh, adversarial lens

**Run:** `20260725T235138Z-9a8250929b67` · 772 s · 7.35M input / 33.7k output tokens · `return_code: 0`
**Wrapper status:** `out_of_scope_mutation` — **false positive, diagnosed.** The guard diffs the
worktree before and after the run; the `new_paths` it flagged is *this review artifact*, which the host
wrote concurrently. Codex ran `-s read-only` and `mutation.patch` is 0 bytes, so it mutated nothing.
Consequence to keep in mind: codex reviewed a **moving target** — it saw the corrected plan but a
partially-corrected spec, so a few of its spec-side remarks were already resolved.

**Codex verdict:** `BLOCKED — P0=6, P1=4, P2=1`.

It independently confirmed all eight challenged measurements, the refuse-branch conjunction, and that
PR-A can clear `port-digest`. It then found six P0s the host review missed. Every one below was
verified against source by the host before adoption; none were taken on codex's say-so.

| # | Pri | Codex finding | Host verification | Status |
|---|---|---|---|---|
| C1 | **P0** | `returns` is a string, so the emitter splits it per character | **CONFIRMED** — emission read `returns: ["T","h","e"," ",...]`; `validate --require-receipts` passed anyway | **fixed** |
| C5 | **P0** | U3 ports only the private branch; the public API is absent | **CONFIRMED** — Claude `OnConflict` `:46`, `LeaseConflictError` `:241`, `acquire_agent` `:2486`; codex has **0** of both symbols | **fixed** |
| C6 | **P0** | U6 names a nonexistent marketplace path, omits plugin manifests | **CONFIRMED** — only `.agents/plugins/marketplace.json` exists; manifests are `plugins/<p>/.codex-plugin/plugin.json` | **fixed** |
| C9 | P1 | The claimed U4/U5 dispatcher overlap is false | **CONFIRMED** — codex already has `default_lease_authority()` at `outcome_dispatcher.py:192` | **fixed** |
| C2 | **P0** | Mandatory classification stage must precede implementation | **CONFIRMED** — `scripts/port_contract.py` exists (`init`/`refresh`/`validate`/`verify-source`/`render`); runbook steps 3-5 gate it | **fixed** |
| C3 | **P0** | `base_ref=b464d090` with no `target_ref` yields zero rows | **CONFIRMED** — `b464d090..b464d090` yields 0 rows; `cf15a09f..b464d090` yields 5; `cf15a09f` is the predecessor contract's `target_ref` | **fixed** |
| C4 | **P0** | A linear 6-unit chain cannot produce three PRs | **CONFIRMED** — `work/SKILL.md:684-728` has one PR-ready boundary; harness in **0 of 4** workflow files, so early green unblocks nothing | **fixed** |
| C7 | P1 | "no ledger record" conflicts with the pre-dispatch intent | **CONFIRMED** — codex `outcome.py:1270-1281` appends intent, `:1308` dispatches, `:1319` is the arm | **fixed** |
| C8 | P1 | R4a is circular; the harness records the digest, never compares it | **CONFIRMED against host finding D3** — `contract_digests` returns `_sha256_file(inventory)` without comparison | **fixed** |
| C10 | P1 | Retry / idempotency / malformed-input modes still unenumerated | **CONFIRMED** — upstream `test_acquire_agent_rejects_unknown_on_conflict`; `reap_worktree` is explicitly idempotent | **fixed** |
| C11 | P2 | KTD3's line-count proof concerns the wrong module | **CONFIRMED, agrees with host D4** — `_reconcile_once` is in `outcome.py` in both repos, in neither `outcome_reconcile.py` | **fixed** |

### Host corrections to its own findings

**D3 overstated its consequence.** C8 is right: `contract_digests` *records* the target inventory
digest and never validates freshness, so a stale inventory does not fail the harness. The file still
must be rebuilt, but R4a's implied failure mode is wrong and needs rewording.

**KTD2a was asserted, not verified.** The claim that `/work` opens a PR at each unit boundary was never
checked against the skill. C4 says `/work` runs all units and then offers one PR. Until verified, the
three-PR decomposition has no execution mechanism behind it.

## Resolution pass — 2026-07-26

All eleven codex findings resolved. Verification for each was taken live against source, not accepted
on the reviewer's authority.

| # | Resolution | Evidence taken |
|---|---|---|
| C1 | `returns` converted to machine-key arrays on all six units; re-emitted | emission now reads `returns: ["changed_files", …]` on all 6 |
| C2 | New **U1** is the classification gate; every other unit renumbered behind it (old U1 → U2). Writes no production code; completion condition is `validate --stage classification` exit 0 | runbook steps 3–5; new KTD8 |
| C3 | Range corrected to `cf15a09f..b464d090`; `expected_count` documented as row-derived; tests retargeted to `tests/test_*_port_contract.py` | `b464d090..b464d090` → 0 rows; `cf15a09f..b464d090` → 5 rows; `port_contract.py:437-450` |
| C4 | Three-PR split **retired**; one PR (KTD2), with the old split moved to Alternatives-rejected | `work/SKILL.md:684-728` (one PR-ready boundary); harness in **0 of 4** `.github/workflows/` files |
| C5 | U3 prompt ports the full public API surface | claude `OnConflict` `:46`, `LeaseConflictError` `:241`, `acquire_agent` `:2486`; codex has neither symbol |
| C6 | U6 targets `.codex-plugin/plugin.json` ×2 and `.agents/plugins/marketplace.json`; the Claude path is explicitly forbidden | only one `marketplace.json` in the tree |
| C7 | R7a rewritten: snapshot the ledger **before** dispatch, assert no record *beyond* the snapshot, spy that lock release was not called | codex `outcome.py:1270-1281` intent → `:1308` dispatch → `:1319` arm |
| C8 | R4a rewritten non-circularly; bundle-hash comparison moved to U6 where the bundle exists | `contract_digests` `:262-267` records, `:256-261` is the only raise |
| C9 | U4 declared sole dispatcher owner; U5 a read-only consumer | codex `default_lease_authority()` already at `outcome_dispatcher.py:192` |
| C10 | Failure modes added to U1 and U3–U5: malformed/`None`/unknown `on_conflict`, repeated-transient append-once, settlement idempotency, second-reap idempotency, malformed receipt, post-preflight registry mutation, removal failure, authority-release failure | upstream `test_acquire_agent_rejects_unknown_on_conflict`; `reap_worktree` idempotency |
| C11 | KTD3's line-count proof replaced with per-module missing-symbol evidence | `_reconcile_once` is in `outcome.py` in **both** repos (codex `:1148`, claude `:1097`) |

### C12 (P0) — found during the resolution pass; neither review leg caught it

**COR3's source rows cannot be derived from any new contract range, because they are orphaned defers
in the predecessor contract.**

`plugins/saga/scripts/outcome_worktrees.py` has **zero** changed lines across `cf15a09f..b464d090`, so
the C3-corrected range produces no row for it and nothing to classify. Its row already exists in
`docs/portability/ports/2026-07-19-lease-safe-substrate.json` at `state: classified`,
`treatment: defer`, rationale *"Worktree reconciliation consumes the guard at Claude seams; Codex
worktree parity is #34 scope."* Two siblings carry the same deferral: `outcome.py` and
`tests/test_outcome_worktrees.py`.

**codex#34 closed 2026-07-20 without treating any of them.** The consequence for the C2 fix is direct:
a classification unit that only bootstraps a new contract would still leave COR3 in no contract at
all, and would *pass* `--stage classification`, because the gate validates the rows the contract has.

Resolved as **R4b** plus U1 step (b): promote the two implementable rows `defer → codex-adapt` in the
existing manifest. Two mechanical constraints, both verified: `refresh` cannot do it
(`refresh_manifest:1548-1578` never touches `state`/`treatment`, so promotion is an operator edit the
validator then checks), and unit ids **U2–U5 are already claimed** in that manifest, so the promoted
rows must take a free id from `UNIT_IDS` (`U1`–`U9`) with the mapping recorded in the rationale.

### Host self-correction from this pass

**`cheaper_fallback` is a Tier, not prose.** The first restructured spec set it to an explanatory
sentence on the new U1 and failed validation with `unit U1: tier needs both 'model' and 'effort'`.
Same shape as C1 — a typed field filled with prose — caught here by the validator rather than by
reading the emission. Corrected to `{"model": "sonnet", "effort": "high"}`, with the justification
moved into `worth_it_because` where it belongs.

### Post-resolution state

- Plan: rewritten across Summary, R4/R4a/R4b, R7a, R8, KTD2, KTD3, KTD8, all six units, Risk, and
  Alternatives.
- Spec: 6 units, `U1 → U2 → U3 → U4 → U5 → U6`, `validate --require-receipts` **exit 0**, spend
  **146** (was 120; the classification gate is opus/high).
- Workflow: re-emitted — 6 agents, 0 `parallel()`, peak fan-out 1, within the concurrency cap.

**Blocked: NO.** Zero unresolved P0/P1.
