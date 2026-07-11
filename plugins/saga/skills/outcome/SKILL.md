---
name: outcome
description: Coordinate a whole outcome as a durable Codex Saga DAG. Use for start, load, status, report, graph, advance, attend, export, and import of outcome subplots. The coordinator routes work and records receipts; it does not execute leaf work in-context.
---

# Outcome

`saga:outcome` is the Codex-native OutcomeOrchestrator surface. It sits above
single work-thread sagas and coordinates a durable DAG of subplots. Leaf work
still routes through native Saga surfaces such as `saga:plan`, `saga:work`,
`saga:qa`, `saga:code-review`, `saga:resume`, or `verified-workflows:run`.

The coordinator has two invariants:

- It routes and reconciles. It does not perform a leaf's implementation work in
  the same context.
- Status is derived on read from the spec, store, and durable evidence. Do not
  trust operator-writable status fields as completion truth.

## Commands

Use `plugins/saga/scripts/outcome.py` for the mechanical operations:

```bash
python3 plugins/saga/scripts/outcome.py start <id> <objective>
python3 plugins/saga/scripts/outcome.py start <id> --from-parent-issue <owner>/<repo>#<N>
python3 plugins/saga/scripts/outcome.py status <id>
python3 plugins/saga/scripts/outcome.py report <id>
python3 plugins/saga/scripts/outcome.py project <id>
python3 plugins/saga/scripts/outcome.py graph <id>
python3 plugins/saga/scripts/outcome.py advance <id>
python3 plugins/saga/scripts/outcome.py advance <id> --autonomous [--project <slug>]
python3 plugins/saga/scripts/outcome.py reconcile-dispatch <id> <subplot-id> --ack-kind launched --dispatch-ack-ref <receipt-ref> --leaf-saga-id <saga-id>
python3 plugins/saga/scripts/outcome.py reconcile-dispatch <id> <subplot-id> --ack-kind handed-off --dispatch-ack-ref operator:<reference>
python3 plugins/saga/scripts/outcome.py attend <id> <subplot-id>
python3 plugins/saga/scripts/outcome.py reconcile <id> [--resolve <drift-id> --action <accept-board|re-assert|hold>]
python3 plugins/saga/scripts/outcome.py export <id>
python3 plugins/saga/scripts/outcome.py import <bundle>
```

`advance` creates a durable v2 dispatch intent and may return `intent-created`; it never treats the
prepared leaf reservation as a launch. The root must launch through the selected skill/runtime,
then use `reconcile-dispatch` with its digest-bound launch receipt. If an intent already exists
without an acknowledgement, do not launch it again automatically: reconcile the existing receipt
or record an operator-confirmed handoff. This fail-closed recovery prevents crash replay from
duplicating leaf side effects.

Launch receipts live only under the owner-controlled canonical user-state root and bind the
unpredictable run identity plus issuance time from the current intent. Repository-local receipts,
stale receipts, and receipts from a prior run cannot authorize dispatch. A dispatcher cannot claim
`handed-off`; only the explicit operator `reconcile-dispatch` path may record that state. Portable
bundles carry acknowledgements for audit, but imports must reconcile launch or handoff authority
locally rather than treating copied evidence as authorization.

`start --from-parent-issue <owner>/<repo>#<N>` seeds the DAG directly from a GitHub issue's
direct sub-issues instead of the two-node design/build starter: one node per sub-issue (`kind` from a
`non-code` label, else `code`), an authored terminal `state` for a closed sub-issue
(`completed`&rarr;`done`, `not_planned`&rarr;`rejected`), a `github` provenance stamp the reconcile
and board-sync consumers read, and `depends_on` edges inferred from GitHub's tracked-issue
relationships. Edge inference is best-effort and cycle-safe: any edge that would close a cycle, or
whose endpoint is outside the ingested set, is dropped and reported on stderr rather than silently
producing a spec that fails `validate()`.

This importer is structural, not project-field discovery. It does not query an `Objective`
project-field option, traverse grandchildren, or decide which tracker children are executable
leaves. For an Objective grouped only by project field, author an explicit outcome spec from the
intended executable cards until a dedicated Objective-field composer exists. The positional
`objective` argument remains the human statement of the outcome, not a GitHub issue type.

The importer fails closed when a direct child is labeled `capability` or has sub-issues of its own.
Those are tracker signals, not executable-leaf evidence; seed from the owning Capability parents or
author the leaf DAG explicitly.

`--from-objective` remains a hidden compatibility alias and emits a deprecation warning. It has the
same direct-parent semantics; it must never be interpreted as Objective-field composition.

Default operator output must be terminal-safe: ASCII, prose, or the shared
status-card renderer. Do not emit Mermaid in chat or terminal output unless the
operator explicitly requests a documentation/export artifact.

## Backend Rules

