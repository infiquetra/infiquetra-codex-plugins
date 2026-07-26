# Learnings

## 2026-07-26: Memoizing A Test-Script Loader Fixes Collection Order By Deleting Test Isolation

**Evidence:** `plugins/saga/tests/test_outcome_worktrees.py` + `test_outcome_board_sync.py` in that
argument order produced **3 failed**; reversed, **62 passed**; either file alone passed. Eighteen
live test modules load `plugins/saga/scripts/*.py` by file path through a byte-identical `_load`
that ends `sys.modules[name] = module; spec.loader.exec_module(module)`. The second module to be
collected re-execs the same files, rebinding `sys.modules` to a fresh generation while the first
module's captured globals (`WT`, `ENG`, `DISPATCH`) still reference the previous one. A lazy sibling
`import outcome_worktrees` inside the running code then resolves to the *live* generation, so
`monkeypatch.setattr(WT, "reconcile_worktree_leases", ...)` patched an orphan and the spy recorded
nothing (`assert [] == [<LeaseBroker ...>]`). The suite was green only because `board_sync` sorts
before `worktrees`.

**Mechanism — and the fix that looked right and was not.** The obvious repair is to make `_load`
idempotent: return the cached module when `sys.modules` already holds one loaded from the same file.
That removed the ordering dependence and **introduced a regression** — measured against a clean
worktree baseline of `2025 passed, 0 failed`, it produced `test_transient_dispatcher_error_
continues_the_tick` failing, because memoizing makes all eighteen modules *share* one module object,
so module-global state leaks across files that previously each got a private generation. Ordering
dependence and cross-file isolation were being provided by the same accident. The correct fix keeps
per-file generations and re-pins identity only for the duration of each test:

```python
@pytest.fixture(autouse=True)
def _pin_script_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    for _name, _module in _LOADED.items():
        monkeypatch.setitem(sys.modules, _name, _module)
```

`setitem` restores the previous binding on teardown, so whichever module loaded last, every test
runs against its own module's objects. Re-measured: `2025 passed`, identical to baseline, and all
four order permutations agree (62 / 62 / 23 / 39).

**Generalizable rule:** A fix for a shared-mutable-state bug must be measured against a full-suite
baseline taken *before* the fix, not against the symptom it targets — the reproducer going green
proves only that the symptom moved. And when scripts are loaded by path rather than imported as a
package, prefer re-pinning `sys.modules` per consumer over collapsing consumers onto one instance:
identity and isolation are separate properties, and sharing buys the first by spending the second.

## 2026-07-26: A Classification Gate Validates The Rows A Contract Has, Not The Ones It Should Have

**Evidence:** `plugins/saga/scripts/outcome_decompose.py` shipped a behavior change on the #45
branch (+34/−3: a fail-closed `prevalidate_reap_authority` ahead of the graph mutation, plus a
`lease_authority` parameter on `prune()`) while appearing in **zero** port-contract rows — none in
`docs/portability/ports/2026-07-25-codex-627-seam-refreeze.json`, none in the predecessor manifest.
`port_contract.py validate --stage classification` exited **0** throughout. KTD8 exists precisely to
stop unclassified production surface from landing, and it did not fire.

**Mechanism:** `expected_count` is derived from the base→target diff **over the pathspecs the
contract was initialized with** (`port_contract.py:437-450`). U1 passed five `--source-pathspec`
values and omitted `outcome_decompose.py`, so no row was ever generated for it — and a gate that
checks "is every row classified?" is trivially satisfied by a contract with a missing row. The gate
is sound; its input was under-specified, and nothing in the tool compares the pathspec set against
the diff the branch actually produced. Claude's copy moved +4/−2 inside the same frozen range, so
the row *would* have existed had the pathspec been passed. Re-running `init` over the same range
with the sixth pathspec added re-derived `expected_count` 6 and left all five existing `row_id`s
byte-identical, which is what made the retrofit safe to splice rather than regenerate.

**Generalizable rule:** A completeness gate keyed on a hand-supplied input set can only audit what
it was told about. Reconcile the gate's input against an independent signal — here, the set of
production files the branch's own diff touches — or the gate reports green on exactly the surface
nobody declared. When retrofitting a missing row, re-derive it with the tool over the unchanged
frozen range and confirm pre-existing row ids are stable; identical ids are the evidence that the
derivation is deterministic and the splice is not inventing history.

