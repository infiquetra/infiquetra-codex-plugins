---
date: 2026-07-01
topic: discord-visual-identity-publisher
maturity: requirements-ready
source: docs/ideation/2026-06-30-discord-visual-identity-publisher-ideation.md#1-discord-visual-identity-publisher
---

# Requirements: Discord Visual Identity Publisher

## Summary

Build a reusable Codex plugin/skill for team-repo Discord bot visual identity publishing. V1 discovers or creates a team-local identity-asset manifest, uses operator-approved prompts with Codex image generation, runs deterministic post-processing and safety checks, publishes bot avatar, Developer Portal app icon, and bot profile banner to Discord, then writes local assets, a runbook/checklist, and API readback evidence.

The first live proof is Mimir: update Mimir's Discord bot avatar, app icon, and profile banner in live Discord, while keeping the product reusable for later team repos and other public Mimir identities.

## Problem Frame

Discord bot identity setup is a routine team-bootstrap activity, but the current knowledge is split across old `home-lab` scripts, runbooks, vault conventions, team repo identity docs, and live Discord behavior. During the Norns launch, the useful creative move was Codex-native image generation, but the surrounding process still required manual archaeology around runbooks, browser/auth state, token locations, app IDs, upload endpoints, and evidence.

The old `home-lab` workflow automated valuable pieces but made the wrong thing central: Replicate prompts, hard-coded app ID dictionaries, guild registries, and home-lab vault assumptions. The reusable center should move to a Codex plugin that a team repo can invoke with a repo-local contract and explicit live-mutation gates.

## Key Decisions

**V1 is a general publisher with Mimir as live proof.** The requirements target a reusable team-repo workflow, not a Mimir-only script. Mimir is the first acceptance pilot because it has clear identity material, visible asset gaps, and a live bot identity to update.

**The stable source of truth is a dedicated identity-asset manifest.** First-run discovery may read existing repo files and write the manifest, but later runs use that manifest as the explicit contract. This prevents future Codex sessions from rediscovering identity state from scattered docs.

**V1 publishes bot visual identity only.** Avatar, Developer Portal app icon, and bot profile banner are in scope. Server/guild icon and banner publishing are future module work because they use a different authority boundary.

**Guided Discord bot provisioning is out of v1.** V1 assumes the Discord application, app ID, bot user, and token already exist. Developer Portal creation, token reset/capture, app ID capture, and OAuth invite consent belong to a future guided-provisioning skill.

**Prompt plus publish-plan approval is the human approval gate.** Before image generation, Codex presents final prompts and the exact Discord publish plan. After approval, v1 may generate, post-process, quality-check, and publish without a second human approval on the final images.

**API readback is the completion receipt.** V1 completion requires local file hashes/dimensions plus Discord API readback showing non-empty avatar, app icon, and profile banner hashes after upload. Screenshots and manual visual approval are not required.

**Partial publish state is recorded, not auto-rolled back.** If a live publish fails after some surfaces changed, v1 stops and records exactly what changed, what failed, and what remains to do. Automatic rollback is out of scope for v1.

**Unmerged local state may publish.** The workflow may publish from an unmerged branch or working tree after prompt plus publish-plan approval. The receipt must record the exact local files and hashes that were published so the repo state can be reconciled afterward.

## Actors

A small number of actors are involved, and each has a different responsibility boundary.

- A1. **Codex agent** - reads the target team repo, drafts prompts and publish plan, invokes image generation, runs deterministic scripts, and records evidence.
- A2. **Operator** - approves the prompts plus publish plan before generation and live Discord mutation.
- A3. **Target team repo maintainer** - later reads the manifest, assets, runbook/checklist, and receipts to rerun or audit the workflow.
- A4. **Discord API** - accepts or rejects avatar, app icon, and profile banner mutations, and provides readback state for the receipt.
- A5. **Target bot identity** - owns the Discord avatar and profile banner; v1 must use the owning bot token for those surfaces.

## Requirements

**Plugin and skill boundary**

