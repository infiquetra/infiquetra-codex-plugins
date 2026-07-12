---
date: 2026-07-11
topic: codex-external-advisory-execution-contract
maturity: requirements-ready
---

# Codex External Advisory Execution Contract Requirements

## Summary

Build one shared Codex runtime that makes approved external offload and second-opinion actions operational across `/ideate`, `/brainstorm`, `/plan`, `/work`, `/doc-review`, and `/code-review`. It must support supervised Claude CLI, contained `agy`, and validated OpenAI-compatible HTTP providers while keeping Codex root responsible for verification, live-worktree mutation, and every substantive gate.

## Problem Frame

Codex currently offers external-engine choices and persists preferences, but the selected preference has no production consumer. The Ideate run that triggered this brainstorm saved `second-opinion`, continued with native agents, and produced no external output or receipt.

The repository already contains a registry, capability resolver, HTTP bridge, receipt validation, reconciliation, and offer helpers. These pieces prove individual contracts but do not form an operator-visible stage-to-provider round trip. The current state can therefore claim configuration and validation machinery without proving that an external model actually ran.

The Claude implementation demonstrates the broader intended shape: capability routing, supervised CLI delegates, generic OpenAI-compatible HTTP providers, bounded second-opinion coordination, claim/replay control, receipts, and advisory reconciliation. The Codex version must adapt that product contract to Codex-native authority and execution boundaries rather than copy Claude host assumptions.

## Key Decisions

**One shared runtime owns external actions.** Lifecycle skills describe stage-specific actions and consume results, but provider routing, approval, dispatch, receipts, reconciliation, and status reporting have one Codex-owned behavioral contract.

**Option 1 is the full adaptation.** Runtime substrate, `/ideate` and `/brainstorm` repair, remaining lifecycle integration, provider adapters, observability, and live proof are one requirements scope. They are not independent MVPs whose missing connections can be deferred again.

**Operators approve action bundles, not opaque provider calls.** A stage may request multiple external actions. Each action independently declares intent, trigger, requiredness, provider constraints, outbound context scope and sensitivity, approved write set when applicable, evidence destination, and route preview.

**Capability routing chooses before approval; the approved egress contract freezes after approval.** The runtime may choose any eligible provider while preparing the preview. A provider, model, cost class, egress destination, material outbound context scope, sensitivity classification, or approved write-set change after approval requires a new preview and approval; substitution is never silent.

**Provider support is adapter-class based.** V1 supports supervised Claude CLI, contained `agy`, and generic OpenAI-compatible chat endpoints. Direct Anthropic API and arbitrary non-compatible JSON APIs require separately reviewed adapters.

**External engines never become gatekeepers.** They provide generated work or advisory evidence. Codex root verifies outputs, adjudicates findings, applies accepted changes, and owns completion decisions.

**Contained patches are the v1 mutation ceiling.** Claude CLI and `agy` may produce patches inside isolated workspaces and approved write sets. Generic HTTP providers return text or structured artifacts only; no external provider mutates the live worktree.

**Direct mutation is a measured capability promotion.** Reconsider it only after at least 20 contained patch runs across Claude and `agy`, zero write-set or receipt-integrity failures, at least 80% acceptance without major rewrite, and a passing rollback drill.

**Operator approval governs sensitive content, but credentials remain blocked.** The route preview provides the provider and egress context needed for an informed decision. Literal API keys, tokens, passwords, and private keys are blocked or redacted regardless of ordinary route approval.

**Provider accounts own spending limits.** The runtime previews cost class and reports estimated and observed usage, but v1 does not enforce a workflow budget or spend ceiling.

**Remember policy, not stale provider identity.** Repo-and-stage templates remember actions, requiredness, provider constraints, and operator preferences. Every run resolves and previews the concrete route again.

### Default Stage Matrix

The default bundle reflects the kind of external contribution each stage can use without transferring authority.

| stage | default external actions |
|---|---|
| `/ideate` | Offload one blind generator frame; request a second opinion on the converged survivor set |
| `/brainstorm` | Offload one alternative approach; request a second opinion on the scope synthesis before writing |
| `/plan` | Offload bounded research or extraction; request a second opinion on major architectural tradeoffs |
| `/work` | Offload eligible bounded units; offer a second opinion on stuck or disputed work |
| `/doc-review` | Request a second opinion on selected findings or through an advisory panel |
| `/code-review` | Request a second opinion on selected findings or through an advisory panel |

