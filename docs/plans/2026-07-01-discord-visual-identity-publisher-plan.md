---
title: Discord Visual Identity Publisher Implementation Plan
type: feat
status: active
date: 2026-07-01
origin: docs/brainstorms/2026-07-01-discord-visual-identity-publisher-requirements.md
deepened: 2026-07-01
---

# Discord Visual Identity Publisher Implementation Plan

## Summary

Build a new Codex plugin named `discord-identity-assets` that turns the Mimir/Norns Discord visual identity workflow into a reusable skill plus deterministic script package.

The plan keeps Codex-native `image_gen` as an agent-guided step, moves deterministic manifest validation, image normalization, Discord upload, and receipt writing into bundled Python scripts, then proves the workflow with a secret-safe Mimir dry run and an explicitly approved live publish.

## Problem Frame

The current reusable center is in the wrong place. `home-lab/scripts/upload_ai_icons.py` has useful endpoint knowledge, but it also carries hard-coded bot lists, application IDs, and home-lab vault paths (`home-lab/scripts/upload_ai_icons.py:32`, `home-lab/scripts/upload_ai_icons.py:50`, `home-lab/scripts/upload_ai_icons.py:101`).

Norns proved the better creative path: Codex `image_gen` generated the active sister avatars and banners, and Discord API readback proved non-empty avatar, icon, and banner hashes (`team-norns/docs/engineering-journal/LEARNINGS.md:37`, `team-norns/docs/engineering-journal/LEARNINGS.md:41`). Mimir is the first reusable proof because its repo records the public council identities, token variable names, bot user IDs, and the deliberate headless Sons boundary (`team-mimir/deploy/team_profiles.yml:5`, `team-mimir/deploy/team_profiles.yml:108`, `team-mimir/assets/icons/README.md:23`).

## Requirements

The implementation must satisfy these plan-level requirements.

**Plugin surface and inventory**

- R1. Add a Codex-native plugin `discord-identity-assets` with one active skill, `discord-identity-assets`.
- R2. Keep the active surface to `.codex-plugin/plugin.json`, `skills/`, `scripts/`, `tests`, docs, and references; do not add Claude commands, Claude manifests, or generic agent personas.
- R3. Update the repo inventory surfaces that validation enforces: `.agents/plugins/marketplace.json`, `scripts/validate_codex_plugins.py`, `docs/portability/matrix.md`, `docs/validation/saga-family-target-inventory.json`, `README.md`, and related tests.
- R4. Preserve the existing source policy: edit repo source, not installed cache copies.

**Manifest and generation boundary**

- R5. Define a committed target-repo manifest at `identity/discord-identity-assets.yml` that contains identity targets, file destinations, source references, Discord IDs, and token variable names, but never secret values.
- R6. Implement first-run discovery that can propose manifest entries from `deploy/team_profiles.yml`, identity docs, persona SOULs, strategy/team docs, and existing `assets/discord/` paths, while marking missing required fields explicitly.
- R7. Treat the manifest as the stable contract after it exists; discovered data that conflicts with the manifest must fail validation or require an explicit manifest edit.
- R8. Keep image generation skill-guided: scripts may validate prompts and files, but no script may attempt to invoke Codex `image_gen`.

**Assets, quality, and evidence**

- R9. Preserve generated originals separately from upload-ready assets under target-repo `assets/discord/` conventions.
- R10. Use deterministic post-processing to produce Discord-ready avatar/app-icon and profile-banner files, with dimension, file-type, size, readability, and duplicate-file checks.
- R11. Record final prompts, prompt source references, local file hashes, dimensions, publish plan, Discord readback identifiers, and partial failure state in a human-readable receipt.
- R12. Generate or update a target-repo runbook/checklist that names what changed, where artifacts live, how to rerun, how to verify, and what remains out of scope.

**Credentialed Discord boundary**

- R13. Resolve Discord bot tokens only from approved environment variable names at publish time; do not read or decrypt vault files in the plugin scripts.
- R14. Reject absent, empty, multiline, trailing-newline, or suspicious token material before any HTTP mutation.
- R15. Verify the resolved token belongs to the expected bot user and application before publishing.
- R16. Publish only the pre-approved surfaces: bot avatar, application icon, and bot profile banner.
- R17. Write API readback evidence that distinguishes local files from proved remote Discord state.
- R18. Stop and record partial state on the first upload or verification failure; do not attempt automatic rollback.

