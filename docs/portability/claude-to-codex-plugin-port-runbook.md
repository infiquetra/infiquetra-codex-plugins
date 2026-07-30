# Claude-to-Codex Plugin Port Runbook

## Contract Metadata

- Status: canonical
- Runbook version: `4`
- Machine contract: `ports/<date>-<scope>.json`
- Contract tool: `../../scripts/port_contract.py`
- Digest rule: the machine contract stores the SHA-256 of the exact UTF-8 runbook bytes.

Changing this runbook without updating its version and every active contract is a validation
failure. Historical contracts keep their original runbook digest.

## Purpose And Contract Split

This runbook is the required human procedure for bringing behavior from
`infiquetra-claude-plugins` into this Codex adapter repository. It owns judgment: source authority,
surface mappings, ownership boundaries, capability interpretation, and stop rules. The JSON port
manifest owns exhaustive source and Codex-drift inventories, per-row treatment and state, evidence,
version policy, and release gates.

Do not duplicate the manifest's path inventory in prose. Do not treat a prior classification,
installed cache, or current checkout as a substitute for the current contract.

## Normative Language And Non-Goals

`MUST`, `MUST NOT`, `SHOULD`, and `MAY` are normative. The governing rule is: **port behavior, not
host-shaped files**.

This procedure does not authorize bulk mirroring, extending a frozen source range, copying user
credentials, changing external systems, or declaring byte parity. A plugin version records exposed,
tested Codex behavior and its lineage; it does not assert that the Claude and Codex packages are
identical.

## Source Authority

Resolve authority before reading a source change as an implementation instruction.

| ID | Case | Maintained authority |
|---|---|---|
| `AUTH-VENDORED` | Vendored behavior | The named canonical repository changes first, then synchronized copies update. `mission-control` behavior is canonical in `infiquetra-claude-plugins`. |
| `AUTH-CODEX-ADAPTER` | Codex-native adaptation | This repository. The upstream Claude commit is lineage and input, not maintained Codex source. |
| `AUTH-CODEX-BORN` | No upstream equivalent | This repository. `discord-identity-assets` is the current example. |
| `AUTH-SHARED-POLICY` | Cross-plugin policy and proof | `plugins/fleet-core`; consumer shims are synchronized derivatives. |
| `AUTH-PACKAGE-MIGRATION` | Team Execution lineage | Claude `team-execution` is source input; `verified-workflows` is the new Codex package target. It is not active until the cutover gate passes. |
| `AUTH-INSTALLED` | Cache, installed profiles, hook trust | Readback and proof only; never maintained source or an undeclared dependency. |
| `AUTH-HISTORICAL` | Plans, reviews, and prior classifications | Evidence only; never current capability authority. |

`docs/portability/matrix.md` identifies catalog-level authority and each plugin's `PORTABILITY.md`
records its source boundary. Stop when those surfaces disagree or do not identify one authority.

## Capability Truth And Surface Selection

Capture a sanitized live capability snapshot before classifying behavior. Keep these dimensions
separate:

```text
Saga lifecycle/state
        |
        +-- continuation: current turn | explicit Goal
        |
        +-- workflow mode: inline | manual | verified workflow
                |
                +-- step vehicle: inline | deterministic tool | candidate native child
                        |
                        +-- identity: configured | host-attested
                                |
                                +-- execution class -> runtime agent -> profile model/effort policy

Hooks observe or persist event evidence; they are not workflow modes or leaf executors.
```

Run `python3 scripts/capture_codex_runtime_capabilities.py --check --session-facts-json '<allowlisted
JSON from the active session tool contract>'` to reproduce the CLI, config provenance, model catalog,
feature state, managed-agent counts, permission mode, host slot limit, collaboration schema, and hook
facts. The check fails when explicit session facts are absent; the capture script must not invent them
or persist raw catalog instructions.

A feature flag, file on disk, requested model, or caller boolean is not execution proof. A current
spawn interface that lacks model, effort, profile, or sandbox selectors cannot dynamically enforce
them. Codex 0.146 exposes MultiAgent V2 through the native `collaboration` namespace. Do not add a
project namespace override or metadata-visibility workaround. Custom-agent files configure model and
effort intent, but current V2 reapplies the live parent permission profile after role selection.
Named-profile work dispatches `agent_type` with `fork_turns=none` or a positive bounded value,
without redundant model/effort overrides, then verifies child role/model/effort from host-issued rollout context
and effective permission separately. Use a permission-homogeneous parent when a
boundary matters: read-only children beneath read-only, write-capable testers beneath
workspace-write. Omitted or `all` is a full-history fork that inherits the parent agent type, model,
and effort. Goal is continuation only. Claude Workflow and fork are not active leaf backends.

