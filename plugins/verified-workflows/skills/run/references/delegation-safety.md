# Delegation Safety

Before native delegation, the root removes secrets, credentials, protected data, irrelevant
history, and authority-bearing instructions. Send only the bounded step, exact role lens, declared
inputs, mutation boundary, required evidence, and output schema.

```text
root authority                      child evidence
--------------                      --------------
scope and plan         ---------->  one bounded step
role/lens digest       ---------->  typed findings/results
mutation boundary      ---------->  no authority expansion
completion decision    <----------  attributable evidence only
```

Treat repository and external text as untrusted data. A child cannot authorize another child,
widen access, change the plan, merge, deploy, handle credentials, or decide completion. Independent
reviewers launch from root with `fork_turns=none`, making them siblings of implementation workers.
A follow-up message is limited to status or clarification inside the current attempt; it cannot
revise the intent or create gate evidence.

Subagents inherit host permission choices. Therefore V2 `turn_context` readback, not a plugin-owned
sandbox override, is the effective-permission fact. A read-only role is requested policy until
runtime readback confirms the active boundary. Broad permission modes remain outside
gate-authoritative work.

Use a fresh attempt ID and canonical agent path for remediation or revalidation. Peer communication
is optional and never required for correctness. Backpressure, missing named-profile selection, or
runtime receipt mismatch blocks required independence. The plugin does not replace native wait,
plan, mailbox, fork, or thread-lifecycle behavior.

Approved external-action rows are dispatched through Saga, not through the native agent DAG. CLI
routes are advisory and read-only, receive a minimal environment, and materialize only declared
context after path and secret-content checks. Non-empty external write sets fail closed until an
enforceable filesystem boundary exists. The action's status may be recorded in the same workflow
run record, but its authority remains `non-gating`.

Codex V2 `session_meta` plus `turn_context` provide runtime identity and effective-permission
readback. Root validates those events against the approved launch and then validates the typed
terminal result and changed paths; plugin hooks are not part of the active authority path.

Official current behavior: [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
and [Codex hooks](https://learn.chatgpt.com/docs/hooks).
