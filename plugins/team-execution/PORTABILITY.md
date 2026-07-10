# team-execution Portability Notes

## Source

- Source plugin: `team-execution`
- Source commit: `16de95c82ccb2ed80d7f11018e1c2e8247a80a7f`
- Port status: Codex-native proof port

## Current Port Contract And Target Identity

The approved 2026-07-10 cycle freezes upstream `team-execution` changes inside
`9470edca65b1db06d2f7562eeb2d5a9e48c34dec..38742ece89880a6b140be237edad6d3f13c97b54`
and records every treatment in `../../docs/portability/ports/2026-07-10-saga-07517.json`.
`team-execution` `2.3.0` remains the only active Codex workflow package during development.

The canonical target is the unpublished `verified-workflows` `1.0.0` package. It will own DAGs,
logical roles, execution classes, validators, gates, and receipts. Team Execution remains source
lineage and a centralized legacy-read alias after cutover; this U1 note does not claim that the new
package, five profiles, hooks, installed-state migration, or release proof exists yet.

## Codex Port Shape

This port keeps the portable reviewer, validator, consensus, and evidence rules from
the source plugin. It does not keep active Claude command directories or Claude
markdown agent definitions. The full source agent roster is represented as
managed Codex TOML definitions under `agents/*.toml`; `sync_codex_agents.py`
installs them into `~/.codex/agents` without overwriting unmanaged local agents.
Runtime behavior is exposed through Codex skills and package-local scripts.

The active state root is repo-local `.codex/team-execution/` only when that path is ignored or
otherwise protected from commits. The user-local fallback is
`~/.codex/team-execution/state/<repo>/`.

## Runtime Modes

- `delegated`: used when Codex subagents are available and the task is safe to delegate.
- `serial`: used when subagents are absent, unsafe, or backpressured. Serial mode records
  per-role reviewer and validator artifacts and labels consensus as serial with independence
  limits.

Subagents never authorize mutation. The main thread owns final verification, confirmation gates,
state writes, and the completion decision.

## Agent Model Mapping

Codex agent TOML records `model_reasoning_effort`. Claude `opus`, `sonnet`, and
`haiku` source tiers are preserved as lineage comments and mapped to Codex model
hints for team-execution dispatch code that can supply spawn-time overrides.
Direct per-agent model pinning is intentionally not required by the checked
Codex TOML surface.

## Retired Source Behavior

The source display setup and host-specific command entrypoints are lineage only in this repo. The
Codex port replaces display-pane behavior with evidence grouping and bounded delegation notes.

## 2.3.0 Additions (2026-07-06 Port Cycle)

Ported from Claude window `b30e0f2..9470edc`: the artifact-pointer protocol (round-trip a
pointer to an external artifact; a pointer to a missing target is a typed failure), resident-
worker required-evidence-absence handling (`missing-output` vs. `skipped-by-config` distinguished
and excluded from consensus rather than fabricated as N/A votes), and adoption of fleet-core's
tier/effort resolution for the managed agent roster in place of the previously hard-coded
`TEAM_EXECUTION_MODEL_HINTS` table. `test_agent_tier_sync.py` guards the three-way agreement
between the roster TOML, the fleet-core palette, and the validator's derived hints. Claude
Workflow/`TeamCreate` backends remain lineage-only negative-gated surfaces (not executable here).
