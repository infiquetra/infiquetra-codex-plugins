# Saga harness adapter contract

`external_action_adapters.py` owns the one-shot adapter boundary. It receives a closed
`saga.harness.request.v1`, resolves the exact `engine_id/variant` from `engine-registry.yaml`, and
returns one `saga.harness.result.v1`.

The harness supports six routes:

- `claude-cli/opus`
- `agy/gemini-3.5-flash-high`
- `agy/gemini-3.1-pro-high`
- `ollama-cloud/gpt-oss-120b`
- `ollama-cloud/nomic-embed-text`
- `deepseek/deepseek-chat`

CLI providers run in a disposable remote-stripped checkout. Direct Saga calls are read-only.
Verified Workflow calls may declare writes; the harness returns a bounded patch without touching
the shared checkout, and only the workflow Git operator imports it.

The `claude-cli/opus` route reads effort only from its selected registry invocation. The adapter
accepts `low`, `medium`, `high`, `xhigh`, or `max`, passes exactly one `--effort <value>` pair in the
process command arguments, and returns unavailable before launch when the configured value is absent,
blank, or unsupported. The receipt proves that effort was requested and passed in the command
arguments; it does not prove the provider observed or applied it.

CLI child environments contain only the allowlisted process basics. A Claude launch additionally
retains a non-blank `USER` so the existing macOS Keychain-backed session can be located; missing or
blank `USER` makes that route unavailable before launch. Non-Claude routes omit `USER`, and every
route continues to omit tokens, credentials, and unrelated parent variables.

HTTP providers use the generic bridge. Endpoint, model, operation, and auth-variable name come only
from the registry row. Provider output is accepted only when its Fleet bridge receipt, invocation
digest, route identity, and output attestation agree. External output is always `non-gating`.
