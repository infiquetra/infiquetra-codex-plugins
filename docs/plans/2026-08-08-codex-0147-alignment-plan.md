---
title: Codex 0.147.0 Alignment
type: refactor
status: active
date: 2026-08-08
deepened: 2026-08-08
origin: docs/brainstorms/2026-08-08-codex-0147-alignment-requirements.md
---

# Codex 0.147.0 Alignment

## Summary

Align this repository with Codex CLI 0.147.0: replace the conflated model-eligibility value with one
raw catalog fact plus two derived projections, restore Luna on the two low-cost profiles behind
per-profile live canaries, re-baseline the capability snapshot behind a target-version constant kept
distinct from observed runtime evidence, prove the reworked turn-environment permission inheritance,
and carry the change through a seeded upgrade acceptance to a merged PR.

## Problem Frame

Codex 0.147.0 relaxed the gate deciding which models a MultiAgent V2 session may use, from "the
catalog must say `v2`" to "the catalog must not say `Disabled`". Luna is catalogued `v1`, so it went
from rejected to accepted.

Grounding found the defect concentrated and then restated. `CatalogModel.selectable`
(`plugins/fleet-core/scripts/fleet_commons/codex_model_catalog.py:55`) is
`visibility == "list" and supported_in_api` — it never consults `multi_agent_version`. The Luna
exclusion is not derived anywhere; it is frozen into policy data as `"preferred": {"model":
"gpt-5.6-terra"}` on the `scan-low` and `monitor-low` execution classes
(`plugins/fleet-core/scripts/fleet_commons/models.json:57`), and restated in the renderer's
`PROFILE_POLICY`, the test fixture at `plugins/verified-workflows/tests/test_agent_tier_sync.py:57`,
the matrix builder at `scripts/build_codex_v2_orchestration_matrix.py:71`, the two generated profiles,
the validation matrix, and four prose documents.

The promotion path already exists and is unreachable. `sync_codex_agents.py --luna-v2-canary-passed`
reaches `plugins/verified-workflows/scripts/render_codex_agents.py:984`, whose predicate at line 986
requires `luna.multi_agent_version == "v2"` — the superseded 0.146 rule — so it raises even when a
canary passes. The machinery was built against the rule that was true when it was written.

The same freeze-and-restate pattern governs the Codex version, hard-pinned in four places that have
already drifted apart (`0.146.0` in two, `0.145.0` in a third). This plan corrects the pattern, not
only the Luna symptom.

## Key Technical Decisions

**KTD1 — The projections live on `CatalogModel`, consumed by `tier_resolver`.** Add derived values
beside the existing `selectable` property in `codex_model_catalog.py`, where `multi_agent_version`
already lands. The override-filter projection is a property of the model. The collaboration projection
takes session position as an input, so its serialized form carries **both** the root and child outcomes
explicitly rather than one position-dependent value. `tier_resolver` consumes the override-filter
projection **only** — collaboration-tool availability is not a model-selection concern. Rejected: a new
module, which would split catalog truth across two files.

**KTD2 — Target version and observed version are different things and never share a field.**
`CODEX_TARGET_VERSION` expresses what this repository targets and drives expectations: the proof
runner's check, both test assertions, and the generated schema `const`. It must never stamp an observed
runtime receipt. `scripts/build_codex_v2_orchestration_matrix.py:509` emits an observed `0.145.0`;
relabelling that to `0.147.0` without rerunning the rows would falsify provenance. Builders therefore
capture the observed version independently and compare it to the target. Rejected: one constant serving
both roles, which is how a target silently becomes a claim about what ran.

**KTD3 — New schema revision `schema-r4.json` at `schema_version` 3, generated not hand-edited.** The
repository already uses `schema.json` / `schema-r2` / `schema-r3` as its revision idiom, and an explicit
revision makes outside breakage visible. A generator is what makes KTD2 hold; a hand-edited schema
drifts from the constant. `scripts/port_contract.py:379` widens from `{1, 2}` to `{1, 2, 3}` in the same
change.

