---
date: 2026-08-08
topic: codex-0147-alignment
maturity: requirements-ready
---

# Codex 0.147.0 Alignment

## Summary

Align this repository's Codex plugins with Codex CLI 0.147.0. The centrepiece is that MultiAgent V2
model eligibility is one catalog fact plus two derived projections, where the repository stores a
single conflated value — which is what let the
claim "Luna is unavailable to MultiAgent V2" ossify into the validation record after it stopped being
true. Restore Luna on the two low-cost profiles behind live canaries, re-baseline the capability
snapshot, and verify the reworked turn-environment permission inheritance.

## Problem Frame

Codex 0.147.0 relaxed the gate that decides which models a MultiAgent V2 session may use. In 0.146.1
a model was admitted only if its own catalog entry said `v2`; in 0.147.0 it is admitted unless the
catalog marks it `Disabled`. Luna is catalogued `v1`, so it went from rejected to accepted.

That single predicate is load-bearing here. When the V2 cutover ran, Luna failed it, and the
contingency in the 0.145-era plan fired: remap `scan_low` and `monitor_low` to Terra. The reason was
recorded as a durable fact in `docs/validation/codex-v2-orchestration-matrix.json` and then restated
across Fleet Core policy, the profile renderer, four prose documents, and the matrix builder. None of
those restatements can notice that the underlying gate changed.

The cost is not only the price difference between Terra and Luna on two low-effort profiles. It is
that a runtime observation was stored as a permanent property, so the repository now asserts something
about Codex that Codex no longer does. The 0.147.0 release is the moment that becomes visible, and the
same shape will recur on every catalog shift unless the data model separates the facts.

Separately, 0.147.0 reworked turn-environment permissions across the whole execution path — spawn
inheritance, shell, unified execution, patching, image reads, resumed children, and capability
discovery. That rework touches the inheritance path the execution profiles depend on and has not been
exercised against this repository at all.

## Key Decisions

**One raw fact, two derived projections.** The catalog's `multi_agent_version` is the only independent
source fact. Both of the things the repository actually needs are *derived* from it by rules Codex
owns: whether a model passes the V2 explicit-model override filter (it does unless the catalog says
`Disabled`), and whether a session receives collaboration tools (a V2 root always does; a V2 child
only when its own effective model reports `v2`). Storing the projections as if they were independent
facts would repeat the original defect in a new shape. Each projection carries a versioned rule
identifier and its Codex provenance, so a future rule change is caught by classification rather than
silently mis-read.

The filter name matters: "passes the V2 explicit-model override filter" is not "may be spawned."
Provider availability, reasoning-level support, depth limits, and capacity can each still prevent a
spawn that the filter admits.

**A Luna child is a non-delegating leaf, and that is the correct shape.** Under V2, collaboration tools
reach a root regardless of model, but reach a child only when the child's own model is catalogued
`v2`. Luna children therefore cannot spawn, wait, or message. Bounded scanning and allowlisted
observation should not delegate, so the constraint matches the roles rather than limiting them. This
is a derived runtime expectation of effective model plus session position — never a permanent property
of a profile.

**`features.multi_agent_v2.subagent_developer_instructions` stays unset.** Preservation behavior only
engages when the setting is configured *and* the selected role omits its own instructions; when it is
configured, Codex replaces or clears the parent session's configurable developer-instruction fragment
across bounded forks, full-history forks, compacted histories, and cold resume. All seven maintained
profiles carry explicit developer instructions, so populating the key buys nothing and moves an
authority boundary for no gain. The narrower claim is the accurate one: it rewrites the configurable
parent fragment, not project instructions generally.

**Terra remains the fallback, not the floor.** Luna becomes the preferred model for the two low
profiles with Terra first in fallback order. A canary failure keeps Terra active without reverting the
eligibility model.

**The turn-environment permission work stays a unit inside this round.** The independent review argued
it warrants its own tracked outcome, on the grounds that it is the likeliest place a real defect
surfaces and that a native Codex defect there should halt the round. It stays in-round, carrying the
blocking stop rule in R19: any permission mismatch blocks source-ready status. Keeping it here means
the round's boundary is set by the stop rule rather than by a separate tracker.

