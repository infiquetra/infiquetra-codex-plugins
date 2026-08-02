# Portability Matrix

Verified: 2026-08-02

Source snapshot:

- Focused Claude import source: 10 plugin directories at `38742ece89880a6b140be237edad6d3f13c97b54`;
  the active contract limits the import to `fleet-core`, `saga`, `team-execution`, and root `tests`
- Antigravity catalog: 15 plugin directories from `infiquetra-antigravity-plugins` at `c0c4d04a253e7ee4a6b5407600c8144eea3d781f`
- Codex portability catalog: 19 tracked identities, including Codex-born and historical deferred rows

Allowed Codex statuses: `included`, `proof-port`, `deferred`, `blocked`, `unsupported`.

Review trigger: rerun this matrix review when either source catalog adds, removes, renames, or
changes a plugin host boundary such as skills, scripts, MCP servers, apps, command files, or
tool-specific orchestration.

| Plugin | Codex Status | Claude Lineage | Antigravity Lineage | Reason | Codex Treatment |
|---|---|---|---|---|---|
| `deploy` | proof-port | yes | no | Deployment operations are part of the Saga-family replacement and need Codex mutation gates before activation. | Port skills and scripts with dry-run, preview, exact-plan confirmation, auth provenance, and proof-owned mutation guards. |
| `discord-identity-assets` | proof-port | no | no | Codex-born reusable Discord visual identity workflow extracted from home-lab scripts and Norns/Mimir operating evidence. | Add one Codex skill plus deterministic scripts for bot and guild manifest validation, image post-processing, Discord upload/readback, receipt writeback, and secret-safe dry-run/live gates. |
| `docs-generator` | deferred | yes | yes | Documentation generation needs separate proof for repo-specific output conventions. | Reassess after `test-suite` proof and validation patterns settle. |
| `fleet-core` | proof-port | yes | no | Shared Codex model/profile resolution, proof schemas, leases, concurrency, orphan evidence, and compatibility policy. | Keep the narrow shared policy canonical in `plugins/fleet-core`, preserve native model-catalog V2 metadata, and keep consumer shims synchronized. Codex owns agent lifecycle and liveness. |
| `hermes-profile-evolution` | proof-port | yes | yes | Profile dialogue requires producer-owned custody and command contracts plus a truthful native advisory boundary. | Call the real Team Mimir classifier, send bounded standard input to canonical Hermes, and ship only a Codex skill plus trusted advisory hook. |
| `home-lab-ops` | included | yes | yes | Already visible in Codex cache and mostly instruction/reference content. | Keep skills and references, omit top-level agent persona. |
| `identity-toolkit` | deferred | yes | yes | Identity flows are higher risk and need fresh Codex-specific validation before porting. | Inventory only for MVP. |
| `marketplace-lister` | deferred | yes | yes | Marketplace mechanics differ by host and should wait for Codex marketplace validation. | Revisit after this repo is installed from a trusted source. |
| `mission-control` | proof-port | yes | no | This is the SDLC successor to the old Codex `sdlc-manager` baseline. | Port skills, config, scripts, and tests; add Codex manifests, dry-run/preview gates, allowlists, and exact-plan confirmation. |
| `pagerduty` | deferred | yes | yes | Operational API client with credentials and mutation paths needs separate smoke tests. | Do not port in MVP. |
| `python-toolkit` | included | yes | yes | Already visible in Codex cache and skill content is portable after README rewrite. | Keep skills and references, omit top-level Python expert agent. |
| `redis-channel` | deferred | yes | no | Not present in Antigravity and includes service/server packaging beyond skill docs. | Needs separate server-boundary proof. |
| `saga` | proof-port | yes | no | Saga is the lifecycle spine and thin external-provider adapter for Codex work. | Keep lifecycle state, handoff envelopes, and six closed provider routes; omit plugin-owned provider lifecycle, preference, promotion, retry, and gatekeeper machinery. |
| `sdk-lifecycle` | deferred | yes | yes | Lifecycle automation needs design review for Codex usage model. | Inventory only for MVP. |
| `slack` | deferred | yes | yes | Credentialed API client with workspace access; requires credential and dry-run policy review. | Do not port in MVP. |
| `splunk` | deferred | yes | yes | Credentialed search client; requires separate auth and query-safety validation. | Do not port in MVP. |
| `team-execution` | proof-port | yes | yes | Retired Codex package and frozen Claude lineage for the completed workflow-package migration. | Preserve historical vocabulary and readable state roots; maintain only the active Codex-native `verified-workflows` package. |
| `test-suite` | proof-port | yes | yes | Best first proof for skill plus bundled script packaging without external auth. | Port skill and runner, add dry-run and selected-check validation. |
| `todoist-manager` | deferred | yes | yes | Credentialed productivity API client; not needed for MVP baseline. | Inventory only for MVP. |
| `unifi` | included | yes | yes | Already visible in Codex cache and skill-plus-script payload is portable with confirmation gates. | Keep skills, references, and scripts. |