- R1. The plugin must expose a Codex-native skill for Discord bot visual identity publishing, not a copied home-lab script or Claude-style command surface.
- R2. The skill must clearly separate creative generation guidance from deterministic script work: Codex image generation is skill-guided, while resizing, validation, upload, verification, and receipt writing are script-backed.
- R3. The plugin must support first-run discovery for a target team repo and write a dedicated identity-asset manifest when one does not already exist.
- R4. Subsequent runs must treat the manifest as the stable contract and must not silently fall back to scattered repo inference when manifest data conflicts with discovered data.

**Manifest and repo-local contract**

- R5. The manifest must describe bot visual identity targets without storing secret values.
- R6. For each target, the manifest must identify the persona/profile, prompt source material, avatar/app icon/banner asset destinations, Discord application identity, bot identity, token variable name, and evidence destination at a product-contract level.
- R7. First-run discovery may use existing deploy, identity, SOUL, strategy, or team docs to propose manifest entries, but Codex must surface the proposed publish plan for operator approval before any generation or live mutation.
- R8. Manifest creation or update must leave real tokens, private keys, and vault plaintext out of the repo.

**Prompt approval and generation**

- R9. Before image generation, Codex must present the final avatar and banner prompts together with the exact publish plan for operator approval.
- R10. Operator approval of that combined prompt plus publish plan authorizes the rest of the v1 run unless an automated quality or safety gate fails.
- R11. The workflow must preserve generated originals separately from final upload assets.
- R12. The workflow must record final prompts and enough prompt-source context for a later run to understand why the images were generated that way.

**Post-processing and automated quality gate**

- R13. Deterministic post-processing must produce Discord-ready avatar/app icon and profile banner assets from the generated originals.
- R14. Before live publish, the workflow must block on technical invalidity: wrong dimensions, wrong file type, empty or unreadable image, unreasonable file size, missing required surface, or accidental reuse of the same final file where distinct avatar/banner assets are expected.
- R15. Before live publish, Codex must perform a prompt-consistency check and block if a generated image plainly contradicts the approved prompt.
- R16. The quality gate must be conservative enough to catch obvious mismatches, but it must not turn v1 into a subjective visual-design review loop.

**Credential handling and publish safety**

- R17. The workflow must resolve Discord tokens only at publish time from approved token-variable references.
- R18. The workflow must not print, persist, or diff token values, decrypted vault values, or API authorization headers.
- R19. The workflow must reject empty, malformed, or suspicious token material, including token values that include accidental trailing newlines.
- R20. The workflow must verify that the resolved token belongs to the expected bot identity before attempting avatar/banner publish.
- R21. The live publish operation must require the pre-approved publish plan and must not mutate any Discord target that was not shown in that plan.

**Discord publish and verification**

- R22. V1 must publish three bot visual surfaces: bot avatar, Developer Portal app icon, and bot profile banner.
- R23. V1 must use the owning bot identity for bot-owned surfaces and must not rely on an admin guild token for global bot avatar or profile banner changes.
- R24. After upload, v1 must perform Discord API readback and record non-empty avatar, app icon, and profile banner hashes or equivalent readback identifiers.
- R25. If any upload or verification step fails, v1 must stop, record partial state, and describe the manual or follow-up action needed. It must not claim success from local files alone.
- R26. V1 must not attempt automatic rollback after partial publish failure.

**Team repo writeback**

- R27. A successful or partially successful run must write back the identity-asset manifest, any generated originals, any final upload assets, prompt records, any API verification receipt, and a human-readable runbook/checklist.
- R28. The runbook/checklist must explain what was published, where the assets and receipt live, how to rerun or verify the workflow, and which steps remain outside v1.
- R29. V1 must not automatically update visible team docs such as generated rosters or public team pages.

**Mimir pilot**

- R30. The first acceptance pilot must update the live Mimir Discord bot's avatar, Developer Portal app icon, and profile banner.
- R31. The Mimir pilot must use Mimir's existing identity and deploy material only as inputs; it must not create a new Discord application or token.
- R32. The Mimir pilot must not generate or publish individual identities for the 31 headless Sons of Ivaldi.
- R33. The Mimir pilot should keep the manifest shape compatible with later public Mimir identities: `mimir`, `brokkr`, `eitri`, and `sons-of-ivaldi`.

## Key Flows

The flows describe user-visible behavior; planning will choose concrete scripts, file names, and command shapes.

