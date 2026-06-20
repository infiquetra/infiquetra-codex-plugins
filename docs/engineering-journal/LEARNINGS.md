# Learnings

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