**Mimir pilot**

- R19. Prove v1 with Mimir's visible bot identity only: avatar, app icon, and bot profile banner.
- R20. Do not create new Discord applications, reset tokens, invite bots, update server/guild art, or generate individual visual identities for the 31 headless Sons.
- R21. Keep Mimir pilot artifacts target-repo-local and mergeable after live publish: manifest, assets, prompts, receipt, and runbook/checklist.

## Key Technical Decisions

The plan pins the implementation choices that should not be rediscovered during `/work`.

| ID | Decision | Rationale |
|---|---|---|
| KTD1 | Name the plugin and skill `discord-identity-assets`. | It is narrower than a generic team identity product, but broad enough to later add guided provisioning and guild/server asset skills under the same plugin without renaming v1. |
| KTD2 | Use `identity/discord-identity-assets.yml` as the target-repo manifest path. | Team repos already carry identity and deploy material; placing the manifest under `identity/` makes it a committed repo contract instead of deployment state or local Codex state. |
| KTD3 | Use PyYAML for YAML manifest and team-profile parsing, and Pillow for deterministic image resize/validation. | YAML is the team-repo convention and `deploy/team_profiles.yml` is YAML; Pillow is the least-surprising Python image dependency for resize/crop/dimension checks. Scripts must fail early with actionable messages when either dependency is unavailable. |
| KTD4 | Use Python standard-library HTTP for the Discord client, with an injectable transport for tests. | Avoids adding `requests` as a second network dependency and makes no-network mocked API tests straightforward. |
| KTD5 | Resolve tokens from environment variables only. | The plugin should integrate with vault conventions by name, but not own vault decryption or home-lab paths. Codex or the operator can materialize the env var from the relevant vault just in time. |
| KTD6 | Prefer `/applications/@me` for application readback and icon publish after verifying it returns the expected application ID; keep `/applications/{id}` only as a compatibility fallback behind tests. | Official Discord docs describe current-application read/edit semantics for the requesting bot user, which reduces the chance of mutating a target outside the approved plan. The legacy script used `/applications/{app_id}`, so the implementation must preserve a tested fallback if the live bot-token behavior requires it. |
| KTD7 | The confirmation object is a signed publish plan, not a human approval of generated pixels. | Requirements make prompt plus publish-plan approval the human gate; after that, automated technical and prompt-consistency gates decide whether publishing may continue. |
| KTD8 | Mimir proof is staged as dry run, operator approval, live publish, and repo reconciliation. | This separates script correctness from live mutation risk and records exactly which local files and remote hashes were used even when publishing from an unmerged branch. |
| KTD9 | Use `team-execution` for implementation and validation. | The backend recommendation helper returns `team-execution` for this scope because the work is multi-phase, credential-sensitive, cross-repo, external-API, and live-mutation capable. |

## High-Level Technical Design

The plugin is a Codex skill wrapper around a small deterministic Python package.

```text
Codex skill
  reads target repo and manifest
  drafts prompts plus publish plan
  invokes image_gen after approval
  calls packaged scripts for deterministic work

Packaged scripts
  discover/validate manifest
  normalize generated images
  check files and prompt consistency inputs
  publish to Discord with injected token env vars
  write receipts and runbook/checklist

Target team repo
  identity/discord-identity-assets.yml
  assets/discord/originals/
  assets/discord/avatars/
  assets/discord/banners/
  assets/discord/prompts/
  docs/runbooks/discord-identity-assets/
```

The implementation should keep the script surface compact. A single CLI entrypoint, `plugins/discord-identity-assets/scripts/discord_identity_assets.py`, can expose subcommands for `discover`, `validate`, `postprocess`, `plan-publish`, `publish`, and `verify-receipt`. If the file grows beyond maintainable size, split helper modules under `plugins/discord-identity-assets/scripts/discord_identity_assets/` while keeping the documented CLI stable.

## Implementation Units

The units are dependency-ordered and independently reviewable. U7 is the only unit that mutates a sibling team repo or live Discord, and it stays gated behind U1-U6.

### U1. Plugin Surface And Inventory

Create the Codex plugin shell and wire it into repository inventory.

**Goal:**

Add `plugins/discord-identity-assets` as an active proof-port plugin with one skill and no legacy host surfaces.