- F1. **First-run manifest discovery.** **Trigger:** Codex is invoked in a team repo without a manifest. **Flow:** Codex scans approved repo-local identity sources, proposes target entries, and writes or updates the manifest as a draft input to the prompt plus publish plan. No generation or Discord mutation happens until the operator approves that combined plan, and the manifest records that it was created by discovery. **Covers R3, R5-R8.**
- F2. **Prompt plus publish-plan approval.** **Trigger:** A target is selected for visual identity publishing. **Flow:** Codex drafts final prompts and shows the exact Discord target plan, including persona, intended surfaces, token variable name, application/bot identity references, asset destinations, and evidence destination. The operator approves or edits before generation starts. **Covers R9-R10, R21.**
- F3. **Generate and post-process.** **Trigger:** The operator approves the prompt plus publish plan. **Flow:** Codex generates avatar and banner images through Codex-native image generation, preserves originals, derives final upload assets, and records prompt and local artifact metadata. **Covers R2, R11-R14, R27.**
- F4. **Automated quality gate.** **Trigger:** Final upload assets exist. **Flow:** The workflow checks technical validity and Codex checks obvious prompt consistency. Any blocking failure stops before live Discord mutation and records the failed preflight. **Covers R14-R16.**
- F5. **Publish and verify.** **Trigger:** Quality gates pass and publish mode is authorized by the approved plan. **Flow:** The workflow resolves the owning bot token safely, verifies ownership, uploads avatar/app icon/profile banner, performs API readback, and writes a receipt with local and remote evidence. **Covers R17-R26.**
- F6. **Partial failure closeout.** **Trigger:** One surface uploads or verifies successfully and a later surface fails. **Flow:** The workflow stops, records changed surfaces and failed surfaces, avoids rollback, and writes follow-up instructions. **Covers R25-R28.**
- F7. **Mimir pilot.** **Trigger:** The first v1 proof is run against Mimir. **Flow:** Codex creates or updates the Mimir identity-asset manifest for Mimir's visible bot identity, generates and publishes Mimir's avatar/app icon/profile banner, and records a receipt proving live Discord readback. **Covers R30-R33.**

## Acceptance Examples

These examples pin the edge cases most likely to cause silent overreach or false success.

- AE1. **Generate-only stops before Discord.** **Given:** the operator chooses generate-only mode for a target. **When:** prompts are approved and assets are generated. **Then:** originals, finals, prompts, and local checks are recorded, but no Discord PATCH is attempted and no live-success receipt is claimed. **Covers R10-R14, R24-R25.**
- AE2. **Publish cannot exceed the approved plan.** **Given:** the approved plan names only Mimir's avatar, app icon, and profile banner. **When:** the workflow runs publish mode. **Then:** it must not mutate server icon/banner, Brokkr, Eitri, Sons, or any newly discovered Discord target. **Covers R21-R23, R30.**
- AE3. **Prompt contradiction blocks publish.** **Given:** the approved prompt asks for Mimir's well-of-wisdom identity. **When:** the generated image plainly depicts an unrelated theme or unusable subject. **Then:** Codex must stop before live publish and record the prompt-consistency failure. **Covers R15-R16.**
- AE4. **Token newline blocks publish.** **Given:** token resolution returns material with an accidental trailing newline or otherwise suspicious shape. **When:** publish preflight runs. **Then:** no Discord mutation occurs, and the receipt records a secret-safe token preflight failure without printing the token. **Covers R17-R20.**
- AE5. **Partial Discord failure is honest.** **Given:** avatar upload succeeds but profile banner verification fails. **When:** the workflow closes out. **Then:** the receipt records the successful avatar change, the failed banner verification, and the required follow-up, while avoiding automatic rollback and avoiding a success claim. **Covers R24-R28.**
- AE6. **Mimir pilot respects headless identity.** **Given:** the target repo has many headless Sons. **When:** the Mimir pilot manifest is created. **Then:** v1 targets Mimir's live bot identity and does not create per-Son visual identity targets. **Covers R30-R33.**

## Success Criteria

The v1 is successful when it proves the reusable flow without hiding credential or evidence risk.

