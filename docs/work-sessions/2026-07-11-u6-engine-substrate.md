# U6 Engine Substrate Work Session

Date: 2026-07-11. Branch: `work/verified-workflows-modernization`. Plan:
`docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`.
Frozen Claude source window: `9470edca65b1db06d2f7562eeb2d5a9e48c34dec..38742ece89880a6b140be237edad6d3f13c97b54`.

## Completed

- Ported all 35 U6 source rows covering host-neutral outcome and board correctness, Fleet Core
  bridge receipts, external-engine registry and resolver policy, generic HTTP transport, overlays,
  conformance, model and effort propagation, and structured workflow-emitter intent.
- Kept native Codex children outside the external-engine registry. External results remain advisory
  and cannot satisfy hard gates.
- Bound bridge evidence to engine, variant, transport, model, full secret-free invocation, output,
  and receipt-emitter signatures. Numeric telemetry is finite and non-negative; oversized registry
  costs, HTTP timeouts, token estimates, and response usage fail closed without `OverflowError`.
- Bound verifier panels to a root-authored tracked subject, contained repository path, clean
  workspace, fixed seat identity, fallback depth, and quorum. Producer result prose is withheld from
  verifier prompts, generated JavaScript comment text is inert, unsafe identifiers fail before emit,
  and every panel still requires Codex root attestation.
- Hardened board replay against cross-owner mutation, forged idempotency markers, multiple markers,
  and unauthenticated comment authors.
- Added executable Node runtime tests and 66 focused degraded-path/branch tests. The unchanged
  ten-module denominator now measures 90.01386962552012% aggregate branch-aware coverage and
  92.637% statement coverage.

## Review And Remediation

The first fresh review waves found stale evidence, under-bound subject and invocation proof,
untrusted verifier-result exposure, marker forgery, comment injection, and numeric overflow paths.
Commits `82242e0`, `b7c0f46`, `a9fbaa5`, and `2a96fd5` fixed those findings. Commit `ca03377`
closed the final coverage P3; `08ab562` binds the current evidence.

Final host-issued child contexts, all with `fork_turns=none`:

| Role | Child thread | Profile readback | Verdict |
|---|---|---|---|
| architecture-reviewer | `019f510a-fe7e-7c40-90c7-2618292b735a` | `review_high`, `gpt-5.6-sol`, `high`, read-only | accept 9.30; no P0-P3 |
| devils-advocate-reviewer | `019f510b-15d9-7680-a7ff-ded0588fa1f1` | `review_high`, `gpt-5.6-sol`, `high`, read-only | accept 9.30; no P0-P3 |
| security-reviewer | `019f5110-9c4a-7ee0-8e78-b64da37fa824` | `review_high`, `gpt-5.6-sol`, `high`, read-only | accept 9.70; no P0-P3 |
| testing-reviewer | `019f511d-97b6-79f2-85ed-cf964b0f5495` | `review_high`, `gpt-5.6-sol`, `high`, read-only | accept 9.32; prior coverage P3 resolved |

The earlier failing review receipts remain in the host session log and were not treated as final
acceptance. The root verified every final child from `session_meta.agent_role`, the first
`turn_context.model` and `turn_context.effort`, and the effective sandbox policy rather than relying
on child self-report.

## Validators

| Role | Child thread | Profile readback | Result |
|---|---|---|---|
| scenario-tester | `019f511f-d1a2-79f1-b169-1e6228db3c07` | `test_medium`, `gpt-5.6-terra`, `medium`, workspace-write | 503 passed; gate `pass` |
| concurrency-tester | `019f511f-edfd-72b0-aea7-3024c645d2ea` | `test_medium`, `gpt-5.6-terra`, `medium`, workspace-write | 208 passed; gate `pass` |

Both validators made no source changes. The concurrency lane used the locked project `.venv` after
its first `uv` attempt could not initialize the host cache; the scenario lane used an isolated
`UV_CACHE_DIR`. The root independently ran the literal repository commands successfully.

## Checks

- U6 focused suite: 503 passed.
- U5 overlap suite: 540 passed.
- U6 branch measurement: 479 passed; 90.01386962552012% aggregate branch-aware coverage across the
  same ten modules.
- Changed-path Ruff: passed.
- Generated JavaScript syntax and runtime fail-closed cases: passed through Node-backed pytest cases.
- `python3 scripts/port_contract.py validate --stage unit --unit U5`: passed.
- `python3 scripts/port_contract.py validate --stage unit --unit U6`: passed.
- `python3 scripts/build_legacy_workflow_inventory.py --check`: passed.
- `python3 scripts/validate_codex_plugins.py`: passed.

The unrelated `.serena/project.yml` change remains user-owned and unstaged.

## Next Step

Execute U7 from the same frozen Claude window: import trust, economics, attestation, onboarding, and
advisory reconciliation while preserving the exact persisted v1 Claude-named enum and field values.
