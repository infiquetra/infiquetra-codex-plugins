---
title: codex#54 — Lease Registry Forward-Compatibility (port of claude#617)
type: fix
status: active
date: 2026-07-26
deepened: 2026-07-26
origin: https://github.com/infiquetra/infiquetra-codex-plugins/issues/54
---

# codex#54 — Lease Registry Forward-Compatibility (port of claude#617)

## Summary

Port claude#617's bounded forward-compatibility into the codex lease registry so the reader preserves
fields it does not recognize instead of raising `RegistryCorruptError`, restoring cross-runtime handoff
from Claude and discharging clause 3 of objective infiquetra-claude-plugins#639.

The port is a **selective semantic mirror**: roughly 340 of the 528 lines by which claude's broker
exceeds codex's are in scope, and the remaining ~190 must be deliberately excluded.

## Problem Frame

Claude writes an `isolation` field into every lease record (claude#616). Codex's registry reader
rejects any unrecognized field outright, so every cross-runtime handoff from Claude fails.

Measured 2026-07-26 at pins claude `b464d090` x codex `d0982fe`, the acceptance bundle
`docs/validation/governed-execution-integrity/cross-runtime-acceptance.json` in
infiquetra-claude-plugins (commit `b11d2df3`, sha256 `c91eaa38…`) records `overall_verdict: fail`,
12 of 14 scenarios passing. Both failures are `RegistryCorruptError: leases.<id>: unknown field(s):
isolation`, and both land on the codex read side.

The asymmetry is the mechanism. Claude tolerates a record *missing* `isolation`, so codex→claude
survives; codex has no tolerance for one *carrying* it, so claude→codex hard-fails.

This is not a regression from codex#45. That work re-froze the #627 seam and never touched the
registry schema; the red is new because *claude* moved. The same bundle confirms #45 succeeded —
`race-codex-first` and `race-simultaneous` both pass, the two legs claude#628 documented as failing.

## Grounding

All measurements taken 2026-07-26 against codex `d0982fe` and claude `b464d090`.

### There is one broker implementation, not two

`git ls-files` reports two `lease_broker.py` files per repo, but they are **authority and adapter**,
not duplicates:

| Path | Role | codex | claude |
|---|---|---|---|
| `plugins/fleet-core/scripts/fleet_commons/lease_broker.py` | the authority | 4249 lines | 4731 lines |
| `plugins/saga/scripts/lease_broker.py` | thin adapter + operator CLI | 542 lines | 582 lines |

The adapter opens with `authority = fleet_commons_shim.load("lease_broker")` and does no parsing of
its own, so it cannot drift on schema. Its only #54-relevant gap is the operator CLI surface.

There is no vendored second copy and no drift-guard test binding the two — `fleet_commons_shim.py`
exists in six copies as the *loader*, which is a different mechanism.

### The rejection is a six-site discipline, not one line

Codex's `_closed_mapping` (`plugins/fleet-core/scripts/fleet_commons/lease_broker.py:345`) raises on
any unknown key. It has 11 call sites. Claude's #617 converted exactly **six** of them to a new
`_tolerant_mapping` and deliberately left the other four strict:

| Call site | codex | claude | disposition |
|---|---|---|---|
| `leases.<id>` | `:846` closed | `:933` tolerant | **convert** |
| `settlements.<digest>` | `:971` closed | `:1068` tolerant | **convert** |
| `resource_fences.<digest>` | `:1069` closed | `:1173` tolerant | **convert** |
| `session_admission` | `:1141` closed | `:1251` tolerant | **convert** |
| `closed_owner_admission` | `:1198` closed | `:1314` tolerant | **convert** |
| `registry` (top level) | `:1254` closed | `:1381` tolerant | **convert** |
| `worktree resource_ref` | `:376` closed | `:447` closed | keep strict |
| `settlement close` | `:619` closed | `:698` closed | keep strict |
| `legacy settlement close` | `:700` closed | `:781` closed | keep strict |
| `settlement recovery intent` | `:4073` closed | `:4555` closed | keep strict |

The retained-strict four are digest-covered commitment records and hash-bound resource references.
Claude's `_closed_mapping` docstring (`:375-383`) states the rule directly: every byte is semantics
there, so tolerance would break the digest.

`FencingToken` is a **fifth** strict boundary reached by its own path rather than by
`_closed_mapping`. Claude `:664` marks it explicitly: *"STRICT / no extras (#617 R4/KTD1 audit verdict
— default closed): the token is embedded…"*. It is strict for the same reason and must stay so.

