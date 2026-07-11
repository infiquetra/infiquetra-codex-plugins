# Work Session: U9 Verified Workflows Identity

Date: 2026-07-10. Branch: `work/verified-workflows-modernization`. Plan:
`docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`. Saga:
`task-port-recent-claude-plugin-updates`. Effective orchestration: `inline`.

## Outcome

U9 is complete. The repository now contains the unpublished `verified-workflows` `1.0.0`
target with `run` and `appsec-audit` skills, while the active marketplace and installed-state
cutover remain reserved for U8.

- Added a closed fleet-core compatibility registry covering plugin and skill identities, Saga
  modes, document anchors, state and config locations, receipt vehicles, evidence keys, and
  managed-profile markers. Readers accept only enumerated aliases; serializers emit canonical
  values.
- Preserved the frozen legacy source at Git tree
  `66b23ca83b6ce3b29871954c63a6554c39bfd72e`, 52 files, and deterministic tree SHA-256
  `ee3486b96fc07308d089d0cabf09a218ecd3008369c5adb2444e70719c1e8c0e`.
- Kept the active marketplace byte-identical at SHA-256
  `42803919b39b720599b9692bfdcd95bcfe8c31b06ebb2c976aacaa890fdfea8a`.
- Added exact current-versus-target inventory validation, cross-plugin import and symlink guards,
  isolated consumer-layout tests, and digest-bound legacy vocabulary classification.
- Preserved the AppSec skill body byte-identically while adapting its invalid source frontmatter to
  the Codex skill schema.
- Added an idempotent source materializer that refuses profile/cache destinations, maintained-repo
  destinations, direct destination symlinks, special nodes, non-directory roots, and drift.
- Did not install, publish, trust, or mutate any plugin profile or cache. Those external states are
  recorded as unobserved rather than inferred.

Implementation commit: `18b057892981cd002a31e142db400f7caab339f2`.
Evidence commit: `509898adb6f75b0a5bb7d00cbd66ca098f9864f7`.
Evidence artifact: `docs/validation/codex-plugin-modernization-u9.json`.

## Review

Two independent read-only re-reviews covered inventory separation, compatibility correctness,
AppSec preservation, materialization safety, isolated layouts, dynamic import boundaries, and
historical evidence binding. Neither found a remaining P0-P3 issue after remediation.

## Checks

- Full suite on the implementation SHA: `1489 passed`.
- Focused U9 suite: `125 passed`.
- Scoped Ruff: passed.
- Current and target-fixture repository validators: passed.
- U9 unit-stage port contract: passed.
- Frozen source-window verification: 156 rows reproduced.
- Generated classification, Saga facts, and visual assets: current.
- Plugin authoring validation and both skill validators: passed.
- Legacy vocabulary inventory: 150 exact entries, 45 bound historical entries, and three
  immutable history sentinels.

The unrelated `.serena/project.yml` modification and `.codex/worktrees/` content remained outside
all commits.

## Next Step

Execute U3: define the 25 logical role contracts, map agent-backed roles onto the five fleet-core
execution classes, keep deterministic validators model-free, render the managed profile set, and
prove role/lens equivalence before U4 adds runtime dispatch.
