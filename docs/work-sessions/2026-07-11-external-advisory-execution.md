# External Advisory Execution Work Session

## U1. Freeze the adaptation and capability boundary

The current external-advisory plan now owns the active port contract instead of inheriting the completed Saga 0.75.17 window.

The frozen Claude window is `38742ece89880a6b140be237edad6d3f13c97b54..675712b1d6a55ead11f3e971ed0e119354621bf2`. Three source rows are classified: current second-opinion behavior and supervised delegate behavior are Codex adaptations, while the Claude-host Codex-delegate contract test remains rejected as an active surface.

The Codex execution boundary is `39f0a2f466cb6f58e203ce3e586a959ff853a342..d8f5d165ad0e859af9c7d7f1ba7461b00ec1ae95`. Seven planning, review, investigation, ideation, and decision artifacts are preserved.

**Files modified:** `scripts/port_contract.py`, `tests/test_port_contract.py`, `docs/validation/codex-runtime-capability-snapshot.json`, `docs/portability/manifests/2026-07-11-external-advisory-execution.json`, `docs/portability/classifications/2026-07-11-external-advisory-execution.md`, `docs/engineering-journal/QUEUED.md`.

**Checks run:** classification gate passed; `tests/test_port_contract.py` passed with 25 tests.

**Next step:** Implement U2 action contracts, durable store, and status projection.

## U2. Add the action contract, store, and status projection

External actions now have closed request, approval, state, transition, and requiredness contracts. Each action stores immutable request and approval records, a locked hash-chained event stream with torn-tail recovery, and reproducible JSON and Markdown status projections.

The store uses `<git-common-dir>/saga-external-actions/<saga-id>/<run-id>/<action-id>/`. It rejects path traversal, conflicting immutable rewrites, skipped or contradictory transitions, duplicate event IDs with changed content, broken hash links, and continuation overrides without a terminal failure and rationale.

**Files modified:** `plugins/saga/scripts/external_action_contract.py`, `plugins/saga/scripts/external_action_store.py`, `plugins/saga/scripts/external_action_status.py`, `tests/test_external_action_store.py`, `tests/test_external_action_status.py`.

**Checks run:** 12 focused pytest cases passed; Ruff passed; mypy passed for all three source modules.

**Next step:** Implement U3 approval, policy, egress, and runtime orchestration.

## U3. Build approval, policy, egress, and runtime orchestration

The shared runtime now resolves explicit actions over repo/stage policy, legacy preferences, and shipped defaults. All six stage bundles are data-authored, while legacy `engine-prefs.json` values remain unapproved intent rather than launch authority.

Outbound payloads are recursively sanitized before any store or executor call. Credential-shaped strings are redacted without retaining values, private keys block the action, and the approved payload digest, route, egress, cost class, context scope, base revision, and write set bind one approval fingerprint.

The provider-neutral runtime implements prepare, approve, claim-before-launch, launch acknowledgement, terminal failure mapping, adjudication, consumption, and status refresh. Executors are injected and must return validated evidence, so no provider is represented as active before U4 wires `engine_dispatch`.

**Files modified:** `plugins/saga/references/external-action-defaults.yaml`, `plugins/saga/scripts/external_action_policy.py`, `plugins/saga/scripts/external_action_egress.py`, `plugins/saga/scripts/external_action_runtime.py`, `plugins/saga/scripts/external_action.py`, `tests/test_external_action_policy.py`, `tests/test_external_action_egress.py`, `tests/test_external_action_runtime.py`.

**Checks run:** 23 combined U2/U3 pytest cases passed; Ruff passed; scoped mypy passed for all four U3 source modules.

**Next step:** Implement U4 supervised Claude, `agy`, and HTTP adapters with disposable-clone containment.
## U4 - Supervised external adapters

- Added disposable local-clone workspaces with detached checkout, remote removal, binary patch capture, write-set enforcement, and cleanup.
- Added supervised Agy and Claude CLI adapters plus thin delegate entry points.
- Added the `claude-cli/opus` registry route and `claude-delegate` bridge-signature policy.
- Preserved the established Agy invocation digest contract while adding Claude model and effort metadata.
- Focused tests: `64 passed`.
- Ruff: passed.
- Mypy: the four U4 source files pass with `--follow-imports=skip`; unrestricted import following reaches seven pre-existing errors in `fleet_commons_shim.py` and `engine_bridge_http.py`.
## U5 - Provider onboarding and policy persistence

