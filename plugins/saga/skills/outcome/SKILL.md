---
name: outcome
description: Coordinate a whole outcome as a durable Codex Saga DAG. Use for start, load, status, report, graph, advance, attend, export, and import of outcome subplots. The coordinator routes work and records receipts; it does not execute leaf work in-context.
---

# Outcome

`saga:outcome` is the Codex-native OutcomeOrchestrator surface. It sits above
single work-thread sagas and coordinates a durable DAG of subplots. Leaf work
still routes through native Saga surfaces such as `saga:plan`, `saga:work`,
`saga:qa`, `saga:code-review`, `saga:resume`, or `team-execution`.

The coordinator has two invariants:

- It routes and reconciles. It does not perform a leaf's implementation work in
  the same context.
- Status is derived on read from the spec, store, and durable evidence. Do not
  trust operator-writable status fields as completion truth.

## Commands

Use `plugins/saga/scripts/outcome.py` for the mechanical operations:

```bash
python3 plugins/saga/scripts/outcome.py start <id> <objective>
python3 plugins/saga/scripts/outcome.py status <id>
python3 plugins/saga/scripts/outcome.py report <id>
python3 plugins/saga/scripts/outcome.py project <id>
python3 plugins/saga/scripts/outcome.py graph <id>
python3 plugins/saga/scripts/outcome.py advance <id>
python3 plugins/saga/scripts/outcome.py attend <id> <subplot-id>
python3 plugins/saga/scripts/outcome.py export <id>
python3 plugins/saga/scripts/outcome.py import <bundle>
```

Default operator output must be terminal-safe: ASCII, prose, or the shared
status-card renderer. Do not emit Mermaid in chat or terminal output unless the
operator explicitly requests a documentation/export artifact.

## Backend Rules

Active Codex backend floor:

- `inline`
- `manual`
- `team-execution`

Conditional backend:

- Codex subagents or multi-agent tools only when callable in the current session
  and safe for the leaf.

Inactive source backends:

- Workflow
- fork
- goal
- hooks

If an inactive or unavailable backend is requested, emit a visible halt/degrade
receipt and offer a safe Codex backend or manual handoff. If side effects may
already have happened, halt for operator attention rather than rerunning on a
weaker backend.

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
