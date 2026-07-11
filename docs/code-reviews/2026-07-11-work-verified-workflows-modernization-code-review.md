# Code Review: work/verified-workflows-modernization

- Target: branch `work/verified-workflows-modernization` vs merge-base `fbd4001`
  (`origin/main`, fetched)
- Reviewed revision: `5e1ad5d1c87001379da7244fe2216a77d16bd6fc`
- Diff: 364 files, +63,622 / -7,791
- Mode: interactive consolidation of the U5-U8 Verified Workflow review rounds
- Blocked status: **NOT blocked** — no unresolved P0/P1 findings
- Plan: `docs/plans/2026-07-10-codex-plugin-model-execution-modernization-plan.md`
- Work session: `docs/work-sessions/2026-07-11-u8-modernization-resume.md`
- Saga: `task-port-recent-claude-plugin-updates`

## Lenses run

Correctness, security, testing, and maintainability/conventions (always-on); reliability because the
diff changes retry, receipt, hook, and external-request failure paths; adversarial because the change
replaces a workflow runtime and crosses local-profile, plugin-install, and HTTP trust boundaries; and
deploy/migration-verification because U8 retires the legacy workflow package, migrates five managed profiles, and
requires exact rollback/readback evidence.

Architecture, adversarial, security, and smoke reviews ran under the approved U8 Workflow Structure.
The final security re-review confirmed the receipt remediations and found the DNS-rebinding gap in the
Saga HTTP bridge; the focused Terra/high fix and rebinding test closed it before this review.

## Findings (validated)

No unresolved findings at confidence 75 or higher.

> Verdict: **PASS — PR-ready.** All P1/P2 review findings were fixed and revalidated before the final
> cutover contract and locked suites passed.

## Remediated during review

- First-run hook receipt storage now creates only the protected final plugin-data directory.
- Agent-validator command records reject secret-shaped argv before durable persistence.
- Receipt join/readback rejects launch acknowledgements after stop and trust captured after launch.
- Current-mode repository validation now requires completed real-profile and cutover-stage evidence.
- The live HTTP bridge pins the TCP dial to one validated public DNS answer while retaining the
  provider hostname for TLS SNI and certificate verification.
- Final cachebuster profile digests are installed and reflected in the Workflow Structure.

## Built-vs-planned

- Scope Check: **CLEAN.** Intent: modernize Fleet Core, Saga, and the workflow runtime against the
  frozen Claude source window, preserve Codex execution-base behavior, retire the legacy workflow package, and
  prove install, rollback, fresh-session, and cutover truth. Delivered: the full U1-U9 plan surface,
  final cachebusted plugins, profile/readback evidence, and a cutover-valid port contract.
- U1 source inventory and capability gate: **DONE** — frozen manifest and runtime capability snapshot.
- U2 Fleet Core execution classes: **DONE** — U2 evidence and catalog/tier tests.
- U3 managed role profiles: **DONE** — five canonical profiles, no legacy profiles.
- U4 root-owned Verified Workflows runtime: **DONE** — protected records, hook receipts, gates, and
  runtime proof.
- U5 Saga continuation and dispatch boundary: **DONE** — 543 locked tests.
- U6 host-neutral correctness and engine substrate: **DONE** — 513 locked tests.
- U7 trust, economics, attestation, and advisory reconciliation: **DONE** — 371 locked tests.
- U8 install, migration, rollback, fresh-session, and cutover: **DONE** — five release evidence kinds
  and cutover-stage contract pass.
- U9 workflow identity migration: **DONE** — canonical new writes with legacy read compatibility.

COMPLETION: 9/9 DONE, 0 PARTIAL, 0 NOT-DONE, 0 CHANGED, 0 UNVERIFIABLE.

## Coverage

- Suppressed findings: 0 after remediation.
- Deterministic gates: current, target-fixture, and cutover validators; generated Saga facts/assets;
  legacy-token inventory; port classification; Ruff; source/cache parity; U5 543, U6 513, U7 371.
- Residual release checks: GitHub CI, merged-main Git marketplace readback, and post-merge QA remain
  downstream shipping gates. The live provider smoke remains credential-gated and was not required for
  this local cutover.
- Excluded worktree change: `.serena/project.yml` is user-owned, uncommitted, and not part of the branch.

## Final re-gate

The final inventory-count guard was corrected at `3e88f2a`. Revalidation passed with 2,102 tests,
all three repository validator modes, the cutover-stage port contract, generated Saga facts/assets,
the legacy-token inventory check, and `git diff --check`. The verdict remains **PASS**.

## Main integration re-review

`origin/main` commit `ca8d105` was integrated as merge commit `823bb6c`. The branch retained its
existing full-URL normalization for qualified GitHub references and extended that same normalization
to base/head/merge-state reads plus update and squash-merge operations. The obsolete `0.65.1`
version metadata from the older base was not carried over; the reviewed modernization versions remain
authoritative.

No new findings. The focused U6 suite passed 514 tests, the full repository suite passed 2,103 tests,
all validator modes and the cutover-stage port contract passed, generated Saga facts/assets remained
current, and GitHub reported PR #26 `MERGEABLE / CLEAN`. The verdict remains **PASS**.
