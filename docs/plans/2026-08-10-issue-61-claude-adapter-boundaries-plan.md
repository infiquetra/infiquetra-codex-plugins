---
title: Issue 61 Claude Adapter Effort and macOS Identity Boundaries
type: fix
status: active
date: 2026-08-10
origin: docs/brainstorms/2026-07-26-codex-plugin-lifecycle-simplification-requirements.md
---

# Issue 61 Claude Adapter Effort and macOS Identity Boundaries

## Summary

This plan makes the surviving one-shot Claude command line interface (CLI) adapter honor its resolved effort and retain its one required non-secret macOS identity input. The change remains confined to the adapter, its registry truth, focused tests, and adapter contract documentation.

## Problem Frame

The current Claude route resolves `effort: high` from `plugins/saga/references/engine-registry.yaml:24-41`, but its process command arguments (argv) builder passes only `--model` in `plugins/saga/scripts/external_action_adapters.py:70-87`. The shared minimal child-environment helper omits `USER` in `plugins/saga/scripts/external_action_adapters.py:36` and `466-469`, which makes a healthy macOS Keychain-backed Claude session appear unauthenticated.

GitHub issue #61's validation comment narrows this plan to defects #51 and #52. Closed issues #49, #50, and #58, plus merged pull request (PR) #69, are historical evidence only: the implementation must not restore status, approval, chaperone, telemetry, subscription, account-detection, or workflow-feasibility surfaces.

## Requirements

These requirements retain only the two approved Claude adapter corrections.

R1. The `claude-cli/opus` route must forward exactly one supported, non-blank effort value resolved from its registry invocation as `--effort <value>` before the provider process launches.

R2. The Claude adapter boundary is the enforcement authority for the closed vocabulary `low`, `medium`, `high`, `xhigh`, and `max`. An absent, blank, or unsupported configured value must produce a clear unavailable result that safely names the invalid value before spawning Claude; the adapter must not default, substitute, or escalate it.

R3. The existing receipt must continue to bind the resolved invocation digest and a redacted runner argv, so it proves the configured effort was requested and passed in argv, but not that the provider applied that effort.

R4. The shared child-environment helper must add `USER` only for the `claude-cli` engine when it is present, while retaining the existing allowlisted process basics and filtering tokens, secrets, and unrelated parent variables for every engine.

R5. A Claude request without a usable `USER` input must return a clear pre-launch unavailable reason. It must not start login, copy credentials, inspect account identity, construct a per-profile home, or inherit the parent environment broadly.

R6. The maintained route documentation and registry recipe must describe the same configured effort that the adapter passes, and must use requested/passed-in-argv language rather than provider-observed wording.

## Key Technical Decisions

These decisions make the adapter fail closed without creating a second lifecycle or account-control surface.

KTD1. Resolve effort only from the selected immutable registry invocation: the closed harness request selects `engine_id/variant`, and `execute()` copies the matching entry invocation before adding request context (`plugins/saga/scripts/external_action_adapters.py:236-261`), so accepting a caller-supplied effort would permit route drift.

KTD2. Use the Claude adapter boundary as the fail-closed enforcer for `low`, `medium`, `high`, `xhigh`, and `max`: missing, whitespace-only, or unsupported configured values are unavailable before `subprocess.Popen`, with a safely named invalid value, rather than silently relying on the provider default. This is narrower than adding a provider capability, fallback, or account-control system.

KTD3. Keep the existing invocation digest and redacted argv receipt as transport proof: the receipt already hashes the invocation and captures the launch argv with only the task redacted (`plugins/saga/scripts/external_action_adapters.py:157-170`, `404-427`, and `481-483`). It can prove the configured value was requested and passed, not provider-observed effective reasoning effort.

KTD4. Make `USER` a Claude-engine-scoped allowlist member and preflight it only for Claude: the shared environment helper must receive the engine identity, include `USER` for `claude-cli` only when non-blank, and omit it for every non-Claude route. `USER` is the validated macOS Keychain lookup input, while allowing OAuth tokens, API keys, account output, or the broad environment would weaken the current secret boundary.

KTD5. Keep the registry recipe executable and internally consistent: remove the current generic rejection of `--effort` in `plugins/saga/scripts/engine_registry.py:269-301`, then validate that any declared effort flag agrees with the route's `invocation.effort`. This lets the Claude recipe document the actual argv without making registry metadata a second execution path.

## Implementation Units

These three units sequence registry truth, adapter enforcement, then documentation and final proof.

### U1. Align the Claude registry route with the supported effort contract.

This unit makes the registry's retained Claude route describe the command it is allowed to launch and rejects contradictory metadata.

**Goal:** Update the Claude registry recipe to include its configured effort, and revise registry validation so an effort flag is permitted only when it matches a non-blank declared invocation effort.

**Requirements:** R1, R2, R6.

**Dependencies:** None.

**Files:** `plugins/saga/references/engine-registry.yaml`; `plugins/saga/scripts/engine_registry.py`; `tests/test_engine_registry_lint.py`; `plugins/saga/tests/test_engine_routing.py`.