Two other `_KEYS` sets are not parse boundaries and need no change: `_LEGACY_FENCE_KEYS` is a
`set(raw) == …` legacy-shape probe inside `ResourceFence.from_dict` (codex `:1067`), and
`_AGENT_RESOURCE_KEYS` is checked inline in `canonical_resource_ref`.

### Codex carries no content claude lacks

The raw diff reports 59 hunks, +528 / −46. The −46 reads as "codex-exclusive content a byte-copy
would destroy," and that reading is **wrong**. Every symbol tested is present in both files:

```
record_parent_completed  BOTH      _closed_mapping   BOTH      ResourceFence  BOTH
parent_completed_at      BOTH      close_receipt     BOTH      _TOP_KEYS      BOTH
child_terminal_at        BOTH      tool_use_id       BOTH      _FENCE_KEYS    BOTH
agent_id                 BOTH      fencing_sequence  BOTH      _LEASE_KEYS    BOTH
```

All 46 removed lines are one half of a modification pair. The largest — `from dataclasses import
dataclass, replace` → `dataclass, field, replace` — is the `field` import that `extras:
dict[str, Any] = field(default_factory=dict)` needs.

Neither broker contains `RUNTIME_LABEL` or any `"codex"` / `"claude"` literal, so unlike
`outcome_compat.py` there is no runtime-identity divergence to preserve.

### What the 528 added lines actually are

Grouped by enclosing definition:

| Group | Lines | In scope |
|---|---|---|
| Tolerance core — `_tolerant_mapping`, `_extras_*`, `_strip_extras`, six `from_dict`/`to_dict` pairs, `Registry` document cap, capacity constants | ~215 | **yes** |
| Operator surface — `LeaseBroker.doctor` (38), `.repair` (44), `._backup_registry` (42) | ~124 | **yes** |
| `#616` isolation — `_agent_isolation` (15) plus the `claim` kwarg | ~21–30 | **no** (forbidden) |
| Unrelated claude drift — `_renew_batch_member` (31), `_renew_live_batch_siblings` (25), `record_child_terminal` (14), `record_parent_completed` `spawn_failed` (13), `assert_write_target` (6) | ~89 | **no** (no contract row) |

Codex already has `assert_write_target`, `_canonical_json`, and `_record_sha256`. It lacks
`_backup_registry`, `_renew_batch_member`, `_renew_live_batch_siblings`,
`_read_bounded_archived_fence_payload`, and `_validated_archived_fence`.

### Codex is already in the extras-dropping shape at the commit path

Claude `:3653-3656` carries the #617 repair with its rationale in-line:

```python
# In-place close of the CAS-verified live head: replace() keeps preserved unknown
# fields (#617 KTD2) — a rebuilt ResourceFence would silently drop a newer writer's
# per-fence extras at exactly the commit that archives the fence.
registry.resource_fences[digest] = replace(head, close_receipt=close)
```

Codex at the same site still rebuilds:

```python
registry.resource_fences[digest] = ResourceFence(
    resource_ref=settlement.resource_ref, broker_epoch=settlement.token.broker_epoch,
    fencing_sequence=settlement.token.fencing_sequence, lease_id=settlement.lease_id,
    close_receipt=close,
)
```

This is the P1 found in claude#617's own review, and codex is sitting on the pre-fix form. The moment
codex gains `extras`, this line becomes an active data-loss bug. U3 is a required co-change, not
cleanup.

### Gating runs through a per-port pytest contract

`scripts/port_contract.py validate` is permanently pinned to the 2026-07-11 external-advisory port —
its `port_id`, refs, row counts, and digests. DECISIONS `2026-07-19: Lease-Safe Substrate Ports
Byte-Faithful, Gates Per-Port` records that release gating therefore runs through a per-port pytest
contract (`tests/test_lease_safe_substrate_port_contract.py`,
`tests/test_codex_627_seam_refreeze_port_contract.py`). This port follows that precedent.

