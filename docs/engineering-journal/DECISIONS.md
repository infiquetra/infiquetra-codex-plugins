# Decisions

## 2026-07-11: Complete U4 Inline, Preserve Named-Child Proof, Then Pause

The modernization run completes U4 in the root thread as five sequential checkpoints: workflow contract/compiler, behavior-preserving receipt-module extraction, executable receipts/root verification, severity-first gates, and named-child selection plus attestation. Extraction reduces the 6,000-plus-line receipt facade into cohesive modules without deleting schemas or behavior.

Named-profile definitions and named-child proof remain in U4 because precise child model/effort selection requires both halves. Selection proves the host accepted one of the five managed profiles; attestation joins the selected profile to hook-observed model, installed-profile digest, expected effort, role/lens, permission, child identity, and result. The current generic spawn schema exposes no profile selector, so U4 may truthfully end as `diagnostic`; definitions and hook evidence alone are not enforcement.

Only raw-hook operational maintenance moves to U8: start-only/stop-only abandonment, digest-bound prune, and deletion after normalized readback. U4 retains safe capture, pair loading, normalized persistence, consumption markers, and exact-readback recovery of prepared normalization transactions because those are part of crash-safe attestation.

After U4 passes its focused and integrated checks, the root writes the U5-U8 `## Workflow Structure` and pauses. U5-U8 may use model-pinned `scan-low`, `test-medium`, `review-high`, `review-max`, and `monitor-low` children only after named-profile selection plus attestation is proved. Otherwise the workflow remains paused unless the operator explicitly accepts a less precise root-inline or generic-child fallback. Verified Workflows may coordinate later units but never accepts its own output; root diff, tests, severity judgment, Git, cutover, and formal code review remain authoritative.

Plan: `docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`.

## 2026-07-10: Verified Workflows Replaces Team Execution And Future Ports Are Contract-Gated

The Codex adapter no longer models reviewer and validator execution as a Claude-style peer team. The canonical package becomes `verified-workflows` `1.0.0`, with `verified-workflows:run`, Saga mode `verified-workflow`, `## Workflow Structure`, canonical Verified Workflows state and receipt vocabulary, and a root-owned DAG. The root Codex thread owns spawn, follow-up, wait, integration, remediation routing, and adjudication.

Readers accept centralized legacy Team Execution aliases, but new serializers emit only canonical vocabulary and append-only historical artifacts are never rewritten.

All 25 logical role IDs remain stable, but job semantics are separated from five execution profiles: `review-max`, `review-high`, `test-medium`, `scan-low`, and `monitor-low`. Agent-lenses have default and allowed risk-adjustable classes plus required-or-preferred independence; deterministic validators bind scripts and evidence schemas without an LLM class. A workflow receipt binds logical role, selected class/profile, hook-observed model, installed-profile digest, role/lens digest, child/task identity, and result.

The profile digest is accepted proof of expected effort because current hooks report model but not reasoning effort. Required role evidence, no unresolved blocker, required validator success, and root verification are authoritative; numeric scores are supporting evidence only.

Future Claude-to-Codex imports must follow `docs/portability/claude-to-codex-plugin-port-runbook.md` and carry a versioned, closed-schema JSON manifest validated by `scripts/port_contract.py`. The manifest binds its runbook digest, the historical Codex plan base and approved execution-base preservation inventory, frozen Claude refs and exact pathspec-scoped source inventory, the current Codex capability-snapshot digest, per-path treatment, preserved Codex-only invariants, staged target/test evidence, version policy, review, isolated install, fresh-session proof, and rollback. Classification blocks source work, per-unit evidence blocks integration, and complete cutover evidence blocks release.

Generated classification drift, missing source or Codex-drift rows, active Claude-only primitives, or incomplete evidence fail the corresponding gate.

Cross-plugin old/new vocabulary lives in one fleet-core compatibility registry consumed through each plugin's normal shim; Saga and Verified Workflows do not import each other. Cutover proves both clean installation and seeded old-to-new migration. Exact restoration material remains in a protected uncommitted rollback bundle, while committed evidence contains only sanitized inventories and hashes.

