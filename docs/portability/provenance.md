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

## Proof-Port Recipe

The `test-suite` proof port establishes this recipe for future skill-plus-script plugins:

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

| Plugin | Source Version | Source | Copied Assets Planned | Codex Differences Required |
|---|---:|---|---|---|
| `saga` | 0.20.0 | Claude plugin at `abcc06b16763975d71e483a6dac768f4664d7b63` | `skills`, references, scripts, README, changelog, document-formatting test | Add Codex manifest; keep source-parity skill names behind the `saga` namespace; rewrite `.claude/saga` to `.codex/saga`; add Codex-native outcome/promote surfaces; omit command files, agent files, hooks, source-only backends, and Claude manifests. |
| `deploy` | 0.1.1 | Claude plugin at `16de95c82ccb2ed80d7f11018e1c2e8247a80a7f` | deploy-state skill, scripts, README, changelog, command-origin behavior | Add Codex manifest; convert commands to skills; add dry-run, preview, exact-plan confirmation, auth-boundary, and proof-owned mutation safeguards; omit agent and command files. |
| `discord-identity-assets` | 0.2.0 | Codex-born plugin grounded in home-lab Discord asset scripts and Norns/Mimir runbook evidence | Skill, references, deterministic CLI, tests, README, and portability notes | Keep Codex-native image generation in the skill; move reusable bot/guild manifest, post-processing, Discord publish, API readback, redaction, and receipt behavior into tested scripts. |
| `mission-control` | 2.0.0 | Claude plugin at `16de95c82ccb2ed80d7f11018e1c2e8247a80a7f` | `skills`, references, config, scripts, tests, README, changelog | Add Codex manifest; rewrite prompt-alignment tests for Codex; preserve dry-run and preview modes; add allowlist and exact-plan confirmation gates; omit command and agent files. |
| `team-execution` | 2.2.0 | Claude plugin at `16de95c82ccb2ed80d7f11018e1c2e8247a80a7f` | `skills`, references, README, changelog, managed Codex agent TOML roster | Add Codex manifest; convert Claude agents into managed Codex TOML definitions plus registries; use Codex subagents only when available; provide tested serial fallback; omit command files and Claude markdown agents. |

The prior SDLC and document-review plugin roots are now lineage and migration
context only, not active plugin source. The active replacement inventory is
`saga`, `deploy`, `mission-control`, `team-execution`, `home-lab-ops`,
`python-toolkit`, `unifi`, `test-suite`, and `discord-identity-assets`.
