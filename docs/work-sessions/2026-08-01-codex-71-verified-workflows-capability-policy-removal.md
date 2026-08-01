# 2026-08-01 — codex#71: Remove Verified Workflows' unenforceable capability policy

Branch `fix/71-remove-unenforceable-capability-policy`, based on `0c20724`. Executed as a seven-unit
`cc-workflows-ultracode` workflow with a three-verifier refute panel over four of the units. This
work session remains uncommitted, unpushed, and has no pull request.

## What was removed and why

Verified Workflows declared per-role and per-profile capabilities — `workspace_cap`, `external_cap`,
`external_mutation`, `allowed_profiles`, the `ROOT_ONLY_ACTIONS` constant, and the per-profile
`workspace` and `external` keys — and built compiler refusals on them. None of it was enforceable.
Codex 0.146 children inherit the parent turn's effective permission profile, so a profile can neither
widen nor narrow what a child may do, and a generated `agents/*.toml` carries no key that a sandbox
or network layer reads. Every declared capability string was compared only against a hardcoded
constant inside the plugin's own compiler.

Six refusals came out — three in `render_codex_agents.py` (the KTD4 profile-transition assert, the
category boundary-cap check, the `allowed_profiles` gate in `resolve_role`) and three in
`workflow_dispatch.py` (read-only profiles may not declare writes, non-Git roles may not name Git
commands, fallbacks may not cross a boundary). A seventh was rewritten rather than deleted: the
fallback check that read `role.allowed_profiles` now tests membership in `PROFILE_IDS`.

The post-hoc evidence layer is deliberately kept. `protocol_probe.py` still fails a run whose runtime
receipt shows a non-`git-integration-operator` role actually invoking Git, and an undeclared changed
path now synthesizes a finding in `result_contract.py` instead of raising.

## The issue's headline claim did not survive verification

Issue 71 attributes a Hermes publication stall to declared policy: the compiler assigned publication
to `git-integration-operator`, the agent committed, and could not push or open the pull request.
Neither removed mechanism can have caused that. The compiler's Git-word refusal read
`if GIT_WORD_RE.search(completion) and not owns_git`, and `owns_git` was true for that role
(pre-change `workflow_dispatch.py:314-318` at `0c20724`). The `work_medium` instruction text
exempted the same role by name. No run record survives under `~/.codex/verified-workflows/state/`,
so the stall's actual cause is unestablished.

Three independent sources reached this conclusion: U2's red-first reproduction against a
reconstructed pre-change tree, one verifier's reproduction in a clean worktree at `0c20724`, and a
direct read of the pre-change source during settlement. The issue's stop condition fires only if a
reproduction shows the Codex harness itself refused; it showed neither that nor a compiler refusal,
so the work proceeded on the mechanism argument, which is verifiable from source without the
anecdote. `DECISIONS.md` and `LEARNINGS.md` record the correction rather than the original story.

## Completed units

| Unit | Scope | Outcome |
|---|---|---|
| U1 | `role-registry.yaml` boundaries and `allowed_profiles` (216 lines), renderer refusals, seven rendered profiles | done |
| U2 | `workflow_dispatch.py` refusals, `ProfileResolution` boundary fields, dispatch tests | complete |
| U3 | `result_contract.py` — undeclared paths synthesize a finding instead of raising | complete |
| U4 | Developer-instruction template and profile re-render | success |
| U5 | Live guidance in README, `workflow-protocol.md`, `delegation-safety.md`, `review-workflow/SKILL.md`, `operator-choice.md` | complete |
| U6 | `DECISIONS.md` and `LEARNINGS.md` entries; U8 cutover gate confirmed passed | complete |
| U7 | `verified-workflows-legacy-token-inventory.json` regenerate | blocked, then cleared by root |

## Root-session repairs after the run

U7 halted rather than silently patching another unit's work, which was correct. Four repairs closed
the gap:

1. **U7's blocker.** `scripts/validate_codex_plugins.py` hardcodes
   `LEGACY_WORKFLOW_HISTORICAL_INVENTORY_SHA256`, and `DECISIONS.md` is classified
   `historical-evidence` in the inventory, so the journal entry staled a frozen constant the
   generator does not own. Bumped to `b397fd9d…`, matching precedent commit `a0d9e46`.
2. **A false sentence in `DECISIONS.md`**, refuted by one verifier and corroborated twice over —
   see above.
3. **A false docstring** on `test_publication_contract_with_push_and_pr_compiles_and_dispatches`
   calling itself a red-first reproduction. It is a regression guard; the row compiled before.
4. **`skills/run/SKILL.md`** stated "Only `git-integration-operator` may run Git commands" under a
   heading of compile-time rules. Now states that no compile-time rule restricts it and names
   `protocol_probe.py` as the observation that does.

## Addition beyond the plan

`LEGACY_WORKFLOW_EXCLUDED_TOP_LEVEL` in `scripts/validate_codex_plugins.py` excluded `.git`, `.venv`,
`.pytest_cache`, `.ruff_cache`, `.codex`, `.claude`, and `.serena`, but not `.saga`. The inventory
builder therefore scanned the saga's own settlement evidence and aborted with
`unclassified legacy workflow token paths`. `.saga` is runtime scratch in the same class as the two
sibling directories already excluded, and without it the repository gate cannot pass locally while
the saga lifecycle is doing its job. Added `.saga` to the set. Entry count is unchanged at 134, so
the exclusion prevented a crash rather than dropping tracked evidence. This is local-only —
a clean CI checkout has no `.saga`.

## Evidence

| Check | Result |
|---|---|
| Full suite, `uv run python -m pytest -q` | `2457 passed` |
| `scripts/validate_codex_plugins.py` | passed |
| `scripts/build_legacy_workflow_inventory.py --check` | exit 0 |
| `render_codex_agents.py --check --pretty` | exit 0 |
| Ruff, all changed Python files | clean |
| `git diff --check` | clean |
| Verify panels, 12 reviewers over 4 units | 0 gating refutations, 42 advisories logged |
| Dispatch settlement | 7/7 delivered, `halt_required: false`, dead-letter queue empty |

`python3 -m pytest` without `uv run` aborts at collection on `ModuleNotFoundError: No module named
'PIL'`. The dependency is present in the uv environment and absent from system Python; it is an
interpreter-selection artifact, not a repository gap, and predates this change.

## Verifier contract divergence — do not re-emit this harness

The saga's `verify.pass_rule` accepts only `majority` or `unanimous` and has no severity axis, so the
emitted gate counts any non-empty `refuted` array as a refutation. The first run died at the Unit 1
gate on 3/3 refutations that were entirely about the unit's prose while 45 claims about its code were
upheld. The operator chose to fix the contract rather than skip the panel.

`docs/plans/2026-08-01-verified-workflows-capability-policy-removal.workflow.js` was therefore
hand-patched to split the reviewer verdict into `refuted_deliverable` (gating: wrong files, missing
or fake tests, destroyed behavior, false `checks_run` claims, visibility gaps) and
`advisory_corrections` (non-gating: wrong explanations, misattributed lines, bad downstream advice).
The harness no longer matches `execution_spec.py emit` output for its spec. Re-emitting before this
change lands silently reverts the fix. The durable repair belongs upstream in the canonical
`infiquetra-claude-plugins` saga emitter and should be filed as its own issue.

The split earned its keep on the second run: two verifiers independently predicted U7's blocker as
advisories, and one verifier's single gating refutation caught a genuinely false sentence in a
permanent decision record — neither of which the old contract could have distinguished from prose
nitpicking.
