---
title: Saga Family Documentation Package Plan
type: docs
status: active
date: 2026-06-09
origin: docs/brainstorms/2026-06-09-saga-family-documentation-package-requirements.md
deepened: 2026-06-09
---

# Saga Family Documentation Package Plan

## Summary

Build a comprehensive `docs/saga/` field guide with generated lifecycle facts, polished visual assets, command dry-run references, scenario playbooks, state and maturity guidance, markdown failure examples, recovery playbooks, and drift tests.

The work is docs/template/test only. It must not change Saga runtime behavior, command semantics, backend choices, or mutation ownership.

---

## Problem Frame

The repo already contains accurate Saga family source material, but the operator-facing explanation is scattered. The root README lists the active plugins and validation commands, but does not teach the lifecycle or command choice (`README.md:5`, `README.md:8`, `README.md:31`).

The Saga README states the core boundary: Saga owns lifecycle choice, local state, and handoff envelopes, while `mission-control`, `deploy`, and `team-execution` own their separate mutation or orchestration domains (`plugins/saga/README.md:5`, `plugins/saga/README.md:42`). The plan turns those source facts into a user-facing documentation package.

The implementation is deep because it will introduce a new docs tree, generated fact data, visual assets, cross-links, and tests across the Saga family. Current grounding found 18 Saga skills, 7 Mission Control skills, 2 Team Execution skills, 5 Deploy skills, no existing `docs/saga/` directory, and 24 existing tracked docs files.

---

## Requirements

**Information Architecture And User Guidance**

- R1. Create `docs/saga/` as the canonical user-facing Saga family guide.
- R2. Cross-link the guide from root and Saga-family plugin READMEs.
- R3. Keep the guide operational and user-facing rather than architecture-first.
- R4. Use repo-relative links and avoid installed-cache paths as maintained source.

**Lifecycle, State, And Maturity**

- R5. Explain the full Saga journey from unframed ask through ideation, requirements, planning, review, work, code review, QA, handoff, retro, and deployment handoff.
- R6. Explain `lifecycle_phase`, `phase_status`, `status`, derived `maturity`, and owner precedence.
- R7. Include a readiness ladder for `idea-ready`, `requirements-ready`, `plan-ready`, `resume-ready`, and `deferred-context`.

**Command Catalog And Scenarios**

- R8. Document every Saga family command surface needed for lifecycle operation: the 17 routable Saga commands, the `saga:ceo-review` alias, 7 Mission Control skills, 2 Team Execution skills, and 5 Deploy skills.
- R9. For each command, show purpose, use cases, avoid cases, inputs, outputs, state impact, mutation boundary, likely next route, and a dry-run read/write/mutate/route map.
- R10. Include scenario playbooks for at least eight common journeys from the requirements artifact.

**Visuals And Generated Truth**

- R11. Generate canonical lifecycle/command facts from repo contracts where practical.
- R12. Render the primary Lifecycle Atlas as polished SVG with PNG/PDF exports when the local renderer is present.
- R13. Keep Mermaid optional and supplemental, not the primary presentation asset.
- R14. Add tests so command inventory, generated facts, required docs, and visual assets do not silently drift.

**Safety And Recovery**

- R15. Include a markdown contract failure matrix tied to the formatting contract and formatting tests.
- R16. Include recovery playbooks for stale Saga state, malformed handoff context, missing artifacts, stale branch/PR pointers, and moved docs.
- R17. Frame any manual repair as last-resort recovery, not normal gate bypass.

---

## Key Technical Decisions

KTD1. `docs/saga/` is the canonical operator guide: the repo currently has plugin-local READMEs and portability docs, but no `docs/saga/` tree. A single guide keeps the user journey coherent while plugin READMEs stay concise and plugin-local.

KTD2. Generate lifecycle facts with standard-library Python and commit the generated JSON: tests can compare skill inventory, route counts, versions, maturity mappings, and required docs without requiring PyYAML or image libraries in `uv run`.

