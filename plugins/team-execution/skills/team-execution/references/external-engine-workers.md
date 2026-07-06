# External-Engine Workers — Chaperone Dispatch Protocol

This document is the wrapper contract R12 names as missing: how a team-execution worker can be
an external engine (agy, codex) instead of an ordinary worker role, without team-execution growing
a second executor kind. It closes #283's deferred U12 leg and activates the dispositions
`worker-manifest.md` reserved (`fell-back-to-claude` / `substituted-engine`).

**Shape (KTD1):** one **chaperone** — an ordinary team-execution worker role (a bounded Codex
subagent or a serial main-thread role), `worker-<engine>` or `worker-<capability>` per the
Workers-table naming rule (`SKILL.md`'s `### Workers`, KTD3) — owns an engine's units end-to-end:
resolve → dispatch → verify → apply → test → manifest. There is no separate "external worker"
executor; the engine never joins wave scheduling or git directly. It is evidence the chaperone
consumes (R23) — never write-capable in this contract.

On the Codex host the chaperone is a Codex-driven role, not a Claude-host resident teammate; the
Claude-host residency protocol and Workflow/TeamCreate chaperone emission are **negative-gated**.
Where the resolver's fallback engine id is spelled `claude` it is a lineage label meaning "the host
driving session handles the unit itself, serially" — no Claude-only surface is invoked.

## Never a gatekeeper (R13/R15, restated)

Nothing in this document lets an external engine satisfy a gate. `engine_dispatch.satisfy_gate()`
(`plugins/saga/scripts/engine_dispatch.py`) hard-requires `evidence.verified_by_claude is True`
before advisory evidence counts toward any verdict (the field name is a lineage spelling for
"verified by the host driving session"), and — when a typed manifest carries `claim_provenance` —
every gate-relevant claim must already be host-adjudicated (R11 extension). An external-engine
worker's diff still goes through the same reviewer consensus and validator gates as any other
worker's diff (`SKILL.md` Step B2/B3); this contract only changes *who wrote the diff*, not what
clears it for merge.

## 1. Context package (coordinator → chaperone)

At dispatch (Step B1's wave scheduling), the coordinator hands the chaperone a context package
carrying:

| Field | Source | Purpose |
|---|---|---|
| `unit_ids` | the plan's Implementation Units assigned to this segment | scope — same as any worker (SKILL.md Step B1) |
| `plan_pointer` | plan doc path | authoritative spec, read once, not re-transcribed |
| `selector` | the unit's `engine` or `capability` field (`execution_spec.py` `Unit.engine`/`Unit.capability`, mutually exclusive) | what `engine_resolver.resolve()` is called with |
| `intent` | the unit's `engine_intent` (`offload` / `second-opinion`, defaults `offload`) | carried for provenance/audit; the operational effect (chaperone tier) was already locked at plan time via the KTD2 tier-table recommendation |
| `plan_time_resolution_preview` | the tier-table recommendation row the operator approved: `{"engine_id": "<key>", "variant": "<key>"}` for a capability-routed unit; absent/null for an explicit-engine unit (R26 makes substitution unreachable there — see §4) | the baseline §4 compares the run-time resolution against |
| `write_set` | the unit's declared `files` (Create/Modify) | scopes what the **chaperone's own apply step** may touch — not the engine's; the wrapper envelope's own `write_set` stays `[]` at v1 (R23) regardless of this value |

No other context crosses the boundary. The chaperone does not forward its own system prompt,
prior conversation, or other units' state to the engine — only what §2 assembles.

## 2. Resolve

The chaperone calls the resolver in `dispatch` mode with `role_kind="worker"`:

```python
resolution = engine_resolver.resolve(
    {"role_kind": "worker", "engine": selector} | {"role_kind": "worker", "capability": selector},
    mode="dispatch",
    registry=registry,
)
```

(`role_kind` rides in the request dict; `engine`/`capability` are mutually exclusive keys —
`MODES = ("advisory", "dispatch")`, `ROLE_KINDS` in `engine_resolver.py`.) `role_kind="worker"` puts
the chaperone in `FALLBACK_ROLE_KINDS`, which governs how the resolver responds when nothing usable
is available:

- **Capability selector, no engine fits** (unsupported capability or a fitness rejection) →
  the resolver itself returns a host-fallback `Resolution` (`engine_id="claude"`, `halt=None`,
  `fallback="<reason>"`). The chaperone does the unit itself, serially; no dispatch happens.
  Disposition = `fell-back-to-claude` (§5).
- **Capability selector, entry found but the engine's CLI/config preflight fails** → same
  host-fallback path (a capability-routed worker falls back rather than halting).
- **Context-window overflow for the resolved variant** → the resolver halts regardless of
  selector kind or role (`_context_window_halt`, R25) — this is not R26; see §4's halt path.
- **Explicit-engine selector, that engine unavailable** → **halt**, never fallback (R26 —
  `explicit_engine=True` forces the halt branch for every role kind). This is the only halt
  condition specific to naming an engine by key.

## 3. Dispatch — protocol forwarded verbatim (R11)

When `resolution.halt` is `None` and the engine is not `"claude"`, the chaperone builds the
wrapper invocation from the resolution's own payload — never re-authored or paraphrased:

```python
invocation = (
    engine_dispatch.build_codex_invocation(resolution, sandbox=unit_sandbox)
    if resolution.engine_id == "codex"
    else engine_dispatch.build_agy_envelope(
        resolution, model=model, sandbox=unit_sandbox, write_set=unit_files
    )
)
evidence = engine_dispatch.dispatch(
    resolution, runner=runner, model=model, sandbox=unit_sandbox, write_set=unit_files
)
```

`unit_sandbox` is the unit's declared `sandbox` envelope (or `None`) and `unit_files` its declared
`files` list. Both builders assert byte-identical payload preservation (`_assert_payload_preserved`)
— `resolution.payload` is the resolved prompting protocol plus context, assembled once by the
resolver and never touched again. The `runner` that actually invokes the engine is the existing
containment wrapper, not a new one this contract adds:

- **agy** → `/agy:delegate` (or the `agy:agy-coder` / `agy:agy-reviewer` Bash-only bridge agents),
  which calls `agy_delegate.py`. Never invoke raw `agy`. **Default / read-only units keep the
  evidence-only ceiling** — `mode: "no-write"`, `write_set: []`, `apply_policy: "preserve-patch"`.
- **codex** → `codex:codex-rescue`, `sandbox: "read-only"` (`build_codex_invocation`). codex has
  **no write adapter**: a `sandboxed-mutate` unit routed to codex HALTS with a visible
  `DispatchError` rather than silently running read-only and dropping the write (#287 KTD4/R6).

(The `sandboxed-mutate` write-ceiling lift is duck-typed by `engine_dispatch` but the sandbox
spawn-site enforcement mechanism itself is deferred on the Codex host, so v1 units stay evidence-only.)

`dispatch()` short-circuits to a halted `AdvisoryEvidence` without invoking the runner at all when
`resolution.halt is not None` — the halt path in §4 never reaches the wrapper.

## 4. Substitution detection (KTD4)

Compare the resolution the chaperone actually got against the plan-time preview from §1, **only
for capability-routed units** (an explicit-engine unit that resolves to anything other than the
named engine is a contradiction the resolver cannot produce — it halts instead, R26):

```python
substituted = (
    plan_time_resolution_preview is not None
    and resolution.halt is None
    and resolution.engine_id != "claude"
    and (resolution.engine_id, resolution.variant)
        != (plan_time_resolution_preview["engine_id"], plan_time_resolution_preview["variant"])
)
```

A `True` result changes the disposition written in §5 from `ran-as-requested` to
`substituted-engine` — the run-time capability router resolved a different engine/variant than
the one the operator approved in the tier table. This is the only reachable substitution path.

## 5. Verify → apply → test → manifest

1. **Verify.** The chaperone reads `evidence.evidence` (the engine's returned patch/output) and
   reviews it itself — never self-attested. Only after review does the chaperone set
   `evidence.verified_by_claude = True` (the host-verification bit `satisfy_gate()` requires).
2. **Apply.** The chaperone applies the reviewed patch and **owns the commit** — the engine never
   touches the working tree (KTD6/R23). This is the same file-edit scope every team-execution
   worker already has.
3. **Test.** The chaperone runs its unit's tests, same as any worker at segment exit.
4. **Manifest.** Two paths, chosen by §4's `substituted` result:

   - **Not substituted** (`ran-as-requested` or `fell-back-to-claude`): call the existing builder
     unchanged —
     ```python
     engine_dispatch.record_dispatch_manifest(
         store, evidence,
         execution_id=f"{worker_id}-{unit_id}", saga_ref=saga_ref, created_at=created_at,
         effort=resolution.effort, protocol="\n".join(resolution.protocol),
     )
     ```
     `build_dispatch_manifest` maps `evidence.halt is not None` → `FELL_BACK_TO_CLAUDE` (carrying
     the halt/downgrade note as `disposition_note`) and otherwise → `RAN_AS_REQUESTED`; attribution
     is `kind=EXTERNAL_ENGINE`, `identity=f"{evidence.engine_id}/{evidence.variant}"`.
   - **Substituted**: `build_dispatch_manifest` has no way to express this disposition (it only
     inspects `evidence.halt`), so the chaperone constructs `provenance_manifest.Manifest`
     directly (this is `worker-manifest.md`'s documented "the worker itself writes it" path) with
     `disposition=pm.Disposition.SUBSTITUTED_ENGINE` and a `disposition_note` naming both the
     previewed and the resolved engine/variant, then writes it via `manifest_store.py write
     --execution-id <worker-id>-<unit-id> --file <manifest.json>`.

   A halted unit (§2's R26/R25 halt paths) never reaches this step — nothing ran, so there is
   nothing to manifest. The chaperone surfaces `resolution.halt` to the coordinator and stops on
   its assigned units, exactly like any other blocked worker.

Tier and `claim_provenance` guidance for the resulting manifest are unchanged from
`worker-manifest.md`'s existing "Tier" and "Claim provenance" sections — this contract only adds
the `kind=external-engine` attribution leg those sections already reserved space for.