`expected_count` and `inventory_sha256` are derived from the base→target diff over the contract's
pathspecs (`scripts/port_contract.py:437-450`) and are never hand-written.

### Test substrate

| Module | Lines | Role here |
|---|---|---|
| `plugins/fleet-core/tests/test_lease_broker.py` | 1755 | primary for U1, U2, **U3**, U5 — extend, do not mint a sibling |
| `tests/test_saga_lease_broker.py` | 167 | adapter surface (U4) — see the harness gap below |
| `tests/test_lease_settlement_conformance.py` | 279 | **not** a U3 home — see below |

Two substrate facts an implementer will otherwise get wrong:

`tests/test_lease_settlement_conformance.py` is a cross-runtime conformance *matrix* (`#33 U4`) over
digest root-independence, read-view projection, and zero-byte-mutation properties. It carries **zero**
`close_receipt` references and does not exercise the settlement-close/archive path. The only modules
that reference `close_receipt` are `plugins/fleet-core/tests/test_lease_broker.py` (4),
`plugins/fleet-core/tests/test_orphan_evidence.py` (4), and `tests/test_outcome_cross_runtime.py` (1).
U3's tests belong in `test_lease_broker.py`.

`tests/test_saga_lease_broker.py` tests the adapter's *library* surface — protocol gating, admission
snapshots, state-root resolution, receipt round-trips. It contains **no** CLI invocation at all (zero
references to `main`, `argv`, `SystemExit`, or `capsys`). U4's exit-code tests therefore need a new
CLI-invocation harness in that module; `tests/test_capability_degrade.py` is the in-repo pattern to
follow.

### Running the suite — measured 2026-07-26 at `d0982fe`, not carried forward

Only one invocation collects. Both obvious ones fail:

| Invocation | Result |
|---|---|
| `uv run pytest` | 2546 collected, **11 collection errors** |
| `python3 -m pytest` | **16 collection errors**, incl. `ModuleNotFoundError: No module named 'PIL'` |
| **`PYTHONPATH=. uv run pytest`** | **2728 passed, 4 failed** (178s) |

The 4 failures in the primary tree are **environmental, not the branch's**. All four are in
`tests/test_verified_workflows_migration.py`. Proven by re-running that module in a clean detached
worktree at the same SHA:

```
primary tree (carries untracked .claude/):  4 failed
clean detached worktree at d0982fe:        14 passed
```

The cause is codex#56 — `scripts/build_legacy_workflow_inventory.py` refuses to run while the untracked
`.claude/` path is present, so the digest-bound inventory assertions fail. **Run every full-suite gate in
a clean detached worktree**, where the baseline is 2728 passed / 4 skipped / 0 failed. Running it in the
primary tree either sends the implementer chasing four phantom failures or, worse, teaches them to wave
off a failure count that later hides a real one.

**This repo has no CI.** `.github` exists; `.github/workflows` does not. Every gate is local-only and
nothing catches a regression after merge.

## Requirements

**R1.** The codex reader accepts a lease record carrying an unrecognized field without raising, at all
six container boundaries: `leases`, `settlements`, `resource_fences`, `session_admission`,
`closed_owner_admission`, and the top-level `registry` document.

**R2.** Preservation is byte-faithful and round-trips: `from_dict(rec).to_dict() == rec` for any record
whose unknown fields are within capacity.

**R3.** Tolerance is generic. The codex broker names no claude-specific field; a synthetic field
present in neither runtime is preserved identically to `isolation`.

**R4.** Tolerance is bounded. The summed serialized size of all preserved unknown mappings across a
document is capped, and a document exceeding it fails closed with a typed registry error rather than
truncating. Archived closed fences, which bypass the document-total cap, are bounded per record.

**R5.** Missing *required* keys still fail closed with the existing error. Only additive unknown keys
are tolerated.