**Portable Agent Plugin migration stays rejected.** The portable manifest auto-discovers direct-child
skills and MCP configuration but still has no custom-agent profile field, so it cannot package
`plugins/verified-workflows/agents/*.toml`. The existing decision to keep `.codex-plugin/plugin.json`
holds for the same reason it was made.

## Requirements

**Eligibility model**

R1. The repository stores the catalog's `multi_agent_version` as the single raw fact, and represents
"passes the V2 explicit-model override filter" and "receives collaboration tools" as generated
projections of it. The collaboration projection takes session position (root or child) as an input
alongside the model, because Codex's rule does.

R2. Each projection carries a versioned rule identifier and its Codex provenance, so the projection
can be regenerated and a rule change is detectable rather than silent.

R3. Fleet Core's tier palette, the capability snapshot schema, and the plugin validator consume the
projections rather than each re-deriving eligibility independently. Deriving from the raw catalog fact
is correct and expected; duplicating the derivation rule per consumer is what this forbids.

R4. The round decides whether the capability-snapshot change is a new schema revision with an
incremented integer version or a backward-compatible extension, inventories every local consumer of
the affected shape, and specifies migration and the treatment of existing artifacts. An explicit
revision is preferred so breakage is detectable rather than silent.

**Model policy**

R5. `scan_low` and `monitor_low` prefer `gpt-5.6-luna`, with `gpt-5.6-terra` first in fallback order.
Each profile is gated independently on its own canary result: a monitoring failure keeps `monitor_low`
on Terra without forcing a passing `scan_low` back. A failed or unrun canary keeps Terra preferred for
that profile.

R6. Both profiles are regenerated through the existing renderer rather than hand-edited, and the
agent-tier synchronization tests are updated to match.

R7. The non-delegating-leaf behavior of a Luna child is recorded as a derived runtime expectation of
effective model plus session position, not as a permanent property of either profile.

**Developer-instruction contract**

R8. The full key `features.multi_agent_v2.subagent_developer_instructions` is proven absent, all seven
maintained profiles are proven to retain explicit developer instructions, and the repository keeps its
boolean feature form. The inheritance semantics are recorded: unset inherits, blank clears, and
role-specific instructions win.

**Evidence and version baseline**

R9. The runtime capability snapshot is re-baselined to Codex 0.147.0.

R10. Every hard version gate accepts the new baseline: the proof runner's snapshot check, the
capability-snapshot test assertion, the orchestration-matrix test assertion, and the JSON Schema
`const` that pins `codex_cli_version` in the snapshot schema itself. The port contract's accepted
schema-version set is widened in step with whatever R4 decides, since it currently admits only
versions 1 and 2.

R11. Runtime capture records the effective approval reviewer exactly, distinguishing `user` from
`auto_review`. A `user` reviewer is necessary where command approval applies but never sufficient as
operator authority; `auto_review` disqualifies runtime approval from being read as operator approval
at all. The bound Workflow Contract or plan digest remains the positive evidence of operator approval.

R12. Runtime capture records effective model, effort, provider, permission profile, sandbox, current
directory, and workspace roots for a spawned child. Where environment identity is wanted beyond that
durable tuple, the round either authorizes an app-server harness that can capture it or drops it —
`TurnContextItem` does not persist an environment identifier, so it cannot be assumed available.

**Corrections to stale claims**

R13. Every location carrying the superseded Luna conclusion is inventoried and given one of three
dispositions: update it when it states a current operational claim; append a superseding dated entry
when it is a dated historical record that was accurate when written; or preserve it unchanged when it
is historical evidence. Dated changelog and decision entries are not rewritten — doing so would
falsify the record of what was true at 0.146.

R14. Assertions that remain true but carry a stale version label are relabelled rather than deleted —
in particular that Codex still exposes no per-child sandbox override, which holds in 0.147.0.

**Live verification**

