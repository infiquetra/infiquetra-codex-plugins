---
date: 2026-06-06
topic: codex-saga-port
focus: Port Saga, deploy, mission-control, and team-execution from infiquetra-claude-plugins into Codex-native plugins
mode: repo-grounded
---

# Ideation: Codex Saga Family Port

## Grounding Context

This repository is explicitly a curated Codex adapter, not a mirror of
`infiquetra-claude-plugins`. The active Codex surface is
`plugins/<name>/.codex-plugin/plugin.json`, `plugins/<name>/skills/`, the
repo-local marketplace, the portability matrix, cutover gates, and
`scripts/validate_codex_plugins.py`.

The current Codex inventory is still the old baseline:
`blueprint-reviewer`, `home-lab-ops`, `python-toolkit`, `sdlc-manager`,
`unifi`, and `test-suite`. The validator hardcodes that inventory, checks the
marketplace against it, and rejects active `.claude-plugin`, `commands`, or
`agents` directories inside Codex plugin roots. The current portability matrix
also marks `team-execution` blocked because the Claude version depended on a
Claude orchestration primitive.

The Claude source has a newer "Saga family":

- `saga` is the lifecycle spine. It routes work through think, plan/execute,
  handoff, review, improve, and resume phases. Its own README keeps clear
  boundaries: `deploy` owns deployment mutation, `mission-control` owns SDLC
  issue/comment/board mutation, `team-execution` stays independent, and `saga`
  owns only the handoff envelope.
- `deploy` is a tag-promotion deployment operations plugin with ordinary Python
  CLIs around `git` and `gh` plus release/deployment state workflows.
- `mission-control` is the SDLC issue and GitHub Projects successor to
  `sdlc-manager`, with prepared issues, board schema, labels, metrics, rollout,
  and a shared `sdlc_manager.py` backend.
- `team-execution` is mostly prompt, reference, reviewer, and validator
  orchestration. It defines a two-phase plan/execution protocol, a
  `## Team Structure` plan section, reviewer consensus, validator gates, and
  nonprod automation rules.

The Every Compound Engineering repo is useful because its Codex path separates
native skills from custom agents. Their Codex README says native install handles
skills through the Codex TUI, while a companion Bun install adds custom agents
because Codex's native plugin spec does not yet register them. Their converter
therefore defaults to agents-only for `--to codex` and treats skills as
externally managed by native plugin install. That is a strong pattern, but not
a drop-in answer for Infiquetra because this repo already has curated
validation, portability, and supersession rules.

## Topic Axes

- Packaging and discovery: what Codex plugin inventory, marketplace entries,
  manifests, skill names, and sidecar artifacts should exist.
- Lifecycle boundaries: how Saga delegates to deploy, mission-control, and
  team-execution without swallowing their ownership.
- Team orchestration: how to replace Claude-specific team primitives with a
  Codex CLI usable path.
- State and artifact paths: how `.claude/saga` and `.claude/team-execution`
  state become Codex-safe, durable, and resumable.
- Validation and cutover: how to prove the new plugins work before removing
  `sdlc-manager` and `blueprint-reviewer`.

## Ranked Ideas

### 1. Stage a Supersession, Not an Immediate Deletion

**Description:** Add the Saga family as the next canonical Codex plugin set,
but treat `sdlc-manager` and `blueprint-reviewer` as superseded only after the
new family validates and installs cleanly. `mission-control` becomes the
successor to `sdlc-manager`; Saga's review flows become the successor to
`blueprint-reviewer`.

**Axis:** Packaging and discovery

**Basis:** direct: the current README, marketplace, and validator all encode
the old six-plugin inventory; direct: the Claude Saga docs say
`blueprint-reviewer` was folded into Saga while `deploy` and `team-execution`
remain standalone.

**Rationale:** Immediate removal would break the only currently validated Codex
surface. Staged supersession lets us prove the new shape, add compatibility
notes or aliases, then remove old plugins as a deliberate cutover.

**Downsides:** Temporarily increases plugin count and documentation surface.

**Confidence:** 92%

**Complexity:** Medium

**Status:** Unexplored

### 2. Make the Port Skill-First and Script-Anchored

**Description:** Convert Claude commands into Codex skills and keep deterministic
behavior in bundled scripts. Do not copy active `commands/`, `.claude-plugin`,
or `agents/` directories into Codex plugin roots. Preserve the useful Python
anchors: Saga's lifecycle helpers, mission-control's `sdlc_manager.py`, and
deploy's tag/status/release-note scripts.

