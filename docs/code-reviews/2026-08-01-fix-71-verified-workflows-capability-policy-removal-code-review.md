# Code review — issue 71, Verified Workflows capability-policy removal

Pre-PR gate on `fix/71-remove-unenforceable-capability-policy`. Two `P2` findings, no `P0`/`P1`.
Both are the same defect class the change exists to remove, surviving in a different shape: a
declaration nothing reads, and a guard that cannot fire.

## Review-result contract

| field | value |
|---|---|
| target | branch `fix/71-remove-unenforceable-capability-policy` |
| reviewed revision | `becc9a8` |
| merge base | `0c20724` (`origin/main`) |
| diff scope | 33 files, +2238 / -417 |
| mode | inline (no lens fan-out; the operator did not authorize subagent dispatch) |
| blocked | no — no `P0`/`P1` findings |
| scope check | CLEAN |
| plan completion | 13/13 requirements DONE |
| excluded from review | untracked `.claude/` and `.saga/` (machine-local saga state) |
| linked issue | https://github.com/infiquetra/infiquetra-codex-plugins/issues/71 |
| plan | `docs/plans/2026-08-01-verified-workflows-capability-policy-removal-plan.md` |
| work session | `docs/work-sessions/2026-08-01-codex-71-verified-workflows-capability-policy-removal.md` |

## Plan completion audit

| Req | Verdict | Evidence |
|---|---|---|
| R1 no `boundaries` block; renderer does not parse one | DONE | zero matches in registry and renderer; the three surviving hits are prose ("input trust boundaries", "approval boundaries") and one comment |
| R2 `allowed_profiles` gone from registry, `RoleSpec`, `resolve_role` | DONE | remaining mentions are negative assertions at `test_role_registry.py:51`, `:57`, `:286` and `test_sync_codex_agents.py:117` |
| R3 `ROOT_ONLY_ACTIONS` deleted | DONE | zero matches repo-wide |
| R4 per-profile `workspace`/`external` keys and `ProfileResolution` boundary fields removed | DONE | `workspace_boundary` and `external_boundary` zero matches |
| R5 three dispatch refusals removed | DONE | `GIT_WORD_RE`, "cannot declare writes", "widens" all absent |
| R6 publication contract compiles and dispatches | DONE | `test_workflow_dispatch.py:376` passes |
| R7 profile instructions carry role scope, not prohibitions | DONE | all seven `agents/*.toml` now read "Perform only the assigned bounded role"; zero prohibition phrases |
| R8 undeclared path synthesizes a finding, does not raise | DONE | `result_contract.py:286-302` extends `findings`; the surviving raises are unrelated type validation |
| R9 named mechanics unchanged | DONE | overlap check at `workflow_dispatch.py:447-483` absent from the diff; `git diff --name-only` requirement retained at `:312-314` |
| R10 no live guidance claims root owns Git or that a profile carries permission | DONE | see advisory A1 for a surviving statement that does not meet either clause |
| R11 `DECISIONS.md` superseding entry with `LEARNINGS.md` companion | DONE | both present, both corrected post-run |
| R12 `CHANGELOG.md`, archived plans, `codex-plugin-modernization-u3.json` unchanged | DONE | none in the diff; `docs/plans/` changes are additions only |
| R13 all four gates pass after the inventory regenerate | DONE | see Evidence |

## Findings

| # | Sev | File | Issue | Confidence | Route |
|---|:---:|---|---|:---:|---|
| 1 | P2 | `render_codex_agents.py:128-140` | Dead per-category profile policy retains the exact `git-operator → work_medium` pin this change removes | 100 | manual |
| 2 | P2 | `workflow_dispatch.py:318-321` | Retained fallback membership check is unreachable; its test passes via a different mechanism | 100 | manual |
| 3 | P3 | `validate_codex_plugins.py:300-308` | New `.saga` exclusion has no test | 100 | safe_auto |
| 4 | P3 | `render_codex_agents.py:691-695` | Deterministic-validator branch retains network and workspace constraints | 100 | advisory |

### 1. `ROLE_PROFILE_POLICY` is dead data that still declares the removed pin (P2)

`ROLE_PROFILE_POLICY` is read at exactly two sites, `render_codex_agents.py:574` and `:627`, both
`if category not in ROLE_PROFILE_POLICY` — membership tests against the keys. The `default` and
`allowed` values have no reader anywhere in the repository.

One of those unread values is `"git-operator": {"default": "work_medium", "allowed": ("work_medium",)}`.
That is the profile pin issue 71 exists to delete, restated in live source. The repository now
contains two contradictory statements of the same policy: `DECISIONS.md` and the passing test
`test_git_integration_operator_resolves_a_requested_work_high_profile` say the Git operator may
select any managed profile, while this dict says it may select only `work_medium`.

**Failure scenario.** A future reader greps for `git-operator` while deciding whether a publication
assignment may run at `work_high`, finds this dict, and concludes the pin holds. Or a refactor
reconnects the `allowed` tuple to `resolve_role` on the assumption it is live configuration,
silently reinstating the removed policy with no test failing.

The plan bounded U1's removal to the `workspace` and `external` keys, so leaving this was a
defensible reading of scope, and U1 self-reported it. It is still the change's own defect class
surviving inside the file the change is about.

