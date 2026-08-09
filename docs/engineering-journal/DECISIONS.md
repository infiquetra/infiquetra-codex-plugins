# Decisions

## 2026-08-09: Committed Profile Bytes Are The Unpromoted Rendering; A Deviation Is Applied At Install

Promoting the two low-cost profiles onto the Luna model is a deviation from what their Fleet Core
execution class states. It has to be recorded somewhere, and there were two places it could live:
in the committed `plugins/verified-workflows/agents/*.toml` bytes, or in the install step that
writes profiles into a Codex home.

Putting it in the committed bytes was tempting, because the canary receipt is itself a committed,
reviewed artifact — its presence in the repository is a deliberate decision, not an ambient file.
It was rejected for two reasons. The receipt states plainly that quality was never measured
(`eligible-on-measured-criteria` means one criterion passed and nothing else was tested), so making
Luna the default byte set would ship an unmeasured model to every run of every scanner and monitor
role. And it collides with the staleness check: `check_generated` requires committed source to equal
the rendered bundle, so a promoted bundle would be reported as stale source.

**Decision.** Committed profile bytes are by definition what the renderer produces with **no**
receipt. Promotion is requested at sync time with `--luna-canary-receipt PATH`. The staleness check
still runs on every sync, against a second, unpromoted rendering — not skipped whenever a receipt is
supplied, which would have dropped the check on exactly the runs that install a deviation.

**Rejected alternatives.** (1) Promote in committed source and let the receipt's presence drive it —
rejected above. (2) Skip `check_generated` when a receipt is passed — this silently disables the
staleness check on the highest-risk runs. (3) Give the renderer CLI its own receipt flag — this would
let `--write` produce promoted bytes and destroy the invariant that makes (2) unnecessary.

**Revisit when** the canary receipt records a measured quality criterion for a profile. At that point
promotion stops being an unmeasured deviation, and defaulting the committed bytes to the promoted
model becomes arguable on its merits.

## 2026-08-09: A Negative Finding Is Not Recorded Until Someone Competent Has Tried To Break It

This session searched for the surface that renders Codex's model-visible tool specification, failed
to find one, and drafted a plan amendment saying no such surface exists in 0.147.0. The evidence
looked good: `codex debug prompt-input` returns prompt messages and is byte-invariant to the
MultiAgent V2 feature flag; a scan of all 246 app-server v2 protocol surfaces found no tool list on
any thread or turn response; `TurnStartParams` accepts thirteen fields and none of them is tools.

The claim was dispatched to the cross-review engine with instructions to refute rather than confirm
it, and it was refuted. The specification is assembled by `router.model_visible_specs`
(`codex-rs/core/src/session/turn.rs:1223-1239` at tag `rust-v0.147.0`) and, under Responses Lite,
serialized as an `additional_tools` **developer input item** while the request's top-level `tools`
property stays empty (`codex-rs/core/src/client.rs:820-848`). Every search had been for a property
named `tools`. It was in an input item.

**Decision.** A negative finding about runtime capability is not recorded until an independent
reviewer has been asked to break it, and the request says *refute*, not *check*. Confirmation-shaped
review of a negative finding produces agreement, because absence is exactly what a confirming search
finds. This is not a general rule about all findings: a positive claim carries its own evidence and
fails visibly when wrong. A false absence does not fail at all. It quietly authorises a substitute.

**What it would have cost.** The amendment would have withdrawn a capture route that works, replaced
it with a substitute, and handed six downstream proof units an inference where a measurement was
available. Nothing later in the round would have contradicted it, because nothing later looks for a
surface the plan says is absent.

**Second-order.** The same review rejected two candidates this session had been ready to record as
supporting evidence. `codex debug prompt-input` is worse than useless as a tool-plan substitute
because its collaboration prose survives when the collaboration tools are not offered — it would read
as a capability being present. It was deleted rather than left available. `codex features list` is
real evidence of effective feature state and was kept, but its docstring now says explicitly that it
is not evidence about tools.

**Revisit when.** Never, as far as the rule goes. The narrower operational part — which command
captures the specification — is version-bound and re-derived by the harness rather than remembered,
which is the point.

## 2026-08-09: The Execution Class Is The Only Place A Managed Profile's Model And Effort Are Stated

Each of the seven managed Verified Workflows profiles carried its own model and effort in a
`PROFILE_POLICY` dictionary in `plugins/verified-workflows/scripts/render_codex_agents.py`, while
Fleet Core's `execution_classes` in `plugins/fleet-core/scripts/fleet_commons/models.json` stated
the same policy for its own consumers. Two sources, no binding between them: a Fleet Core policy
change moved nothing in the rendered profiles, and nothing failed to say so. That is the same
freeze-and-restate shape this alignment round exists to remove, one layer up from the catalog
facts that motivated it.

**Decision.** The execution class is the single source. `render_codex_agents.py` now maps each
profile to exactly one class by name and reads the model and effort from that class at render
time, through `fleet_commons_shim.load("tier_palette")`. The plugin keeps only two things of its
own: the profile-to-class mapping, and the operator-facing description text rendered into the
profile. The class carries its own description written for the Fleet Core policy reader; those
two descriptions have different audiences and are deliberately not merged.

**Scope of the freshness claim, stated exactly.** The renderer holds no copy of its own and asks
`tier_palette` on every render. `tier_palette` itself reads `models.json` once per process and
freezes the derived policies, so a policy edit takes effect on the **next run**, not mid-process.
That per-process freeze is correct rather than a limitation: reloading between two profiles in one
bundle would let a single render emit two different policies. The claim U4 earns is "no second copy
in the plugin, and no plugin edit needed to adopt a policy change" — not live reload.

**Three failure modes, all loud.** A profile with no mapped class fails the roster check. A profile
naming a class Fleet Core does not define fails with the class name in the message. And a
`ProfileResolution` whose model or effort departs from its class fails at render unless it names a
reason in `PROFILE_POLICY_DEVIATIONS` — today only the Luna canary, which substitutes a model and
never an effort. That last check exists because `render_profile` is public and takes a
caller-supplied resolution: without it the single-source claim would have held only for resolutions
this module built, which a cross-engine review demonstrated by rendering `work_high` as
`gpt-5.4-mini` / `low` against a class that says `gpt-5.6-sol` / `high`.

**Proved by byte identity, not by argument.** The seven rendered profile digests were captured
before the change and pinned in `plugins/verified-workflows/tests/test_agent_tier_sync.py` as
`PRE_COLLAPSE_PROFILE_SHA256`. All seven are byte-identical after it. A collapse that changed what
gets rendered would be a model change wearing a refactor's clothes; this one is not.

**Two classes had to be created.** Seven profiles mapped to five classes: `work-high` and
`work-medium` had no Fleet Core class at all. Both were added to `models.json`, which extends
shared Fleet Core vocabulary rather than a plugin-local list — the operator approved that
explicitly.

**Rejected alternative: renumber `order` into cost order.** Appending the two classes at ranks 5
and 6 places an expensive `gpt-5.6-sol` / `high` class after the cheap `monitor-low`, which looks
wrong if `order` is read as a cost ranking. It is not one. `order` exists so the derived class
tuple is deterministic and so a duplicate or gap fails loudly; the only consumers are
`_derive_ordered` and one pinned roster test. Renumbering would have changed ranks for five
existing classes to encode a meaning nothing reads. Appending changes none of them. The semantic
is now stated in `plugins/fleet-core/references/tier-palette.md` so the next reader does not have
to re-derive it.

**Revisit when.** Something starts reading `order` as a ranking — a cost report, a preference
walk, a fallback ladder across classes. At that point the meaning has genuinely changed, ranks
must be assigned deliberately, and the reference note above becomes wrong rather than merely
incomplete.

