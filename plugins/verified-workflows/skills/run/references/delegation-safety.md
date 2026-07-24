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
reviewers and validators receive a fresh execution context for every attempt when the runtime
exposes that option. A follow-up message is limited to status or clarification inside the current
attempt; it cannot revise the intent or create gate evidence.

Subagents inherit parent permission choices, and live overrides can supersede profile defaults.
Therefore the V2 `turn_context` permission profile and the profile's configured `sandbox_mode`
remain separate facts. A read-only label or profile is requested policy until runtime readback and
the root workspace audit agree. Broad permission modes remain outside gate-authoritative work.
Requested read-only output needs a root-recorded pre/post mutation-audit digest with no observed
writes before it can enter the gate; otherwise it remains advisory. The audit covers repository
dirty, untracked, and ignored files with content, mode, and symlink readback, plus hashed Git HEAD,
index, config, hooks, all refs, logs, and operation state. Empty directories are outside the audit
claim because they do not affect repository content. Quiesce every other root/test/Git writer for
the audit interval so a concurrent legitimate write cannot invalidate or be mistaken for child
behavior.

Use a fresh attempt ID and canonical agent path for remediation or revalidation. Peer communication
is optional and never required for correctness. Backpressure, missing named-profile selection, or
runtime receipt mismatch blocks required independence.

Approved external-action rows are dispatched through Saga, not through the native agent DAG. CLI
routes are advisory and read-only, receive a minimal environment, and materialize only declared
context after path and secret-content checks. Non-empty external write sets fail closed until an
enforceable filesystem boundary exists. The action's status may be recorded in the same workflow
run record, but its authority remains `non-gating`.

Codex V2 `session_meta` plus `turn_context` provide runtime identity and effective-permission
readback. The root validates those events against the approved launch and combines them with the
typed terminal result and workspace audit; plugin hooks are not part of the active authority path.

Official current behavior: [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
and [Codex hooks](https://learn.chatgpt.com/docs/hooks).
