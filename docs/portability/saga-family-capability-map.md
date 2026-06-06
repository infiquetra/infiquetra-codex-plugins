# Saga-Family Capability Map

Verified: 2026-06-06

This map records the U1 disposition for every active `sdlc-manager` and
`blueprint-reviewer` skill before the old plugin roots are deleted. It is a
gating artifact for the Saga-family replacement.

Disposition values:

- `mapped`: replacement owner and operator-facing skill are known.
- `mapped-with-boundary`: replacement requires more than one owner because
  review, mutation, or orchestration authority is split.
- `lineage-only`: old material can appear only as source or migration history.
- `retired`: behavior is intentionally removed.
- `accepted-break`: behavior will break and the reason is documented.

No active old skill is currently marked `retired` or `accepted-break`.

## Active Skill Mapping

| Old plugin | Old skill | Current capability | New owner | Replacement skill or prompt | Disposition |
|---|---|---|---|---|---|
| `sdlc-manager` | `sdlc-board` | View board state, move cards, add issues to projects, archive deployed items, WIP analysis, standup prep. | `mission-control` | `mission-control:board` | `mapped` |
| `sdlc-manager` | `sdlc-flow` | Operator-facing GitHub GraphQL and REST helpers for fields, sub-issues, card validation, labels, and project mapping discovery. | `mission-control` | `mission-control:flow` | `mapped` |
| `sdlc-manager` | `sdlc-issues` | Prepared issues, issue type selection, template-guided issue creation, labels, project assignment, milestone linking. | `mission-control` | `mission-control:issues` | `mapped` |
| `sdlc-manager` | `sdlc-labels` | Label application, label audit, label deployment, initiative/objective field sync, field option creation. | `mission-control` | `mission-control:labels` | `mapped` |
| `sdlc-manager` | `sdlc-metrics` | Cycle time, throughput, WIP age, per-column time, SLA and flow health metrics. | `mission-control` | `mission-control:metrics` | `mapped` |
| `sdlc-manager` | `sdlc-milestones` | GitHub milestone lifecycle for objectives, progress, risk, and cross-repo coordination. | `mission-control` | `mission-control:milestones` | `mapped` |
| `sdlc-manager` | `sdlc-rollout` | SDLC rollout status, repo gap analysis, label and template deployment, rollout tracking. | `mission-control` | `mission-control:rollout` | `mapped` |
| `blueprint-reviewer` | `blueprint-review` | Idea-phase rubric review for blueprint sections and ADRs. | `saga` plus `team-execution` when independent consensus is requested | `saga:doc-review` for idea-phase rubrics; `team-execution:team-execution` for reviewer protocol escalation | `mapped-with-boundary` |
| `blueprint-reviewer` | `spec-review` | Spec-phase rubric review with section-embedded review log. | `saga` plus `team-execution` when independent consensus is requested | `saga:spec` for spec-phase rubric flow; `saga:doc-review` routes specs to `saga:spec`; `team-execution:team-execution` for reviewer protocol escalation | `mapped-with-boundary` |
| `blueprint-reviewer` | `issue-review` | Issue-phase rubric review and optional GitHub issue comment. | `saga`, `mission-control`, and `team-execution` | `saga:doc-review` for issue-phase rubrics; `mission-control:issues` for GitHub issue mutation or comments; `team-execution:team-execution` for reviewer protocol escalation | `mapped-with-boundary` |

## Old Slash-Command And Alias Mapping

Old slash-command language appears in source docs and in external migration
inputs. These command names do not remain active in the Codex cutover.

| Old invocation | Replacement |
|---|---|
| `/sdlc-board` | Use `mission-control:board` or ask Codex to run the mission-control board workflow. |
| `/create-issue` | Use `mission-control:issues` prepared issue flow. |
| `/sdlc-create` | Use `mission-control:issues` prepared issue flow. |
| `/sdlc-triage` | Use `mission-control:issues` for issue triage plus `mission-control:flow` for project-field or card mutation helpers. |
| `/sdlc-metrics` | Use `mission-control:metrics`. |
| `/blueprint-review` | Use `saga:doc-review` for blueprint or ADR review. |
| `/spec-review` | Use `saga:spec`, or `saga:doc-review` when routing from a mixed document-review request. |
| `/issue-review` | Use `saga:doc-review` for issue review and `mission-control:issues` for any GitHub comment mutation. |

## Ownership Boundaries

- Saga owns lifecycle choice, document classification, review routing, and
  handoff envelopes.
- Mission-control owns all SDLC mutation, including GitHub issues, project
  cards, labels, milestones, comments, and rollout mutation.
- Deploy owns tag promotion, rollback, hotfix, release-note preview, deployment
  status, and deployment evidence.
- Team-execution owns reviewer and validator protocol orchestration. It may use
  Codex subagents when available and must provide serial fallback when not.

## Deletion Gate

U8 may delete `plugins/sdlc-manager/` and `plugins/blueprint-reviewer/` only
after validation proves every row above has either an active replacement,
documented retirement, or accepted break. This file currently maps every active
old skill to a replacement owner.