## 2026-08-08: Model Eligibility Is One Catalog Fact Plus Two Derived Projections

Codex 0.147.0 relaxed the MultiAgent V2 model gate from "the catalog must report `v2`" to "the catalog
must not report `Disabled`" (`codex-rs/core/src/tools/handlers/multi_agents_common.rs`, function
`model_supports_multi_agent_backend`). Luna is catalogued `v1`, so it moved from rejected to accepted as
a V2 child.

The repository had stored that runtime observation as a permanent property. `CatalogModel.selectable` at
`plugins/fleet-core/scripts/fleet_commons/codex_model_catalog.py:55` never consulted
`multi_agent_version`; the exclusion was frozen into policy data as `"preferred": {"model":
"gpt-5.6-terra"}` on the `scan-low` and `monitor-low` execution classes in `models.json`, then restated
in the renderer, the generated profiles, the validation matrix, and four prose documents. None of those
restatements could notice the gate had changed.

Only the catalog's `multi_agent_version` is an independent source fact. Both values the repository needs
are derived from it by rules Codex owns: passing the V2 explicit-model override filter (true unless the
catalog says `Disabled`), and receiving collaboration tools (a V2 root always; a V2 child only when its
own model reports `v2`, per `codex-rs/core/src/tools/spec_plan.rs:533-543`). The projections carry
versioned rule identifiers and Codex provenance so a future rule change is detected rather than silently
mis-read.

A Luna child is therefore a non-delegating leaf — correct for bounded scanning and allowlisted
observation, which should not delegate. That is a derived runtime expectation of effective model plus
session position, never a permanent property of a profile.

Rejected: modelling the three values as independent facts, which repeats the original defect in a new
shape; and treating this as a text correction, which leaves the conflation in the data model.

Revisit when Codex changes either derivation rule, or when Luna's catalog entry reports `v2` — at which
point the collaboration expectation inverts and the rule identifiers should surface it.

Plan: `docs/plans/2026-08-08-codex-0147-alignment-plan.md`.

## 2026-08-08: One Sourced Codex Version Constant Replaces Four Hard Pins

The Codex version was hard-pinned as an exact string in four independent places: the proof runner
(`scripts/prove_verified_workflows_runtime.py:139`), two test assertions
(`tests/test_codex_runtime_capability_snapshot.py:81` at `0.146.0` and
`tests/test_build_codex_v2_orchestration_matrix.py:28` at `0.145.0` — already drifted apart), and a JSON
Schema `const` in `docs/validation/codex-runtime-capability-snapshot.schema-r3.json`. The proof runner
raises on any other value, so the tooling could not run against a 0.147.0 snapshot at all.

A single `CODEX_TARGET_VERSION` now feeds all four, with the schema file generated rather than
hand-edited. The capability snapshot moves to a new revision (`schema-r4.json`, `schema_version` 3)
because the repository already uses revision files as its idiom and an explicit revision makes outside
breakage visible; `scripts/port_contract.py:379` widens from `{1, 2}` accordingly.

Rejected: re-pinning the four literals to `0.147.0`, which is what every prior round did. It keeps each
gate independently readable and the diff small, but rebuilds the same four-place restatement — the exact
pattern that let the superseded Luna claim persist. The two assertions having already drifted to
different versions is the evidence that restatement does not hold.

Revisit when the generation step proves more costly than the drift it prevents, or if a consumer needs
to pin a different version than the repository targets.

Plan: `docs/plans/2026-08-08-codex-0147-alignment-plan.md`.

## 2026-08-02: Hermes Profile Evolution Remains A Thin Codex Adapter

The Codex plugin calls Team Mimir's real classifier and canonical `hermes profile-request` instead
of copying custody policy or command schemas. Pinned producer fixtures define the closed response
keys, bounds, and exact doctor fields. Ordinary repository work does not contact Hermes. Governed
file edits intercepted by Codex receive a native advisory stop and target-addressed dialogue
suggestion; the documentation explicitly excludes shell, external-editor, disabled-hook,
untrusted-hook, same-user, and root enforcement. Conversation requests are bounded JSON on standard
input and are never queued or persisted by this adapter.

## 2026-08-01: Harness Integration Is A Logical Role, Not A Compute Profile

Verified Workflows adds `harness-integration-engineer` for assignments that connect producer-owned
contracts to a native harness. The role discovers native extension seams, keeps adapters thin,
declares unsupported behavior, exercises adversarial compatibility cases, and updates approved
release metadata. It defaults to the existing `work_high` compute profile; the managed profile set,
model choices, and reasoning efforts remain unchanged. The compiler binds the role lens bytes into
workflow authority and therefore into the operator approval digest.

## 2026-08-01: Delegated Git Publication Replaces Root-Only Git Ownership In Verified Workflows

Verified Workflows deletes the capability layer it invented rather than trying to make it truthful.
The per-role `workspace_cap`, `external_cap`, and `external_mutation` declarations, the
`allowed_profiles` membership check, the `ROOT_ONLY_ACTIONS` constant, the per-profile `workspace`
and `external` keys, and six compiler refusals built on them are removed. Three came out of
`render_codex_agents.py`: the `profile transition violates KTD4` assert, the `boundary cap violates
its category contract` check, and the `allowed_profiles` gate inside `resolve_role`. Three came out
of `workflow_dispatch.py`: a read-only profile may not declare writes, a non-Git role may not name a
Git command in its completion condition, and a fallback may not cross its profile's boundary. A
seventh was rewritten rather than deleted — the fallback check that read `role.allowed_profiles` now
tests membership in `PROFILE_IDS`. An assignment may select any member of `PROFILE_IDS`.

**What this changed for a publication assignment is narrower than the issue framing suggests, and
the record should be exact.** A `git-integration-operator` row whose completion condition names
`git push` and `gh pr create` *already compiled before this change*. The deleted guard read
`if GIT_WORD_RE.search(completion) and not owns_git`, and `owns_git` was true for that role, so it
never applied to the Git operator at all (pre-change `workflow_dispatch.py:314-318` at `0c20724`).
Three things did change for that role: it is no longer pinned to `work_medium` and may select any
managed profile; a non-Git role may now name Git or `gh` in a completion condition; and the rendered
`work_medium` profile no longer instructs the child "Do not run Git unless the role is
`git-integration-operator`."

The reason for the removal is that none of it was ever enforced. Codex 0.146 children inherit the
parent turn's effective permission profile, so a profile can neither widen nor narrow what a child
may do (`plugins/saga/references/operator-choice.md`), and a generated `agents/*.toml` carries no
key that a sandbox or network layer reads. The declared capability string was only ever compared
against a hardcoded constant inside the plugin's own compiler. That argument is verified from source
and is what this decision rests on.

**The Hermes anecdote does not support the conclusion it was cited for.** Issue 71 reports that
during the Hermes profile self-sovereign evolution workflow the compiler assigned publication to
`git-integration-operator`, the agent committed, and then could not push or open the pull request,
and concludes that declared policy rather than authentication was the blocker. Neither removed
mechanism can have produced that failure: the compiler's Git-word refusal exempted
`git-integration-operator` by construction, and the `work_medium` instruction text exempted it by
name. No run record for that failure exists under `~/.codex/verified-workflows/state/`, so its
actual cause is unestablished. The issue's stop condition fires only if a red-first reproduction
shows the Codex harness itself refused; the reproduction showed neither that nor a compiler refusal,
so the work proceeded. Whoever next touches this should treat the Hermes cause as an open question
and not as settled precedent.

This supersedes the 2026-07-24 decision "Codex V2 Owns Live Execution And Verified Workflows Becomes
A Minimal Kernel" in one specific respect: its assertion that the main Codex session "owns workflow
preview, approval binding, dependency release, integration, Git, gates, merge, installation,
rollback, and completion" no longer holds for Git and integration inside a dispatched workflow. Root
remains the orchestrator, the gate evaluator, and the approval boundary; it is no longer the only
actor that may run Git or GitHub commands during a run. The rest of that decision — the V2 kernel,
the canonical tables, the managed profiles, the run record, the external-action control plane —
stands unchanged.

