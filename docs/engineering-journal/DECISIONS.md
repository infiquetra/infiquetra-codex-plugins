# Decisions

## 2026-07-24: Codex V2 Owns Live Execution And Verified Workflows Becomes A Minimal Kernel

Codex 0.145.0 MultiAgent V2 becomes the only active workflow execution path after an isolated proof and current-Mac cutover. The main Codex session remains the sole orchestrator and owns workflow preview, approval binding, dependency release, integration, Git, gates, merge, installation, rollback, and completion. Codex V2 owns live agent identity, hierarchy, bounded context, messages, waiting, interruption, and restoration; Saga owns lifecycle state and points to one concise workflow run record under the owner-controlled `~/.codex/verified-workflows/state/<repo>/workflow-runs/` root.

Verified Workflows keeps its public plugin, skill, and 25 logical role identities but replaces the current evidence-chain implementation. Three compact canonical tables declare assignments, exact six-profile mappings, write ownership, checks, reviewers, fallback conditions, and external actions and share one approval digest. Native typed results and deterministic checks feed a small root-owned gate evaluator. A lightweight root audit compares pre/post `HEAD`, branch, index, bounded Git-control state, and porcelain-v2 changed paths; writable work is sequential unless V2 supplies per-agent mutation attribution. Protected subject chains, full workspace snapshots, content-addressed intents, duplicated event records, custom attestation as authority, and the plugin-owned executable DAG leave the active path.

The managed child profiles are `review_max` Sol/max read-only, `review_high` Sol/high read-only, `work_high` Sol/high workspace-write, `test_medium` Terra/medium workspace-write, `scan_low` Luna/low read-only, and `monitor_low` Luna/low read-only with allowlisted external reads. Ultra remains explicit and root-only. Runtime acceptance requires V2 readback of profile/type, model, effort, provider, effective permissions, and canonical identity. Luna remains only if its complete V2 leaf proof passes; otherwise the two low-cost profile IDs move to Terra/low without preserving a V1 fallback.

Saga's external-action lifecycle remains the provider, approval, egress, and adjudication control plane. External actions appear in the same preview and run record. A non-empty external write set requires a registry `write_capable` route and an adapter that captures a bounded patch in the existing contained clone; the root imports it into the shared workspace only after path, Git-metadata, base, dirty-overlap, and secret-boundary checks. Caller input cannot promote a response-only route, and external output never satisfies a gate until the root independently verifies and adopts a finding.

Implementation bootstraps inline because the workflow system is changing itself. The implementation root performs maintained-source and Git mutations. After candidate-byte V2 readback is proved, authority-bearing reviews run under separately started fresh V2 review-root sessions rather than descendants of the implementation root; the implementation root validates their typed results and remains the final orchestrator. Delivery proceeds through reviewed PR, merge, supported installation of the changed plugins and profiles in the current Codex environment, fresh-session proof, and an exercised rollback that restores the pre-cutover repository ref, installed `fleet-core`, `saga`, and `verified-workflows` versions, project/user configuration, profiles, and model catalog. The rollback package is recaptured immediately before host mutation rather than assumed current from the initial baseline. Active V1 scripts and instructions are removed; historical V1 evidence remains lineage only.

The release unit starts only after a preflight proves authority for tracked `.codex`, Git metadata, GitHub, and supported current-user Codex plugin/profile/config/catalog mutation. Missing authority pauses and resumes the same approved plan in a suitable session; it does not convert a required proof, review, or rollback step into an advisory action.

This decision supersedes the 2026-07-18 root-inline feasibility policy and the 2026-07-17 temporary V1 catalog policy after the U8 live cutover gate passes. Until that gate passes, the current installation remains unchanged.

Plan: `docs/plans/2026-07-24-codex-v2-orchestrated-execution-system-plan.md`.

## 2026-07-18: Feasibility Review Keeps Root-Owned Workflows Usable

Verified Workflows must review an approved Workflow Structure against the available Codex capability projection before it is treated as executable. The root Codex session remains the owner of scope, mutation, integration, Git, gates, and completion; native child profiles remain bounded advisory workers unless a runtime can provide authenticated host-issued child attestation.

Preferred-independence lenses use root-inline evidence for gate authority whenever strict child attestation is unavailable. Required-independence lenses remain blocked in that environment rather than being silently downgraded. Risk or file count alone does not justify selecting `verified-workflow`; strict independently attestable execution must be explicit and feasible.

The review is deterministic and read-only. It composes the rendered workflow table with a bounded capability snapshot, reports the required correction by step, and does not launch children, modify runtime configuration, or turn requested model/effort selection into observed execution facts.

Plan: `docs/plans/2026-07-18-workflow-feasibility-review-plan.md`.

## 2026-07-17: Normalize Subject-Exclusion Parent Links And Bootstrap Self-Hosting Fixes Manually