**R6.** The five digest-covered / hash-bound boundaries stay strictly closed: the four retained
`_closed_mapping` sites (`worktree resource_ref`, `settlement close`, `legacy settlement close`,
`settlement recovery intent`) and `FencingToken`, which is strict via its own inline path.

**R7.** Preserved fields survive the settlement/archive commit path, not merely `from_dict` →
`to_dict`.

**R8.** A document with no unknown fields serializes byte-identically to its pre-port output.

**R9.** The `#616` isolation surface is **not** ported. No `isolation` identifier appears in the codex
broker, and the exclusion is pinned by a named guard test.

**R10.** The ~89 lines of unrelated claude drift (batch renewal, `spawn_failed`, `record_child_terminal`)
are not ported. They belong to no contract row in this port.

**R11.** The operator surface ships: a read-only `doctor` reporting preserved fields by JSON path with
a distinct exit-code seam, and a `repair` that performs no default action and requires an explicit
`--strip-unknown` flag, taking a backup before stripping.

**R12.** A port manifest under `docs/portability/ports/` pins the exact pathspecs, with `expected_count`
and `inventory_sha256` derived; a per-port pytest contract gates it; release surfaces
(`.codex-plugin/plugin.json`, `CHANGELOG.md`) are updated in the same PR.

**R13.** The cross-runtime acceptance harness reports `overall_verdict: pass` with both
`handoff-negatives-*` green and no regression against the 12/14 baseline in bundle `c91eaa38…`.

## Key Technical Decisions

**KTD1 — Selective semantic mirror, not a byte-copy; and the reason is the inverse of the issue's
premise.** The issue anticipated that codex carries content claude lacks. It does not — every tested
symbol is in both files and all 46 removed lines are modification pairs. A byte-copy is mechanically
viable. It is nonetheless **rejected**, because claude's file carries ~21–30 lines of `#616` isolation
semantics that this port is forbidden to import (R9) and ~89 lines of unrelated drift that would land
under no contract row — precisely the defect class codex#45's review flagged as P1 #5. The constraint
is what claude carries that codex must *not* receive, not what codex would lose.

**KTD2 — Convert exactly six `_closed_mapping` sites; keep four strict.** Tolerance applies to
container mappings holding mutable state. It must not apply to digest-covered commitment records or
hash-bound resource references, where an unknown byte changes the hash and a preserved-then-replayed
field would forge a commitment. Mirror claude's split verbatim rather than re-deriving it.

**KTD3 — In-place `replace()` at the archive commit, never a rebuild.** Codex's current rebuild at the
settlement-close CAS silently drops per-fence extras at exactly the commit that archives the fence.
Ship the `replace(head, close_receipt=close)` form together with the tolerance, in the same unit.

**KTD4 — Bounded capacity with a separate archived-fence bound.** One document-total constant enforced
in `Registry.from_dict`, plus a per-record bound on archived closed fences, which are read through a
sidecar path that bypasses the document total and would otherwise be an uncapped channel. Over-capacity
fails closed with a typed error; it never truncates.

**KTD5 — Pin the isolation non-port as a named guard test.** Following the precedent in DECISIONS
`2026-07-19: Cross-Runtime Parity Port` KTD6 (the dormant lease seam pinned as
`test_dispatcher_lease_seam_stays_dormant_ktd6`), assert that `isolation` appears nowhere in the codex
broker. Teaching codex the field then requires deleting a named test with a written rationale, not
silent drift. Prose-only deferrals are silently reversible.

**KTD6 — Gate through a per-port pytest contract.** `scripts/port_contract.py validate` is permanently
pinned to the 2026-07-11 external-advisory port, so it cannot gate this manifest. Add
`tests/test_lease_registry_forward_compat_port_contract.py` on the model of the two existing per-port
contracts. Do not edit the shared CLI validator — that would unfreeze a sealed contract, a rejected
alternative in the 2026-07-19 decision.

