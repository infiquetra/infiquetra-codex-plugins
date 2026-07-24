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

## Next Step

Execute U2: add `work_high`, publish the exact six-profile contract, and map all 25 maintained roles to underscore profile IDs without mutating the active user profile.