## 2026-07-26: A Partial Authority Port Turns A Refusal Into A Half-Applied Mutation

**Evidence:** `plugins/saga/scripts/outcome_decompose.py` — codex `prune` called
`outcome_worktrees.reap_worktree(store, subplot_id, worktree_ops, at=at)` AFTER `_commit(spec, ...)`
had already removed the node, dropped its edges, and bumped `spec_revision`. The #45 U5 port arms
worktree registry entries with a broker lease, and the ported `reap_worktree` refuses a lease-bound
entry it cannot prove authority for. Porting only the two files the plan scoped
(`outcome_worktrees.py`, `outcome.py`) would therefore have made a lease-bound prune raise
`WorktreeAuthorityError` against an already-mutated spec. Upstream Claude at `b464d090` carries the
matching preflight at `outcome_decompose.py:282-309`, which runs `prevalidate_reap_authority` BEFORE
`_live_state` and before any spec edit. `plugins/saga/tests/test_outcome_worktrees.py::
test_prune_prevalidates_before_the_graph_mutation` pins it.

**Mechanism:** the new refusal was introduced upstream of an existing mutation, not downstream of it.
A subsystem port that adds a fail-closed check changes the failure *timing* of every caller that
already invoked the ported function — and a caller that mutates first and cleans up second flips from
"best-effort cleanup failed, reported in the summary" to "canonical state advanced, then raised".
Counting the port's line surface (55 `lease_authority` lines across three modules) found the seam; it
did not find the caller whose ordering the new refusal invalidates.

**Generalizable rule:** When a port adds a refusal to a shared function, enumerate its existing call
sites and check what each one has already mutated by the time the call happens. Any caller that
mutates before calling needs the refusal hoisted above its mutation in the same change — a scope
boundary drawn by file count will silently ship a half-applied write.

## 2026-07-25: Dict Literal Ordering Decides Whether A Halt Record Exists At All

**Evidence:** `plugins/saga/scripts/outcome.py` — the `DispatcherError` reconcile arm builds its halt
record spread-first / literal-last (`{**receipt, "receipt_kind": ..., "kind": "dispatch"}`), while the
three sibling halt appends in the same function (the degrade halt, the orchestration-ref halt, and the
`BackendHaltError` arm) build theirs literal-first / spread-last. A probe against a real store shows the
sibling arms persist `{"phase": "halt", "kind": "halt", ...}`: the receipt's own `kind` overwrites the
literal, `outcome_store.reduce_dispatch_ledger` matches no branch for it, and
`outcome_report._halted_subplots` returns an empty set for a leaf that just halted. Upstream Claude at
`b464d090` writes the same record spread-first / literal-last and IS reducer-visible.

**Mechanism:** `reduce_dispatch_ledger` dispatches on the `(kind, phase)` pair. Every halt receipt
carries `kind: "halt"` of its own, so any append that spreads the receipt LAST silently rewrites the
routing key the reducer reads. The record is still durably on disk and still returned in the in-memory
`halted` list, so the tick looks correct in every signal except the derived one — the operator page.
This is the #628 invisibility shape: an orphaned intent, a store lock leaking to its TTL, and a silent
re-dispatch.

**Generalizable rule:** When a dict literal both spreads a payload and sets the field a reducer routes
on, put the routing literal LAST and preserve the payload's own value under a distinct key
(`receipt_kind`). Test the reducer's output, never the append — asserting "a record was written" passes
against a record no consumer can see.

## 2026-07-18: Read-Only Validation Can Still Leave Lock Files

**Evidence:** Repository validation and the code-review action-bundle read each created six zero-byte
`.lock` files beside committed external-action release evidence. The product checks passed, but a strict
workspace snapshot correctly saw the added ignored/untracked paths until they were removed.

**Mechanism:** A read-only validation path can still acquire a filesystem lock in the maintained source
tree. Logical read-only behavior and process-level file creation are separate mutation surfaces.

**Generalizable rule:** For snapshot-sensitive gates, run validators with lock or cache side effects in a
disposable worktree, compare porcelain state before and after, and remove the disposable worktree after
capturing results. A successful validator exit code does not prove a no-mutation contract.