## Actors

- A1. **Operator.** Approves action bundles and concrete route previews, overrides provider selection when needed, controls requiredness, and decides whether Codex may use an external result.
- A2. **Codex root.** Owns stage state, provider chaperoning, verification, adjudication, live-worktree mutation, hard gates, and final completion claims.
- A3. **Lifecycle stage.** Declares the action bundle it can use, supplies bounded context, and consumes accepted artifacts or advisory findings at a named point in its workflow.
- A4. **External-action runtime.** Resolves capabilities, prepares previews, enforces approval identity, dispatches through the selected adapter, validates receipts, and renders durable action state.
- A5. **CLI provider adapter.** Supervises Claude CLI or `agy`, enforces containment and timeouts, and emits an attributable result and receipt.
- A6. **HTTP provider adapter.** Invokes a validated OpenAI-compatible endpoint using registry metadata and an environment-variable secret reference, then returns bounded output and a receipt.
- A7. **Provider registry and onboarding workflow.** Describes capabilities, models, trust, egress, cost class, invocation metadata, and authentication references without storing credentials.

## Requirements

**Lifecycle and action bundles**

- R1. One shared external-action runtime must serve all six named lifecycle stages.
- R2. A stage must be able to request multiple external actions in one bundle; offload and second opinion are not mutually exclusive at the stage level.
- R3. Each action must declare its intent, trigger, requiredness, provider constraints, outbound context scope and sensitivity classification, approved write set when applicable, evidence destination, and expected consumption point.
- R4. The default action bundles must match the Default Stage Matrix unless a repo-and-stage policy template overrides them.
- R5. Before any external provider call, the runtime must persist the proposed bundle and concrete route preview. An attended run must show it interactively; an unattended or resumed run may launch only from an already recorded run-specific approval for the unchanged bundle and egress contract.
- R6. An operator must approve the intent, resolved route preview, outbound context scope and sensitivity classification, and approved write set when applicable, with the ability to remove actions, change requiredness, narrow outbound context, or override an eligible provider.
- R7. A repo-and-stage policy template may remember preferred actions and constraints, but every run must resolve and preview the concrete route again.
- R8. Changes to provider, model, cost class, egress destination, material outbound context scope, sensitivity classification, or approved write set after approval must invalidate that approval and require a new preview.
- R9. No stage may interpret a saved preference as proof that an external action ran or as approval to launch one. Legacy preferences migrate only as unapproved desired intent.

**Provider routing and adapters**

- R10. Capability routing must support both logical capability selection and explicit provider selection.
- R11. Explicit provider requests that cannot run must become visibly unavailable; they must not silently select another provider.
- R12. Capability-selected routes may consider capability strength, provider availability, model family, context fit, cost class, trust, and egress posture before preview.
- R13. Second-opinion routing must prefer a different model family from the active Codex root.
- R14. An operator may explicitly approve a same-family second opinion after seeing a reduced-independence warning.
- R15. V1 must include a supervised Claude CLI adapter with explicit model selection, bounded input, timeout and no-output handling, terminal process cleanup, and receipt emission.
- R16. V1 must include the existing `agy` provider class with contained no-write or patch-producing execution and receipt emission.
- R17. V1 must include a generic OpenAI-compatible chat adapter driven by registry metadata rather than provider-specific branches.
- R18. The generic HTTP adapter must support provider base URL, model, key environment-variable name, capability ratings, cost policy, trust metadata, and egress metadata.
- R19. Direct Anthropic API support and non-OpenAI-compatible HTTP protocols require a separately reviewed adapter and are not implied by R17.
- R20. Native Codex agents and Codex root must not masquerade as external providers or external second opinions.

**Provider onboarding and credentials**

- R21. Operators must be able to propose a new OpenAI-compatible provider without changing provider-specific execution code.
- R22. Onboarding must be dry-run by default and show the endpoint, model, capability claims, key environment-variable name, cost policy, trust metadata, and intended registry change.
- R23. Onboarding must perform validation and a bounded smoke before an explicit apply confirmation can make the provider selectable.
- R24. Provider configuration may store only secret references such as environment-variable names; it must never store, log, receipt, or render secret values.
- R25. Credential-like values found in task payloads must be blocked or redacted before dispatch, regardless of ordinary route approval.
- R26. Other sensitive source or business content may be sent only after the operator approves the concrete provider, route preview, and bounded outbound context scope and sensitivity classification.

