---
date: 2026-05-27
topic: codex-plugin-strategy
focus: infiquetra-codex-plugins and cross-tool plugin porting
mode: repo-grounded
---

# Ideation: Codex Plugin Strategy

Status: Saved and ready for brainstorming handoff.

## Topic

Whether to create `infiquetra-codex-plugins`, how to port useful Claude Code plugins
to Codex, and how to avoid accidental drift while allowing tool-specific divergence.

## Grounding

- Workspace currently has `infiquetra-claude-plugins` and
  `infiquetra-antigravity-plugins`; no `infiquetra-codex-plugins` directory exists.
- Claude plugin repo has 16 plugins. Antigravity has 15 and omits `redis-channel`.
- Codex already sees five Infiquetra plugin bundles locally:
  `blueprint-reviewer`, `home-lab-ops`, `python-toolkit`, `sdlc-manager`, and
  `unifi`.
- Codex native plugin scaffolding uses `.codex-plugin/plugin.json`, optional
  `skills/`, `.mcp.json`, `.app.json`, assets, and marketplace metadata.
- Claude and Codex both center skills as reusable instruction/script/resource
  packages, but plugin packaging, orchestration, commands, agents, hooks, and
  marketplace semantics differ by host.
- `team-execution` is the clearest non-portable example: the Claude version relies
  on `TeamCreate`; Codex and Antigravity need a native redesign or an explicit
  unsupported status.
- The user clarified that separate repos are acceptable. The strategic problem is
  not repo count; it is distinguishing intentional divergence from accidental drift.

## Topic Axes

1. Repository topology
2. Plugin portability classification
3. Shared core versus host adapter
4. Codex MVP scope
5. Drift detection and verification

## Ranked Ideas

### 1. Capability Matrix Before Repos

**Axis:** Plugin portability classification

Track each plugin per host as `native`, `adapted`, `skill-only`, `blocked`, or
`not worth porting`. This makes missing or different plugins explainable without
turning plugin counts into the health metric.

**Basis:** direct: Claude has 16 plugins, Antigravity has 15, Codex already sees
five Infiquetra bundles locally, and `team-execution` depends on Claude-specific
`TeamCreate` behavior.

**Rationale:** `team-execution` and `redis-channel` should not be treated the same
as `python-toolkit` or `blueprint-reviewer`. Some absences are design decisions.

**Downsides:** Adds one more registry to maintain.

**Confidence:** 95%

**Complexity:** Low

**Status:** Unexplored

### 2. Codex Repo As Curated Native Adapter

**Axis:** Repository topology

Create `infiquetra-codex-plugins`, but define it as a curated Codex-native adapter
repo, not a mirror of `infiquetra-claude-plugins`.

**Basis:** direct: there is no local `infiquetra-codex-plugins` directory, while
Codex native scaffolding expects `.codex-plugin/plugin.json` and Codex marketplace
metadata.

**Rationale:** Initial MVP should likely start with the five bundles Codex already exposes:
`blueprint-reviewer`, `home-lab-ops`, `python-toolkit`, `sdlc-manager`, and `unifi`.

**Downsides:** Creates a third repo surface, so it needs explicit scope control.

**Confidence:** 85%

**Complexity:** Medium

**Status:** Unexplored

### 3. Portable Core, Native Adapter

**Axis:** Shared core versus host adapter

Treat `SKILL.md`, references, scripts, rubrics, fixtures, and shared docs as the
portable core. Treat manifests, commands, agents, MCP/app wiring, install docs, and
orchestration flow as host adapters.

**Basis:** external: OpenAI, Anthropic, and Google docs all center skills as a
portable unit, while local Codex, Claude, and Antigravity manifests differ.

**Rationale:** This lets repos differ without losing the shared intent of a plugin.

**Downsides:** Requires discipline to avoid making the shared core too abstract.

**Confidence:** 90%

**Complexity:** Medium

**Status:** Unexplored

### 4. Intentional Divergence Ledger

**Axis:** Drift detection and verification

For every plugin that exists in more than one host, add a small `PORTABILITY.md` or
metadata file listing:

- shared source or lineage
- intentional host-specific differences
- unsupported host capabilities
- validation commands
- last verification date
- revisit trigger

**Basis:** direct: the Antigravity port contains stale Claude-oriented spec text,
but some differences, such as `team-execution`, are legitimate.

**Rationale:** This turns reviews from "why are these different?" into "does this difference match
the declared boundary?"

**Downsides:** Easy to let the ledger go stale unless CI checks it.

**Confidence:** 90%

**Complexity:** Low

**Status:** Unexplored

### 5. Team Execution As Redesign, Not Port

**Axis:** Plugin portability classification

Treat `team-execution` as a family of related host-native products:

- Claude: `TeamCreate` and Claude agent-team handoff.
- Codex: redesign around available Codex multi-agent/subagent primitives and Codex
  plan/default-mode behavior.
- Antigravity: redesign only if it earns its cost; otherwise explicitly mark as
  unsupported or experimental.

**Basis:** direct: the Claude `team-execution` flow relies on `TeamCreate`, tmux
display assumptions, Claude settings, and Claude agent-team handoff rules.

**Rationale:** This plugin should become the test case for honest divergence.

**Downsides:** Higher effort than a manifest port; may produce different UX per host.

**Confidence:** 95%

**Complexity:** High

**Status:** Unexplored

### 6. Drift Validator

**Axis:** Drift detection and verification

Add checks that detect accidental drift:

- stale platform names in docs
- wrong marketplace/plugin paths
- invalid host manifests
- broken relative references
- plugin inventory differences not listed in the matrix
- Claude-only primitives leaking into Antigravity/Codex docs

**Basis:** direct: the current Antigravity `docs/PLUGIN_SPEC.md` still describes the
Claude marketplace.

**Rationale:** This would have caught the current Antigravity spec text that still describes the
Claude marketplace.

**Downsides:** Needs allowlists so intentional divergence does not fail every check.

**Confidence:** 85%

**Complexity:** Medium

**Status:** Unexplored

### 7. Port Recipes Before Generators

**Axis:** Codex MVP scope

Start with per-plugin port recipes instead of a full generator. A recipe should say
what copies, what transforms, what is rewritten, what is unsupported, and how to
verify the target in the real tool.

**Basis:** reasoned: the current Antigravity port shows hand-copy drift, but a
generator created too early may encode the wrong portability boundary.

**Rationale:** After two or three recipes stabilize, generate the boring pieces: manifests,
marketplace entries, inventory docs, and stale-word checks.

**Downsides:** Slower than jumping directly to automation.

**Confidence:** 80%

**Complexity:** Low

**Status:** Unexplored

## Rejected Or Lower-Priority Ideas

| # | Idea | Reason Rejected |
|---|------|-----------------|
| 1 | Full one-repo-for-everything monorepo | Too likely to hide real host differences behind a shared tree. |
| 2 | Three fully hand-maintained repos with no matrix | Acceptable topology, weak process; it will drift silently. |
| 3 | Bulk port all Claude plugins to Codex first | Premature; Codex already proves a smaller high-fit set. |
| 4 | Treat Antigravity as an equal peer target | Not justified by current user value; keep it selective. |

## Suggested Next Workflow

Use `ce-brainstorm` on one selected idea before planning. Best next subject:

`Codex-native adapter repo and portability matrix for Infiquetra plugins`

That should define the repo shape, plugin classification table, MVP plugin list,
and the first port recipe before any scaffolding happens.
