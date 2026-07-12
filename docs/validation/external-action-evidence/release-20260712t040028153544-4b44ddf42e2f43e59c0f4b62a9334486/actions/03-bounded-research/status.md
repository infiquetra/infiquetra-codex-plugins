# External Action `bounded-research`

The action is `consumed`; this card is derived from its immutable records and event log.

| field | value |
|---|---|
| State | consumed |
| Intent | offload |
| Requiredness | best-effort |
| Route | engine_id=ollama-cloud, invocation={'auth': {'key_env': 'OLLAMA_API_KEY', 'mode': 'bearer'}, 'base_url': 'https://ollama.com/v1', 'effort': 'default', 'model': 'gpt-oss:120b', 'recipe': 'POST https://ollama.com/v1/chat/completions (gpt-oss:120b)', 'via': 'engine-bridge-http', 'write_capable': False}, protocol=['Resolve the bearer token from OLLAMA_API_KEY at request-build time only; never log it.', 'Availability-gated: skip (never fail) when OLLAMA_API_KEY is absent or endpoint unreachable.', 'Advisory only -- never a gate/verdict source (R6, {#external-engines-never-gatekeepers}).'], stage=plan, variant=gpt-oss-120b |
| Resolved provider | ollama-cloud |
| Resolved model | gpt-oss:120b |
| Adapter class | engine-bridge-http |
| Launch acknowledged | True |
| Receipt validity | valid |
| Cost class | free |
| Estimated usage | - |
| Observed usage | 294.0 |
| Egress | host=ollama.com, policy=networked |
| Evidence destination | .codex/saga/external-actions |
| Consumption point | plan grounding |
| Codex adjudication | accept |
| Consumed artifact | release-matrix://plan/bounded-research |
| Approval fingerprint | e226bcf35dd154114d9d31eaa8b119a28dae66adecc9abd37a29f11aba543542 |
| Last event | consume |
