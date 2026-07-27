# Code review — codex#54 lease-registry forward-compatibility

**Target:** PR [#60](https://github.com/infiquetra/infiquetra-codex-plugins/pull/60), branch
`work/54-lease-registry-forward-compat`
**Reviewed SHA:** `cd6c53ae9f71659c823b5dfd2d5aa238709fe0c0`
**Diff base:** `d0982fec60465b35e3ae5a15cf5e69197e4bf7f5` (merge-base with `origin/main`, re-derived after
`git fetch`)
**Mode:** programmatic / report-only · **Backend:** inline
**Excluded from review:** untracked `.claude/` (codex#56) — not in `git diff`, not reviewed

## Verdict

**CLEAN** — 0 P0, 0 P1, 2 P2, 3 P3. Nothing blocks merge.

Scope check: **CLEAN**. The two prior-port contract edits are a necessary consequence of the R12
version bump, not unrelated drift.

## Findings

| # | Pri | File | Issue | Confidence | Route |
|---|---|---|---|---|---|
| 1 | P2 | `plugins/fleet-core/tests/test_lease_broker.py:1986` | The R8 golden pin asserts strictly less than its name claims | 100 | safe_auto |
| 2 | P2 | `plugins/fleet-core/scripts/fleet_commons/lease_broker.py:1116` | Settlement extras diverge `settlement_sha256`, wedging three fail-closed paths | 100 | advisory (upstream) |
| 3 | P3 | `plugins/fleet-core/CHANGELOG.md` | Over-generalizes `doctor`'s never-raises property | 100 | safe_auto |
| 4 | P3 | `tests/test_lease_registry_forward_compat_port_contract.py:69` | This port's strongest oracles skip by default in the authoritative gate | 100 | manual |
| 5 | P3 | `plugins/fleet-core/scripts/fleet_commons/lease_broker.py:2220` | `configure_session_admission` drops extras on a contract change | 100 | advisory (upstream) |

### 1 (P2) — The R8 golden pin asserts strictly less than its name claims

`test_extras_free_document_is_byte_identical_across_a_read_write_cycle` compares
`json.dumps(parsed.to_dict(), sort_keys=True)` against
`json.dumps(json.loads(before), sort_keys=True)` (`:1986-1988`). **Both sides are re-serialized
through the same canonicalizer**, so the assertion proves semantic mapping equality — not byte
identity against `before`. The comment at `:1985` nonetheless says "reproduces the on-disk bytes
exactly", and the test name says `byte_identical`. There is also no post-write byte comparison
despite `across_a_read_write_cycle`: the `renew()` at `:1989` writes, but nothing re-reads.

**The underlying property does hold** — verified by probe. The write path serializes with
`json.dumps(payload, indent=2, sort_keys=True) + "\n"` (`lease_broker.py:1821`), and

```python
(json.dumps(parsed.to_dict(), indent=2, sort_keys=True) + "\n").encode("utf-8") == before
```

returns `True`. So R8 is genuinely satisfied and this is a pin-strength issue, not a correctness one.

P2 rather than P3 because this is the *named golden pin* for a stated requirement in a repo with **no
CI**. An overclaiming test name is exactly how a later reader concludes something is pinned when it
is not. Fix is the one-line stronger assertion above.

### 2 (P2) — Settlement extras diverge `settlement_sha256`, wedging three fail-closed paths

`SettlementRecord.to_dict()` merges extras (`:1112`) and `settlement_sha256` digests `to_dict()`
(`:1116-1122`). Demonstrated: the same record with one added unknown field produces a different
digest (`ca4e23e0…` vs `1629075…`).

Three sites compare a prepare-time in-memory record against a re-read one:

| Site | Comparison | Effect on divergence |
|---|---|---|
| `:3566` | `persisted.settlement_sha256 != settlement.settlement_sha256` | rollback raises `LeaseOwnershipError` |
| `:4481` | `close["settlement_sha256"] == settlement.settlement_sha256` | close-receipt binding returns `False` |
| `:4553` | `handler.settlement.settlement_sha256 != settlement.settlement_sha256` | recovery raises `LeaseOwnershipError` |

So a foreign runtime writing an unknown field onto a live `settlements.<digest>` record between
prepare and commit would wedge rollback and recovery for that settlement.

**This is fail-CLOSED, never a forge** — the driver's judgment on the forge question is correct. It
is nonetheless a liveness hazard the plan did not name.

**Not a port defect.** Upstream claude is identical (`to_dict` merges extras at `:1143`,
`settlement_sha256` reads `to_dict()` at `:1150`). Per KTD5 upstream-first, any change is an
**upstream issue against infiquetra-claude-plugins**, never a codex-first fix. No current trigger
exists: claude#616 writes `isolation` onto lease records only, and nothing writes settlement extras
today.

### 3 (P3) — CHANGELOG over-generalizes `doctor`'s never-raises property

`plugins/fleet-core/CHANGELOG.md` says `doctor` "reports a corrupt document as *data* rather than
raising, so an operator diagnostic never aborts on the state it exists to diagnose."

Demonstrated: `doctor()` against a `0644` registry raises `UnsafeAuthorityError` — it catches only
`RegistryCorruptError`. Through the adapter that is a `LeaseBrokerError`, so it hits
`except (authority.LeaseBrokerError, …)` → `_die` → **exit 2**, outside the documented `0/3/4` seam,
with no JSON on stdout.

The first clause is precise; the second over-generalizes, because a world-readable registry *is* a
state an operator would run `doctor` to diagnose. The in-code comment is correctly scoped ("never
raises **for a corrupt document**") and matches upstream verbatim, as does the behavior — so only
the CHANGELOG sentence is codex-owned and worth narrowing.

### 4 (P3) — This port's strongest oracles skip by default in the authoritative gate

`DEFAULT_SOURCE_REPO = ROOT.parent / "infiquetra-claude-plugins"` (`:69-72`) does not resolve from
inside a detached worktree — and a clean detached worktree is exactly where this repo runs its
authoritative full-suite gate. Four tests therefore skip silently there, and they are the most
load-bearing in the module:

- `test_expected_count_and_inventory_digest_are_derived_not_hand_written` (the guard against
  codex#45's P1 #5)
- `test_every_changed_source_path_has_a_row`
- `test_frozen_target_is_byte_equivalent_to_claude_origin_main_for_these_paths`
- `test_excluded_drift_predates_the_frozen_range`

Measured: 8 skips in the gate run; with `CODEX_PORT_SOURCE_REPO` set this module is 12 passed / 0
skipped and all five per-port contracts total 69 passed.

`pre_existing: partial` — the codex#45 contract established the same env-var pattern with the same
property; this PR adds four more silently-skipping tests to it. Mitigated: the work session documents
the required gate command. A more robust default resolution would remove the footgun.

**Scope is broader than first assessed.** Re-running the full suite with the env var set gives
**2789 passed, 0 skipped** against 2781 passed / 8 skipped without it. All eight skips were
frozen-source oracles across the five per-port contracts — not only this port's four. The repo's
default gate has therefore been silently skipping every cross-repo oracle it owns, in every port.
That is a pre-existing repo-wide property this PR inherits rather than creates, and it is the
strongest argument for making the env var part of the standing gate command.

### 5 (P3) — `configure_session_admission` drops extras on a contract change

At `:2220-2229`, when an existing admission's contract differs and it is not live, the code
constructs a fresh `SessionAdmission(...)` with default `extras={}` and overwrites at `:2229`,
dropping any preserved field. `close_owner_admission` by contrast returns early on an existing record
(`:3682-3684`) and never drops.

Upstream claude is byte-identical here (`:2249-2258`), so this is a faithful mirror. It is also
defensible by design — a different contract is a new pin, and carrying the old pin's additive fields
onto it would be questionable. Recorded as an asymmetry against U3's preserve-across-close behavior,
not as a bug.

## What was verified and held

**The six/four boundary split — the whole correctness argument.** Exactly four `_closed_mapping`
sites remain (`:427` worktree resource_ref, `:675` settlement close, `:756` legacy settlement close,
`:4405` settlement recovery intent) and exactly six `_tolerant_mapping` sites exist. No strict site
was widened.

**`FencingToken` — the fifth strict boundary.** All four `FencingToken.from_dict` call sites
(`:685`, `:766`, `:1047`, `:4420`) are immediately preceded by an inline exact-shape check
(`:680`, `:761`, `:1042`, `:4415`). Every embedding site is guarded — the boundary an audit sweeping
only `_closed_mapping` would miss.

**No uncapped path into extras.** `ResourceFence.from_dict` has exactly two call sites: `:1384`
inside `Registry.from_dict` (capped by the document total at `:1434`) and `:1965` inside
`_validated_archived_fence` (capped per-record at `:1966`). Both archived read paths go through the
bounded reader and the validated wrapper.

**The commit-path repair.** The CAS guard runs before the in-place close; `_make_resource_current`'s
rebuild at `:2337` is correctly left as a rebuild (it mints a new fence; there is no head to
preserve) and matches upstream. All six construction sites of extras-bearing types were audited —
`:1532` is `_strip_extras` (deliberate), `:3692` returns early on an existing record, and the
remainder mint genuinely new records. Finding 5 is the one residual.

**`repair` write discipline.** `_locked()` is held across the whole read-decide-write; strict
revalidation runs before the write and refuses without mutating; the backup is taken before the write
and captures the exact pre-repair bytes under the same temp + rename + fsync + 0600 discipline as
every other write path.

**The frozen-range argument — both measurements re-derived independently.**
`git diff 1648a21b..b464d090` over both pathspecs is empty (the range is not stale), and all four
excluded-drift symbols exist at `4eb2fe15` (they precede the range and cannot land under a row). The
classification narrative holds.

**Manifest integrity.** `expected_count` (2) and `inventory_sha256` re-derived from the source diff
and both match. All four evidence `artifact_sha256`, the capability-snapshot `sha256`, and the
capability-schema `sha256` match disk. Every evidence entry carries `cwd: "."` and `exit_code: 0`.

**Release-surface completeness.** All seven live surfaces bumped. The only remaining old-version
strings are the new port's own `current_codex_version` fields (correctly recording the before state)
and the two frozen codex#45 evidence files — correctly untouched. The legacy-token inventory
regenerated to exactly the 7 tracked files edited, no paths added or removed, 135 entries, and
`LEGACY_WORKFLOW_HISTORICAL_INVENTORY_SHA256` agrees with the rollup.

**The prior-port contract edits (adjudicated).** The change is minimal and surgical: only the
equality line changed in each. Every other assertion survives — the policy's own
`current_codex_version` baseline pin, `release_unit == "U6"`, the inventory/manifest agreement, and
the historical `## 0.80.0` CHANGELOG entry (which still holds because 0.81.0 was prepended, not
substituted). The monotone form is the right call: equality encoded "nothing has happened since" as
an invariant, which no completed port can claim. The driver's KTD6 reading is **correct** —
`scripts/port_contract.py` is not in the diff, so the sealed CLI validator was not unfrozen; these
are per-port pytest gates, the layer intended to be maintained.

**Honesty on acceptance.** Nothing in the diff, the CHANGELOGs, the work session, or the PR body
claims objective infiquetra-claude-plugins#639 clause 3 is discharged. Both the work session and the
PR body state explicitly that it is not.

## Built-vs-planned

| Req | State | Evidence |
|---|---|---|
| R1 six boundaries tolerate | DONE | 6 `_tolerant_mapping` sites; AC1 verified verbatim |
| R2 byte-faithful round-trip | DONE | AC2 verified verbatim |
| R3 generic tolerance | DONE | AC3 verified; synthetic-key test; no runtime literals in the broker |
| R4 bounded, fails closed | DONE | `:1434` document total, `:1966` per-record; capacity tests |
| R5 missing required fails closed | DONE | `_tolerant_mapping` raises; per-site parametrized test |
| R6 five strict boundaries | DONE | 4 `_closed_mapping` + `FencingToken` at all 4 embedding sites |
| R7 survives settlement/archive commit | DONE | archived record read back off disk; neuter probe red |
| R8 byte-identical without extras | DONE (pin weak) | property verified true by probe; see finding 1 |
| R9 `isolation` not ported | DONE | 0 occurrences in both brokers; `test_isolation_is_not_ported_ktd5` |
| R10 unrelated drift not ported | DONE | enforced structurally by the frozen range; re-derived |
| R11 operator surface | DONE | `doctor`/`repair` + exit-code seam; 9 new CLI tests |
| R12 manifest, contract, release | DONE | all digests re-derived; 7 live surfaces bumped |
| R13 acceptance harness | NOT-DONE (deliberate) | post-merge by design; honestly documented |

KTD1–KTD8 all honored. KTD6 independently confirmed: `scripts/port_contract.py` is absent from the
diff.

## Coverage and residual risk

**Suppressed:** 0 findings below anchor 75.

**Not independently re-derived:** the two neuter probes were run and observed by the driver in
session (Lease → `_closed_mapping` produced 4 red / 5 container tests still green; restoring the
rebuild produced `KeyError: 'carried_forward'`). They were not re-executed by this pass, since
re-running requires mutating the source; the reported outputs were directly observed rather than
self-reported by a subagent.

**No CI.** `.github` exists, `.github/workflows` does not. Every gate is local-only — nothing catches
a regression after merge. This weighted findings 1 and 4 upward: a weak pin and a silently-skipping
oracle are worth more here than in a repo with post-merge coverage.

**Pre-existing, out of scope, confirmed not this branch's:**
`tests/test_outcome_cross_runtime.py::TestAttachedAdvance::test_frontier_change_halts_rather_than_broadening`
fails inside the suite and passes alone, reproducing in a clean worktree at the pristine `d0982fe`
(the test alone passes; its whole module alone passes 125). codex#45 P1 #3 defect class.

**Two findings route upstream** (2 and 5). Both are faithful mirrors of claude `b464d090`; per KTD5
neither may be fixed codex-first.

## Routing and disposition

`/code-review` is a gate, not a fixer — it made no code change. The dispositions below were applied
afterward by `/work`, which owns fixes, and are recorded here for custody.

| # | Pri | Disposition |
|---|---|---|
| 1 | P2 | **fixed** — assertion strengthened to true byte identity against the on-disk bytes using the write path's own serialization, plus a second comparison after a real mutating write (`renew`), so `across_a_read_write_cycle` is now literally tested. 104 passed. |
| 2 | P2 | **routed upstream** — faithful mirror of claude `b464d090`; KTD5 forbids a codex-first fix. No current trigger. |
| 3 | P3 | **fixed** — the fleet-core CHANGELOG now states the bound explicitly: only `RegistryCorruptError` is caught, an unsafe-mode authority still raises `UnsafeAuthorityError` and surfaces as exit 2, and that is deliberate. |
| 4 | P3 | **documented** — the work session records `CODEX_PORT_SOURCE_REPO` as part of the gate command. A more robust default resolution remains available as follow-up. |
| 5 | P3 | **routed upstream** — byte-identical to claude; defensible by design. |

No P0/P1 were found, so the merge gate is satisfied. `/qa` is the next gate; U6 runs post-merge.

**Verified after the fixes:** `plugins/fleet-core/tests/test_lease_broker.py` 104 passed; ruff check
and format clean; the legacy-token inventory regenerated (only the fleet-core CHANGELOG's content
digest moved, the historical rollup is unchanged and still agrees with
`LEGACY_WORKFLOW_HISTORICAL_INVENTORY_SHA256`); `validate_codex_plugins` passes in a clean worktree;
full suite re-run in a clean worktree **with `CODEX_PORT_SOURCE_REPO` set**, so this port's four
frozen-source oracles executed rather than skipping.
