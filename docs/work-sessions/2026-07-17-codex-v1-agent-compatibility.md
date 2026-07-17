# Work Session: Codex V1 Agent Compatibility

## Goal

Restore explicit named-agent model and reasoning-effort selection for GPT-5.6 Sol and Terra by
temporarily selecting stable MultiAgent V1, while preserving the five maintained agent profiles and
an explicit rollback path.

## Completed Work

- **U1:** Added a full-catalog transformer and installer that changes only Sol and Terra
  `multi_agent_version`, writes UTF-8 without BOM atomically, installs an absolute
  `model_catalog_json`, validates readback, and restores a one-time config backup.
- **U2:** Replaced active V2 bootstrap guidance with the stable V1 contract while preserving the
  digest-bound V2 snapshot and cutover receipts as historical evidence.
- **U3:** Added `verified-workflows:select-agent` for the five maintained profiles and kept ordinary
  native delegation independent of Verified Workflow gates.
- **U4:** Completed focused tests, repository validation, isolated install/check/rollback proof,
  code review, and the full suite. Fresh-session proof, PR, merge, and worktree cleanup remain.

## Decisions And Deviations

- Source selection is cache-first, then bundled, with explicit `--source-json`. This differs from
  the plan's initial refreshed-command wording because the ordinary command can resolve the already
  configured override on a reinstall.
- The frozen V2 capability snapshot was not rewritten. It is historical port evidence, not current
  runtime policy; active documentation and tests now point to live V1 readback instead.
- Ultra remains unsupported and was not tested because its proactive delegation may depend on V2.
- Verified Workflows was not used as the execution backend because its current bootstrap depends on
  the V2 behavior being repaired. The operator approved root-inline execution through merge.

## Review

- Review: `docs/code-reviews/2026-07-17-fix-codex-v1-agent-compatibility-code-review.md`
- Reviewed working tree base: `38518d825330b44a8232a4e09938452905049d5d`
- Result: no P0/P1 findings; one P2 documentation mismatch found and resolved.
- External second opinion: not executed because the best-effort external action was not approved.

## Checks

- Focused compatibility and validator suite: `113 passed`
- Full suite: `2241 passed in 177.70s`
- `python3 scripts/validate_codex_plugins.py`: passed
- `uv run ruff check .`: passed
- `git diff --check`: passed
- Bandit: no medium/high findings; low fixed-argv subprocess warnings only
- Isolated catalog: source `bundled`, Sol/Terra/Luna `v1`, 292501 bytes, no BOM
- Isolated rollback: restored the original config byte-for-byte

## Next

Commit the reviewed tree, install the override into the local Codex profile, verify fresh Sol and
Terra sessions report the requested named child model and effort, then open and merge the PR after
required checks pass.
