# Associated Plugins

The Saga family works because ownership is explicit.

Saga carries lifecycle context and recommendations. It does not privately mutate another plugin's domain.

## Ownership Matrix

| Plugin | Owns | Does not own |
|---|---|---|
| `saga` | lifecycle choice, `.codex/saga/` state, routing, durable lifecycle docs, handoff envelopes | GitHub issue mutation, deployment tags, reviewer execution |
| `mission-control` | prepared issues, issue comments, labels, milestones, boards, project fields, rollout, flow metrics | Saga lifecycle phase authority or deployment tags |
| `verified-workflows` | root-owned DAGs, reviewer consensus, selected validators, protected evidence | final mutation approval, scope decisions, deployment ownership |
| `deploy` | tag promotion, rollback, hotfix, deployment status, release-note previews | readiness review, issue lifecycle, code implementation |

## Boundary Rules

| Rule | Why it matters |
|---|---|
| Saga emits context, not authority | A handoff envelope is useful input, but the receiving plugin must verify before mutation. |
| GitHub mutation belongs to `mission-control` | Issue bodies, labels, comments, project fields, and board moves need Mission Control's dry-run and auth rules. |
| Deployment mutation belongs to `deploy` | Tag promotion and rollback require deployment-specific guardrails and confirmation. |
| Reviewer protocol belongs to `verified-workflows` | Saga can recommend escalation, but Verified Workflows owns selected reviewers, validators, and evidence. |
| Git remains authoritative for branch and commit state | Saga caches branch/SHA for offline display only. |

## Common Hand-Offs

| From | To | Trigger |
|---|---|---|
| `saga:handoff` | `mission-control:issues` | A durable artifact should become a prepared SDLC issue draft. |
| `saga:work` | `saga:code-review` | Work reaches the PR boundary and needs code-quality review. |
| `saga:work` or `saga:code-review` | `saga:qa` | Merged or PR-ready work needs acceptance evidence. |
| `saga:qa` | `deploy:deploy` | QA passes and the next operator move is tag promotion. |
| `saga:plan`, `saga:work`, or `saga:doc-review` | `verified-workflows:run` | The work needs independent consensus, selected validators, or broad fan-out. |

See [Command Catalog](command-catalog.md) for per-command dry-run maps.
