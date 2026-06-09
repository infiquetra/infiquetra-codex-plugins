# State And Maturity

Saga state answers where a lifecycle thread is, whether the current phase is complete, and what should happen next.

Maturity is derived from that state for handoff and routing; it is not stored in Saga frontmatter.

## Stored Axes

| Axis | Values | Meaning |
|---|---|---|
| `lifecycle_phase` | `ideation`, `brainstorm`, `plan`, `review`, `work`, `qa`, `retro` | Where the thread sits in the lifecycle. |
| `phase_status` | `pending`, `in_progress`, `complete` | Whether the current numeric phase is finished. |
| `status` | `active`, `blocked`, `paused`, `handed-off`, `done`, `abandoned` | The whole thread's disposition. |

Do not mix `status` and `phase_status`. `status=active` with `phase_status=complete` means the current phase is done but the thread still has lifecycle work ahead.

## Derived Maturity

| `lifecycle_phase` | Derived maturity |
|---|---|
| `ideation` | `idea-ready` |
| `brainstorm` | `requirements-ready` |
| `plan` | `plan-ready` |
| `review` | `plan-ready` |
| `work` | `resume-ready` |
| `qa` | `resume-ready` |
| `retro` | `resume-ready` |

`deferred-context` appears in handoff issue context when work is intentionally parked or lacks enough lifecycle evidence for direct planning or execution.

## Readiness Ladder

| Maturity | Means | Normal consumer |
|---|---|---|
| `idea-ready` | A worthwhile direction exists, but requirements may still need shaping. | `saga:brainstorm` or `saga:plan` depending on clarity |
| `requirements-ready` | WHAT is settled enough to plan. | `saga:plan` |
| `plan-ready` | HOW is settled and reviewed enough to execute. | `saga:work` |
| `resume-ready` | Execution, QA, or retro context can be resumed. | `saga:work`, `saga:code-review`, `saga:qa`, or `saga:retro` |
| `deferred-context` | The artifact carries useful context but needs recipient judgment before direct action. | `saga:handoff` or `mission-control:issues` |

## Owner Precedence

Saga caches tiny pieces of external state so work can be resumed offline, but those cached values are never authority.

| Domain | Authority | Saga may cache |
|---|---|---|
| GitHub issue, labels, comments, boards | `mission-control` and live GitHub | `issue_ref` and source pointers |
| Deployment status and tags | `deploy` and live release state | destination intent and PR refs |
| Branch, commit, working tree | git | branch and SHA for display |
| Decisions and learnings | `docs/engineering-journal/` | journal refs and mirrored KTDs |

If cached `.codex/saga/` state disagrees with an owner, the owner wins.

## Example Tick Interpretation

| Field | Example | Operator reading |
|---|---|---|
| `lifecycle_phase` | `plan` | The thread has a plan but has not moved into execution. |
| `phase_status` | `complete` | The plan phase is finished. |
| `status` | `active` | The thread still has work ahead. |
| `destination` | `pr` | The expected route is through PR-ready work. |
| `plan_path` | `docs/plans/example-plan.md` | `/work` should consume that plan after doc review. |
| `next_step` | `/doc-review docs/plans/example-plan.md` | The next safe lifecycle move. |

For the canonical state contract, read [Saga spec](../../plugins/saga/references/saga-spec.md).