KTD3. Use SVG as the source visual format and `rsvg-convert` for PNG/PDF export: local probing found `rsvg-convert` available, while Python `PIL`, `cairosvg`, and `reportlab` are unavailable. SVG keeps the atlas editable and presentation-worthy without adding dependencies.

KTD4. Put docs drift checks in a focused `tests/test_saga_docs_package.py`: this keeps the normal plugin validator scoped to plugin packaging while the new test owns documentation-package completeness and generated-fact alignment.

KTD5. Keep recovery docs safety-first: recovery starts with inspection, validation, rerun, and owner-state reconciliation because Saga cached state is explicitly not authoritative when it disagrees with git, GitHub, deployment state, or the engineering journal (`plugins/saga/references/saga-spec.md:33`, `plugins/saga/references/saga-spec.md:45`).

KTD6. Route implementation to a PR with `team-execution` available: the plan touches enough files and phases to benefit from reviewer/validator orchestration, even though the work remains documentation/test-only.

---

## High-Level Technical Design

The package has three layers: generated facts, human-authored guide pages, and presentation assets.

| Layer | Files | Role |
|---|---|---|
| Generated facts | `scripts/build_saga_docs_facts.py`, `docs/saga/generated/lifecycle-facts.json` | Extract command, plugin, route, state, maturity, and visual-node facts from repo source. |
| Human guide | `docs/saga/*.md`, README cross-links | Explain how an operator actually uses Saga family workflows. |
| Visual assets | `docs/saga/visual-assets/*`, `scripts/render_saga_docs_assets.py` | Render the lifecycle atlas and quick-reference visuals from generated facts. |
| Drift tests | `tests/test_saga_docs_package.py` | Assert the package remains aligned with plugin inventory, state contracts, and docs assets. |

The generated facts should be intentionally small. They should not try to parse every sentence in every skill file. They should extract stable facts from plugin manifests, skill frontmatter, `scripts/validate_codex_plugins.py`, `plugins/saga/references/saga-spec.md`, and the dispatch table.

The authored docs should read as a product manual. They can cite source contracts, but should not force a new operator to read them.

---

## Implementation Units

### U1. Build Generated Saga Docs Facts

Create the deterministic fact layer that downstream docs, visuals, and tests can trust.

**Goal:** Generate a compact JSON file describing Saga family plugins, commands, route facts, state axes, maturity mappings, and visual nodes.

**Requirements:** R8, R11, R14.

**Dependencies:** none.

**Files:** `scripts/build_saga_docs_facts.py`, `docs/saga/generated/lifecycle-facts.json`, `tests/test_saga_docs_package.py`.

**Approach:** Implement a standard-library Python script that reads plugin manifests and `SKILL.md` frontmatter for `saga`, `mission-control`, `team-execution`, and `deploy`. Use direct constants or conservative regexes for route and maturity facts anchored to `plugins/saga/skills/loop/references/dispatch-table.md` and `plugins/saga/references/saga-spec.md`.

The generated JSON should record at least plugin versions, skill names, 17 routable Saga commands, `saga:ceo-review` as an alias-style skill, lifecycle phases, phase statuses, thread statuses, maturity derivation, hard/advisory gate notes, and owner-plugin boundaries.

**Patterns to follow:** `scripts/validate_codex_plugins.py` already centralizes expected plugin versions and skills (`scripts/validate_codex_plugins.py:55`). `scripts/prove_codex_plugin_profile.py` already reads skill files for namespace proof (`scripts/prove_codex_plugin_profile.py:135`).

**Test scenarios:** Happy path: running the script regenerates `docs/saga/generated/lifecycle-facts.json` deterministically. Edge case: missing or renamed skill frontmatter causes the docs package test to fail. Error path: the script exits with a clear message when a referenced source file is missing. Integration scenario: the generated facts agree with `TARGET_EXPECTED_PLUGINS` for Saga family versions and skills.

**Verification:** `python3 scripts/build_saga_docs_facts.py --check` passes, and `PYTHONPATH=. python3 -m pytest tests/test_saga_docs_package.py -q` fails if the generated file is stale.

