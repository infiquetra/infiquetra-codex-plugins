---
date: 2026-06-06
topic: codex-saga-family-replacement
origin: docs/ideation/2026-06-06-codex-saga-port-ideation.md
---

# Codex Saga Family Replacement Requirements

## Summary

Replace the active `sdlc-manager` and `blueprint-reviewer` Codex plugins with a
full Saga-family plugin set: `saga`, `deploy`, `mission-control`, and
`team-execution`. The replacement must land as one atomic change, keep
source-parity skill names behind plugin namespaces, prove Codex CLI visibility
in an isolated profile, and preserve Saga-family ownership boundaries.

---

## Problem Frame

`infiquetra-codex-plugins` started as a curated Codex-native adapter for the
first plugin baseline. That baseline intentionally excluded `team-execution`
because the Claude version depended on host-specific orchestration, and it kept
`sdlc-manager` plus `blueprint-reviewer` as working Codex-visible surfaces.

The upstream Claude plugin family has since moved to a different operating
model. Saga is now the lifecycle spine, `mission-control` is the SDLC successor,
`deploy` owns tag-promotion deployment operations, and `team-execution` is a
reviewer and validator protocol rather than a direct code dependency of Saga.
Keeping the old Codex baseline as active source would make Codex drift from the
current Infiquetra workflow.

The replacement should be direct and opinionated. This is not a compatibility
release. The old plugin names and old skill names disappear from active Codex
source once the new family passes validation.

---

## Key Decisions

- **Atomic replacement.** The first implementation PR must port all four
  Saga-family plugins and remove active `sdlc-manager` and `blueprint-reviewer`
  in the same change. This is a high-risk cutover choice, so the PR must carry
  explicit rollback instructions and split criteria for postponing the hard
  delete if any replacement plugin fails proof.
- **Hard delete active old plugins.** Remove the old plugin directories,
  marketplace entries, validator expectations, and active baseline docs; keep
  only migration and provenance notes where they help future readers.
- **Source-parity skill names.** Keep Saga-family skill names close to the
  Claude source and rely on Codex plugin namespaces for invocation, including
  generic names such as `saga:plan` and `saga:work`.
- **Codex-specific state.** Runtime state for Saga and team-execution belongs
  under `.codex/saga/` and `.codex/team-execution/`.
- **Subagents first, fallback required.** `team-execution` uses Codex subagents
  when available and allowed, but remains usable through serial main-thread
  execution when they are unavailable.
- **No custom-agent sidecar in v1.** The replacement must work through native
  Codex plugins and current runtime tools; optional `.codex/agents/` installers
  are deferred.
- **Host-gated backend contract.** `cc-workflows-ultracode` remains documented
  as Claude lineage or reference context, but Codex must not offer it as an
  executable backend.
- **Strict Codex proof.** Local validation is not enough; the replacement must
  prove installability and namespaced skill visibility in an isolated Codex test
  profile before merge.
- **Frozen source baseline.** Planning must freeze the Claude source snapshot
  and capability inventory that define parity before implementation begins.
- **Cutover can fail closed.** Hard deletion remains the target, but old active
  plugins must not be removed unless the parity map, validation, degraded-mode
  proof, and isolated Codex proof all pass.
- **Known-use inventory before deletion.** Hard deletion also requires an
  inventory of known old-plugin and old-skill invocations so each use is mapped,
  retired, or accepted as an intentional break.

---

## Actors

- A1. Plugin maintainer: ports the plugins, removes the old active surfaces, and
  owns validation evidence.
- A2. Codex operator: installs or invokes the new plugins from Codex CLI.
- A3. Lifecycle operator: uses Saga to choose lifecycle phases, route handoffs,
  and record local state.
- A4. SDLC operator: uses mission-control for issues, boards, labels,
  milestones, metrics, rollout, comments, and card validation.
- A5. Release operator: uses deploy for tag promotion, rollback, hotfix,
  release notes, status, and deployment evidence.
- A6. Team-execution operator: uses reviewer consensus, validator gates, and
  subagent or fallback execution.
- A7. Reviewer: checks that hard deletion did not remove required behavior
  without a mapped replacement.

---

## Requirements

**Plugin Inventory And Removal**

- R1. The active Codex plugin inventory must include `saga`, `deploy`,
  `mission-control`, `team-execution`, `home-lab-ops`, `python-toolkit`,
  `unifi`, and `test-suite`.
