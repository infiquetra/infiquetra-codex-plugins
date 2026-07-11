# Fleet effort convention (Codex)

The active scalar vocabulary is
`fleet_commons.tier_palette.SCALAR_EFFORTS = ("low", "medium", "high", "xhigh", "max")`.
Ultra is not an effort rung: it is root-only orchestration behavior that can add automatic
delegation.

New work selects an execution class. Fleet Core resolves that class against one immutable Codex
model-catalog snapshot, preserving the requested effort across ordered model candidates before it
allows any downward clamp. Roles and allowed risk transitions are owned by Verified Workflows.

```text
logical role -> allowed execution class -> catalog resolution -> managed profile
                                                          |
                                             profile digest proves expected effort
                                                          |
                                             hook proves active model only
```

Codex's direct spawn interface currently has no per-child model or effort field. Consequently:

- The managed custom-agent profile is the enforceable model/effort configuration boundary.
- The exact installed-profile digest is evidence of expected effort.
- The SubagentStart/Stop hook can attest active model and agent type, but not reasoning effort.
- A prompt `EFFORT_RIDER` is advisory only and never proves effective effort.

`effort_rider.inject_effort()` retains historical `workflow`, `external-engine`, and `agent`
branches temporarily for imported consumers. The generic `agent` branch prepends advisory text;
`reconcile_effort()` can prove only that the text was constructed, not that the runtime spent the
requested reasoning effort.

The legacy `tier_palette.EFFORTS` tuple stops at `xhigh` until pre-cutover Saga and Team Execution
consumers migrate. It is source-lineage compatibility, not the active Codex effort policy.
