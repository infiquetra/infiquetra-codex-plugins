---
name: select-agent
description: Show and launch the five maintained Infiquetra Codex agent profiles. Use when the operator asks to list, choose, select, or start a review, test, scan, or monitor agent, or wants the pre-spawn agent-picker experience before using /agent to switch threads.
---

# Select Agent

Present an explicit profile catalog, launch the chosen named profile in fresh context, and report the
runtime-observed role, model, and effort. This is native interactive delegation, not a Verified
Workflow gate.

## Select

1. Read the five TOMLs under `../../agents/`. Treat those files as the source of truth for name,
   description, model, effort, and configured sandbox intent.
2. Render one compact table in this order: `review_max`, `review_high`, `test_medium`, `scan_low`,
   `monitor_low`. Include purpose, model, effort, and permission intent.
3. If the operator already named a profile, continue immediately. Otherwise ask for exactly one
   profile choice and wait.
4. Reject names outside the five maintained profiles. Do not silently substitute a built-in or a
   different model tier.

## Launch

1. Require an active spawn surface that accepts a named agent type plus model and effort metadata.
   When the surface lacks those fields, stop and direct the operator to run:

   ```bash
   python3 plugins/fleet-core/scripts/codex_v1_catalog.py install
   ```

   Then require a Codex restart and a fresh session because the catalog and tool schema are pinned at
   startup.
2. Spawn the chosen profile through the active native `spawn_agent` tool using its exact profile name.
   Keep the child fresh: use `fork_context=false` on the stable V1 schema, or `fork_turns="none"` when
   a host wrapper exposes that equivalent spelling.
3. Let the profile own model and effort. Pass direct overrides only when the operator explicitly asks
   for them.
4. Give the child one bounded, self-contained task. Do not attach Verified Workflow receipt or gate
   requirements unless the operator explicitly selected that workflow mode.

## Verify

Read the host-issued spawn activity or child turn context. Report the role, model, and effort as
observed only when that runtime evidence contains them. On a mismatch, stop the child before assigning
more work and report requested versus observed values. Never use child self-report as runtime proof.

After launch, tell the operator that `/agent` switches among the root and spawned agent threads; it
does not open the pre-spawn catalog.

## Boundaries

- Forcing Sol and Terra to V1 may alter Ultra automatic delegation. Do not use Ultra under this
  workaround unless a separate runtime test proves it.
- A profile's sandbox value is configured intent. Verify the effective child permission boundary
  separately when it matters.
- Do not edit installed agent TOMLs or plugin cache copies. Change the maintained source profiles and
  synchronize them through the repository tooling.