**Requirements:**

R1-R4, KTD1, KTD9.

**Dependencies:**

None.

**Files:**

- `plugins/discord-identity-assets/.codex-plugin/plugin.json`
- `plugins/discord-identity-assets/README.md`
- `plugins/discord-identity-assets/PORTABILITY.md`
- `plugins/discord-identity-assets/skills/discord-identity-assets/SKILL.md`
- `.agents/plugins/marketplace.json`
- `scripts/validate_codex_plugins.py`
- `docs/portability/matrix.md`
- `docs/validation/saga-family-target-inventory.json`
- `README.md`
- `tests/test_validate_codex_plugins.py`

**Approach:**

Follow the active plugin layout in `README.md:26` and the manifest checks in `scripts/validate_codex_plugins.py:360`. Add `discord-identity-assets` to the expected plugin dictionaries, marketplace inventory, portability matrix, target fixture, and validation tests.

The skill should state the hard boundary that Codex invokes `image_gen`, while scripts do only deterministic file, API, and receipt work.

**Patterns to follow:**

- `plugins/test-suite/.codex-plugin/plugin.json`
- `plugins/test-suite/PORTABILITY.md`
- `plugins/test-suite/skills/run-quality-checks/SKILL.md`
- `scripts/validate_codex_plugins.py:274`

**Test scenarios:**

- Happy path: repository validation sees 9 active plugins, including `discord-identity-assets`, and the new skill inventory exactly matches the validator.
- Error path: a plugin manifest with a missing `interface.defaultPrompt` or wrong skill path still fails validation.
- Regression path: stale `.claude-plugin`, `commands`, or unexpected `agents` directories under the new plugin are rejected.

**Verification:**

`python3 scripts/validate_codex_plugins.py`, `uv run python -m pytest -q tests/test_validate_codex_plugins.py`, and the plugin inventory count in the README agree.

### U2. Manifest Schema, Discovery, And Validation

Make the target-repo manifest the stable contract instead of rediscovering identity state every run.

**Goal:**

Implement manifest discovery and validation for target repos, including Mimir's first-run manifest proposal.

**Requirements:**

R5-R8, R19-R21, KTD2, KTD3.

**Dependencies:**

U1.

**Files:**

- `plugins/discord-identity-assets/references/manifest-schema.md`
- `plugins/discord-identity-assets/scripts/discord_identity_assets.py`
- `plugins/discord-identity-assets/tests/test_manifest_contract.py`
- `pyproject.toml`
- Target repo output during pilot: `team-mimir:identity/discord-identity-assets.yml`

**Approach:**

Define a YAML manifest with `schema_version`, `targets[]`, `prompt_sources[]`, `asset_paths`, `discord`, `token_env`, `evidence`, and `mode_defaults`. Require `discord.application_id`, `discord.expected_bot_user_id`, `token_env`, and explicit output paths before publish mode can run.

Discovery should read `deploy/team_profiles.yml` for `persona`, `discord_token_var`, and `bot_user_id` where present. Mimir currently exposes `discord_token_var` and `bot_user_id` for `mimir-engineer`, `brokkr`, `eitri`, and `sons-of-ivaldi` (`team-mimir/deploy/team_profiles.yml:5`, `team-mimir/deploy/team_profiles.yml:42`, `team-mimir/deploy/team_profiles.yml:78`, `team-mimir/deploy/team_profiles.yml:108`). If an application ID is not explicitly present, discovery may propose the bot user ID as an application ID candidate, but validation must require live API confirmation before publish.

**Patterns to follow:**

- `team-mimir/deploy/team_profiles.yml:12`
- `team-mimir/assets/icons/README.md:14`
- `team-mimir/docs/team/roster.md:95`

**Test scenarios:**

- Happy path: a target repo with a valid manifest returns one publishable target and stable artifact paths.
- Discovery path: Mimir-like `deploy/team_profiles.yml` produces a draft Mimir target with token variable and expected bot user ID, plus explicit missing-field diagnostics for any unverified application ID.
- Conflict path: an existing manifest disagrees with discovered `bot_user_id`; validation fails and does not silently overwrite.
- Secret path: token-looking values in manifest fields fail validation, while token variable names pass.
- Missing dependency path: if PyYAML is unavailable, the CLI exits before mutation with an actionable dependency message.

**Verification:**