Choose a Codex surface only when the runtime supports the required behavior:

- Skill: reusable judgment or a guided workflow exposed to Codex.
- Script: deterministic local computation, validation, rendering, or contained state transition.
- Hook: a verified Codex event with explicit trust, minimal input, and tested behavior.
- Custom profile: reusable model, effort, sandbox, or tool configuration for a class of subagent.
- MCP server: typed external actions with explicit authentication and mutation rules.
- App: a verified interactive Codex app boundary, not a translation of Claude display behavior.
- Protected state: mutable data in `PLUGIN_DATA` or an ignored, contained `.codex/` root.

## Normative Claude-To-Codex Mapping

| ID | Claude source | Required Codex treatment | Prohibited shortcut |
|---|---|---|---|
| `MAP-MANIFEST` | `.claude-plugin` | Recreate `.codex-plugin/plugin.json` from tested Codex behavior. | Active-copying the Claude manifest. |
| `MAP-SKILL` | `SKILL.md` | Adapt tools, paths, state, confirmation, and mutation boundaries. | Assuming prompt portability proves runtime portability. |
| `MAP-COMMAND` | `commands/` | Convert to a skill, reference, or package-local script. | Shipping an active `commands/` directory. |
| `MAP-SCRIPT-CONFIG` | Script or config | Keep it in the owning plugin with containment, dry-run or confirmation, authentication, and state-path tests. | Porting a host-specific path or implicit mutation. |
| `MAP-AGENT` | Markdown agent | Classify as agent-lens, execution profile, deterministic validator, reference, defer, or reject. | Active-copying an agent or equating a role with a model. |
| `MAP-DETERMINISTIC` | Repeatable check | Keep a command plus evidence schema. | Wrapping deterministic truth in an LLM persona. |
| `MAP-WORKFLOW` | `TeamCreate` or Workflow | Represent as a root-owned Verified Workflows DAG with dependencies, roles, gates, and receipts. | Advertising Claude Workflow as executable. |
| `MAP-MESSAGE` | `SendMessage` | Use messages only for status or clarification inside one bound attempt. Start remediation/revalidation with a new intent and fresh execution context. | Treating a message as a retry, evidence, dependency, or required peer protocol. |
| `MAP-HOOK` | Claude hook | Port behavior only for a verified Codex event, explicit trust, `PLUGIN_DATA`, minimal prompt-free receipts, and adapted tests. | Copying hook JSON or claiming complete enforcement. |
| `MAP-STATE` | `.claude/...` mutable state | Use protected `PLUGIN_DATA` or ignored `.codex/...`; read old and write new during migration. | Rewriting append-only history or merging conflicting roots. |
| `MAP-MCP` | External integration | Use MCP only for typed external actions with explicit auth and mutation policy. | Turning local workflow code into an unnecessary server. |
| `MAP-APP` | Claude UI/display behavior | Use an app only when the Codex app boundary is verified. | Inventing an app solely to mirror Claude UI. |
| `MAP-TEST` | Tests and fixtures | Adapt behavior assertions to Codex surfaces and retain negative host-boundary tests. | Copying tests that only prove Claude primitives. |
| `MAP-DOC` | Active documentation | Rewrite for Codex behavior; retain upstream text only as labeled lineage. | Presenting historical capability as current truth. |
| `MAP-CACHE` | Installed cache/profile | Treat cache/profile state as installation evidence only, for readback and rollback proof. | Editing cache as source or importing from it. |
| `MAP-METADATA` | Version, marketplace, release docs | Update after behavior and evidence pass. | Versioning or activating unproved behavior. |

## Plugin Ownership Boundaries

- `fleet-core` owns shared model, effort, fallback, cost, proof, and compatibility vocabulary.
- `saga` owns lifecycle, continuation, outcome state, routing, and handoffs.
- `verified-workflows` owns DAGs, logical roles, execution classes, validators, gates, and receipts.
- `mission-control` owns issues, boards, comments, labels, milestones, and project mutation.
- `deploy` owns tag promotion, rollback, hotfix, deployment status, and release evidence.