**KTD4 — One canonical policy source, not two cross-asserted ones.** Two independent surfaces encode
model policy today: the renderer's `PROFILE_POLICY` (which generates the profiles Codex spawns, and
never reads `models.json`) and `models.json`'s `execution_classes` (which
`tier_resolver.resolve_execution_class` answers with). A cross-assertion between them cannot hold,
because the canary gate makes the rendered value differ from the class value in the ungated state by
design. Profiles therefore map to Fleet execution classes and rendering consumes the class policy after
a valid canary receipt — collapsing two sources to one. Rejected: keeping both and asserting equality,
which fails in exactly the state the gate exists to express.

**KTD5 — The canary gate is a per-profile receipt artifact, not a pair-wide boolean.**
`--luna-v2-canary-passed` is one flag applied to both `scan_low` and `monitor_low`
(`render_codex_agents.py:984`), so it cannot represent `scan_low` passing while `monitor_low` fails.
A validated per-profile receipt replaces it. Rejected: two booleans, which works but leaves the pass
evidence outside the artifact that gates on it.

**KTD6 — Permission drift stops the round; it never triggers a model fallback.** The permission path is
model-independent, so falling back to Terra would mask a defect rather than avoid it.

**KTD7 — Tool absence is proven from the model-visible tool plan, via a named mechanism.** An
unobserved collaboration call does not prove schema absence. The existing harness cannot do this:
`scripts/prove_verified_workflows_runtime.py:257` infers observed tool calls from rollout rows and has
no access to the tool specification. The proof therefore requires an app-server route that captures the
tool plan, plus a separate runtime negative probe. Naming the mechanism is part of the harness unit, not
left to the proof units.

**KTD8 — Paired execution with separated harness authorship and evidence adjudication.** Execution is
inline, paired with the Codex Herdr session `update-codex-plugins` (pane `w25:p7`). Neither engine
reviews its own work. Critically, the engine that runs a proof does not also author its harness: the
harness is built and cross-reviewed in U5 and frozen before any receipt is produced, and Claude
independently adjudicates every receipt Codex produces. Any harness change after freeze invalidates and
reruns the affected proofs. Rationale: during the brainstorm and two document reviews, self-review
repeatedly missed what cross-engine review caught — including this independence defect, which the first
draft of this plan contained.

Ownership per unit:

| Unit | Owner | Reviewer |
|---|---|---|
| U1 Source freeze and contract extension | Codex | Claude |
| U2 Contract migration (atomic) | Claude | Codex |
| U3 Developer-instruction contract | Claude | Codex |
| U4 Policy source collapse | Claude | Codex |
| U5 Proof harness (frozen after review) | Claude | Codex |
| U6 Luna canary | Codex | Claude adjudicates the receipt |
| U7 Permission proof | Codex | Claude adjudicates the receipt |
| U8 Skill-resource proof | Codex | Claude adjudicates the receipt |
| U9 Luna promotion | Claude | Codex |
| U10 Discovery and routing proof | Codex | Claude adjudicates the receipt |
| U11 Stale-claim corrections | Claude | Codex |
| U12 Candidate packaging | Claude | Codex |
| U13 Live seeded-upgrade acceptance | Codex | Claude adjudicates the receipt |
| U14 Integration and merge | Claude | Codex |

**Codex session context is a live constraint.** The session was at 91% of its 258K window after this
review. It needs compaction or a fresh session before U1, and its upstream clone at
`/tmp/codex-0147-analysis.oXEtw0` is machine-local and disposable — U1 pins references from the
manifest, never from that path.

## Requirements

Requirements carry forward from
`docs/brainstorms/2026-08-08-codex-0147-alignment-requirements.md` (R1–R26). Each unit names the R-IDs
it satisfies; the review gate checks coverage against the source document.

## Implementation Units

### U1. Source freeze, contract extension, and classification

Extend the port-manifest contract to express divergent topology, then freeze and classify the source.

**Satisfies:** R23, R24.

