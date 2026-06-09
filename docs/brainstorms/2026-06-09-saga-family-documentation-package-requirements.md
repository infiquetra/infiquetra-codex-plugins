---
date: 2026-06-09
topic: saga-family-documentation-package
maturity: requirements-ready
---

# Saga Family Documentation Package Requirements

## Summary

Build a comprehensive, presentation-quality Saga family documentation package that helps a new operator understand what Saga is, which associated plugin owns each job, how the lifecycle moves, what every command is for, how Saga state and handoff maturity work, and what safe recovery looks like when a lifecycle thread stalls.

The package should be user-facing and operational. It should avoid becoming an implementation architecture guide.

## Problem Frame

The current repository has accurate source material, but it is spread across plugin READMEs, skill files, portability docs, dispatch tables, validation docs, and Saga state contracts. A user can eventually reconstruct the model, but only by reading too much source.

Saga is also not a standalone experience. The practical operator surface is the Saga family: `saga` routes lifecycle work and records state, `mission-control` owns SDLC mutation, `team-execution` owns reviewer and validator orchestration, and `deploy` owns tag-promotion deployment work.

The documentation needs to make that family legible without flattening the ownership boundaries. It also needs better visual communication than a default Mermaid diagram can provide.

## Key Decisions

The documentation package is a product surface for operators, not a code architecture reference.

| Decision | Requirement impact |
|---|---|
| Treat this as Saga family documentation | Cover `saga`, `mission-control`, `team-execution`, and `deploy` together, with Saga as the lifecycle spine. |
| Make `docs/saga/` the canonical guide | Put the comprehensive user-facing manual under one durable docs tree, then cross-link from root and plugin READMEs. |
| Use generated truth plus polished rendering | Generate lifecycle and command facts from repo contracts where practical, then render user-facing visuals as polished SVG/PNG/PDF assets. |
| Keep visuals operator-oriented | Show journeys, commands, artifacts, maturity, gates, and owners, not module-level implementation structure. |
| Make safety first-class | Include formatting failure examples, dry-run command diagrams, and recovery playbooks so operators can recognize and repair stuck or malformed states. |
| Keep runtime behavior unchanged | This package documents and guards the existing Saga family; it must not alter command semantics, backends, mutation ownership, or lifecycle routing. |

## Actors

The docs must serve both first-time readers and maintainers who need the contracts to stay accurate.

| ID | Actor | Need |
|---|---|---|
| A1. New Codex operator | Understand what Saga is, which command to invoke, and what happens next. |
| A2. Saga lifecycle operator | Follow idea, requirements, plan, work, review, QA, handoff, and retro flows without reading every skill file. |
| A3. Plugin maintainer | Update docs and visuals without letting them drift from skill metadata, state contracts, or routing tables. |
| A4. SDLC operator | Know when Saga hands work to `mission-control` and what issue/project mutation boundary applies. |
| A5. Release operator | Know when lifecycle work ends and `deploy` becomes the correct owner. |
| A6. Reviewer or validator | Know when `team-execution` is appropriate and how it relates to Saga review gates. |
| A7. Future resumer | Inspect Saga state and recover a stalled thread safely. |

## Requirements

**Information Architecture**

- R1. The package must add a `docs/saga/` documentation tree that is the canonical user-facing entrypoint for Saga family understanding.
- R2. The root `README.md` must point users to `docs/saga/` as the place to understand the Saga family lifecycle.
- R3. `plugins/saga/README.md`, `plugins/mission-control/README.md`, `plugins/team-execution/README.md`, and `plugins/deploy/README.md` must link back to the Saga family guide where their responsibilities participate in the lifecycle.
- R4. The guide must use repo-relative links and avoid installed-cache paths as maintained source.
- R5. The guide must separate operator documentation from migration provenance, validation evidence, and implementation internals.

**Lifecycle Atlas And Visual System**

- R6. The package must include a presentation-quality Lifecycle Atlas that shows the end-to-end Saga journey from unframed ask through ideation, requirements, planning, readiness review, work, code review, QA, handoff, retro, and deployment handoff.
- R7. The Lifecycle Atlas must show commands, durable artifacts, Saga state axes, derived maturity, hard or advisory gates, and owner plugins in one coherent visual.
- R8. The primary visual assets must be polished SVG/PNG/PDF outputs, not default Mermaid exports.
- R9. Mermaid may be used only as a supplemental source or intermediate representation when it improves maintainability.
- R10. A visual asset system must define consistent phase badges, maturity chips, owner lanes, gate markers, artifact icons, and command styling.