**Axis:** Packaging and discovery

**Basis:** direct: this repo's validator rejects active Claude command and agent
directories; direct: Codex plugin manifests use a skills path; direct: the
Claude source already stores much of the real behavior in scripts and
references rather than command files alone.

**Rationale:** This keeps the port native to Codex and avoids a brittle
mechanical copy. It also gives validation concrete files and commands to check.

**Downsides:** Requires careful content transformation for slash-command
references, host paths, and skill invocation names.

**Confidence:** 90%

**Complexity:** High

**Status:** Unexplored

### 3. Redesign Team Execution Around Codex Subagents Plus Fallbacks

**Description:** Port `team-execution` as a Codex orchestration protocol first:
plan intake, team structure, reviewer/validator registry, consensus rules,
checks, and evidence capture. Use Codex subagents when available and allowed,
but require the skill to degrade to main-thread execution, serial batches, or
worktree-isolated handoff when subagents or custom agents are missing.

**Axis:** Team orchestration

**Basis:** direct: the Claude skill's value is the two-phase protocol, reviewer
consensus, validator gates, and nonprod safeguards; reasoned: Codex CLI sessions
can expose subagent tools, but installed custom agents are a separate concern
from native plugin skills.

**Rationale:** Trying to recreate Claude's primitive exactly is the wrong
abstraction. The portable value is the operating model: who reviews, what gates
must pass, what evidence is captured, and when deployment is allowed.

**Downsides:** Some Claude behavior becomes less automatic until custom agent
installation is solved. The skill must be blunt about degraded mode.

**Confidence:** 88%

**Complexity:** High

**Status:** Unexplored

### 4. Add an Infiquetra Agent Sidecar Installer, Inspired by Every

**Description:** Keep native Codex plugins responsible for skills. Add a
separate, explicit installer or generator for optional custom agents under
`.codex/agents/<plugin>/`, probably starting with `team-execution` reviewers and
validators plus Saga/deploy specialist agents. Treat this as an opt-in sidecar,
not as active plugin root content.

**Axis:** Team orchestration

**Basis:** external: Every's Codex path uses native plugin install for skills
and an agents-only companion install because native Codex plugins do not yet
register custom agents; direct: this repo's current validator rejects active
`agents/` directories inside plugin roots.

**Rationale:** This preserves a Codex-native plugin surface while still giving
advanced users named reviewers and validators. It also keeps sidecar cleanup and
manifesting separate from plugin validation.

**Downsides:** Adds one more install step. The repo would need clear proof that
Codex CLI can actually discover and use the sidecar agents in the user's
profile.

**Confidence:** 82%

**Complexity:** Medium-high

**Status:** Unexplored

### 5. Host-Gate the Saga Backend Contract Instead of Blindly Renaming It

**Description:** Preserve Saga's core execution choice contract, but make the
Codex offer host-aware. `inline` remains always available. `team-execution`
means the Codex team-execution protocol. `cc-workflows-ultracode` is documented
as Claude-only and omitted from Codex offers unless a real equivalent exists.
Only add a new `codex-subagents` enum if we decide it is a distinct backend
rather than an implementation detail of team-execution.

**Axis:** Lifecycle boundaries

**Basis:** direct: Saga's operator-choice spec says lifecycle chooses but
backends execute, and `cc-workflows-ultracode` is Claude Code only; reasoned:
adding a new enum too early creates migration cost before the Codex behavior is
settled.

**Rationale:** This minimizes churn in saga storage while still being honest in
Codex sessions. It also keeps execution ownership outside Saga.

**Downsides:** The old enum name may look odd in Codex-visible reference docs
unless the host-gating prose is clear.

**Confidence:** 84%

**Complexity:** Medium

**Status:** Unexplored

### 6. Port Mission-Control and Deploy Before the Full Saga Loop

**Description:** Bring over `mission-control` and `deploy` first as direct
skill-plus-script Codex plugins with read-only/status and dry-run smoke paths.
Then port Saga on top of working issue/board and deployment boundaries.

**Axis:** Lifecycle boundaries

**Basis:** direct: Saga explicitly delegates SDLC mutation to mission-control
and deployment mutation to deploy; direct: deploy and mission-control have
ordinary Python script anchors and clearer standalone behavior than the full
Saga loop.