**Approach:** Keep `invocation.effort` as the one route value. Make the recipe's `--effort` token a checked representation of that value rather than a second configurable source, and retain the Claude adapter as the runtime enforcer of `low`, `medium`, `high`, `xhigh`, and `max`. Preserve the existing generic validation for every route that does not place an effort flag in its recipe, and reject blank, duplicate, or mismatched effort flag forms where the registry exposes one.

**Patterns to follow:** The invocation schema already requires non-empty `model`, `effort`, `via`, recipe, and write capability fields in `plugins/saga/scripts/engine_registry.py:269-303`; the shipped-route and resolution assertions live in `plugins/saga/tests/test_engine_routing.py:32-61` and `tests/test_engine_registry_lint.py:35-94`.

**Test scenarios:** (1) Input: the shipped `claude-cli/opus` row; action: load the registry; expected outcome: its recipe declares exactly the configured `high` effort. (2) Input: a fixture with no recipe effort flag; action: validate a non-Claude generic CLI row; expected outcome: existing valid routes remain accepted. (3) Input: blank, duplicated, or different recipe effort values; action: load the fixture; expected outcome: validation fails with the route and inconsistency reason before any adapter can run.

**Verification:** The registry accepts the six maintained routes, preserves the selected Claude invocation unchanged through resolver output, and rejects contradictory route metadata deterministically.

### U2. Fail closed at the one-shot Claude launch boundary while preserving receipt proof.

This unit forwards the approved effort and makes missing Claude identity input unavailable before a provider process can start.

**Goal:** Extend the Claude argv construction and pre-launch route checks without changing direct read-only, bounded-write, workspace, or receipt ownership behavior.

**Requirements:** R1, R2, R3, R4, R5.

**Dependencies:** U1.

**Files:** `plugins/saga/scripts/external_action_adapters.py`; `plugins/saga/tests/test_external_action_adapters.py`; `tests/test_external_action_adapters.py`.

**Approach:** Validate the registry-supplied Claude effort at the Claude adapter boundary against `low`, `medium`, `high`, `xhigh`, and `max`, and append exactly one `--effort <value>` pair to the existing Claude argv. Change the shared environment helper to accept the engine identity, add `USER` only for non-blank Claude launches, and return the normal `saga.harness.result.v1` unavailable response before invoking the runner when a Claude request lacks that input. Retain the current task redaction, invocation digest, receipt validation, safe mode, limited tools, remote-stripped workspace, and no-write direct-call rules.

**Patterns to follow:** The current Claude configuration and shared CLI runner are in `plugins/saga/scripts/external_action_adapters.py:70-188`; request-to-invocation construction and normal unavailable mapping are in `plugins/saga/scripts/external_action_adapters.py:222-289`; the minimal environment helper is at `plugins/saga/scripts/external_action_adapters.py:466-469`.

**Test scenarios:**

1. Input: registry effort `high` and a fake Claude process. Action: execute a read-only Claude request. Expected outcome: process command arguments contain one `--effort high`, safe read-only tools remain unchanged, and the receipt records the redacted command arguments plus an invocation digest for the same effort.

2. Input: an approved diagnostic fixture with `xhigh`. Action: execute it. Expected outcome: process command arguments contain one `--effort xhigh` and the receipt binding accepts the matching invocation.

3. Input: missing, empty, whitespace-only, or unsupported effort. Action: execute or run the Claude boundary. Expected outcome: the unavailable detail safely names the invalid configured value before `Popen`; no default effort or launch receipt is produced.

4. Input: `USER` set with `AWS_SESSION_TOKEN`, `ANTHROPIC_API_KEY`, and unrelated variables also set. Action: build the child environment for `claude-cli` and execute the fake launch. Expected outcome: `USER` is retained and every unallowlisted value remains absent.

5. Input: missing or blank `USER`. Action: execute a Claude request. Expected outcome: a clear unavailable detail returns before the runner/provider process, with no login, credential, or environment-expansion path.

6. Input: `USER` set for a non-Claude route. Action: build that route's child environment and execute its existing path. Expected outcome: `USER` is absent, and the Claude-specific identity preflight does not alter the non-Claude route.

**Verification:** Focused adapter tests prove the command arguments, receipt binding, pre-launch failures, and engine-scoped allowlist behavior; direct calls remain read-only and the adapter does not add lifecycle or provider-observation data.

### U3. Document the narrow truth boundary and retain it through focused regression coverage.

This unit makes the maintained harness contract state exactly what the receipt and minimal environment do, without reviving retired runtime surfaces.

**Goal:** Update the adapter contract documentation and decision record with requested-versus-observed language, then run the focused suite that guards registry, launch, receipt, and containment behavior.

**Requirements:** R3, R4, R5, R6.

**Dependencies:** U1, U2.