**Approach:** The existing manifest contract requires an ancestor base and permits an exact closed
source shape (`scripts/port_contract.py:1104`), with nowhere to store the peeled `rust-v0.146.1`
reference or the two left-only commits. The contract is therefore extended first, with a closed topology
object: left tag and peeled commit, right tag and peeled commit, common base, and left-only commits each
with a disposition. Then bootstrap the manifest and pass classification, including the generated
classification document that classification validation requires.

Pin: peeled `rust-v0.146.1` `79b4f03d3596`, peeled `rust-v0.147.0` `be6e8eac`, common base
`95637f7056835fea66bdd0044414af480fc0fd74`, left-only commits `7558bede75dd` (behavioral backport,
present in 0.147.0) and `79b4f03d3596` (release commit). State the exact upstream pathspecs rather than
instructing the implementer to discover them.

**Files:** `scripts/port_contract.py`, `tests/test_port_contract.py`,
`docs/portability/ports/2026-08-08-codex-0147-alignment.json` (new), generated classification document
(new).

**Test scenarios:** `tests/test_codex_0147_alignment_port_contract.py` (new) — the topology object
round-trips; a manifest missing the common base fails classification; a left-only commit without a
disposition fails; the pre-extension contract still validates existing manifests.

### U2. Contract migration — version constant, schema, projections, and every consumer

One atomic landing. The digest cascade makes partial application incoherent.

**Satisfies:** R1, R2, R3, R4, R9, R10.

**Depends on:** U1.

**Approach:** This is deliberately one unit because the pieces cannot land independently. Adding
projections to `CatalogModel.to_jsonable` changes the normalized digest
(`codex_model_catalog.py:225`), and **all seven** profiles embed that digest
(`render_codex_agents.py:1025`) — not just the two Luna ones. The renderer also requires the old closed
catalog shape (`render_codex_agents.py:903`), and `scripts/capture_codex_runtime_capabilities.py:51`
normalizes catalog rows independently, so a change to `to_jsonable` does not reach it.

Components:

- `CODEX_TARGET_VERSION` in a new `scripts/codex_target_version.py` (constant only, no other imports;
  `scripts/` is importable from both the proof runner and the test suite). Rewire
  `prove_verified_workflows_runtime.py:139` and `tests/test_codex_runtime_capability_snapshot.py:81`.
  Relabel the still-true stale-version messages at `prove_verified_workflows_runtime.py:202` and `:614`.
- **Fix the normalizer first.** `codex_model_catalog.py:26` accepts `{None, "v1", "v2"}` and rejects
  `"disabled"` — but Codex serializes `MultiAgentVersion` with `rename_all = "snake_case"`, so
  `Disabled` is the wire value `"disabled"`. Catalog normalization raises today on the exact value the
  override-filter projection must test. This is a latent bug, not a new requirement.
- The two projections per KTD1, with versioned rule identifiers and a serialized shape carrying root
  and child outcomes explicitly.
- `scripts/render_capability_schema.py` (new) generating
  `docs/validation/codex-runtime-capability-snapshot.schema-r4.json` with its `const` from the constant.
- Every consumer: `capture_codex_runtime_capabilities.py`, the renderer's closed catalog shape,
  `scripts/validate_codex_plugins.py`, `docs/validation/codex-runtime-capability-snapshot.json`, and all
  seven regenerated profiles. Widen `port_contract.py:379` to `{1, 2, 3}`.
- The matrix builder is **not** relabelled here (KTD2); it is handled in U11.

**Files:** `scripts/codex_target_version.py` (new), `scripts/render_capability_schema.py` (new),
`docs/validation/codex-runtime-capability-snapshot.schema-r4.json` (new, generated),
`plugins/fleet-core/scripts/fleet_commons/codex_model_catalog.py`,
`plugins/fleet-core/scripts/fleet_commons/tier_resolver.py`,
`plugins/verified-workflows/scripts/render_codex_agents.py`,
`scripts/capture_codex_runtime_capabilities.py`, `scripts/validate_codex_plugins.py`,
`scripts/port_contract.py`, `docs/validation/codex-runtime-capability-snapshot.json`,
`plugins/verified-workflows/agents/*.toml` (all seven).