**Execution containment and mutation**

- R27. Claude CLI and `agy` patch-producing actions must execute in an isolated workspace against a bounded approved write set.
- R28. A CLI provider may return a patch and supporting evidence but must never apply it to the live worktree.
- R29. Generic HTTP providers must remain artifact-only and must not receive a live-worktree mutation capability.
- R30. Codex root must inspect, verify, and explicitly apply any accepted patch or generated artifact through the normal stage workflow.
- R31. Output outside the approved write set, containment failure, incomplete shutdown, or receipt-integrity failure must make the action unusable.
- R32. Direct live-worktree mutation must remain disabled until the measured promotion criteria in Key Decisions are satisfied and a later operator decision changes the capability boundary.

**Dispatch truth, receipts, and reconciliation**

- R33. Every external action must distinguish requested, approved, resolved, launched, completed, adjudicated, and consumed milestones as well as unavailable, rejected, canceled, timed-out, interrupted, and integrity-failure outcomes.
- R34. Launch acknowledgement and a schema-valid receipt are required before the runtime may claim that an external provider ran.
- R35. A successful receipt must bind the configured provider endpoint, requested model, adapter class, invocation identity, output attestation, terminal status, non-secret telemetry, and provider or model identity observed in the response when available. It must not claim stronger remote-provider identity proof than the adapter trust model and response evidence support.
- R36. A second-opinion result must contain typed findings suitable for bounded reconciliation; raw provider prose alone cannot become a review finding or gate input.
- R37. External output must remain inert evidence until Codex root verifies and adjudicates it.
- R38. The runtime must prevent duplicate dispatch after an uncertain or resumed action through durable claim/replay semantics.
- R39. Missing, malformed, substituted, or contradictory receipts and unavailable durable claim or status persistence must produce a visible unavailable or integrity-failure state, never synthetic success or blind redispatch.
- R40. No external finding, score, vote, timeout, or absence may independently pass or block a lifecycle hard gate.

**Failure handling and requiredness**

- R41. External actions must default to `best-effort` unless the approved bundle marks them `required-before-continue`.
- R42. A best-effort action that fails or is unavailable must be recorded visibly and may be skipped without converting native Codex work into external evidence.
- R43. A required action may pause the stage until it succeeds, is explicitly removed from the bundle, or the operator approves continuation without it. Removal or continuation must record the operator decision and rationale in the durable status card.
- R44. Requiredness controls workflow progression only; it does not grant the external result substantive gate authority.
- R45. Provider substitution after approval is forbidden even when another provider appears equivalent.
- R46. The runtime must never silently continue while representing a selected but undispatched action as completed.

**Operator visibility and cost reporting**

- R47. Every action must produce a durable operator-visible status card.
- R48. The status card must show requested intent, approved route, resolved provider and model, adapter class, launch acknowledgement, receipt validity, requiredness, artifact or finding destination, Codex adjudication, and consumption state.
- R49. The status card must show cost class plus estimated and observed token or usage telemetry when available.
- R50. The runtime must not enforce a workflow budget or spend ceiling in v1; provider-account controls remain authoritative.
- R51. Operator-facing summaries must distinguish `unavailable`, `not launched`, `launched`, `timed out`, `interrupted`, `canceled`, `invalid evidence`, `available`, `accepted`, `rejected`, and `consumed` without collapsing them into success/failure prose.

**Release and capability promotion**

- R52. Release proof must include a real Claude CLI action, a real `agy` action, and a real generic HTTP action using Ollama Cloud.
- R53. Release proof must show that every named lifecycle stage consumes at least one approved external action and renders its durable status card.
- R54. The live matrix must include both offload and second-opinion actions, best-effort and required actions, contained patch and artifact-only results, and cross-family plus warned same-family routing.
- R55. Negative proof must cover missing credentials, unavailable provider, timeout, no output, invalid receipt, substituted route, secret detection, write-set escape, duplicate resume, and operator rejection.
- R56. Provider onboarding proof must add a test OpenAI-compatible provider through preview, smoke, explicit apply, subsequent selection, and receipt readback without exposing the key.
- R57. Direct-mutation promotion evidence must count qualifying contained runs by provider and preserve the acceptance, containment, integrity, and rollback measurements needed for the later decision. Before the first run can qualify, the plan must define and review the meanings of qualifying run, major rewrite, and passing rollback drill; those definitions must remain versioned and cannot change retroactively within an evidence window.