## 2026-07-18: Directory Link Counts Can Leak Authorized Child Creation

**Evidence:** On APFS, both an authorized missing file and an authorized missing directory changed the
outside-scope workspace digest when created. The excluded subject bytes, outside-scope file count,
outside-scope byte count, repository identity, and Git-control digest remained stable; the immediate
parent directory's raw `st_nlink` value was the changing input.

**Mechanism:** Excluding a subject path from traversal does not exclude metadata already hashed for its
parent. Filesystems may change a directory's link count when an immediate child appears, so raw parent
link metadata can turn an authorized subject mutation into false outside-scope drift.

**Generalizable rule:** When a projection excludes an authorized path, audit metadata dependencies on
that path as well as the path entry itself. Normalize only the directly affected scalar on the immediate
parent; keep higher ancestors, siblings, inode, device, mode, symlink, content, and full-snapshot evidence
strict, and prove the boundary with both positive and negative tests.

## 2026-07-17: The Model Catalog Can Override The MultiAgent Feature Flag

**Evidence:** Codex CLI 0.144.5 reported `multi_agent_v2` disabled while the live Sol and Terra model
rows still reported `multi_agent_version: v2`; Luna reported V1. A generated full-catalog copy with
only Sol and Terra changed to V1 produced V1 rows for all three models and retained UTF-8 without BOM.

**Mechanism:** Feature state and model-selected tool version are separate configuration inputs. The
catalog can select V2 even when the feature flag is false, and the resulting schema is pinned to the
thread. Editing only feature flags or changing config inside an existing thread cannot restore V1.

**Generalizable rule:** When Codex exposes a surprising tool schema, inspect both feature state and
the active model catalog. Apply catalog changes to a complete refreshed snapshot, change only
allowlisted fields, restart, and verify a fresh thread. Treat Ultra as a separate compatibility test
because its automatic delegation may depend on V2.

## 2026-07-12

### Workflow approval needs a concrete preview  {#workflow-approval-needs-concrete-preview}

**Context.** The external advisory execution plan named Verified Workflows, but execution began
root-inline and the operator did not see the concrete workflow before agents and validators ran.

**Evidence.** PR #28, `docs/work-sessions/2026-07-11-external-advisory-execution.md`, and
`docs/retros/task-codex-external-advisory-execution-contract-2026-07-12.md`.

**Mechanism.** Selecting a backend or approving a plan does not expose the actual task graph,
dependencies, roles, model and effort choices, or downgrade and upgrade recommendations. Automatic
inline fallback also changes the approved execution contract without returning to the operator.

**Fix (or queued).** QUEUED `#verified-workflow-preview-and-agent-runtime-contract`.

**What surprised.** V2 orchestration and approval semantics caused more rework than the provider
adaptation itself.

**Generalizable rule.** Treat workflow approval as approval of a concrete execution revision, not a
backend label. Render the complete proposed workflow conversationally, re-render it after every
operator-requested change, start nothing before explicit approval, and stop for a new preview whenever
runtime receipts cannot prove the approved role, model, effort, or permissions.

**Refs.** `docs/ideation/2026-07-11-codex-workflow-control-agent-lifecycle-ideation.md` and QUEUED
`#verified-workflow-preview-and-agent-runtime-contract`.

## 2026-07-11: Sol And Terra V2 Can Select Named Profiles After Namespace Bootstrap

**Evidence:** `codex-cli 0.144.1`; OpenAI Codex source tag `rust-v0.144.1`
(`44918ea10c0f99151c6710411b4322c2f5c96bea`); current OpenAI Codex `main`
`5c19155cbd93bfa099016e7487259f61669823ff`; fresh local parent/child rollout
receipts. The relevant source behavior was unchanged between the installed tag and that `main`.

**Mechanism:** The Sol and Terra model catalog rows select MultiAgent V2. V2 defaults
`hide_spawn_agent_metadata = true`, which removes the functional `agent_type`, `model`,
`reasoning_effort`, and `service_tier` inputs from the model-visible spawn schema. The default
`collaboration` namespace is also reserved by the model backend: setting only
`hide_spawn_agent_metadata = false` expands that reserved schema and fails before inference with
`Function 'collaboration.spawn_agent' is reserved for use by this model and must match the
configured schema.` This restricted default is not proof that custom-agent model and effort fields
are unsupported.

