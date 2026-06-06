# Saga-Family Known-Use Inventory

Verified: 2026-06-06

This inventory records known active or migration-relevant uses of the old
`sdlc-manager` and `blueprint-reviewer` plugin family before hard deletion. It
uses normalized plugin and skill identifiers instead of local cache paths.

## Search Scope

Searches covered:

- This repo's maintained source, docs, scripts, tests, marketplace config, and
  planning artifacts.
- Installed Codex cache inventory for `sdlc-manager` and `blueprint-reviewer`,
  treated as installed-state evidence rather than maintained source.
- `hermes-extensions` as the known external migration input named by the plan.

No other external active invocation source was confirmed in this checkpoint.

## Disposition Vocabulary

| Disposition | Meaning |
|---|---|
| `replace-in-u8` | Active current repo surface that will be removed or rewritten during cutover. |
| `update-before-u8` | Active validation or test config that must learn the replacement before deletion. |
| `cutover-complete` | U8 removed or rewired this active surface to the Saga-family target. |
| `migration-reference` | Planning, provenance, or cutover text that may mention old names as historical or migration context. |
| `external-migration-input` | Confirmed external repo references that should route to the replacement owners after Codex cutover. |
| `cache-provenance` | Installed cache evidence only; not maintained source and not copied into the repo. |
| `lineage-only` | Old plugin source content that may be referenced only as source history until deletion. |

## Inventory

| Hit class | Evidence | Normalized identifiers | Confirmed active? | Disposition | Replacement |
|---|---|---|---|---|---|
| Repo marketplace entries | `.agents/plugins/marketplace.json` | `blueprint-reviewer`, `sdlc-manager` | Was active before U8 | `cutover-complete` | Replaced by `saga`, `deploy`, `mission-control`, and `team-execution` entries during U8. |
| Repo validator expectations | `scripts/validate_codex_plugins.py`, `tests/test_validate_codex_plugins.py` | `blueprint-reviewer`, `sdlc-manager`, `blueprint-review`, `issue-review`, `spec-review`, `sdlc-board`, `sdlc-flow`, `sdlc-issues`, `sdlc-labels`, `sdlc-metrics`, `sdlc-milestones`, `sdlc-rollout` | Was active before U8 | `cutover-complete` | Default validation now checks the eight-plugin Saga-family inventory; legacy names remain only as migration-check data. |
| Repo pytest discovery | `pyproject.toml` | `plugins/sdlc-manager/tests` | Was active before U8 | `cutover-complete` | Removed old test path; active plugin tests now cover mission-control, deploy, team-execution, saga, and repo-level checks. |
| Repo active inventory docs | `README.md`, `docs/baseline/codex-visible-plugins.md`, `docs/validation.md`, `docs/cutover/cache-replacement.md` | old active plugin and skill identifiers | Was active before U8 | `cutover-complete` | Updated to the eight-plugin Saga-family target and exact migration map links. |
| Current old plugin source roots | `plugins/sdlc-manager/`, `plugins/blueprint-reviewer/` | all old active plugin and skill identifiers | Was active before U8 | `cutover-complete` | Deleted after proof gates passed. Final active aliases are not allowed. |
| Portability and provenance docs | `docs/portability/matrix.md`, `docs/portability/provenance.md` | old plugin identifiers | Yes, as repo docs | `migration-reference` | Update with replacement provenance and mark old plugins as superseded lineage, not active target inventory. |
| Planning and ideation docs | `docs/brainstorms/`, `docs/ideation/`, `docs/plans/` | old plugin identifiers and old skill examples | No, migration planning only | `migration-reference` | Keep as historical decision context. Do not treat as active invocation proof. |
| Installed Codex cache | Codex cache inventory for old plugins | `sdlc-manager:{sdlc-board,sdlc-flow,sdlc-issues,sdlc-labels,sdlc-metrics,sdlc-milestones,sdlc-rollout}`, `blueprint-reviewer:{blueprint-review,issue-review,spec-review}` | Installed-state evidence only | `cache-provenance` | U7/U9 isolated proof must show old skills absent from fresh and upgrade profiles. |
| Hermes operation skill docs | `hermes-extensions/skills/infiquetra-operations/**` | `sdlc-manager:*` | Yes, external migration input | `external-migration-input` | Route SDLC references to `mission-control:*`; route loop or issue handoff ownership to `saga` handoff plus `mission-control:issues`. |
| Hermes operation registry and tests | `hermes-extensions/lib/infiquetra_ops/registry.py`, `hermes-extensions/lib/infiquetra_ops/tests/` | `sdlc-manager`, `sdlc-manager:*`, old slash commands | Yes, external migration input | `external-migration-input` | Replace registry family with `mission-control` equivalents in the Hermes repo after this Codex cutover plan establishes the target names. |
| Hermes loop SDLC references | `hermes-extensions/plugins/infiquetra_loop/**` | `sdlc-manager`, `/sdlc-board`, `/create-issue`, `/sdlc-create`, `/sdlc-triage`, `/sdlc-metrics` | Yes, external migration input | `external-migration-input` | Route lifecycle state and issue handoff through Saga; route SDLC mutation through `mission-control`. |
| Hermes review references | `hermes-extensions/plugins/infiquetra_loop/skills/doc-review/SKILL.md` | `blueprint-reviewer`, `/blueprint-review`, `/spec-review`, `/issue-review` | Yes, external migration input | `external-migration-input` | Route document review to `saga:doc-review` and `saga:spec`; route issue comment mutation to `mission-control:issues`; use `team-execution:team-execution` for consensus review where needed. |

