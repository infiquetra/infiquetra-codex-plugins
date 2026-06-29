# Saga-Family Source Baseline

Verified: 2026-06-06

This file freezes the source snapshot for the Saga-family replacement before
porting or deleting any active Codex plugin. It is the U1 checkpoint for
`docs/plans/2026-06-06-001-feat-saga-family-replacement-plan.md`.

## Source Snapshot

| Field | Value |
|---|---|
| Source repo | `git@github.com:infiquetra/infiquetra-claude-plugins.git` |
| Source commit | `16de95c82ccb2ed80d7f11018e1c2e8247a80a7f` |
| Commit date | `2026-06-05 14:08:33 -0400` |
| Commit subject | `docs(journal): fill plugin-family-rename SHAs (PR #199, squash b6a03e0) + record multi-repo Phases 2-3 (#200)` |
| Source roots | `plugins/saga`, `plugins/deploy`, `plugins/mission-control`, `plugins/team-execution` |

The Codex port may copy and rewrite portable source material from this
snapshot. It must not treat Claude manifests, command files, or agent files as
active Codex runtime surfaces.

## Saga Refresh

Saga was refreshed after this frozen family baseline to source commit
`abcc06b16763975d71e483a6dac768f4664d7b63` for version `0.20.0`, limited to the shared document
formatting contract, doc-writing skill template updates, changelog, manifest version, and
markdown-only formatting test.

## Portability Rule

| Source material | Codex treatment |
|---|---|
| `.claude-plugin/plugin.json` | Lineage only. Recreate as `.codex-plugin/plugin.json`. |
| `skills/**/SKILL.md` | Portable after Codex prompt, path, state, and host-behavior rewrites. |
| `skills/**/references/` | Portable after stale path, link, and host-boundary rewrites. |
| `scripts/` | Portable only inside the owning plugin boundary, with dry-run, confirmation, auth, and state-path rewrites where applicable. |
| `config/` | Portable as package-local configuration when validation covers references. |
| `tests/` | Portable after rewriting Claude prompt-alignment assertions to Codex surfaces. |
| `commands/` | Command-origin source only. Convert behavior into skills, references, or scripts. Do not copy as active directories. |
| `agents/` | Claude markdown agents are lineage only. Convert into managed Codex TOML when explicitly in scope, or references/templates otherwise. Do not copy Claude agent files as active directories. |
| `docs/` under a plugin | Lineage only unless a document is rewritten as Codex-safe reference material. |

## Source Root Inventory

| Plugin | Source version | Portable roots | Host-only or lineage roots | Codex target |
|---|---:|---|---|---|
| `saga` | `0.20.0` | `skills/`, `references/`, `scripts/`, README, changelog, doc-formatting test | `.claude-plugin/`, `commands/` | Lifecycle spine with source-parity skill names, `.codex/saga/` state, handoff envelopes, and shared document formatting contract. |
| `deploy` | `0.1.1` | `skills/deploy-state/`, `scripts/`, README, changelog | `.claude-plugin/`, `commands/`, `agents/` | Deployment owner with dry-run, preview, and exact-plan confirmation gates. |
| `mission-control` | `2.0.0` | `skills/`, skill references, `config/`, `scripts/`, `tests/`, README, changelog | `.claude-plugin/`, `commands/`, `agents/` | SDLC successor for issue, board, label, milestone, metrics, rollout, and flow operations. |
| `team-execution` | `2.0.0` | `skills/`, skill references, README, changelog | `.claude-plugin/`, `commands/`, `agents/`, tmux-oriented `docs/` | Reviewer and validator protocol using Codex subagents when available and serial fallback otherwise. |

## Source Skill Inventory

| Plugin | Source skills |
|---|---|
| `saga` | `brainstorm`, `code-review`, `doc-review`, `founder-review`, `handoff`, `ideate`, `investigate`, `loop`, `office-hours`, `optimize`, `plan`, `qa`, `resume`, `retro`, `spec`, `strategy`, `work` |
| `deploy` | `deploy-state` |
| `mission-control` | `board`, `flow`, `issues`, `labels`, `metrics`, `milestones`, `rollout` |
| `team-execution` | `appsec-audit`, `team-execution` |

## Command-Origin And Agent-Origin Inventory

| Plugin | Source command files | Source agent files | Codex disposition |
|---|---:|---:|---|
| `saga` | 18 | 0 | Convert command behavior into the matching source-parity skills. |
| `deploy` | 4 | 1 | Convert commands into `deploy`, `deploy-status`, `deploy-notes`, and `deploy-hotfix` skills; convert release-orchestrator guidance into references if needed. |
| `mission-control` | 4 | 1 | Convert board, issue, metrics, and triage command behavior into mission-control skills; convert operator guidance into skill references if needed. |
| `team-execution` | 2 | 25 | Convert `team-execute` and `team-setup` into protocol guidance; convert reviewer and validator agents into registries or prompt snippets. |

## Script, Config, And Test Inventory

| Plugin | Scripts | Config | Tests | Notes |
|---|---|---|---|---|
| `saga` | `detect_deploy_strategy.py`, `discover_sessions.py`, `discover_subissues.py`, `extract_session_skeleton.py`, `find_inflight_work.py`, `handoff_envelope.py`, `issue_progress.py`, `journal_triggers.py`, `lifecycle_review.py`, `lifecycle_state.py`, `load_saga_context.py`, `parse_issue.py`, `qa_health_score.py`, `saga.py`, `scaffold_checkpoint.py` | none | none in source | Add new Codex characterization tests for state, handoff, backend, and links. |
| `deploy` | `mint_tag.py`, `preview_release_notes.py`, `query_deployments.py` | none | none in source | Add new tests for dry-run, preview, repo guards, confirmation, and auth provenance. |
| `mission-control` | `sdlc_manager.py`, `sync_template_docs.py` | `project-mappings.json`, `sdlc-schema.json` | 12 source tests | Port tests and rewrite prompt-alignment expectations from Claude to Codex. |
| `team-execution` | none in source | none | none in source | Add a Codex protocol probe and tests for delegated and serial modes. |

## Cutover Gates

The implementation must preserve these constraints:

- Target validation, source parity mapping, known-use mapping, and isolated
  proof gates must pass before active replacement is considered complete.
- Prior SDLC and document-review plugin content is lineage and migration
  evidence only; old skill aliases must not survive the final cutover as active
  compatibility shims.
- New active plugin roots must not contain top-level `.claude-plugin`,
  `commands`, or `agents` directories.
- Saga and team-execution state must use ignored `.codex/saga/` and
  `.codex/team-execution/` roots, not `.claude/...`.

## Saga 0.41 Parity Addendum

| Field | Value |
|---|---|
| Source repo | `git@github.com:infiquetra/infiquetra-claude-plugins.git` |
| Source commit | `b30e0f2ba7cd0cfdeaf97c1d4510c9a0468e96da` |
| Codex baseline | `fce697c24bd17a49f70897de53d614adc8478947` |
| Drift windows classified | `80e8731..aad9d6a`, `aad9d6a..origin/main` |
| Codex treatment | `saga:outcome`, `saga:promote`, outcome scripts, completeness gate, status card, override-rate reader, and selected tests ported with Codex backend gates. |

Source Workflow, fork, goal, hooks, command files, source manifests, and source agents remain lineage-only unless a future Codex capability proof and negative fallback tests activate them.
