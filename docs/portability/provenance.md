# Provenance

Verified: 2026-05-27

This file records where MVP plugin content came from and what changed for Codex.

| Plugin | Version | Source | Copied Assets | Codex Differences |
|---|---:|---|---|---|
| `blueprint-reviewer` | 0.1.0 | Claude plugin at `8f5baebb35bb865e3680a457ef02aba5cb418ac4`; cache path `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins/blueprint-reviewer/0.1.0` | `skills`, `rubrics`, `scripts`, README, changelog | Added `.codex-plugin/plugin.json`; rewrote script paths; omitted Claude command files. |
| `home-lab-ops` | 1.0.0 | Claude plugin at `8f5baebb35bb865e3680a457ef02aba5cb418ac4`; cache path `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins/home-lab-ops/1.0.0` | `skills`, references, README, changelog | Added Codex manifest; rewrote README agent section as Codex skill usage; omitted top-level agent file. |
| `python-toolkit` | 1.0.0 | Claude plugin at `8f5baebb35bb865e3680a457ef02aba5cb418ac4`; cache path `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins/python-toolkit/1.0.0` | `skills`, `references`, README, changelog | Added Codex manifest; rewrote install/support language; omitted top-level agent file. |
| `sdlc-manager` | 1.4.0 | Claude plugin at `8f5baebb35bb865e3680a457ef02aba5cb418ac4`; cache path `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins/sdlc-manager/1.4.0` | `skills`, `scripts`, `config`, script tests, README, changelog | Added Codex manifest; rewrote script locations; changed per-user defaults path from `~/.claude` to `~/.codex`; omitted command and top-level agent files. |
| `unifi` | 1.0.0 | Claude plugin at `8f5baebb35bb865e3680a457ef02aba5cb418ac4`; cache path `/Users/jefcox/.codex/plugins/cache/infiquetra-plugins/unifi/1.0.0` | `skills`, skill references, skill scripts, README, changelog | Added Codex manifest; rewrote README host name; omitted command and top-level agent files. |
| `test-suite` | 2.0.0 | Claude plugin at `8f5baebb35bb865e3680a457ef02aba5cb418ac4` | `skills/run-quality-checks`, runner script, README, changelog | Added Codex manifest; added runner `--dry-run`; made `--checks` select the requested checks; rewrote skill docs to match implemented flags. |

## Historical Proof-Port Recipe (Superseded)

This recipe is retained as origin evidence. It is superseded for active and future imports by the
mandatory [Claude-to-Codex plugin port runbook](claude-to-codex-plugin-port-runbook.md) and its
per-cycle closed JSON manifest. The runbook covers the orchestration, capability, state, trust,
installation, and rollback boundaries that this early recipe did not establish.

The `test-suite` proof port originally established this recipe for skill-plus-script plugins:

1. Copy only portable assets: `skills`, local references, local scripts, README, and changelog.
2. Do not copy host-specific command files, top-level agent files, or host manifests as active Codex surface.
3. Add a `.codex-plugin/plugin.json` with `skills: "./skills/"` and preserved lineage version.
4. Rewrite active instructions so script references resolve inside the packaged plugin boundary.
5. Add a smoke path that does not mutate external state. For `test-suite`, this is `--dry-run`.
6. Record unsupported or deferred host features in `PORTABILITY.md` and this provenance file.

This proof does not establish transform rules for MCP servers, apps, external credentials,
marketplace publishing, or native orchestration features.

## Saga-Family Replacement Baseline

Verified: 2026-06-06

The Saga-family replacement is frozen against
`infiquetra-claude-plugins` commit
`16de95c82ccb2ed80d7f11018e1c2e8247a80a7f`. The detailed source inventory is
recorded in `source-baseline-saga-family.md`; old-to-new capability ownership is
recorded in `saga-family-capability-map.md`; known old-use dispositions are
recorded in `saga-family-known-use-inventory.md`.

Saga itself was later refreshed to
`infiquetra-claude-plugins@abcc06b16763975d71e483a6dac768f4664d7b63` for the 0.20.0 document
formatting contract. The rest of the Saga-family source baseline remains at the 2026-06-06 snapshot.