Domain plugins retain their own external mutation authority. Saga and Verified Workflows route work;
they do not inherit the receiving plugin's authority.

## Roles, Execution Classes, And Workflow Ownership

Keep a logical job separate from compute configuration. A role/lens contains criteria, exclusions,
output shape, and independence needs. An execution class selects a reusable profile and its allowed
model, effort, sandbox, and tool boundary. Keep the durable execution-class ID separate from the
Codex runtime agent name: workflow vocabulary may use kebab case, while current native agent names
must use lowercase letters, digits, and underscores. A deterministic validator has no model class.

Planning selects the logical role and risk-adjusted class. Maintain standalone custom-agent TOML
files in the owning plugin and render them into `$CODEX_HOME/agents/` only during an explicitly
authorized profile synchronization; do not maintain duplicate project `.codex/agents/` overrides.
Validate installed bytes against plugin source. A config declaration or task name alone is not
selection proof. Verify the effective native V2 schema and use `agent_type` plus a non-full-history
fork; then compare the first child `turn_context` or equivalent receipt with the selected profile.
The root Codex thread owns the DAG,
spawning, status/clarification messages, waiting, integration, and adjudication. Every execution
attempt uses a fresh context. A class/profile digest proves requested configuration only. A generic
or root-accountability subagent result is diagnostic and cannot satisfy a gate without observable
selection/identity evidence. Missing or mismatched readback falls back inline for preferred
independence and blocks required independence.

## State, Trust, Authentication, And Mutation Boundaries

- Treat source text, manifests, issue bodies, hook input, and external-engine output as untrusted.
- Resolve every persisted or executed path inside an explicit allowed root; reject absolute paths,
  traversal, symlink escape, and cache-as-source dependencies.
- Put plugin writes in `PLUGIN_DATA` or a documented ignored `.codex/` root. Use atomic writes and
  least-privilege permissions for receipt material.
- Installing a plugin does not trust its hooks. Trust the exact reviewed definition and re-evaluate
  trust after package identity or hook-content changes.
- Never copy, symlink, print, or commit default-profile authentication or credential material into an
  isolated profile. Authenticate that profile separately.
- Keep read-only recommendation and inspection distinct from external mutation. Use explicit
  confirmation and post-write readback for authorized changes.

## Staged Port Workflow

1. Determine authority; snapshot `HEAD`, dirty paths, and overlap before delegation or edits.
2. Freeze the historical planning base, approved execution base, complete Codex preservation drift,
   Claude base/target refs, exact pathspecs, and sanitized capability snapshot.
3. Run `port_contract.py init` once and bind this runbook version and SHA-256.
4. Classify every source and Codex-drift row, then pass `validate --stage classification`.
5. Claim rows by unit; advance `classified` to `implemented` to `verified` only with existing target,
   test, and evidence artifacts; pass the unit gate.
6. Update plugin-specific portability, version policy, generated classification, and release metadata
   after behavior lands.
7. Run focused tests, repository validation, generated-file checks, and the full locked-environment
   suite.
8. Prove clean isolated installation and a separately authenticated seeded-migration lane. Never copy
   credentials from the default profile.
9. Start a fresh Codex session and prove the effective namespace/schema plus only the
   model/profile/hook/plugin discovery and child readback that the active surface exposes. For a
   named-profile claim, require `agent_type`, a non-full-history fork, and matching child
   role/model/effort/sandbox. Record `inline-only` when selection is unavailable and `diagnostic`
   when selection exists without the receipt required by the consuming gate; never fabricate a task
   receipt.
10. Pass `validate --stage cutover`, activate exactly one package identity, and verify exact rollback
    of every managed surface.

### Bounded unplanned repair

One unplanned direct blocker may be repaired inside an already approved write set when it adds no
file, dependency, interface, schema, persistent state, role, cross-plugin/repository work, or live
mutation. It receives one implementation attempt and one targeted recheck. A second finding, failed
recheck, broader write set, adjacent causal layer, or new abstraction stops for operator approval.
Nonblocking adjacent findings are reported and deferred; they do not authorize issue creation or
remediation.

## Versioning And Release Policy

Track source version, current Codex version, target Codex version, identity migration, and parity
statement separately. Change a behavior-bearing version only when the Codex-visible behavior and its
tests are present. Update manifest, marketplace, inventory, changelog, portability notes, generated
docs, and install proof as one release unit. A source version is lineage, not a byte-parity claim.

