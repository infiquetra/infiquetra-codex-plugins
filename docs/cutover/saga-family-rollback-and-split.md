# Saga-Family Rollback And Split Criteria

Verified: 2026-07-11

Partial replacement activation is not a successful merge state. A mergeable
cutover must complete the full Saga-family cutover: active plugin roots,
marketplace entries, validator expectations, baseline docs, migration rows, and
proof evidence must all agree on the same ten-plugin inventory.

## Successful Cutover State

The only successful active state is:

- Present plugin roots: `saga`, `deploy`, `mission-control`,
  `verified-workflows`, `home-lab-ops`, `python-toolkit`, `unifi`, `test-suite`,
  `fleet-core`, and `discord-identity-assets`.
- Absent active plugin roots: the prior SDLC, document-review, and Team Execution plugin roots.
- Marketplace inventory: exactly the ten present plugin roots.
- Default validation: `python3 scripts/validate_codex_plugins.py` passes.
- Cutover validation: `python3 scripts/validate_codex_plugins.py --mode cutover`
  passes.
- Proof: `docs/validation/saga-family-codex-proof.md` and
  `docs/validation/saga-family-codex-proof.schema.json` describe an isolated
  profile where the prior skills are absent and the Saga namespace proof passes.

## Rollback Path

Use rollback when any gate fails after active replacement has been attempted.

1. Stop using the failed repo-managed marketplace entry.
2. Verify the protected ignored rollback bundle digest, then restore its exact marketplace,
   config, hooks, agent profiles, legacy workflow state, and installed cache bytes.
3. Reinstall Team Execution `2.3.0` from the restored local marketplace, remove the failed
   Verified Workflows install, and restart Codex.
4. Confirm the restored file and inventory hashes match the recorded pre-state exactly.
5. Record the failed gate, proof run id, and fix target before another cutover attempt.

Rollback does not mean editing installed cache copies as source. Cache-backed
content remains installed state, not maintained source for this repository.

## Split Criteria

Split the work only when the branch can remain non-activating preparatory work.
Acceptable split branches may add source baselines, capability maps, target
fixtures, plugin roots that are not active marketplace entries, tests, or proof
scripts. They must not remove the old active roots, flip the default validator,
or publish a marketplace inventory that mixes old active plugins with only part
of the Saga-family replacement.

Do not merge a split branch as active cutover unless it also satisfies the
successful cutover state above.

## Operator Migration Boundary

The migration source of truth is
`docs/portability/saga-family-known-use-inventory.md`. Prior SDLC operations
route to `mission-control:*`, prior document-review operations route to
`saga:doc-review` or `saga:spec`, GitHub issue mutation routes to
`mission-control:issues`, and reviewer consensus escalation routes to
`verified-workflows:run`.
