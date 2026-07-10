# Doc Review Round 3: Codex Plugin Model, Execution, and Upstream Modernization Plan

All actionable P0-P3 findings were fixed in place, and the materially amended plan is ready for operator approval.

## Applied Fixes

Eighteen readiness findings were resolved from live repository, frozen-source, current-runtime, and official Codex evidence.

| ID | Priority | Status | Finding | Applied fix |
|---|---|---|---|---|
| DR3-01 | P1 | FIXED | The plan still treated Codex `7889025` as current even though `origin/main` now carries Saga `0.65.0` behavior. | Split historical plan base from approved execution base and required a complete Codex drift-preservation inventory. |
| DR3-02 | P1 | FIXED | The claimed 156-file Claude delta omitted the pathspec needed to distinguish it from the unrestricted 333-file range. | Pinned `plugins/fleet-core`, `plugins/saga`, `plugins/team-execution`, and `tests` as the only source pathspecs and made drift fail validation. |
| DR3-03 | P1 | FIXED | R20 required a completed port manifest before U1 could implement the manifest tooling, and it conflated planned evidence with verified evidence. | Made U1 the narrow bootstrap exception and added `classification`, `unit`, and `cutover` validation stages with explicit row-state transitions. |
| DR3-04 | P1 | FIXED | R5 required every role to select a model class while U3 also allowed deterministic validators with no model. | Defined closed `agent-lens` and `deterministic-validator` kinds; only agent-lenses select classes, while deterministic roles bind commands and evidence schemas. |
| DR3-05 | P1 | FIXED | Putting compatibility mappings inside Verified Workflows would force Saga to import another independently installed plugin or duplicate aliases. | Moved the one old/new vocabulary registry to fleet-core and required both consumers to load it through their existing shims. |
| DR3-06 | P1 | FIXED | `workflow_dispatch.py` could be read as a Python launcher even though only the Codex host can call native spawn, follow-up, and wait controls. | Made the script a deterministic DAG/intent interpreter and the `verified-workflows:run` skill plus root thread the sole runtime adapter. |
| DR3-07 | P1 | FIXED | U9 could not remove the legacy source while leaving the active marketplace pointed at it, but activating the unfinished replacement would violate release-last sequencing. | Permitted a temporary dual-source development state with only Team Execution marketplace-active; U8 atomically removes the old source and activates the new entry. |
| DR3-08 | P1 | FIXED | A fresh isolated home could prove installation but not old-to-new migration or rollback. | Added separate clean-home and seeded-migration lanes, including exact seeded rollback before real-profile mutation. |
| DR3-09 | P1 | FIXED | The committed “sanitized” cutover artifact was also expected to contain exact trust/config restoration material. | Split exact restoration bytes into a protected uncommitted rollback bundle and limited committed proof to sanitized relative inventories and hashes. |
| DR3-10 | P2 | FIXED | Role kind and independence choices were left to implementation preference. | Defaulted current roles to agent-lenses, defined the full-behavior test for deterministic conversion, set preferred independence as the compatibility default, and allowed risk-only elevation to required. |
| DR3-11 | P2 | FIXED | The runbook could change without a version update, and rerunning `init` could destroy completed classifications. | Bound the runbook SHA-256, added structural tests, and made manifest refresh require an explicit operation plus expected prior digest. |
| DR3-12 | P2 | FIXED | Isolated live proof did not say how authentication was obtained and could encourage copying the default profile's credentials. | Required separately authenticated isolated homes or explicit operator login and prohibited reading, copying, linking, printing, or persisting default auth material. |
| DR3-13 | P2 | FIXED | “Byte-identical round trip” conflicted with read-old/write-new serialization. | Replaced it with semantic legacy parsing, unchanged original checksums, and canonical-only new ticks. |
| DR3-14 | P2 | FIXED | An identifier-less Goal result could leave `continuation_mode=goal` with no durable reference. | Required both mode and reference to remain in turn state unless a successful Goal result returns a stable identifier. |
| DR3-15 | P2 | FIXED | `scan-low` and `monitor-low` shared model/effort without documenting why both profiles exist. | Added intended tool/mutation boundaries and made their distinction explicit while retaining U4 runtime attestation. |
| DR3-16 | P3 | FIXED | The port contract requirement was not named by every source-consuming implementation unit. | Added R20 and a unit-stage manifest gate to U2-U7 and U9, with cutover coverage in U8. |
| DR3-17 | P3 | FIXED | The plan still routed to this review and contained long generated paragraphs that violated Saga formatting guidance. | Marked round three reviewed, routed to explicit operator approval, and split narrative paragraphs to the shared formatting contract. |
| DR3-18 | P3 | FIXED | Historical review artifacts still routed readers to round two after the material round-three amendment. | Preserved their findings but marked rounds one and two superseded and linked both to the current round-three verdict. |

## Readiness Summary

PASS: the plan can now drive implementation without inventing a baseline, role policy, plugin dependency, native-agent bridge, port-evidence lifecycle, or rollback strategy.

The corrected control flow keeps human guidance and machine enforcement distinct:

