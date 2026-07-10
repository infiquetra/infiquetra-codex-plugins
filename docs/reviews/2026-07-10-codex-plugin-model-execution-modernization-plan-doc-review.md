# Doc Review: Codex Plugin Model, Execution, and Upstream Modernization Plan

Readiness summary: the plan is implementation-ready and remains `plan-only` pending explicit execution approval. Every actionable P0-P3 finding was safe-fixed in place; no finding remains open. Blocked: NO.

## Review-Result Contract

- Target: `docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`
- Reviewed revision: working tree (plan is uncommitted; repository HEAD `788902513e48ea95fd0504ac3c850c8c02e5d920`)
- Blocked status: NOT blocked
- Review type: plan readiness-skeptic plus compatibility, security, and operations passes; no formal idea/issue/spec rubric phase applies
- Linked origin: `docs/plans/2026-06-27-port-recent-claude-plugin-updates.md`
- Linked Saga: `task-port-recent-claude-plugin-updates`
- Review artifact: `docs/reviews/2026-07-10-codex-plugin-model-execution-modernization-plan-doc-review.md`
- External review panel: not requested; skipped
- Operator override: none

## Applied Fixes

| # | Priority | Finding | Applied fix |
|---:|---|---|---|
| 1 | P1 | The architecture picture made U6 feed U5 although U6 depends on U5. | Replaced the apparent cycle with the actual U1 through U8 dependency spine. |
| 2 | P1 | The superseding plan did not trace origin R1-R9 and silently dropped the repeatable-port-procedure requirement. | Added total origin traceability plus R16 and U1/U8 procedure coverage. |
| 3 | P1 | U1 treated movement of Claude `main` as a gate failure despite a deliberately frozen commit. | Made upstream movement recorded drift; only a missing/unreachable frozen commit or unreproducible classification fails. |
| 4 | P1 | The live runtime characterization had no durable, sanitized schema or test. | Added a closed capability-snapshot artifact/test and an explicit forbidden-data policy. |
| 5 | P1 | U4 required live named proof before U8 installed/trusted the plugin and made lack of named selection look release-blocking. | Added an isolated, dry-run-by-default proof harness; delegated mode is conditional and a truthful `serial-only` result can ship. |
| 6 | P1 | The receipt design omitted trust origin, effort observability, containment, permissions, retention, and normalization rules. | Bound effort through the exact installed-TOML digest, made the handler compute that digest, allowlisted prompt-free fields, and pinned contained atomic storage/pruning. |
| 7 | P1 | Outcome intent/commit wording did not define manual handoff, legacy records, deduplication, or migration. | Pinned `outcome.dispatch.v2`, launched versus handed-off acknowledgements, `legacy-unverified`, and append-only evidence reconciliation. |
| 8 | P1 | Saga continuation/identity fields, Goal binding, and the explicit-default scalar regression lacked a compatible schema plan. | Added backward-compatible v1 defaults, success-only Goal binding, and parser-derived tracking for every persisted scalar save option. |
| 9 | P1 | Proposed versions `0.9.0`/`0.76.0`/`2.15.0` contradicted the repository's preserved-lineage policy. | Pinned fleet-core `0.8.4`, Saga `0.75.17`, and Codex-line Team Execution `2.4.0`; updated the decision record. |
| 10 | P1 | Real-profile cutover had no pre-state, transaction boundary, or verified rollback. | Added R17/KTD12, isolated-first application, sanitized cutover evidence, managed-only restoration, and rollback readback. |
| 11 | P2 | Catalog parsing did not constrain subprocess behavior, sensitive/irrelevant fields, or plan/apply time-of-check drift. | Pinned argv-only execution, timeout/output ceiling, refreshed-to-bundled fallback, an allowlisted projection, one input hash, and one immutable snapshot. |
| 12 | P2 | The ordered model fallbacks had no capability rationale and could be mistaken for a cost claim. | Recorded current-family continuity and explicitly disclaimed unproved price reasoning. |
| 13 | P2 | U5's hook inventory could be read to include lifecycle/guard hooks beyond the proven surface. | Reduced Saga to one read-only SessionStart context hook; deferred PreToolUse/PostToolUse/Stop and lifecycle receipts. |
| 14 | P2 | U7 said only “keep v1 names” and left provider mutation authority vague. | Pinned `verified_by_claude`, `FELL_BACK_TO_CLAUDE`, and `fell-back-to-claude`; made recommendation/promotion read-only and onboarding digest-gated apply. |
| 15 | P2 | U8 referred to the project environment without naming the executable locked command; bare pytest had previously missed Pillow, and bare `uv run pytest` cannot import `scripts.*` under this repo's importlib mode. | Required `PYTHONPATH=. uv run pytest`; verified Pillow and the test stack are already declared in `pyproject.toml` and `uv.lock`. |
| 16 | P3 | U6/U7 named nonexistent or noncanonical test paths. | Replaced them with the frozen source paths `test_engine_registry_conformance.py`, `test_engine_registry_lint.py`, `test_team_execution_consensus.py`, and `test_team_execution_consensus_advisory.py`. |
| 17 | P3 | The next step still instructed the operator to run the review that produced this artifact. | Changed the route to explicit approval followed by `saga:work` U1 in serial mode. |