Unit tests cover manifest parsing, discovery, conflict detection, secret rejection, and schema documentation examples.

### U3. Asset Post-Processing And Local Evidence

Turn Codex-generated originals into Discord-ready files without mixing generation into scripts.

**Goal:**

Implement deterministic image normalization, technical quality checks, prompt recording, and local receipt payloads.

**Requirements:**

R8-R12, KTD3, KTD7.

**Dependencies:**

U1, U2.

**Files:**

- `plugins/discord-identity-assets/scripts/discord_identity_assets.py`
- `plugins/discord-identity-assets/references/asset-pipeline.md`
- `plugins/discord-identity-assets/tests/test_asset_pipeline.py`
- `plugins/discord-identity-assets/tests/fixtures/images/`
- Target repo outputs during pilot:
  - `team-mimir:assets/discord/originals/`
  - `team-mimir:assets/discord/avatars/`
  - `team-mimir:assets/discord/banners/`
  - `team-mimir:assets/discord/prompts/`

**Approach:**

Use Pillow to read generated originals, normalize avatar/app-icon outputs to square PNG files, normalize profile banners to the chosen Discord-ready landscape size, and compute SHA-256 hashes plus dimensions. Preserve generated originals unchanged and write prompt records as Markdown or YAML sidecars that include approved prompts, prompt-source refs, generation timestamp, and target ID.

The prompt-consistency gate stays Codex-owned: the skill asks Codex to inspect the generated image against the approved prompt before scripts publish. Scripts should store the prompt-consistency verdict in the receipt input and block if it is missing or failed.

**Patterns to follow:**

- `team-norns/docs/runbooks/well-of-urd-bootstrap.md:9`
- `team-norns/docs/runbooks/well-of-urd-bootstrap.md:18`
- `home-lab/scripts/setup_bot_assets.py:245`

**Test scenarios:**

- Happy path: valid generated avatar and banner files produce expected final paths, dimensions, hashes, and prompt sidecars.
- Edge path: a huge but valid image is resized without replacing the original.
- Error path: missing original, unreadable file, wrong file type, zero-byte file, or file above configured size fails before publish.
- Duplicate path: avatar/app icon may intentionally share derived bytes, but avatar/banner may not point at the same final file.
- Prompt gate path: publish input without a passed prompt-consistency verdict fails.

**Verification:**

Asset tests run offline with fixtures and prove originals are preserved, finals are deterministic, and invalid files fail before live mutation.

### U4. Secret-Safe Discord Client And Verification

Implement the credentialed API boundary with mocked tests before any live publish.

**Goal:**

Publish avatar, app icon, and profile banner only when the token, target identity, approved plan, and local assets all match.

**Requirements:**

R13-R18, KTD4-KTD8.

**Dependencies:**

U1-U3.

**Files:**

- `plugins/discord-identity-assets/scripts/discord_identity_assets.py`
- `plugins/discord-identity-assets/references/discord-api-boundary.md`
- `plugins/discord-identity-assets/tests/test_discord_client.py`
- `plugins/discord-identity-assets/tests/test_secret_safety.py`

**Approach:**

Build an injectable HTTP transport around `urllib.request`. The live path must support dry-run preview, ownership preflight, publish, readback, and receipt writing without logging tokens or authorization headers.

The client should call `GET /users/@me` and verify the returned user ID matches `expected_bot_user_id`. It should call the current-application endpoint and verify the returned application ID matches `discord.application_id` before icon publish. For mutation, use official current-user avatar/banner parameters and current-application icon editing when available; preserve a tested `/applications/{application_id}` compatibility path because the legacy home-lab script used it successfully.

**Patterns to follow:**

- `home-lab/scripts/upload_ai_icons.py:156`
- `home-lab/scripts/upload_ai_icons.py:185`
- `home-lab/scripts/upload_ai_icons.py:209`
- Discord User Resource: https://docs.discord.com/developers/resources/user
- Discord Application Resource: https://docs.discord.com/developers/resources/application

**Test scenarios:**

- Happy path: mocked Discord returns matching bot/application IDs, all three PATCH calls succeed, and the receipt records non-empty avatar, icon, and banner identifiers.
- Token path: missing, empty, whitespace-only, trailing-newline, multiline, or non-token-shaped env var fails before HTTP.
- Wrong identity path: token resolves to the wrong bot user or application; no PATCH occurs.
- Plan drift path: approved plan names one target but CLI arguments or manifest resolve another; no PATCH occurs.
- Partial failure path: avatar succeeds and banner verification fails; receipt records changed and failed surfaces and does not claim success.
- Secret log path: captured stdout/stderr and receipt text do not contain token values or authorization headers.

