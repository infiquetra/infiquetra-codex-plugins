# Codex V2 Orchestrated Execution Work Session

## Status

U1 is complete. The frozen Claude lineage, Codex 0.145.0 capability contract, current-host baseline, isolated profile preflight, and mandatory classification gate are recorded. The isolated live receipt remains blocked because two device-auth attempts expired without browser authorization; no capability was promoted from source-confirmed to runtime-supported.

## U1: Freeze Lineage And Establish The Runtime Contract

- Froze Claude source range `9470edca65b1db06d2f7562eeb2d5a9e48c34dec..46fefb6f17f0c9d0d63858978536d3369ab57dfe` over the reviewer and validator registries.
- Classified both source rows as Codex adaptations owned by U6. External advisory output remains opaque, non-gating input under root authority.
- Added the schema-r3 Codex 0.145.0 snapshot. It separates the active V1 host state from source-confirmed V2 request, response, and rollout-readback contracts.
- Corrected host capture for canonical concurrency, V2 total-thread semantics, effective project feature state, and Codex's boolean-V2 defaults (`hide_spawn_agent_metadata=true`, `non_code_mode_only=true`).
- Removed the obsolete V1 managed-profile counter from the active capability capture so the current cutover surface contains no legacy workflow marker.
- Added a bounded V2 proof harness that requires a separate isolated login, source-identical installed profiles, `session_meta` plus `turn_context` runtime receipts, exact role/model/effort/provider/permission readback, root-child permission equality, and root-only context exclusion for `fork_turns=none`.
- Installed the five current profiles into the isolated proof home through the transactional sync command. This did not mutate the active Codex home.
- Recorded `auth-unavailable` proof after two isolated device-auth timeouts. The complete runtime matrix and any runtime-supported claims remain hard U8 work.
- Generalized port contracts for schema version 2, custom frozen refs, dedicated evidence tags, and digest-bound historical capability preimages without changing the historical `2026-07-10` manifest.
- Deferred all three candidate plugin versions to U8.

## Key Decisions

- Codex 0.145.0 reapplies the parent turn's permission profile after loading a named profile. Strict child work therefore requires a permission-homogeneous parent; a child profile cannot widen or narrow the parent turn independently.
- Spawn request fields and tool responses are not runtime authority. Runtime authority is the combined child `session_meta` and `turn_context` receipt.
- Rollout `history_mode` is storage metadata, not proof of `fork_turns` isolation. The probe uses a root-only marker that must be absent from the child rollout.
- Hooks remain observation surfaces only and cannot substitute for missing V2 readback.
- U1 may truthfully record a blocking probe, but U8 cannot version, merge, install, or cut over until the authenticated full V2 matrix passes.

## Files

- `scripts/capture_codex_runtime_capabilities.py`
- `scripts/prove_verified_workflows_runtime.py`
- `scripts/port_contract.py`
- `docs/validation/codex-runtime-capability-snapshot.json`
- `docs/validation/codex-runtime-capability-snapshot.schema-r3.json`
- `docs/validation/codex-v2-orchestration-baseline.json`
- `docs/validation/codex-v2-orchestration-runtime-proof.json`
- `docs/portability/ports/2026-07-24-codex-v2-orchestration.json`
- `docs/portability/ports/2026-07-24-codex-v2-orchestration-version-policy.json`
- `docs/portability/classifications/2026-07-24-codex-v2-orchestration.md`
- Focused tests under `tests/` for capture, schema, proof, and port-contract behavior.

## Checks

- `python3 scripts/port_contract.py validate --manifest docs/portability/ports/2026-07-24-codex-v2-orchestration.json --stage classification`
- `python3 scripts/port_contract.py verify-source --manifest docs/portability/ports/2026-07-24-codex-v2-orchestration.json --source-repo ../infiquetra-claude-plugins`
- `python3 scripts/capture_codex_runtime_capabilities.py --check --session-facts-json <allowlisted-current-session-facts>`
- `python3 scripts/prove_verified_workflows_runtime.py --live --codex-home <isolated-home> --authenticated-isolated-home --pretty` -> `auth-unavailable`
- Focused pytest: 120 passed.
- Focused Ruff: passed.
- Repository validator and generated inventory checks: passed.
- `git diff --check`: passed.