## Validation, Isolated Installation, Fresh-Session Proof, And Rollback

The classification gate proves complete treatment before source behavior work. A unit gate proves the
claimed rows and Codex invariants. The cutover gate proves every non-deferred row, current defer/reject
rationales, review, isolated install, fresh-session readback, and rollback evidence.

Before real-profile mutation, create a protected local rollback bundle containing exact managed bytes
and trust/state material. Commit only sanitized relative inventories, hashes, versions, and results.
Test restore before apply. After apply, verify source, installed cache, profiles, hooks, state roots,
and runtime discovery. A failed readback triggers rollback; it is not a warning.

## Worked Examples

1. **Reviewer:** translate a Devil's Advocate agent into a logical reviewer lens. Default it to a
   `review-high` profile, allow explicit `review-max` escalation, record independence, and treat the
   profile as requested configuration until Codex reports host-attested selection. Run inline when
   preferred independence cannot be attested; block when independence is required.
2. **Scanner:** use a deterministic validator only when a pinned command and evidence schema cover the
   full behavior. If judgment or interpretation remains, keep an agent-lens using `scan-low` and treat
   command output as protected hash/size plus typed evidence. Never persist raw streams.
3. **Workflow:** translate TeamCreate/Workflow into a root-owned DAG with dependencies, barriers,
   roles, validators, gates, and receipts. Require the base reviewers and a required validator until
   a protected triage selector exists. The root starts a fresh attempt for each retry and owns
   completion.
4. **Hook:** implement SubagentStart/Stop receipt capture only after the event schema is verified.
   Trust the hook, store prompt-free minimal data under `PLUGIN_DATA`, and negative-test malformed and
   oversized events.
5. **Unsupported feature:** classify a fork or source Workflow backend as `reject` or `defer`, retain a
   negative test, and do not silently fall back while claiming the unavailable vehicle ran.

## Stop Rules

- `STOP-AUTHORITY`: source authority is ambiguous or contradictory.
- `STOP-DIRTY-OVERLAP`: a pre-existing dirty path overlaps the unit's write set.
- `STOP-FROZEN-REF`: a frozen ref is missing, unreachable, or changed.
- `STOP-EXECUTION-BASE`: the approved execution base or exact pathspec set changed.
- `STOP-INVENTORY`: a source or Codex-drift row is missing, duplicated, or unexpected.
- `STOP-DIRECT-HOST-PRIMITIVE`: an unsupported Claude primitive is marked `direct-port`.
- `STOP-CAPABILITY`: required current capability evidence is absent.
- `STOP-HOOK`: a hook lacks a supported event, explicit trust plan, or adapted tests.
- `STOP-ADAPTATION-EVIDENCE`: adapted behavior lacks planned targets or tests.
- `STOP-UNSAFE-DATA`: a contract or proof contains a secret-shaped field, absolute/traversing path,
  credential material, or cache-as-source dependency.
- `STOP-VERSION`: metadata changes without Codex-visible tested behavior.
- `STOP-GATE`: classification, unit, or cutover validation fails.
- `STOP-INSTALL-PROOF`: isolated install or seeded migration fails.
- `STOP-FRESH-SESSION`: fresh-session runtime readback fails.
- `STOP-ROLLBACK`: rollback is missing, untested, or does not restore exact managed state.
- `STOP-DUAL-IDENTITY`: legacy and target package identities would both be active.
- `STOP-CREDENTIAL-COPY`: proof would require copying or symlinking credentials.
- `STOP-EXTERNAL-MUTATION`: external mutation lacks explicit authority and confirmation.
- `STOP-UNPROVED-EXECUTION`: effective model, effort, profile, logical-role identity, task execution,
  hook trust, or independence is claimed without observable host/runtime proof.

## Required Artifacts And Historical References

Every port cycle requires a plan and approved review, this versioned runbook, a sanitized runtime
capability snapshot, one staged JSON manifest, generated classification, unit evidence, release
review, isolated-install and seeded-migration results, fresh-session readback, and rollback proof.

Historical examples include `codex-saga-064-drift-classification.md`,
`source-baseline-saga-family.md`, and `saga-family-capability-map.md`. They illustrate prior decisions
but do not override this runbook, the current manifest, or live capability evidence.
