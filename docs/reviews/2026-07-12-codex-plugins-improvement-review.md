# Codex Plugins Improvement Review

- **Date:** 2026-07-12
- **Baseline:** `main` @ `fc077d4`
- **Scope:** full repo, weighted toward the Saga family (`saga`, `verified-workflows`, `fleet-core`, `deploy`, `mission-control`); lighter pass over `test-suite`, `python-toolkit`, `home-lab-ops`, `unifi`, `discord-identity-assets`; repo infrastructure (`scripts/validate_codex_plugins.py`, marketplace, `docs/portability/`).
- **Method:** three parallel read-only review passes (skill surface, Python code, adjacent plugins + infrastructure), followed by first-hand re-verification of every P0/P1 claim against the working tree. Every finding cites `file:line` evidence. Counts (duplication, coverage) come from grep/scan sweeps of the tree at the baseline commit.
- **Codex framing:** every recommendation here is implementable inside the Codex plugin surface this repo already uses (skills + `description`-based discovery, bundled scripts, `.codex-plugin` manifests, plugin hooks with `$PLUGIN_ROOT`, custom-agent TOMLs, marketplace policy). Where the repo currently does something a Codex-native mechanism does better, that is called out explicitly.

Priorities: **P0** = safety/correctness defect, fix before further feature work. **P1** = high-value, small-to-medium effort. **P2** = structural, schedule deliberately. **P3** = enhancement.

---

## Top 10, ranked

