---
date: 2026-06-30
topic: discord-visual-identity-publisher
focus: Reusable Codex plugin/skill for team-repo Discord visual identity assets, live upload, and verification
scope: broad
repo: infiquetra-codex-plugins
maturity: idea-ready
---

# Ideation: Discord Visual Identity Publisher

## Grounding Context

**Repo:** `infiquetra-codex-plugins` is a curated Codex-native adapter repo, not a Claude mirror. Active plugin source lives under `plugins/<name>/.codex-plugin/plugin.json` and `plugins/<name>/skills/`, with the repo-local marketplace and `docs/portability/matrix.md` kept in sync. Codex-active ports must be skills, references, scripts, tests, config, docs, and `.codex-plugin` manifests, while cache copies are installed proof state, not source. `docs/engineering-journal/QUEUED.md:3` explicitly calls out the need to prove a credentialed API-client plugin boundary before porting identity-like tooling.

**Context-libraries:** `infiquetra-context-library` contributed one relevant constraint: Discord identity is not cosmetic in the operating model. `platform-specs/05-technical-specifications/attention-surface.md:11` says the operator triages by direct Discord sender identity, and `:32-35` forbids aggregation while keeping self-ordering local. That makes visual identity correctness part of the attention surface, not just polish.

**Named repos:** `home-lab` contributed the legacy workflow and endpoint lessons: Developer Portal creation/token/app-ID capture are manual/browser-drivable, while avatar, app icon, and profile banner upload are deterministic API calls. The reusable material is the endpoint and vault behavior; the hard-coded prompt/app-ID/guild registries and Replicate dependency are legacy reference material.

**Named repos:** `team-norns` contributed the successful Codex image_gen precedent and the reusable asset convention: upload assets under `assets/discord/avatars/` and `assets/discord/banners/`, generated originals under `assets/discord/originals/`, and non-secret Discord config placeholders in repo files. Its journal records the key Discord lesson: use the owning bot token for bot visual identity, set avatar/banner through `/users/@me`, set app icon through the application endpoint, and verify hashes after upload.

**Named repos:** `team-mimir` is the right v1 pilot if scoped to public identities. Mimir has rich SOUL material for `mimir`, `brokkr`, `eitri`, and `sons-of-ivaldi`, but the 31 Sons are headless and share one collective crest. `assets/icons/README.md:14-26` names the four persona icon paths and says the Sons share one crest; `docs/team/roster.md:7-12` says roster icons are still placeholders pending art migration. For the first proof, the operator wants Mimir's live Discord bot avatar, app icon, and bot profile banner updated and verified, not only files committed.

## Topic Axes

1. Product boundary and plugin shape
2. Repo-local identity contract
3. Generation and post-processing
4. Credentialed upload and verification
5. Provisioning and bootstrap integration

## Ranked Survivors

### 1. Discord Visual Identity Publisher

Create a new Codex plugin/skill focused on Discord visual identity publishing for team repos.

The core skill guides Codex-native image_gen use, then hands deterministic work to packaged scripts: preserve originals, normalize/crop/resize upload files, upload bot avatar, Developer Portal app icon, and bot profile banner, and verify Discord readback. It should be a new plugin rather than a `home-lab-ops` extension because the reusable center is no longer home-lab deployment; it is a credentialed team-repo publishing workflow.

This is the strongest survivor because it matches the actual churn: searching old home-lab runbooks, reconstructing vault/app-ID state, and manually proving Discord changed. The downside is that it makes this repo prove a credentialed API-client boundary, so v1 needs dry-run, no-secret logging, mocked tests, and a live pilot receipt before being treated as routine.

| field | value |
|-------|-------|
| basis | direct: `team-norns/docs/engineering-journal/LEARNINGS.md:33-45` recorded the endpoint and verification lesson; `home-lab/scripts/upload_ai_icons.py:156-224` shows the existing avatar/icon/banner API calls; user context requires live Mimir Discord update |
| confidence | 92 |
| complexity | Med |
| axis | Credentialed upload and verification |
| status | Explored |

### 2. Repo-Local Identity Asset Manifest

Make the team repo describe the identity work before the plugin acts.

The manifest should record profile/persona names, source documents for prompt grounding, avatar/icon/banner paths, original and final asset destinations, Discord application IDs, bot user IDs, token variable names, and evidence output paths. It should record names and references only, never token values, and it should let Codex enter a repo cold without searching `home-lab`.

This converts the workflow from institutional memory into a repo contract. The main downside is schema discipline: if the manifest duplicates `deploy/team_profiles.yml` carelessly, it becomes another stale registry; the design should either read existing deploy truth or make the manifest a thin overlay.

