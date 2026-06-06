---
date: 2026-05-27
topic: codex-plugin-repo
origin: docs/ideation/2026-05-27-codex-plugin-strategy.md
---

# Codex Plugin Repo Requirements

## Summary

Create `infiquetra-codex-plugins` as the maintained Codex-native source for selected
Infiquetra plugins. The MVP contains the five Infiquetra plugins already visible in Codex,
adds `test-suite` as the first Claude-to-Codex proof port, and records portability decisions
so cross-tool differences are intentional rather than accidental drift.

---

## Problem Frame

Infiquetra currently has mature Claude plugin work and an Antigravity port, while Codex
already exposes a subset of Infiquetra plugin capabilities through installed cache state.
That cache proves Codex can use some of the content, but it is not a maintainable source of
truth. A Codex repo is useful only if it becomes a curated native adapter, not a third
mirror that silently inherits Claude or Antigravity assumptions.

The central risk is unmanaged divergence. Some plugins should be nearly portable across
tools, while others depend on host-specific primitives. `team-execution` is the canonical
example: the Claude version relies on `TeamCreate`, so a Codex version would need a native
workflow rather than a copied manifest.

---

## Key Decisions

- **Repo-managed replaces cache-managed.** The current Codex-visible plugins are the
  behavioral baseline, but the new repo becomes authoritative only after its versions load
  and expose equivalent capabilities through a trusted, rollbackable cutover path.
- **MVP includes one proof port.** `test-suite` is the first Claude-to-Codex port because it
  exercises skill plus script packaging without requiring a full orchestration redesign. It
  proves that boundary only; it does not prove MCP, app, marketplace, or orchestration
  transform rules.
- **Native Codex adapter, not Claude mirror.** Included plugins should use Codex-native
  metadata and docs while preserving portable skill content where that content genuinely
  applies.
- **Portability is explicit.** Every included, proof-port, deferred, blocked, or unsupported
  plugin needs a matrix entry explaining its Codex status and relationship to Claude and
  Antigravity.
- **Generators wait.** The MVP may include recipes and validation checks, but should not
  require a full generator until each boundary the generator would cover has been manually
  proven by a port or baseline plugin.

---

## Actors

- A1. Plugin maintainer: curates the Codex repo, ports plugins, and reviews divergence.
- A2. Codex user: installs or uses the repo-managed Codex plugins in normal Codex sessions.
- A3. Planning agent or reviewer: reads the matrix and requirements to plan port work without
  guessing which plugins belong in Codex.
- A4. Cross-tool maintainer: compares Claude, Codex, and Antigravity variants and decides
  whether differences are intended.

---

## Requirements

**Repository Scope**

- R1. The repo must position `infiquetra-codex-plugins` as a curated Codex-native adapter
  repo, not a full mirror of `infiquetra-claude-plugins`.
- R2. The MVP plugin set must include `blueprint-reviewer`, `home-lab-ops`,
  `python-toolkit`, `sdlc-manager`, `unifi`, and the `test-suite` proof port.
- R3. The repo must distinguish source-managed plugin content from installed or cached Codex
  state; cached plugin copies must not be edited as the source of truth.
- R4. The repo must document how repo-managed plugin installs supersede the currently
  installed Codex-visible versions after validation, including the trust and rollback gates
  required before cache-managed usage is replaced.

**Codex-Native Plugin Shape**

- R5. Each MVP plugin must have Codex-native plugin metadata suitable for Codex discovery and
  presentation.
- R6. Each MVP plugin must preserve portable skill assets where they apply, including
  `SKILL.md`, references, and scripts, while rewriting host-specific docs or invocation
  wording for Codex.
- R7. The `test-suite` proof port must include its quality-check skill and bundled runner
  script so the port tests skill plus script packaging, not manifest-only packaging.
- R8. The repo must avoid carrying Claude-only or Antigravity-only primitives into Codex docs
  unless they are explicitly marked as unsupported or lineage-only context.
- R18. Bundled script references must resolve only to reviewed scripts inside the packaged
  plugin; validation must reject path traversal and external script targets.

**Portability Matrix**

- R9. The repo must include a portability matrix covering the current Claude plugin catalog
  and classifying each plugin for Codex as one of: `included`, `proof-port`,
  `deferred`, `blocked`, or `unsupported`.
- R10. Matrix entries must include a short reason, the expected Codex treatment, and whether
  the plugin has Claude or Antigravity lineage.