The 2026-07-18 decision "Feasibility Review Keeps Root-Owned Workflows Usable" is not superseded
here, because it was already conditionally superseded by the 2026-07-24 decision, which stated it
would take effect "after the U8 live cutover gate passes." That gate passed. The QA record
`docs/qa/qa-task-codex-v2-orchestrated-execution-system-2026-07-24.md` returns verdict PASS across
installed-byte readback, six managed profiles, a fresh-session V2 proof, an attended rollback drill,
and a reapply smoke, and PR #46's merge commit `74258be` is present on `main`. So the operative
predecessor on 2026-08-01 is the 2026-07-24 entry, and the 2026-07-18 entry is already historical;
this decision does not supersede it a second time.

**The weak link, stated on the record.** The 2026-07-18 decision let native children leave advisory
status only if "a runtime can provide authenticated host-issued child attestation." Codex ships
nothing under that name. What it ships is combined `session_meta` and `turn_context` readback on the
canonical agent path, which root must match against the approved path, profile, model, effort,
provider, permission profile, sandbox, and V2 mode before it accepts an assignment
(`plugins/verified-workflows/skills/run/references/workflow-protocol.md`). This decision reads that
readback as satisfying the 2026-07-18 condition: it is host-reported rather than child-reported, and
a mismatch fails visibly. The honest gap is that it proves *identity*, not *confinement* — it tells
you which agent ran, and cannot show that the host held that agent inside a narrower boundary,
because on 0.146 the child inherits the parent turn's permission profile outright. It was also first
proved on 0.145.0 at cutover and carried forward to 0.146. A future reader may reasonably conclude
that the 2026-07-18 condition was never actually met and that this decision relaxed it rather than
satisfied it. That disagreement is recorded rather than resolved.

**One nearby decision survives and still governs this change.** The 2026-07-17 decision "Normalize
Subject-Exclusion Parent Links And Bootstrap Self-Hosting Fixes Manually" holds that Verified
Workflows cannot grant gate authority to changes in its own implementation, and that self-hosting
patches keep root ownership of implementation, integration, Git, release, and installation. This
change is exactly that category — Verified Workflows editing itself — so the root session performs
every Git operation for it and children remain advisory here, even though the plugin no longer
forbids delegated publication in ordinary workflows. Do not read the relaxation above as reaching
self-hosting work. (This is a different entry from the 2026-07-17 "Force Sol And Terra Back To
MultiAgent V1 Temporarily" catalog policy, which is the 2026-07-17 policy the 2026-07-24 decision
superseded.)

Nothing else in the execution path moves. The dependency graph, the concurrent-writer overlap check,
typed results, runtime identity readback, gate evaluation, reviewer independence, and the
`git diff --name-only` completion requirement are unchanged. An undeclared changed path now
validates and carries a synthesized finding instead of raising `ResultContractError`, so the
evidence is still recorded — it just no longer refuses the result.

**Rejected alternatives:** a conditionally publication-capable `work_medium`, and a dedicated
publication profile. Both assume a profile can carry permission, which it cannot on Codex 0.146, so
each would have shipped a second unenforceable claim in place of the first.

**Revisit when:** Codex gives a profile an enforceable permission or sandbox key, or emits a signed
child attestation distinct from readback. Either would make a declared per-role capability a control
again rather than prose, and delegated Git could then be bounded by something the host actually
reads.

Plan: `docs/plans/2026-08-01-verified-workflows-capability-policy-removal-plan.md`.

## 2026-07-30: Frozen-Source Port Oracles Resolve Through Git's Common Directory And Fail Closed

The two current frozen-source port contracts must not derive the Claude checkout from the active worktree's parent. A clean detached worktree lives outside the sibling checkout layout, so that rule skips eight source-oracle tests in the same full-suite command that is used as the repository gate.

The shared pytest resolver first honors `CODEX_PORT_SOURCE_REPO`. Without it, it reads the current clone's absolute Git common directory, derives the primary clone's sibling directory from the manifest source repository identifier, and validates the candidate's normalized `origin` identity. This locates the normal sibling checkout even when the active worktree is elsewhere, while refusing an unrelated Git repository.

When neither route produces the expected source checkout, the oracle fails with the override name rather than skipping. A source-free environment cannot re-derive frozen source truth; a red gate is accurate and a green gate with that evidence missing is not.

**Rejected alternatives:** retaining skips with clearer text (the gate remains passable without the oracle); hard-coding a machine-local path or adding a repository-local path registry (neither is portable); and changing `scripts/port_contract.py` (the sealed validator is outside this test-resolution defect).

Plan: `docs/plans/2026-07-30-codex-67-port-source-oracle-resolution-plan.md`.

## 2026-07-26: A Frozen Port Range Can Enforce An Exclusion That Prose Cannot

codex#54 ports Claude `#617`'s registry forward-compatibility. The obvious framing — "copy Claude's
broker, minus the parts we don't want" — was rejected, and the reason inverts the issue's own premise.

The issue anticipated that Codex carried content Claude lacks, so a byte-copy would destroy it. It
does not: every symbol tested is present in both files, the class lists are identical (25 classes,
same order), and all 46 removed lines in the raw diff are one half of a modification pair. A
byte-copy was therefore mechanically viable. It was rejected anyway, because the real constraint runs
the other way — what Claude carries that Codex must **not** receive: ~21–30 lines of `#616`
`isolation` semantics that this port is forbidden to import, plus ~89 lines of unrelated drift
(`_renew_batch_member`, `_renew_live_batch_siblings`, `record_child_terminal`, `spawn_failed`,
`assert_write_target`) that would land under no contract row — precisely the defect class codex#45's
review flagged as P1 #5.

The decision that matters is how that exclusion is *enforced*. Picking the frozen source range as
`4eb2fe15..1648a21b` — the `#617` merge and its parent, rather than a convenient wide range ending at
`origin/main` — makes the exclusion structural. Two measurements:

- `git diff 1648a21b..b464d090` over both pathspecs is **empty**, so the narrow range is not stale;
  the frozen target is byte-equivalent to current `origin/main` for exactly these paths.
- Every excluded-drift symbol already exists at `4eb2fe15`, i.e. *before* the range opens.

Those lines cannot land under a contract row because the range does not contain them. codex#45's
P1 #5 was a file ported under zero contract rows; the guarantee here runs the other direction, and
`tests/test_lease_registry_forward_compat_port_contract.py` pins both measurements so a later
widening of the range is a test failure rather than a silent scope creep.

