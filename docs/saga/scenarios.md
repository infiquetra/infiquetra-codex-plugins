# Scenario Playbooks

These examples show how Saga family workflows feel from the operator seat.

Each scenario names the prompt shape, route, artifact trail, maturity transition, owner boundary, and outcome.

## Vague idea to plan

| Step | Command | Artifact or state |
|---|---|---|
| Start | "I have an idea but I don't know the frame." | no saga required |
| Frame | `saga:office-hours` | settled frame |
| Generate options | `saga:ideate` | `docs/ideation/...` with `idea-ready` survivor |
| Deepen one idea | `saga:brainstorm` | `docs/brainstorms/...` with `requirements-ready` |
| Plan | `saga:plan` | `docs/plans/...`, Saga phase `plan` |
| Review | `saga:doc-review` | `docs/reviews/...` when findings or gate evidence warrant |

Outcome: the work becomes plan-ready and safe to execute.

## Plan-ready issue to PR

| Step | Command | Artifact or state |
|---|---|---|
| Start | issue has `plan-ready` handoff maturity | `mission-control` issue context |
| Execute | `saga:work <issue>` | work-thread Saga moves to `work` |
| Record | `saga:work` | `docs/work-sessions/...` |
| Review | `saga:code-review` | code review artifact or envelope |
| PR loop | `saga:work` | PR actions only with confirmation |

Outcome: the reviewed plan becomes PR-ready without Saga mutating issue fields directly.

## Experiment-ready prototype to plan

| Step | Command | Artifact or state |
|---|---|---|
| Start | ideation survivor has an unproven product assumption | `docs/ideation/...` |
| De-risk | `saga:product-review` | `docs/product-reviews/...` with `experiment-ready` route |
| Plan experiment | `saga:plan` | experiment-sized plan, metric, threshold, and stop condition |
| Review | `saga:doc-review` | confirms the spike can run without inventing product decisions |
| Execute | `saga:work` | scoped prototype or measurement work |

Outcome: the team learns from a small experiment before committing to full requirements or feature work.

## PR-ready work through review and QA

| Step | Command | Artifact or state |
|---|---|---|
| Work boundary | `saga:work` reaches PR-ready | reviewed SHA is captured |
| Code review | `saga:code-review` | no unresolved P0/P1 before PR-ready |
| Merge or pause | `saga:work` | confirmed PR action |
| Acceptance gate | `saga:qa` | QA artifact and ship verdict |
| Closeout | `saga:handoff` or `saga:retro` | follow-up issue or learning |

Outcome: implementation moves through review and acceptance evidence before terminal routing.

## Handoff issue creation

| Step | Command | Artifact or state |
|---|---|---|
| Source | `docs/brainstorms/...`, `docs/plans/...`, or `docs/work-sessions/...` | maturity inferred from artifact |
| Envelope | `saga:handoff` | structured handoff context |
| Draft | `mission-control:issues` | `docs/sdlc-issue-drafts/...` and sidecar |
| Mutation | `mission-control:issues` | GitHub issue only after preview and confirmation |

Outcome: the receiving issue is self-contained enough for the next operator without assuming Saga is installed.

## Security-sensitive review escalation

| Step | Command | Artifact or state |
|---|---|---|
| Plan or work detects risk | `saga:plan`, `saga:doc-review`, or `saga:work` | security, infra, API, or deployment-sensitive signal |
| Escalate | `team-execution:team-execution` | reviewer and validator evidence |
| Specialized audit | `team-execution:appsec-audit` when URL/input boundaries matter | appsec findings |
| Resume | `saga:work` | implements or fixes only after gate decisions |

Outcome: Team Execution collects independent evidence, while Saga and the operator retain mutation decisions.

## Deployment after QA

| Step | Command | Artifact or state |
|---|---|---|
| QA passes | `saga:qa` | ship verdict and evidence |
| Inspect | `deploy:deploy-status` | environment and version drift |
| Preview | `deploy:deploy-notes` | candidate release notes |
| Promote | `deploy:deploy` | tag push only with explicit confirmation |

Outcome: Saga records deployment intent, but Deploy owns tag promotion and guardrails.

## Hotfix flow

| Step | Command | Artifact or state |
|---|---|---|
| Diagnose | `saga:investigate` | root-cause evidence |
| Fix | `saga:work` | focused work session and review |
| Validate | `saga:code-review` and `saga:qa` | review and acceptance evidence |
| Promote | `deploy:deploy-hotfix` | hotfix tag and evidence after confirmation |

Outcome: urgent work still preserves diagnosis, review, QA, and deployment ownership.

## Stalled Saga recovery

| Step | Command | Artifact or state |
|---|---|---|
| Inspect | `python3 plugins/saga/scripts/saga.py scan` | candidate local threads |
| Restore | `python3 plugins/saga/scripts/saga.py restore --saga-id <id>` | latest tick |
| Reconcile | check git, GitHub, deployment state, and journal | owners beat cache |
| Resume | `saga:work`, `saga:code-review`, `saga:qa`, or `saga:retro` | route from verified state |

Outcome: the operator resumes from verified owner state rather than blindly trusting stale cache.