| field | value |
|-------|-------|
| basis | direct: `team-norns/deploy/well_of_urd.example.yml:18-39` maps profiles to token vars, app IDs, and asset paths; `team-mimir/deploy/team_profiles.yml:12,49,85,112` holds current runtime token vars and bot user IDs |
| confidence | 88 |
| complexity | Med |
| axis | Repo-local identity contract |
| status | Unexplored |

### 3. Evidence Receipt as Product Output

Treat prompts, files, hashes, and Discord readback as the thing the workflow ships.

Each run should preserve generated originals, final upload assets, final prompts, prompt source references, local file hashes, dimensions, upload endpoints, returned Discord hashes, and a compact runbook/evidence artifact in the team repo. For live publish mode, the receipt should distinguish local file state from proved Discord state.

This plugs the exact gap Norns left: the repo has good final assets and a journal claim, but not a reusable evidence payload future Codex sessions can replay. The downside is modest extra ceremony, but it pays back immediately by making future visual identity work auditable.

| field | value |
|-------|-------|
| basis | direct: `team-norns/docs/runbooks/well-of-urd-bootstrap.md:18-21` preserves originals/finals; `team-norns/docs/engineering-journal/LEARNINGS.md:39-41` records verification happened but not the actual receipt payload |
| confidence | 87 |
| complexity | Low |
| axis | Generation and post-processing |
| status | Unexplored |

### 4. Generate-Only / Publish Gate Split

Separate creative file production from live Discord mutation.

The skill should support generate-only/post-process-only by default, then require an explicit publish gate that prints the exact Discord targets, token variable names, endpoints, and assets before any PATCH. Publish mode should verify token ownership with `/users/@me`, reject suspicious newline/empty tokens, suppress secret output, and record the approval/evidence boundary.

This keeps the user-facing workflow unified without pretending all steps have the same risk. The downside is a little more command structure, but the Mimir journal's secret-diff incident makes a casual "dry-run is safe" posture unacceptable.

| field | value |
|-------|-------|
| basis | direct: `team-mimir/docs/engineering-journal/LEARNINGS.md:744-750` records secret leakage through Ansible diff; `team-norns/docs/engineering-journal/LEARNINGS.md:85-104` records token newline failure; user seed requested generate-only and generate plus upload modes |
| confidence | 86 |
| complexity | Med |
| axis | Credentialed upload and verification |
| status | Unexplored |

### 5. Mimir-First Live Pilot

Prove v1 by updating Mimir's live Discord bot avatar, app icon, and profile banner.

The first acceptance proof should target the visible Mimir bot identity the operator named, not all of Mimir's headless workers. The manifest should still be designed so a later run can cover the four public identities: `mimir`, `brokkr`, `eitri`, and `sons-of-ivaldi`.

This is a strong pilot because it proves the workflow outside Norns while using a repo with explicit identity material and visible asset gaps. The downside is live mutation risk; the pilot should happen only after a dry-run plan, local asset receipt, secret-safe token resolution, and explicit approval.

| field | value |
|-------|-------|
| basis | direct: `team-mimir/assets/icons/README.md:14-26` defines the public persona set and shared Sons crest; `team-mimir/docs/team/roster.md:7-12` says art is missing; user context requires Mimir's live Discord avatar/icon/banner update |
| confidence | 85 |
| complexity | Med |
| axis | Product boundary and plugin shape |
| status | Unexplored |

### 6. Guided Provisioning as Adjacent Skill

Keep Discord application creation in scope, but out of the core publisher path.

A second skill can guide Developer Portal application creation, token reset/capture, app ID capture, and OAuth invite consent through Chrome/computer-use when the user wants it. It should output non-secret manifest updates and checklist evidence, then hand off to the publisher once app IDs and tokens exist.

This acknowledges that new bot creation is part of routine team identity setup without mixing browser-state brittleness into the deterministic upload/verify core. The downside is that it depends on live browser auth and human consent clicks, so it should be a guided phase rather than the v1 proof gate.

| field | value |
|-------|-------|
| basis | direct: `home-lab/Discord-Bot-Creation-Instructions.md:24-31` lists Developer Portal creation/token/app-ID capture as manual but browser-drivable; `:64-76` says OAuth invite requires human consent |
| confidence | 79 |
| complexity | High |
| axis | Provisioning and bootstrap integration |
| status | Unexplored |

### 7. Server/Guild Asset Module

Support server icon and banner as a separate module with a different authority boundary.

The plugin family should eventually handle Discord home/server icon and banner assets, because Norns needed them and future teams will too. It should not be part of the Mimir v1 proof because Mimir's ask is bot avatar/icon/banner only, and guild/server assets use guild authority rather than the owning bot token.