- Extended repo-local engine overlays with validated additive provider rows and canonical-plus-overlay composition.
- Redirected OpenAI-compatible onboarding apply away from the canonical registry and into a digest-bound overlay after a bounded non-sensitive HTTP smoke.
- Added environment-variable secret-reference enforcement, duplicate-key rejection, optimistic concurrency, and composed-registry CLI visibility.
- Added atomic digest-bound external-action policy persistence.
- Added canonical promotion diff output and overlay finalization that requires identical canonical readback.
- Focused tests: `77 passed`.
- Ruff: passed.
- Mypy: passed for the six U5 source files with `--follow-imports=skip --ignore-missing-imports`.
## U6 - Six-stage lifecycle integration

- Replaced legacy Engine Offer instructions in ideate, brainstorm, plan, work, doc-review, and code-review with one editable prepare-approve-execute-adjudicate-consume contract.
- Added a shared lifecycle module for stage bundles, pre-approval route/cost/egress/status views, selected-action preparation, approval, requiredness-aware execution, typed reconciliation, and consumption.
- Added the `external_action.py bundle` operator command and covered the previously missing plan stage.
- Proved all ten default actions, both intents, operator removal, pre-dispatch bundle halt, best-effort continuation, required pause, typed-finding completeness, status cards, and final consumption.
- Focused tests: `113 passed`.
- Ruff: passed.
- Mypy: passed for the two U6 source files with `--follow-imports=skip --ignore-missing-imports`.
## U7 - Hermetic vertical and negative matrix

- Bound approved lifecycle previews to shipped CLI/HTTP adapters and dispatch validation through `executor_for_preview`.
- Added content-addressed, owner-only evidence artifacts carrying normalized evidence, typed findings, and validated bridge receipts.
- Proved the real subprocess/disposable-workspace path for both offload and second-opinion without injecting a fake runner.
- Expanded durable status cards with provider, model, adapter, launch, receipt validity, usage, adjudication, and consumption history.
- Added version-1 frozen definitions for qualifying runs, major rewrites, provider distribution, integrity failures, containment failures, and passing rollback drills.
- Added R55 closure, operator rejection, duplicate resume, no-output, timeout, drift, containment, onboarding, promotion, and receipt-integrity proof.
- Hermetic U7 matrix: `196 passed`; grouped external-action/resolver/overlay follow-up: `56 passed`.
- Ruff: passed.
- Mypy: passed for the three changed runtime source files with `--follow-imports=skip --ignore-missing-imports`.
## Workflow execution deviation

The approved plan contains a Verified Workflows DAG, but U1-U7 were executed manually in the root
session instead of being initiated and tracked through `verified-workflows:run`.

**Why it happened:** The workflow table assigns U1-U8 to the root with `vehicle=root`. I incorrectly
treated that root ownership as making the Verified Workflows coordinator optional, rather than
understanding that the coordinator still had to create the protected subject, intents, workspace
snapshots, evidence records, dependency chronology, and final barrier. Repeated disconnect/resume
continuations reinforced the manual per-unit checklist instead of restoring the approved execution
backend.

**Impact:** The U1-U7 commits and reported tests are real repository evidence, but they do not have
the protected intent/snapshot/result/root-verification chain required to claim Verified Workflows
compliance. The planned post-U8 architecture, security, adversarial, testing, scanner, and smoke
barrier has not run. U8's attended live matrix was stopped when the deviation was identified; no
release cutover has been claimed.

**Remediation:** Preserve the existing atomic commits as pre-existing implementation, resume the
Saga, invoke `verified-workflows:run` against the approved plan, declare the current repository state
as the protected subject, revalidate U1-U7 evidence through the workflow contract, and execute U8 plus
the final review and validator barrier under the runner. Any evidence the runner cannot bind is rerun
rather than retroactively represented as protected workflow evidence.

## Verified workflow reconciliation

