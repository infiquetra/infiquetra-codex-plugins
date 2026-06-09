# Decisions

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
