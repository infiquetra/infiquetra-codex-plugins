# Portability Matrix

Verified: 2026-06-06

Source snapshot:

- Claude catalog: 17 plugin directories from `infiquetra-claude-plugins` at `16de95c82ccb2ed80d7f11018e1c2e8247a80a7f`
- Antigravity catalog: 15 plugin directories from `infiquetra-antigravity-plugins` at `c0c4d04a253e7ee4a6b5407600c8144eea3d781f`

Allowed Codex statuses: `included`, `proof-port`, `deferred`, `blocked`, `unsupported`.

Review trigger: rerun this matrix review when either source catalog adds, removes, renames, or
changes a plugin host boundary such as skills, scripts, MCP servers, apps, command files, or
tool-specific orchestration.

| Plugin | Codex Status | Claude Lineage | Antigravity Lineage | Reason | Codex Treatment |
|---|---|---|---|---|---|
| `deploy` | proof-port | yes | no | Deployment operations are part of the Saga-family replacement and need Codex mutation gates before activation. | Port skills and scripts with dry-run, preview, exact-plan confirmation, auth provenance, and proof-owned mutation guards. |
| `discord-identity-assets` | proof-port | no | no | Codex-born reusable Discord visual identity workflow extracted from home-lab scripts and Norns/Mimir operating evidence. | Add one Codex skill plus deterministic scripts for manifest validation, image post-processing, Discord upload/readback, receipt writeback, and secret-safe dry-run/live gates. |
| `docs-generator` | deferred | yes | yes | Documentation generation needs separate proof for repo-specific output conventions. | Reassess after `test-suite` proof and validation patterns settle. |
| `home-lab-ops` | included | yes | yes | Already visible in Codex cache and mostly instruction/reference content. | Keep skills and references, omit top-level agent persona. |
| `identity-toolkit` | deferred | yes | yes | Identity flows are higher risk and need fresh Codex-specific validation before porting. | Inventory only for MVP. |
| `marketplace-lister` | deferred | yes | yes | Marketplace mechanics differ by host and should wait for Codex marketplace validation. | Revisit after this repo is installed from a trusted source. |
| `mission-control` | proof-port | yes | no | This is the SDLC successor to the old Codex `sdlc-manager` baseline. | Port skills, config, scripts, and tests; add Codex manifests, dry-run/preview gates, allowlists, and exact-plan confirmation. |
| `pagerduty` | deferred | yes | yes | Operational API client with credentials and mutation paths needs separate smoke tests. | Do not port in MVP. |
| `python-toolkit` | included | yes | yes | Already visible in Codex cache and skill content is portable after README rewrite. | Keep skills and references, omit top-level Python expert agent. |
| `redis-channel` | deferred | yes | no | Not present in Antigravity and includes service/server packaging beyond skill docs. | Needs separate server-boundary proof. |
| `saga` | proof-port | yes | no | Saga is the new lifecycle spine and must be ported as Codex skills with namespaced source-parity names. | Port skills, references, scripts, lifecycle state, and handoff envelopes; omit command files and Claude-only backend choices. |
| `sdk-lifecycle` | deferred | yes | yes | Lifecycle automation needs design review for Codex usage model. | Inventory only for MVP. |
| `slack` | deferred | yes | yes | Credentialed API client with workspace access; requires credential and dry-run policy review. | Do not port in MVP. |
| `splunk` | deferred | yes | yes | Credentialed search client; requires separate auth and query-safety validation. | Do not port in MVP. |
| `team-execution` | proof-port | yes | yes | Claude version depends on `TeamCreate`, but the Saga-family target uses managed Codex agents when available and serial fallback otherwise. | Port protocol material as skills and references; convert agents into managed Codex TOML plus registries; prove degraded serial mode. |
| `test-suite` | proof-port | yes | yes | Best first proof for skill plus bundled script packaging without external auth. | Port skill and runner, add dry-run and selected-check validation. |
| `todoist-manager` | deferred | yes | yes | Credentialed productivity API client; not needed for MVP baseline. | Inventory only for MVP. |
| `unifi` | included | yes | yes | Already visible in Codex cache and skill-plus-script payload is portable with confirmation gates. | Keep skills, references, and scripts. |

## Notes

- Count differences are intentional. The active Codex inventory has 9 active plugins, not the full Claude catalog.
- The prior SDLC and document-review plugin roots are superseded by `saga`, `team-execution`, and `mission-control`.
- `team-execution` is no longer blocked as a target. Its Codex design must prove subagent and serial fallback behavior before activation.
- The `sdlc-manager` rollout field named `claude_md` is retained because it is part of the existing SDLC tracking data model, not a Codex plugin host dependency.
