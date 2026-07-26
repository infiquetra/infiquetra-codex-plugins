# 2026-07-26 — codex#45 round-4: code-review P1 repairs

Branch `work/45-codex-refreeze-627-seam-cor3`, base `f79f141b`, code HEAD `d9e345d4` (repairs
uncommitted in the working tree). Routed from the programmatic `/code-review` that returned
**BLOCKED** — 0 P0, 8 P1, 12 P2, 11 P3 — recorded at
`docs/code-reviews/2026-07-26-issue-45-codex-627-seam-refreeze-code-review.md`.

The review's framing held up under repair: the engineering was sound, the claims about it were not.
Six of the eight P1s were corrections to prose and evidence; two needed real work.

## Disposition by finding

| ID | Finding | Disposition |
|---|---|---|
| P1 #1 | `plugins/saga/CHANGELOG.md` claimed the transient path "settles the attempt" | **Fixed** — clause struck, R7b(c) moved to a new `### Deferred` section naming the 3-vs-67 settlement-reference gap |
| P1 #2 | Port-contract row `src-3b34fc68149a7c76` rationale carried the same claim at `state: verified` | **Fixed** — rationale corrected; deferral named in-row. Row stays `verified` (it *is* verified for what it now claims) |
| P1 #3 | Three tests decided by collection order | **Fixed** — see below; proven across four permutations and a full-suite baseline diff |
| P1 #4 | Both CHANGELOGs claimed red-first for units with no red-first artifact | **Fixed** — audited all 24 `docs/validation/*.json`: exactly one carries a `red_first` block. Claim narrowed to that unit; U2/U3/U4 now state "post-port results only" |
| P1 #5 | `outcome_decompose.py` ported into zero contract rows | **Fixed** — sixth pathspec added, row re-derived by the tool, fresh evidence recorded, all unit stages green |
| P1 #6 | (withdrawn by the reviewer) | **No change** — the cutover-gate rationale is sound |
| P1 #7 | `lease-safe-substrate-u6.json` `repo_head` names a tree lacking its own test file | **Fixed** — `repo_head` kept (it is the head the run was based on) and annotated; `replayable_from: 30a37c21` added |
| P1 #8 | U6 self-review's "2520 passed, 4 deselected" cannot describe a 2731-test suite | **Partially explained, marked unreproducible** — see below |
| P1 #9 | R7a's coordinator-lock claim untested | **Fixed** — `test_non_transient_abort_releases_the_coordinator_lock` added |

Non-gating P2s repaired in the same artifacts: #16 (12/14 → 13/15, denominators disambiguated),
#17 (falsified cutover prediction replaced with the re-measured blocked state), #19 (`git stash`
now described as confirming what it actually confirms), #32 (precedent count corrected — one
manifest tags `U8`, two tag `U5`), #28 (the `U8` literal located in `validate_manifest:1379-1380`,
not `_validate_cutover_release_proof`, and the "Revisit when" grep target corrected).

**P2 #18 withdrawn.** The cutover artifact's `gates.full_suite: "2727 passed, 4 failed"` is
**correct** for the primary working tree. The review compared it against a clean-detached-worktree
measurement (`2727 passed, 4 skipped`). Both are right; they describe different trees. The field now
says which tree it means rather than being "corrected" into falsity.

**P2 #31 recorded, not repairable.** The cutover evidence `argv` points at
`tools/run_cross_runtime_outcome_acceptance.py`, which does not exist in this repo. An attempted fix
(`../infiquetra-claude-plugins/tools/...`) was **rejected by the validator** — `port_contract.py`
pins evidence `cwd` to `.` (`:1236`), rejects `..` traversal as an unsafe path, and enforces a
closed evidence key set (`:1196`) with no note field. The harness's real location is inexpressible
in that schema, so the argv was reverted and the limitation recorded in the artifact's own
`harness_location` field, where the schema is open.

## P1 #3 — the fix that had to be measured twice

`_load` re-execs each script and rebinds `sys.modules[name]`, so the last loader wins while earlier
modules' captured globals point at orphans. Making `_load` memoize removed the ordering dependence
**and regressed the suite** (one new failure against a `2025 passed / 0 failed` clean-worktree
baseline) because sharing one module object across eighteen files leaks module-global state that was
previously private per file. Replaced with an autouse `_pin_script_modules` fixture that re-pins
`sys.modules` to the module's own generation via `monkeypatch.setitem` — identity without sharing.

Proof: worktrees→board_sync **62 passed**; board_sync→worktrees **62 passed**; worktrees alone
**23**; board_sync alone **39** (23 + 39 = 62). Full `tests/ plugins/saga/tests/` run: **2025
passed**, byte-identical to the pre-repair baseline.

## P1 #8 — what is and is not reproducible

Measured at the reviewed commit in a clean worktree: the suite collects **2731** and runs **2727
passed, 4 skipped, 0 failed**. `plugins/mission-control/tests` collects exactly **211** and is in
`testpaths`; 2731 − 211 = **2520**, so the passed-count almost certainly came from a run excluding
that path. What does **not** reproduce: "4 deselected" — deselection needs `-k`/`-m`/`--deselect`
and no recorded `argv` carries one; the suite's own four non-passing tests are *skipped* (the
frozen-source oracles, which skip only when the sibling Claude clone is unresolvable). The pointer
to the cutover artifact is dead: that file records a different number, a different outcome word, and
no deselected set. Recorded as an unverified recollection rather than reconciled by guesswork.