**Files:** `plugins/saga/references/dispatch-adapter-contract.md`; `docs/engineering-journal/DECISIONS.md`; `plugins/saga/tests/test_external_action_adapters.py`; `plugins/saga/tests/test_engine_routing.py`; `tests/test_external_action_adapters.py`; `tests/test_engine_registry_lint.py`.

**Approach:** State that the selected registry effort is requested and passed in process command arguments, while effective provider effort remains unknown without independent provider evidence. State that `USER` is an intentionally minimal Claude-only input, document the pre-launch unavailable outcome, and keep the route list, advisory authority, and six-route inventory unchanged.

**Patterns to follow:** The maintained one-shot contract is `plugins/saga/references/dispatch-adapter-contract.md:1-20`; the journal's reverse-chronological decision format is `docs/engineering-journal/DECISIONS.md:1-31`.

**Test scenarios:** (1) Input: the updated maintained adapter contract; action: inspect its Claude route wording; expected outcome: it distinguishes requested/passed process command arguments from provider-observed effort and identifies the Claude-only `USER` boundary. (2) Input: the focused registry and adapter suites; action: run them after the documentation and behavior changes; expected outcome: all route, receipt, environment-filtering, containment, and no-write assertions pass without any status, telemetry, approval, chaperone, or account-control test surface. (3) Input: the attended macOS host with its existing Claude authentication; action: run the adapter-scoped Keychain smoke without login or credential mutation; expected outcome: the adapter sees the same sanitized authentication class, the auth state is unchanged afterward, and only sanitized pass/fail evidence is retained.

**Verification:** The documentation agrees with executable behavior, the decision record explains the boundary, focused tests demonstrate no retired lifecycle surface has returned, and the attended macOS Keychain smoke is a final gate before completion.

## Risks and Dependencies

This work depends on the Claude CLI vocabulary and a supplied macOS identity input without inspecting either account state or credentials.

The Claude CLI's supported effort vocabulary is an external dependency. The adapter fails unavailable for unsupported registry configuration instead of changing the selected model, choosing a substitute, or treating a launch receipt as provider confirmation.

`USER` depends on the caller environment. The pre-launch check prevents the misleading provider-side login error, but it intentionally does not diagnose macOS account state, inspect Keychain contents, or create a portable authentication mechanism.

## Scope Boundaries

This boundary excludes every retired lifecycle, telemetry, and account-control surface.

**Non-goals:** Provider-observed model or effort telemetry; status projection; approval, claim/replay, promotion, chaperone, or economics state; subscription or account detection; login; credential, token, or Keychain reads/copies; per-profile homes; broad environment inheritance; external writes; changes to the Codex native-agent or Verified Workflows paths.

**Historical evidence only:** Closed issues #49 and #50 describe telemetry, status, economics, and account-control surfaces deleted by PR #69. Closed issue #58 describes the portability gate removed by PRs #68 and #69. None is an implementation unit or follow-up requirement for this plan.

**Deferred to Follow-Up Work:** A future provider integration may add independent effective-effort observation only if it defines a secret-safe evidence contract and is separately approved. It must not reinterpret argv or a receipt as that observation.

## Sources

These sources establish the retained adapter behavior and the historical exclusions.

- GitHub issue #61 and its validation comment; open child issues #51 and #52 and their validation comments.
- `plugins/saga/scripts/external_action_adapters.py:36-36`, `70-188`, `222-289`, `404-427`, and `466-483`.
- `plugins/saga/scripts/engine_registry.py:269-303` and `plugins/saga/references/engine-registry.yaml:24-41`.
- `plugins/saga/tests/test_external_action_adapters.py:17-104`, `tests/test_external_action_adapters.py:32-188`, `tests/test_engine_registry_lint.py:35-94`, and `plugins/saga/tests/test_engine_routing.py:32-61`.
- `plugins/saga/references/dispatch-adapter-contract.md:1-20` and `docs/brainstorms/2026-07-26-codex-plugin-lifecycle-simplification-requirements.md:1-316`.
- Merged PR #69 (`12b5f2c72ff6954cbdbcda8e93408ab2bc518c45`) and closed GitHub issues #49, #50, and #58, used only to confirm retired surfaces remain excluded.

## Final Verification

Complete the focused behavior proof, attended macOS smoke, and repository gates in this order before marking the work complete.

1. Run the focused registry and adapter suites first:

   ```bash
   python3 -m pytest \
     plugins/saga/tests/test_external_action_adapters.py \
     plugins/saga/tests/test_engine_routing.py \
     tests/test_external_action_adapters.py \
     tests/test_engine_registry_lint.py -q
   ```

2. Run the attended macOS Keychain smoke using the existing Claude authentication only. Confirm that the normal and adapter-scoped commands report the same sanitized authentication class, confirm the auth state remains unchanged afterward, and persist only a sanitized pass/fail result rather than raw authentication output or identity.

3. Run `python3 scripts/validate_codex_plugins.py` after the focused proof and smoke pass.

4. Run `python3 -m pytest -q` after plugin validation passes. Completion requires every preceding gate to pass; a failure stops the work without a login, credential, telemetry, or account-control workaround.