**Verification:**

All Discord client tests run without network access. The live path requires an explicit `--publish` plus matching confirmation ID.

### U5. Skill Workflow, Runbook, And Receipts

Make the operator workflow reusable from a cold team repo.

**Goal:**

Write the skill instructions and receipt/runbook templates so a future Codex session can perform generate-only, dry-run, and publish modes without rediscovering the process.

**Requirements:**

R1-R18, R21, KTD7, KTD8.

**Dependencies:**

U1-U4.

**Files:**

- `plugins/discord-identity-assets/skills/discord-identity-assets/SKILL.md`
- `plugins/discord-identity-assets/references/runbook-template.md`
- `plugins/discord-identity-assets/references/receipt-schema.md`
- `plugins/discord-identity-assets/tests/test_receipt_writer.py`
- Target repo output during pilot: `team-mimir:docs/runbooks/discord-identity-assets/`

**Approach:**

The skill should guide Codex through these phases: target repo discovery, manifest validation or draft creation, final prompt plus publish-plan presentation, `image_gen` invocation after approval, deterministic post-processing, prompt-consistency gate, dry-run or publish, API readback, and target-repo writeback.

The receipt writer should produce a human-readable Markdown receipt plus a structured JSON sidecar if useful for later automation. The receipt must identify mode, local git state, target repo, manifest hash, prompt hashes, final asset hashes, Discord endpoints, remote readback identifiers, partial failure state, and follow-up steps.

**Patterns to follow:**

- `plugins/deploy/skills/deploy/SKILL.md`
- `plugins/unifi/skills/unifi-network/SKILL.md`
- `team-norns/docs/runbooks/well-of-urd-bootstrap.md:83`

**Test scenarios:**

- Generate-only path: no Discord mutation is attempted and the receipt avoids live-success language.
- Dry-run path: publish plan and confirmation ID are emitted, but no PATCH calls are made.
- Publish path: receipt includes local and remote proof and masks all secret material.
- Resume path: a later run can read the receipt and know whether it was generate-only, dry-run, successful publish, or partial failure.

**Verification:**

Receipt tests verify required fields, redaction, mode-specific wording, and stable paths.

### U6. Validation, Docs, And Quality Gates

Prove the plugin boundary before the Mimir pilot.

**Goal:**

Add tests and documentation that keep the new plugin from becoming another unvalidated credentialed API client.

**Requirements:**

R1-R18, KTD1-KTD9.

**Dependencies:**

U1-U5.

**Files:**

- `plugins/discord-identity-assets/tests/`
- `tests/test_validate_codex_plugins.py`
- `tests/test_saga_doc_formatting.py`
- `pyproject.toml`
- `docs/engineering-journal/DECISIONS.md`
- `docs/engineering-journal/LEARNINGS.md`
- `docs/portability/matrix.md`

**Approach:**

Broaden validation only where the plugin boundary requires it: inventory tests, manifest tests, image tests, no-network Discord client tests, no-secret logging tests, and receipt tests. Keep live Discord out of automated tests.

Add `PyYAML` and `Pillow` to local development dependencies so tests run consistently, but keep script startup checks explicit so plugin users get clear messages if dependencies are missing.

**Patterns to follow:**

- `tests/test_validate_codex_plugins.py:13`
- `plugins/deploy/tests/test_mint_tag.py`
- `plugins/team-execution/tests/test_protocol_probe.py`

**Test scenarios:**

- Full repo validation passes with the new plugin in current and cutover modes.
- Mock Discord tests prove success, wrong identity, rate-limit/error, and partial failure behavior.
- Secret-safety tests prove token values do not appear in stdout, stderr, receipts, or assertion messages.
- Skill-doc formatting tests still pass with the new skill docs.

**Verification:**

Run `python3 scripts/validate_codex_plugins.py`, `python3 plugins/test-suite/skills/run-quality-checks/scripts/test_runner.py --dry-run --checks pytest,ruff`, and `uv run python -m pytest -q`.

### U7. Mimir Dry Run And Live Proof