The working V2 bootstrap is:

```toml
[features.multi_agent_v2]
hide_spawn_agent_metadata = false
tool_namespace = "agents"
```

After a fresh task loads that configuration, dispatch selects the TOML profile with `agent_type`;
`task_name` only names the workflow task/path and does not resolve a profile. Because V2 defaults
omitted `fork_turns` to `all` and rejects agent-type/model/effort overrides for a full-history fork,
profile-selected work must pass `fork_turns = "none"` or a positive bounded turn count. Verified
Workflows should normally use `none` and send a self-contained role/lens evidence packet.

The differential runtime proof used a Sol/high root and dispatched `agent_type = "scan_low"` with
`fork_turns = "none"` through the `agents` namespace. The child receipt recorded
`agent_role = "scan_low"`, model `gpt-5.6-luna`, effort `low`, and read-only sandbox. A separate
Luna/V1 control selected `review_high` and produced Sol/high/read-only. This proves that named TOML
profiles apply model, effort, and instructions; it does not remove the separate requirement
to bind the planned role, installed-profile digest, child identity, observed turn context, and
structured result before granting workflow evidence authority.

The read-only result did **not** prove that the profile narrowed the sandbox because that parent was
also read-only. A later workspace-powerful parent spawned `review_max`; its host-issued child
`turn_context` correctly recorded Sol/max but inherited the parent's permission profile instead of
the TOML's `sandbox_mode = "read-only"`. Installed-tag and current-main source explain the result:
V2 applies the role and then calls `apply_spawn_agent_runtime_overrides`, which copies the live
parent permission profile onto the child. Until that ordering changes, permissions must be enforced
by a permission-homogeneous parent task. Read-only scanner/reviewer/monitor profiles run beneath a
read-only parent; `test_medium` runs beneath workspace-write. A profile sandbox field remains the
declared policy and future-compatible configuration, not present runtime enforcement.

**Generalizable rule:** Do not infer a Codex capability is absent from one model-visible tool
schema. Check model-selected tool versions, schema-hiding configuration, reserved namespaces, fork
semantics, and a differential child `turn_context`. For current Sol/Terra V2 named-profile dispatch,
require the two-setting namespace bootstrap, `agent_type`, a non-full-history fork, and host-issued
runtime readback. Verify model and effort from the child rollout, never child self-report. Verify the
effective permission profile separately and use a permission-homogeneous parent because current V2
overwrites the role's sandbox with the parent turn permission. Fail closed instead of substituting a
generic child when any part is missing.

