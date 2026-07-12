# External Action `blind-generator`

The action is `consumed`; this card is derived from its immutable records and event log.

| field | value |
|---|---|
| State | consumed |
| Intent | offload |
| Requiredness | best-effort |
| Route | engine_id=claude-cli, invocation={'auth': {'mode': 'files', 'paths': ['~/.claude/.credentials.json']}, 'cli': 'claude', 'effort': 'high', 'model': 'opus', 'recipe': "claude --safe-mode --tools '' --disable-slash-commands --print --model opus", 'via': 'claude:delegate', 'write_capable': True}, protocol=['Use the approved bounded task and repository clone only.', 'Never claim gate authority or mutate the live Codex worktree.'], stage=ideate, variant=opus |
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
| Consumption point | divergent candidate pool |
| Codex adjudication | accept |
| Consumed artifact | release-matrix://ideate/blind-generator |
| Approval fingerprint | 059abc1472dc3dc24c78a8331f38465817adbfea8d98204ea05df3de8c9eb613 |
| Last event | consume |
