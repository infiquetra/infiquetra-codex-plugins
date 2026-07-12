# External Action `findings-opinion`

The action is `consumed`; this card is derived from its immutable records and event log.

| field | value |
|---|---|
| State | consumed |
| Intent | second-opinion |
| Requiredness | required-before-continue |
| Route | engine_id=ollama-cloud, invocation={'auth': {'key_env': 'OLLAMA_API_KEY', 'mode': 'bearer'}, 'base_url': 'https://ollama.com/v1', 'effort': 'default', 'model': 'gpt-oss:120b', 'recipe': 'POST https://ollama.com/v1/chat/completions (gpt-oss:120b)', 'via': 'engine-bridge-http', 'write_capable': False}, protocol=['Resolve the bearer token from OLLAMA_API_KEY at request-build time only; never log it.', 'Availability-gated: skip (never fail) when OLLAMA_API_KEY is absent or endpoint unreachable.', 'Advisory only -- never a gate/verdict source (R6, {#external-engines-never-gatekeepers}).'], stage=code-review, variant=gpt-oss-120b |
| Resolved provider | ollama-cloud |
| Resolved model | gpt-oss:120b |
| Adapter class | engine-bridge-http |
| Launch acknowledged | True |
| Receipt validity | valid |
| Cost class | free |
| Estimated usage | - |
| Observed usage | 199.0 |
| Egress | host=ollama.com, policy=networked |
| Evidence destination | .codex/saga/external-actions |
| Consumption point | before review verdict |
| Codex adjudication | accept |
| Consumed artifact | release-matrix://code-review/findings-opinion |
| Approval fingerprint | b5dd33673f676a71b7744e6c2d21d7994640902b7a3322cc55f048f7bdb1b0af |
| Last event | consume |
