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

HTTP providers use the generic bridge. Endpoint, model, operation, and auth-variable name come only
from the registry row. Provider output is accepted only when its Fleet bridge receipt, invocation
digest, route identity, and output attestation agree. External output is always `non-gating`.
