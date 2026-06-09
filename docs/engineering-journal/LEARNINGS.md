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
