---
title: Codex 0.146 Native-Harness Alignment and Bounded Plugin Simplification
type: refactor
status: source-ready
date: 2026-07-29
source: Codex CLI rust-v0.145.0..rust-v0.146.0
---

# Codex 0.146 Native-Harness Alignment and Bounded Plugin Simplification

## Summary

Target Codex CLI 0.146 and delete plugin machinery now owned by the native harness. Keep the behavior-bearing contracts that Codex does not supply: logical roles, named execution profiles, runtime receipt checks, typed results, bounded write ownership, external-provider adapters, lifecycle reconstruction, domain mutation, and the Git integration operator.

The first seven implementation units are already source-ready in the working tree. This amendment
does not reopen them; it classifies the rest of the plugin-facing 0.146 source surface, adds a
bounded routing audit across all ten plugins, removes stale Codex interaction and agent vocabulary
from Saga, and separates native session resume from Saga lifecycle reconstruction while
recognizing Saga's real plugin hook.

Luna remains a V1 model in the 0.146 catalog. Low-effort V2 profiles stay on Terra until a future profile-synchronization run observes Luna as V2 and an isolated canary passes.

The source comparison is frozen at peeled commits
`25af12f7e61572b0bc18ddb1008be543b91519b0` (0.145) and
`e363b08c9175ac1cbe5893615dd2cb9ddf95043b` (0.146).

The existing native-harness manifest records `99efeef6506cd7f6512404d0ad8755a87ff5a011`,
the parent of the 0.145 release tag, as its base. The parent-to-tag tree difference is only
`codex-rs/Cargo.toml`; all 41 selected plugin-facing paths are byte-identical at the tag. Preserve
that historical manifest, record this equivalence explicitly, and use the shared parent as the
machine-contract base because the 0.145 and 0.146 release tags are siblings. The exact peeled
0.145 tag remains the human source-comparison authority.

## Working-tree state

The plan distinguishes completed baseline work from the amendment so another agent does not repeat or reinterpret the implementation.

| units | state | boundary |
|---|---|---|
| U1-U7 | source-ready in the current working tree | Do not redo except to repair a regression caused by U8-U11. |
| U8-U11 | source-ready 2026-07-30 | Implemented within the amendment allowlists and stop rules; 17/17 routes and all repository gates pass. |
| commit through release | not authorized | No commit, push, PR, merge, publication, profile synchronization, restart, or deployment. The operator authorized a bounded normal-profile plugin refresh for U11 only. |

## Evidence and ownership conclusions

Codex 0.146 changes more than the native agent harness. The implementation must use these source-backed ownership boundaries.

| 0.146 surface | evidence | plugin treatment |
|---|---|---|
| Skill selection and metadata pressure | `codex-rs/ext/skills/src/dynamic_skill_selector/routing_card_lexical.rs`, `rrf_lexical_char.rs`, and `render.rs`; this repository currently exposes 49 skills and 13,711 normalized description characters | Codex owns selection, budgeting, path compaction, and warnings. Plugins own concise, unambiguous routing metadata and must not implement a second selector or truncation engine. |
| Skill sources and resources | `catalog.rs`, `provider/{host,executor,orchestrator}.rs`, and `tools/{list,read}.rs` | Codex owns authority-bound listing and bounded resource reads, including executor-provided skills. Keep plugin references relative and validated; do not add a plugin resource loader. |
| Root interaction tool | `codex-rs/core/src/tools/handlers/request_user_input_spec.rs` | Use `request_user_input` only when the runtime exposes it for the current mode. Otherwise ask one concise blocking question in normal conversation and stop. Never use `tool_search` to discover a core interaction tool. |
| Native agent roles and optional tools | `spawn.rs`, `spec_plan.rs`, the 0.146 model catalog, and the live `spawn_agent` schema | Use actual built-ins: `explorer` for read-only discovery, `worker` for implementation, and `default` when neither specialization fits. Do not emit Claude-style `Explore` or `Task` agent names. Treat `wait_agent` and `update_plan` as conditional runtime tools, not guaranteed plugin APIs. |
| Native session continuation | `codex resume`, `/resume`, named and pinned threads, paginated history, and fork changes in 0.146 | Native Codex owns continuation of a known saved chat. `saga:resume` owns cross-artifact lifecycle reconstruction; its JSONL Tier 2 remains an explicit last-resort multi-session forensic path this cycle. |
| Plugin hooks | `codex-rs/core-plugins/src/loader.rs`, `codex-rs/hooks/src/engine/command_runner.rs`, and the stable `hooks` feature | Saga's default `hooks/hooks.json` is active after trust and may emit bounded SessionStart re-entry context. The 0.146 runner now preserves output from hooks such as `session_context.py` that exit without reading stdin. Hook output is not an execution vehicle, identity attestation, or gate receipt. |
| Plugin cache and refresh | 0.146 `plugin/list` force-refresh and cache-wait behavior | Use a fresh `codex exec` process after the operator-authorized normal-profile refresh. The repository has no manual cache polling workaround to remove, and an active thread's catalog refresh is not assumed. |
| Agent Plugins manifests | `agent_plugin_manifest.rs`, `manifest.rs`, and `loader.rs` | Keep `.codex-plugin/plugin.json`. The alternate root manifest auto-discovers skills and MCP plus Codex-extension hooks/Apps but does not package maintained custom-agent TOMLs; migrating ten working manifests adds no capability. |
| Custom-agent profiles | Agent Plugins parsing plus current `plugins/verified-workflows/agents/*.toml` synchronization | Retain the explicit, operator-authorized `$CODEX_HOME/agents` sync path. 0.146 does not make plugin installation discover those TOMLs automatically. |
| MCP, Apps, proxies, and trusted-script attribution | 0.146 MCP/App refresh, proxy, and script-attribution source plus current plugin manifests | Current plugins bundle no MCP server or App, so add no adapter. Native proxy fixes cover Codex-owned HTTP only; retain UniFi, Discord, and Saga domain transports. Treat script attribution as diagnostics, not authorization. |