Rejected: retaining the Team Execution name as the canonical Codex identity, globally replacing historical/upstream names, maintaining 25 manually coupled model profiles, collapsing roles without equivalence fixtures, requiring peer-to-peer agent messaging, or relying on a prose-only port checklist.

Plan: `docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`.

## 2026-07-10: Execute The Modernization Through Codex-Native Subagents

The model/execution modernization plan runs with Saga's `inline` backend and direct Codex subagents, not Team Execution. `inline` identifies the root Codex thread as the runtime owner; it does not prohibit the existing `/work` mechanics for serial or parallel generic subagents. The root owns Saga state, integration, Git, installed-state mutation, final verification, and completion decisions, while bounded children perform requested-read-only exploration, one-writer implementation slices, fresh-context review, and focused validation under root-owned mutation checks.

The preferred execution policy is Sol/max for the root coordinator, Terra/medium for explorers, Sol/high for implementation and judgment-heavy review, Terra/medium for validators, and Luna/low for deterministic scans. The root selection is explicit. Child model, effort, named-agent, and sandbox selections are preferences until the active spawn surface returns readback or a selected custom-agent profile is proved by runtime receipt; an installed file or prompt request alone is not enforcement. Ultra is not used because this plan already defines explicit bounded fan-out.

Concurrency uses the lower of host-advertised capacity and `agents.max_threads`. U1-U7 prefer parent `workspace-write`; requested-read-only waves use pre/post worktree snapshots, fresh-context reviewers and validators use `fork_turns=none`, shared-worktree writes remain single-writer, and pre-existing path overlap pauses the unit until ownership is resolved. Real-profile mutation is root-only in U8 after isolated proof. Team Execution profiles, receipts, gates, consensus, and advisory logic are systems under test in U3/U4/U7/U8 and never accept their own implementation.

Rejected: serial Team Execution as the bootstrap protocol, treating generic Codex children as Team Execution evidence, or adding another permanent orchestration plugin solely to run this plan.

Plan: `docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`.

## 2026-07-10: Modernize Codex Model And Execution Truth Before The Next Claude Import

The next port cycle is commit-bounded at Codex `788902513e48ea95fd0504ac3c850c8c02e5d920` and Claude `38742ece89880a6b140be237edad6d3f13c97b54`, a focused `9470edc..38742ece` window of 156 files across fleet-core, Saga, team-execution, and their tests. The cycle first separates lifecycle state, continuation, dispatch vehicle, role identity, model/effort policy, and hooks; it then modernizes fleet-core, activates and attests Team Execution, repairs Saga's real-launch boundary, and only then imports the Claude engine/trust/reconciliation delta.

The Codex model policy keeps `fable`/`opus`/`sonnet`/`haiku` only as lineage keys. Preferred mappings are Sol/max for exceptional bounded root judgment, Sol/high for reviewer judgment, Terra/medium for general workers and testers, and Luna/low for scanners and monitors, with catalog-aware ordered fallbacks. Scalar effort is `low..max`; Ultra is a root orchestration profile because it adds automatic delegation and is prohibited in leaf agent profiles.

Managed Team Execution agent files must carry active `model` and `model_reasoning_effort`, but installation alone is not execution proof. Delegated evidence requires a receipt binding named role, child identity, hook-reported active model, the digest of the exact installed TOML (which binds expected effort because the hook does not report it), and result vehicle. Generic subagents never satisfy Team Execution gates, and a fresh isolated proof may leave the capability explicitly `serial-only`. P0, security, and required-validator hard failures remain blocking after the three-cycle remediation cap.

Saga keeps durable lifecycle/outcome state. Goal is explicit long-running continuation, hooks are event extensions, and Team Execution is a dispatch/gate protocol; none is a substitute execution backend. Outcome dispatch becomes a v2 intent plus typed acknowledgement: only `launched` creates dispatched work, `handed-off` is visible but not launched, and legacy commit records remain settled as `legacy-unverified` until append-only evidence reconciliation. A synthetic `leaf-*` id cannot advance state by itself. Codex hooks are behavioral adaptations with explicit trust, prompt-free contained receipts, and no surprise Git mutation; blocking PreToolUse enforcement is deferred while unified-exec interception remains incomplete.

