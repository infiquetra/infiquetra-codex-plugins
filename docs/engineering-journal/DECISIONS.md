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