- R11. The matrix must explicitly mark `team-execution` as `blocked` or `unsupported` for
  the MVP, with the reason or expected Codex treatment stating that a Codex-native redesign is
  required.
- R12. The matrix must make plugin count differences explainable without treating every
  missing plugin as backlog debt.
- R19. The matrix must record the source catalog snapshot, verification date or source
  commit, and the upstream-change trigger that requires review.

**Divergence and Validation**

- R13. Each MVP plugin must include a lightweight portability note or equivalent metadata
  describing shared lineage, intentional Codex differences, unsupported host features, and
  validation expectations.
- R14. Validation must prove that the five existing Codex-visible plugins still expose their
  expected skills and pass representative smoke or dry-run workflows when managed from the
  repo.
- R15. Validation must prove that the `test-suite` proof port is discoverable by Codex and
  that its runner script is reachable from the skill instructions and can pass a smoke or
  dry-run execution inside the packaged plugin boundary.
- R16. Drift checks must flag stale platform language, invalid host manifests, broken relative
  references, and unlisted inventory differences.
- R17. Any intentional difference from Claude or Antigravity must be recorded before it is
  allowed to pass drift checks.
- R20. Repo-managed cutover must only supersede cached plugins after an explicit trusted-source
  check, allowlisted plugin inventory, version or integrity pin verification, and documented
  rollback path.
- R21. Each baseline plugin entry must record provenance, including cache path, plugin version
  or source commit when available, exposed skills, and comparison against the canonical source
  used for the Codex repo.
- R22. The `test-suite` proof port must produce a reusable port recipe or decision record
  covering copied assets, Codex metadata transforms, host wording rewrites, unsupported host
  features, validation evidence, and what the proof does and does not establish for future
  generator work.

---

## Key Flows

- F1. Baseline the existing Codex-visible plugins
  - **Actors:** A1, A3
  - **Steps:** Identify the five plugins already visible in Codex, record cache provenance and
    exposed skills, compare them against the canonical source, and treat that behavior as the
    replacement baseline only after provenance is captured.
  - **Outcome:** The repo has a clear, sourced definition of what must continue working after
    cutover.
  - **Covers:** R2, R3, R14, R21

- F2. Port `test-suite` from Claude to Codex
  - **Actors:** A1, A3
  - **Steps:** Start from the Claude `test-suite` skill and runner script, adapt packaging and
    docs for Codex, validate the packaged script boundary, run a smoke or dry-run check, and
    record the port recipe.
  - **Outcome:** The proof port demonstrates a repeatable path for skill plus script plugins
    without overclaiming other plugin boundaries.
  - **Covers:** R5, R6, R7, R13, R15, R18, R22

- F3. Replace cache-managed usage with repo-managed usage
  - **Actors:** A1, A2
  - **Steps:** Validate repo-managed plugin discovery and runtime smoke checks, compare exposed
    skills to the baseline, verify the trusted source, inventory allowlist, pins, and rollback
    path, then treat the repo-managed versions as authoritative.
  - **Outcome:** The local cache is no longer the maintained source for these plugins; a
    permanent local install switch remains a separate post-validation action unless planning
    explicitly includes it.
  - **Covers:** R3, R4, R14, R15, R20, R21

- F4. Review plugin divergence
  - **Actors:** A1, A4
  - **Steps:** Compare Claude, Codex, and Antigravity inventory from a recorded source
    snapshot, classify each plugin in the matrix, and require notes for intentional
    differences or upstream inventory changes.
  - **Outcome:** Differences are either explained or fail validation as accidental drift.
  - **Covers:** R8, R9, R10, R11, R12, R16, R17, R19

---

## Acceptance Examples

- AE1. Existing Codex-visible plugin remains available
  - **Covers:** R2, R4, R14, R20, R21
  - **Given:** `python-toolkit` is included in the new repo-managed Codex plugin set.
  - **When:** Codex loads plugins from the repo-managed source and baseline validation runs.
  - **Then:** The same expected Python toolkit skills are visible to Codex, representative
    validation passes, cache provenance is recorded, and the cached copy is no longer treated
    as the source of truth.

- AE2. `test-suite` proves script packaging
  - **Covers:** R7, R15, R18, R22
  - **Given:** The Claude `test-suite` plugin includes a quality-check skill and runner script.
  - **When:** The Codex proof port is installed from `infiquetra-codex-plugins`.
  - **Then:** Codex can discover the skill, the skill instructions point to a reachable runner
    script inside the packaged plugin, the runner passes a smoke or dry-run check, and the port
    recipe records what the proof does and does not establish.