- R2. The active Codex plugin inventory must not include `sdlc-manager` or
  `blueprint-reviewer`.
- R3. The replacement must remove active source directories, marketplace
  entries, validator expectations, and baseline visibility entries for
  `sdlc-manager` and `blueprint-reviewer`.
- R4. Migration notes must map old capabilities to new owners without keeping
  old skill names active.
- R5. Provenance notes may mention removed plugins as lineage, but active usage
  docs must point to the Saga-family replacements.

**Codex-Native Packaging**

- R6. Each new plugin must have a Codex manifest, active skill surface, README,
  portability note, and validation coverage consistent with existing repo
  conventions.
- R7. New plugins must not carry active `.claude-plugin`, `commands`, or
  `agents` directories inside Codex plugin roots.
- R8. Claude slash-command behavior must be represented as Codex skills,
  references, and bundled scripts rather than active command files.
- R9. Skill names must preserve source-parity where Codex namespaces make that
  safe.
- R10. Validation must prove namespaced invocation for generic Saga skills,
  including at least `saga:plan`, `saga:work`, and `saga:brainstorm`.
- R11. The replacement must use repo-relative paths in docs and avoid stale
  active references to Claude plugin cache paths or Claude runtime state.

**Saga Lifecycle**

- R12. `saga` must provide the full Saga lifecycle surface, including ideation,
  brainstorming, planning, work, loop orchestration, handoff, QA, reviews,
  resume, retro, strategy, and related helpers.
- R13. Saga must own lifecycle choice, state recording, handoff envelopes, and
  routing, but not deployment mutation or SDLC mutation.
- R14. Saga must route deployment work to `deploy` and SDLC issue, comment,
  card, and board mutation to `mission-control`.
- R15. Saga must offer only Codex-executable backends in Codex sessions:
  `inline` and `team-execution`.
- R16. Saga may document `cc-workflows-ultracode` as Claude lineage or context,
  but must not present it as a Codex operator choice.
- R17. Saga local runtime state must use `.codex/saga/` rather than
  `.claude/saga/`.

**Mission-Control Successor Scope**

- R18. `mission-control` must be the full active successor to `sdlc-manager`.
- R19. `mission-control` must cover prepared issues, board movement, issue
  comments, labels, milestones, metrics, rollout, card validation, and SDLC
  status workflows.
- R20. Existing `sdlc-manager` capabilities that remain part of Infiquetra SDLC
  operations must have a mapped mission-control replacement.
- R21. Before old-plugin deletion is approved, the replacement must include a
  finite capability map covering active `sdlc-manager` skills and workflows,
  marking each as replaced by mission-control or intentionally removed.

**Deploy Scope**

- R22. `deploy` must include full deployment operations scope: tag minting,
  tag promotion, rollback, hotfix, release notes, status, and deployment
  evidence workflows.
- R23. Deploy mutation paths must require explicit operator confirmation before
  changing tags, releases, GitHub state, or deployment records.
- R24. Deploy must provide dry-run or preview paths for release notes, tag
  planning, rollback/hotfix planning, and status inspection.
- R25. Saga must not duplicate deploy mutation behavior.

**Team-Execution Runtime**

- R26. `team-execution` must port the two-phase planning and execution protocol,
  reviewer registry, validator registry, consensus expectations, evidence
  capture, and nonprod automation safeguards.
- R27. `team-execution` must use Codex subagents when the runtime exposes them
  and the task is safe to delegate.
- R28. `team-execution` must still operate without subagents by running the same
  reviewer, validator, and evidence gates in serial or main-thread mode.
- R29. Missing subagent support must degrade with a clear note, not fail the
  workflow.
- R30. The v1 replacement must not require a custom-agent sidecar installer.
- R31. `team-execution` local runtime state must use
  `.codex/team-execution/` rather than `.claude/team-execution/`.

**Validation And Cutover**

- R32. Repo validation must fail if old active plugin inventory remains or if
  new Saga-family plugins are missing.
- R33. Plugin manifest validation must pass for every active plugin.
- R34. Unit tests and script smoke checks must cover the new bundled script
  boundaries and dry-run paths.
- R35. A strict Codex install and visibility proof must run in an isolated Codex
  test profile before merge.
- R36. The isolated Codex proof must show the new plugin set is discoverable and
  the new namespaced skills are visible or invocable.
- R37. The isolated Codex proof must not mutate the user's default Codex profile.
- R38. Validation must prove `team-execution` degraded mode works when subagents
  are absent.
