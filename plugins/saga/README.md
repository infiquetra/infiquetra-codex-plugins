# saga

Codex-native Infiquetra lifecycle spine.

Saga owns lifecycle choice, local saga state, outcome orchestration, handoff envelopes, and promotion proposals. It does not own issue mutation, deployment mutation, reviewer/validator execution, or context-library writes without approval.

## Skill Groups

- Framing: `office-hours`, `ideate`, `product-review`, `brainstorm`, `spec`, `implementation-spec`, `strategy`
- Planning execution routing: `plan`, `work`, `outcome`, `loop`, `resume`, `handoff`
- Review validation: `doc-review`, `code-review`, `founder-review`, `ceo-review`, `qa`
- Learning improvement: `investigate`, `retro`, `optimize`, `promote`

Source-parity skill names are intentionally generic and expected to be used through the plugin namespace, for example `saga:plan`, `saga:work`, `saga:outcome`, and `saga:promote`.

Native Codex `/resume` continues a known saved chat. `saga:resume` reconstructs lifecycle state across
Saga ticks, issues, PRs, and committed artifacts; it uses local multi-session forensics only when
explicitly requested. After trust, Saga's SessionStart hook may emit a fixed `saga:loop resume <id>`
hint. That hint is advisory context, not workflow, identity, or completion proof.

For full Saga family lifecycle, command catalog, state guide, scenarios, and visual atlas, see `../../docs/saga/README.md`.

## State

Ignored local Saga state belongs under:

```text
.codex/saga/
```

Durable project artifacts remain in tracked docs `docs/plans/`, `docs/product-reviews/`, `docs/brainstorms/`, `docs/specs/`, `docs/reviews/`, `docs/work-sessions/`, and `docs/outcomes/`. Context-library implementation specs live under the target library's `platform-specs/` profile.

## Execution Backends

Codex Saga offers only:

- `inline`
- `manual`
- `verified-workflow`

Use `verified-workflow` for reviewer consensus, validators, broad fan-out, cross-repo work,
security/infra risk, deployment-sensitive gates, or adversarial confidence. Historical backend
values remain readable but are never emitted for new work.

## External Provider Harness

Saga retains six exact advisory routes: Claude Opus, Agy Gemini Flash and Pro, Ollama gpt-oss and
embeddings, and DeepSeek. Each route accepts `saga.harness.request.v1` and returns
`saga.harness.result.v1`. The harness performs one provider invocation in a disposable,
remote-stripped workspace, validates the Fleet receipt and output attestation, and returns
non-gating evidence.

Direct mode is read-only. Verified Workflow mode may declare writes inside the disposable clone and
produce a patch artifact; only the Git integration operator may import that patch. Saga no longer
maintains an external-action lifecycle, preference store, promotion state, retry state, or a second
gatekeeper.

## Plugin Boundaries

- `mission-control` owns issue artifacts, issue comments, labels, milestones, boards, and project movement.
- `deploy` owns deployment mutation, tag promotion, rollback, hotfixes, deployment status, and release-note previews.
- `verified-workflows` owns reviewer consensus, selected validators, subagent delegation, truthful
  inline fallback, and protected evidence state.
- `saga` emits handoff envelopes, outcome receipts, status cards, and promotion proposals. Receiving plugins must re-read and re-verify handoff payloads before mutation.

## Scripts

- `scripts/saga.py` stores and restores `.codex/saga/` state.
- `scripts/lifecycle_state.py` normalizes destination labels and recommends `inline`, `manual`, or
  `verified-workflow`.
- `scripts/outcome.py` coordinates durable outcome DAGs and routes leaves back to native Saga skills.
- `scripts/promote_scan.py` scans engineering journals for gated context-library promotion candidates.
- `scripts/status_card.py` renders shared derived-on-read status cards.
- `scripts/completeness_gate.py` validates structured delegated output and catches omissions.
- `scripts/external_action_adapters.py` runs the six thin external-provider routes.
- `scripts/handoff_envelope.py` emits structured handoff material for `mission-control`.
- `scripts/product_review.py` supports `product-review` revival route recommendations.
- `scripts/implementation_spec_audit.py` discovers context-library profiles and audits service implementation spec folders.
- `scripts/detect_deploy_strategy.py` classifies deployment workflow coverage.
- `scripts/discover_sessions.py` and `scripts/extract_session_skeleton.py` support local Codex session forensics without reading full session bodies into normal context.