### U2. Create The Saga Family Field Guide

Create the main user-facing guide and connect it from the normal repo entrypoints.

**Goal:** Make `docs/saga/README.md` the first place a new user goes to understand Saga family workflows.

**Requirements:** R1, R2, R3, R4.

**Dependencies:** U1.

**Files:** `docs/saga/README.md`, `docs/saga/associated-plugins.md`, `docs/saga/quick-reference.md`, `README.md`, `plugins/saga/README.md`, `plugins/mission-control/README.md`, `plugins/team-execution/README.md`, `plugins/deploy/README.md`.

**Approach:** Write the field guide around operator questions: what Saga is, what the Saga family includes, what to run next, where durable artifacts live, and which plugin owns which mutation. Keep plugin READMEs concise by adding cross-links and short orientation text instead of duplicating the full guide.

**Patterns to follow:** Root README already carries active plugin inventory and source policy (`README.md:8`, `README.md:41`). Saga README already names skill groups, state path, execution backends, and plugin boundaries (`plugins/saga/README.md:8`, `plugins/saga/README.md:20`, `plugins/saga/README.md:32`, `plugins/saga/README.md:42`).

**Test scenarios:** Happy path: every README link resolves to an existing repo-relative path. Edge case: guide text does not use installed cache paths. Error path: docs package tests fail if `docs/saga/README.md` or required cross-links are missing.

**Verification:** Link/path tests pass, and the root README gives a clear Saga family guide entrypoint.

### U3. Document State, Maturity, And Ownership Boundaries

Turn the Saga state contract into an operator reference.

**Goal:** Explain what Saga stores, what it derives, and which external owner wins when state disagrees.

**Requirements:** R5, R6, R7.

**Dependencies:** U1, U2.

**Files:** `docs/saga/state-and-maturity.md`, `docs/saga/associated-plugins.md`.

**Approach:** Write a state reference with tables for `lifecycle_phase`, `phase_status`, `status`, and derived maturity. Include a readiness ladder and examples for durable artifact paths, handoff maturity, and stale cached state. Keep ownership boundaries tied to `saga`, `mission-control`, `team-execution`, and `deploy`.

**Patterns to follow:** Saga spec defines the three stored axes and derived maturity (`plugins/saga/references/saga-spec.md:158`). The same spec states Saga owns only work-thread state and external owners are authoritative (`plugins/saga/references/saga-spec.md:33`). The capability map records boundary replacements across Saga, Mission Control, Deploy, and Team Execution (`docs/portability/saga-family-capability-map.md:51`).

**Test scenarios:** Happy path: the readiness ladder includes all expected maturity values. Edge case: `deferred-context` is documented as handoff issue context rather than Saga frontmatter. Error path: docs tests fail if any maturity value or owner plugin is omitted.

**Verification:** A reader can determine that `requirements-ready` normally routes to `/plan` and that `mission-control` owns issue mutation.

### U4. Build The Command Catalog And Dry-Run Maps

Create a command-level reference that makes every Saga family command actionable.

**Goal:** Document purpose, inputs, outputs, consumed artifacts, emitted artifacts, state impact, owner boundary, and next route for each command.

**Requirements:** R8, R9, R14.

**Dependencies:** U1, U3.

**Files:** `docs/saga/command-catalog.md`, `docs/saga/generated/lifecycle-facts.json`, `tests/test_saga_docs_package.py`.

**Approach:** Use generated facts for command inventory and write human-authored catalog entries grouped by plugin. Represent dry-run behavior as tables: reads, writes, mutates, routes. Explicitly label shipped, advisory, off-chain, hard-gated, and alias behaviors.

**Patterns to follow:** Dispatch table defines the 17 routable Saga commands and hard/advisory behavior (`plugins/saga/skills/loop/references/dispatch-table.md:3`, `plugins/saga/skills/loop/references/dispatch-table.md:21`). Mission Control README lists its seven Codex skills (`plugins/mission-control/README.md:65`). Team Execution README names its two skills and runtime modes (`plugins/team-execution/README.md:5`, `plugins/team-execution/README.md:12`). Deploy README lists deployment command surfaces (`plugins/deploy/README.md:5`).