| # | Pri | Improvement | Where |
|---|-----|-------------|-------|
| 1 | P0 | Gate the `outcome advance` auto-merge behind `--autonomous` (today it fires real `gh pr merge` on every tick) | `plugins/saga/scripts/outcome.py`, `outcome_merge.py` |
| 2 | P1 | Standardize script invocation on a convention that survives the installed cache layout (the dominant repo-root-relative form breaks when installed) | all `SKILL.md` script calls |
| 3 | P1 | Move `when_to_use` trigger content into `description` in 16 skills — Codex discovery reads only `description`; `when_to_use` is inert | mission-control, home-lab-ops, python-toolkit, test-suite |
| 4 | P1 | Replace literal Claude subagent names (`Explore`/`Task`/`general-purpose`) with the Codex-neutral conditional-subagent vocabulary the corpus already defines | 15 saga skill files |
| 5 | P1 | Fix the state-durability trio: `saga.py` atomic-write race, `effort_ledger.py` unlocked read-modify-write, non-atomic writers in `promote_scan.py`/`lifecycle_review.py` | saga scripts |
| 6 | P1 | Extend `validate_codex_plugins.py` from manifest checks to prose-adjacent contracts (path resolution, description policy, home paths, referenced-file existence, CHANGELOG presence) | `scripts/validate_codex_plugins.py` |
| 7 | P2 | Delete or quarantine the dead Claude-era Workflow emitter (1,877 lines incl. the repo's largest test file, zero skill references) | `execution_spec.py`, `workflow_emitter.py`, `tests/test_workflow_emitter.py` |
| 8 | P2 | Fix the post-cutover documentation drift cluster (five files still describe the pre-2026-07-11 world where team-execution is active) | `docs/portability/`, `verified-workflows/README.md`, `saga/PORTABILITY.md`, `docs/validation.md` |
| 9 | P2 | Package-ify `plugins/saga/scripts/` — one entrypoint, shared CLI/IO primitives; retires 38 copied `sys.path` shims and 51 hand-rolled `main()`s | saga scripts |
| 10 | P2 | Decide `ship_ceremony.py`: wire it into `/work` with a structural tier gate, or delete it (currently orphaned but merge-capable) | `plugins/saga/scripts/ship_ceremony.py` |

---

## 1. Safety: the mutation boundary is prose, not code (P0)

The repo's stated safety model is strong — "preview or propose by default; never silently merge, push, or write GitHub state" (`plugins/saga/skills/outcome/SKILL.md:164-169`, and the same contract in the harness-delta and PORTABILITY docs). But in three separate places the enforcement lives in SKILL.md prose or calling convention while the code path itself is ungated. A Codex agent follows prose *most* of the time; a boundary that matters must hold when it doesn't.

### 1.1 `outcome advance` auto-merges without `--autonomous` — verified

- `plugins/saga/skills/outcome/SKILL.md:108` promises: "By default `advance` performs **no** GitHub writes — it dispatches and derives status, nothing more." Lines 121-123 add that merging is "never autonomous — always the operator's keystroke."
- Reality: the `advance` CLI wiring passes `merge_processor=production_merge_processor()` unconditionally (`outcome.py:2050`), and the tick loop runs it on **every tick with no `autonomous` check** (`outcome.py:1041-1044`) — while board-sync, thirty lines below, is correctly gated behind `if autonomous:` (`outcome.py:1077`).
- The only merge guard is `if node.gated or node.risky or node.destructive` (`outcome_merge.py:132-133`), and all three flags default to `False` (`outcome_spec.py:124-126`). Nothing in `outcome_decompose.py` sets them. So a plain `python3 outcome.py advance <id>` squash-merges (`outcome_github.py:329-346`, real `gh pr merge --squash`) any unflagged, CI-clean PR.
- Compounding: `reversibility_certificate.py` — the repo's one default-deny write authority — explicitly scopes itself to board/issue verbs and excludes merge ("Merge, deploy, and repo-level mutations are intentionally absent (R20)", `reversibility_certificate.py:16,51`). Merge policy therefore lives entirely in three booleans with an unsafe default.

**Fix:** gate `merge_processor` on `args.autonomous` (or a dedicated `--allow-auto-merge`), matching the board-sync precedent; or flip the `gated` default to `True` for code leaves. Then pin the promise with a regression test: `advance` without the flag makes zero `gh pr merge` calls (today `tests/test_outcome_merge_queue.py` covers the merge state machine thoroughly but nothing asserts the SKILL.md's default-posture claim — which is currently false).

**Also:** `gated`/`risky`/`destructive` are documented only as degrade-decision inputs (`outcome_spec.py:110-111`, `references/outcome-spec.md:48`); their reuse as the auto-merge gate is invisible to a spec author. Split into distinct fields or document the dual meaning at the point of authorship.

### 1.2 `ship_ceremony.py`: orphaned, merge-capable, tier-recorded-but-not-enforced — verified orphan

591 lines with an installable `git ship` alias (`ship_ceremony.py:485-514`) that can execute `merge` and `branch_delete` — both declared `ALWAYS_OPERATOR` in its own `TRANSITION_TIERS` (`ship_ceremony.py:95-103`) — yet `run()` (`:393-424`) never checks the tier before executing; the tier is only *recorded* alongside the saga tick. No SKILL.md anywhere invokes this script (verified: zero references under `plugins/` and `docs/`); `/work` instead hand-rolls the same commit→PR→merge sequence in prose (`work/SKILL.md:397-410`).

**Fix:** either wire `/work` to call it and make `run()` require an explicit `--confirm-tier <name>` matching the upcoming transition, or delete the module. Keeping an unreferenced, ungated merge-capable CLI in the tree is the worst of both options.

### 1.3 The pattern, named

Same shape in a third place: `external_action_runtime.py`'s prepare→approve→execute chain is structurally sound (execute refuses non-APPROVED state, approval fingerprint re-validated — `external_action_runtime.py:158-200`), but the `operator=` identity is an unverified string; the gate holds only if the calling skill honors its prose. That one is acceptable (the approval state machine is real); 1.1 and 1.2 are not. The general improvement: **any operation on the wrong side of the mutation boundary gets a structural default-deny in code — the SKILL.md prose is documentation of the gate, never the gate itself.**

---

## 2. Script invocation portability: the dominant convention breaks when installed (P1)

This is the finding where the two runtime contexts — this development checkout vs. the installed plugin — point in opposite directions, and the repo currently standardizes on the wrong one.

- The corpus's dominant convention (~90 occurrences) is repo-root-relative: `python3 plugins/saga/scripts/saga.py ...`.
- The installed cache layout is `~/.codex/plugins/cache/infiquetra-codex-plugins/saga/<version>/{skills,scripts,references,...}` — verified on this machine. **There is no `plugins/saga/` prefix in the installed layout.** When saga runs installed in a target repo (its actual purpose), every repo-root-relative invocation fails: cwd is the target repo, and no `plugins/saga/` exists there.
- The one "outlier" — `python3 ../../scripts/lifecycle_review.py`, explicitly documented as "relative to this skill" (`doc-review/SKILL.md:59,69-74`, `spec/SKILL.md:141-144`) — is the only convention that resolves in **both** layouts, because `scripts/` is a sibling of `skills/` in the checkout and in the cache alike.

**Fix:** standardize all script invocations on skill-file-relative paths with an explicit anchor sentence ("resolve relative to this skill file's directory"), i.e., generalize the doc-review convention rather than eliminating it. Alternative worth a one-time verification: if Codex expands `$PLUGIN_ROOT` in skill context the way it verifiably does for hooks commands (`validate_codex_plugins.py:1170-1220` checks the hooks.json command string uses it), `$PLUGIN_ROOT/scripts/...` is even cleaner. Either way: pick one convention, convert all ~90 call sites, and add a validator rule (see §7) so the two schemes never coexist again.

The same disease affects documentation cross-references, in three forms (all verified):

- 52 citations use a bare `saga/...` prefix (`saga/references/formatting-style.md` alone: 21 hits across 17 files) that resolves in **neither** layout — a leftover of Claude's plugin-namespace addressing.
- `references/operator-choice.md` is cited bare (resolving to a nonexistent per-skill path) from `loop/SKILL.md:240`, `work/SKILL.md:185`, `plan/SKILL.md:279`, `office-hours/SKILL.md:39,232`, while six other skills correctly use `../../references/operator-choice.md`.
- `dispatch-table.md` is spelled four different ways across the corpus, only one of which resolves from a sibling skill.

**Fix:** one addressing scheme for docs too — skill-file-relative — applied mechanically, then enforced by the validator.

---

## 3. Codex-native skill discovery is underused (P1)

Codex routes to skills on `name` + `description` frontmatter alone. That makes `description` the single highest-leverage line in every skill, and the repo treats it inconsistently.

### 3.1 `when_to_use` is dead weight — verified, 16 files

Sixteen SKILL.md files (mission-control ×7, home-lab-ops ×5, python-toolkit ×3, test-suite ×1) put their entire trigger vocabulary in a custom `when_to_use:` key that Codex does not read, leaving `description` at 71–167 characters with no trigger phrasing. `deploy` and `verified-workflows` already do it right (triggers inlined in `description`). **Fix:** fold `when_to_use` content into `description` (respecting the 1024-char cap) across all 16 files; drop the dead key.

### 3.2 Saga description drift

Within saga itself, descriptions span 87–977 characters; 9 of 22 lack any trigger phrasing. The worst combination is short *and* trigger-free on exactly the skills with the most ambiguous natural asks: `doc-review/SKILL.md:3` (87 chars — "review this" needs triggers to route here vs. code-review/founder-review) and `handoff/SKILL.md:3` (88 chars). At the other end, `retro` (977) and `optimize` (761) are compressed skill bodies crammed into frontmatter. **Fix:** adopt a description policy — a length band (roughly 150–600 chars) plus a mandatory trigger clause — and enforce it in the validator (§7).

### 3.3 Literal Claude subagent names — verified, 15 files

`` `Explore` ``, `` `Task` ``, and once `general-purpose` — Claude Code's built-in subagent types — appear as the concrete dispatch mechanism in 15 skill markdown files (e.g. `brainstorm/SKILL.md:17,133`, `ideate/SKILL.md:212`, `code-review/SKILL.md:190`, `plan/SKILL.md:150-151,263`, `qa/SKILL.md:171`, `investigate/SKILL.md:210`, `resume/SKILL.md:248,330`, `retro/SKILL.md:181,311`, plus reference files). These names don't exist in Codex. The corpus already has the right vocabulary — `outcome/SKILL.md:89-92`: "Codex subagents or multi-agent tools only when callable in the current session and safe for the leaf" — and verified-workflows already demonstrates the Codex-native alternative: real custom-agent TOMLs (`agents/{review_high,review_max,test_medium,scan_low,monitor_low}.toml`) with `model`, `model_reasoning_effort`, `sandbox_mode`. **Fix:** a mechanical rename of all sites to the conditional-subagent phrasing, with one shared definition in `references/operator-choice.md`; where a saga skill genuinely wants a reusable reviewer/researcher persona, define a custom-agent TOML the way verified-workflows does rather than naming a Claude built-in.

For the record, the corpus is otherwise clean on literal Claude-isms: zero hits for `AskUserQuestion`, `Task tool`, `commands/`, or `.claude-plugin` in active skill text, and every skill correctly uses the deferred "Codex blocking question" + ToolSearch pattern. Inactive backends (`Workflow`, `fork`, `goal`) are consistently negative-gated in prose. The port discipline is genuinely good — 3.3 is the one systematic leak.

---

## 4. State durability and robustness (P1)

The codebase knows how to do this right — `outcome_store.py:184-221` has a pid+thread+monotonic-nonce atomic write with an `os.link` write-once — but the hardening never propagated to the other writers.

1. **`saga.py` — the primary writer for `/work` — has the weakest atomic write in the repo (verified).** `_atomic_write` (`saga.py:653-657`) uses a fixed `.tmp` filename (no pid/nonce), and its caller `_allocate_envelope_path` (`saga.py:640-650`) does exists-check-then-write. Two concurrent `saga.py save` calls for the same saga id (plausible under outcome-DAG parallel dispatch) can truncate each other's tmp file. Port `outcome_store._unique_tmp` here.
2. **`effort_ledger.py` has no locking and no atomicity (verified).** The CLI cycle is `load → mutate → save` per subprocess, and `save()` is a bare `path.write_text` (`effort_ledger.py:186-188`). Concurrent `allocate`/`record` calls silently drop each other's updates. `run_ledger.py:130-142` already demonstrates the house `fcntl.flock` pattern — apply it, and route `save` through an atomic replace.
3. **Direct `write_text` in `promote_scan.py:526-531` and `lifecycle_review.py:247,329`** — a crash mid-write tears a context-library journal or an ADR review file. Same fix.
4. **16 `subprocess.run` sites without `timeout=`** — notably `external_action_runtime.py:533,550,624` (on the critical path of every external-action lifecycle transition; a hung `gh` auth prompt blocks it forever) and nine sites in `external_action_release_matrix.py`. The repo's own discipline elsewhere is `timeout=10/20/60` (`outcome_store.py:113`, `outcome_github.py:42`, `saga.py:550`).
5. **Unguarded `json.loads` on operator-supplied files and subprocess stdout** (16 sites, e.g. `effort_ledger.py:193`, `manifest_store.py:325,347,349`, `ship_ceremony.py:169,463`, `outcome.py:2133`) — corrupted state files surface as raw tracebacks instead of the modules' own clean-error envelopes.

**Consolidation:** four independent atomic-write implementations (`outcome_store`, `board_progression`, `external_action_store`, `saga.py`) with different safety levels, five independent git/gh subprocess runners, and four bespoke load-a-sibling-module loaders. `fleet-core` is the designed home for shared primitives, and its vendored-shim + byte-drift-test pattern (`plugins/fleet-core/tests/test_shim_drift.py`) already proves the distribution mechanism works. Add `atomic_io.py` and `proc.py` (subprocess wrapper with mandatory timeout) to `fleet_commons` and migrate the callers.

---

## 5. Architecture and dead code (P2)

1. **Package-ify `plugins/saga/scripts/`.** Eighty-four flat files, of which ~26 are actually shell-invoked from skills and the rest are internal library modules; 38 carry an identical `sys.path.insert` shim, 51 hand-roll `main()`/argparse/error-envelope boilerplate, and one module reaches into another's underscore-private function (`manifest_store.py:127` → `outcome_store._atomic_write`). A package `__init__.py` plus one `saga` CLI entrypoint (subcommand per current script) retires all three classes of duplication at once. The bundled-script model still works — the entrypoint is just another bundled file — and the skills' invocation lines get shorter, not longer. First increment, without a full rewrite: a shared `cli.py` (`run_subcommand(parser, handlers)` + the common `{"ok": bool, "error": str}` emitter).
2. **Delete or quarantine the Workflow emitter (verified orphan).** `emit_workflow_script` in `execution_spec.py` (~150 lines of JavaScript code generation) plus `workflow_emitter.py` (175 lines) have zero references from any skill or production import, and `outcome/SKILL.md:94-99` already declares Workflow an inactive backend. Their test file, `tests/test_workflow_emitter.py`, is 1,702 lines — the largest test file in the repo, entirely exercising unreachable code. The repo already has the correct pattern for retired backends: a small typed degrade record (`lifecycle_state.recheck_orchestration_capability`, `lifecycle_state.py:176-223`). Keep that; drop the generator. This is the single largest maintenance-cost-to-value item found.
3. **Split `outcome.py` (94.7 KB).** The `outcome_*` satellites are a genuinely well-factored package (pure functions, injected runners/clocks, single responsibilities); `outcome.py` is simultaneously CLI, reconcile-tick loop, production-adapter factory, and graph-mutation dispatch. Extract the production factories and the tick loop; leave `outcome.py` as parsing + wiring.
4. **Single-source the backend vocabulary.** `ORCHESTRATION_TIERS`/`NODE_BACKENDS`/degrade-ladder constants are declared in three modules (`lifecycle_state.py:11-20`, `outcome_spec.py:82-87`, `outcome_dispatcher.py:46-54`) synced only by comments.

---

## 6. Documentation governance (P2)

### 6.1 The post-cutover drift cluster — verified

Commit `e27c6f9` (2026-07-11) deleted `plugins/team-execution/` and activated verified-workflows, but the narrative prose was never swept. Five surfaces still describe the pre-cutover world:

- `plugins/verified-workflows/README.md` **contradicts itself**: line 5-6 "the retired package is not co-installed" vs. line 204-205 "the legacy package remains byte-stable and solely marketplace-active... do not install both."
- `plugins/verified-workflows/PORTABILITY.md:104-105` — same stale language.
- `plugins/saga/PORTABILITY.md:42,46,55` — still names `team-execution` as an active owning plugin and backend, contradicting its own "Current Port Contract" section thirty lines above.
- `docs/portability/matrix.md:35,44-49` — "team-execution remains the only active workflow package before cutover"; verified-workflows has no matrix row.
- `docs/validation.md:16` — describes the validator's default mode as "requires Team Execution as the sole active workflow package."
- Also `docs/portability/saga-family-state-policy.md:5-11` still defines state roots for the deleted plugin.

**Fix:** one sweep commit. Then the process fix: the release checklist (or validator, §7) should require that a cutover commit touches the narrative docs that describe the cutover state — this cluster is evidence that "keep matrix.md in sync" (`AGENTS.md:33`) is aspirational.

### 6.2 Governance docs need currency markers

`docs/portability/codex-saga-041-harness-delta.md` reads as ground-truth policy but is contradicted by shipped, deliberate, tested behavior — the saga SessionStart hook (`plugins/saga/hooks/`, KTD8 in the 2026-07-10 modernization plan, tested by `tests/test_saga_session_context.py`) and the backend rename. The hook itself is fine: Codex plugins natively bundle hooks (`hooks/hooks.json`, `$PLUGIN_ROOT`, SubagentStart/SubagentStop — the validator verifies verified-workflows' hook surface exactly, `validate_codex_plugins.py:1170-1220`). What's broken is a policy doc with no "superseded in part by …" header. **Fix:** one-line supersession pointers on 041 (and a "verified against version X" line as a convention for future classification docs). Same class of fix: `references/saga-spec.md:2` still says "plugin version: 0.4.0" against a 0.75.17 manifest.

### 6.3 Status and provenance discipline

- **Two unaligned status vocabularies:** root README (`active`/`baseline`/`proof port`) vs. per-plugin `PORTABILITY.md` (`proof-port`/`included`). Only 2 of 10 plugins agree with themselves (deploy and mission-control say "proof-port" about themselves while README says "active"). Pick one axis.
- **Two-tier provenance with no stated reason:** saga/fleet-core record commit windows with per-cycle breakdowns; mission-control records one frozen SHA; home-lab-ops, python-toolkit, unifi, test-suite record no SHA at all. Minimum bar: a frozen upstream SHA for every Claude-lineage plugin.
- **Vendor drift is undetectable for mission-control:** the only guard (`test_prompt_alignment.py`) checks internal consistency, never the upstream. Even a checklisted "diff against upstream, record new SHA" step per release cycle beats the current nothing.

### 6.4 Stale references — verified

`plugins/unifi/README.md:163,166` instructs running two test files that don't exist (only `test_unifi_retry.py` does). `docs/validation.md:26` embeds a `/Users/jefcox/...` command no other operator can run.

---

## 7. Validator: turn conventions into gates (P1)

`validate_codex_plugins.py` (2,189 lines) is the repo's single pre-PR quality gate and its strongest asset — but its checks stop at manifests, inventories, and a six-literal-string stale-pattern list. Every defect class in this review that shipped silently is one the validator could catch mechanically:

1. **Skill-body path resolution:** every backtick `python3 <path>` and markdown cross-reference in `skills/**/*.md` must resolve under the chosen convention (§2) from both the checkout and the cache layout. Would have caught the `saga/` prefix (52 sites), the bare `references/operator-choice.md` drift, and the convention split.
2. **Description policy:** presence, length band, trigger clause, and rejection of unrecognized frontmatter keys (`when_to_use`, `script:`) — or their explicit allowlisting. Would have caught §3.1/3.2.
3. **Generic home-path sweep:** `/Users/<name>` outside a lineage-evidence allowlist. The README already *claims* the validator checks "stale host paths"; today that check is six literal strings (`validate_codex_plugins.py:252`) and one U8-artifact-scoped scan (`:2036`). Would have caught `docs/validation.md:26` and four PORTABILITY files.
4. **`CHANGELOG.md` presence for every plugin** (today hardcoded to three; `discord-identity-assets` has none).
5. **README-referenced file existence** (catches the unifi phantom tests).
6. **`python3` (not bare `python`) in all skill/README code fences** (test-suite ×8 and unifi currently drift).
7. **Claude-ism token scan over skill bodies:** `` `Explore` ``/`` `Task` ``/`general-purpose` as agent names — cheap insurance that §3.3 never regresses after the rename.

---

## 8. Smaller items and enhancements

- **Factor the six near-verbatim `## External Action Runtime` sections** (`brainstorm`, `plan`, `work`, `code-review`, `doc-review`, `ideate`; ~66 lines) into one shared reference parameterized by `--stage` — `external-action-defaults.yaml` already encodes everything the prose restates. Then adding stages for the decision-heavy gates that currently lack one (`qa`, `founder-review`, `retro`) becomes a yaml row, not six paragraphs. (P2, enables P3 capability growth.)
- **Split `references/operator-choice.md`** — the most-cited shared contract (15 skills) — into an agent-facing decision table and a maintainer capability-status log; the current file leads with "U5 canonical workflow boundary; cutover gated by U8" register that an executing agent has to tunnel through. (P2)
- **Relocate the five orphaned references** never loaded by any skill or script (`dispatch-adapter-contract.md`, `engine-output-trust-boundary.md`, `execution-spec.md`, `run-fact-ledger.md`, `sandbox-spawn-sites.md` — 195 lines of port-tracking artifacts) from `plugins/saga/references/` to `docs/portability/`. (P3)
- **Test backfill** for the 10 skill-invoked scripts with zero coverage, prioritizing `parse_issue.py` (used by `/work`, `/plan`, `/loop` routing) and `lifecycle_review.py` (untested file-writer, also non-atomic — §4.3). (P2)
- **`fleet_commons_shim` failure mode:** `resolve_root()` raises a raw `RuntimeError` at import time when fleet-core can't resolve (`fleet_commons_shim.py:122-153`), crashing consumers (`execution_spec.py:58`, `engine_dispatch.py:28-30`) instead of failing through the repo's typed halt-receipt vocabulary. (P2)
- **mission-control `claude_md` field:** the rollout skill's data model checks target repos for a `CLAUDE.md` SDLC section (`sdlc_manager.py:1958,2109,5144`) — documented as a data-model key, not a host dependency, but a Codex-native rollout should recognize `AGENTS.md` as an equally valid instruction surface, since that is the convention this very repo uses. Land it upstream first per the vendoring rule. (P3)
- **Repo hygiene:** untrack the three `.serena/` files (tracked from before the ignore rule; `project.yml` shows as perpetually modified), and add an explicit `.mypy_cache/` line to `.gitignore` rather than relying on mypy's self-generated ignore. (P3)
- **Positive patterns worth preserving** (called out so nobody "fixes" them): the `outcome_*` satellite modules' injected-runner purity; `deploy`'s `--confirm-plan` exact-triple match gate (`mint_tag.py:259-261`); `external_action_runtime`'s approval fingerprint; the shim byte-drift test; the `ceo-review` thin-alias pattern; the "read the dispatch table, never restate it" discipline; verified-workflows' native hooks + agent TOMLs, which are the model for §3.3's fix.

---

## Suggested sequencing

1. **Safety first, one PR:** §1.1 merge gate + regression test, §1.2 ship_ceremony decision. Small diff, closes the only findings where the tool can act against its own documented contract.
2. **Durability, one PR:** §4.1–4.3 (atomic writes + locking), §4.4 timeouts. Mechanical, low-risk.
3. **Codex-alignment sweep, one PR per concern:** §3.1 `when_to_use` fold-in; §3.3 subagent rename; §2 path-convention conversion (largest, most mechanical — do it last of the three, immediately followed by its validator rule so it can't regress).
4. **Validator batch (§7)** — lands with or right after 3, converting every convention above into a gate.
5. **Docs sweep (§6), one commit** for the cutover cluster + supersession markers + status vocabulary.
6. **Structural work (§5) as scheduled refactors:** dead-code deletion first (pure win), then the package-ification, then the `outcome.py` split.