Mission Control and Deploy retain domain mutation ownership. Home Lab Ops, UniFi, Discord Identity
Assets, Python Toolkit, and Test Suite retain their domain behavior. Fleet's installed-cache lookup
also remains: native plugin refresh does not provide cross-plugin Python imports. Test Suite and
Python Toolkit overlap with other installed Python skills, but no 0.146-caused defect is yet proven;
redesign is outside this cycle unless U8 produces a reproducible routing failure.

## Approved baseline interface changes

These U1-U7 decisions are already implemented and remain fixed.

- Delete `verified-workflows:select-agent`; callers dispatch native `agent_type` directly.
- Change Workflow Contract assignments to `id | depends | role | profile | writes | completion | fallback`. Model and effort are derived from the maintained profile.
- Delete `workflow_feasibility.py` and the snapshot-driven planning gate.
- Add finding `scope_disposition` values `planned | one-hop | defer | approval-required`.
- Add `saga.harness.request.v1` and `saga.harness.result.v1` for retained external routes.
- Keep `.codex-plugin/plugin.json`; do not add a second root manifest.

## Amendment interface decisions

The amendment changes routing instructions, not domain ownership.

- Replace every active Saga instruction that names `Codex blocking question` or tells Codex to search for it with the conditional native interaction contract from the evidence table.
- Replace every active Saga instruction that names generic `Explore` or `Task` agents with the matching 0.146 built-in role and preserve existing authorization and no-auto-spawn rules.
- Keep the skill identity `saga:resume`, but remove bare session-continuation language from its routing description. A request to continue one saved chat routes to native `/resume`; Saga runs only for lifecycle reconstruction across Saga state, issues, PRs, documents, or explicitly requested multi-session forensics.
- Keep Tier 2 JSONL forensics in this cycle. Deleting it requires separate evidence that native history covers the cross-session synthesis case and separate operator approval.
- Treat Saga's trusted SessionStart hook as active context injection. Its output may suggest `saga:loop resume <id>` but cannot prove current model, role, workflow state, or completed work.
- Audit natural-language routing across every plugin in fresh normal-profile processes after the bounded local-marketplace refresh. A non-Saga source edit is not authorized merely because a canary fails; report the failure and request the smallest cross-plugin or canonical-repository expansion.

## Bounded deviation policy

One unplanned issue may be fixed without new approval only when it directly fails an approved blocking check, stays inside the current unit's explicit write allowlist, changes one direct cause, adds no file, dependency, interface, schema, state, role, cross-plugin or cross-repository work, or live mutation, and receives one implementation attempt plus one targeted recheck.