**Rationale:** Saga is the conductor. The conductor is easier to validate after
the sections it points at already work in Codex.

**Downsides:** Users do not get the complete lifecycle on the first increment.

**Confidence:** 87%

**Complexity:** Medium

**Status:** Unexplored

### 7. Treat Validation and Codex CLI Visibility as Product Requirements

**Description:** Update the repo validator, portability matrix, provenance,
marketplace, and cutover docs as part of the port, not as cleanup. Add a Codex
visibility proof: marketplace registration, TUI install when required, skill
visibility, `plugin-creator` manifest validation, repo validator, unit tests,
dry-run script smoke, and a missing-agent degraded-mode check.

**Axis:** Validation and cutover

**Basis:** direct: this repo already treats validation and cutover as first
class; direct: the user specifically wants the result usable by Codex CLI.

**Rationale:** A port that exists in files but cannot be installed, discovered,
or safely invoked in Codex has not met the goal.

**Downsides:** Slower than just copying directories.

**Confidence:** 93%

**Complexity:** Medium

**Status:** Unexplored

## Rejection Summary

| # | Idea | Reason Rejected |
|---|------|-----------------|
| 1 | Directly run Every's converter over the Saga family and commit the output | Too blunt. Every's path is useful evidence, but Infiquetra needs curated plugin names, validation, state-path decisions, and ownership boundaries. |
| 2 | Delete `sdlc-manager` and `blueprint-reviewer` first | Risky. Those are the currently validated Codex plugins; removal should follow parity and cutover proof. |
| 3 | Collapse Saga, deploy, mission-control, and team-execution into one mega-plugin | Violates the source ownership boundaries and makes deployment and GitHub mutation harder to reason about. |
| 4 | Recreate Claude `TeamCreate` exactly | Not grounded in Codex. The value should be ported as a protocol with Codex subagent or fallback execution. |
| 5 | Keep offering `cc-workflows-ultracode` as a normal Codex backend | Incorrect host behavior. It is documented as Claude Code only and should be omitted or gracefully degraded in Codex. |
| 6 | Put converted agents inside each Codex plugin root | The current validator rejects active `agents/` directories, and native Codex plugin install does not yet handle custom agents. |
| 7 | Keep `.claude/saga` and `.claude/team-execution` as active Codex state paths | Stale host leakage. Codex-visible runtime docs should use `.codex/...` or a deliberately tool-neutral path. |
| 8 | Let Saga own deployment mutation | Violates the Claude source boundary. Deployment mutation belongs in deploy with explicit gates and rollback evidence. |
| 9 | Port only docs and skip install/visibility proof | Does not satisfy the Codex CLI usability requirement. |

## Recommended Direction

The strongest path is a staged native port:

1. First approve a brainstorm on the supersession model and skill names.
2. Then plan an implementation sequence that ports `mission-control` and
   `deploy` first, because Saga depends on their boundaries.
3. Port Saga as the lifecycle spine with host-gated execution backend offers and
   Codex-safe state paths.
4. Port `team-execution` as a Codex protocol with optional custom-agent sidecar
   support and loud degraded-mode behavior.
5. Only after validation and install proof, remove or deprecate
   `sdlc-manager` and `blueprint-reviewer`.

## Decisions Needed Before Implementation

- Skill naming: use source names under plugin namespaces, or prefix every skill
  name for direct `$skill` safety.
- State path: `.codex/saga` and `.codex/team-execution`, or a neutral
  `.agents/...` path shared across hosts.
- Team-execution runtime: skill-only fallback first, optional custom-agent
  sidecar first, or both in the first port.
- Cutover policy: keep old plugins until parity proof, or remove them in the
  same implementation PR.
- Validation policy: keep `EXPECTED_PLUGINS` hardcoded and update it, or move
  expected inventory into a generated/declared contract.

## Sources

- Current Codex repo shape: `README.md`, `scripts/validate_codex_plugins.py`,
  `docs/portability/matrix.md`
- Claude source family: `../infiquetra-claude-plugins/plugins/saga`,
  `../infiquetra-claude-plugins/plugins/deploy`,
  `../infiquetra-claude-plugins/plugins/mission-control`,
  `../infiquetra-claude-plugins/plugins/team-execution`
- Every Compound Engineering Codex pattern:
  https://github.com/EveryInc/compound-engineering-plugin
- Local clone inspected at commit:
  `bb0c9ab4ee596d546f2965222e0ec8c2a097ae53`