- Protected workflow run: `record:workflow-run:238c5184211e384e00550032d8f504935145140501c22fab68b6c36ef37970f7`.
- U1-U7 were recorded as root-owned revalidation receipts against the protected pre-existing implementation subject. These receipts prove the recovery checks; they do not claim that the original implementation was workflow-launched.
- U8 started under protected intent `record:intent:af453ad43a1cdc75c96b11163f18ed68f9a147ef1c6a68c812a4ee98911874ef`.
- The first attended U8 matrix failed closed at the Agy brainstorm action because the adapter wrote `.saga-agy.log` inside a disposable clone while declaring an empty write set. The containment layer correctly classified that adapter-owned log as a write-set escape and invalidated the evidence.
- The adapter now sends the Agy diagnostic log to `os.devnull`; the registry recipes describe the actual Agy CLI invocation, and the integration test asserts that the log path cannot enter the clone.
- Narrow repair checks passed: the Agy adapter integration case (`2 passed`), release-matrix tests (`6 passed`), and scoped Ruff checks.
- The attended retry passed with proof content SHA-256 `3e4c78fc10d8a9b1b17465e721409c22805eb9bdbd97eb32bfbed12e471ee7bf`.
- Cutover remains unclaimed until the protected U8 receipt, independent review/validation barrier, and final gate all pass.
- The first reconciliation run could not normalize U8 because its initial protected subject omitted the not-yet-created proof path. The subject-chain guard correctly rejected the proof as an outside-scope workspace mutation. That run remains nonpassing evidence; a replacement protected run starts from the complete current subject and revalidates U1-U8 before independent review.

## Review round 1 remediation

- Independent architecture, security, adversarial, and testing lenses found blocking correctness gaps after the first protected U8 receipt.
- Fixed overlay transforms that deleted onboarded engine rows.
- Approval now binds the persisted sanitized payload, dirty-worktree overlap, route, request, and approved base revision; adapter execution reloads the persisted approval instead of trusting mutable preview state.
- Added explicit immutable attempt identity, predecessor binding, interruption handling, and fresh-store retry behavior.
- Bundle execution now preflights every executor and approval before the first provider launch.
- Runtime completion now requires a validated, content-addressed evidence artifact contained in the action store.
- CLI receipts redact prompt argv content, and timeout handling terminates the provider process group.
- Replaced the marker rollback with an isolated candidate install, fresh-interpreter API readback, prior-state restoration, and digest comparison. Added closed proof fields and semantic content-hash verification.
- Deterministic remediation evidence: `126 passed`; scoped mypy and Ruff passed.
- Operator-accepted risk remains unchanged from the plan decision: disposable clones plus provider-native safe/sandbox modes are the containment boundary. Full containers, executable signing, and host-wide credential/egress isolation are not being added in this iteration.
- A final replacement workflow run is used because earlier reviewer/pytest commands changed ignored cache files outside the prior protected subject. Remaining commands disable bytecode and pytest cache writes so the final subject chain remains auditable.
- Remediated attended matrix passed under protected U8 intent with proof content SHA-256 `40d905b4e2d7409f0622d76a0af26da6edfe6fb23870143543dcab7c86289b65`.
- The proof now includes closed per-stage evidence fields, semantic hash verification, an isolated candidate install, a fresh-interpreter runtime API readback, and restoration to the captured prior installed-state digest.

## Review round 2 remediation

- Final review round remained blocked on symbolic `HEAD`, retry lineage forks, retry without termination proof, executor-asserted evidence validity, overlay-only providers bypassing public validation, and self-attested/simulated cutover proof.
- Preparation now resolves symbolic refs to a full commit SHA and derives dirty overlap from repository state; execution rechecks overlap before claim and launch.
- Retry lineage now permits one atomic successor per predecessor. Launched interruption requires a termination receipt before retry, and durable load/interrupt/retry operations are exposed through the lifecycle boundary.
- The runtime now parses a closed `external_action_evidence.v1` artifact, recomputes its evidence and file digests, validates the bridge receipt, and binds action, intent, engine, and variant to persisted approval. Raw provider evidence is no longer duplicated in `events.jsonl`; status reads the protected artifact by reference.
- Public execution-spec validation and release routing now use the repo-aware composed registry so overlay-only providers remain selectable.
- Release proof now records the committed Git tree and dereferenceable action-store paths. Verification recomputes the tree and each action-record directory digest and can require the evidence tag to resolve to `source_head`.
- The rollback drill now creates a temporary local marketplace, installs `fleet-core` and `saga` through the real Codex plugin CLI under an isolated `CODEX_HOME`, proves fresh `codex plugin list` discovery plus the installed public lifecycle probe, removes both plugins and the marketplace, and verifies restoration to the initial plugin-list state.
- Deterministic remediation evidence: `129 passed`; Ruff passed; scoped mypy passed apart from the repository's known PyYAML stub dependency, handled with the existing local ignore convention.