**Generated Truth And Drift Guardrails**

- R11. The lifecycle graph facts should be generated from existing repo contracts where practical, including `plugins/saga/references/saga-spec.md`, `plugins/saga/skills/loop/references/dispatch-table.md`, skill frontmatter, and validation fixtures.
- R12. Generated graph or catalog data must be testable so documentation fails fast when command inventory, versions, routing, or lifecycle maturity contracts drift.
- R13. The generated layer must not replace human-facing prose; it supplies canonical facts that the guide and visual assets consume.
- R14. Documentation guardrails must avoid enforcing generated-document soft-wrap rules on authored template source.

**Command Catalog**

- R15. The package must include a command catalog for every routable Saga lifecycle command and every associated plugin skill that participates in the Saga family.
- R16. Each command entry must explain purpose, use cases, avoid cases, inputs, outputs, consumed artifacts, emitted artifacts, Saga state impact, handoff maturity impact, owner plugin, mutation boundary, and likely next route.
- R17. Each command entry must include a dry-run style diagram or table showing what the command reads, writes, mutates, and routes before an operator invokes it.
- R18. The catalog must distinguish shipped, advisory, off-chain, hard-gated, and stub behaviors where those distinctions affect operator choice.
- R19. The catalog must preserve namespace clarity, such as `saga:plan`, `mission-control:issues`, `team-execution:team-execution`, and `deploy:deploy`.

**State And Maturity Reference**

- R20. The package must include a dedicated state and maturity reference explaining `lifecycle_phase`, `phase_status`, `status`, and derived `maturity`.
- R21. The reference must make clear that maturity is derived for handoff and is not stored in Saga frontmatter.
- R22. The reference must include a readiness ladder covering `idea-ready`, `requirements-ready`, `plan-ready`, `resume-ready`, and `deferred-context`.
- R23. The reference must show concrete examples of how a user should interpret a Saga tick, a durable artifact path, and a handoff issue's maturity/source context.
- R24. The reference must state which external owner wins when Saga cached state disagrees with GitHub, git, deployment state, or engineering-journal records.

**Scenario Playbooks**

- R25. The package must include scenario playbooks that show realistic end-to-end operator journeys.
- R26. Each scenario must include the user's starting prompt, the route through commands, artifacts produced, state/maturity transitions, owner-plugin boundaries, and final outcome.
- R27. The scenario set must cover at least: vague idea to plan, plan-ready issue to PR, PR-ready work through review and QA, creating a handoff issue, security-sensitive review escalation, deployment after QA, hotfix flow, and stalled Saga recovery.
- R28. Scenario playbooks must be narrative enough for a new user to learn the lifecycle without reading skill source.

**Markdown Contract Failure Matrix**

- R29. The package must include a bad-versus-good markdown contract matrix for generated Saga artifacts.
- R30. The matrix must show collapse-prone stacked bold labels, unreadable prose walls, ambiguous tables, malformed maturity/source context, and other layout failures that can confuse humans or downstream agents.
- R31. The matrix must tie examples back to `plugins/saga/references/formatting-style.md` and `tests/test_saga_doc_formatting.py`.
- R32. The matrix must teach maintainers how to recognize failures without implying that parser-hostile markdown should be accepted.

**Recovery Playbooks**

- R33. The package must include controlled recovery playbooks for stuck lifecycle threads.
- R34. Recovery playbooks must start with inspection, validation, rerun, and owner-state reconciliation before any manual repair.
- R35. Manual state repair must be framed as a last-resort recovery action with explicit warnings against bypassing readiness, review, deployment, or issue-mutation gates.
- R36. Recovery examples must cover stale cached Saga state, malformed handoff context, missing durable artifacts, stale branch or PR pointers, and docs that moved during a repo migration.

**Associated Plugin Boundaries**