**Fix.** Collapse to `ROLE_CATEGORIES = frozenset({"reviewer", "worker", "git-operator", ...})` and
update the two membership tests.

### 2. The retained fallback guard cannot fire, and its test does not test it (P2)

`workflow_dispatch.py:318-321` rejects a fallback whose profile is not in `renderer.PROFILE_IDS`.
It is unreachable. `FALLBACK_RE` at `:20-22` hardcodes the same seven profile names in its
alternation, so `_parse_fallbacks` raises at `:262-266` for any other name before the membership
check runs. U2 installed this check as the replacement for the deleted `allowed_profiles` check,
believing it enforces something.

`test_fallback_outside_the_managed_set_is_rejected` at `tests/test_workflow_dispatch.py:295-298`
uses `work_ultra@ambiguity` and asserts only `match="fallback"`. That substring appears in the
`where` string `assignment test.fallback`, so the test passes on the regex error. It would pass
unchanged if the membership check were deleted, and it would pass unchanged if it were the only
guard. The test's name claims coverage it does not provide.

**Failure scenario.** An eighth profile is added to `PROFILE_IDS` and the seven-name alternation in
`FALLBACK_RE` is not updated. A contract declaring `fallback: work_ultra@ambiguity` is refused with
"entries must be profile@condition with an underscore profile ID" — a syntax error naming the wrong
problem, for a profile that is in fact managed. No test catches the drift, because nothing pins the
two lists in sync.

**Fix.** Either build `FALLBACK_RE` from `PROFILE_IDS` so one list is authoritative, or drop the
alternation to `[a-z][a-z0-9_]*` and let the membership check do its job. Then tighten the test to
match the specific message it means to assert.

### 3. The new `.saga` exclusion has no test (P3)

`LEGACY_WORKFLOW_EXCLUDED_TOP_LEVEL` at `validate_codex_plugins.py:300-308` gained `.saga` in this
change. Nothing pins the set. Dropping the entry reintroduces the
`unclassified legacy workflow token paths` abort, but only when saga settlement evidence happens to
exist in the working tree — an intermittent, environment-dependent failure that a clean CI checkout
never reproduces. A one-line test asserting the runtime scratch directories are excluded closes it.

### 4. Deterministic-validator branch retains network and workspace constraints (P3, advisory)

`render_codex_agents.py:691-695` still enforces `command.network in {"none", "allowlisted-read"}` and
an empty `command.workspace_writes`. Same declarative shape as the layer this change removes. The
plan explicitly scoped the branch out of deletion and D1 narrowed that boundary to "do not delete the
branch", so this is honored scope, not drift. The branch is unreachable — no registry entry uses
`kind: deterministic-validator`. No action required; recorded so the next person removing declared
capability knows it is here.

## Advisory

**A1 — an unenforced patch-import convention survives.** `plugins/verified-workflows/README.md:130`
and `plugins/saga/README.md:54` state that only the Git integration operator may import a patch
produced in a disposable clone. The only enforcement is a docstring at
`plugins/saga/scripts/external_action_adapters.py:353` ("callers must assign this to the Git
operator"). This is pre-existing, untouched by this diff, and does not violate R10 — it neither
claims the root session owns Git nor claims a profile carries permission. Same defect family,
different subsystem; worth its own issue rather than scope creep here.

**A2 — the issue's causal premise did not survive verification.** Recorded in full in the work
session and corrected in `DECISIONS.md`. Three independent reproductions agree the Hermes
publication stall cannot have been caused by either removed mechanism. The removal stands on the
inheritance argument, which is source-verifiable. Not a code finding; noted because a reviewer
reading issue 71 alone would expect a behavior change the diff does not produce.

## Evidence

| Check | Result |
|---|---|
| `uv run python -m pytest -q` | `2457 passed` |
| Targeted: dispatch, result-contract, registry, sync | `88 passed` |
| `scripts/validate_codex_plugins.py` | passed |
| `scripts/build_legacy_workflow_inventory.py --check` | exit 0 |
| `render_codex_agents.py --check --pretty` | exit 0 |
| Ruff, all changed Python | clean |
| `git diff --check` | clean |

`python3 -m pytest` without `uv run` aborts at collection on missing Pillow. The dependency is in the
uv environment and absent from system Python; interpreter selection, not a repository gap, and it
predates this change.

## Coverage and residual risk

Suppressed below anchor 75: none — every finding above is verified at source.

**Review depth.** This pass ran inline. Findings 1, 2, and 4 came from reading outside the diff
(`FALLBACK_RE`, the `ROLE_PROFILE_POLICY` reader sites, `protocol_probe.py`), which is where the
enum-completeness category lives. An adversarial fan-out would add independent confirmation, not
different coverage, on a diff this well-instrumented — the workflow's own twelve-verifier panel
already ran over four of the seven units.

**Residual risk carried forward from the plan, unchanged:** no run record exists under
`~/.codex/verified-workflows/state/` for the Hermes failure, so its cause stays unestablished. The
live proof the issue proposes — compile an approved publication assignment in a disposable branch,
verify the runtime receipt, push and open a PR from that assignment rather than from root — has not
been run. It belongs to `/qa`, not to this gate.

**Testing gap:** finding 2's test asserts a message substring loose enough to pass on the wrong
error path. Finding 3's exclusion set is unpinned.