## U2: Publish The Six-Profile And Role Contract

- Added the exact six underscore profile IDs: `review_max`, `review_high`, `work_high`, `test_medium`, `scan_low`, and `monitor_low`.
- Made profile policy direct and closed: model, effort, workspace ceiling, and external boundary are resolved without an execution-class or model-catalog fallback.
- Added `work_high` as the explicit Sol/high escalation from `test_medium`; Ultra remains unavailable to child profiles.
- Reduced the role registry to the 25 maintained role lenses, direct profile mappings, compact result-schema references, and risk-based assurance policy.
- Made `devils-advocate-reviewer` the one required independent reviewer. Every additional reviewer is selected only by a concrete risk trigger.
- Replaced protected-evidence result vocabulary on the generated profile surface with `assignment-result.v1` and its reviewer extension, `reviewer-result.v1`.
- Generated byte-identical maintained and project-discovery profile copies without mutating the active user profile.
- Updated the capability snapshot, diagnostic proof, isolated auth-unavailable proof, portability binding, and legacy-token inventory for the six-profile state.

## U2 Checks

- Focused pytest: 144 passed.
- Focused Ruff: passed.
- Profile rendering and isolated sync dry-run: passed.
- Port classification and frozen-source verification: passed.
- Repository validator and legacy inventory check: passed.
- `git diff --check`: passed.

## U3: Compile The Compact Workflow Contract

- Replaced the 18-column evidence parser and intent emitter with a pure three-table compiler for assignments, blocking checks, and external actions.
- Added exact KTD3 grammars for dependencies, parents, bounded context, profile/model/effort agreement, writes, ordered fallbacks, blocking checks, and fixed `non-gating` external authority.
- Added acyclic graph, declared-parent, root-only Git, independent fresh-root reviewer, fallback-boundary, and concurrent write-overlap validation.
- Canonicalized rows and unordered cells into one contract digest, then bound that digest to an explicit approved plan revision. Material edits now fail as a stale approval binding.
- Emitted root-owned V2 launch specifications only. The compiler stores no runtime status and creates no subjects, snapshots, intents, receipts, or second task tree.
- Reworked the feasibility review to require Codex V2 named-profile, bounded-context, and runtime-readback capability fields without claiming runtime proof.
- Updated the workflow protocol and review skill to describe the compact V2 contract.

## U3 Checks

- Compiler and feasibility pytest: 36 passed.
- Focused Ruff: passed.
- Repository plan compiled deterministically and returned `ready` against the U1 capability snapshot.
- Repository validator and legacy inventory regeneration: passed.
- `git diff --check`: passed.

## U4: Make Native V2 Runtime Results Authoritative

- Replaced the diagnostic protocol fixture with a closed parser and validator over Codex V2 `session_meta` plus `turn_context`.
- Bound strict work to the exact canonical agent path, configured profile, model, effort, provider, permission, sandbox, and V2 mode; requested fields, profile bytes, messages, and hooks cannot satisfy the receipt.
- Added undeclared-descendant and worker-Git-command rejection while keeping messages coordination-only.
- Added closed `assignment-result.v1` and `reviewer-result.v1` validation, including changed-path ownership, check/finding types, reviewer exclusions, denominator, and arithmetic.
- Added the lightweight pre/post workspace audit over HEAD, branch, index, refs, local config, hooks, and porcelain-v2 paths. Sequential writers work without native attribution; concurrent writers require it.
- Added one owner-controlled, identity-guarded, atomically replaced run record. Same-attempt restoration preserves the path; retry, remediation, and revalidation require a fresh path and classified partial edits.
- Removed V1 and hook-attestation instructions from the active run and selector skills.

## U4 Checks

- Native runtime, result, run-record, workspace-audit, compiler, feasibility, profile, and role pytest: 83 passed.
- Focused Ruff: passed.
- Repository validator and legacy inventory regeneration: passed.
- `git diff --check`: passed.
- Authenticated isolated strict-worker and fresh-reviewer runtime execution remains unclaimed because the isolated home is not logged in; it stays part of the blocking U8 matrix.

## Next Step

Execute U5: reduce assurance to deterministic checks, independent reviewer scoring, root-adopted findings, and at most three shared remediation rounds.
