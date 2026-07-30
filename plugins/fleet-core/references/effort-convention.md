# Fleet effort convention (Codex)

The active scalar vocabulary is
`fleet_commons.tier_palette.SCALAR_EFFORTS = ("low", "medium", "high", "xhigh", "max")`.
Ultra is not an effort rung: it is root-only orchestration behavior that can add automatic
delegation.

New work selects a maintained native profile. Fleet Core resolves compatibility execution classes
against one immutable Codex model-catalog snapshot, preserving the requested effort across ordered
model candidates before it allows any downward clamp. Roles and allowed risk transitions are owned
by Verified Workflows.

```text
logical role -> allowed profile -> expected model and effort
                                      |
                           native agent_type launch
                                      |
                         runtime receipt proves both
```

Codex 0.146 accepts per-child `agent_type`, model, and effort. Consequently:

- The managed profile supplies the default model and effort.
- Profile bytes prove expected configuration only.
- Combined `session_meta` and `turn_context` readback proves effective runtime identity.
- Fleet Core does not inject prompt riders or infer effort from prompt text.

The legacy `tier_palette.EFFORTS` tuple stops at `xhigh` until pre-cutover Saga and Team Execution
consumers migrate. It is source-lineage compatibility, not the active Codex effort policy.