- R39. Cutover documentation must state that old invocations are removed and
  point operators to the new plugin namespaces.

**Replacement Gates, Security, And Proof**

- R40. README and cutover docs must include an old-to-new invocation map for
  removed skills, reachable from the normal install or usage path.
- R41. Planning must freeze the upstream source commit and per-plugin
  capability inventory used as the parity baseline.
- R42. If isolated Codex proof shows source-parity namespaced invocation does
  not work, the replacement must fail before merge rather than silently
  renaming skills or adding aliases.
- R43. Mission-control GitHub write paths must present preview or dry-run output
  and require explicit operator confirmation before mutation, except for
  narrowly defined read-only and status workflows.
- R44. Mission-control and deploy must use an explicit GitHub authentication
  model with least-privilege scopes, no plugin-managed long-lived token storage,
  no credential logging, validation/real-operation environment separation, and
  clear failure behavior when permissions are insufficient.
- R45. Team-execution degraded mode must preserve reviewer and validator gates,
  evidence capture, dissent or uncertainty recording, and main-thread final
  verification.
- R46. Team-execution must define delegation safety criteria covering what data
  may be shared with subagents, which operations remain main-thread or
  confirmation-gated, and how delegated outputs are verified.
- R47. The isolated Codex proof must run at least one representative skill flow
  per new plugin, including reference loading, bundled script or dry-run reach,
  and approved `.codex/...` state behavior where applicable.
- R48. Hard deletion of old active plugins must be blocked unless the frozen
  source baseline, capability map, local validation, isolated Codex proof,
  deploy/mission-control confirmation gates, and team-execution degraded-mode
  proof all pass.
- R49. Generated `.codex/saga/` and `.codex/team-execution/` state or evidence
  paths must be gitignored or otherwise protected, avoid credentials, redact
  secrets and sensitive operational data, and define retention or cleanup
  expectations.
- R50. Mutation-capable validation for deploy and mission-control must use
  dry-run or preview by default.
- R51. Any real mutation proof must target an explicit disposable or
  non-production repository or environment, never protected release state or
  production deployment state.
- R52. The replacement must inventory known active uses of `sdlc-manager`,
  `blueprint-reviewer`, `sdlc-*`, `blueprint-review`, `spec-review`, and
  `issue-review` invocations before merge, then map each to a replacement,
  retire it, or record it as an intentional break.
- R53. Mission-control mutation paths must retain dry-run or preview modes
  where the old workflow had them.
- R54. Serial degraded mode must produce separate reviewer and validator
  artifacts per role, mark consensus as serial or non-subagent consensus, and
  state independence limits in captured evidence.

---

## Key Flows

- F1. Replace the active plugin inventory
  - **Actors:** A1, A7
  - **Steps:** Port the four Saga-family plugins, remove active
    `sdlc-manager` and `blueprint-reviewer` source, update marketplace and
    validator inventory, update baseline and portability docs, and prove every
    cutover gate before deletion.
  - **Outcome:** The repo exposes the Saga-family plugin set as the active Codex
    source.
  - **Covers:** R1, R2, R3, R4, R5, R6, R7, R8, R32, R33, R34, R40, R41,
    R48, R52

- F2. Invoke generic Saga skills through namespaces
  - **Actors:** A2, A3
  - **Steps:** Install from an isolated Codex profile, verify the Saga plugin is
    visible, and invoke or otherwise prove addressability for namespaced generic
    skills.
  - **Outcome:** Source-parity names are usable in Codex without global-prefix
    renames.
  - **Covers:** R9, R10, R35, R36, R37, R42

- F3. Route lifecycle work through Saga boundaries
  - **Actors:** A3, A4, A5, A6
  - **Steps:** Saga records local state, recommends an executable backend, routes
    SDLC mutation to mission-control, routes deployment mutation to deploy, and
    records handoff or backend references.
  - **Outcome:** Saga coordinates the lifecycle without becoming the owner of
    deployment or SDLC mutation.
  - **Covers:** R12, R13, R14, R15, R16, R17, R25

- F4. Run mission-control as the SDLC successor
  - **Actors:** A4
  - **Steps:** Prepare or update issues, validate cards, move board state,
    manage labels and milestones, inspect metrics, record comments, and run
    rollout workflows.
  - **Outcome:** Current SDLC operations move from `sdlc-manager` to
    `mission-control`.
  - **Covers:** R18, R19, R20, R21, R43, R44, R53