**Test scenarios:** Happy path: catalog includes all 32 Saga family skill surfaces. Edge case: `saga:ceo-review` is documented as an alias-style skill rather than a separate lifecycle phase. Error path: tests fail if a skill appears in generated facts but lacks a catalog entry.

**Verification:** A user can distinguish `saga:handoff` from `mission-control:issues` and `saga:qa` from `deploy:deploy`.

### U5. Write Scenario Playbooks

Make the lifecycle learnable through concrete examples.

**Goal:** Add scenario playbooks that show real operator journeys through commands, artifacts, state/maturity changes, and owner boundaries.

**Requirements:** R5, R10.

**Dependencies:** U2, U3, U4.

**Files:** `docs/saga/scenarios.md`.

**Approach:** Write at least eight scenarios: vague idea to plan, plan-ready issue to PR, PR-ready work through review and QA, handoff issue creation, security-sensitive review escalation, deployment after QA, hotfix flow, and stalled Saga recovery. Each scenario should include starting prompt, route, artifacts, state/maturity transitions, owner boundary, and outcome.

**Patterns to follow:** The dispatch table’s main chain is `idea/requirements-ready -> /plan -> /doc-review -> /work -> /code-review -> /qa -> /handoff or /retro` (`plugins/saga/skills/loop/references/dispatch-table.md:61`). Off-chain commands and recovery-related routes are explicitly advisory (`plugins/saga/skills/loop/references/dispatch-table.md:88`).

**Test scenarios:** Happy path: scenarios cover the required eight journeys. Edge case: security-sensitive review escalation names `team-execution` without implying it authorizes mutation. Error path: docs tests fail if a required scenario heading is missing.

**Verification:** A new operator can read one scenario and know which command to invoke next for that situation.

### U6. Add Markdown Contract And Recovery Playbooks

Document failure modes that make generated artifacts hard to read or lifecycle state hard to resume.

**Goal:** Make formatting failures and stuck-state recovery recognizable and safe to handle.

**Requirements:** R15, R16, R17.

**Dependencies:** U2, U3.

**Files:** `docs/saga/markdown-contracts.md`, `docs/saga/recovery-playbooks.md`.

**Approach:** Write a bad-versus-good markdown matrix for stacked bold labels, prose walls, ambiguous tables, malformed maturity/source context, and missing blank-line separation. Write recovery playbooks that start with `saga.py scan`, `saga.py restore`, artifact inspection, git/GitHub owner checks, and rerun paths before any manual state repair.

**Patterns to follow:** The formatting contract states the collapse failure and the no-stacked-label rule (`plugins/saga/references/formatting-style.md:9`, `plugins/saga/references/formatting-style.md:29`). The existing formatting test documents the collapse detector and the nine doc-writing skill coverage (`tests/test_saga_doc_formatting.py:9`, `tests/test_saga_doc_formatting.py:38`).

**Test scenarios:** Happy path: docs include at least one bad/good example for stacked labels and one recovery path for stale cached state. Edge case: manual repair warnings appear before any repair example. Error path: tests fail if the docs omit links back to the formatting contract.

**Verification:** A maintainer can identify a collapse-prone artifact and a user can recover from stale local Saga state without treating `.codex/saga` as authoritative.

### U7. Render The Lifecycle Atlas And Visual Assets

Create the presentation-grade visual layer.

**Goal:** Produce a polished Lifecycle Atlas and quick-reference visual assets from deterministic facts.

**Requirements:** R11, R12, R13.

**Dependencies:** U1, U3, U4, U5.

**Files:** `scripts/render_saga_docs_assets.py`, `docs/saga/lifecycle-atlas.md`, `docs/saga/visual-assets/saga-lifecycle-atlas.svg`, `docs/saga/visual-assets/saga-lifecycle-atlas.png`, `docs/saga/visual-assets/saga-lifecycle-atlas.pdf`, `docs/saga/visual-assets/readiness-ladder.svg`, `docs/saga/visual-assets/ownership-boundaries.svg`.