**Test scenarios:** `plugins/fleet-core/tests/test_codex_model_catalog.py` — `"disabled"` normalizes
rather than raising; a `v1` model passes the override filter; a `"disabled"` model does not; `None` is
handled explicitly; the collaboration projection serializes root `true` / child `false` for `v1`, both
`true` for `v2`. `plugins/fleet-core/tests/test_tier_resolver.py` — resolution consults the
override-filter projection and never the collaboration one. `tests/test_codex_runtime_capability_snapshot.py`
— an r4 snapshot validates; `schema_version` 3 passes the port contract, 4 is rejected; an r3 artifact
still validates against r3; a regenerated schema matches the committed file (drift test).
`plugins/verified-workflows/tests/test_agent_tier_sync.py` — all seven profiles' embedded digests match
the new normalized catalog.

### U3. Developer-instruction contract

Prove the setting stays absent across every shipped configuration surface.

**Satisfies:** R8.

**Depends on:** U1.

**Approach:** Assert `features.multi_agent_v2.subagent_developer_instructions` is absent from
`.codex/config.toml` and from **every plugin-shipped configuration surface**, that all seven profiles
retain non-empty `developer_instructions`, and that the boolean feature form survives at
`.codex/config.toml:8` (line 6 is the `[features]` header). Record the semantics — unset inherits,
blank clears, role-specific instructions win.

**Files:** `scripts/validate_codex_plugins.py`, `plugins/verified-workflows/README.md`,
`plugins/verified-workflows/PORTABILITY.md`.

**Test scenarios:** `tests/test_validate_codex_plugins.py` — a **configuration** fixture carrying the
key fails the validator (the key is a config key, not a profile key); the validator scans all shipped
configuration surfaces, and a new surface added without coverage fails.
`plugins/verified-workflows/tests/test_agent_tier_sync.py` — all seven profiles carry non-empty
developer instructions.

### U4. Policy source collapse

Make the execution class the single policy source the renderer consumes.

**Satisfies:** R5 (structure only; the model change is U9).

**Depends on:** U2.

**Approach:** Map each managed profile to its Fleet execution class and have `render_codex_agents.py`
consume the class policy instead of its own `PROFILE_POLICY` literals, per KTD4. This lands before any
model change so the collapse is provable against unchanged behavior: every rendered profile must be
byte-identical before and after. Replace the hardcoded expectation at `test_agent_tier_sync.py:57` with
an assertion against the class policy rather than editing it to a new literal.

**Files:** `plugins/verified-workflows/scripts/render_codex_agents.py`,
`plugins/fleet-core/scripts/fleet_commons/models.json`,
`plugins/verified-workflows/tests/test_agent_tier_sync.py`.

**Test scenarios:** `plugins/verified-workflows/tests/test_agent_tier_sync.py` — rendered profiles are
byte-identical to the pre-collapse bytes for all seven; a class-policy change moves the rendered profile
with no renderer edit; a profile with no mapped class fails loudly.

### U5. Proof harness — built, cross-reviewed, then frozen

One harness for every live proof, frozen before any receipt is produced.

**Satisfies:** enabling infrastructure for R15–R21.

**Depends on:** U2.

**Approach:** The proofs cannot be evidence if the engine producing them is also changing the
instrument (KTD8). Build the harness once, cross-review it, freeze it, and record its digest in every
receipt. Any later harness change invalidates and reruns the affected proofs.

The harness must add what the current one cannot do. `prove_verified_workflows_runtime.py:257` infers
observed tool calls from rollout rows; it cannot read the model-visible tool specification. Name and
implement the tool-plan capture route — an app-server harness against the installed binary — plus a
separate runtime negative probe. Add an execution-environment fixture for executor-backed `skill://`
resources, which is a different mechanism from a host-installed plugin reference.

Every receipt records the harness digest, the observed Codex version (KTD2), and a stable case
identifier per matrix row.

**Files:** `scripts/prove_verified_workflows_runtime.py`, `tests/conftest.py`.

