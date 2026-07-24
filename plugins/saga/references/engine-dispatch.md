# External-engine dispatch contract

How a resolved `{engine, effort, protocol, payload}` (from `engine_resolver.resolve`) reaches an
external engine and comes back as evidence the host driving session verifies. This reference governs
the *policy*; the mechanism lives in `plugins/saga/scripts/engine_dispatch.py`.

The rule that governs everything here: **the host driving session is verifier-of-record (R13). An
external engine never holds a gated verdict.** Dispatch produces *advisory evidence*, never a decision.
(The code field is spelled `verified_by_claude` as a lineage name; on the Codex host it means "verified
by the driving session.")

## Dispatch paths

The adapter dispatches to the wrapper each engine already owns — it does not re-implement containment.

- **agy** (`resolution.engine_id == "agy"`) → `agy:delegate`. The invocation is an
  `agy.delegation.v1` envelope with `mode: no-write` (R23), `task` = `resolution.payload`, and `model`
  and `effort` copied from the validated registry row.
- **HTTP** (`invocation.via == "engine-bridge-http"`) → the generic OpenAI-compatible bridge. The
  invocation contains the reviewed HTTPS provider root, model, effort, and bearer environment
  variable name. The secret value exists only in the outbound header and never enters evidence.

Native Codex children are not external engines. Their `gpt-5.6-sol` or `gpt-5.6-terra` model and
scalar effort are selected by Fleet Core execution classes and Verified Workflows profiles, then
verified from host-issued child context. Luna remains V1-only in Codex 0.145.0 and is not used by
the V2 profile set. `codex:delegate` and stale `codex --effort` recipes are rejected by the registry.

Both paths are **evidence-only by default** (R23): the engine returns proposed output; it does not
mutate the working tree. File-mutating external work is deferred until the ideation-R14 sandbox
profile exists — until then an external worker asked to change files returns the proposed change as
evidence, not an edit (AE7).

## The advisory-evidence result type (R13 enforcement)

`dispatch()` returns an `AdvisoryEvidence` — a value that carries `evidence`, `provenance`, a
`verified_by_claude` lineage flag (default `False`), a typed `runner_receipt`, and an optional `halt`.
The lineage field keeps the persisted schema compatible; on Codex it means independent root
verification. Runner results containing `verdict`, `gate_status`, or `adjudicated` are structurally
rejected. An `ok` result without a schema-valid, signature-valid bridge receipt is also rejected.

## Failure modes → halt + provenance

The runner (the thing that actually invokes the wrapper) reports a `status`. Every non-`ok` status —
`timeout`, `no-output`, `error`, `malformed`, `clone-failed` (the statuses the engine wrappers
actually return) — produces an `AdvisoryEvidence` with `halt` set and
a one-line downgrade/provenance note (R24), and **never** a gated verdict. A `resolution` that already
carries a `halt` (an unavailable named engine, an unavailable panel member, or a context-window
overflow from the resolver) short-circuits: `dispatch()` returns that halt without invoking the runner.

## Provenance and downgrade notes (R24)

Any fallback or substitution emits a visible one-line note (`downgrade_note(engine, reason)`), shaped
like the existing `orchestration_downgrade` record (`plugins/saga/references/saga-spec.md:121-125`), so
a later `/retro` or `/optimize` pass — and the operator — can see the run went degraded and why.
Degradation is durable, never silent. An implicit worker fallback returns to the Codex root inline;
an explicitly selected unavailable engine and every unavailable advisory reviewer halt.

## Override semantics (R20)

- **Inline / interactive dispatch** — the operator can override the resolver's selection *before*
  dispatch.
- **Serial autonomous dispatch** — the adapter acts on the standing registry configuration (which is
  itself the operator's authored choice) and surfaces its selection *post-hoc* in the result rather than
  blocking to wait for an override.

## Backends (Codex host truth)

Root-owned dispatch and dry-run route explanation are in scope. Claude Workflow, TeamCreate, fork,
and peer-team messaging are negative-gated. External-engine evidence never satisfies Verified
Workflows reviewer, validator, or gate arithmetic, even when its transport receipt is valid.