R15. A canary proves whether a Luna child completes bounded V2 work, with separate cases for
instruction adherence, typed-result schema validity, cold resume preserving canonical child identity
and restored model and provider, and an unknown-provider negative case.

R16. The absence of collaboration tools from a Luna child is proven from the model-visible tool schema
or tool plan, not inferred from the absence of an observed collaboration call. A runtime negative
probe accompanies the schema evidence.

R17. The Luna acceptance oracle is defined before the canary runs: separate scan and monitor fixture
corpora, required recall, forbidden false negatives, typed-schema validity, a repeated-run threshold,
and the Terra comparison each stated concretely enough that two planners would build the same gate.

R18. Host-installed plugin skill references and executor-backed `skill://` resources are verified
separately, because only the latter is subject to the fail-closed sandbox-context change. Each covers
its relevant permission profiles, and each states whether denial occurs at discovery or at read and
what error is expected.

R19. The reworked turn-environment permission inheritance is exercised with a stated case matrix and
stop rule: at minimum one read-only and one workspace-write turn, multiple workspace roots, spawn
after role application, cold resume under current runtime permissions, later-turn permission updates,
and no widening beyond the parent turn. Any mismatch blocks source-ready status. Permission drift is
never resolved by a model fallback — the permission path is model-independent.

**Positive discovery proof**

R20. All ten tracked legacy manifests validate, the applicable plugin-search scopes resolve, isolated
source-plugin discovery works, and explicit and implicit routing canaries pass across the tracked
plugins. A no-change inventory does not substitute for proving discovery still works after the 0.147
skill-discovery refactor.

R21. Custom agent profiles are confirmed to still require separate synchronization, since no packaging
path carries them.

**Negative inventory**

R22. Changes verified as not affecting this repository are recorded as explicit no-change rows with
their evidence: the removed `codex exec --full-auto` flag, the opt-in MCP 2026-07-28 protocol, Apps,
tool-registry collision policy, symlink handling during plugin installation, and portable Agent Plugin
packaging.

**Process gates and packaging**

R23. The cycle's JSON port manifest is bootstrapped or loaded and passes its `classification` gate
before any source-derived behavior changes. This is mandatory for every refresh under the port
runbook, not optional for a version-alignment round.

R24. The port manifest pins the immutable references: peeled `rust-v0.146.1` at `79b4f03d3596`, peeled
`rust-v0.147.0` at `be6e8eac`, common base `95637f7056835fea66bdd0044414af480fc0fd74`, and the two
commits reachable only from 0.146.1 — the behavioral backport `7558bede75dd` and the release commit
`79b4f03d3596` — with their treatment stated. It also records how an ancestor-requiring port tool uses
the common base without misclassifying the backport.

R25. Fleet Core and Verified Workflows receive version bumps and changelog entries unless another unit
proves further plugins changed, accompanied by a version-policy sidecar mapping the Codex source
version to each plugin's current and target version. The round states its version-selection rule and
its stop gate rather than leaving the increment to the planner.

R26. Plugin manifests, the marketplace inventory, and `docs/portability/matrix.md` stay in sync with
the changes this round makes.

## Acceptance Examples

AE1. **Covers R5, R15, R17.** When a profile's canary meets its defined oracle, that profile ships
preferring Luna. When it does not, that profile alone keeps Terra. R1 through R4 ship either way,
because the eligibility model is independent of which model wins.

AE2. **Covers R7, R16.** When a V2 root spawns a Luna child, the child completes its task and returns
a schema-valid typed result, and the model-visible tool schema contains no collaboration tool. A Luna
child whose schema *did* expose collaboration tools would contradict the documented gate and blocks
the round.

AE3. **Covers R18.** When a managed permission profile's permitted roots include an executor-backed
resource, the `skill://` read succeeds. When they omit it, the read fails closed rather than returning
partial or unsandboxed content. An ordinary host-installed plugin reference is verified separately and
is not expected to fail closed on the same rule.

AE4. **Covers R10.** When the proof runner executes against a 0.147.0-stamped snapshot it proceeds.
Today it raises, because it accepts only the exact string `0.146.0`.