## Key Flows

- F1. **Stage offer and approval.** A lifecycle stage proposes its default or remembered action bundle. The runtime resolves providers, renders concrete route previews, the operator edits or approves the bundle, and the approved route identities freeze. **Covers R1-R9, R12-R14.**
- F2. **External action execution.** The runtime claims the action, invokes the selected supervised CLI or HTTP adapter, validates terminal state and receipt, and writes the durable status card. **Covers R15-R20, R33-R40, R47-R51.**
- F3. **Codex consumption.** Codex root verifies a patch, artifact, or typed opinion, records accept/reject/partial-use adjudication, and attaches accepted material to the stage's native output without transferring gate authority. **Covers R28-R30, R36-R40, R48.**
- F4. **Unavailable or invalid action.** The runtime records the precise failure. Best-effort work continues visibly; required work pauses until the operator changes the bundle or approves continuation. **Covers R39, R41-R46, R51.**
- F5. **Contained patch action.** Claude CLI or `agy` works in isolation, produces a bounded patch and receipt, and returns it to Codex root for inspection and application. **Covers R27-R32.**
- F6. **Provider onboarding.** The operator supplies non-secret provider metadata and a key reference, reviews validation and smoke results, then explicitly applies the registry change before using the provider. **Covers R21-R26, R56.**
- F7. **Remembered policy reuse.** A later run loads the repo-and-stage template, resolves current provider state, and requires a new approval when the concrete route differs from the previous preview. **Covers R7-R8, R45.**
- F8. **Direct-mutation reconsideration.** Operational evidence accumulates from contained runs; only a complete qualifying dataset and passing rollback drill can reopen the mutation boundary. **Covers R32, R57.**

## Acceptance Examples

- AE1. **Trigger:** `/ideate` proposes its default bundle. **Expected:** the operator sees one blind-generator offload and one survivor-set second opinion as separate actions with separate routes; approving both produces two independently receipted status cards. **Covers R2-R6, R47-R49.**
- AE2. **Trigger:** a remembered `/brainstorm` policy previously resolved to Claude, but the current resolver selects Gemini. **Expected:** the route change is previewed and requires fresh approval; no call occurs under the old approval. **Covers R7-R8, R45.**
- AE3. **Trigger:** an approved best-effort Ollama Cloud action cannot authenticate. **Expected:** the card records `unavailable`, no fallback provider runs, and the stage may continue without representing external evidence. **Covers R11, R41-R42, R46.**
- AE4. **Trigger:** an approved required second opinion times out. **Expected:** the stage pauses, records `timed out` with terminal evidence, and asks the operator to retry, remove the action, or continue without it; any override decision and rationale are durable, and the timeout does not determine the substantive verdict. **Covers R43-R44, R51.**
- AE5. **Trigger:** the payload contains a token-like credential. **Expected:** the runtime blocks or redacts it before provider invocation even though the operator approved sending other sensitive content. **Covers R24-R26.**
- AE6. **Trigger:** Claude CLI produces a patch outside its approved write set. **Expected:** the patch is unusable, the live tree remains untouched, and the card records the containment failure. **Covers R27-R31.**
- AE7. **Trigger:** an Ollama Cloud action returns an artifact and a valid HTTP receipt. **Expected:** the card proves the configured endpoint, requested provider and model, invocation identity, and any provider or model identity observed in the response without overstating remote internals; Codex root either consumes or rejects the artifact explicitly. **Covers R17-R18, R33-R39, R48.**
- AE8. **Trigger:** the operator explicitly chooses an OpenAI-family provider for Codex's second opinion. **Expected:** the preview warns that family independence is reduced and requires explicit approval before launch. **Covers R13-R14.**
- AE9. **Trigger:** a preference is saved but no production runner is available. **Expected:** the action becomes visibly `unavailable` or `not launched`; the lifecycle stage cannot claim or imply that a second opinion occurred. **Covers R9, R34, R39, R46.**
- AE10. **Trigger:** a metered provider exceeds an estimate while remaining within its provider-account limit. **Expected:** the runtime records observed usage and does not block solely because there is no workflow budget. **Covers R49-R50.**
- AE11. **Trigger:** an operator onboards a new OpenAI-compatible endpoint. **Expected:** dry-run validation and smoke complete before apply, the registry stores only the key environment-variable name, and a later action resolves and runs through the generic HTTP adapter. **Covers R21-R26, R56.**
- AE12. **Trigger:** a resumed stage sees an uncertain prior dispatch claim. **Expected:** it reads the durable claim and status card, never blindly redispatches, and either consumes the completed evidence or records an `interrupted`, `unavailable`, or `integrity failure` outcome. If durable claim state cannot be read, dispatch fails closed. **Covers R33, R38-R39.**

