# Codex V1 Agent Compatibility Plan

## Goal

Restore selectable named-agent model and effort controls for GPT-5.6 Sol and Terra by using the
stable MultiAgent V1 runtime until MultiAgent V2 is ready. Preserve the five existing custom-agent
profiles and make the catalog override reproducible when OpenAI changes model metadata.

## Current State

- Codex CLI 0.144.5 reports `multi_agent` stable and `multi_agent_v2` under development.
- The live model catalog assigns Sol and Terra to V2 and Luna to V1. The catalog assignment wins
  over the disabled V2 feature flag for model-selected tool schemas.
- The repository currently encodes the V2 namespace and `fork_turns` workaround as the default
  execution contract.
- `/agent` switches among spawned threads; it is not a pre-spawn custom-agent catalog.

## Key Decisions

1. Clone the complete live Codex catalog and change only Sol and Terra `multi_agent_version` values
   to `v1`. Never maintain a reduced replacement catalog.
2. Generate the override from the Codex model cache, an explicit full-catalog file, or the bundled
   catalog fallback; write UTF-8 without BOM atomically and fail loudly if target rows or the catalog
   schema drift.
3. Keep `multi_agent = true` and `multi_agent_v2 = false`. Treat V2 as an optional compatibility
   probe, not the default workflow substrate.
4. Preserve the existing custom-agent TOMLs and their model/effort mappings.
5. Keep high-assurance Verified Workflow gates opt-in. Native interactive delegation must remain
   usable without satisfying workflow attestation requirements.
6. Warn that forcing Sol/Terra to V1 may affect Ultra's automatic delegation. Ultra is unsupported
   under this workaround until separately proven.

## Implementation Units

### U1: Reproducible V1 catalog override

**Goal:** Produce and safely install an exact live-catalog clone with only the Sol/Terra runtime
selector changed.

**Files:** Fleet Core catalog utility, focused tests, Fleet Core documentation.

**Approach:** Prefer `$CODEX_HOME/models_cache.json` so a reinstall cannot read its own configured
override, fall back to the existing bounded bundled-catalog runner, and accept an explicit saved full
catalog. Validate the full JSON document, apply an allowlisted two-row transformation, write without
BOM, and support render/check/install modes with explicit paths and rollback-safe configuration
updates.

**Verification:** Unit tests cover success, idempotence, schema drift, unchanged non-target fields,
UTF-8 encoding, atomic replacement, configuration preservation, and Ultra warnings.

### U2: Stable V1 repository contract

**Goal:** Stop presenting V2-only schema behavior as the repository default.

**Files:** `.codex/config.toml`, capability snapshot, capability capture/proof scripts, Saga and
Verified Workflows operator documentation, drift tests.

**Approach:** Describe stable V1 named-profile selection and model/effort controls; retain V2 facts
only as an explicitly experimental compatibility section. Remove V2 namespace bootstrap and
full-history fork requirements from normal interactive guidance.

**Verification:** Contract tests and runtime capability tests accept the V1 schema and reject a
return to mandatory V2 defaults.

### U3: Agent selection experience

**Goal:** Give operators an explicit catalog of the five maintained agents before spawning one.

**Files:** A small reusable skill plus plugin manifest/documentation and focused structural tests.

**Approach:** Show name, purpose, model, effort, and permission intent; spawn the selected named
profile through the stable runtime; explain that `/agent` handles thread switching after spawn.

**Verification:** Plugin validation discovers the skill, and tests pin all five profile mappings
without duplicating the canonical Fleet Core policy.

### U4: Validation and delivery

**Goal:** Prove the workaround, review it, and merge it without touching unrelated user work.

**Approach:** Run focused tests, repository validation, the full suite, an isolated generated-catalog
readback, and a fresh-session V1 probe. Run the code-review gate, open a PR, merge after checks, then
return the primary checkout to clean current `main` while preserving pre-existing dirty paths.

**Verification:** Merged PR, current `origin/main` contains the commits, and the isolated worktree is
removed.

## Scope Boundaries

- Do not patch Codex binaries or installed plugin cache snapshots.
- Do not claim Ultra compatibility without a separate runtime proof.
- Do not remove custom-agent profiles or their model/effort settings.
- Do not weaken Verified Workflow gates when that workflow mode is explicitly selected.
- Do not modify unrelated local worktree files.

## Execution

Saga recommended `verified-workflow` from file and phase count. Execution is intentionally inline
because the Verified Workflows bootstrap depends on the MultiAgent V2 behavior being repaired. The
operator approved implementation through merge; focused tests, full validation, and code review remain
mandatory gates.
