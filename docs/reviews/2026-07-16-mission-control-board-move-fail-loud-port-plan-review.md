# Plan review: Mission Control board move fail-loud Codex port

Date: 2026-07-16
Issue: `infiquetra/infiquetra-codex-plugins#35`
Plan: `docs/plans/2026-07-16-mission-control-board-move-fail-loud-port-plan.md`
Verdict: APPROVE

## Findings resolved

1. **High - source lineage and merge proof were initially conflated.** The plan
   separately pins the behavior commit `5d4dfb2` for inventory and the merged
   main commit `a6f3bcf` for release authority.

2. **High - copying the Claude root marketplace version would corrupt the
   native Codex schema.** The plan classifies that source row but rejects direct
   copy. Codex version truth remains in `.codex-plugin/plugin.json` and generated
   repository facts.

3. **High - implementation must not precede the portability gate.** The plan
   freezes source, target, pathspecs, capability snapshot, and complete row
   treatments, then requires a passing classification stage before behavior
   edits.

4. **Medium - the target main advanced after #108 discovery.** The execution
   base is the fresh current main `7b429f7`; its five intervening commits touch
   only issue templates and have no write-set overlap.

5. **Medium - source execution would not prove installed Codex behavior.** The
   plan requires merged-main installation, enabled/version/path readback,
   invalid-Status behavior, no mutation, fresh-session discovery, rollback, and
   cleanup in an isolated VM 209 Codex home.

6. **Medium - the shared validator is specialized to another active port.**
   `scripts/port_contract.py validate` hardcodes the external-advisory contract
   refs, inventories, and evidence tag, so it cannot truthfully validate a
   second concurrent manifest. This port uses the generic initializer,
   source-verification and renderer, plus an exact cycle-specific pytest gate
   for authority, inventory, classification, lineage, and final evidence.

## Readiness

The source authority, exact refs, independent version lineage, validator
boundary, behavior and metadata treatments, tests, nonproduction host,
dirty-state isolation, installed proof, rollback, verification, and stop
conditions are decision-complete. No unresolved P0-P2 finding remains.
