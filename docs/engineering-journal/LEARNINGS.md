# Learnings

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