This preserves the unified product story without collapsing distinct permission surfaces. The downside is extra scope; keep it behind a separate module or mode until the bot-identity publisher is proven.

| field | value |
|-------|-------|
| basis | direct: `team-norns/docs/runbooks/well-of-urd-bootstrap.md:7-31` includes server icon/banner assets and guild vault variables; user context said server assets should stay in scope generally, but Mimir proof should update only bot avatar/icon/banner |
| confidence | 74 |
| complexity | Med |
| axis | Product boundary and plugin shape |
| status | Unexplored |

## Did not survive (revivable)

Explicit rejection is the quality mechanism. Cut ideas keep stable ids so they can be revived with new evidence.

| id | title | summary | reason | status |
|----|-------|---------|--------|--------|
| R1 | Full Team Bootstrap Monolith | One plugin owns decisions, VM creation, Hermes deploy, souls, strategy, Discord home, bots, assets, and evidence. | Scope overrun: mixes different consumers, credentials, and operational risk classes; better as single pane of glass over smaller blocks. | rejected |
| R2 | Home-Lab Script Port | Copy home-lab Discord asset scripts into a Codex plugin with minimal edits. | Not Codex-native: hard-coded prompt/app-ID/guild registries and Replicate dependency are the churn source, not the reusable center. | rejected |
| R3 | Replicate-Primary Generator | Keep Replicate FLUX-schnell as the main automated generator. | Violates the chosen Codex-native image_gen direction and keeps generation tied to external token/env setup. | rejected |
| R4 | Per-Worker Mimir Fanout | Generate assets for all 31 Mimir worker profiles. | Contradicts Mimir's identity boundary: headless Sons have no individual public Discord/GitHub identity. | rejected |
| R5 | No-Live-Mutation MVP | Stop v1 at generated repo files and a dry-run upload plan. | Fails the operator's explicit evidence bar: Mimir must be updated and verified in live Discord. | rejected |
| R6 | Browser Provisioning Inside Core Publisher | Make the core publisher create Discord applications before asset generation. | Different brittleness and approval model; keep as guided provisioning, not the deterministic publisher core. | rejected |
| R7 | Server Home Provisioning in V1 | Create guild, channels, roles, permissions, and server art in the first proof. | Scope overrun for the Mimir proof; useful later but not required to prove bot visual identity publishing. | rejected |
| R8 | SVG-First Roster Icon Pipeline | Generate SVG persona icons first, then derive Discord assets. | Covers Mimir docs roster needs but does not directly prove live Discord avatar/icon/banner publishing. | rejected |
| R9 | Generic Team Identity Plugin | Name the first plugin broadly around all team identity assets. | Too vague for v1; the stronger boundary is Discord visual identity publishing with explicit adjacent modules. | rejected |

## Co-ideation log

| source | entered | idea / seed | outcome |
|--------|---------|-------------|---------|
| user-seed | Phase 0 | Reusable skill should orchestrate Codex-native image_gen for Discord avatars/banners/server icons. | survived as #1 with server assets split to #7 |
| user-seed | Phase 0 | Bundle deterministic scripts for resize, normalize, upload, and verify. | survived as #1 |
| user-seed | Phase 0 | Prompts should be team-local, not hard-coded in home-lab dictionaries. | survived as #2 and #3 |
| user-seed | Phase 0 | Support generate-only and generate plus upload modes. | survived as #4 |
| user-seed | Phase 0 | Upload should use vault/token conventions without committing secrets. | survived as #2 and #4 |
| user-seed | Phase 0 | Preserve originals, finals, prompts, and verification evidence. | survived as #3 |
| user-seed | Phase 0 | Write or update a runbook/checklist. | survived as #3 |
| user-seed | Phase 0 | Replace old Replicate-centered home-lab workflow for new work. | survived as #1; Replicate-primary cut as R3 |
| user-seed | Phase 0 | Distinguish reusable identity assets from home-lab deployment/guild provisioning. | survived as #1, #6, and #7 |
| user-seed | Phase 0 | Keep guided Discord bot creation in scope as separate provisioning. | survived as #6 |
| user-seed | Phase 0 | Verify v1 by updating Mimir's live avatar/icon/banner in Discord. | survived as #5; no-live-mutation MVP cut as R5 |

## Recommended Next Step

Route the top survivor cluster to `/brainstorm`, not `/plan` yet.

The strongest idea is already more than a name, but it is not requirements-ready because the manifest contract, secret-safe token resolver, evidence schema, and live Mimir pilot gates need to be specified together. `/brainstorm` should deepen survivor #1 with #2, #3, #4, and #5 as required companion constraints, then a doc-review gate should harden it before implementation planning.