Target Codex releases are fleet-core `0.8.4` and Saga `0.75.17`, preserving the frozen source-lineage labels, plus team-execution `2.4.0` on its existing Codex adapter line. Codex differences remain explicit in `PORTABILITY.md`; no version claims byte parity. Metadata changes land last, after locked-environment tests, isolated install, agent sync, hook trust, fresh-session capability proof, and a recorded managed-surface rollback path.

Rejected: importing Claude `0.75.17` before fixing model/runtime foundations, treating Ultra as a scalar leaf effort, inheriting the mutable machine default, counting installed TOMLs or a simulated probe as named dispatch, keeping Goal/hooks/subagents/Workflow in one backend enum, copying Claude hooks/commands, or editing installed cache as source.

Plan: `docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`.

## 2026-07-07: Saga Resolves Sibling Plugins From The Codex Plugin Environment

Saga outcome board-sync depends on mission-control, and several plugins depend on fleet-core, but those are sibling plugin dependencies, not files under the consumer repository. Runtime resolution should therefore start from the executing script's plugin environment: source checkout or local marketplace `plugins/<name>` siblings first, then installed-cache marketplace versions, with explicit env overrides only for fleet-core.

Rejected: hardcoding `/Users/jefcox/...` paths, requiring every outcome consumer repo to vendor mission-control, or weakening the board-sync certificate to route around a missing path. The fix must keep board-write authorization and idempotency unchanged while resolving the correct dependency root.

Plan: `docs/plans/2026-07-07-outcome-plugin-dependency-resolution-plan.md`.

## 2026-07-06: The 0.64 Port Window Lands Fleet-Commons As A Codex fleet-core Plugin

The upstream port window is commit-bounded at Claude `b30e0f2..9470edc` (saga 0.41.0 to 0.64.0), with per-plugin lineage baselines recorded because non-saga plugins were synced earlier than saga. The fleet-commons tier/retry substrate lands as a Codex `plugins/fleet-core` scripts-only plugin mirroring the upstream shape, with the shim resolution ladder rewritten Codex-native (env override, repo walk-up, `~/.codex` layout, fail-loud) instead of emulating Claude's `installed_plugins.json` rungs. `models.json` carries a dual palette: Claude tier names as lineage keys mapped to Codex models and effort ceilings. Saga versions to 0.64.0 as a parity label per the 0.41 precedent, with non-ported surfaces recorded in PORTABILITY.md.

Rejected alternatives: vendoring fleet_commons into each plugin without a fleet-core plugin (structural divergence makes every future sync fan out copies); deferring the substrate (dependent features would hard-code tier/retry logic to be reworked later). Deferred by operator decision: remote gate transport (#379, waits on the redis-channel server-boundary proof), the `agy` plugin (own ecosystem), PreCompact spore and residency hooks (no Codex trigger), marketplace generation.

Revisit when: Codex gains a hook/compaction seam, redis-channel gets its server-boundary proof, or upstream changes the fleet-commons distribution mechanism.

Plan: `docs/plans/2026-07-06-port-claude-plugin-updates-to-0.64-plan.md`.

## 2026-07-06: Baseline Freeze Holds At `9470edc` Despite Further Upstream Drift

U1 baseline-freeze verification found Claude `origin/main` had already moved to
`43646b3` (past the plan's `9470edc` boundary) by the time discord-identity-assets
0.2.0 and this plan landed. Per KTD1, the window is not silently extended:
implementation units U2 through U9 read only the `b30e0f2..9470edc` delta (31
commits, 141 files, confirmed by direct diff). Chasing `43646b3` requires a
deliberate plan amendment with its own commit-bounded window, not an in-flight
scope change during port execution.

Rejected alternative: quietly picking up the newer upstream commits while
implementing, since "more current" felt strictly better — rejected because it
mixes evidence from two different upstream snapshots into one classification
and breaks the reproducibility the commit-bounded window is meant to guarantee.

Revisit when: the 0.64 port window closes and a new cycle is opened against a
fresh upstream ref.

Artifact: `docs/portability/codex-saga-064-drift-classification.md`.

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
