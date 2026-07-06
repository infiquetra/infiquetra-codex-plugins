# Worker Exit Manifest — team-execution

A provenance manifest (`saga.manifest.v1`, `plugins/saga/scripts/provenance_manifest.py`) is a
typed, cross-worktree evidence record for a delegated output. This document is the worker-exit
contract: what a team-execution worker's manifest carries and how it is written. It complements —
never duplicates — `validator-evidence-state.md`: validators keep their repo-local per-run
evidence JSON (`.codex/team-execution/validators/`); a manifest is the cross-worktree envelope
for the worker's *output*, and it outlives the run (git-common-dir, R19).

On the Codex host a "worker" is a bounded Codex subagent or a serial main-thread role — never a
Claude-host resident teammate or a Workflow wave-thunk (those are negative-gated here). The manifest
contract below is identical for both Codex worker forms.

---

## Evidence, never authority (R20/R21)

A worker manifest grants no privilege and holds no verdict. It does not gate a wave, unblock a
dependency, or substitute for reviewer/validator consensus. It is read-only, advisory evidence
(R8) that downstream consumers (`/code-review`, `/qa`, `/retro`) may use to spend attention more
efficiently — never something a worker or coordinator can use to skip a required check. Nothing
in this contract expands what a team-execution worker is authorized to mutate; workers keep
today's file-edit scope (R21 — mutating external workers stay out of scope entirely, blocked on
the sandbox profile, issue #287). This covers both worker kinds: an ordinary team-execution worker
role, and a **chaperone worker** — a worker role whose units are owned by an external engine (agy,
codex) it resolves, dispatches, verifies, and applies on behalf of (KTD1, #283 U12). The chaperone
is still the one that touches the working tree and owns the commit — R21's scope never widens; see
`external-engine-workers.md` for the full resolve → dispatch → verify → apply → test → manifest
protocol this document's attribution/disposition/tier fields feed into.

## Who writes it and when

The **worker itself**, at segment/unit exit (Step B1, after its assigned units complete and
before the coordinator captures the wave's diff summary) — a worker is a live agent (Codex subagent
or serial main-thread role) with filesystem access, so it writes its own manifest directly.

Call the store CLI directly:

```bash
python3 plugins/saga/scripts/manifest_store.py \
  --repo-root <repo-root> --saga-id <saga-id> \
  write --execution-id <worker-id>-<unit-id> --file <path-to-manifest.json>
```

`<manifest.json>` is the `to_dict()` output of a `provenance_manifest.Manifest` built as below.

## Manifest shape for a worker exit

**Attribution (R2), ordinary worker:** `kind="team-execution"`, `identity="worker-<plugin>"`
(the worker id, matching the `worker-<plugin>` naming in the Workers table), `effort` the tier the
worker ran at (`opus/high`, etc., from the team-execution spec), `protocol=""` (no external-engine
protocol applies to an ordinary worker).

**Attribution (R2), chaperone worker:** `kind="external-engine"`, `identity="<engine>/<variant>"`
(the resolved engine and variant, not the worker id — the same identity format
`engine_dispatch.build_dispatch_manifest` always emits), `effort` the resolved engine's effort,
`protocol` populated from the resolution. The worker id (`worker-<engine>` / `worker-<capability>`)
still names the segment in the Workers table (KTD3) — it is not what `identity` carries here, since
`identity` attributes the *output*, not the slot that produced it. Full mechanics in
`external-engine-workers.md` §5.

**Disposition (R18):** `ran-as-requested` for a worker (either kind) that completed its assigned
units as requested. For a chaperone worker, two more dispositions are live (not reserved): the
engine call itself never runs — `fell-back-to-claude` (a lineage disposition name meaning
"handled by the host worker directly, serially") when the resolver's own capability-no-fit /
preflight-unavailable path routes the unit to the chaperone rather than an external engine, carrying
the fallback reason as `disposition_note`; the engine ran but wasn't the one the operator approved —
`substituted-engine` when run-time capability routing resolved a different engine/variant than the
plan-time preview the tier table recorded (KTD4). An ordinary worker (no `engine`/`capability`
selector) only ever writes `ran-as-requested` — the other two dispositions require a resolution to
diverge from. Trigger conditions and the halt path (R25/R26 — a halt writes no manifest at all,
nothing ran) are in `external-engine-workers.md` §2 and §4.

**Output completeness (R3):** one `OutputCompleteness` per unit the worker owned, derived the same
way `completeness_gate.Contract.from_unit` + `classify()` already do for spec-driven runs:
declared keys from the unit's `returns`/contract, produced keys from what the worker actually
changed/returned. A required, non-skipped, contract-bearing unit with no manifest at wave-close is
a `missing-output` trip — consistent with `validator-evidence-state.md`'s Required-Evidence
Absence rule for validators, applied here to workers.

**Claim provenance:** optional at v1. For an ordinary worker, output is code/diff, not a set of
prose claims — leave `claim_provenance` absent (lightweight tier, KTD9) unless a future revision
asks a worker to attest specific claims about its own diff. For a chaperone worker whose engine
returned prose claims alongside its evidence (e.g. a second-opinion review verdict), the chaperone
may populate `claim_provenance` from the engine's claimed layer — but every claim stays
producer-`claimed`-only until the chaperone (the host driving session) adjudicates it
(`engine_dispatch.adjudicate_manifest`, never the engine itself); a claimed-`verified` status never
counts toward a gate on its own (D5, no self-attestation — same rule either worker kind).

## Tier

Lightweight is the default and typically sufficient (attribution + disposition + existence bit).
Use full tier — with `output_completeness` populated — for any unit whose plan marks it
contract-bearing (has a declared `returns`/output contract), matching R10/R13's existing
completeness-gate scoping.

## Failure modes stay evidence-only

A worker that halts, is reassigned, or produces a partial result records that honestly in
`disposition` + a `disposition_note` — never silently. The manifest records what happened; it
never decides whether the wave proceeds. That decision stays with the coordinator and the
existing reviewer/validator consensus machinery.