A second unplanned issue, failed recheck, broader write set, adjacent causal layer, new abstraction, non-Saga plugin edit, or canonical Mission Control change is `approval-required`. Stop and present the evidence, impact, smallest expansion, and choices to expand, defer, or stop. Nonblocking adjacent findings are `defer`; report them without remediation or issue creation.

Security and privacy review is proportional to the changed trust boundary. Category or numeric score alone does not block. Verified P0/P1 secret exposure, auth bypass, destructive unauthorized write, or material data disclosure remains a hard stop. Unplanned P2/P3 hardening is deferred unless it directly fails an approved acceptance condition.

## Implementation units

### U1-U7 — Completed baseline

The original native-harness alignment remains source-ready and is not reimplemented by this amendment.

1. Refresh the sanitized runtime snapshot and pass the port classification gate.
2. Remove obsolete V1, namespace, and feasibility assumptions plus plugin-owned native-harness substitutes.
3. Make one profile policy source render seven minimal agent TOMLs; keep Terra fallback for Luna.
4. Simplify Verified Workflows around native dispatch, direct-sibling independent review, typed results, one remediation and recheck, bounded deviation, and the retained Git operator.
5. Replace Saga external lifecycle machinery with a thin request/result harness while preserving Claude Opus, Agy Gemini Flash and Pro, Ollama gpt-oss and embeddings, and DeepSeek.
6. Retain Fleet model and profile resolution, bridge and output proof, shim, leases, concurrency, orphan evidence, and workflow compatibility; retire audit and delegation state, effort and cost riders, retry and circuit-breaker state, and the tier-table runtime helper.
7. Update documentation and release metadata to Verified Workflows 3.0.0, Saga 0.83.0, and Fleet Core 0.14.0 with Codex build metadata.

### U8 — Port freeze and full-plugin routing contract

Freeze the omitted 0.146 source inputs and define a deterministic canary before changing
source-derived Saga instructions. This unit specifies the routing proof; U11 runs it against the
final plugin bytes.

**Write allowlist:** a new amendment-cycle port manifest at
`docs/portability/ports/2026-07-29-codex-0146-cross-plugin-alignment.json`, its generated
classification at
`docs/portability/classifications/2026-07-29-codex-0146-cross-plugin-alignment.md`, and one bounded
validation receipt under `docs/validation/`.

**Port-contract boundary:**

1. Do not extend or re-freeze the existing `codex-0146-native-harness` source inventory. It remains
   authoritative for its original 11 pathspecs. First prove all 41 selected plugin-facing paths
   have no diff from the recorded shared parent to the exact 0.145 tag.
2. Create the amendment contract with
   `99efeef6506cd7f6512404d0ad8755a87ff5a011` as its machine base and
   `e363b08c9175ac1cbe5893615dd2cb9ddf95043b` as its target. Record
   `25af12f7e61572b0bc18ddb1008be543b91519b0` as the exact 0.145 comparison tag whose
   selected paths are byte-equivalent to the machine base. Its bootstrap
   pathspecs cover the plugin-facing feature boundaries found in the full 1,167-file release diff:
   - all changed source under `codex-rs/ext/skills/src`;
   - Agent Plugins parsing, plugin loading/management, script attribution, and app-server
     plugin-list refresh;
   - native spawn and optional-tool planning;
   - the model catalog row governing Luna;
   - paginated model context/fork/segment paging and TUI resume selection; and
   - the changed hook command runner.
   Resolve the changed rows from exactly these bootstrap selectors before applying the exclusion
   in step 3:
   - `codex-rs/ext/skills/src`
   - `codex-rs/core-plugins/src/agent_plugin_manifest.rs`
   - `codex-rs/core-plugins/src/loader.rs`
   - `codex-rs/core-plugins/src/manager.rs`
   - `codex-rs/core-plugins/src/script_attribution.rs`
   - `codex-rs/app-server-protocol/src/protocol/v2/plugin.rs`
   - `codex-rs/app-server/src/request_processors/plugins.rs`
   - `codex-rs/core/src/agent/control/spawn.rs`
   - `codex-rs/core/src/tools/spec_plan.rs`
   - `codex-rs/models-manager/models.json`
   - `codex-rs/thread-store/src/local/model_context.rs`
   - `codex-rs/thread-store/src/local/paginated_fork.rs`
   - `codex-rs/thread-store/src/local/thread_history/segment_paging.rs`
   - `codex-rs/tui/src/resume_picker.rs`
   - `codex-rs/hooks/src/engine/command_runner.rs`
