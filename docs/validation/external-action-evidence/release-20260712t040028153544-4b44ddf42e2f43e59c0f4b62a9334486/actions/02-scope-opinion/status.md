# External Action `scope-opinion`

The action is `consumed`; this card is derived from its immutable records and event log.

| field | value |
|---|---|
| State | consumed |
| Intent | second-opinion |
| Requiredness | best-effort |
| Route | engine_id=agy, invocation={'auth': {'mode': 'files', 'paths': ['~/.config/agy/config.json', '~/.gemini/settings.json']}, 'cli': 'agy', 'effort': 'high', 'model': 'Gemini 3.5 Flash (High)', 'recipe': "agy --model 'Gemini 3.5 Flash (High)' --print-timeout 900s --log-file /dev/null --add-dir . --sandbox --print <prompt>", 'via': 'agy:delegate', 'write_capable': False}, protocol=['Assign an explicit adversarial/critic role; do not rely on goodwill.', 'Put behavioral constraints at the top; keep prompts terse and command-style.', "Avoid vague blanket negatives ('don't infer' breaks reasoning).", 'Give explicit stop conditions to counter over-eagerness; put the question last.', 'Set thinking level High on hard tasks; keep temperature default.'], stage=brainstorm, variant=gemini-3.5-flash-high |
| Resolved provider | agy |
| Resolved model | Gemini 3.5 Flash (High) |
| Adapter class | agy:delegate |
| Launch acknowledged | True |
| Receipt validity | valid |
| Cost class | metered |
| Estimated usage | - |
| Observed usage | - |
| Egress | host=agy, policy=networked |
| Evidence destination | .codex/saga/external-actions |
| Consumption point | before requirements write |
| Codex adjudication | accept |
| Consumed artifact | release-matrix://brainstorm/scope-opinion |
| Approval fingerprint | a89d6575750633fc4d7cc1992ff6e7e0ad9476759af9cf574be31ada7c9d7fff |
| Last event | consume |