- R37. The package must include an ownership boundary guide for `saga`, `mission-control`, `team-execution`, and `deploy`.
- R38. The boundary guide must state that Saga routes, records lifecycle state, and emits handoff context; receiving plugins re-read and re-verify before mutation.
- R39. The boundary guide must clarify that `mission-control` owns GitHub issue, board, label, milestone, rollout, and project-field mutation.
- R40. The boundary guide must clarify that `team-execution` owns reviewer consensus, selected validators, delegated or serial evidence, and does not authorize mutation by itself.
- R41. The boundary guide must clarify that `deploy` owns deployment mutation, tag promotion, rollback, hotfixes, deployment status, and release-note previews.

**Quick Reference And Presentation Assets**

- R42. The package must include a one-page quick reference that gives operators the most common command choice, maturity, and ownership answers.
- R43. The visual assets must be usable in repository docs and presentations without requiring a live renderer.
- R44. The package should include enough visual source material that maintainers can update assets without redrawing from scratch.

## Key Flows

The flows should read like operator journeys, not implementation traces.

- F1. New operator learns the system.
  - **Trigger:** A user opens the repository and wants to understand the Saga plugin family.
  - **Steps:** The root README points to `docs/saga/`; the field guide explains the family; the Lifecycle Atlas gives the whole journey; the command catalog answers what to invoke next.
  - **Outcome:** The user can choose the right namespaced skill without reading source skill files.
  - **Covers:** R1, R2, R5, R6, R15, R19, R42.

- F2. Operator decides the next lifecycle command.
  - **Trigger:** A user has an idea, a requirements doc, a plan, a PR boundary, or a post-merge QA concern.
  - **Steps:** The command catalog and scenario playbooks map the input shape to the correct command, show consumed and emitted artifacts, and state the next likely route.
  - **Outcome:** The operator chooses the right Saga command and understands the downstream owner boundary.
  - **Covers:** R15, R16, R17, R18, R25, R26, R27.

- F3. Operator interprets Saga state and maturity.
  - **Trigger:** A user sees a Saga tick, a handoff issue, or a durable artifact path and needs to know what it means.
  - **Steps:** The state reference explains the stored axes, derived maturity, owner precedence, and readiness ladder.
  - **Outcome:** The user can tell whether work is idea-ready, requirements-ready, plan-ready, resume-ready, or deferred-context.
  - **Covers:** R20, R21, R22, R23, R24.

- F4. Maintainer updates a command or lifecycle route.
  - **Trigger:** A skill, dispatch table, state contract, or plugin version changes.
  - **Steps:** Generated graph/catalog facts update or fail; tests catch stale documentation; polished visual assets are refreshed from canonical data.
  - **Outcome:** The docs stay aligned with the repo instead of becoming a hand-drawn fossil.
  - **Covers:** R8, R10, R11, R12, R13, R14, R44.

- F5. Operator recovers from a stuck or malformed Saga.
  - **Trigger:** A lifecycle route stalls, cached state disagrees with the owner, or a handoff artifact is malformed.
  - **Steps:** The recovery playbook guides inspection, owner-state reconciliation, safe rerun, and last-resort repair.
  - **Outcome:** The operator can unstick the work without bypassing readiness, review, issue, or deployment gates.
  - **Covers:** R29, R30, R31, R32, R33, R34, R35, R36.

## Acceptance Examples

Examples describe the behavior the documentation should enable.

- AE1. A first-time user lands on the repo, opens `docs/saga/README.md`, and can explain the difference between `saga:plan`, `mission-control:issues`, `team-execution:team-execution`, and `deploy:deploy`.
- AE2. A maintainer changes the Saga dispatch table and a docs drift check identifies the Lifecycle Atlas or command catalog facts that must change.
- AE3. A user with a `requirements-ready` artifact can tell that `/plan` is the next normal lifecycle move and that `mission-control` is only involved if the work is handed off as an issue.
- AE4. A user at the PR boundary can see that `/code-review` is a review gate, `/qa` is a ship-readiness gate, and deployment mutation belongs to `deploy`.
- AE5. A maintainer comparing bad and good markdown examples can recognize why stacked bold labels collapse and how the formatting contract avoids that failure.
- AE6. A user with stale `.codex/saga` state can use a recovery playbook to reconcile against git or GitHub rather than trusting cached fields blindly.

## Success Criteria

The documentation succeeds when it materially reduces lifecycle ambiguity for a new operator.

