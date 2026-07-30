# Command Catalog

This catalog explains what each Saga family command is for before an operator invokes it.

Each command keeps its plugin namespace. Generic names such as `plan` and `work` are intentionally used as `saga:plan` and `saga:work`.

## Saga Commands

| Command | Purpose | Reads | Writes | Mutates | Next route |
|---|---|---|---|---|---|
| `saga:office-hours` | Find the right frame for an early ask. | prompt, light repo context | optional framing notes | none | `saga:ideate`, `saga:brainstorm`, `saga:plan`, or `saga:strategy` |
| `saga:ideate` | Generate and rank grounded ideas. | repo scan, journal, optional web/context | `docs/ideation/` | none | `saga:brainstorm` or `saga:plan` |
| `saga:product-review` | De-risk ideation survivors before committing. | ideation artifact, current grounding | `docs/product-reviews/` | none | `saga:plan`, `saga:brainstorm`, or parked |
| `saga:brainstorm` | Turn one idea into requirements. | ideation survivor or topic | `docs/brainstorms/` | none | `saga:plan`, `saga:spec`, `saga:handoff`, or `saga:doc-review` |
| `saga:spec` | Sharpen a vague WHAT. | prompt, repo evidence, requirements | `docs/specs/` | none | `saga:plan`, `saga:handoff`, or `saga:doc-review` |
| `saga:implementation-spec` | Author profile-backed context-library implementation specs. | target context library, profile standard, requirements | context-library spec folders and review inputs | docs only | `saga:doc-review` or `saga:plan` |
| `saga:strategy` | Create or maintain durable direction. | repo state, strategy context | `STRATEGY.md` | docs only | `saga:ideate`, `saga:brainstorm`, or `saga:plan` |
| `saga:plan` | Decide HOW to build settled requirements. | issue, requirements, repo evidence | `docs/plans/`, `.codex/saga/` | local ignored state | `saga:doc-review` |
| `saga:doc-review` | Check implementation readiness. | plan, requirements, strategy, issue docs | `docs/reviews/` when needed | safe in-place doc fixes only | `saga:work` if no P0/P1 |
| `saga:work` | Execute a reviewed plan to PR-ready. | plan, review, saga state, repo | code/docs/tests, `docs/work-sessions/`, `.codex/saga/` | git commits and PR actions only with confirmation | `saga:code-review`, then `saga:qa` |
| `saga:outcome` | Coordinate a durable outcome DAG. | outcome spec, store, receipts, backend capability | `docs/outcomes/`, `.codex/saga/`, status cards | preview/propose only unless explicitly approved | native Saga leaf routes or `verified-workflows` |
| `saga:code-review` | Review implementation at PR boundary. | merge-base diff, plan, review context | `docs/reviews/` | none | `saga:work` for fixes or `saga:qa` |
| `saga:qa` | Gather acceptance evidence after shipped or PR-ready work. | work session, PR/merge state, app/repo evidence | QA artifact | none | `saga:handoff` or `saga:retro` |
| `saga:investigate` | Diagnose bugs and root causes off-chain. | failure evidence, repo, logs | investigation report | optional trivial fix only when gated | `saga:work`, `saga:handoff`, or `saga:brainstorm` |
| `saga:founder-review` | Challenge scope and ambition. | strategy, brainstorm, plan, scope ask | scope decision/review | none | `saga:plan` and `saga:doc-review` |
| `saga:ceo-review` | Alias-style entry to founder review. | same as `saga:founder-review` | same as `saga:founder-review` | none | `saga:founder-review` flow |
| `saga:optimize` | Run a bounded metric-improvement loop off-chain. | measurable target, repo evidence | optimization notes | docs/code only through explicit work path | `saga:work` or done |
| `saga:promote` | Promote select cross-repo learnings. | workspace engineering journals, promotion ledger | proposed context-library journal diffs | context-library writes only after explicit approval | terminal |
| `saga:handoff` | Convert durable artifacts into handoff context. | docs artifact, repo, target metadata | handoff envelope | none | `mission-control:issues` |
| `saga:retro` | Capture learnings and lifecycle improvements. | completed work, reviews, sessions | `docs/engineering-journal/` or retro report | docs only | terminal or `saga:handoff` |
| `saga:resume` | Reconstruct stale or interrupted lifecycle context. | `.codex/saga/`, docs, git, sessions | local context notes | none | relevant lifecycle command |
| `saga:loop` | Route the next lifecycle move. | input, saga state, handoff maturity | `.codex/saga/` tick | local ignored state | one routable command |

## Mission Control Commands

Mission Control owns SDLC mutation. It uses preview or dry-run behavior before write-capable actions.

| Command | Purpose | Reads | Writes or mutates |
|---|---|---|---|
| `mission-control:board` | Board views, movement, WIP, standup prep. | GitHub projects | project cards after confirmation |
| `mission-control:flow` | Field assignment, sub-issue linking, card validation, label self-heal. | GitHub GraphQL/REST | project fields, sub-issues, labels after confirmation |
| `mission-control:issues` | Prepared issue drafts and issue creation. | source docs, templates, target config | `docs/sdlc-issue-drafts/`, GitHub issues after confirmation |
| `mission-control:labels` | Label audit, deploy, sync, auto-label, field options. | repo labels, config | labels and field options after confirmation |
| `mission-control:metrics` | Cycle time, throughput, WIP age, column time. | GitHub timeline events | reports only |
| `mission-control:milestones` | Objective milestone create/list/link/progress. | GitHub milestones | milestones after confirmation |
| `mission-control:rollout` | SDLC rollout status and deployment to repos. | repo config, labels, templates | labels/templates/tracking after confirmation |

## Verified Workflows Commands

Verified Workflows owns reviewer and validator protocol.

| Command | Purpose | Reads | Writes or mutates |
|---|---|---|---|
| `verified-workflows:run` | Execute an approved native V2 workflow contract with typed results, bounded deviations, and concise gates. | approved contract, repo, runtime readback | declared assignment writes and one run record |
| `verified-workflows:review-workflow` | Validate a Workflow Contract's graph, roles, profiles, writes, checks, fallbacks, and external actions before execution. | plan and profile policy | read-only contract review |
| `verified-workflows:appsec-audit` | Audit URL and input trust boundaries. | app code and trust-boundary context | security findings |

## Deploy Commands

Deploy owns tag-promotion workflows and deployment status.

| Command | Purpose | Reads | Writes or mutates |
|---|---|---|---|
| `deploy:deploy-state` | Explain deployment state and tag-promotion policy. | deployment docs and repo context | none |
| `deploy:deploy` | Preview or push nonprod, staging, production, and rollback tags. | git refs, deployment state | tags only with `--confirm-plan` |
| `deploy:deploy-status` | Show environment status and version drift. | deployment records and tags | reports only |
| `deploy:deploy-notes` | Preview release notes for a candidate range. | git history and deployment refs | reports only |
| `deploy:deploy-hotfix` | Prepare hotfix tags and evidence. | git refs, hotfix context | tags only with confirmation |

## Dry-Run Question

Before any command, ask this compact map.

| Question | Good answer |
|---|---|
| What does it read? | Prompt, artifact path, Saga state, GitHub state, deployment refs, or repo files. |
| What does it write? | Durable docs, local ignored Saga state, evidence, or nothing. |
| What does it mutate? | Only the owning plugin's domain, and only with confirmation. |
| What route follows? | The next Saga family command or terminal state. |

Generated command facts live in [lifecycle-facts.json](generated/lifecycle-facts.json).