- AE3. `team-execution` is not accidentally copied
  - **Covers:** R8, R11, R12
  - **Given:** `team-execution` depends on Claude-specific orchestration.
  - **When:** The portability matrix is reviewed.
  - **Then:** `team-execution` is marked as `blocked` or `unsupported` for the MVP, with its
    expected Codex treatment stating that native redesign is required, rather than appearing as
    a direct Codex port.

- AE4. Drift check catches stale host language
  - **Covers:** R16, R17, R19
  - **Given:** A Codex plugin README includes Claude-only installation wording.
  - **When:** Drift checks run.
  - **Then:** The check fails unless that language is explicitly recorded as lineage context
    or an intentional unsupported note.

- AE5. Cutover is gated before cache replacement
  - **Covers:** R4, R20
  - **Given:** Repo-managed plugin artifacts have been created for the MVP set.
  - **When:** The maintainer prepares to replace cache-managed usage.
  - **Then:** The cutover fails unless the trusted source, allowlisted inventory, version or
    integrity pin, and rollback path are documented.

- AE6. Matrix freshness is explicit
  - **Covers:** R9, R19
  - **Given:** The Claude plugin catalog changes after the matrix is written.
  - **When:** Drift checks compare the matrix against its declared source snapshot.
  - **Then:** The change is flagged for review instead of silently leaving the old
    classification in place.

---

## Success Criteria

- Codex can load the repo-managed versions of the five existing Codex-visible plugins and pass
  representative smoke or dry-run validation.
- Codex can load the `test-suite` proof port, resolve its bundled runner inside the packaged
  plugin boundary, and run its smoke or dry-run check.
- The portability matrix explains every current Claude plugin's Codex status and records the
  source snapshot or verification point behind that claim.
- The repo has enough validation to distinguish intentional divergence from stale copied
  content.
- The proof port leaves behind a reusable port recipe or decision record.
- Cutover documentation covers trusted source, allowed inventory, pins, and rollback without
  requiring a permanent local install switch as part of the MVP.
- A planning agent can use this requirements document to plan the repo scaffold and first
  proof port without inventing MVP scope.

---

## Scope Boundaries

Deferred for later:

- Native Codex redesign of `team-execution`.
- Bulk-porting the full Claude plugin catalog.
- Building a generator for all host manifests and docs.
- Publishing or marketplace distribution beyond local/repo-managed validation.
- Permanently switching the local Codex installation away from cached plugins, unless the
  implementation plan explicitly opts into that post-validation action.

Outside the MVP:

- Treating Antigravity as an equal peer target for every plugin.
- Editing installed Codex cache artifacts as maintained source.
- Requiring identical file trees across Claude, Codex, and Antigravity.
- Treating cached plugin behavior as normative without provenance and source comparison.

---

## Dependencies And Assumptions

- The current Codex-visible five plugins are usable enough to define the initial baseline only
  after their provenance and exposed behavior are recorded.
- Codex-native packaging should use Codex plugin metadata rather than relying on
  Claude-shaped manifests.
- `test-suite` is a better MVP proof port than `team-execution` because it tests real
  skill and script packaging without requiring a new orchestration model.
- `test-suite` does not prove transform rules for MCP servers, apps, marketplace metadata, or
  native orchestration; those boundaries need separate proof before generator work depends on
  them.
- Exact installation and cutover mechanics can be settled during planning as long as trusted
  source, provenance, rollback, and validation outcomes are preserved.

---

## Outstanding Questions

Deferred to planning:

- Which local or repo marketplace entry should be used for first validation?
- Should the repo preserve plugin versions from Claude lineage or assign new Codex-specific
  versions for the MVP?
- What is the narrowest automated check set that proves equivalent Codex skill discovery for
  the five baseline plugins?
- Which install source and version identity should be treated as trusted for the first
  repo-managed cutover?
- Which additional plugin boundary, if any, must be manually proven before generator work is
  considered?

---

## Sources

- `docs/ideation/2026-05-27-codex-plugin-strategy.md`
- `infiquetra-claude-plugins/README.md`
- `infiquetra-antigravity-plugins/README.md`
- `infiquetra-claude-plugins/plugins/test-suite/README.md`
- `infiquetra-claude-plugins/plugins/test-suite/skills/run-quality-checks/SKILL.md`
- `infiquetra-claude-plugins/plugins/team-execution/README.md`