3. Exclude the seven paths already owned by the native-harness manifest:
   `agent_plugin_manifest.rs`, `script_attribution.rs`, `spawn.rs`, `spec_plan.rs`,
   `provider/executor.rs`, `render.rs`, and `paginated_fork.rs`. The resulting amendment inventory
   must contain exactly 34 non-overlapping changed rows. After `init`, the amendment manifest owns
   the exhaustive row data and later prose references it rather than duplicating it.
4. Bind the stable `request_user_input` schema and the live native-agent schema through the
   sanitized 0.146 capability snapshot; they are current host invariants, not invented delta rows.
5. Pass classification-stage validation, source verification against an OpenAI Codex checkout at
   the machine-contract refs, exact-tag equivalence checking, and generated-classification
   checking before U9.
6. If the required checkout is unavailable, its refs do not peel to the recorded commits, the
   existing-path equivalence fails, or the amendment inventory is not exactly 34 rows, stop;
   do not substitute a moving branch or broaden the source inventory.

**Deterministic canary contract:**

- After U9 and U10, use the operator-authorized normal authenticated Codex profile. Record its
  configured Infiquetra marketplace source and installed versions before mutation.
- Temporarily replace the configured `infiquetra-codex-plugins` Git marketplace with the repository
  root, verify the marketplace name, and refresh exactly
  `saga`, `deploy`, `mission-control`, `verified-workflows`, `home-lab-ops`, `python-toolkit`,
  `unifi`, `test-suite`, `fleet-core`, and `discord-identity-assets` from that marketplace.
- After the receipt is sealed, restore the original Git marketplace source and ref through the
  native marketplace CLI. Do not edit credentials, trust, saved sessions, agent configuration, or
  unrelated plugins. Native cache retention is acceptable; do not hand-delete cache entries.
- Use Codex 0.146 and one invocation per row with this command shape:
  `codex exec --ephemeral --json --output-schema <temporary-schema> -m gpt-5.6-sol
  -c 'model_reasoning_effort="low"' <route-only-prompt>`.
- Give every invocation this route-only instruction: `Route-only canary. Do not use tools, execute
  a skill, mutate files, or contact external systems. Given USER_INTENT, return only JSON matching
  the supplied schema with route set to exactly one canonical route id and a short reason.`
- The temporary output schema constrains `route` to the canonical IDs in the table and requires
  `route` and `reason` with no additional properties. Route selection tests catalog metadata; it
  does not prove skill execution.
- Record the exact prompt, expected route, actual structured route, model, effort, exit code,
  Codex version, refreshed plugin versions, catalog truncation/omission warnings, and the bounded
  profile mutation/restoration evidence in the receipt.

| prompt intent | canonical route id |
|---|---|
| Continue my most recent saved Codex chat | `native:resume` |
| Reconstruct issue 54 across Saga ticks and prior PR rounds | `saga:resume` |
| Switch Codex into Plan mode | `native:plan-mode` |
| Produce a lifecycle implementation plan with review and deploy gates | `saga:plan` |
| Review this implementation plan for readiness | `saga:doc-review` |
| Review this PR diff before opening or merging | `saga:code-review` |
| Show deployment drift across nonprod, staging, and production | `deploy:deploy-status` |
| Promote this repository to nonprod with a deployment tag | `deploy:deploy` |
| Prepare a canonical defect issue from these rough notes | `mission-control:issues` |
| Move this project card to Active | `mission-control:board` |
| Validate inventory after a home-lab hardware change | `home-lab-ops:inventory-sync` |
| Show a Lambda Powertools serverless error-handling pattern | `python-toolkit:python-patterns` |
| Run pytest, ruff, mypy, bandit, and coverage together | `test-suite:run-quality-checks` |
| Manage a UniFi VLAN and firewall rule | `unifi:unifi-network` |
| Prepare Discord guild identity assets | `discord-identity-assets:discord-identity-assets` |
| Review an approved Workflow Contract without launching it | `verified-workflows:review-workflow` |
| Execute this approved Workflow Contract | `verified-workflows:run` |

**Failure policy:** one Saga route may receive one description-only correction limited to the
failing Saga skill and its direct Saga competitor, followed by one rerun. A second failure, any
non-Saga failure, any executable-skill canary, or a general routing framework is
`approval-required`.