Use the new plugin to update Mimir's live Discord visual identity with receipts.

**Goal:**

Run the first proof against Mimir's bot avatar, app icon, and profile banner while preserving target-repo artifacts and avoiding headless Son fanout.

**Requirements:**

R19-R21, KTD8.

**Dependencies:**

U1-U6.

**Files:**

- Target repo input: `team-mimir:deploy/team_profiles.yml`
- Target repo input: `team-mimir:profiles/mimir-engineer/SOUL.md`
- Target repo input: `team-mimir:docs/team/README.md`
- Target repo output: `team-mimir:identity/discord-identity-assets.yml`
- Target repo output: `team-mimir:assets/discord/originals/`
- Target repo output: `team-mimir:assets/discord/avatars/mimir.png`
- Target repo output: `team-mimir:assets/discord/banners/mimir.png`
- Target repo output: `team-mimir:assets/discord/prompts/mimir.yml`
- Target repo output: `team-mimir:docs/runbooks/discord-identity-assets/`

**Approach:**

First run generate-only or dry-run mode against Mimir, then present the final prompt plus publish plan for explicit approval. After approval, publish only Mimir's avatar, app icon, and profile banner.

The pilot should record the exact local files and hashes used for live Discord mutation, the token variable name used, the verified bot user ID, the verified application ID, and non-empty remote readback identifiers. It must not update generated roster docs, server/guild art, Brokkr, Eitri, the Sons collective, or any individual headless Son.

**Patterns to follow:**

- `team-mimir/docs/team/README.md:32`
- `team-mimir/docs/team/roster.md:7`
- `team-mimir/assets/icons/README.md:23`
- `team-norns/docs/engineering-journal/LEARNINGS.md:39`

**Test scenarios:**

- Dry-run path: Mimir manifest and assets validate, publish plan prints the exact target, but no Discord PATCH occurs.
- Approval path: live publish refuses to run unless the confirmation ID matches the printed plan.
- Live success path: receipt records non-empty avatar, app icon, and banner readback identifiers.
- Partial failure path: if one surface fails after another succeeds, the receipt records partial state and no rollback attempt.
- Scope path: Brokkr, Eitri, Sons collective, and all 31 headless Sons are excluded from the Mimir v1 target list.

**Verification:**

Mimir proof is complete only when the target repo has committed local artifacts and the receipt shows live Discord API readback for all three surfaces.

## Team Structure

Team Execution is recommended and selected for this plan because the work touches credentials, external APIs, target-repo artifacts, and a live Discord mutation gate.

| Role | Focus | Required evidence |
|---|---|---|
| Builder A | Plugin surface, inventory, manifest schema | Validation passes and plugin inventory docs are updated. |
| Builder B | Asset pipeline and receipt writer | Offline image and receipt tests pass with fixture assets. |
| Builder C | Discord client and secret safety | No-network mocked API tests pass; no token material appears in logs or receipts. |
| Reviewer | Architecture, security, and scope | Confirms Codex image generation boundary, token env boundary, and Mimir headless-Sons exclusion. |
| Validator | Test and pilot readiness | Confirms full repo checks, dry-run receipt, and explicit live-publish approval gate before U7. |

The orchestration receipt for Saga is this section: `docs/plans/2026-07-01-discord-visual-identity-publisher-plan.md#team-structure`.

## Outcome Coordination

Use the outcome coordinator explicitly; ordinary Saga ticks do not complete outcome nodes by themselves.

The active outcome is `discord-visual-identity-publisher`. Outcome state is derived from `docs/outcomes/discord-visual-identity-publisher/outcome-spec.json`, the git-common-dir outcome store, and GitHub or outcome completion evidence. A local `.codex/saga/` tick is useful session history, but it is not enough to move an outcome node from ready or dispatched to done.

Before implementation starts, reconcile the outcome deliberately. The `plan` node must have a canonical completion marker or closed tracking issue before dependent implementation nodes can unlock. Then run `python3 plugins/saga/scripts/outcome.py status discord-visual-identity-publisher`, `python3 plugins/saga/scripts/outcome.py approve discord-visual-identity-publisher`, and `python3 plugins/saga/scripts/outcome.py advance discord-visual-identity-publisher`; use `python3 plugins/saga/scripts/outcome.py attend discord-visual-identity-publisher <subplot-id>` for any dispatched leaf handoff.