**KTD7 — The acceptance evidence carries its caveat in the referenced artifact, not in the entry.** The
harness lives in infiquetra-claude-plugins and the port-contract evidence schema cannot express a
cross-repo path (codex#57, open). Two schema facts constrain the shape, both read directly from
`scripts/port_contract.py` at `d0982fe`:

- `:1236` — `if entry.get("cwd") != ".": errors.append(...)`. `cwd` is pinned to the literal `"."`.
- `:1196` — `evidence_keys` is a **closed** set: `evidence_id`, `unit`, `kind`, `artifact_path`,
  `artifact_sha256`, `argv`, `cwd`, `exit_code`, `recorded_at`, `repo_head` (plus optional
  `target_paths`, `target_tree_sha256`).

There is therefore **no field in the entry to hold an annotation** — attempting one fails validation on
an unknown key. The entry records `cwd: "."` and the real `argv`, which will not resolve from this tree;
the explanation lives in the `artifact_path` document the entry points at, which is unconstrained prose.
codex#45 set the precedent that an honest unresolvable path beats a fabricated-but-valid one. Do not
relax `cwd`, do not invent a key, and do not fix #57 here.

**KTD8 — One release unit.** Following DECISIONS `2026-07-26: codex#45 — One Release Unit for a
Five-Row, Two-Manifest Port`, this ships as a single release unit across fleet-core and saga rather
than split versions, because the adapter's CLI verbs are inert without the authority's methods.

## Implementation Units

### U1. Tolerance primitives and capacity constants

Add the mechanism without wiring it to any call site, so the diff that changes behavior stays small.

**Files:** `plugins/fleet-core/scripts/fleet_commons/lease_broker.py`

**Scope:** `_tolerant_mapping` returning `(known, extras)`; `_extras_serialized_size`; the
document-total and archived-fence capacity constants; the `field` import; the `_closed_mapping`
docstring rewrite stating why four sites stay strict. No call site changes.

**Test scenarios** (`plugins/fleet-core/tests/test_lease_broker.py`):
- `_tolerant_mapping` returns known and extras disjointly for a mapping with one unknown key.
- A mapping missing a required key still raises the existing error with the existing message.
- A non-dict value raises `RegistryCorruptError`.
- `_extras_serialized_size({})` is `0`; a populated mapping returns its canonical-JSON UTF-8 length.
- The archived-fence bound is a strict multiple of the document bound (guards a future edit that
  accidentally equalizes them).

**Tier:** sonnet / medium — mechanical, fully specified by the upstream source.

### U2. Extras on the six record types

Thread `extras` through each container record and enforce the document-total cap.

**Depends on:** U1

**Files:** `plugins/fleet-core/scripts/fleet_commons/lease_broker.py`

**Scope:** the `extras: dict[str, Any] = field(default_factory=dict)` dataclass field, the
`_closed_mapping` → `_tolerant_mapping` conversion, the constructor argument, and the merge-last
`result.update(self.extras)` in `to_dict` — for `Lease`, `SettlementRecord`, `ResourceFence`,
`SessionAdmission`, `OwnerAdmissionClose`, and `Registry`. Plus the document-total sum and cap check in
`Registry.from_dict`. The four strict sites are untouched.

**Test scenarios** (`plugins/fleet-core/tests/test_lease_broker.py`). Existing helpers to build on rather
than reinvent: the `broker` and `runtime` fixtures (`:72-78`), `_raw_registry(broker)` (`:120`, returns
the raw dict — the natural vehicle for round-trip and byte-identity assertions), `_agent(...)` (`:86`),
`_worktree_resource(...)` (`:112`), and `_recovery_intent(...)` (`:1029`).

- A lease record carrying `isolation` loads without raising and round-trips byte-identically.
- The same for a synthetic key present in neither runtime — R3's genericity proof.
- One test per container type, so a missed record type cannot hide behind the lease case passing.
- A record with no extras serializes byte-identically to the pre-port output (R8 golden pin).
- A missing required key still fails closed at every converted site.
- All five strict boundaries still reject an unknown key — the four retained `_closed_mapping` sites
  plus `FencingToken` (R6 regression lock). Assert each individually; a single combined test would let
  one silently widen.
- A document whose summed extras exceed capacity raises a typed error; one just under capacity loads.
- A neuter probe: reverting one record type to `_closed_mapping` turns its test red.

**Tier:** sonnet / medium — repetitive and fully specified, but six near-identical edits is where a
copy-paste omission hides; the per-type tests exist for that reason.

### U3. The settlement and archive commit path

Make preserved fields survive the commit that archives a fence, and bound the sidecar read.

**Depends on:** U2

**Files:** `plugins/fleet-core/scripts/fleet_commons/lease_broker.py`

**Scope:** replace the `ResourceFence(...)` rebuild at the settlement-close CAS with
`replace(head, close_receipt=close)`; add `_validated_archived_fence` enforcing the per-record bound
and the bounded sidecar payload read.

**Test scenarios** (`plugins/fleet-core/tests/test_lease_broker.py` — *not* the conformance matrix; see
Grounding):
- A fence carrying extras retains them across a full settlement close — asserted by reading the
  archived record back, not by inspecting the in-memory object.
- An archived fence whose extras exceed the per-record bound raises rather than loading.
- The settlement close CAS still rejects a lost head (existing invariant unregressed).
- A neuter probe: restoring the rebuild form turns the retention test red. **This is the unit's most
  important test** — it is the P1 that claude#617's own review caught, and codex ships the failing
  shape today.

**Tier:** opus / high — the CAS commit path is the highest-consequence surface in the file and the
known historical failure point.

### U4. Operator surface

Ship `doctor` and `repair` on the authority and expose them through the adapter CLI.

**Depends on:** U2

**Files:** `plugins/fleet-core/scripts/fleet_commons/lease_broker.py`,
`plugins/saga/scripts/lease_broker.py`

**Scope:** `_extras_inventory` (preserved fields by JSON path), `_document_extras_bytes`,
`_strip_extras`, `LeaseBroker.doctor`, `LeaseBroker.repair`, `LeaseBroker._backup_registry`; adapter
subparsers for `doctor` and `repair --strip-unknown` with the exit-code seam.

Port only the `#617` half of the adapter delta. The adapter's other claude-only lines —
`_declared_isolation` and the two `isolation=` kwargs (#616), and `record_parent_completed`'s
`spawn_failed` kwarg — are explicitly excluded per R9 and R10.

**Test scenarios** (`tests/test_saga_lease_broker.py` — the module has **no** existing CLI-invocation
harness, so building one is part of this unit; follow `tests/test_capability_degrade.py`):
- `doctor` on a clean registry reports status `valid` and exit `0`.
- `doctor` on a registry with preserved fields reports `tolerated-unknowns`, exit `3`, and lists each
  field by JSON path.
- `doctor` on a corrupt document reports `corrupt`, exit `4`, and does not raise.
- An unrecognized status maps to the corrupt exit code — a diagnostic verb must never report clean for
  a state it does not recognize.
- `repair` without `--strip-unknown` exits non-zero having written nothing.
- `repair --strip-unknown` writes a backup first, then clears every extras mapping; re-running `doctor`
  reports `valid`.
- `doctor` never mutates the registry (byte-compare before and after).

**Tier:** sonnet / medium — mechanical, with the exit-code seam fully specified upstream.

### U5. Isolation-exclusion guard, port manifest, and release surfaces

Pin what was deliberately not ported and record the port.

**Depends on:** U3, U4

**Files:** `plugins/fleet-core/tests/test_lease_broker.py`,
`docs/portability/ports/2026-07-26-lease-registry-forward-compat.json`,
`docs/portability/ports/2026-07-26-lease-registry-forward-compat-version-policy.json`,
`tests/test_lease_registry_forward_compat_port_contract.py`,
`plugins/fleet-core/.codex-plugin/plugin.json`, `plugins/fleet-core/CHANGELOG.md`,
`plugins/saga/.codex-plugin/plugin.json`, `plugins/saga/CHANGELOG.md`,
`docs/engineering-journal/DECISIONS.md`, `docs/engineering-journal/LEARNINGS.md`

**Scope:** the KTD5 guard test; the manifest pinning both changed source paths with derived
`expected_count` and `inventory_sha256`; the per-port pytest contract (KTD6); release surfaces for one
release unit (KTD8); journal entries for KTD1 (the inverted byte-copy rationale) and KTD3 (the
rebuild-drops-extras mechanism).

Verify the registry-parity check this repo actually runs before assuming a claude-style
`marketplace.json` exists.

**Test scenarios:**
- `test_isolation_is_not_ported_ktd5` — `isolation` appears nowhere in the codex broker.
- The per-port contract validates the manifest's rows, refs, and derived counts.
- A manifest round-trip pin: it serializes byte-exactly under
  `json.dumps(obj, indent=2, sort_keys=True) + "\n"`, so no tool writeback reformats it. codex#45 hit
  exactly this — a writeback emitted 1-space indent and needed renormalizing.
- Version and CHANGELOG parity for both plugins.

**Tier:** sonnet / medium — mechanical, but `expected_count` must be *derived*; hand-writing it is the
P1 #5 failure mode from codex#45.

### U6. Acceptance harness and evidence

Prove the fix against the real cross-runtime contract.

**Depends on:** U5

**Files:** `docs/validation/2026-07-26-lease-registry-forward-compat-acceptance.json`,
`docs/portability/ports/2026-07-26-lease-registry-forward-compat.json` (evidence entry)

**Inner loop (cheap).** Do not run the full harness while iterating. The two failing scenarios reduce
to a direct assertion: construct a registry document with a lease carrying `isolation`, write it, and
read it back through the codex broker. That is a unit test, and it is the whole of what the harness
proves about this defect. Reserve the harness for the closing gate.

**Run it at the merged SHA, which means after the merge.** This repo merges with merge commits
(`d0982fe`, `f79f141`, `74258be` are all `Merge pull request …`), so the shipped SHA is never the branch
head. `require_clean_pinned` pins an exact SHA, so a bundle produced at the branch head describes a
commit that is not what landed on `main` — and objective #639 needs the *shipped* state proven.

Sequencing that follows: the PR merges on the targeted gates (U1–U5 plus the full suite in a clean
worktree), then U6 runs against the post-merge `main` SHA and its bundle is committed as follow-up
evidence. Do not claim clause 3 discharged from a pre-merge run.

**Closing gate (expensive, once).** Both runtimes must be clean detached worktrees at exact SHAs.
`require_clean_pinned` (harness `:218`, verified at `b464d090`) verifies `HEAD == pin.sha` and refuses a
dirty tree — it does **not** check out, and both primary trees are dirty, so disposable worktrees are
mandatory.

```bash
git -C <claude-repo> worktree add --detach /tmp/pin-claude b464d090
git -C <codex-repo>  worktree add --detach /tmp/pin-codex  <fixed-codex-sha>
export TMPDIR=$(mktemp -d)

env -u INFIQUETRA_FLEET_LEASE_ENFORCEMENT \
python3 /tmp/pin-claude/tools/run_cross_runtime_outcome_acceptance.py \
  --claude-repo /tmp/pin-claude --claude-sha b464d090fccb59d0ff862f273902f1653f1d8835 \
  --claude-saga-version 0.115.0 --claude-fleet-core-version 0.23.0 \
  --codex-repo /tmp/pin-codex --codex-sha <fixed-codex-sha> \
  --codex-saga-version <v> --codex-fleet-core-version <v> \
  --output /tmp/acceptance.json
```

Run with `INFIQUETRA_FLEET_LEASE_ENFORCEMENT` unset — an acceptance run about governed leases executed
with lease enforcement disabled proves nothing.

**Two traps.** The harness prints `{"ok": true}` on stdout while exiting 1 and writing
`overall_verdict: "fail"` — read the bundle, never the stdout summary. And read `HARNESS_EXIT`, not the
shell exit code.

**Acceptance:** `overall_verdict: pass`; both `handoff-negatives-*` green; all 12 previously-passing
scenarios still passing, compared scenario-by-scenario against bundle `c91eaa38…` rather than by count.

**Evidence:** record the harness entry with its real command plus the KTD7 annotation naming codex#57
as the reason it is not replayable from this tree.

**Tier:** opus / high — judgment on what the bundle proves, and the regression comparison is
scenario-by-scenario, not a count.

## Scope Boundaries

### Non-goals

**The `#616` isolation surface is not ported** (R9). Codex must not learn claude-specific lease
semantics. Forward-compatibility is the contract; `isolation` is merely the first field to exercise it.
A reader that special-cases it defers the identical failure to the next field claude adds.

**No claude-side change.** claude#616 and #617 are both closed; KTD5 upstream-first is satisfied and
this issue is the codex re-freeze half. A new defect found in the shared mechanism becomes a new
upstream issue against infiquetra-claude-plugins — never a codex-first fix.

**The ~89 lines of unrelated claude drift stay out** (R10) — batch renewal, `spawn_failed`,
`record_child_terminal`. They belong to no contract row here.

**The four strict boundaries stay strict** (R6). Widening them is a correctness regression, not a
convenience.

**No edit to `scripts/port_contract.py`** — it is a sealed contract (KTD6).

**No `--stage cutover` work.** That gate is structurally blocked:
`plugins/saga/scripts/external_action_release_matrix.py:697-701` raises on the proof's own
`content_sha256` before `_validate_expected_ref` (`:716-720`) is reached. Do not create an evidence tag
or fabricate a release run.

**No re-litigation of codex#45.** Merged at `d0982fe` and measurably successful.

### Deferred to follow-up work

- **codex#57** — the port-contract evidence schema cannot express a cross-repo path. Planned around
  per KTD7, not fixed here.
- **codex#55** — the transient halt never settles the attempt (R7b(c)). A real deferred capability gap
  with its own owner.
- **codex#56** — `.gitignore` omits `.claude/`. One line, separately owned. It does not block this port,
  but it is why explicit-paths-only staging is mandatory: `git add -A` here would commit saga session
  state.
- **claude#663** — the pre-push gate matches command text rather than the git subcommand. It will fire
  against this work: `cd <codex-repo> && git push` runs the *claude* repo's suite. Use
  `git -C <codex-repo> push`.
- **Objective #639 clause 2** — a governed armed-hook Workflow run completing end-to-end remains
  separately unevidenced. This port discharges clause 3 only; #639 does not close on this work alone.

## Risks

**A missed record type.** Six near-identical edits in U2 is where a copy-paste omission hides, and the
lease case passing would mask it. Mitigated by one test per container type.

**Silent extras loss at commit.** Codex ships the failing shape today (U3). Mitigated by a neuter probe
that restores the rebuild form and asserts the test goes red.

**Hand-written `expected_count`.** The P1 #5 failure mode from codex#45. Mitigated by deriving it and
pinning the derivation in the per-port contract.

**No CI.** Every gate is local-only; nothing catches a regression after merge. Mitigated by running the
full suite at the head that is actually merged, not at an earlier repair commit — and by checking the
review→close SHA delta before writing closure evidence.

**A green harness that proves less than it appears to.** Mitigated by comparing scenario-by-scenario
against bundle `c91eaa38…` rather than comparing counts.

**Rollback.** The down-migration is the feature's own `repair --strip-unknown` (U4): it backs up the
registry, clears every preserved mapping, and returns the document to its pre-port shape. That is why
`repair` takes a backup before stripping and refuses to act without the explicit flag — it is the
recovery path, not a convenience verb. A reader that has not yet been upgraded is unaffected either way,
since an extras-free document is byte-identical before and after (R8).

## Verification

Targeted runs are fine in the working tree:

```bash
cd <codex-repo>
PYTHONPATH=. uv run pytest plugins/fleet-core/tests/test_lease_broker.py -q
PYTHONPATH=. uv run pytest tests/test_saga_lease_broker.py -q
PYTHONPATH=. uv run pytest tests/test_lease_registry_forward_compat_port_contract.py -q
git grep -c isolation -- plugins/fleet-core/scripts/fleet_commons/lease_broker.py   # expect no match
```

The full-suite gate runs in a **clean detached worktree**, never the primary tree:

```bash
git -C <codex-repo> worktree add --detach /tmp/gate-codex <fix-sha>
cd /tmp/gate-codex && PYTHONPATH=. uv run pytest -q     # expect 2728+N passed, 4 skipped, 0 failed
git -C <codex-repo> worktree remove /tmp/gate-codex
```

Then the U6 closing gate.