**Test scenarios:** `tests/test_prove_verified_workflows_runtime.py` — a receipt without a harness
digest is refused; a receipt whose harness digest differs from the frozen value is refused; the tool-plan
capture returns a specification, not an inferred call list; a receipt missing a declared case identifier
fails rather than passing silently.

### U6. Luna canary

Prove per-profile whether Luna is fit, against an oracle fixed before the run.

**Satisfies:** R15, R16, R17.

**Depends on:** U5.

**Approach:** Fix the oracle first, as a table per profile: exact fixture paths, corpus entries,
expected observations, response schema, repetition count, the zero-false-negative set, minimum recall,
transport-failure allowance, and the pass comparison against Terra. Nouns are not an oracle; two
planners must derive the same gate from it.

Cases: instruction adherence, typed-result schema validity, cold resume preserving canonical child
identity with restored model and provider, and an unknown-provider negative. Collaboration-tool absence
comes from the tool plan plus the runtime negative probe (KTD7). Results are recorded **per profile**
into the receipt artifact KTD5 defines.

**Files:** `docs/validation/codex-0147-luna-canary.json` (new).

**Test scenarios:** `tests/test_prove_verified_workflows_runtime.py` — the receipt is rejected when any
oracle field is missing; tool-absence evidence sourced from behavior alone is rejected; an
unknown-provider fixture produces the expected failure; a receipt asserting a pass for a profile with no
recorded fixture run fails.

### U7. Turn-environment permission proof

Exercise permission inheritance against a full case matrix with a blocking stop rule.

**Satisfies:** R11, R12, R19.

**Depends on:** U5.

**Approach:** Every matrix row carries a stable case identifier and an exact expected tuple; a missing
or duplicate case fails the proof. Rows: read-only turn; workspace-write turn; multiple workspace roots;
spawn after role application; cold resume under current runtime permissions; later-turn permission
updates; and no widening beyond the parent turn.

Capture effective model, effort, provider, permission profile, sandbox, current directory, and workspace
roots (R12). Environment identity is captured only if an app-server route is authorized —
`TurnContextItem` does not persist an environment identifier, so the durable tuple is the default.
Capture the approval reviewer exactly, with explicit negative controls for both `user` and `auto_review`
(R11): `user` is necessary where command approval applies but never sufficient as operator authority,
and `auto_review` disqualifies runtime approval from being read as operator approval at all.

Any mismatch blocks source-ready. Permission drift is never remediated by a model fallback (KTD6).

**Files:** `docs/validation/codex-0147-permission-inheritance.json` (new).

**Test scenarios:** `tests/test_prove_verified_workflows_runtime.py` — one test per matrix row asserting
its expected tuple; a missing row fails; a duplicate case identifier fails; a child widening beyond its
parent fails and is reported as blocking; a receipt recording `auto_review` as operator authority fails.

### U8. Skill-resource proof

Verify host-installed references and executor-backed resources as distinct mechanisms.

**Satisfies:** R18.

**Depends on:** U7.

**Approach:** These are different mechanisms and conflating them is a repeat finding. A host-installed
plugin's `references/` file is host-backed and not subject to the fail-closed sandbox-context change.
Executor-backed `skill://` resources are. Verify each separately.

Executor rows: permitted roots, denied roots, multiple workspace roots, discovery-time denial versus
read-time denial, and recovery after a turn-scoped permission grant. Pin the expected denial text and
prove no denied content leaks.

**Files:** `docs/validation/codex-0147-skill-resources.json` (new).

**Test scenarios:** `tests/test_prove_verified_workflows_runtime.py` — a permitted executor read
succeeds; a denied one fails closed with the pinned message and no content; discovery-time and read-time
denials are distinguished; a permission grant recovers the read; a proof treating a host-installed
reference as executor-backed is rejected.

### U9. Luna promotion

Repair the unreachable gate and promote per profile on its own receipt.

**Satisfies:** R5, R6, R7.

**Depends on:** U4, U6.