**Approach:** Render SVG from the generated JSON using standard-library Python. Use a lane-based visual model: user intent, command, artifact, state/maturity, gate, and owner plugin. Export PNG/PDF with `rsvg-convert` when present and fail with a clear setup message when it is missing.

**Patterns to follow:** Formatting contract favors tables and compact comparative layouts for readability (`plugins/saga/references/formatting-style.md:31`). The Lifecycle Atlas should reflect the dispatch table’s route and destination classes (`plugins/saga/skills/loop/references/dispatch-table.md:149`).

**Test scenarios:** Happy path: renderer writes SVG and exports PNG/PDF on a machine with `rsvg-convert`. Edge case: renderer `--check` reports stale assets without rewriting. Error path: missing `rsvg-convert` produces setup guidance rather than a silent partial export.

**Verification:** Visual asset files exist, are referenced by docs, and the SVG contains the expected owner lanes and lifecycle phases.

### U8. Add Final Drift Tests And Validation Coverage

Make the docs package maintainable.

**Goal:** Ensure the new guide, command catalog, generated facts, visual assets, and cross-links remain aligned with the repo.

**Requirements:** R4, R14.

**Dependencies:** U1 through U7.

**Files:** `tests/test_saga_docs_package.py`, `README.md`, `docs/saga/README.md`.

**Approach:** Add tests for required docs existence, repo-relative links, generated JSON freshness, command catalog coverage, maturity values, visual asset existence, and required cross-links. Keep these tests narrow and separate from plugin packaging validation.

**Patterns to follow:** Existing validation tests assert repository inventory and expected Saga-family skills (`tests/test_validate_codex_plugins.py:20`, `tests/test_validate_codex_plugins.py:33`). The formatting gate demonstrates a focused docs-structure test that avoids broad runtime coupling (`tests/test_saga_doc_formatting.py:1`).

**Test scenarios:** Happy path: `PYTHONPATH=. python3 -m pytest tests/test_saga_docs_package.py tests/test_saga_doc_formatting.py -q` passes. Edge case: an added Saga skill without a catalog entry fails the docs package test. Error path: stale generated JSON fails with the regeneration command.

**Verification:** Full repo validation and the new docs tests pass before `/doc-review`.

---

## Risks & Dependencies

| Risk | Mitigation |
|---|---|
| Visual assets rot or contradict the routing table | Generate canonical facts and test generated JSON freshness before rendering assets. |
| The docs become architecture-first | Keep every page organized around operator questions, command choice, state interpretation, and scenarios. |
| Catalog coverage becomes too large to maintain manually | Use generated facts to assert coverage while preserving human-authored summaries. |
| PNG/PDF export depends on local tooling | Use SVG as the editable source and `rsvg-convert` for exports, with explicit setup guidance if missing. |
| Recovery playbooks normalize bypassing gates | Put inspection, validation, rerun, and owner reconciliation before any manual repair, and label repair as last resort. |
| `uv run pytest -q` still lacks PyYAML in the isolated env | Keep new scripts standard-library only and validate with targeted tests plus `python3 -m pytest`; do not add a dependency for this docs package. |

---

## Alternatives Considered

| Alternative | Decision |
|---|---|
| One giant `plugins/saga/README.md` | Rejected because it would hide associated plugin boundaries and become too dense for new users. |
| Mermaid as the primary visual system | Rejected because the user asked for presentation-worthy diagrams and default Mermaid output is not strong enough for the centerpiece asset. |
| Fully hand-drawn visuals only | Rejected because visuals would drift from the dispatch table and command inventory. |
| Interactive sandbox in v1 | Deferred because a dummy runtime path adds maintenance cost and is not needed to document the existing lifecycle. |
| Add a new dependency for image/PDF export | Rejected for v1 because `rsvg-convert` is available locally and SVG source keeps the assets maintainable. |