Sources: [custom-agent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agents),
[V2 defaults](https://github.com/openai/codex/blob/44918ea10c0f99151c6710411b4322c2f5c96bea/codex-rs/core/src/config/mod.rs#L1144-L1179),
[spawn schema hiding](https://github.com/openai/codex/blob/44918ea10c0f99151c6710411b4322c2f5c96bea/codex-rs/core/src/tools/handlers/multi_agents_spec.rs#L595-L642),
[namespace wiring](https://github.com/openai/codex/blob/44918ea10c0f99151c6710411b4322c2f5c96bea/codex-rs/core/src/tools/spec_plan.rs#L786-L815),
and [V2 role/fork application](https://github.com/openai/codex/blob/44918ea10c0f99151c6710411b4322c2f5c96bea/codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs#L40-L85),
including [parent permission reapplication](https://github.com/openai/codex/blob/44918ea10c0f99151c6710411b4322c2f5c96bea/codex-rs/core/src/tools/handlers/multi_agents_common.rs#L150-L167).

## 2026-07-06: Force Structured Agent Output With A Schema; Never Gate-Parse Prose

**Evidence:** `plugins/saga/scripts/execution_spec.py` `_agent_schema_js`/`_agent_opts`,
`tests/test_workflow_emitter.py::test_returns_units_emit_structured_output_schema`. The 0.64
port run (`wf_12ad0962-7f7`) aborted twice at `__gate` on completed work: U1 returned fenced
JSON inside prose, U3 returned pure `key: value` prose, U4 a bare brace block mid-prose.

**Mechanism:** The emitted workflow's `__gate` accepted only a bare JSON dict as the agent's
final text, but agents wrap results in prose in unbounded ways — parsing is a losing game
played after the fact. The workflow harness already solves this at the source: passing
`schema:` in `agent()` opts forces a validated StructuredOutput tool call, retried at the
tool layer on mismatch. The emitter now derives that schema from each unit's `returns` keys;
`__gate` stays as a backstop only.

**Generalizable rule:** When a harness offers schema-forced output, demand structure at
generation time instead of parsing it out of free text afterward.

## 2026-07-06: Verify-Panel Consensus Must Recompute Over Reporters, Not Declared N (U7)

**Evidence:** `plugins/saga/scripts/execution_spec.py` `_emit_panel_reconciliation`
(new single-source helper), `plugins/saga/tests/test_verify_panel_robustness.py`.
Ported from `infiquetra-claude-plugins@9470edc`.

**Mechanism:** The old emitted refute-N panel compared `refute_count` against a threshold
baked over the declared `n`. A verifier that crashed or returned a malformed verdict
resolved to a `null`/shapeless slot that was silently counted as a *non-refuting* N/A vote,
so a degraded panel could pass a unit its reporting skeptics would have refuted. The port
filters verdicts to reporters (`v != null && Array.isArray(v.refuted)`), recomputes the
pass-rule threshold over the reporter count (`Math.max(1, Math.ceil(k/2))` majority,
`Math.max(1, k)` unanimous), and annotates UNDER-STRENGTH below the baked quorum floor —
excluding runtime-missing members instead of fabricating votes. The three emission sites
(thunk, iterate singleton, one-shot panel) were collapsed into one helper to kill the same
three-copy drift risk the verifier-opts helper already guards.

**Generalizable rule:** When aggregating a quorum over delegated agents, absence is not a
vote — recompute the threshold over the members that actually reported, and `max(1, …)`-guard
the all-missing case so `0 >= ceil(0/2)` cannot vacuously pass.

## 2026-07-06: Provenance-Manifest Trio Ports Clean; Only the CLI Root Path Is Host-Specific (U7)

**Evidence:** `plugins/saga/scripts/{provenance_manifest,manifest_store,manifest_reader}.py`,
ported from `9470edc`. Only edit beyond a verbatim copy: `manifest_reader.py --root` default
`.claude/saga-manifests` → `.codex/saga-manifests`.

**Mechanism:** The manifest schema is pure stdlib and leans only on already-Codex-adapted
siblings (`outcome_store.resolve_common_dir/_safe_name/_atomic_write`, `execution_spec`,
`completeness_gate`), so it needed no path rewrites of its own. The `Disposition` wire value
`fell-back-to-claude` and the `ProducerKind.CC_WORKFLOWS` label were kept verbatim: they are
serialized evidence strings shared across the ecosystem, so changing them would break
round-trip fidelity for zero behavioral gain in a repo with no stored manifests to migrate.

**Generalizable rule:** For a ported evidence/serialization schema, adapt only the host-path
*resolution* seams; leave wire-format enum values alone unless a stored corpus forces a
migration — schema fidelity beats cosmetic host-renaming.

## 2026-05-27: Test Suite Is a Useful First Proof Port

`test-suite` exercises the skill-plus-script boundary without requiring credentials,
orchestration primitives, or remote APIs. Adding `--dry-run` gives a package-boundary smoke
test that is safe to run repeatedly.

## 2026-05-27: Drift Checks Need Explicit Exceptions

Some strings that look platform-specific are real domain data, such as the `sdlc-manager`
`claude_md` rollout field. Validation should reject stale cache/source paths while allowing
documented compatibility keys.

## 2026-06-08: Validate Claimed Parsers Before Preserving Bad Markdown Shape

The Saga readability import confirmed that ideation schema fields are consumed as markdown by humans
and LLMs, not by a field-level parser. When a template claims a shape is needed for machine parsing,
verify the parser exists before keeping a hard-to-read generated format.

For Saga document outputs, compact fields render better as tables than as stacked bold labels. The
new `tests/test_saga_doc_formatting.py` gate catches the known collapse pattern without reflowing
template source prose.

## 2026-06-20: Vendored mission-control Mirrors Canonical Olympus-Routing By Behavior, Not Bytes

The fleet context audit retired Mount Olympus from active routing in the canonical
`infiquetra-claude-plugins/plugins/mission-control` (PR #230: `_TEAM_CHOICES` olympus->campps,
prepared-issue dispatch retarget, no-default boards). The vendored codex copy is a structural port
(`.codex-plugin`, `PORTABILITY.md`, `import_helpers.py`, no `agents/`/`commands/` dirs), so mirroring
is by **load-bearing behavior**, not file bytes.

Evidence: `plugins/mission-control/scripts/sdlc_manager.py` — `_TEAM_CHOICES = ("asgard", "campps")`,
`_TEAM_SAFE_STATUSES` campps->Idea, and the prepared-issue dispatch block retargeted olympus->campps.
The vendored `config/project-mappings.json` keeps its **deliberate** campps repo-based `board add`
routing (guarded by `tests/test_project_mappings_resolution.py`) — that is a vendored-specific feature,
not Olympus routing, so it was preserved rather than emptied to match canonical KTD17.

EC-1 KEEP held: `olympus:*` / `OLYMPUS_*` / `*.olympus.infiquetra.com` / `olympus.db` and the
legacy `if project_name == "mount-olympus"` read-only helpers stay (historical card reads), exactly
as canonical retained them. Whole-repo `context_census.py` exits 0; 158 mission-control tests pass.

Generalizable rule: when mirroring a fix into a vendored/ported copy, mirror the **routing semantics**
(constants, dispatch targets, defaults), not the file diff — and do not regress intentional
divergences that carry their own guard tests.

## 2026-07-26: Version-Drift Guards Live in More Places Than the Plugin Manifest, and a Green Suite Can Still Hide a Stale Assertion Against Removed Behavior

**Evidence:** codex#45 U6 (PR pending, this session). Bumping `saga` 0.79.0→0.80.0 and
`fleet-core` 0.11.0→0.12.0 required edits in seven live-tree files beyond the two
`.codex-plugin/plugin.json` manifests: `scripts/validate_codex_plugins.py`'s
`TARGET_EXPECTED_PLUGINS` dict (a hand-maintained version fixture, not derived from the
manifests), `docs/validation/saga-family-target-inventory.json` (also hand-maintained — no
generator script owns it), `README.md`'s plugin table, `docs/saga/generated/lifecycle-facts.json`
(this one DOES have a generator, `scripts/build_saga_docs_facts.py` — run it instead of
hand-editing), `docs/validation/verified-workflows-legacy-token-inventory.json` (a sha256-per-file
content-digest inventory that drifts whenever ANY file containing a tracked legacy token changes
byte-for-byte, including a CHANGELOG entry or a version string), and two hardcoded version-string
assertions inside `tests/test_codex_627_seam_refreeze_port_contract.py` and
`tests/test_outcome_cross_runtime_parity_port_contract.py` that were written against the
pre-cutover baseline and needed updating to the new version, not just left to fail.

**Mechanism:** none of these six drift points get updated by bumping the two plugin.json files.
`scripts/validate_codex_plugins.py::validate_repository` walks the **filesystem**
(`root.rglob("*")`), not just git-tracked paths, for the legacy-token inventory — so an untracked
stray file anywhere outside the excluded top-level set (`.claude/` is NOT excluded; only `.codex/`
is) shows up as a permanent, pre-existing "unclassified legacy workflow token path" error that no
amount of correct release-surface work can clear without touching repo hygiene explicitly ruled
out of scope. Confirmed via `git stash` that this exact error pre-dates the U6 diff.

**Generalizable rule:** before calling a version bump complete, `grep -rn "<old version string>"`
the whole tree (not just the plugin manifests) and re-run every generator script that owns a
derived doc (`build_saga_docs_facts.py`, `build_legacy_workflow_inventory.py --write` when the
untracked-file gap doesn't block it) rather than hand-patching generated JSON. Also: `--stage
unit` and `--stage classification` gates on a port-contract test file can go stale exactly the way
production code does — a test asserting `state == "classified"` was correct when U1 wrote it and
became a false assertion the moment U2–U5 landed, but nothing forced it to update because no gate
re-runs those assertions against the current manifest until the SAME test file is executed at
cutover. A green suite between units is not proof the fixed assertions in that suite still match
the state the units are supposed to reach.