- F5. Run deployment operations through deploy
  - **Actors:** A5
  - **Steps:** Inspect status, preview release notes or tag plans, request
    explicit confirmation, then perform tag promotion, rollback, hotfix, or
    release-state mutation when approved.
  - **Outcome:** Deployment mutation is centralized in `deploy` with preview and
    confirmation gates.
  - **Covers:** R22, R23, R24, R25, R44, R50, R51

- F6. Execute team protocol with and without subagents
  - **Actors:** A6
  - **Steps:** Build the team structure, choose reviewers and validators, use
    Codex subagents when available, fall back to serial execution when not, and
    capture evidence for reviewer consensus and gates.
  - **Outcome:** `team-execution` remains usable in Codex even without custom
    agents.
  - **Covers:** R26, R27, R28, R29, R30, R31, R38, R45, R46, R54

- F7. Prove the replacement in an isolated Codex profile
  - **Actors:** A1, A2, A7
  - **Steps:** Install the replacement in an isolated profile, verify the active
    plugin set, run representative skill flows for each new plugin, verify
    namespaced invocation, and confirm generated state stays in approved
    Codex-local paths.
  - **Outcome:** The replacement proves actual Codex usability, not only
    manifest visibility.
  - **Covers:** R35, R36, R37, R47, R49

---

## Acceptance Examples

- AE1. Old plugins are hard-deleted
  - **Covers R1, R2, R3, R32, R48, R52.**
  - **Given:** The replacement branch is ready for validation.
  - **When:** Repo validation checks plugin directories, marketplace inventory,
    expected plugin inventory, and known active uses of the old plugin names.
  - **Then:** `sdlc-manager` and `blueprint-reviewer` are absent from active
    inventory only after required cutover gates pass, known uses are mapped or
    retired, and the four Saga-family plugins are present.

- AE2. Old skill names are not active
  - **Covers R4, R39, R40.**
  - **Given:** A user previously invoked `sdlc-board` or `blueprint-review`.
  - **When:** They read the replacement migration note.
  - **Then:** The note maps the old capability to the new owner without
    preserving the old skill as an alias or warning shim, and the mapping is
    reachable from normal install or usage docs.

- AE3. Saga generic skills are namespace-addressable
  - **Covers R9, R10, R35, R36, R37, R42.**
  - **Given:** The replacement is installed in an isolated Codex test profile.
  - **When:** Codex lists or invokes Saga skills with plugin namespaces.
  - **Then:** Generic source-parity names such as `saga:plan`, `saga:work`, and
    `saga:brainstorm` are visible or invocable without mutating the default
    Codex profile; if namespace invocation fails, the replacement does not
    merge.

- AE4. Claude-only backend is not offered in Codex
  - **Covers R15, R16.**
  - **Given:** Saga recommends execution backends during a Codex session.
  - **When:** The operator sees the backend choice.
  - **Then:** `inline` and `team-execution` are available choices, and
    `cc-workflows-ultracode` is not offered as executable.

- AE5. Mission-control replaces SDLC operations
  - **Covers R18, R19, R20, R21, R41, R43, R44, R53.**
  - **Given:** A workflow previously handled by `sdlc-manager` is still part of
    Infiquetra SDLC operations.
  - **When:** The replacement capability map is reviewed.
  - **Then:** The workflow has a mission-control owner or is explicitly recorded
    as removed from active scope, and any GitHub write path has preview and
    confirmation gates under the declared authentication model.

- AE6. Deploy mutation is gated
  - **Covers R22, R23, R24, R25, R44, R50, R51.**
  - **Given:** An operator asks deploy to mint or promote a tag.
  - **When:** The action would mutate GitHub, release, tag, or deployment state.
  - **Then:** Deploy presents preview or dry-run evidence and requires explicit
    confirmation before mutation under the declared authentication model; any
    validation mutation uses disposable or non-production targets.

- AE7. Team-execution degrades without subagents
  - **Covers R26, R27, R28, R29, R30, R38, R45, R46, R54.**
  - **Given:** Codex subagents are unavailable in the test environment.
  - **When:** `team-execution` runs a representative protocol check.
  - **Then:** It reports degraded mode and still applies reviewer, validator,
    evidence, dissent-recording, and main-thread verification gates through
    serial execution while marking the consensus as serial and limited.