**Approach:** Repair the predicate at `render_codex_agents.py:986` to consult U2's override-filter
projection instead of testing the raw catalog value for equality with `"v2"`. Replace the pair-wide
`--luna-v2-canary-passed` boolean with the per-profile receipt artifact (KTD5), so `scan_low` can
promote while `monitor_low` does not. Because U4 collapsed the sources, promotion is a single change to
the execution class consumed by rendering. Regenerate both profiles through the renderer, never by hand.
Record the non-delegating-leaf behavior as a derived runtime expectation of effective model plus session
position, not a profile property.

**Files:** `plugins/verified-workflows/scripts/render_codex_agents.py`,
`plugins/verified-workflows/scripts/sync_codex_agents.py`,
`plugins/fleet-core/scripts/fleet_commons/models.json`,
`plugins/verified-workflows/agents/scan_low.toml`,
`plugins/verified-workflows/agents/monitor_low.toml`.

**Test scenarios:** `plugins/verified-workflows/tests/test_agent_tier_sync.py` — with a passing receipt
and a `v1` Luna entry, promotion **succeeds** (the branch that has never run; today it raises); with no
receipt, both stay on Terra; asymmetric receipts promote exactly one profile, tested in both directions;
a `"disabled"` Luna entry refuses; a non-selectable entry refuses; an entry missing the requested effort
refuses; a forged receipt failing validation refuses.

### U10. Discovery and routing proof

Prove discovery and routing survive the 0.147 skill-discovery refactor.

**Satisfies:** R20, R21.

**Depends on:** U5.

**Approach:** `tests/test_explicit_skill_invocation.py:17` only checks that Saga and Verified Workflows
are explicit-only — it does not resolve every plugin, and nothing covers implicit routing or search
scopes. Add a dedicated discovery and routing module with safe non-mutating prompts. Validate all ten
tracked manifests, the applicable Global / Workspace / Personal search scopes, and isolated
source-plugin discovery. Distinguish "skill was offered" from "skill executed". Confirm custom agent
profiles still require separate synchronization.

**Files:** `tests/test_discovery_and_routing.py` (new),
`docs/validation/codex-0147-discovery-routing.json` (new).

**Test scenarios:** `tests/test_discovery_and_routing.py` — explicit invocation resolves for each of the
ten tracked plugins; implicit routing surfaces the expected skill and the assertion distinguishes
offered from executed; each applicable search scope resolves; a plugin removed from the manifest stops
resolving.

### U11. Stale-claim corrections and negative inventory

Correct current claims, preserve dated records, and re-establish matrix provenance.

**Satisfies:** R13, R14, R22.

**Depends on:** U9.

**Approach:** Inventory every location carrying the superseded Luna conclusion with one of three
dispositions: update a current operational claim; append a superseding dated entry beside a dated
historical record; or preserve historical evidence unchanged.

Dated records that stay unmodified: `plugins/verified-workflows/CHANGELOG.md:17`, and
`docs/portability/matrix.md:45` — that line sits **inside** the dated 2026-07-29 note and is historical,
so it earns an appended superseding note rather than an edit.

Current claims to update: `docs/validation/codex-v2-orchestration-matrix.json:45` (the reason string;
line 41 opens the object), `scripts/build_codex_v2_orchestration_matrix.py:71-72` (the Terra entries)
and `:520` (the superseded reason), `plugins/verified-workflows/README.md:80`, and
`plugins/fleet-core/references/tier-palette.md:45`.

Matrix provenance (KTD2): the builder's observed `0.145.0` at `:509` is not relabelled. Either rerun the
full matrix on 0.147.0 and stamp the observed version, or introduce per-row provenance so reproved rows
are distinguishable from inherited ones. Relabelling without rerunning falsifies the record.

Record the no-change rows with their evidence: `codex exec --full-auto`, MCP 2026-07-28, Apps,
tool-registry collision policy, symlink handling, and portable Agent Plugin packaging.

**Files:** the locations above, `scripts/build_codex_v2_orchestration_matrix.py`,
`tests/test_build_codex_v2_orchestration_matrix.py`,
`docs/validation/codex-0147-negative-inventory.json` (new).