## Success Criteria

- An operator can approve an external action and see attributable evidence that the approved adapter and configured route ran, which provider or model identity was requested and observed, what it produced, and whether Codex used the result; the runtime does not overstate remote internals it cannot independently verify.
- All six lifecycle stages use one coherent approval, dispatch, receipt, and status vocabulary.
- Claude CLI, `agy`, and Ollama Cloud each complete a real end-to-end action before release.
- No live-worktree mutation originates from an external provider in v1.
- No credential value appears in a provider payload, registry entry, receipt, status card, or log.
- Provider unavailability, route substitution, and invalid receipts are always visible and never become synthetic external evidence.
- A planner can derive implementation units without deciding product behavior, stage defaults, provider authority, fallback semantics, or release proof.

## Scope Boundaries

- Direct external mutation of the live worktree is deferred until the measured promotion gate is satisfied and separately approved.
- Direct Anthropic API support is deferred; Claude CLI is the v1 Claude provider.
- Non-OpenAI-compatible generic JSON APIs are outside v1 and require reviewed protocol adapters.
- External engines are never native Codex children, workflow gatekeepers, Git authorities, or final adjudicators.
- Silent dispatch, substitution, fallback, or success inference is outside the product's identity.
- Workflow-enforced provider budgets and spend ceilings are outside v1; cost visibility remains in scope.
- Supporting additional lifecycle stages is deferred until the six named stages prove the shared contract.
- Replacing native Codex work entirely with an external executor is outside this product's identity; external actions remain chaperoned units or advisory evidence.

## Dependencies and Assumptions

- The existing Codex registry, resolver, HTTP bridge, receipt primitives, trust boundary, reconciliation, and offer helpers are reusable substrate, but their current presence is not proof of runtime integration.
- Claude CLI and `agy` must be installed and authenticated independently of the plugin. The runtime may preflight them but must not own account credentials.
- OpenAI-compatible HTTP providers must expose compatible chat behavior and provide credentials through operator-managed environment variables.
- Ollama Cloud is the required live HTTP proof provider because its key is available and its registry row already exists.
- Provider-account controls are assumed sufficient for the operator's spending policy in v1.
- Model capability ratings and cost metadata drift; route resolution must treat them as dated policy data rather than permanent truth.
- The stage matrix is a default policy, not a claim that every run benefits from every action.
- A real external response may still be low quality; receipt validity proves execution identity and integrity, not correctness.
- For remote HTTP providers, receipt validity proves the supervised request, configured route, and observed response identity within the adapter trust model; it cannot independently prove an undisclosed provider-side model implementation.

## Outstanding Questions

No product decision remains unresolved before planning.

The following are deferred to planning: runtime and adapter ownership, invocation and receipt schemas, status-card persistence and rendering, preference migration, registry-update mechanics, isolated workspace implementation, exact test organization, and the controlled environment used for the live release matrix.

## Sources and Research

- `docs/investigations/external-second-opinion-preference-noop-2026-07-11.md`
- `docs/ideation/2026-07-11-codex-workflow-control-agent-lifecycle-ideation.md`
- `docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`
- `plugins/saga/references/engine-registry.yaml`
- `plugins/saga/references/surface_intent_defaults.yaml`
- `plugins/saga/scripts/engine_dispatch.py`
- `plugins/saga/scripts/engine_bridge_http.py`
- `plugins/saga/scripts/engine_offer.py`
- `../infiquetra-claude-plugins/docs/brainstorms/2026-06-27-external-engine-capability-routing-requirements.md`
- `../infiquetra-claude-plugins/docs/plans/2026-07-10-issue-394-second-opinion-triggers-plan.md`
- `../infiquetra-claude-plugins/plugins/saga/scripts/second_opinion.py`
- `../infiquetra-claude-plugins/plugins/agy/scripts/agy_delegate.py`
- `../infiquetra-claude-plugins/plugins/codex/scripts/codex_delegate.py`
- Claude objective `#336`, issue `#394`, and PR `#558`
