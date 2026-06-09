# Saga Family Field Guide

Saga is the lifecycle spine for Infiquetra work in Codex.

It helps an operator move from a vague ask to a durable artifact, a reviewed plan, PR-ready work, QA evidence, handoff, and deployment routing while keeping each plugin's ownership boundary intact.

## Start Here

Use this guide when you need to understand the Saga family, choose the next command, inspect Saga state, or recover a stalled lifecycle thread.

| Need | Go to |
|---|---|
| See the full journey | [Lifecycle Atlas](lifecycle-atlas.md) |
| Pick the next command | [Command Catalog](command-catalog.md) |
| Understand state and maturity | [State And Maturity](state-and-maturity.md) |
| See plugin ownership boundaries | [Associated Plugins](associated-plugins.md) |
| Learn by examples | [Scenario Playbooks](scenarios.md) |
| Avoid markdown artifact failures | [Markdown Contracts](markdown-contracts.md) |
| Recover stuck work | [Recovery Playbooks](recovery-playbooks.md) |
| Keep a compact reference open | [Quick Reference](quick-reference.md) |

## The Saga Family

Saga is not a one-plugin monolith. It is the lifecycle wrapper around four cooperating Codex plugins.

| Plugin | Owns | Typical moment |
|---|---|---|
| `saga` | lifecycle choice, local Saga state, durable lifecycle docs, handoff envelopes | choose and record the next lifecycle move |
| `mission-control` | issues, comments, labels, milestones, project boards, project fields, rollout, metrics | create or mutate SDLC issue/project state |
| `team-execution` | reviewer consensus, selected validators, delegated or serial evidence | add independent review and validation protocol |
| `deploy` | tag promotion, rollback, hotfixes, deployment status, release-note previews | promote or inspect release state |

The short rule: Saga routes and records context; receiving plugins re-read, re-verify, and mutate only their own domains.

## Lifecycle In One View

The normal linear spine is:

```text
office-hours / ideate
-> brainstorm or spec
-> plan
-> doc-review
-> work
-> code-review
-> qa
-> handoff or retro
-> deploy when deployment mutation is needed
```

The polished visual version lives in [Lifecycle Atlas](lifecycle-atlas.md).

## Durable Artifacts

Saga writes and consumes durable repo artifacts rather than relying on chat memory.

| Artifact family | Typical owner command | Maturity or role |
|---|---|---|
| `docs/ideation/` | `saga:ideate` | `idea-ready` |
| `docs/brainstorms/` | `saga:brainstorm` | `requirements-ready` |
| `docs/specs/` | `saga:spec` | `requirements-ready` off-chain |
| `docs/plans/` | `saga:plan` | `plan-ready` after review |
| `docs/reviews/` | `saga:doc-review`, `saga:code-review` | readiness and code review evidence |
| `docs/work-sessions/` | `saga:work` | `resume-ready` execution evidence |

Ignored local Saga state belongs under `.codex/saga/`. That cache helps resume work, but external owners remain authoritative.

## Current Source Material

This guide is built from the repo's active contracts and generated facts.

| Source | Use |
|---|---|
| [Saga spec](../../plugins/saga/references/saga-spec.md) | state axes, tick format, maturity derivation, owner precedence |
| [Dispatch table](../../plugins/saga/skills/loop/references/dispatch-table.md) | lifecycle routing and hard/advisory gates |
| [Formatting style](../../plugins/saga/references/formatting-style.md) | generated-document readability contract |
| [Capability map](../portability/saga-family-capability-map.md) | migration and ownership boundaries |
| [Generated facts](generated/lifecycle-facts.json) | deterministic command, plugin, state, and visual facts |