Saga, team-execution, mission-control, unifi, and deploy are, as of 2026-07-06,
mid-port against a further commit-bounded window
`infiquetra-claude-plugins@b30e0f2ba7cd0cfdeaf97c1d4510c9a0468e96da..9470edca65b1db06d2f7562eeb2d5a9e48c34dec`
(saga 0.41.0 to 0.64.0 parity target). This window is frozen per KTD1 in
`docs/plans/2026-07-06-port-claude-plugin-updates-to-0.64-plan.md` even though
upstream `origin/main` has since moved to `43646b3e1b57979ce6e144c59bef2de9f88e09c8`.
The row values below still reflect the last-landed source versions; each row
updates in the unit that actually ports that plugin's 0.64-window behavior. See
`docs/portability/codex-saga-064-drift-classification.md` for the full
per-surface classification, and the new `fleet-core` plugin this window
introduces (source `infiquetra-claude-plugins` `fleet-core` 0.5.0, a
fleet-commons tier/retry substrate shared by saga, team-execution,
mission-control, and unifi).

| Plugin | Source Version | Source | Copied Assets Planned | Codex Differences Required |
|---|---:|---|---|---|
| `saga` | 0.20.0 | Claude plugin at `abcc06b16763975d71e483a6dac768f4664d7b63` | `skills`, references, scripts, README, changelog, document-formatting test | Add Codex manifest; keep source-parity skill names behind the `saga` namespace; rewrite `.claude/saga` to `.codex/saga`; add Codex-native outcome/promote surfaces; omit command files, agent files, hooks, source-only backends, and Claude manifests. |
| `deploy` | 0.1.1 | Claude plugin at `16de95c82ccb2ed80d7f11018e1c2e8247a80a7f` | deploy-state skill, scripts, README, changelog, command-origin behavior | Add Codex manifest; convert commands to skills; add dry-run, preview, exact-plan confirmation, auth-boundary, and proof-owned mutation safeguards; omit agent and command files. |
| `discord-identity-assets` | 0.2.0 | Codex-born plugin grounded in home-lab Discord asset scripts and Norns/Mimir runbook evidence | Skill, references, deterministic CLI, tests, README, and portability notes | Keep Codex-native image generation in the skill; move reusable bot/guild manifest, post-processing, Discord publish, API readback, redaction, and receipt behavior into tested scripts. |
| `mission-control` | 2.0.0 | Claude plugin at `16de95c82ccb2ed80d7f11018e1c2e8247a80a7f` | `skills`, references, config, scripts, tests, README, changelog | Add Codex manifest; rewrite prompt-alignment tests for Codex; preserve dry-run and preview modes; add allowlist and exact-plan confirmation gates; omit command and agent files. |
| `team-execution` | 2.2.0 | Claude plugin at `16de95c82ccb2ed80d7f11018e1c2e8247a80a7f` | `skills`, references, README, changelog, managed Codex agent TOML roster | Add Codex manifest; convert Claude agents into managed Codex TOML definitions plus registries; use Codex subagents only when available; provide tested serial fallback; omit command files and Claude markdown agents. |

The prior SDLC and document-review plugin roots are now lineage and migration
context only, not active plugin source. The active replacement inventory is
`saga`, `deploy`, `mission-control`, `team-execution`, `fleet-core`, `home-lab-ops`,
`python-toolkit`, `unifi`, `test-suite`, and `discord-identity-assets`.

## 2026-07-10 Contract-Gated Import

The current Saga/fleet/workflow modernization is governed by the canonical
[Claude-to-Codex plugin port runbook](claude-to-codex-plugin-port-runbook.md) and
`ports/2026-07-10-saga-07517.json`. It freezes Claude
`9470edca65b1db06d2f7562eeb2d5a9e48c34dec..38742ece89880a6b140be237edad6d3f13c97b54`
under four exact pathspecs, binds the approved Codex execution base, and classifies every source and
preservation row before later units may import behavior. `verified-workflows` is a target identity,
not an active package at this stage.

### Unpublished Verified Workflows Target

U9 materializes `verified-workflows` `1.0.0` as maintained Codex source with the skills
`verified-workflows:run` and `verified-workflows:appsec-audit`. Its behavior lineage is the frozen
upstream `team-execution` package; the path-by-path adaptations are the target paths on those source
rows in `ports/2026-07-10-saga-07517.json`. This is not an upstream byte-parity claim.

The active marketplace remains byte-stable on `team-execution` `2.3.0`. The target fixture marks
Verified Workflows unpublished, the shared fleet-core compatibility registry reads exact old aliases
and emits canonical new values, and U8 alone may replace the source, marketplace, cache, managed
profiles, hook trust, and state-writing identity.