**Acceptance:** both port contracts pass their independent gates and the routing contract is
machine-checkable. The amendment contract contains 34 classified non-overlapping rows and no
unknown treatment. U11 must record all 17 passing rows and no omitted skill before the amendment is
source-ready. Missing source or failure to refresh and restore the normal profile pauses the unit
and is reported as a blocker; it is not a passing substitute.

### U9 — Saga interaction and native-agent vocabulary

Remove instructions that make Saga fight Codex's actual interaction and multi-agent schemas.

**Write allowlist:** active Markdown under `plugins/saga/skills/**` and `plugins/saga/references/**` that matches the stale-token inventory; `plugins/saga/tests/test_codex_operator_choice.py`; `scripts/validate_codex_plugins.py`; `tests/test_validate_codex_plugins.py`; and directly affected Saga documentation or changelog entries.

**Changes:**

- Replace `Codex blocking question` and its `ToolSearch` lookup with one shared wording: use `request_user_input` only when listed and allowed in the current mode; otherwise ask one concise blocking question in the normal response and stop.
- Preserve channel-inline behavior without inventing a separate tool name.
- Map read-only exploration to `explorer`, implementation to `worker`, and unspecialized work to `default`.
- Preserve every existing operator-choice, explicit-workflow, cost disclosure, and no-auto-spawn rule.
- Extend drift validation so active Saga text cannot reintroduce the stale tool or Claude agent vocabulary.

**Baseline:** active Saga skills and references currently contain `Codex blocking question` in 20
files, `ToolSearch` in 16 files, and Claude-style `Explore` or `Task` agent vocabulary in 15 files.
Headings and ordinary English uses of “explore” or “task” are not stale-agent matches.

**Acceptance:** those three file counts reach zero for the defined stale forms, the validator
catches one representative reintroduction of each form, and existing Saga skill and
operator-choice tests pass.

### U10 — Native resume boundary and real hook behavior

Make Saga complement native thread continuation and document the hook that Codex actually loads.

**Write allowlist:** `plugins/saga/skills/resume/**`, `plugins/saga/references/operator-choice.md`, Saga README and changelog, `tests/test_saga_session_context.py`, `plugins/saga/tests/test_codex_operator_choice.py`, and directly affected package or documentation tests.

**Changes:**

- Narrow `saga:resume` frontmatter and entry logic to lifecycle reconstruction.
- Route a known saved-chat continuation request to native `/resume` without reading Saga JSONL.
- Keep Tier 1 whole-tick and PR reconstruction unchanged.
- Keep Tier 2 only for explicit multi-session reconstruction when no Saga or resolvable issue exists; do not claim it replaces native resume.
- State that default `hooks/hooks.json` is auto-discovered after trust and emits advisory SessionStart context only.
- Do not add a manifest `hooks` field, new hook, or hook-state abstraction.

**Acceptance:** static tests distinguish native continuation from Saga reconstruction, the existing
SessionStart hook tests pass, and `codex features list` reports stable `hooks` and removed
`plugin_hooks`. U11's operator-authorized normal-profile refresh is the only allowed current-user
configuration change.

The static assertions must prove that native continuation is evaluated before Saga artifact scans,
returns `native:resume` without JSONL reads, and that Tier 2 remains reachable only for an explicit
multi-session reconstruction with no Saga state or resolvable issue. Hook assertions cover
trust-gated discovery and advisory output; they must not treat hook output as model, role, workflow,
or completion proof.

### U11 — Authority, versions, and final validation

Close the amended source-ready batch without expanding its lifecycle.

**Changes:**

- Run the U8 routing canary only after U9 and U10 source bytes and their targeted tests stabilize.
- Refresh plan and review hashes in the existing cycle port manifest without changing its frozen
  source pathspecs, then regenerate its classification.
- Finalize and render the amendment-cycle U8 manifest/classification independently.
- Add U8-U10 evidence rows only after their checks run.
- Preserve the existing U1-U7 receipts; do not overwrite earlier unit evidence with amendment
  results.
- Keep Verified Workflows 3.0.0 and Fleet Core 0.14.0 unless their bytes change.
- Keep Saga 0.83.0 and regenerate only its Codex build metadata after final Saga bytes stabilize; update the manifest, inventory, README, changelog, and version-policy fixture together.
- If U8 is approved to change another plugin's bytes, stop for an explicit semantic-version decision before editing that plugin.