## Risks And Mitigations

This plan treats Discord publishing as a credentialed external mutation, not as ordinary file generation.

| Risk | Mitigation |
|---|---|
| Discord API behavior has drifted since the home-lab scripts. | Implement official-doc current-user/current-application paths first, preserve mocked compatibility tests for the legacy application-id path, and require live readback before success. |
| Bot token leakage through logs or receipts. | Token resolver rejects suspicious values and tests capture stdout/stderr plus receipt text for redaction. |
| Mimir app ID is inferred incorrectly from bot user ID. | Discovery may propose it, but publish must verify current application readback matches the manifest before PATCH. |
| Image generation produces beautiful but wrong assets. | Prompt-consistency gate blocks obvious contradictions before publish; no subjective design loop is introduced. |
| Partial live publish leaves Discord inconsistent. | Receipt records changed and failed surfaces, stops immediately, and avoids automatic rollback in v1. |
| The plugin becomes a generic team bootstrap monolith. | Server/guild assets, bot provisioning, VM/Hermes deploy, roster generation, and broad team-bootstrap orchestration remain out of v1. |

## Scope Boundaries

The plan keeps v1 small enough to prove the reusable credentialed workflow.

**In scope**

- New `discord-identity-assets` Codex plugin and skill.
- Target-repo manifest discovery and validation.
- Codex-guided image generation prompts and prompt records.
- Deterministic image post-processing and technical checks.
- Secret-safe Discord publish and API readback for bot avatar, app icon, and bot profile banner.
- Mimir live proof after dry-run and explicit approval.

**Deferred to follow-up work**

- Guided Discord Developer Portal provisioning.
- Discord server/guild icon and banner module.
- Brokkr, Eitri, Sons collective, or broader Mimir public identity assets.
- Installation proof flow that replaces currently installed cache copies.

**Non-goals**

- Home-lab vault ownership or deployment orchestration.
- Replicate-first generation or hard-coded prompt dictionaries.
- VM creation, Hermes deployment, bot invite/guild provisioning, or visible roster/team-doc regeneration.
- Individual identities for the 31 headless Sons.

## Success Metrics

The implementation succeeds when it proves both reuse and safe live mutation.

| Metric | Target |
|---|---|
| Plugin validation | `scripts/validate_codex_plugins.py` passes with 9 expected plugins. |
| Test coverage by behavior | Manifest, asset pipeline, Discord client, secret safety, and receipt tests cover happy, failure, and partial-state paths. |
| Mimir dry run | Produces manifest, prompts, assets, publish plan, and dry-run receipt without Discord mutation. |
| Mimir live proof | Receipt records non-empty remote avatar, app icon, and banner identifiers after upload. |
| Secret safety | No token value or authorization header appears in logs, diffs, or receipts. |

## Sources / Research

These sources ground the plan and should be refreshed by `/work` before live publish.

- `docs/brainstorms/2026-07-01-discord-visual-identity-publisher-requirements.md`
- `docs/reviews/2026-07-01-discord-visual-identity-publisher-requirements-doc-review.md`
- `README.md:26`
- `scripts/validate_codex_plugins.py:56`
- `scripts/validate_codex_plugins.py:274`
- `docs/engineering-journal/QUEUED.md:3`
- `docs/engineering-journal/DECISIONS.md:39`
- `docs/outcomes/discord-visual-identity-publisher/outcome-spec.json`
- `plugins/saga/scripts/outcome.py`
- `plugins/saga/scripts/outcome_orchestrator.py`
- `plugins/saga/references/outcome-spec.md`
- `home-lab/scripts/upload_ai_icons.py:32`
- `home-lab/scripts/upload_ai_icons.py:156`
- `home-lab/scripts/upload_ai_icons.py:185`
- `home-lab/scripts/upload_ai_icons.py:209`
- `team-norns/docs/engineering-journal/LEARNINGS.md:33`
- `team-norns/docs/engineering-journal/LEARNINGS.md:85`
- `team-mimir/deploy/team_profiles.yml:5`
- `team-mimir/assets/icons/README.md:14`
- `team-mimir/docs/team/README.md:32`
- `team-mimir/docs/team/roster.md:95`
- Discord User Resource: https://docs.discord.com/developers/resources/user
- Discord Application Resource: https://docs.discord.com/developers/resources/application
