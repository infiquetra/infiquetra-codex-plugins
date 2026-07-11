# Work Session: U4F Verified Workflows Runtime Identity

Date: 2026-07-11. Branch: `work/verified-workflows-modernization`. Plan:
`docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`. Saga:
`task-port-recent-claude-plugin-updates`. Effective orchestration: `inline`.

## Outcome

U4F corrected the profile-definition boundary but did not prove named-profile selection.

- Preserved the five durable kebab-case execution classes and mapped them to Codex-safe runtime
  agent names: `review_high`, `review_max`, `test_medium`, `scan_low`, and `monitor_low`.
- Bound both identities in generated profiles, Workflow Structure rows, dispatch intents, launch
  records, hook matchers, normalized receipts, runtime facts, and validation.
- Added exact project-scoped custom-agent discovery files under `.codex/agents/`. They are regular
  files whose bytes must match the maintained plugin profiles. U8 still owns global profile install
  and marketplace/plugin cutover.
- Updated the U5-U8 Workflow Structure to 18 columns and refreshed all five profile digests.
- Added a full-suite-safe import boundary for the Verified Workflows protocol-probe test so the
  legacy and target modules cannot collide in one pytest process.

## Fresh-Task Attestation

Codex CLI `0.144.1` loaded the trusted project after the discovery files were present. A fresh
read-only task requested `review_high` and spawned child
`019f4fb8-addd-7d82-abfc-b3d9fccbb245` from parent
`019f4fb8-8f7e-76c1-accf-6d238c41e5e1`.

The host state disproved selection:

```text
requested agent:  review_high
observed role:    null
expected model:   gpt-5.6-sol
observed model:   gpt-5.6-sol
expected effort:  high
observed effort:  xhigh (inherited from parent)
expected sandbox: read-only
observed sandbox: read-only
```

The active `spawn_agent` schema exposes `task_name`, `message`, and fork context, but no
`agent_type`, model, effort, sandbox, or selection readback. The task path `/root/review_high` was
therefore only a task name. Reloading or starting another task cannot select a profile through a
field that the active tool does not expose. The durable capability outcome remains `inline-only`.

## Checks

- Integrated U4/U4F partition: `299 passed`.
- Full locked suite: `1708 passed in 125.67 seconds`.
- Legacy/target protocol-probe collision regression: `16 passed`.
- Current repository validator: passed.
- Port-contract classification and generated classification checks: passed.
- Legacy workflow inventory check: passed.
- Profile renderer and five-profile sync dry run: passed.
- Scoped Ruff: passed.
- Plugin manifest/package validation: passed.
- Plain system-Python collection is not authoritative and stopped before tests because Pillow was
  absent; the locked `uv` environment included Pillow and passed the complete suite.

The unrelated `.serena/project.yml` modification remained outside the change set.

## Next Step

U5-U8 remain planned and paused. Resume model-pinned delegation only when a fresh root task exposes
an explicit custom-agent selector and the first child receipt confirms the requested runtime agent,
model, effort, and sandbox. Root-inline implementation remains possible only if the operator
explicitly chooses that less precise fallback.