**Rejected alternative:** range `cf15a09f..b464d090` (chaining off codex#45's frozen target). It
would have covered `#617` but also swept in the unrelated drift, leaving R10 to reviewer discipline.

**Revisit when:** a port needs content from more than one upstream merge. The narrow-range technique
only buys a structural exclusion when the payload is one coherent upstream change; a multi-merge port
would have to re-derive the guarantee some other way.

## 2026-07-24: Codex V2 Owns Live Execution And Verified Workflows Becomes A Minimal Kernel

Codex 0.145.0 MultiAgent V2 becomes the only active workflow execution path after a current-auth proof and current-Mac cutover. The proof reuses the existing Codex login and project configuration; it does not create or copy authentication homes. The main Codex session remains the sole orchestrator and owns workflow preview, approval binding, dependency release, integration, Git, gates, merge, installation, rollback, and completion. Codex V2 owns live agent identity, hierarchy, bounded context, messages, waiting, interruption, and restoration; Saga owns lifecycle state and points to one concise workflow run record under the owner-controlled `~/.codex/verified-workflows/state/<repo>/workflow-runs/` root.

Verified Workflows keeps its public plugin, skill, and 25 logical role identities but replaces the current evidence-chain implementation. Three compact canonical tables declare assignments, exact six-profile mappings, write ownership, checks, reviewers, fallback conditions, and external actions and share one approval digest. Native typed results and deterministic checks feed a small root-owned gate evaluator. A lightweight root audit compares pre/post `HEAD`, branch, index, bounded Git-control state, and porcelain-v2 changed paths; writable work is sequential unless V2 supplies per-agent mutation attribution. Protected subject chains, full workspace snapshots, content-addressed intents, duplicated event records, custom attestation as authority, and the plugin-owned executable DAG leave the active path.

The managed child profiles are `review_max` Sol/max read-only, `review_high` Sol/high read-only, `work_high` Sol/high workspace-write, `test_medium` Terra/medium workspace-write, and `scan_low` plus `monitor_low` on Terra/low with their existing boundaries. The native catalog reports Luna as V1, so no Luna child or V1 fallback remains. Ultra is effective at the root; a child request remains capped by its selected profile. Runtime acceptance requires V2 readback of profile/type, model, effort, provider, effective permissions, and canonical identity.

Saga's external-action lifecycle remains the provider, approval, egress, and adjudication control plane. External actions appear in the same preview and run record. CLI routes are advisory and read-only, receive a minimal environment and secret-scanned declared context, and reject non-empty write sets until an enforceable filesystem boundary exists. Caller input cannot promote a response-only route, and external output never satisfies a gate until the root independently verifies and adopts a finding.

Implementation bootstraps inline because the workflow system is changing itself. The implementation root performs maintained-source and Git mutations. After candidate-byte V2 readback is proved, authority-bearing reviews run under separately started fresh V2 review-root sessions rather than descendants of the implementation root; the implementation root validates their typed results and remains the final orchestrator. Delivery proceeds through reviewed PR, merge, supported installation of the changed plugins and profiles in the current Codex environment, fresh-session proof, and an exercised rollback that restores the pre-cutover repository ref, installed `fleet-core`, `saga`, and `verified-workflows` versions, project/user configuration, profiles, and model catalog. The rollback package is recaptured immediately before host mutation rather than assumed current from the initial baseline. Active V1 scripts and instructions are removed; historical V1 evidence remains lineage only.

The release unit starts only after a preflight proves authority for tracked `.codex`, Git metadata, GitHub, and supported current-user Codex plugin/profile/config/catalog mutation. Missing authority pauses and resumes the same approved plan in a suitable session; it does not convert a required proof, review, or rollback step into an advisory action.

This decision supersedes the 2026-07-18 root-inline feasibility policy and the 2026-07-17 temporary V1 catalog policy after the U8 live cutover gate passes. Until that gate passes, the current installation remains unchanged.

Plan: `docs/plans/2026-07-24-codex-v2-orchestrated-execution-system-plan.md`.

## 2026-07-18: Feasibility Review Keeps Root-Owned Workflows Usable

Verified Workflows must review an approved Workflow Structure against the available Codex capability projection before it is treated as executable. The root Codex session remains the owner of scope, mutation, integration, Git, gates, and completion; native child profiles remain bounded advisory workers unless a runtime can provide authenticated host-issued child attestation.

Preferred-independence lenses use root-inline evidence for gate authority whenever strict child attestation is unavailable. Required-independence lenses remain blocked in that environment rather than being silently downgraded. Risk or file count alone does not justify selecting `verified-workflow`; strict independently attestable execution must be explicit and feasible.

The review is deterministic and read-only. It composes the rendered workflow table with a bounded capability snapshot, reports the required correction by step, and does not launch children, modify runtime configuration, or turn requested model/effort selection into observed execution facts.

Plan: `docs/plans/2026-07-18-workflow-feasibility-review-plan.md`.

## 2026-07-17: Normalize Subject-Exclusion Parent Links And Bootstrap Self-Hosting Fixes Manually

Verified Workflows outside-scope projections will normalize only the raw directory link-count field for the immediate lexical parent of each authorized subject exclusion. APFS changes a directory's link count when an immediate file is added, so retaining that scalar makes an authorized new file look like outside-scope mutation; higher-ancestor links, device, inode, mode, path, visible-entry content, symlink handling, whole-workspace link counts, and unrelated-directory link counts remain strict.

The correction ships as `verified-workflows` `1.0.2+codex.20260718004419`. The manifest, validator expectations, target inventory, generated lifecycle facts, README, changelog, portability status, and direct version tests advance as one release unit.

Verified Workflows cannot grant gate authority to changes in its own implementation. Self-hosting patches therefore use an operator-approved manual bootstrap sequence: root owns implementation, integration, Git, release, and installation; independent named children provide advisory trust-boundary review and platform-test evidence only. The repaired package can resume ordinary Verified Workflow authority after supported installation and source-to-cache readback.

Existing v1 subject records store only an aggregate outside-scope digest and no projection-algorithm version or entry manifest. A chain recorded with the old projection is not retroactively converted; the failed run remains audit evidence and one replacement run replays a mode, size, status, and SHA-256 preservation manifest from its clean baseline without creating a new outcome dispatch. The original worktree remains available until the replacement root receipt seals.

Plan: `docs/plans/2026-07-17-verified-workflows-apfs-subject-snapshot-plan.md`.

## 2026-07-17: Force Sol And Terra Back To MultiAgent V1 Temporarily

Codex 0.144.5 selects the subagent tool version from each model's catalog row. Sol and Terra remain
assigned to MultiAgent V2 even when `features.multi_agent_v2=false`, so the feature flag alone does
not restore named-agent, model, and effort controls. Until V2 exposes those controls reliably, Fleet
Core generates a complete local catalog snapshot and changes only the Sol and Terra
`multi_agent_version` fields to `v1`.

The generated catalog lives under `$CODEX_HOME/model-catalogs/`, is written atomically as UTF-8
without BOM, and is selected by an absolute `model_catalog_json` path. Installation preserves one
rollback copy of the prior config, enables stable MultiAgent, disables V2, and removes the obsolete
V2 namespace workaround. A restart and fresh session are mandatory because Codex pins the
catalog-selected tool schema at startup. Re-run installation after upstream catalog changes.

The five custom-agent profiles and their model/effort mappings remain canonical. Native interactive
delegation uses `verified-workflows:select-agent` before spawn and `/agent` after spawn. Verified
Workflow receipts and gates apply only when that workflow mode is explicitly selected; they do not
block ordinary native agent use.

Ultra is not approved under this workaround. Sol and Terra describe Ultra as automatic delegation,
and no current evidence proves that behavior remains correct when their catalog rows are forced to
V1. A separate runtime proof is required before Ultra can be re-enabled.

This decision temporarily supersedes the 2026-07-11 V2 bootstrap as current runtime policy. The old
capability snapshot and port artifacts remain immutable historical evidence.

Plan: `docs/plans/2026-07-17-codex-v1-agent-compatibility-plan.md`.

## 2026-07-11: Bootstrap MultiAgent V2 For Named Verified Workflow Profiles

Verified Workflows keeps its existing architecture: 25 logical role/lens definitions map through
risk-selected execution classes to five named Codex profiles, and the root thread owns the workflow
DAG, integration, gates, and final adjudication. The earlier conclusion that Sol/Terra could not
select those profiles was a capability-detection error, not a reason to redesign the profile set.

The effective Codex configuration for profile-selected MultiAgent V2 work must include:

```toml
[features.multi_agent_v2]
hide_spawn_agent_metadata = false
tool_namespace = "agents"
```

The root dispatches a fresh named child with `agent_type = <runtime_agent_name>` and
`fork_turns = "none"` by default. `task_name` remains workflow identity only. A positive bounded
turn count is allowed when explicitly justified; omitted or `all` is forbidden for profile-selected
work because full-history forks inherit the parent agent type, model, and effort.

Current V2 also reapplies the live parent permission profile after applying the named role. The five
profile TOMLs remain correct for role/model/effort/instruction selection, but their `sandbox_mode`
cannot narrow a more-powerful parent. Workflow dispatch therefore groups attempts by permission:
read-only scanner/reviewer/monitor children run under a fresh read-only parent, while
`test_medium` runs under workspace-write. Host-issued child rollout context, not child prose, proves
model, effort, role, and effective permission. A parent/child permission mismatch blocks authority.

The runtime bootstrap is a prerequisite, not an assumption. Installation/cutover must verify the
effective config in an isolated task and then a fresh real task, prove a differential parent/child
model and effort, and stop rather than substitute a generic child if `agent_type` is absent or the
child receipt disagrees. User-profile mutation remains a root-owned U8 cutover action with rollback;
an unpublished plugin or ordinary workflow run must not silently edit global Codex configuration.

This decision supersedes only the inline-only/unavailable-selector conclusion in the earlier
2026-07-11 decision and related U4 characterization. It does not weaken named-child receipt,
installed-profile digest, role/lens binding, observed child-context, mutation-audit, structured
result, root-verification, independence, or severity-gate requirements. Inline remains an explicit
degraded path where the role permits it, not the normal model-pinned execution path.

Learning: `docs/engineering-journal/LEARNINGS.md`, "Sol And Terra V2 Can Select Named Profiles
After Namespace Bootstrap."

## 2026-07-11: External Advisory Actions Use One Codex-Owned Runtime

External offload and second-opinion actions use one shared Codex runtime across Ideate, Brainstorm, Plan, Work, Doc Review, and Code Review. Lifecycle stages declare and consume actions; the runtime owns concrete route preview, run-specific approval, dispatch, durable action state, receipts, replay, adjudication, and status projection, while Codex root remains the only live-tree mutation and gate authority.

Each action stores an immutable request and approval record plus an append-only transition log under the repository Git common directory. The store references existing engine manifests and run-ledger facts rather than overloading them, because those surfaces prove execution and record facts but do not model operator approval, requiredness, adjudication, or consumption.

The runtime owns the adapter factory while `engine_dispatch.py` remains the receipt and advisory-evidence validator. V1 adapters are supervised Claude CLI, contained `agy`, and generic OpenAI-compatible HTTP; CLI patch work uses full disposable local clones pinned to a recorded base with remotes removed, write-set diff evidence, terminal cleanup, and no provider application to the live tree.

Repo-and-stage policy moves to `external-action-policy.json`; legacy `engine-prefs.json` values are unapproved desired intent only. Validated provider onboarding applies first to a repo-local registry overlay, canonical promotion is a separate reviewed source change, normal CI remains hermetic, and an explicit attended release harness proves real Claude, `agy`, Ollama Cloud, and all six lifecycle stages before cutover.

Plan: `docs/plans/2026-07-11-codex-external-advisory-execution-contract-plan.md`.

## 2026-07-11: Complete U4 Inline, Preserve Named-Child Proof, Then Pause

The modernization run completes U4 in the root thread as five sequential checkpoints: workflow contract/compiler, behavior-preserving receipt-module extraction, executable receipts/root verification, severity-first gates, and named-child selection plus attestation. Extraction reduces the 6,000-plus-line receipt facade into cohesive modules without deleting schemas or behavior.

Named-profile definitions and named-child proof remain in U4 because precise child model/effort selection requires both halves. Selection proves the host accepted one of the five managed profiles; attestation joins the selected profile to hook-observed model, installed-profile digest, expected effort, role/lens, permission, child identity, and result. The current generic spawn schema exposes no profile selector, so U4 may truthfully end as `diagnostic`; definitions and hook evidence alone are not enforcement.

Only raw-hook operational maintenance moves to U8: start-only/stop-only abandonment, digest-bound prune, and deletion after normalized readback. U4 retains safe capture, pair loading, normalized persistence, consumption markers, and exact-readback recovery of prepared normalization transactions because those are part of crash-safe attestation.

After U4 passes its focused and integrated checks, the root writes the U5-U8 `## Workflow Structure` and pauses. U5-U8 may use model-pinned `scan-low`, `test-medium`, `review-high`, `review-max`, and `monitor-low` children only after named-profile selection plus attestation is proved. Otherwise the workflow remains paused unless the operator explicitly accepts a less precise root-inline or generic-child fallback. Verified Workflows may coordinate later units but never accepts its own output; root diff, tests, severity judgment, Git, cutover, and formal code review remain authoritative.

Plan: `docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`.

## 2026-07-10: Verified Workflows Replaces Team Execution And Future Ports Are Contract-Gated

The Codex adapter no longer models reviewer and validator execution as a Claude-style peer team. The canonical package becomes `verified-workflows` `1.0.0`, with `verified-workflows:run`, Saga mode `verified-workflow`, `## Workflow Structure`, canonical Verified Workflows state and receipt vocabulary, and a root-owned DAG. The root Codex thread owns spawn, follow-up, wait, integration, remediation routing, and adjudication.

Readers accept centralized legacy Team Execution aliases, but new serializers emit only canonical vocabulary and append-only historical artifacts are never rewritten.

All 25 logical role IDs remain stable, but job semantics are separated from five execution profiles: `review-max`, `review-high`, `test-medium`, `scan-low`, and `monitor-low`. Agent-lenses have default and allowed risk-adjustable classes plus required-or-preferred independence; deterministic validators bind scripts and evidence schemas without an LLM class. A workflow receipt binds logical role, selected class/profile, hook-observed model, installed-profile digest, role/lens digest, child/task identity, and result.

The profile digest is accepted proof of expected effort because current hooks report model but not reasoning effort. Required role evidence, no unresolved blocker, required validator success, and root verification are authoritative; numeric scores are supporting evidence only.

Future Claude-to-Codex imports must follow `docs/portability/claude-to-codex-plugin-port-runbook.md` and carry a versioned, closed-schema JSON manifest validated by `scripts/port_contract.py`. The manifest binds its runbook digest, the historical Codex plan base and approved execution-base preservation inventory, frozen Claude refs and exact pathspec-scoped source inventory, the current Codex capability-snapshot digest, per-path treatment, preserved Codex-only invariants, staged target/test evidence, version policy, review, isolated install, fresh-session proof, and rollback. Classification blocks source work, per-unit evidence blocks integration, and complete cutover evidence blocks release.

Generated classification drift, missing source or Codex-drift rows, active Claude-only primitives, or incomplete evidence fail the corresponding gate.

Cross-plugin old/new vocabulary lives in one fleet-core compatibility registry consumed through each plugin's normal shim; Saga and Verified Workflows do not import each other. Cutover proves both clean installation and seeded old-to-new migration. Exact restoration material remains in a protected uncommitted rollback bundle, while committed evidence contains only sanitized inventories and hashes.

Rejected: retaining the Team Execution name as the canonical Codex identity, globally replacing historical/upstream names, maintaining 25 manually coupled model profiles, collapsing roles without equivalence fixtures, requiring peer-to-peer agent messaging, or relying on a prose-only port checklist.

Plan: `docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`.

## 2026-07-10: Execute The Modernization Through Codex-Native Subagents

The model/execution modernization plan runs with Saga's `inline` backend and direct Codex subagents, not Team Execution. `inline` identifies the root Codex thread as the runtime owner; it does not prohibit the existing `/work` mechanics for serial or parallel generic subagents. The root owns Saga state, integration, Git, installed-state mutation, final verification, and completion decisions, while bounded children perform requested-read-only exploration, one-writer implementation slices, fresh-context review, and focused validation under root-owned mutation checks.

The preferred execution policy is Sol/max for the root coordinator, Terra/medium for explorers, Sol/high for implementation and judgment-heavy review, Terra/medium for validators, and Luna/low for deterministic scans. The root selection is explicit. Child model, effort, named-agent, and sandbox selections are preferences until the active spawn surface returns readback or a selected custom-agent profile is proved by runtime receipt; an installed file or prompt request alone is not enforcement. Ultra is not used because this plan already defines explicit bounded fan-out.

Concurrency uses the lower of host-advertised capacity and `agents.max_threads`. U1-U7 prefer parent `workspace-write`; requested-read-only waves use pre/post worktree snapshots, fresh-context reviewers and validators use `fork_turns=none`, shared-worktree writes remain single-writer, and pre-existing path overlap pauses the unit until ownership is resolved. Real-profile mutation is root-only in U8 after isolated proof. Team Execution profiles, receipts, gates, consensus, and advisory logic are systems under test in U3/U4/U7/U8 and never accept their own implementation.

Rejected: serial Team Execution as the bootstrap protocol, treating generic Codex children as Team Execution evidence, or adding another permanent orchestration plugin solely to run this plan.

Plan: `docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`.

## 2026-07-10: Modernize Codex Model And Execution Truth Before The Next Claude Import

The next port cycle is commit-bounded at Codex `788902513e48ea95fd0504ac3c850c8c02e5d920` and Claude `38742ece89880a6b140be237edad6d3f13c97b54`, a focused `9470edc..38742ece` window of 156 files across fleet-core, Saga, team-execution, and their tests. The cycle first separates lifecycle state, continuation, dispatch vehicle, role identity, model/effort policy, and hooks; it then modernizes fleet-core, activates and attests Team Execution, repairs Saga's real-launch boundary, and only then imports the Claude engine/trust/reconciliation delta.

The Codex model policy keeps `fable`/`opus`/`sonnet`/`haiku` only as lineage keys. Preferred mappings are Sol/max for exceptional bounded root judgment, Sol/high for reviewer judgment, Terra/medium for general workers and testers, and Luna/low for scanners and monitors, with catalog-aware ordered fallbacks. Scalar effort is `low..max`; Ultra is a root orchestration profile because it adds automatic delegation and is prohibited in leaf agent profiles.

Managed Team Execution agent files must carry active `model` and `model_reasoning_effort`, but installation alone is not execution proof. Delegated evidence requires a receipt binding named role, child identity, hook-reported active model, the digest of the exact installed TOML (which binds expected effort because the hook does not report it), and result vehicle. Generic subagents never satisfy Team Execution gates, and a fresh isolated proof may leave the capability explicitly `serial-only`. P0, security, and required-validator hard failures remain blocking after the three-cycle remediation cap.

Saga keeps durable lifecycle/outcome state. Goal is explicit long-running continuation, hooks are event extensions, and Team Execution is a dispatch/gate protocol; none is a substitute execution backend. Outcome dispatch becomes a v2 intent plus typed acknowledgement: only `launched` creates dispatched work, `handed-off` is visible but not launched, and legacy commit records remain settled as `legacy-unverified` until append-only evidence reconciliation. A synthetic `leaf-*` id cannot advance state by itself. Codex hooks are behavioral adaptations with explicit trust, prompt-free contained receipts, and no surprise Git mutation; blocking PreToolUse enforcement is deferred while unified-exec interception remains incomplete.

Target Codex releases are fleet-core `0.8.4` and Saga `0.75.17`, preserving the frozen source-lineage labels, plus team-execution `2.4.0` on its existing Codex adapter line. Codex differences remain explicit in `PORTABILITY.md`; no version claims byte parity. Metadata changes land last, after locked-environment tests, isolated install, agent sync, hook trust, fresh-session capability proof, and a recorded managed-surface rollback path.

Rejected: importing Claude `0.75.17` before fixing model/runtime foundations, treating Ultra as a scalar leaf effort, inheriting the mutable machine default, counting installed TOMLs or a simulated probe as named dispatch, keeping Goal/hooks/subagents/Workflow in one backend enum, copying Claude hooks/commands, or editing installed cache as source.

Plan: `docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`.

## 2026-07-07: Saga Resolves Sibling Plugins From The Codex Plugin Environment

Saga outcome board-sync depends on mission-control, and several plugins depend on fleet-core, but those are sibling plugin dependencies, not files under the consumer repository. Runtime resolution should therefore start from the executing script's plugin environment: source checkout or local marketplace `plugins/<name>` siblings first, then installed-cache marketplace versions, with explicit env overrides only for fleet-core.

Rejected: hardcoding `/Users/jefcox/...` paths, requiring every outcome consumer repo to vendor mission-control, or weakening the board-sync certificate to route around a missing path. The fix must keep board-write authorization and idempotency unchanged while resolving the correct dependency root.

Plan: `docs/plans/2026-07-07-outcome-plugin-dependency-resolution-plan.md`.

## 2026-07-06: The 0.64 Port Window Lands Fleet-Commons As A Codex fleet-core Plugin

The upstream port window is commit-bounded at Claude `b30e0f2..9470edc` (saga 0.41.0 to 0.64.0), with per-plugin lineage baselines recorded because non-saga plugins were synced earlier than saga. The fleet-commons tier/retry substrate lands as a Codex `plugins/fleet-core` scripts-only plugin mirroring the upstream shape, with the shim resolution ladder rewritten Codex-native (env override, repo walk-up, `~/.codex` layout, fail-loud) instead of emulating Claude's `installed_plugins.json` rungs. `models.json` carries a dual palette: Claude tier names as lineage keys mapped to Codex models and effort ceilings. Saga versions to 0.64.0 as a parity label per the 0.41 precedent, with non-ported surfaces recorded in PORTABILITY.md.

Rejected alternatives: vendoring fleet_commons into each plugin without a fleet-core plugin (structural divergence makes every future sync fan out copies); deferring the substrate (dependent features would hard-code tier/retry logic to be reworked later). Deferred by operator decision: remote gate transport (#379, waits on the redis-channel server-boundary proof), the `agy` plugin (own ecosystem), PreCompact spore and residency hooks (no Codex trigger), marketplace generation.

Revisit when: Codex gains a hook/compaction seam, redis-channel gets its server-boundary proof, or upstream changes the fleet-commons distribution mechanism.

Plan: `docs/plans/2026-07-06-port-claude-plugin-updates-to-0.64-plan.md`.

## 2026-07-06: Baseline Freeze Holds At `9470edc` Despite Further Upstream Drift

U1 baseline-freeze verification found Claude `origin/main` had already moved to
`43646b3` (past the plan's `9470edc` boundary) by the time discord-identity-assets
0.2.0 and this plan landed. Per KTD1, the window is not silently extended:
implementation units U2 through U9 read only the `b30e0f2..9470edc` delta (31
commits, 141 files, confirmed by direct diff). Chasing `43646b3` requires a
deliberate plan amendment with its own commit-bounded window, not an in-flight
scope change during port execution.

Rejected alternative: quietly picking up the newer upstream commits while
implementing, since "more current" felt strictly better — rejected because it
mixes evidence from two different upstream snapshots into one classification
and breaks the reproducibility the commit-bounded window is meant to guarantee.

Revisit when: the 0.64 port window closes and a new cycle is opened against a
fresh upstream ref.

Artifact: `docs/portability/codex-saga-064-drift-classification.md`.

## 2026-07-02: Discord Guild Art Extends The Existing Identity Assets Plugin

Guild/server icon and image-banner publishing extends `discord-identity-assets` as a sibling target type instead of becoming a new plugin. Bot targets remain under `targets[]`; guild targets use schema v2 `guild_targets[]` with `guild_id_env` and `manage_guild_token_env` references so live guild IDs and tokens stay out of committed state.

The plugin publishes guild icons and Discord guild image banners through the guild API only after signed publish-plan confirmation, token/guild preflight, prompt consistency, and API readback. Discord Server Profile banner color is a UI color setting, not an uploaded image surface for this workflow, so the plugin records `profile_banner_color` as manifest/runbook metadata and does not automate it.

Deferred: server creation, channel/role provisioning, bot invites, Server Profile color automation, and generic team bootstrap orchestration.

## 2026-07-01: Discord Identity Assets Uses A Manifest-First Codex Boundary

The Discord visual identity workflow becomes a new Codex plugin named `discord-identity-assets` with one active skill, a target-repo manifest at `identity/discord-identity-assets.yml`, and deterministic Python scripts for manifest validation, image post-processing, Discord publish, verification, and receipts. Codex-native `image_gen` remains an agent-guided action; packaged scripts do not attempt to invoke it.

Target repositories own non-secret identity contracts and artifacts. The plugin resolves Discord tokens only from approved environment variable names at publish time, rejecting empty or suspicious material before HTTP, so it can integrate with vault conventions without making home-lab vault paths or plaintext secrets part of the reusable center.

The Discord client should use official current-user/current-application semantics where possible, verify bot and application ownership before mutation, and keep a tested compatibility path for the legacy application-ID endpoint used by the old home-lab script. Mimir is the first live proof, staged as dry run, explicit prompt plus publish-plan approval, live publish, and target-repo receipt reconciliation.

Rejected: copying home-lab hard-coded prompt/app registries, making Replicate the reusable generator, putting Discord Developer Portal provisioning in v1, using guild/admin tokens for bot-owned visual identity, and creating individual visual identities for the 31 headless Sons of Ivaldi.

## 2026-06-30: Team Execution Requires A Receipt Before Saga Can Execute It

Saga keeps Team Execution as an active Codex backend, but `orchestration_mode=team-execution` is not executable by itself. Executable Team Execution requires an `orchestration_ref` that resolves to a `## Team Structure` section or a protected Team Execution evidence/state root.

Planning materializes the receipt before a Team Execution plan is considered ready. Work, resume, outcome dispatch, and QA closeout validate the receipt before claiming Team Execution ran. Missing delegated subagents, unsafe delegation, or backpressure select serial Team Execution with the same roles and gates; inline execution is valid only when the operator chose inline or an explicit downgrade is recorded.

Saga owns lifecycle-level provenance: recommendation, explicit operator choice, actual mode, ref, and downgrade. Team Execution owns role-level vehicle evidence such as `team-execution-delegated`, `team-execution-serial`, `generic-subagent`, and `inline-assist`; generic assistance does not satisfy reviewer or validator gates.

Rejected: removing Team Execution from the Codex plugin, treating generic subagents as Team Execution reviewers, fabricating operator choice from actual mode, and minting Team Execution outcome leaves without a real receipt.

## 2026-06-17: Codex Active Plugin Parity Tracks CAMPPS And Codex Backends

Mission Control now treats Jeff Intent, Asgard, and CAMPPS as the active board topology. Mount
Olympus remains vendored only as retired historical context and compatibility data. CAMPPS Project
#4 is the active long-lived initiative board for current CAMPPS routing, with `Idea -> Committed ->
In Progress -> Done -> Parked` as its workflow.

Saga keeps the Codex execution backend set to `inline`, `manual`, and `team-execution`. The source
workflow fan-out backend remains lineage-only and unreachable in active Codex surfaces. Large
no-code-surface work stays `inline` unless cross-repo, consensus, fan-out, deployment, security, infra,
or adversarial-confidence signals require `team-execution`; unsafe automation routes to `manual`.

Rejected: porting Claude commands, agents, `.claude-plugin` manifests, GitHub Actions workflows, or
the source workflow backend as active Codex surfaces.

## 2026-06-09: Track renamed Hermes plugin repo in Mission Control

Mission Control project mappings now use `infiquetra-hermes-plugins` for the Hermes-facing plugin
repository (commit `698b4b0`). The proof script and active portability docs moved with the mapping
so board routing, proof scenarios, and migration guidance stay aligned.

Rejected: relying on GitHub redirects or leaving the old source name in proof fixtures. Redirects do
not help board-routing config or test fixtures, and stale proof data would keep validating the wrong
operator path. Revisit if Mission Control starts discovering repository sets live instead of carrying
a vendored canonical list.

## 2026-05-27: Curated Codex Adapter Repo

`infiquetra-codex-plugins` is a Codex-native adapter repo, not a mirror of the Claude or
Antigravity repos. The active surface is Codex manifests and skills. Claude command files,
top-level agent files, and host manifests are excluded unless a future Codex-native design
explicitly adds an equivalent.

## 2026-05-27: Preserve Lineage Versions

MVP plugin versions preserve the source/cache lineage versions. `sdlc-manager` uses 1.4.0
because that is the Codex-visible cache version and source plugin manifest version.

## 2026-05-27: Cache Is Installed State Only

Installed cache paths define the behavioral baseline but must not be edited as maintained
source. Repo-managed installs can replace cache-managed usage only after documented gates pass.

## 2026-06-06: Saga-Family Replacement Is Gated

The Codex baseline will move from `sdlc-manager` and `blueprint-reviewer` to
`saga`, `deploy`, `mission-control`, and `team-execution`, but the old active
plugins are not deleted until source baseline, capability mapping, known-use
inventory, staged validation, and isolated Codex proof gates pass.

The source snapshot for this replacement is
`infiquetra-claude-plugins@16de95c82ccb2ed80d7f11018e1c2e8247a80a7f`.
Claude command files, agent files, and `.claude-plugin` manifests remain
lineage only. Codex-active ports must be skills, references, scripts, tests,
config, docs, and `.codex-plugin` manifests.

## 2026-06-08: Saga Document Formatting Contract

Codex Saga adopts the shared document formatting contract from
`infiquetra-claude-plugins@abcc06b16763975d71e483a6dac768f4664d7b63`.
All Saga skills that write durable documents link `saga/references/formatting-style.md`.

The contract chooses tables for compact comparative fields and short prose for narrative fields. This
preserves field names for humans and LLM consumers while avoiding the CommonMark collapse caused by
adjacent `**label:**` lines.

## 2026-06-09: Saga Family Documentation Package Shape

The Saga family documentation package will use `docs/saga/` as the canonical operator guide, backed by
standard-library generated lifecycle facts and focused docs drift tests. The guide will explain the
Saga family as `saga`, `mission-control`, `team-execution`, and `deploy` together, while keeping each
plugin's mutation and orchestration boundary intact.

Visual assets will use SVG as the editable source format and `rsvg-convert` for PNG/PDF exports when
available. This avoids adding a new dependency for a documentation package while still producing
presentation-ready assets.

Rejected: one giant Saga README, Mermaid-only centerpiece visuals, and fully hand-drawn diagrams.
Those options either hide ownership boundaries, fail the presentation-quality bar, or drift away from
the routing/state contracts too easily.

## 2026-07-19: Lease-Safe Substrate Ports Byte-Faithful, Gates Per-Port

The #33 port copies the frozen-source lease/settlement modules byte-faithfully (the port manifest's
inventory digest freezes what identifies each row; row state and evidence float underneath), with
exactly two deliberate divergences: the audit-store default root moves to the runtime-neutral
`~/.local/state/infiquetra/delegation-audit`, and the dispatcher lease graft is written codex-native
around the record-only `prepared` seam instead of importing the source's authoritative-mint shape.
Release gating runs through the per-port pytest contract (`tests/test_lease_safe_substrate_port_contract.py`)
because `scripts/port_contract.py validate` is permanently pinned to the 2026-07-11 external-advisory
port (its port_id, refs, row counts, and digests) — the mission-control ports set this precedent.

Rejected: editing the shared CLI validator to accept multiple manifests (would unfreeze a sealed
contract), scoping run_ledger down to the settlement slice (would fork the shared module lineage),
and porting the source's dispatcher shape (would overwrite Codex's intent/ack machinery).

## 2026-07-19: Cross-Runtime Parity Port — Zero-Drift Inventory, Refusal Subsumes Validation

**Decision.** The #34 outcome cross-runtime parity port (manifest
`docs/portability/ports/2026-07-19-outcome-cross-runtime-parity.json`) makes four pattern choices:
(1) the codex preservation inventory is **empty by construction** — the plan's 2026-07-19 refresh
re-grounded it at the execution base `3723a818`, so `historical_plan_base == execution_base` and
there is no drift window to classify (the per-port gate pins this equality so the emptiness is a
provable construction, not an omission); (2) `RUNTIME_LABEL = "codex"` is the **single deliberate
byte divergence** in `outcome_compat.py` — every other byte tracks the frozen Claude source so
future diff-against-upstream stays one-line; (3) legacy `outcome-bundle/1` import is retired by
**wholesale refusal before reading records**, and the record-level chain validators are deleted
with the machinery — a rejection oracle that proves zero writes subsumes per-record validation
that can only run after parsing attacker-supplied bytes; (4) the operator's lease-seam deferral
(KTD6) is pinned as a **test** (`test_dispatcher_lease_seam_stays_dormant_ktd6`), so activating
the seam in this repo requires editing a named guard, not just wiring a call.

**Rejected alternatives.** Enumerating the full #33 substrate diff as preservation rows (59 files
of already-merged, already-gated content — busywork with no new invariant); keeping the import
validators "for reference" (dead code that implies a live path); recording the seam deferral only
in prose (silently reversible).

**Revisit when.** The cross-runtime-acceptance leaf activates the seam (the KTD6 guard test moves
to assert the wired form), or a future port needs a non-empty preservation inventory again (the
zero-drift shape is a special case, not the new default).

## 2026-07-26: codex#45 — One Release Unit for a Five-Row, Two-Manifest Port; U8 is a Fixed Evidence Label, Not a Real Unit ID

**Decision.** The #45 re-freeze (#627/#637 seam + COR3 worktree lease-authority) claims rows out
of TWO port-contract manifests under ONE release: the five surfaces changed in
`cf15a09f..b464d090` live in the new `2026-07-25-codex-627-seam-refreeze.json` contract (rows
claim U2/U3/U4 there); COR3's three orphaned defers were promoted in the PREDECESSOR contract
(`2026-07-19-lease-safe-substrate.json`) under that manifest's own free unit id, which happens to
also be spelled `U6` there but names this plan's U5 — the mapping lives in each promoted row's
rationale, not in a shared id space across manifests. Both manifests moved their release surfaces
(plugin.json, CHANGELOG, marketplace) together in the single U6 PR, per KTD2 (one PR-ready
boundary per execution contract).

`port_contract.py` hard-codes `unit == "U8"` for every `release_evidence.*` entry regardless of how
many units the port itself has (this plan has six, U1–U6). `U8` is a fixed evidence-label
convention baked into the shared tool, not a claim that an actual "U8" unit exists in this plan;
`init` seeds `"release_unit": "U8"` as a scaffolding default at `:398`/`:408`/`:418`.

*Corrected 2026-07-26 (round-4 code review). Two claims in the paragraph above were wrong as
originally written, though the decision they support survives both corrections:*

1. *Where the check lives.* It is **not** in `_validate_cutover_release_proof` (`:1405-1458`),
   which contains no `U8` literal at all. The enforcing line is
   `if evidence_by_id[reference].get("unit") != "U8"` at `:1379-1380`, inside `validate_manifest`
   (`:961`) — which runs at **every** stage, not just `cutover`. That is a stronger constraint than
   the original text described, and it is why the "Revisit when" below now names the right symbol.
   The three `:398`/`:408`/`:418` hits seed `release_unit`, a *different* field.
2. *The precedent count.* Measured across the three cited manifests by resolving each
   `release_evidence.*` reference into `evidence[]`: only `2026-07-10-saga-07517` tags `U8`.
   `2026-07-19-lease-safe-substrate` and `2026-07-19-outcome-cross-runtime-parity` both tag
   **`U5`** — which is exactly why each currently reports five `release_evidence.* must reference
   U8` errors under `validate --stage classification`. The convention has **one** precedent, not
   three. That argues *more* strongly for following the tool literally, not less: two of three
   prior ports diverged from it and are non-compliant today.

**Rejected alternatives.** Splitting into three PRs to land `port-digest` green early (KTD2 in the
plan; rejected because the acceptance harness appears in none of the four workflow files, so an
early green unblocks nothing automated); tagging release evidence with the plan's real terminal
unit id instead of `U8` (would pass validation for THIS manifest alone but breaks the moment
`_validate_cutover_release_proof`'s hard-coded check runs against it — the check is literal, not
"last unit").

**Revisit when.** `port_contract.py` stops hard-coding `U8` for release evidence, or a plan needs
release evidence before its cutover unit for some staged-release reason. To check: grep `"U8"` in
`scripts/port_contract.py` and read the hit inside `validate_manifest` (`:1379-1380` as of
2026-07-26) — **not** `_validate_cutover_release_proof`, which has never contained the literal.
Grepping that function returns empty and would read as "the constraint was removed" when it is
still enforced at every stage.

## 2026-07-26: `port_contract.py --stage cutover`'s Release-Proof Check Only Fits External-Action Ports; No Manifest Has Ever Cleared It

**Finding, not a fix.** `port_contract.py`'s `--stage cutover` unconditionally calls
`_validate_cutover_release_proof`, which requires the manifest's `release_evidence.cutover`
artifact to be a full proof generated by
`plugins/saga/scripts/external_action_release_matrix.py` — real provider-stage assignments, an
evidence-bundle directory tree, actual `marketplace add`/install/remove rollback-drill digests,
and a git tag whose tree contains the exact proof file. This is the Verified Workflows
**external-action** provider release matrix; it has no natural fit for a port that changes no
external-action surface at all (this port touches a lease broker, a dispatcher, an ancestor
guard, and a worktree-authority subsystem — none of them external-action providers).

Tested every manifest under `docs/portability/ports/*.json` against `--stage cutover` in this
session: **none has ever passed.** Each fails earlier in the pipeline for its own reason (a
`U8`-vs-actual-unit release-evidence mismatch, an unverified codex-invariant row, a missing
artifact, a capability-snapshot schema drift) — meaning `_validate_cutover_release_proof` itself
has never actually been exercised to success by any port in this repository's history. codex#45's
manifest is the first to clear every earlier check and reach this one, only to be blocked by it.

**Decision for this unit (U6).** Do not fabricate an external-action release run to satisfy a
check that does not semantically apply to this port — that would be gaming the gate, not passing
it. Reported honestly instead: classification, `verify-source`, and every `--stage unit` gate
(U2/U3/U4) pass; full `--stage cutover` is blocked on this one check, documented as a tooling gap
rather than silently worked around. `port_contract.py` lives only in this repo (no
`infiquetra-claude-plugins` twin), so this is squarely a codex-side tool question, not a KTD5
upstream-first boundary — but it is still bigger than one release unit's scope to redesign here.

**Revisit when.** A future unit either builds a non-external-action release-proof path in
`port_contract.py` (a `release_evidence.cutover` kind that doesn't require
`external_action_release_matrix.py`), or a port that DOES touch Verified Workflows external
actions arrives and can exercise the existing path for real, proving the mechanism works as
designed for its intended subject matter.