**Acceptance:** all 17 canary rows pass and the original Git marketplace source/ref is restored.
Changed-plugin tests, both port-contract gates, validator, Ruff, the full test suite, and
`git diff --check` pass with no stale authority hash or version reference.

## Implementation sequence

1. U8 freezes and classifies the amendment-cycle non-overlapping source inventory.
2. U9 updates interaction and native-agent vocabulary and its drift tests.
3. U10 narrows resume and documents the real hook boundary.
4. U11 stabilizes Saga metadata, refreshes those final bytes through the normal profile, runs the
   route-only canary in fresh processes, restores the original marketplace source, refreshes
   authority evidence, and runs final repository checks.

No model canary result collected before U9/U10 counts as final routing evidence.

## Explicit deferrals and non-changes

These findings were reviewed but do not authorize extra implementation:

- Do not migrate manifests to Agent Plugins or remove Verified Workflows profile synchronization;
  0.146 does not auto-install custom-agent TOMLs.
- Do not remove Fleet's installed-cache resolution rung; it locates shared Python code, which the
  native cache refresh does not expose as an import API.
- Do not rewrite UniFi, Discord, Saga provider, Deploy, or Mission Control transports around
  Codex's HTTP pool. The 0.146 proxy fixes apply to Codex-owned auth, plugin, MCP, and remote-exec
  traffic, not arbitrary bundled scripts.
- `plugins/saga/scripts/lease_broker.py` still contains dormant Claude-shaped `Agent|Task` hook
  adapters, but Saga's active plugin hook references only `hooks/session_context.py`. Removing that
  shared lease adapter surface is a separate authority-bearing cleanup, not a direct 0.146 blocker;
  record it as deferred rather than deepening this cycle.
- Do not redesign Python Toolkit versus Test Suite from description similarity alone. Escalate only
  a reproducible U8 route failure.

## Execution and release boundary

Implement U8-U11 root-owned. Verified Workflows remains a test target rather than the bootstrap mechanism for its own source rewrite.

The operator authorized the normal authenticated profile for U11. The Infiquetra marketplace source
and its ten installed plugins may be refreshed from this repository only for the routing evidence,
then the original Git marketplace source/ref must be restored. Credentials, hook trust, saved
sessions, unrelated plugins, and agent configuration remain read-only.

Stop source-ready before commit, push, PR, merge, publication, profile synchronization, Codex
restart, issue creation, or deployment.

## Verification

Run the narrowest changed-surface tests first, then the cycle and repository gates:

```bash
python3 -m pytest -q \
  plugins/saga/tests/test_codex_operator_choice.py \
  tests/test_saga_session_context.py \
  tests/test_validate_codex_plugins.py
python3 scripts/port_contract.py validate \
  --manifest docs/portability/ports/2026-07-29-codex-0146-native-harness.json \
  --stage classification
python3 scripts/port_contract.py verify-source \
  --manifest docs/portability/ports/2026-07-29-codex-0146-native-harness.json \
  --source-repo <openai-codex-checkout>
python3 scripts/port_contract.py render \
  --manifest docs/portability/ports/2026-07-29-codex-0146-native-harness.json \
  --output docs/portability/classifications/2026-07-29-codex-0146-native-harness.md \
  --check
python3 scripts/port_contract.py validate \
  --manifest docs/portability/ports/2026-07-29-codex-0146-cross-plugin-alignment.json \
  --stage classification
python3 scripts/port_contract.py verify-source \
  --manifest docs/portability/ports/2026-07-29-codex-0146-cross-plugin-alignment.json \
  --source-repo <openai-codex-checkout>
python3 scripts/port_contract.py render \
  --manifest docs/portability/ports/2026-07-29-codex-0146-cross-plugin-alignment.json \
  --output docs/portability/classifications/2026-07-29-codex-0146-cross-plugin-alignment.md \
  --check
python3 scripts/validate_codex_plugins.py
python3 plugins/test-suite/skills/run-quality-checks/scripts/test_runner.py \
  --dry-run --checks pytest,ruff
uv run ruff check .
python3 -m pytest -q
git diff --check
```

`<openai-codex-checkout>` is the operator-supplied local checkout whose recorded refs must peel to
the plan's two source commits. Checks that require credential changes, trusted-hook mutation,
restart, publication, or remote lifecycle action remain outside the source-ready boundary.
