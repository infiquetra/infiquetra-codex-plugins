# saga

Codex-native Infiquetra lifecycle spine.

Saga owns lifecycle choice, local saga state, and handoff envelopes. It does not
own issue mutation, deployment mutation, or reviewer/validator execution.

## Skill Groups

- Framing: `office-hours`, `ideate`, `brainstorm`, `spec`, `strategy`
- Planning and execution routing: `plan`, `work`, `loop`, `resume`, `handoff`
- Review and validation: `doc-review`, `code-review`, `founder-review`,
  `ceo-review`, `qa`
- Learning and improvement: `investigate`, `retro`, `optimize`

The source-parity skill names are intentionally generic and are expected to be
used through the plugin namespace, for example `saga:plan`, `saga:work`, and
`saga:brainstorm`.

## State

Ignored local Saga state belongs under:

```text
.codex/saga/
```

Durable project artifacts remain in tracked docs such as `docs/plans/`,
`docs/brainstorms/`, `docs/specs/`, `docs/reviews/`, and
`docs/work-sessions/`.

## Execution Backends

Codex Saga offers only:

- `inline`
- `team-execution`

Use `team-execution` for reviewer consensus, validators, broad fan-out,
cross-repo work, security/infra risk, or deployment-sensitive gates.

## Plugin Boundaries

- `mission-control` owns issue artifacts, issue comments, labels, milestones,
  boards, and project movement.
- `deploy` owns deployment mutation, tag promotion, rollback, hotfixes,
  deployment status, and release-note previews.
- `team-execution` owns reviewer consensus, selected validators, subagent
  delegation, serial fallback, and evidence state.
- `saga` emits handoff envelopes and recommendations. Receiving plugins must
  re-read and re-verify handoff payloads before mutation.

## Scripts

- `scripts/saga.py` stores and restores `.codex/saga/` state.
- `scripts/lifecycle_state.py` normalizes destination labels and recommends
  `inline` or `team-execution`.
- `scripts/handoff_envelope.py` emits structured handoff material for
  `mission-control`.
- `scripts/detect_deploy_strategy.py` classifies deployment workflow coverage.
- `scripts/discover_sessions.py` and `scripts/extract_session_skeleton.py`
  support local Codex session forensics without reading full session bodies into
  normal context.