## U8 Migration Rows

These old operator-facing invocations are removed as active aliases. Use the
exact namespaced replacement or representative prompt below.

| Old invocation | Replacement | Capability owner | Behavior difference | Removal rationale |
|---|---|---|---|---|
| `sdlc-manager:sdlc-board` / `sdlc-board` / `/sdlc-board` | `mission-control:board` | `mission-control` | Same board workflow owner, with Codex preview and confirmation gates preserved under the new namespace. | Old alias would keep the replaced plugin active. |
| `sdlc-manager:sdlc-flow` / `sdlc-flow` | `mission-control:flow` | `mission-control` | Field, sub-issue, card-validation, and mapping helpers move to the SDLC successor. | Old alias duplicates the successor namespace. |
| `sdlc-manager:sdlc-issues` / `sdlc-issues` / `/create-issue` / `/sdlc-create` / `/sdlc-triage` | `mission-control:issues`, with `mission-control:flow` for project-field helpers | `mission-control` | Prepared issue and triage flows stay mutation-gated; project-field helpers are split to `mission-control:flow`. | Old alias hides the mutation boundary split. |
| `sdlc-manager:sdlc-labels` / `sdlc-labels` | `mission-control:labels` | `mission-control` | Label audit and mutation remain SDLC operations with explicit confirmation. | Old alias keeps a retired package name visible. |
| `sdlc-manager:sdlc-metrics` / `sdlc-metrics` / `/sdlc-metrics` | `mission-control:metrics` | `mission-control` | Metrics remain read-oriented flow analysis under the SDLC successor. | Old alias is unnecessary compatibility surface. |
| `sdlc-manager:sdlc-milestones` / `sdlc-milestones` | `mission-control:milestones` | `mission-control` | Milestone lifecycle remains GitHub SDLC mutation with preview and confirmation. | Old alias would route mutation through the wrong owner name. |
| `sdlc-manager:sdlc-rollout` / `sdlc-rollout` | `mission-control:rollout` | `mission-control` | Rollout tracking remains SDLC rollout work under the successor plugin. | Old alias preserves obsolete package identity. |
| `blueprint-reviewer:blueprint-review` / `blueprint-review` / `/blueprint-review` | `saga:doc-review`; use `team-execution:team-execution` for independent reviewer consensus | `saga`, with `team-execution` escalation | Review routing moves to Saga; separate reviewer consensus is explicit instead of implicit. | Old alias would keep the deleted review plugin active. |
| `blueprint-reviewer:spec-review` / `spec-review` / `/spec-review` | `saga:spec` or `saga:doc-review` routing to `saga:spec`; use `team-execution:team-execution` for consensus | `saga`, with `team-execution` escalation | Spec review becomes Saga-owned spec flow, with consensus protocol separated. | Old alias conflicts with Saga as lifecycle spine. |
| `blueprint-reviewer:issue-review` / `issue-review` / `/issue-review` | `saga:doc-review`; `mission-control:issues` for GitHub comment mutation; `team-execution:team-execution` for consensus | `saga`, `mission-control`, and `team-execution` | Review classification, GitHub mutation, and consensus are split across explicit owners. | Old alias combines review and mutation authority too loosely. |

## Deletion Gate

Deletion was blocked until validator coverage proved this inventory had a
disposition for every confirmed active hit class and the U8 cutover docs exposed
the required migration rows. U8 removes the old active roots and marketplace
entries; any remaining old names in this file are migration or lineage context,
not active usage instructions.