**Test scenarios:** `tests/test_claim_inventory.py` (new) — every inventoried location has a recorded
disposition; a current-claim surface still asserting Luna is unavailable fails; the dated changelog line
and the dated matrix note are byte-unchanged; generated matrix content comes from its builder.
`tests/test_build_codex_v2_orchestration_matrix.py` — the observed version is captured, not asserted
from the target constant.

### U12. Candidate packaging

Freeze the exact bytes that live acceptance will install.

**Satisfies:** R25, R26.

**Depends on:** U3, U10, U11.

**Approach:** Packaging must precede acceptance, or acceptance validates bytes that later change. Bump
Fleet Core `0.14 → 0.15` and Verified Workflows `3.0 → 3.1` with one packaging timestamp suffix — minor
increments, because behavior changes without breaking the documented interface. If any unit proves a
third plugin's behavior changed, packaging **stops for plan amendment** rather than the implementer
choosing a version. Write the version-policy sidecar, sync plugin manifests,
`.agents/plugins/marketplace.json`, and `docs/portability/matrix.md`. Freeze and record a candidate
content digest.

**Files:** `plugins/fleet-core/.codex-plugin/plugin.json`,
`plugins/verified-workflows/.codex-plugin/plugin.json`, both `CHANGELOG.md` files,
`.agents/plugins/marketplace.json`, `docs/portability/matrix.md`,
`docs/portability/ports/2026-08-08-codex-0147-version-policy.json` (new).

**Test scenarios:** `tests/test_validate_codex_plugins.py` — manifest versions match the marketplace
inventory; the portability matrix agrees with the manifests; a sidecar missing a changed plugin fails; a
third changed plugin without a plan amendment fails.

### U13. Live seeded-upgrade acceptance

Install the candidate into an isolated home and prove the real upgrade path, not just a clean install.

**Satisfies:** end-to-end confirmation of R5–R8 and R15–R21.

**Depends on:** U12.

**Approach:** This unit is **execution only**. It runs the frozen U5 harness against the frozen U12
candidate and produces a receipt; Claude adjudicates it (KTD8). No harness or packaging changes here —
either would invalidate the acceptance.

Isolation, stated exactly because the earlier draft was wrong. `sync_codex_agents.py:155` requires
`--isolated-target` to accompany an explicit `--target-dir`; an absolute `CODEX_HOME` is **not** an
alternative, and if `CODEX_HOME` names the same directory the resolver treats it as active and refuses
to mark it isolated. The invocation keeps the sync process's active `CODEX_HOME` distinct and passes
`--target-dir <isolated-home>/agents --isolated-target`, parses and binds the `--dry-run` pre-state
digest, then applies. `--allow-real-profile` is withheld throughout.

Rollback is defined explicitly: `recover_sync` (`sync_codex_agents.py:1533`) repairs an incomplete
transaction or cleans a committed one — it does **not** undo a successful apply. Real rollback is
reinstalling the seeded prior state and proving the isolated home matches its recorded digest.

The isolated home is provisioned with its own configuration and authenticated through supported login.
Credentials are never copied or symlinked.

Sequence — the upgrade path is what matters, because a clean install can pass while an upgrade retains
stale cache entries or Terra profiles:

1. **Seed** — install the previously released versions into a separately authenticated isolated home.
2. **Baseline** — run a fresh process against that seeded home from a **neutral fixture directory**,
   not this repository. A session started inside this repo can resolve workspace-scoped plugins from
   repository source instead of the staged cache, which passes against the wrong bytes. The existing
   `tesing-codex` pane runs Full Access inside this repository and is therefore **not** usable as a
   controlled baseline.
3. **Upgrade** — upgrade that same home to the exact U12 candidate digest.
4. **Fresh process** — spawn a new Herdr pane with the isolated home, from the neutral directory. Codex
   pins the catalog-selected tool schema at startup, so a pre-existing process cannot see the change.
5. **Acceptance** — profile roster and per-profile model; readback identity; non-delegating leaf from
   the tool plan; skill routing; host-installed and executor-backed resource reads; and a no-regression
   diff against the baseline.
6. **Rollback** — restore the seeded state and prove the isolated home matches its recorded digest.