AE5. **Covers R19.** When a child's effective permissions match the parent turn's across the case
matrix, the round proceeds. When any child widens beyond its parent, the round stops at that finding —
regardless of which model the profile was running.

## Scope Boundaries

- Migrating the ten tracked manifests to the portable Agent Plugin format. It adds no capability this
  repository needs and does not remove the separate profile-synchronization path, so it is cost
  without benefit rather than a lossy migration.
- Populating `features.multi_agent_v2.subagent_developer_instructions`, and any change to the boolean
  feature form in `.codex/config.toml`.
- Re-proving orchestration matrix rows that 0.147.0 did not touch. The round enumerates which rows
  those are; permission, resume, model-selection, and skill-resource rows *are* touched and are in
  scope.
- Installing profiles into the user Codex profile tree, and marketplace publication. The round stops
  at source-ready. Disposable workspace-local profile and catalog staging is permitted, since the
  existing canary depends on it.
- Any change to logical role definitions or the role registry. This round is about execution profiles
  and the harness contract, not domain roles.

## Success Criteria

- A planner can decompose this without re-reading Codex source to learn what changed.
- The eligibility model survives the next catalog shift without a prose correction sweep — the test is
  whether a reader can tell what Codex reports from what this repository decided.
- Every live canary produces a recorded result against a pre-defined oracle, pass or fail. An unrun
  canary is a failed round, since shipping on an unverified hypothesis is the failure being corrected.
- No claim in the repository names a Codex version older than 0.147.0 as current behavior.
- `scripts/validate_codex_plugins.py` and the full test suite pass before the round is called
  source-ready, with targeted tests run first.

## Dependencies / Assumptions

- Codex CLI 0.147.0 is the installed and authenticated runtime. Verified on this host.
- The canaries need a live authenticated Codex session. Neither hypothesis is settleable from source
  reading, which is why they are requirements rather than findings.
- Work begins from a clean worktree. The current checkout is behind its remote and carries unrelated
  uncommitted work from concurrent sessions.
- Luna's catalog entry continues to report `v1`. If it ever reports `v2`, Luna children gain
  collaboration tools and R7's expectation inverts — which is precisely the shift the projection model
  exists to absorb, since the rule identifier makes the change detectable.
- Codex's derivation rules stay as recorded for 0.147.0. A future rule change still requires source
  classification; the projections make that a detected event rather than a silent drift.
- External consumers of the capability snapshot are not enumerated. R4 resolves this by preferring an
  explicit schema revision, so any outside consumer breaks visibly instead of silently.

## Outstanding Questions

**Deferred to planning**

- Whether a discovered permission defect is repaired in-round when it is repository-owned parser or
  harness code, versus stopping the round when it is native Codex behavior.
- Whether the canaries can share one live session or need separate permission profiles.
- Whether environment identity is captured via an app-server harness or dropped in favor of the
  durable tuple named in R12.

## Sources / Research

**Codex 0.147.0 source, read at tag `rust-v0.147.0` against `rust-v0.146.1`**

