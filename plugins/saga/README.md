# saga

Codex-native Infiquetra lifecycle spine.

Saga owns lifecycle choice, local saga state, outcome orchestration, handoff envelopes, and promotion proposals. It does not own issue mutation, deployment mutation, reviewer/validator execution, or context-library writes without approval.

## Skill Groups

- Framing: `office-hours`, `ideate`, `product-review`, `brainstorm`, `spec`, `implementation-spec`, `strategy`
- Planning execution routing: `plan`, `work`, `outcome`, `loop`, `resume`, `handoff`
- Review validation: `doc-review`, `code-review`, `founder-review`, `ceo-review`, `qa`
- Learning improvement: `investigate`, `retro`, `optimize`, `promote`

Source-parity skill names are intentionally generic and expected to be used through the plugin namespace, for example `saga:plan`, `saga:work`, `saga:outcome`, and `saga:promote`.

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
- `team-execution`

Use `team-execution` for reviewer consensus, validators, broad fan-out, cross-repo work, security/infra risk, deployment-sensitive gates, or adversarial confidence. Source Workflow, fork, goal, and hook backends are inactive unless a Codex capability proof and tests land.

## Plugin Boundaries

- `mission-control` owns issue artifacts, issue comments, labels, milestones, boards, and project movement.
- `deploy` owns deployment mutation, tag promotion, rollback, hotfixes, deployment status, and release-note previews.
- `team-execution` owns reviewer consensus, selected validators, subagent delegation, serial fallback, and evidence state.
- `saga` emits handoff envelopes, outcome receipts, status cards, and promotion proposals. Receiving plugins must re-read and re-verify handoff payloads before mutation.

## Scripts

- `scripts/saga.py` stores and restores `.codex/saga/` state.
- `scripts/lifecycle_state.py` normalizes destination labels and recommends `inline`, `manual`, or `team-execution`.
- `scripts/outcome.py` coordinates durable outcome DAGs and routes leaves back to native Saga skills.
- `scripts/promote_scan.py` scans engineering journals for gated context-library promotion candidates.
- `scripts/status_card.py` renders shared derived-on-read status cards.
- `scripts/completeness_gate.py` validates structured delegated output and catches omissions.
- `scripts/handoff_envelope.py` emits structured handoff material for `mission-control`.
- `scripts/product_review.py` supports `product-review` revival route recommendations.
- `scripts/implementation_spec_audit.py` discovers context-library profiles and audits service implementation spec folders.
- `scripts/detect_deploy_strategy.py` classifies deployment workflow coverage.
- `scripts/discover_sessions.py` and `scripts/extract_session_skeleton.py` support local Codex session forensics without reading full session bodies into normal context.
