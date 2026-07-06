# Decisions

## 2026-07-06: The 0.64 Port Window Lands Fleet-Commons As A Codex fleet-core Plugin

The upstream port window is commit-bounded at Claude `b30e0f2..9470edc` (saga 0.41.0 to 0.64.0), with per-plugin lineage baselines recorded because non-saga plugins were synced earlier than saga. The fleet-commons tier/retry substrate lands as a Codex `plugins/fleet-core` scripts-only plugin mirroring the upstream shape, with the shim resolution ladder rewritten Codex-native (env override, repo walk-up, `~/.codex` layout, fail-loud) instead of emulating Claude's `installed_plugins.json` rungs. `models.json` carries a dual palette: Claude tier names as lineage keys mapped to Codex models and effort ceilings. Saga versions to 0.64.0 as a parity label per the 0.41 precedent, with non-ported surfaces recorded in PORTABILITY.md.

Rejected alternatives: vendoring fleet_commons into each plugin without a fleet-core plugin (structural divergence makes every future sync fan out copies); deferring the substrate (dependent features would hard-code tier/retry logic to be reworked later). Deferred by operator decision: remote gate transport (#379, waits on the redis-channel server-boundary proof), the `agy` plugin (own ecosystem), PreCompact spore and residency hooks (no Codex trigger), marketplace generation.

Revisit when: Codex gains a hook/compaction seam, redis-channel gets its server-boundary proof, or upstream changes the fleet-commons distribution mechanism.

Plan: `docs/plans/2026-07-06-port-claude-plugin-updates-to-0.64-plan.md`.

## 2026-07-02: Discord Guild Art Extends The Existing Identity Assets Plugin

Guild/server icon and image-banner publishing extends `discord-identity-assets` as a sibling target type instead of becoming a new plugin. Bot targets remain under `targets[]`; guild targets use schema v2 `guild_targets[]` with `guild_id_env` and `manage_guild_token_env` references so live guild IDs and tokens stay out of committed state.

The plugin publishes guild icons and Discord guild image banners through the guild API only after signed publish-plan confirmation, token/guild preflight, prompt consistency, and API readback. Discord Server Profile banner color is a UI color setting, not an uploaded image surface for this workflow, so the plugin records `profile_banner_color` as manifest/runbook metadata and does not automate it.

Deferred: server creation, channel/role provisioning, bot invites, Server Profile color automation, and generic team bootstrap orchestration.

## 2026-07-01: Discord Identity Assets Uses A Manifest-First Codex Boundary

The Discord visual identity workflow becomes a new Codex plugin named `discord-identity-assets` with one active skill, a target-repo manifest at `identity/discord-identity-assets.yml`, and deterministic Python scripts for manifest validation, image post-processing, Discord publish, verification, and receipts. Codex-native `image_gen` remains an agent-guided action; packaged scripts do not attempt to invoke it.

Target repositories own non-secret identity contracts and artifacts. The plugin resolves Discord tokens only from approved environment variable names at publish time, rejecting empty or suspicious material before HTTP, so it can integrate with vault conventions without making home-lab vault paths or plaintext secrets part of the reusable center.

The Discord client should use official current-user/current-application semantics where possible, verify bot and application ownership before mutation, and keep a tested compatibility path for the legacy application-ID endpoint used by the old home-lab script. Mimir is the first live proof, staged as dry run, explicit prompt plus publish-plan approval, live publish, and target-repo receipt reconciliation.

Rejected: copying home-lab hard-coded prompt/app registries, making Replicate the reusable generator, putting Discord Developer Portal provisioning in v1, using guild/admin tokens for bot-owned visual identity, and creating individual visual identities for the 31 headless Sons of Ivaldi.

## 2026-06-30: Team Execution Requires A Receipt Before Saga Can Execute It

Saga keeps Team Execution as an active Codex backend, but `orchestration_mode=team-execution` is not executable by itself. Executable Team Execution requires an `orchestration_ref` that resolves to a `## Team Structure` section or a protected Team Execution evidence/state root.

Planning materializes the receipt before a Team Execution plan is considered ready. Work, resume, outcome dispatch, and QA closeout validate the receipt before claiming Team Execution ran. Missing delegated subagents, unsafe delegation, or backpressure select serial Team Execution with the same roles and gates; inline execution is valid only when the operator chose inline or an explicit downgrade is recorded.

Saga owns lifecycle-level provenance: recommendation, explicit operator choice, actual mode, ref, and downgrade. Team Execution owns role-level vehicle evidence such as `team-execution-delegated`, `team-execution-serial`, `generic-subagent`, and `inline-assist`; generic assistance does not satisfy reviewer or validator gates.

Rejected: removing Team Execution from the Codex plugin, treating generic subagents as Team Execution reviewers, fabricating operator choice from actual mode, and minting Team Execution outcome leaves without a real receipt.

## 2026-06-17: Codex Active Plugin Parity Tracks CAMPPS And Codex Backends

Mission Control now treats Jeff Intent, Asgard, and CAMPPS as the active board topology. Mount
Olympus remains vendored only as retired historical context and compatibility data. CAMPPS Project
#4 is the active long-lived initiative board for current CAMPPS routing, with `Idea -> Committed ->
In Progress -> Done -> Parked` as its workflow.

Saga keeps the Codex execution backend set to `inline`, `manual`, and `team-execution`. The source
workflow fan-out backend remains lineage-only and unreachable in active Codex surfaces. Large
no-code-surface work stays `inline` unless cross-repo, consensus, fan-out, deployment, security, infra,
or adversarial-confidence signals require `team-execution`; unsafe automation routes to `manual`.

Rejected: porting Claude commands, agents, `.claude-plugin` manifests, GitHub Actions workflows, or
the source workflow backend as active Codex surfaces.

## 2026-06-09: Track renamed Hermes plugin repo in Mission Control

Mission Control project mappings now use `infiquetra-hermes-plugins` for the Hermes-facing plugin
repository (commit `698b4b0`). The proof script and active portability docs moved with the mapping
so board routing, proof scenarios, and migration guidance stay aligned.

Rejected: relying on GitHub redirects or leaving the old source name in proof fixtures. Redirects do
not help board-routing config or test fixtures, and stale proof data would keep validating the wrong
operator path. Revisit if Mission Control starts discovering repository sets live instead of carrying
a vendored canonical list.

## 2026-05-27: Curated Codex Adapter Repo

`infiquetra-codex-plugins` is a Codex-native adapter repo, not a mirror of the Claude or
Antigravity repos. The active surface is Codex manifests and skills. Claude command files,
top-level agent files, and host manifests are excluded unless a future Codex-native design
explicitly adds an equivalent.

## 2026-05-27: Preserve Lineage Versions

MVP plugin versions preserve the source/cache lineage versions. `sdlc-manager` uses 1.4.0
because that is the Codex-visible cache version and source plugin manifest version.

## 2026-05-27: Cache Is Installed State Only

Installed cache paths define the behavioral baseline but must not be edited as maintained
source. Repo-managed installs can replace cache-managed usage only after documented gates pass.

## 2026-06-06: Saga-Family Replacement Is Gated

The Codex baseline will move from `sdlc-manager` and `blueprint-reviewer` to
`saga`, `deploy`, `mission-control`, and `team-execution`, but the old active
plugins are not deleted until source baseline, capability mapping, known-use
inventory, staged validation, and isolated Codex proof gates pass.

The source snapshot for this replacement is
`infiquetra-claude-plugins@16de95c82ccb2ed80d7f11018e1c2e8247a80a7f`.
Claude command files, agent files, and `.claude-plugin` manifests remain
lineage only. Codex-active ports must be skills, references, scripts, tests,
config, docs, and `.codex-plugin` manifests.

## 2026-06-08: Saga Document Formatting Contract

Codex Saga adopts the shared document formatting contract from
`infiquetra-claude-plugins@abcc06b16763975d71e483a6dac768f4664d7b63`.
All Saga skills that write durable documents link `saga/references/formatting-style.md`.

The contract chooses tables for compact comparative fields and short prose for narrative fields. This
preserves field names for humans and LLM consumers while avoiding the CommonMark collapse caused by
adjacent `**label:**` lines.

## 2026-06-09: Saga Family Documentation Package Shape

The Saga family documentation package will use `docs/saga/` as the canonical operator guide, backed by
standard-library generated lifecycle facts and focused docs drift tests. The guide will explain the
Saga family as `saga`, `mission-control`, `team-execution`, and `deploy` together, while keeping each
plugin's mutation and orchestration boundary intact.

Visual assets will use SVG as the editable source format and `rsvg-convert` for PNG/PDF exports when
available. This avoids adding a new dependency for a documentation package while still producing
presentation-ready assets.

Rejected: one giant Saga README, Mermaid-only centerpiece visuals, and fully hand-drawn diagrams.
Those options either hide ownership boundaries, fail the presentation-quality bar, or drift away from
the routing/state contracts too easily.