Verified Workflows outside-scope projections will normalize only the raw directory link-count field for the immediate lexical parent of each authorized subject exclusion. APFS changes a directory's link count when an immediate file is added, so retaining that scalar makes an authorized new file look like outside-scope mutation; higher-ancestor links, device, inode, mode, path, visible-entry content, symlink handling, whole-workspace link counts, and unrelated-directory link counts remain strict.

The correction ships as `verified-workflows` `1.0.2+codex.20260718004419`. The manifest, validator expectations, target inventory, generated lifecycle facts, README, changelog, portability status, and direct version tests advance as one release unit.

Verified Workflows cannot grant gate authority to changes in its own implementation. Self-hosting patches therefore use an operator-approved manual bootstrap sequence: root owns implementation, integration, Git, release, and installation; independent named children provide advisory trust-boundary review and platform-test evidence only. The repaired package can resume ordinary Verified Workflow authority after supported installation and source-to-cache readback.

Existing v1 subject records store only an aggregate outside-scope digest and no projection-algorithm version or entry manifest. A chain recorded with the old projection is not retroactively converted; the failed run remains audit evidence and one replacement run replays a mode, size, status, and SHA-256 preservation manifest from its clean baseline without creating a new outcome dispatch. The original worktree remains available until the replacement root receipt seals.

Plan: `docs/plans/2026-07-17-verified-workflows-apfs-subject-snapshot-plan.md`.

## 2026-07-17: Force Sol And Terra Back To MultiAgent V1 Temporarily

Codex 0.144.5 selects the subagent tool version from each model's catalog row. Sol and Terra remain
assigned to MultiAgent V2 even when `features.multi_agent_v2=false`, so the feature flag alone does
not restore named-agent, model, and effort controls. Until V2 exposes those controls reliably, Fleet
Core generates a complete local catalog snapshot and changes only the Sol and Terra
`multi_agent_version` fields to `v1`.

The generated catalog lives under `$CODEX_HOME/model-catalogs/`, is written atomically as UTF-8
without BOM, and is selected by an absolute `model_catalog_json` path. Installation preserves one
rollback copy of the prior config, enables stable MultiAgent, disables V2, and removes the obsolete
V2 namespace workaround. A restart and fresh session are mandatory because Codex pins the
catalog-selected tool schema at startup. Re-run installation after upstream catalog changes.

The five custom-agent profiles and their model/effort mappings remain canonical. Native interactive
delegation uses `verified-workflows:select-agent` before spawn and `/agent` after spawn. Verified
Workflow receipts and gates apply only when that workflow mode is explicitly selected; they do not
block ordinary native agent use.

Ultra is not approved under this workaround. Sol and Terra describe Ultra as automatic delegation,
and no current evidence proves that behavior remains correct when their catalog rows are forced to
V1. A separate runtime proof is required before Ultra can be re-enabled.

This decision temporarily supersedes the 2026-07-11 V2 bootstrap as current runtime policy. The old
capability snapshot and port artifacts remain immutable historical evidence.

Plan: `docs/plans/2026-07-17-codex-v1-agent-compatibility-plan.md`.

## 2026-07-11: Bootstrap MultiAgent V2 For Named Verified Workflow Profiles

Verified Workflows keeps its existing architecture: 25 logical role/lens definitions map through
risk-selected execution classes to five named Codex profiles, and the root thread owns the workflow
DAG, integration, gates, and final adjudication. The earlier conclusion that Sol/Terra could not
select those profiles was a capability-detection error, not a reason to redesign the profile set.

The effective Codex configuration for profile-selected MultiAgent V2 work must include:

```toml
[features.multi_agent_v2]
hide_spawn_agent_metadata = false
tool_namespace = "agents"
```

The root dispatches a fresh named child with `agent_type = <runtime_agent_name>` and
`fork_turns = "none"` by default. `task_name` remains workflow identity only. A positive bounded
turn count is allowed when explicitly justified; omitted or `all` is forbidden for profile-selected
work because full-history forks inherit the parent agent type, model, and effort.

Current V2 also reapplies the live parent permission profile after applying the named role. The five
profile TOMLs remain correct for role/model/effort/instruction selection, but their `sandbox_mode`
cannot narrow a more-powerful parent. Workflow dispatch therefore groups attempts by permission:
read-only scanner/reviewer/monitor children run under a fresh read-only parent, while
`test_medium` runs under workspace-write. Host-issued child rollout context, not child prose, proves
model, effort, role, and effective permission. A parent/child permission mismatch blocks authority.

The runtime bootstrap is a prerequisite, not an assumption. Installation/cutover must verify the
effective config in an isolated task and then a fresh real task, prove a differential parent/child
model and effort, and stop rather than substitute a generic child if `agent_type` is absent or the
child receipt disagrees. User-profile mutation remains a root-owned U8 cutover action with rollback;
an unpublished plugin or ordinary workflow run must not silently edit global Codex configuration.

