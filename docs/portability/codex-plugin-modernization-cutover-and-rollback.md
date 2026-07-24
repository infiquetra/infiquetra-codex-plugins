# Codex Plugin Modernization Cutover And Rollback

> Historical runbook: this records the completed July 2026 Team Execution-to-Verified Workflows
> cutover. It is non-current evidence and must not be used for the native Codex V2 release.

This is the operator runbook for the U8 package, profile, hook, and cache cutover. The machine record
is [codex-plugin-modernization-cutover.json](../validation/codex-plugin-modernization-cutover.json).
The general port contract remains
[claude-to-codex-plugin-port-runbook.md](claude-to-codex-plugin-port-runbook.md).

## Transaction Boundary

The active workflow identity changes atomically:

```text
before                                  after
------                                  -----
team-execution 2.3.0                    verified-workflows 1.0.0
saga 0.65.1              ----->         saga 0.75.17
no managed compute profiles             five marker-owned compute profiles
legacy state readable                   legacy state readable; canonical writes only
```

Never enable both workflow packages. Installed cache is a proof/runtime snapshot, not maintained
source. Run source validation and both isolated lanes before touching the real profile.

## Protected Pre-State

1. Capture marketplace, installed package/cache references, managed and unmanaged agent inventory,
   workflow state roots, hook definition/trust shape, and relevant config bytes in an ignored local
   bundle.
2. Set the bundle directory to `0700` and the archive to `0600`.
3. Record only relative path classes, versions, counts, and SHA-256 digests in committed evidence.
4. Validate that the bundle restores the captured shape before continuing.

Do not commit absolute paths, raw config or trust values, prompts, transcripts, environment values,
credentials, or rollback bytes.

## Isolated Gates

The clean-home lane must install all ten marketplace plugins, discover the canonical Saga and
Verified Workflows skills and hooks, and synchronize exactly five profiles from the pinned catalog
snapshot. Do not copy default-profile credentials. An authenticated isolated fresh task is optional;
record `not-run-no-isolated-auth` when no separate isolated authentication exists.

The seeded lane must reconstruct the old package, 25 old managed markers, unrelated user profiles,
and legacy state from protected or frozen fixtures. It must then prove:

- the old package is removed before the new package is enabled;
- 25 legacy profiles become exactly five canonical profiles while unrelated profiles are unchanged;
- legacy Saga state remains readable and new writes are canonical;
- package and profile rollback reproduce the exact pre-state digests.

## Real Profile Apply

Only the root thread performs these steps after source, full-suite, port-contract, clean-home, and
seeded-lane gates pass:

1. Verify the local rollback bundle digest and current pre-state digest.
2. Remove the retired installed plugin, refresh the configured marketplace, and install the three
   cachebuster releases through `codex plugin` commands.
3. Run the profile synchronizer with `--allow-real-profile`, the pinned catalog snapshot, and the
   exact expected pre-state digest. Preserve all unrelated profiles.
4. Read back exactly one active workflow plugin, the three target versions, five canonical profiles,
   no legacy managed profiles, and unchanged unrelated-profile digest.
5. Start a fresh authenticated Codex task and prove Saga and Verified Workflows discovery plus named
   model/effort selection. The running task that performed installation is not fresh-session proof.

## Rollback

On any failed apply or readback:

1. Stop using the new hooks.
2. Remove Verified Workflows and restore the old marketplace/config/cache bytes from the validated
   local bundle.
3. Restore exact managed-agent bytes and legacy markers; preserve unrelated files.
4. Reinstall Team Execution `2.3.0` and Saga `0.65.1` from the restored local marketplace.
5. Restart Codex and require exact marketplace, config, hook, package, profile, and state-root digest
   readback before declaring rollback complete.

Deleting the rollback bundle is a separate cleanup step after merged code, CI, and fresh-session
evidence are all durable.