- SC1. A planner can implement v1 from this document without inventing product behavior, approval boundaries, or success criteria.
- SC2. The plugin can be described as a credentialed Codex skill-plus-script proof, with no active Claude command surface or home-lab registry dependency.
- SC3. A first Mimir run can produce a manifest, approved prompts plus publish plan, generated originals, final upload assets, runbook/checklist, and API readback receipt.
- SC4. The Mimir live proof verifies non-empty Discord avatar, app icon, and profile banner state after upload.
- SC5. A failed or partial publish leaves enough evidence for a later Codex session to know what changed and what remains, without exposing secrets.
- SC6. Server/guild assets, guided provisioning, VM/Hermes deploy, and team-doc updates remain visibly outside v1 rather than half-supported.

## Scope Boundaries

V1 is intentionally narrow around bot visual identity publishing.

**In scope for v1**

- Reusable Discord bot visual identity publishing plugin/skill.
- First-run discovery that creates a dedicated team-local manifest.
- Bot avatar, Developer Portal app icon, and bot profile banner.
- Codex-native image generation guided by approved prompts.
- Deterministic image post-processing and quality gates.
- Secret-safe token resolution and ownership preflight.
- Live Discord upload and API readback receipt.
- Manifest, assets, prompts, receipt, and runbook/checklist writeback.
- Mimir live bot identity update as the first proof.

**Deferred for later**

- Guided Developer Portal provisioning and OAuth invite flow.
- Discord server/guild icon and banner publishing.
- Visible team docs or generated roster updates.
- Support for additional public Mimir identities beyond the first Mimir pilot.
- Rollback from prior remote visual state.

**Outside this product's identity**

- VM creation, Hermes deployment, runtime service rollout, and vault provisioning.
- Generic team-bootstrap orchestration that owns souls, strategy, deployment, Discord home, and evidence in one monolith.
- Per-headless-worker Discord identities where a team explicitly says workers are headless.
- Reinstating Replicate-centered hard-coded prompt dictionaries as the reusable source of truth.

## Dependencies / Assumptions

These constraints shape planning but do not require new product decisions here.

- D1. Codex-native image generation remains an agent/skill-guided action; packaged shell scripts cannot invoke `image_gen` by themselves.
- D2. Target team repos can tolerate a small identity-asset manifest and receipt/runbook artifacts.
- D3. Mimir's existing Discord application ID, bot user identity, and bot token already exist for the first proof.
- D4. Discord API readback hashes or equivalent identifiers are available for avatar, app icon, and profile banner verification.
- D5. The implementation will include safe dry-run and mocked Discord tests before any live Mimir publish attempt.
- D6. The planner will choose concrete file names, script names, manifest shape, and package layout; this brainstorm pins behavior and boundaries, not code structure.

## Outstanding Questions

No product question blocks planning. The remaining questions are planning details.

**Deferred to planning**

- Which plugin name should be used: `discord-visual-identity`, `discord-identity-assets`, or a broader identity-assets name?
- What exact manifest file path and receipt path should the plugin standardize?
- Which existing image-processing dependency, if any, should be packaged or required for deterministic resizing and validation?
- How should mocked Discord API tests be structured so validation proves the credentialed boundary without live credentials?
- How should the Mimir pilot sequence be staged so local repo artifacts, live Discord mutation, and later commit/merge evidence stay traceable?

## Sources / Research

The requirements derive from the saved ideation artifact and the concrete repo evidence it gathered.

- `docs/ideation/2026-06-30-discord-visual-identity-publisher-ideation.md`
- `AGENTS.md`
- `README.md`
- `docs/engineering-journal/DECISIONS.md`
- `docs/engineering-journal/LEARNINGS.md`
- `docs/engineering-journal/QUEUED.md`
- `scripts/validate_codex_plugins.py`
- `docs/portability/matrix.md`
- `team-norns/docs/runbooks/well-of-urd-bootstrap.md`
- `team-norns/docs/engineering-journal/LEARNINGS.md`
- `team-mimir/assets/icons/README.md`
- `team-mimir/docs/team/README.md`
- `team-mimir/docs/team/roster.md`
- `team-mimir/deploy/team_profiles.yml`
- `home-lab/Discord-Bot-Creation-Instructions.md`
- `home-lab/scripts/setup_bot_assets.py`
- `home-lab/scripts/upload_ai_icons.py`
- `infiquetra-context-library/platform-specs/05-technical-specifications/attention-surface.md`
