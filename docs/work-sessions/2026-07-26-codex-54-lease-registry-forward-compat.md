# Work session — codex#54 lease-registry forward-compatibility

**Issue:** [infiquetra/infiquetra-codex-plugins#54](https://github.com/infiquetra/infiquetra-codex-plugins/issues/54)
**Plan:** `docs/plans/2026-07-26-codex-54-lease-registry-forward-compat-plan.md`
**Doc review:** `docs/reviews/2026-07-26-codex-54-forward-compat-plan-doc-review.md` (not blocked)
**Branch:** `work/54-lease-registry-forward-compat` from `main` at `d0982fe`
**Backend:** inline · **Destination:** merge

## What was built, by unit

**U1 — tolerance primitives.** `_tolerant_mapping` returning `(known, extras)`,
`_extras_serialized_size`, the 64 KiB document-total constant and its 4x archived-fence sibling, the
`field` import, and the `_closed_mapping` docstring rewritten to state why four sites stay strict.
No call-site changes.

**U2 — extras on six record types.** `extras: dict[str, Any] = field(default_factory=dict)` on
`Lease`, `SettlementRecord`, `ResourceFence`, `SessionAdmission`, `OwnerAdmissionClose`, and
`Registry`; exactly six `_closed_mapping` call sites converted; merge-last `result.update(self.extras)`
in each `to_dict`; the document-total cap enforced in `Registry.from_dict`.

**U3 — the archive commit.** `replace(head, close_receipt=close)` at the settlement-close CAS, plus
`_read_bounded_archived_fence_payload` and `_validated_archived_fence` wired into both sidecar read
paths.

**U4 — operator surface.** `_extras_inventory`, `_document_extras_bytes`, `_strip_extras`,
`LeaseBroker.doctor`, `LeaseBroker.repair`, `LeaseBroker._backup_registry` on the authority;
`doctor` and `repair --strip-unknown` subparsers with the exit-code seam on the adapter.

**U5 — guard, manifest, release.** `test_isolation_is_not_ported_ktd5`, the port manifest and its
per-port pytest contract, release surfaces for one release unit, and two journal entries.

**U6 — deferred to post-merge.** See "What is not done" below.

## Decisions taken during execution

**The frozen source range is `4eb2fe15..1648a21b`, not a wider range ending at `origin/main`.**
`1648a21b` *is* the claude#617 merge; `4eb2fe15` is its parent. Two measurements made this the
right range rather than a convenient one: `git diff 1648a21b..b464d090` over both pathspecs is
**empty** (so the narrow range is not stale), and every symbol R10 excludes as unrelated claude
drift already exists at `4eb2fe15` (so it is outside the diff the contract derives rows from). The
R10 exclusion is therefore enforced structurally by the range, not by reviewer discipline. Recorded
in DECISIONS; both measurements pinned in the per-port contract.

**`FencingToken` is strict at its embedding sites, not inside `from_dict`.** The plan described it as
"a fifth strict boundary reached by its own inline path". Reading the code, `FencingToken.from_dict`
uses `data.get()` and does **not** reject unknown keys — in claude either. The exact
`{broker_epoch, fencing_sequence}` shape is pinned by an inline check at each site that embeds a
token. The R6 regression test was retargeted accordingly, and upstream's audit-verdict comment was
ported onto the codex `from_dict` so a later reader does not "helpfully" add tolerance there.

**The legacy-shape probes stay exact-match.** `ResourceFence.from_dict`'s
`if set(raw) == _LEGACY_FENCE_KEYS` means a legacy-shaped record that *also* carries extras is not
recognized as legacy and fails on the missing `close_receipt`. Upstream made the same choice; it is
mirrored verbatim per KTD2 rather than "fixed", because diverging would be a codex-first change to
shared mechanism. The combination does not arise on the actual cross-runtime path (claude writes
current-shape fences).

**Extras are inside `settlement_sha256`.** `SettlementRecord.settlement_sha256` digests
`self.to_dict()`, which now merges extras. This is the fail-safe direction and matches upstream: a
reader that *dropped* extras would compute a different digest than the writer, so tolerance actually
removes a latent digest divergence rather than creating one.

## Verification

All runs use `PYTHONPATH=. uv run pytest`; the other two obvious invocations fail collection in this
repo (`uv run pytest` → 11 errors; `python3 -m pytest` → 16 errors including a missing `PIL`).

**Baseline established, not assumed.** A clean detached worktree at the pristine `d0982fe` running
the identical selection gives **1 failed, 2309 passed, 4 skipped**. The one failure,
`tests/test_outcome_cross_runtime.py::TestAttachedAdvance::test_frontier_change_halts_rather_than_broadening`,
passes when run alone — it is collection-order dependent and pre-existing. See "Findings not in
scope".

**Neuter probes.** Both load-bearing tests were proven load-bearing:

| Mutation | Observed |
|---|---|
| Revert the `Lease` container to `_closed_mapping` | 4 failed, 3 passed — both the `isolation` and synthetic-key parameters red, the other five container tests still green |
| Restore the pre-#617 `ResourceFence(...)` rebuild at the archive commit | 1 failed, `KeyError: 'carried_forward'` |

The second is the whole point of U3: the preserved field is dropped at exactly the commit that
archives the fence, and nothing else in the module notices.

**Full suite, clean detached worktree:** `2781 passed, 8 skipped, 0 failed` (3m46s).

**The gate command needs `CODEX_PORT_SOURCE_REPO`.** Four of this port's contract tests — the
`expected_count`/`inventory_sha256` derivation guard, the every-changed-path-has-a-row guard, the
range-not-stale guard, and the drift-predates-the-range guard — resolve the claude checkout via
`ROOT.parent / "infiquetra-claude-plugins"`, which does not exist from inside a detached worktree.
They therefore **skip silently** in the clean-worktree gate, and those are the most load-bearing
tests in the module. Four of the eight skips in the run above are exactly these. With the env var
set they run: `12 passed, 0 skipped` for this module, and `69 passed` across all five per-port
contracts. The same pattern and the same env var already govern the codex#45 contract.

```bash
CODEX_PORT_SOURCE_REPO=<claude-clone> PYTHONPATH=. uv run pytest -q
```

**Port contract.** `validate --stage classification` and `--stage unit` for U1, U2, U3, U4 all
report valid. `verify-source` re-derives the frozen inventory from the claude checkout and matches.
`expected_count` (2) and `inventory_sha256` are derived by `port_contract.py init`, never
hand-written — the per-port contract re-derives both and requires an exact match, which is the
guard codex#45's P1 #5 lacked.

**Plugin validator.** `scripts/validate_codex_plugins.py` passes in a clean worktree. It fails in
the primary tree only on the untracked `.claude/` path (codex#56).

**R9.** `isolation` appears 0 times in both brokers, asserted in the unit suite and again in the
per-port contract.

## D8 — the registry-parity check, resolved

The doc review left open what parity mechanism this repo actually has, warning against assuming a
claude-style `marketplace.json`. Measured:

`.agents/plugins/marketplace.json` exists but carries **no versions** — only name, source, policy,
and category. Version parity is enforced instead by a hard-coded `TARGET_EXPECTED_PLUGINS` table in
`scripts/validate_codex_plugins.py`, compared against each `plugins/<p>/.codex-plugin/plugin.json`
and against `docs/validation/saga-family-target-inventory.json`.

A version bump therefore touches **seven** live locations, not the four the plan named:

1. `plugins/fleet-core/.codex-plugin/plugin.json`
2. `plugins/saga/.codex-plugin/plugin.json`
3. `scripts/validate_codex_plugins.py` (`TARGET_EXPECTED_PLUGINS`)
4. `docs/validation/saga-family-target-inventory.json`
5. `plugins/saga/tests/test_codex_operator_choice.py` (an explicit version drift guard)
6. `README.md`
7. `docs/saga/generated/lifecycle-facts.json` (regenerated via `scripts/build_saga_docs_facts.py`)

Two files that also contain the old version strings were deliberately **left alone**:
`docs/validation/codex-627-seam-refreeze-u8-cutover.json` and `-u8-install.json` are frozen evidence
recording what was true at codex#45. `MODERNIZATION_CUTOVER_VERSIONS` is likewise a frozen July-11
receipt and is documented as such in the validator.

There is also a digest-bound content inventory
(`docs/validation/verified-workflows-legacy-token-inventory.json`, 135 entries) whose per-file
digests and rollup must be regenerated when tracked content changes, with
`LEGACY_WORKFLOW_HISTORICAL_INVENTORY_SHA256` updated to match. The regenerated delta was exactly
the 7 files edited here plus the rollup — no paths added or removed.

## A latent defect the version bump exposed

Bumping the plugin versions turned **two previously green prior-port contracts red**, in a clean
worktree, with everything else passing:

- `tests/test_codex_627_seam_refreeze_port_contract.py:388` —
  `assert policy["target_codex_version"] == installed.split("+codex.")[0]`
- `tests/test_outcome_cross_runtime_parity_port_contract.py:303` —
  `assert manifest_version.split("+codex.")[0] == "0.80.0"`

Both bind a *prior* port's **target** version to the repo's **live** version. That equality holds
only while the repo stays frozen at that port's release, so the Nth port to bump a version breaks
all N−1 prior contracts. Nothing was wrong with this port; the older gates encoded "nothing has
happened since" as an invariant. The codex#45 docstring anticipated the *direction* of change but
not that anything would move past it.

Both were changed to the monotone form — `live >= target` — which is what a completed port can
honestly still claim: its release landed and has not been reverted. Every other assertion in those
contracts is untouched, including the policy's own `current_codex_version` before-story and the
inventory/CHANGELOG agreement, because those are genuinely frozen facts.

This is per-port pytest gates, not the shared `scripts/port_contract.py` validator — KTD6's
prohibition on unfreezing the sealed CLI validator is respected.

**How it surfaced matters.** Only the full-suite run in a clean worktree caught it. Every targeted
per-unit run was green, and so was the narrower `plugins/ tests/` selection taken before the bump. A
gate scoped to "the files I touched" would have shipped it. Recorded in LEARNINGS.

## Findings not in scope

**Pre-existing collection-order failure.**
`tests/test_outcome_cross_runtime.py::TestAttachedAdvance::test_frontier_change_halts_rather_than_broadening`
fails inside the suite but passes alone, **in a clean worktree at the pristine `d0982fe`**. This is
the codex#45 P1 #3 defect class — `_load()` overwrites `sys.modules[name]`, so the last loader wins
while captured module globals point at orphaned modules. The `_pin_script_modules` repair from that
round evidently does not cover this module. Not introduced here and not fixed here; it warrants its
own defect. `/work` does not file issues — `mission-control` owns that.

**codex#56 remains the reason full-suite gates need a clean worktree.**
`scripts/build_legacy_workflow_inventory.py` refuses to run while the untracked `.claude/` path is
present, which also blocks `validate_codex_plugins.py` in the primary tree. Regenerating the
inventory required a clean worktree overlaid with the working-tree changes.

## What is not done

**U6 — the cross-runtime acceptance harness — has not run.** By design: this repo merges with merge
commits, `require_clean_pinned` pins an exact SHA, and objective infiquetra-claude-plugins#639
clause 3 needs the *shipped* state proven. A bundle produced at the branch head would describe a
commit that never lands. U6 runs against the post-merge `main` SHA and its bundle is committed as
follow-up evidence.

**Clause 3 is therefore not yet discharged**, and clause 2 of that objective's Definition of Done —
a governed armed-hook Workflow run completing end to end — is separately unevidenced and is not
touched by this work.

**`--stage cutover` was not attempted.** It is structurally blocked at
`plugins/saga/scripts/external_action_release_matrix.py:697-701`, which raises on the proof's own
`content_sha256` before `_validate_expected_ref` (`:716-720`) is reached. No evidence tag was
created and no release run was fabricated.

## Rollback

The down-migration is the feature's own `repair --strip-unknown`: it backs the registry up to a 0600
sibling, clears every preserved mapping, and returns the document to its pre-port shape. A reader
that has not been upgraded is unaffected either way, because an extras-free document serializes
byte-identically before and after (R8, pinned by
`test_extras_free_document_is_byte_identical_across_a_read_write_cycle`).

## Next step

Open the PR, then run `/code-review` before merge. U6 after merge.