- AE8. Runtime state uses Codex paths
  - **Covers R11, R17, R31, R49.**
  - **Given:** Saga or team-execution writes local runtime state.
  - **When:** The state path is inspected.
  - **Then:** New active state is under `.codex/saga/` or
    `.codex/team-execution/`, not `.claude/...`, and the state path is
    protected from accidental secret or evidence leaks.

- AE9. Each new plugin proves actual Codex use
  - **Covers R6, R7, R8, R33, R34, R35, R36, R37, R47.**
  - **Given:** The replacement is installed in an isolated Codex profile.
  - **When:** Validation runs representative skill flows for `saga`, `deploy`,
    `mission-control`, and `team-execution`.
  - **Then:** Each plugin can load its references, reach bundled scripts or
    dry-run paths where applicable, and operate without mutating the default
    Codex profile.

---

## Success Criteria

- The active plugin inventory contains the four Saga-family plugins and no
  active `sdlc-manager` or `blueprint-reviewer`.
- Repo validation, manifest validation, unit tests, and script smoke checks pass.
- An isolated Codex test profile proves new plugin discovery, namespaced skill
  invocation, and representative skill flow execution for each new plugin.
- Migration notes clearly map old capabilities to new owners without preserving
  old aliases.
- A known-use inventory maps or intentionally retires active old plugin and skill
  invocations before hard deletion.
- Deploy and mission-control mutation paths require preview or dry-run evidence,
  declared authentication boundaries, and explicit confirmation.
- Team-execution proves both subagent-preferred behavior and no-subagent
  degraded behavior with preserved reviewer, validator, evidence, dissent, and
  main-thread verification gates.
- Active docs and skills use Codex runtime state paths rather than Claude
  runtime state paths.
- Saga and team-execution local state paths are protected from credential,
  secret, and sensitive operational-data leakage.

---

## Scope Boundaries

Deferred for later:

- Custom-agent sidecar installer or generator for `.codex/agents/`.
- Reintroducing aliases or warning skills for old `sdlc-*` or review skill
  names.
- Adding a new Codex-specific broad-fanout backend to replace
  `cc-workflows-ultracode`.
- Publishing beyond the repo-local or isolated-profile validation path.

Outside this replacement:

- Keeping `sdlc-manager` or `blueprint-reviewer` as active Codex plugins.
- Treating Claude command files or agent files as active Codex plugin runtime
  surfaces.
- Mutating the user's default Codex profile during validation.
- Letting Saga own deployment mutation or SDLC mutation directly.

---

## Dependencies And Assumptions

- Codex plugin namespaces can make source-parity generic skill names usable in
  practice; the isolated profile proof exists to validate this assumption, and
  failure blocks merge.
- Codex subagent tools may be unavailable in some sessions; team-execution must
  treat that as degraded mode, not a fatal missing dependency.
- Mission-control can preserve the SDLC behavior that still matters from
  `sdlc-manager`, as defined by the frozen capability map.
- Deploy can safely expose real mutation behavior only with confirmation and
  dry-run or preview evidence.
- Hard deletion is acceptable only after migration notes, frozen parity,
  validation, confirmation gates, and strict Codex proof replace compatibility
  shims.

---

## Outstanding Questions

Deferred to planning:

- The exact file moves, script rewrites, test names, and validator structure.
- The exact migration-note location and wording.
- The exact Codex visibility command sequence for the isolated profile.
- The exact isolated `CODEX_HOME` profile name or path for validation.
- The mission-control mapping inventory for existing `sdlc-manager` behavior.
- Representative deploy mutation checks that avoid production or protected
  release state.
- The minimal representative `team-execution` no-subagent degraded-mode
  scenario.
- The exact GitHub auth scopes and environment separation used by deploy and
  mission-control.
- The concrete data classes allowed in `.codex/saga/` and
  `.codex/team-execution/` state.
- The representative end-to-end Codex skill flow for each new plugin.

---

## Sources

- `docs/ideation/2026-06-06-codex-saga-port-ideation.md`
- `docs/brainstorms/2026-05-27-codex-plugin-repo-requirements.md`
- `README.md`
- `scripts/validate_codex_plugins.py`
- `docs/portability/matrix.md`
- `infiquetra-claude-plugins` source plugin `plugins/saga`
- `infiquetra-claude-plugins` source plugin `plugins/deploy`
- `infiquetra-claude-plugins` source plugin `plugins/mission-control`
- `infiquetra-claude-plugins` source plugin `plugins/team-execution`
- https://github.com/EveryInc/compound-engineering-plugin