## P1 #5 — closing the KTD8 hole

`init` re-run over the **unchanged** frozen range `cf15a09f..b464d090` with
`plugins/saga/scripts/outcome_decompose.py` added as a sixth pathspec. All five pre-existing
`row_id`s came back byte-identical, which is the evidence the derivation is deterministic and the
splice is not inventing history; `expected_count` derived to **6** and `inventory_sha256` was taken
from the tool, not hand-written. The frozen range did not move, so the runbook's prohibition on
extending a frozen source range is not engaged.

The new row is `src-a723b33e54606f82`, `codex-adapt`, units `["U5"]`, `state: verified`, backed by
freshly measured evidence (`docs/validation/codex-627-seam-refreeze-u5-decompose.json`: the three
prune oracles, **3 passed, 20 deselected**, exit 0) rather than by borrowing the predecessor
manifest's artifact. The gate then did exactly its job — it rejected the row as `implemented` with
no U5 evidence before accepting it as `verified` with evidence.

The branch's own guard suite then caught the shape change, which is the behavior you want from it:
`tests/test_codex_627_seam_refreeze_port_contract.py` pinned `SOURCE_PATHSPECS`, `EXPECTED_ROWS`,
`expected_count == 5`, and `verify_source(...)["row_count"] == 5`. All four were updated to the
six-row contract with the reason recorded inline, and the `expected_count` test's docstring now
carries the P1 #5 lesson rather than just the number. 21 passed.

## Gates

| Gate | Result |
|---|---|
| Full suite (clean detached worktree, repairs staged) | **2728 passed, 4 skipped, 0 failed** — baseline at `d9e345d4` was 2727 / 4 / 0, so +1 is exactly the new coordinator-lock test and nothing regressed |
| `ruff check .` | clean |
| `ruff format --check .` | 124 would-reformat at HEAD, **124 at base, identical sets** — zero formatting debt added |
| `mypy plugins/ scripts/ tests/` | 1 error, byte-identical to base (`discord_identity_assets` duplicate module) |
| `port_contract verify-source` | `verified: true` |
| `validate --stage classification` | valid |
| `validate --stage unit` U2/U3/U4/U5 | valid (U5 is new this round) |
| `validate --stage cutover` | **still BLOCKED** — re-measured, see below |
| Collection-order permutations | 62 / 62 / 23 / 39 — order-independent |

**Cutover remains blocked, and correctly so.** `validate --stage cutover` exits with "cutover
release proof is not retained by the evidence tag: external action release proof invalid: release
proof content_sha256 is invalid".

The first failing check is **not** the tag. `_validate_cutover_release_proof`
(`scripts/port_contract.py:1405-1458`) shells out to
`plugins/saga/scripts/external_action_release_matrix.py --verify`, which at `:697-701` reads the
proof's own `content_sha256`, pops it, rehashes the remainder and compares. This artifact is a
cross-runtime acceptance record and carries no `content_sha256` field at all, so the verifier raises
there and `_validate_expected_ref` (`:716-720`) never runs. The tag named in `codex.evidence_ref`
(`refs/tags/evidence/codex-627-seam-refreeze-20260725`) is **also** absent — only
`evidence/external-advisory-execution-20260711` and
`evidence/verified-workflows-modernization-20260711` exist — but that is an unreached second
blocker, not the cause.

Verified not a regression: running the verifier against this file's pre-repair `HEAD` version yields
a byte-identical error, so the round-4 edits neither caused nor changed it. Not repaired:
fabricating an external-action release run to clear it is gaming the gate, not passing it. The
structural mismatch — a cutover gate that only fits external-action ports — is the subject of the
existing DECISIONS entry.

An earlier draft of this section attributed the block to the missing tag. That was wrong in the same
way the findings this round repairs are wrong: it described a check that never executes. Corrected
here rather than quietly reworded.

**The four full-suite failures in the primary tree are environmental**, from one untracked file
(`.claude/codex/runs/20260725T235138Z-9a8250929b67/transcript.jsonl`) that the legacy-workflow token
scanner picks up because `.claude/` is not in its excluded-top-level set. The same commit in a clean
detached worktree has zero failures. `.gitignore` for `.claude/` remains out of scope for this unit.

**Legacy-workflow inventory rebuilt** because this round edited `DECISIONS.md`. Both pinned copies
moved in lockstep: `docs/validation/verified-workflows-legacy-token-inventory.json` and
`LEGACY_WORKFLOW_HISTORICAL_INVENTORY_SHA256` in `scripts/validate_codex_plugins.py`
(`ca960a7c…` → `63f29976…`). Entry count unchanged at 135, no additions or removals; the six changed
entries are exactly the token-bearing files this round edited. The builder cannot run in the primary
tree (it raises on the untracked `.claude/` path), so it was run with `--repo-root` against a clean
worktree carrying the repairs.

## Next step

Operator decision on committing. Nothing is committed, pushed, or PR'd — repairs sit in the working
tree by instruction. Suggested follow-ups for `mission-control` to file (this skill does not file
issues): the R7b(c) settlement deferral; the `.claude/` gitignore gap; and the `port_contract.py`
evidence-schema limitation that makes a cross-repo harness path unrecordable.