---

## Scope Boundaries

**In Scope**

- New `docs/saga/` guide tree.
- Generated lifecycle facts and docs drift tests.
- Presentation-quality SVG plus PNG/PDF visual assets.
- Command catalog with dry-run maps.
- Scenario playbooks.
- State/maturity and ownership boundary references.
- Markdown contract and recovery guidance.
- README cross-links.

**Deferred to Follow-Up Work**

- Interactive `saga --sandbox` or live dummy execution.
- Full standalone documentation website.
- Slide deck export beyond committed visual assets and quick-reference docs.
- Broader docs for plugins outside the Saga family.

**Out of Scope**

- Saga runtime behavior changes.
- New command aliases, renamed skills, or command semantics changes.
- GitHub issue mutation, deploy mutation, or team-execution protocol changes.
- Claude-only `.claude`, `commands`, or `agents` active surfaces.
- Treating installed cache copies as maintained source.

---

## Success Metrics

| Metric | Target |
|---|---|
| Required docs coverage | All required `docs/saga/` pages exist and are linked. |
| Command coverage | 17 routable Saga commands, `saga:ceo-review`, 7 Mission Control skills, 2 Team Execution skills, and 5 Deploy skills appear in generated facts and command catalog. |
| Visual coverage | Lifecycle Atlas SVG, PNG, PDF, readiness ladder SVG, and ownership boundary SVG exist and are referenced. |
| Drift guardrails | New docs package tests fail on stale generated facts, missing catalog entries, missing maturity values, or broken repo-relative links. |
| Validation | `python3 scripts/validate_codex_plugins.py`, targeted docs tests, and full `python3 -m pytest -q` pass. |

---

## Sources / Research

| Source | Finding |
|---|---|
| `README.md:5` | This repo is a Codex-ready adapter, not a full source mirror. |
| `README.md:8` | Active plugin inventory includes `saga`, `deploy`, `mission-control`, and `team-execution`. |
| `README.md:31` | `scripts/validate_codex_plugins.py` is the existing package validation gate. |
| `plugins/saga/README.md:5` | Saga owns lifecycle choice, local state, and handoff envelopes, not issue/deploy/reviewer mutation. |
| `plugins/saga/README.md:20` | Ignored local Saga state belongs under `.codex/saga/`. |
| `plugins/saga/README.md:32` | Codex Saga backends are `inline` and `team-execution`. |
| `plugins/saga/references/saga-spec.md:20` | A saga is the durable, resumable work-state envelope for one lifecycle thread. |
| `plugins/saga/references/saga-spec.md:158` | Saga has three stored axes plus derived maturity. |
| `plugins/saga/skills/loop/references/dispatch-table.md:3` | `/loop` routing is total over 17 routable lifecycle commands. |
| `plugins/saga/skills/loop/references/dispatch-table.md:61` | The main chain runs requirements-ready work through plan, doc-review, work, code-review, QA, then handoff or retro. |
| `plugins/saga/references/formatting-style.md:17` | Generated Saga documents use short paragraphs and readable visual structure. |
| `plugins/mission-control/README.md:89` | Mission Control uses operator `gh` auth and requires preview/dry-run behavior for mutation. |
| `plugins/team-execution/README.md:12` | Team Execution has delegated and serial modes. |
| `plugins/deploy/README.md:12` | Deploy mutating commands must use explicit guardrails. |
| `docs/portability/saga-family-capability-map.md:51` | Saga family ownership boundaries are already mapped as migration context. |

---

## Review And Execution Route

The plan is ready for `/doc-review` before `/work`.

| Route field | Value | Rationale |
|---|---|---|
| Destination | `pr` | The package should land as one reviewed documentation/test PR. |
| Orchestration mode | `team-execution` | The work spans many files and benefits from independent docs, visual, and validator review. |
| Next command | `/doc-review docs/plans/2026-06-09-saga-family-documentation-package-plan.md` | `/work` gates on doc-review and blocks unresolved P0/P1 findings. |