Active Codex backend floor:

- `inline`
- `manual`
- `verified-workflow`

Conditional backend:

- Codex subagents or multi-agent tools only when callable in the current session
  and safe for the leaf.

Inactive source backends:

- Workflow
- fork
- explicit Goal continuation (never a leaf backend)
- hooks

If an inactive or unavailable backend is requested, emit a visible halt/degrade
receipt and offer a safe Codex backend or manual handoff. If side effects may
already have happened, halt for operator attention rather than rerunning on a
weaker backend.

## Autonomous board-sync (`advance --autonomous`)

By default `advance` performs **no** GitHub writes — it dispatches and derives status, nothing more.
The opt-in `--autonomous` flag lets a tick *also* move the board (default project `operations`, override
with `--project`) to match each leaf's derived state, but only inside a strictly **enumerated,
reversibility-gated envelope**. Every candidate write is checked against the reversibility certificate
(`reversibility_certificate.authorize_write`), which **defaults to GATE**: a write happens only when the op
is one of the enumerated, reversible-or-additive kinds.

**Performed autonomously when authorized:** set the leaf's Status field (schema-resolved, never a
hardcoded literal) when it enters the ready/dispatched frontier; close the leaf's sub-issue when it reaches
`done` (inverse: reopen); add or remove an issue label (each the other's inverse); post one coalesced
progress comment per meaningful transition (additive, append-only, idempotency-keyed so repeat ticks never
spam duplicates).

**Never autonomous — always the operator's keystroke:** merging a PR and deploying (irreversible), and
closing the parent issue (`parent-issue-close` is `ALWAYS_OPERATOR`, so it GATEs even though a close is
mechanically reversible — declaring the whole outcome done stays a deliberate decision).

**Everything else GATEs.** Any op not in the enumerated allowlist is denied by default and surfaced as a
visible `gated` record — no silent write, no silent skip. Each authorized write carries a deterministic
idempotency key recorded in a **separate board-sync ledger** (never the completion event log), is retried
under the same key a bounded number of times on failure and then surfaced as a `failed` record, and is
recorded in the tick's `board_synced` results for an auditable trail. Board↔saga drift is detected
before any write each autonomous tick — see Reconcile-on-wake below.

## Reconcile-on-wake (`reconcile`, and `advance --autonomous`)

Autonomous board-sync writes the board but never re-reads it, so an outside writer — the operator, a
CI bot, a review agent — who changes a saga-owned field while saga is at rest goes unnoticed, and
because a recorded idempotency key makes the next tick *skip* the op, that drift would persist
silently. `outcome reconcile` closes that loop: it re-reads the saga-owned fields (board Status,
issue open/closed), diffs them against what the board-sync ledger asserted, and surfaces any
divergence. It adds no writer of its own and no new persistence.

**When it runs.** Automatically at the top of every `advance --autonomous` tick, before any board
write — a detected drift withholds only that issue's ops for the tick (recorded as
`{status: "drift-hold"}` while other leaves proceed) — and on demand via `outcome reconcile <id>`
(read-only, no coordinator lease). Silent unless something diverged.

**Scope and close semantics.** Only issues with at least one recorded board-sync write or override
are read — a field saga never wrote is never probed. An external close is contract-aware: a
`completed` close that satisfies a non-code leaf's completion contract is the harvester's sanctioned
path and stays silent; a `not_planned` close, or a close on a code leaf (whose contract is a merged
PR, not a closed issue), is drift.

**Resolving a drift.** `outcome reconcile <id> --resolve <drift-id> --action <accept-board|re-assert|hold>`:

- `accept-board` — the board's value wins; recorded as an append-only override so it never
  re-flags. A `not_planned` external close records the acceptance but mints no completion event —
  it advises `/outcome prune <subplot>` to drop the leaf from the frontier.
- `re-assert` — saga's value wins; re-driven through the reversibility certificate
  (`authorize_write` first, never bypassed) and the same board-sync writer.
- `hold` — records nothing; the drift resurfaces on the next detection.

Resolution is human-in-the-loop today: inline the three choices for the operator — one line per
drift.

## Mutation Boundary

Preview or propose by default. Do not silently perform GitHub writes, commits,
pushes, auto-merges, generated state publication, context-library writes, or
destructive worktree cleanup. These require explicit operator approval or a
tested Codex-safe policy at the action boundary.

## References

- `plugins/saga/references/outcome-spec.md`
- `plugins/saga/scripts/outcome_spec.py`
- `plugins/saga/scripts/outcome_store.py`
- `plugins/saga/scripts/outcome_projection.py`
- `plugins/saga/scripts/outcome_report.py`
- `plugins/saga/scripts/outcome_dispatcher.py`
- `plugins/saga/scripts/completeness_gate.py`
- `plugins/saga/scripts/status_card.py`