## Review round 3 remediation

- The replacement Verified Workflows run revalidated U1-U8 against protected subject `record:subject:37acebdf2536a37424c6d94de29e5f724439f3ef97451f572b4ddd0da98154bc`; it did not represent the original root-inline implementation as workflow-launched.
- Architecture, security, adversarial, and testing lenses found atomic-claim replay, reusable process-group identity, structured-secret bypass, post-launch invalid-evidence retry dead ends, under-validated retry recovery, root-scope overlap gaps, incomplete action-record semantics, replayable command evidence, machine-local proof preimages, stale manifest bindings, and optional tag verification.
- Claim acquisition is now atomic and nonce-bound. A losing concurrent executor cannot call the provider, and a CLI child is killed if durable launch persistence fails.
- CLI termination receipts now bind the observed process start identity and reject stale or reused numeric process IDs. HTTP operations no longer self-attest remote termination; uncertain remote work remains launched and cannot be blindly retried.
- Structured credential fields, JWTs, and private-key variants fail closed before persistence or dispatch. Repository-root scope matches every dirty path, while absolute and parent-traversal scopes are rejected.
- Every post-launch failure either records an attempt-bound runtime termination receipt or remains interruptible/uncertain. Retry markers and recovered successor requests use closed, exact lineage validation.
- Release verification now revalidates the closed evidence artifact and completion-event bindings, recomputes adapter identity, and captures command evidence directly at the subprocess boundary with run identity, sequence, chronology, timestamps, argv, cwd, exit status, and stream hashes.
- The attended run retains copied action records and command evidence under `docs/validation/external-action-evidence/`, allowing the evidence tag to contain every proof preimage required for fresh-clone verification.
- `port_contract.py validate --stage cutover` now invokes exact proof-and-bundle tag verification instead of relying on an optional manual command.
- Operator-accepted scope remains unchanged: disposable clones plus provider-native safe/sandbox modes are the containment boundary for this iteration. Full containers, host-wide credential isolation, controlled network namespaces, and keyed/HMAC action-history anchoring remain explicitly outside this plan.
- Combined deterministic remediation checks: `99 passed` with the stale-manifest assertion deferred until proof regeneration; Ruff passed. The attended portable provider/install/rollback matrix passed with content digest `beb32190736c58dfcd0025ed995732e5dc0d6db87dc854976b7a993cb6cd0e87` from source commit `4800246eb492366c0b08369d101ad504713dd74c`.

## Review round 4 remediation

- The final adversarial reviewer found two P1 issues: a successful CLI leader could complete while a same-process-group descendant remained alive, and the port-contract suite still expected the finalized U2/cutover manifest to fail.
- CLI completion now requires terminal process-group confirmation. If the provider group remains active after a valid artifact is returned, the action stays `launched-uncertain`, no completion event or termination receipt is written, and retry remains blocked until the launched attempt is resolved.
- Added a real subprocess regression test whose leader exits after spawning a same-process-group descendant. The test proves the runtime remains launched and then explicitly cleans up the group.
- Replaced the obsolete pre-cutover assertion with a positive current-manifest U2/cutover test while retaining mutation-based negative coverage.
- Focused remediation checks passed with `61 passed`; Ruff and `git diff --check` passed.
- The attended portable provider/install/rollback matrix was regenerated from source commit `45403b9c2906e110beaf640918431d292b96bb4f`. Exact retained-bundle verification passes with content digest `a2dfa2ae5b6b456ed8f4e96151fd490822816376f44a73d25f339c3b9f04de09`.
- The prior final reviewer receipts remain diagnostic because they predate these fixes. A fresh protected final barrier must accept the refreshed subject before cutover is claimed.
