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