## Verification Evidence

- Frozen source truth remains reproducible: `9470edc..38742ece` contains 156 focused files split 12 fleet-core, 63 Saga, 10 Team Execution, and 71 tests. The Claude checkout's current `HEAD`, local `main`, and local `origin/main` are `321f74c65f80d4819e78f440c93d264a30862fab`; `38742ece` remains an ancestor, so this is recorded drift rather than scope expansion.
- Frozen source manifests verify fleet-core `0.8.4`, Saga `0.75.17`, and Team Execution `2.14.3`. Current Codex manifests verify the separate starting points `0.5.0`, `0.64.0`, and `2.3.0`; the plan's Team Execution `2.4.0` is explicitly the Codex adapter line.
- Frozen source code verifies the compatibility spellings `verified_by_claude`, `FELL_BACK_TO_CLAUDE`, and `fell-back-to-claude`.
- Coverage is total: plan requirements R1-R17 are each owned by at least one unit; origin requirements R1-R9 all have a disposition; KTD1-KTD12 and U1-U8 are contiguous; the dependency chain is acyclic.
- The current managed roster has 25 profiles with the planned split: 10 opus/high reviewers, 8 sonnet/medium testers, and 7 haiku/low scanners/monitors.
- Current Saga code confirms the reviewed failure boundary: outcome schema v1 derives `dispatched` from any dispatch `commit`, the default dispatcher mints a synthetic `leaf-*`, and `_explicit_save_scalars` recognizes only orchestration mode.
- The declared dev environment includes Pillow, pytest, PyYAML, requests, and urllib3 in `pyproject.toml`/`uv.lock`.
- Current official Codex sources are linked in the plan for model/effort, custom-agent, plugin-hook, Goal, and event-shape claims; U1 requires a fresh closed-schema snapshot before implementation uses them.
- `PYTHONPATH=. uv run pytest -q tests/test_saga_doc_formatting.py tests/test_team_execution_readiness.py tests/test_validate_codex_plugins.py`: 49 passed.
- `PYTHONPATH=. uv run pytest -q tests/test_team_execution_agents.py tests/test_saga_docs_package.py`: 17 passed.
- `uv run python scripts/validate_codex_plugins.py`, both generated Saga docs `--check` commands, and `git diff --check`: passed.
- `team_execution_readiness.py validate --context plan-ready`: ready; the Team Structure receipt resolves.

## Remaining Findings

None at P0, P1, P2, or P3.

## Residual Risk / Limited Evidence

- This review proves plan readiness, not that the planned runtime adapters work. U1-U8 retain targeted, full-suite, isolated-profile, fresh-session, and rollback gates.
- Named custom-agent selection is not proved by the current generic spawn contract. The plan therefore permits a `serial-only` release and prohibits delegated claims without a live receipt.
- Existing active outcomes with legacy dispatch commits may pause at `legacy-unverified` until an operator supplies launch evidence or confirms handoff; the plan chooses visible blocking over silently trusting synthetic ids.
- Codex catalogs and hook schemas may change after this review. The immutable U1 snapshot and U8 refresh/readback are the designed drift gates.