Record installed paths, manifest versions, and content digests proving resolution came from the isolated
cache rather than repository source. Teardown removes the isolated home; `~/.codex/` is never written.

**Files:** `docs/validation/codex-0147-live-acceptance.json` (new).

**Test scenarios:** `plugins/verified-workflows/tests/test_sync_codex_agents.py` — `--isolated-target`
without `--target-dir` raises; a target equal to the active `CODEX_HOME` refuses isolation; `--dry-run`
mutates nothing; the bound pre-state digest is required by apply.
`tests/test_prove_verified_workflows_runtime.py` — an acceptance receipt missing any check fails; a
receipt whose resolved plugin path is not under the isolated cache fails (the workspace-shadow guard); a
receipt whose candidate digest differs from U12's frozen value fails; rollback verification compares
against the seeded digest.

### U14. Integration and merge

Carry the change to a merged PR — the destination is `merge`, not source-ready.

**Satisfies:** completion of the mandatory port lifecycle.

**Depends on:** U13.

**Approach:** The port runbook requires more than the classification gate: per-unit gates, release
review, and the cutover gate. Run paired code review across both engines, validate the cutover gate,
create a branch and PR, reach green CI, merge, verify `origin/main` contains the merge, and close out to
a clean worktree. Daily-profile installation and marketplace publication stay out of scope.

No behavior or packaging change may land after U13 without repeating acceptance; if review forces one,
U12 and U13 rerun.

**Files:** port manifest cutover fields, PR body.

**Test scenarios:** full suite green on the branch; `python3 scripts/validate_codex_plugins.py` clean;
`test expectation: none` for the merge mechanics themselves — verification is the CI result and the
post-merge `origin/main` check.

## Scope Boundaries

- Migrating the ten tracked manifests to the portable Agent Plugin format. It adds no capability this
  repository needs and does not replace the separate profile-synchronization path.
- Populating `features.multi_agent_v2.subagent_developer_instructions`, or changing the boolean feature
  form at `.codex/config.toml:8`.
- Installing into the operator's Codex profile tree (`~/.codex/agents`), and marketplace publication.
  Installation into an isolated, separately authenticated home is required by U13.
- Any change to logical role definitions or `plugins/verified-workflows/config/role-registry.yaml`.
- Re-proving orchestration matrix rows 0.147.0 did not touch. Permission, resume, model-selection, and
  skill-resource rows *are* touched and are in scope.

### Deferred to Follow-Up Work

- Whether a discovered permission defect is repaired in-round when it is repository-owned harness code,
  versus stopping the round when it is native Codex behavior. U7 stops the round either way.
- Whether environment identity warrants a permanent app-server route or the durable tuple suffices.

## Risk Analysis & Mitigation

**U13 is the highest implementation and operational risk.** It installs software, in an isolated home,
against a live authenticated session, and a mistake can write the operator's real profile tree — where
seven managed profiles live right now. Mitigations: `--allow-real-profile` withheld; `--dry-run` before
every `--apply` with the pre-state digest bound; tests asserting an isolated target never resolves to
`~/.codex/agents`; and the workspace-shadow guard proving resolution came from the isolated cache.

**U7 is the highest behavioral risk.** It crosses discovery, environment selection, filesystem roots,
child inheritance, and installed-versus-source paths, and can pass unit tests while failing under a real
managed profile. Mitigation: the case matrix is fixed before the run and any mismatch blocks.

**U2 is a wide atomic change.** It touches the catalog, the renderer, the capture script, the validator,
the schema, the committed snapshot, and all seven profiles, because the normalized digest cascades.
Splitting it produces a repository that does not validate at the split point. Mitigation: land it as one
reviewed change, with the byte-identical assertion in U4 immediately after to prove the collapse changed
nothing else.

**U9 turns on code that has never run.** The promotion success branch is unreachable today, so no test
exercises it. Mitigation: its scenarios cover the success branch and both asymmetric per-profile cases,
not only the refusal branches that pass now.

**The working tree is not clean.** `main` is behind its remote with uncommitted work from concurrent
sessions. Work begins in a clean worktree from the agreed integration base.