| Signal | Success condition |
|---|---|
| Command clarity | A reader can pick the correct namespaced command for the common lifecycle scenarios without reading `SKILL.md` files. |
| State clarity | A reader can explain Saga's three stored axes and derived maturity from the state reference. |
| Boundary clarity | A reader can state which plugin owns issues, reviews/validators, deployments, and lifecycle state. |
| Visual quality | The Lifecycle Atlas and quick-reference visuals are readable in GitHub and usable in a presentation. |
| Drift resistance | Tests or generation scripts fail when key command, route, version, or maturity facts drift. |
| Safety | Recovery docs help users inspect and repair state without normalizing gate bypasses. |

## Scope Boundaries

The first implementation should build the comprehensive docs package and the maintainable visual foundation.

| In scope for v1 | Deferred for later | Out of scope |
|---|---|---|
| `docs/saga/README.md` field guide | Interactive sandbox or dummy execution CLI | Runtime behavior changes to Saga commands |
| Lifecycle Atlas page and visual assets | Full documentation website | New command aliases or renamed skills |
| Command catalog with dry-run diagrams | Video walkthroughs | Claude-only `.claude`, `commands`, or `agents` surfaces |
| State and maturity reference | Fully automated design-system renderer | Architecture-first module diagrams |
| Associated plugin ownership guide | Exported slide deck | Deployment or issue mutation behavior changes |
| Scenario playbooks | Generated docs from every `SKILL.md` section | Casual manual bypass instructions |
| Markdown contract failure matrix | Rich interactive graph exploration | Treating installed cache copies as source |
| Recovery playbooks | PDF polish beyond a one-page quick reference | Replacing validation/cutover docs |
| Docs drift tests or generated fact checks | Broader plugin docs unrelated to Saga family | Reflowing authored template source for soft-wrap |

## Dependencies / Assumptions

Planning can choose exact file names and generation mechanics, but the brainstorm depends on the current Saga family contracts.

| Dependency or assumption | Impact |
|---|---|
| `plugins/saga/references/saga-spec.md` remains the state contract | State and maturity docs should derive their vocabulary from it. |
| `plugins/saga/skills/loop/references/dispatch-table.md` remains the routing contract | Lifecycle Atlas and command catalog route facts should align with it. |
| `plugins/saga/references/formatting-style.md` remains the generated-document readability contract | Markdown failure examples should cite and reinforce it. |
| Existing plugin READMEs describe active ownership boundaries | The Saga family guide should cross-link and clarify, not duplicate every operational detail. |
| The package is docs/template/test work | It should not modify runtime command behavior or mutation ownership. |
| The current thread may still show pre-reload skill metadata | Repo and installed-plugin verification should be used for current version facts. |

## Outstanding Questions

No open question blocks `/plan`.

| Type | Question |
|---|---|
| Deferred to planning | Should the generated lifecycle graph data be committed as JSON, generated only during tests, or both? |
| Deferred to planning | Which renderer should produce the polished SVG/PNG/PDF assets from generated facts? |
| Deferred to planning | Should the first visual asset set include PDF export immediately or start with SVG/PNG plus a quick-reference markdown page? |
| Deferred to planning | Should docs drift checks validate only command/version/maturity facts, or also require every command catalog entry to exist? |

## Sources / Research

The planner should treat these as the current grounding set.

| Source | Use |
|---|---|
| `README.md` | Active plugin inventory and repo source policy. |
| `plugins/saga/README.md` | Saga skill groups, state path, backends, and plugin boundaries. |
| `plugins/saga/references/saga-spec.md` | Saga state axes, maturity derivation, owner precedence, and tick format. |
| `plugins/saga/skills/loop/references/dispatch-table.md` | Lifecycle routing, command list, hard gate, advisory/off-chain behavior. |
| `plugins/saga/references/formatting-style.md` | Markdown readability and failure-prevention contract. |
| `plugins/mission-control/README.md` | SDLC mutation ownership and prepared issue behavior. |
| `plugins/team-execution/README.md` | Reviewer/validator protocol ownership and delegated/serial modes. |
| `plugins/deploy/README.md` | Tag-promotion deployment ownership and guardrails. |
| `docs/portability/saga-family-capability-map.md` | Old-to-new ownership mapping and active replacement boundaries. |
| `docs/brainstorms/2026-06-06-codex-saga-family-replacement-requirements.md` | Prior Saga family replacement requirements and cutover framing. |