The two tags are *diverged*, not linear: 344 commits are reachable only from `rust-v0.147.0`, and two
only from `rust-v0.146.1` — the behavioral backport `7558bede75dd` ("Backport safer cyber-model
auto-review defaults") and the release commit `79b4f03d3596`. The backported behavior is present in
0.147.0. Comparisons here are merge-base relative, from `95637f7056835fea66bdd0044414af480fc0fd74`.

- `codex-rs/core/src/tools/handlers/multi_agents_common.rs` — `model_supports_multi_agent_backend`
  changed from requiring equality with V2 to requiring only that the model is not `Disabled`.
  Enforced in `find_spawn_agent_model_name`.
- `codex-rs/core/src/tools/spec_plan.rs:533-543` — `collab_tools_enabled`. Under V2, collaboration
  tools reach a root unconditionally, and a child only when its own model is catalogued `v2`. This is
  the source of the non-delegating-leaf property.
- `codex-rs/core/config.schema.json` — `subagent_developer_instructions` is the only property added to
  the V2 configuration object, reached at `features.multi_agent_v2`. No schema property was removed,
  though description text changed and properties were added elsewhere.
- `codex-rs/core/src/agent/role.rs` — `apply_role_to_config_for_multi_agent_v2` preserves
  caller-selected developer instructions, but only when the role omits its own and the new setting is
  configured.
- `codex-rs/core/src/agent/control/spawn.rs` — cold-loading a stored V2 child now restores its stored
  model and provider, and rejects a stored provider identifier that is missing from the current
  provider registry.
- `codex-rs/ext/skills/src/tools/read.rs` and `codex-rs/ext/skills/src/provider/executor.rs` — the
  fail-closed behavior applies when `skills.read` resolves an environment-backed resource with no
  matching sandbox context. Upstream's own test at
  `codex-rs/app-server/tests/suite/v2/executor_skills.rs` reads a referenced file successfully under
  `sandbox_mode = "read-only"`, which is why an ordinary host-installed reference is not expected to
  fail closed.
- `codex-rs/core-plugins/src/agent_plugin_manifest.rs` — the portable manifest auto-discovers
  direct-child skills and MCP configuration but carries no custom-agent profile field.
- `codex-rs/app-server-protocol/src/protocol/v2/plugin_search.rs` — search scopes are Global,
  Workspace, and Personal. `codex-rs/core-plugins/src/marketplace.rs` is unchanged between the tags.
- `codex-rs/core/src/tools/handlers/multi_agents_spec.rs` — byte-identical between the two tags. No
  per-child sandbox or permission parameter exists in either version.
- `codex-rs/protocol/src/protocol.rs` — the persisted turn-context item carries current directory,
  workspace roots, permission profile, sandbox, model, effort, and reviewer, but no environment
  identifier.
- Upstream pull requests 35895, 36901, 36930, 37031, 37038, and 37040 — turn-environment permissions
  became authoritative across spawn inheritance, tool execution, and capability discovery.

**Repository state this round corrects**

- `docs/validation/codex-v2-orchestration-matrix.json` — records `fallback-selected` with the reason
  "Luna is unavailable to MultiAgent V2".
- `scripts/build_codex_v2_orchestration_matrix.py` — hard-codes the same assumption.
- `scripts/prove_verified_workflows_runtime.py` — raises unless the snapshot reports exactly
  `0.146.0`; separately labels the per-child sandbox finding with that version.
- `tests/test_codex_runtime_capability_snapshot.py`, `tests/test_build_codex_v2_orchestration_matrix.py`
  — assert `0.146.0` and `0.145.0` respectively.
- `docs/validation/codex-runtime-capability-snapshot.schema-r3.json` — pins
  `"codex_cli_version": {"const": "0.146.0"}` in the schema itself, a fourth version gate. Revisions
  `schema.json`, `schema-r2`, and `schema-r3` establish the existing revision pattern.
- `scripts/port_contract.py` — rejects any capability-snapshot schema version outside `{1, 2}`, so a
  new revision requires widening it in the same change.
- `plugins/verified-workflows/README.md`, `plugins/verified-workflows/CHANGELOG.md`,
  `plugins/fleet-core/references/tier-palette.md`, `docs/portability/matrix.md` — restate the
  superseded Luna conclusion.

**Repository process gates**

- `AGENTS.md` — the Claude-to-Codex port runbook is mandatory for every import or refresh, and its
  port-manifest `classification` gate must pass before source-derived behavior changes. Manifests and
  `docs/portability/matrix.md` must stay in sync. `scripts/validate_codex_plugins.py` runs before a PR.
- `docs/portability/ports/2026-07-29-codex-0146-native-harness-version-policy.json` — the version-policy
  sidecar shape, mapping the Codex source version to each plugin's current and target version.

**Prior work**

- `docs/plans/2026-07-29-codex-0146-native-harness-alignment-plan.md` — the shape this round follows.
- `docs/plans/2026-07-24-codex-v2-orchestrated-execution-system-plan.md` — records the original
  contingency that produced the Terra fallback, confirming Luna was the intended selection.
