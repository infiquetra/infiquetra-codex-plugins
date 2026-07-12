# External Action `stuck-opinion`

The action is `consumed`; this card is derived from its immutable records and event log.

| field | value |
|---|---|
| State | consumed |
| Intent | second-opinion |
| Requiredness | best-effort |
| Route | engine_id=claude-cli, invocation={'auth': {'mode': 'files', 'paths': ['~/.claude/.credentials.json']}, 'cli': 'claude', 'effort': 'high', 'model': 'opus', 'recipe': "claude --safe-mode --tools '' --disable-slash-commands --print --model opus", 'via': 'claude:delegate', 'write_capable': True}, protocol=['Use the approved bounded task and repository clone only.', 'Never claim gate authority or mutate the live Codex worktree.'], stage=work, variant=opus |
| Resolved provider | claude-cli |
| Resolved model | opus |
| Adapter class | claude:delegate |
| Launch acknowledged | True |
| Receipt validity | valid |
| Cost class | metered |
| Estimated usage | - |
| Observed usage | - |
| Egress | host=claude-cli, policy=networked |
| Evidence destination | .codex/saga/external-actions |
| Consumption point | before remediation |
| Codex adjudication | accept |
| Consumed artifact | release-matrix://work/stuck-opinion |
| Approval fingerprint | e90f4a734f50c069e1d5b4153ab642841f263f196f0f7bc3e6382289dd7e1b54 |
| Last event | consume |
