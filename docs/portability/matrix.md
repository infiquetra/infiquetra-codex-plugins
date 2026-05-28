# Portability Matrix

Verified: 2026-05-27

Source snapshot:

- Claude catalog: 16 plugin directories from `infiquetra-claude-plugins` at `8f5baebb35bb865e3680a457ef02aba5cb418ac4`
- Antigravity catalog: 15 plugin directories from `infiquetra-antigravity-plugins` at `c0c4d04a253e7ee4a6b5407600c8144eea3d781f`

Allowed Codex statuses: `included`, `proof-port`, `deferred`, `blocked`, `unsupported`.

Review trigger: rerun this matrix review when either source catalog adds, removes, renames, or
changes a plugin host boundary such as skills, scripts, MCP servers, apps, command files, or
tool-specific orchestration.

| Plugin | Codex Status | Claude Lineage | Antigravity Lineage | Reason | Codex Treatment |
|---|---|---|---|---|---|
| `blueprint-reviewer` | included | yes | yes | Already visible in Codex cache and skill-plus-script payload is portable after path rewrites. | Keep skills and rubric script, omit Claude command files. |
| `docs-generator` | deferred | yes | yes | Documentation generation needs separate proof for repo-specific output conventions. | Reassess after `test-suite` proof and validation patterns settle. |
| `home-lab-ops` | included | yes | yes | Already visible in Codex cache and mostly instruction/reference content. | Keep skills and references, omit top-level agent persona. |
| `identity-toolkit` | deferred | yes | yes | Identity flows are higher risk and need fresh Codex-specific validation before porting. | Inventory only for MVP. |
| `marketplace-lister` | deferred | yes | yes | Marketplace mechanics differ by host and should wait for Codex marketplace validation. | Revisit after this repo is installed from a trusted source. |
| `pagerduty` | deferred | yes | yes | Operational API client with credentials and mutation paths needs separate smoke tests. | Do not port in MVP. |
| `python-toolkit` | included | yes | yes | Already visible in Codex cache and skill content is portable after README rewrite. | Keep skills and references, omit top-level Python expert agent. |
| `redis-channel` | deferred | yes | no | Not present in Antigravity and includes service/server packaging beyond skill docs. | Needs separate server-boundary proof. |
| `sdk-lifecycle` | deferred | yes | yes | Lifecycle automation needs design review for Codex usage model. | Inventory only for MVP. |
| `sdlc-manager` | included | yes | yes | Already visible in Codex cache and script can remain bundled with Codex path updates. | Keep skills, config, script, and script tests; omit Claude command and agent files. |
| `slack` | deferred | yes | yes | Credentialed API client with workspace access; requires credential and dry-run policy review. | Do not port in MVP. |
| `splunk` | deferred | yes | yes | Credentialed search client; requires separate auth and query-safety validation. | Do not port in MVP. |
| `team-execution` | blocked | yes | yes | Claude version depends on `TeamCreate`; Codex and Antigravity do not provide that primitive. | Requires Codex-native redesign, not a direct port. |
| `test-suite` | proof-port | yes | yes | Best first proof for skill plus bundled script packaging without external auth. | Port skill and runner, add dry-run and selected-check validation. |
| `todoist-manager` | deferred | yes | yes | Credentialed productivity API client; not needed for MVP baseline. | Inventory only for MVP. |
| `unifi` | included | yes | yes | Already visible in Codex cache and skill-plus-script payload is portable with confirmation gates. | Keep skills, references, and scripts. |

## Notes

- Count differences are intentional. The Codex MVP has 6 plugins, not the full 16-plugin Claude catalog.
- `team-execution` is not backlog debt. It is blocked until there is a Codex-native orchestration design.
- The `sdlc-manager` rollout field named `claude_md` is retained because it is part of the existing SDLC tracking data model, not a Codex plugin host dependency.