This decision supersedes only the inline-only/unavailable-selector conclusion in the earlier
2026-07-11 decision and related U4 characterization. It does not weaken named-child receipt,
installed-profile digest, role/lens binding, observed child-context, mutation-audit, structured
result, root-verification, independence, or severity-gate requirements. Inline remains an explicit
degraded path where the role permits it, not the normal model-pinned execution path.

Learning: `docs/engineering-journal/LEARNINGS.md`, "Sol And Terra V2 Can Select Named Profiles
After Namespace Bootstrap."

## 2026-07-11: External Advisory Actions Use One Codex-Owned Runtime

External offload and second-opinion actions use one shared Codex runtime across Ideate, Brainstorm, Plan, Work, Doc Review, and Code Review. Lifecycle stages declare and consume actions; the runtime owns concrete route preview, run-specific approval, dispatch, durable action state, receipts, replay, adjudication, and status projection, while Codex root remains the only live-tree mutation and gate authority.

Each action stores an immutable request and approval record plus an append-only transition log under the repository Git common directory. The store references existing engine manifests and run-ledger facts rather than overloading them, because those surfaces prove execution and record facts but do not model operator approval, requiredness, adjudication, or consumption.

The runtime owns the adapter factory while `engine_dispatch.py` remains the receipt and advisory-evidence validator. V1 adapters are supervised Claude CLI, contained `agy`, and generic OpenAI-compatible HTTP; CLI patch work uses full disposable local clones pinned to a recorded base with remotes removed, write-set diff evidence, terminal cleanup, and no provider application to the live tree.

Repo-and-stage policy moves to `external-action-policy.json`; legacy `engine-prefs.json` values are unapproved desired intent only. Validated provider onboarding applies first to a repo-local registry overlay, canonical promotion is a separate reviewed source change, normal CI remains hermetic, and an explicit attended release harness proves real Claude, `agy`, Ollama Cloud, and all six lifecycle stages before cutover.

Plan: `docs/plans/2026-07-11-codex-external-advisory-execution-contract-plan.md`.

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

## 2026-07-19: Lease-Safe Substrate Ports Byte-Faithful, Gates Per-Port

The #33 port copies the frozen-source lease/settlement modules byte-faithfully (the port manifest's
inventory digest freezes what identifies each row; row state and evidence float underneath), with
exactly two deliberate divergences: the audit-store default root moves to the runtime-neutral
`~/.local/state/infiquetra/delegation-audit`, and the dispatcher lease graft is written codex-native
around the record-only `prepared` seam instead of importing the source's authoritative-mint shape.
Release gating runs through the per-port pytest contract (`tests/test_lease_safe_substrate_port_contract.py`)
because `scripts/port_contract.py validate` is permanently pinned to the 2026-07-11 external-advisory
port (its port_id, refs, row counts, and digests) — the mission-control ports set this precedent.

Rejected: editing the shared CLI validator to accept multiple manifests (would unfreeze a sealed
contract), scoping run_ledger down to the settlement slice (would fork the shared module lineage),
and porting the source's dispatcher shape (would overwrite Codex's intent/ack machinery).

## 2026-07-19: Cross-Runtime Parity Port — Zero-Drift Inventory, Refusal Subsumes Validation

**Decision.** The #34 outcome cross-runtime parity port (manifest
`docs/portability/ports/2026-07-19-outcome-cross-runtime-parity.json`) makes four pattern choices:
(1) the codex preservation inventory is **empty by construction** — the plan's 2026-07-19 refresh
re-grounded it at the execution base `3723a818`, so `historical_plan_base == execution_base` and
there is no drift window to classify (the per-port gate pins this equality so the emptiness is a
provable construction, not an omission); (2) `RUNTIME_LABEL = "codex"` is the **single deliberate
byte divergence** in `outcome_compat.py` — every other byte tracks the frozen Claude source so
future diff-against-upstream stays one-line; (3) legacy `outcome-bundle/1` import is retired by
**wholesale refusal before reading records**, and the record-level chain validators are deleted
with the machinery — a rejection oracle that proves zero writes subsumes per-record validation
that can only run after parsing attacker-supplied bytes; (4) the operator's lease-seam deferral
(KTD6) is pinned as a **test** (`test_dispatcher_lease_seam_stays_dormant_ktd6`), so activating
the seam in this repo requires editing a named guard, not just wiring a call.

**Rejected alternatives.** Enumerating the full #33 substrate diff as preservation rows (59 files
of already-merged, already-gated content — busywork with no new invariant); keeping the import
validators "for reference" (dead code that implies a live path); recording the seam deferral only
in prose (silently reversible).

**Revisit when.** The cross-runtime-acceptance leaf activates the seam (the KTD6 guard test moves
to assert the wired form), or a future port needs a non-empty preservation inventory again (the
zero-drift shape is a special case, not the new default).
