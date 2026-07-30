---
name: run
description: Explicitly run an operator-approved Infiquetra Workflow Contract as a root-orchestrated Codex V2 DAG with exact profiles, runtime receipts, bounded writes, one independent review, one remediation, and one targeted recheck.
---

# Run Verified Workflow

Use this skill only after the operator approves the complete `## Workflow Contract` defined in
[workflow-protocol.md](references/workflow-protocol.md). The approved contract is the execution
boundary; root does not redesign or further decompose it.

Apply the [gate policy](references/gate-policy.md), [validator evidence
state](references/validator-evidence-state.md), [worker manifest](references/worker-manifest.md), and
[delegation safety](references/delegation-safety.md) contracts.

## Approval Gate

Compile the exact approved contract with `workflow_dispatch.py`. Do not launch work until the
operator has reviewed the assignment graph, role, profile, writes, completion condition, fallback,
checks, and approval binding. Model and reasoning effort are maintained properties of the profile,
not duplicate workflow columns or per-spawn overrides.

A new assignment, changed write set, different role or profile, additional reviewer, or material
scope change returns to planning and operator approval. Use only an approved fallback as written.

## Root Loop

Root means the main Codex session. Root only:

1. Dispatches dependency-ready assignments through the native `collaboration` tools with the
   approved `agent_type` and `fork_turns=none`.
2. Verifies the first `session_meta` plus `turn_context` runtime receipt matches the approved agent
   type, model, effort, provider, permission profile, sandbox, and canonical path.
3. Waits for a terminal typed result and validates it with `result_contract.py`.
4. Compares returned changed paths with the assignment's approved write paths.
5. Releases dependencies from validated results and blocking check outcomes.
6. Presents approval boundaries and reports completion or blockers.

Root does not edit files, implement, remediate, test, review, or run Git, PR, merge, deployment,
installation, or release commands. Every executable action must be an approved assignment.

## Write Ownership

Every writable assignment declares repository-relative paths. Concurrent writers must have disjoint
write sets; writers that share a file or directory must be dependency-ordered or combined. Workers
return their actual changed paths.

Only `git-integration-operator` may run Git commands. Its assignment performs the final
`git diff --name-only` comparison against the union of approved write paths before any approved Git
integration.

## Review Convergence

Run the independent reviewer named by the contract as a direct child of root and a sibling of every
implementation worker, with `fork_turns=none`. Add another reviewer only when the approved plan
names a concrete risk that requires it.

Every finding carries `scope_disposition`: `planned`, `one-hop`, `defer`, or `approval-required`.
Across the whole run, root may adopt at most one `one-hop` issue: it must directly block the
approved work, stay inside the approved writes, add no file, dependency, interface, schema, state,
role, abstraction, cross-plugin/repository work, or live mutation, and receive one repair plus one
targeted check. Defer adjacent nonblocking issues. A second issue, failed recheck, wider scope, or
new authority stops for operator approval.

All remaining actionable planned findings go to the single `remediation-worker` assignment. Run
one targeted recheck. If an actionable finding remains, stop and return it to the operator. Do not
start another remediation cycle or automatically add reviewers.

## Results

Report completed assignments, actual profile/model/effort receipts, changed paths, checks, finding
dispositions, whether the one-hop budget was used, and blockers concisely. Messages and raw model
output never release a dependency or satisfy a gate.