## Notes

- 2026-08-02: `hermes-profile-evolution` `0.1.0` consumes pinned producer conformance
  artifacts. It exposes one Codex skill and one native advisory `PreToolUse` hook. Credentials,
  profile mutation, offline queuing, and absolute same-user enforcement remain outside the plugin.

- 2026-07-29: Codex 0.146 alignment removes repository-local agent copies, `select-agent`,
  snapshot feasibility gating, plugin-owned lifecycle substitutes, and Fleet audit/delegation
  state. Seven minimal profiles remain; Luna is still V1 so low V2 profiles stay on Terra.
  Verified Workflows keeps contracts, typed results, bounded deviations, direct-sibling review,
  concise gates, and the Git operator. Historical proof and lineage artifacts remain historical.

- 2026-07-19: the lease-safe substrate port (#33) lands the frozen `a6f3bcff..cf15a09f`
  fleet_commons broker/orphan/policy/audit modules and the saga settlement adapter inside the
  already-included `fleet-core` and `saga` identities (fleet-core 0.9.0, saga 0.77.0
  after the #34 cross-runtime parity port) — no new
  portability identity; contract at `docs/portability/ports/2026-07-19-lease-safe-substrate.json`.

- Count differences are intentional. The active Codex marketplace has 10 plugins, not the full portability catalog.
- The prior SDLC and document-review plugin roots are superseded by `saga`, `verified-workflows`, and `mission-control`.
- `verified-workflows` `3.0.0+codex.20260729164721` is the V2-only release candidate.
  `team-execution` remains only as frozen lineage and legacy-readable state vocabulary.
- The target fixture exposes `verified-workflows:run`, `verified-workflows:review-workflow`, and
  `verified-workflows:appsec-audit`; direct launches use native `agent_type`. The Claude catalog
  retains one `team-execution` lineage row;
  `verified-workflows` is not a second upstream identity.
- The `sdlc-manager` rollout field named `claude_md` is retained because it is part of the existing SDLC tracking data model, not a Codex plugin host dependency.

## Maintained Source Authority

| Surface | Authority | Rule |
|---|---|---|
| Vendored `mission-control` behavior | `infiquetra-claude-plugins` | Change the canonical copy first, then synchronize this adapter. |
| Codex adapters and Codex-born plugins | This repository | Upstream commits are lineage inputs, not maintained Codex source. |
| Shared execution policy and proof | `plugins/fleet-core` | Consumer shims remain synchronized derivatives. |
| Saga lifecycle and continuation | `plugins/saga` | Preserve existing Codex behavior while applying classified upstream changes. |
| Workflow package | This repository's `verified-workflows`; frozen Claude `team-execution` lineage | Maintain exactly one active marketplace identity and preserve legacy reads without reviving legacy writers. |
| Installed cache, profiles, and hook trust | Installed-state evidence only | Never edit or import them as maintained source. |