```text
Codex plan base ----> execution-base preservation inventory ---+
                                                               |
Claude frozen range -> exact four-pathspec source inventory ----+--> staged JSON contract
                                                               |       |
human port runbook -- version + SHA-256 ------------------------+       +--> U2-U9 unit gates
                                                                       +--> U8 cutover gate
```

## Review-Result Contract

The durable result is a clean document verdict with operator approval still required before work begins.

- Target: `docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`
- Reviewed revision: working tree at repository `HEAD` `fbd400183c2de70115cbaadc4c301b03d759527d`; reviewed plan blob `a3391d46f0b1791f83225797f60dfa5be5192ead`
- Blocked status: NOT BLOCKED by document findings; explicit operator approval and KTD14 ownership preflight remain lifecycle gates
- Classification: implementation plan
- Review type: readiness-skeptic plus compatibility, security, operations, current Codex capability, portability, and deployment/cutover scrutiny
- Formal rubric phase: none; plan artifacts do not map to the idea, issue, or spec rubric phases
- Linked origin: `docs/plans/2026-06-27-port-recent-claude-plugin-updates.md`
- Linked Saga: `task-port-recent-claude-plugin-updates`
- Prior reviews: round one and round two remain historical and are superseded by this artifact
- Review artifact: `docs/reviews/2026-07-10-codex-plugin-model-execution-modernization-plan-doc-review-r3.md`
- External review panel: not requested; skipped
- Operator override: none

## Verification Evidence

The current evidence supports the corrected decisions while leaving runtime claims to the implementation gates.

- Codex `HEAD` and `origin/main` are `fbd4001`; the historical `7889025` plan base is an ancestor. The full Codex drift contains 33 paths, 13 of which intersect the port's active source/inventory surfaces, and current Saga is `0.65.0`.
- The focused Claude command returns exactly 156 paths split 12 fleet-core, 63 Saga, 10 Team Execution, and 71 tests; the unrestricted range returns 333. Frozen target `38742ec` remains reachable from current Claude `HEAD` `46fefb6`, and its manifests are fleet-core `0.8.4`, Saga `0.75.17`, and Team Execution `2.14.3`.
- Live Codex is `0.144.1`; the bundled catalog has eight rows including Sol, Terra, Luna, scalar efforts through `max`, and Ultra. Local config selects Sol/max with `agents.max_threads=6` and `agents.max_depth=1`.
- The active collaboration tool schema exposes task name, message, and fork context but no direct per-child profile/model/effort/sandbox selector. The plan therefore treats requested choices as preferences until hook/profile evidence proves selection.
- Current official Codex guidance supports Sol/Terra/Luna task matching, Max versus Ultra, custom agent `model`, `model_reasoning_effort`, and `sandbox_mode`, root-owned spawn/steer/wait behavior, inherited parent permissions, SubagentStart/Stop identity/model fields, `PLUGIN_DATA`, and explicit hook trust: [models](https://learn.chatgpt.com/docs/models), [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), [hooks](https://learn.chatgpt.com/docs/hooks). The Codex manual helper failed because its response omitted `x-content-sha256`, so the review used these direct official pages as the documented fallback.
- Requirements R1-R20 each map to at least one unit; nine stable U-IDs form an acyclic dependency graph in the recommended order; source-consuming units carry R20 stage gates.
- `PYTHONPATH=. uv run pytest -q tests/test_saga_doc_formatting.py tests/test_saga_docs_package.py tests/test_validate_codex_plugins.py`: 50 passed.
- `uv run python scripts/validate_codex_plugins.py`, `uv run python scripts/build_saga_docs_facts.py --check`, `uv run python scripts/render_saga_docs_assets.py --check`, and `git diff --check`: passed.

## Remaining Findings by Priority

No P0, P1, P2, or P3 finding remains after the safe fixes above.

## Review Artifact Path

This round supersedes the earlier readiness verdicts without rewriting them.

`docs/reviews/2026-07-10-codex-plugin-model-execution-modernization-plan-doc-review-r3.md`

## Residual Risk / Limited Evidence

The residual risks are implementation evidence, not missing document decisions.

- The current direct spawn interface may still fail to select a named custom profile. U4 must record an attested role/class receipt or truthfully retain `inline-only`/`auth-unavailable`; required-independence steps cannot pass inline.
- The current worktree contains pre-existing plan/review/journal and `.serena/project.yml` edits. After approval, `/work` must run KTD14's HEAD/dirty-path ownership preflight and pause on unresolved overlap.
- The U9 temporary dual-source state is safe only while Verified Workflows remains unpublished and absent from the active marketplace. U8 must remove the legacy source and prove one active package before release.
- Codex catalogs, hook schemas, upstream Claude, and local main can move after review. U1 refreshes and freezes both inventories, while U8 revalidates catalog, runbook, source, execution-base, install, fresh-session, and rollback evidence.
- This review proves implementation readiness, not shipped behavior. No plugin code, installation, authentication, marketplace cutover, PR, merge, or deployment was performed.
