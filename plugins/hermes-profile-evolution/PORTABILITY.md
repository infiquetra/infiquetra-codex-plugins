# Portability

This is a Codex-native behavior adaptation, not an upstream byte-parity claim.

| Surface | Treatment |
|---|---|
| Team Mimir custody classification | Adapted transport: execute the producer script and validate against the pinned producer fixture. |
| Hermes proposal dialogue | Adapted transport: bounded JSON standard input to canonical `hermes profile-request`. |
| Codex skill discovery | Direct native `.codex-plugin/plugin.json` plus `skills/`. |
| Edit advisory | Direct native `hooks/hooks.json` `PreToolUse` hook for supported file-edit tools. |
| Credentials, route registry, service, profile mutation | External custody; this plugin neither implements nor stores them. |
| Offline queue, background processor, provider/model overrides | Unsupported. |
| Absolute same-user or root enforcement | Unsupported; the hook is a trusted advisory guardrail only. |
| Claude commands or hook manifest | Rejected; no `.claude-plugin`, `commands/`, or `hooks/manifest.json` surface ships. |

Imported files under `conformance/` and their provenance record are immutable producer bytes. The
adapter derives closed response keys, field names, and bounds from those artifacts instead of
copying classifier policy or inventing Hermes doctor fields.
