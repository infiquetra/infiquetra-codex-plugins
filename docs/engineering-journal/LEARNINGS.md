# Learnings

## 2026-05-27: Test Suite Is a Useful First Proof Port

`test-suite` exercises the skill-plus-script boundary without requiring credentials,
orchestration primitives, or remote APIs. Adding `--dry-run` gives a package-boundary smoke
test that is safe to run repeatedly.

## 2026-05-27: Drift Checks Need Explicit Exceptions

Some strings that look platform-specific are real domain data, such as the `sdlc-manager`
`claude_md` rollout field. Validation should reject stale cache/source paths while allowing
documented compatibility keys.
