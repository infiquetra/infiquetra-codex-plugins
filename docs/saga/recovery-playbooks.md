# Recovery Playbooks

Use these when a Saga thread stalls, looks inconsistent, or cannot route cleanly.

Recovery starts with inspection and owner-state reconciliation. Manual repair is last resort.

## Recovery Order

| Order | Action | Why |
|---|---|---|
| 1 | Run `python3 plugins/saga/scripts/saga.py scan` | Find candidate local Saga threads. |
| 2 | Restore the likely thread | Read the latest cached lifecycle state. |
| 3 | Reconcile with owners | Git, GitHub, deploy state, and journal records beat cache. |
| 4 | Inspect durable artifacts | Plans, reviews, work sessions, and QA docs explain what should happen next. |
| 5 | Rerun the correct command | Prefer normal Saga routing over editing state. |
| 6 | Repair only if necessary | Manual state edits are last-resort and must not bypass gates. |

## Stale cached Saga state

| Symptom | Safe recovery |
|---|---|
| Cached branch no longer exists | Check live git branches and PR state, then save a new tick from the correct branch. |
| Cached SHA is behind the worktree | Trust git, not the cache; rerun review if commits changed since reviewed SHA. |
| Cached `lifecycle_phase` says `work`, but PR is merged | Treat git/GitHub as authoritative and route to `saga:qa` or `saga:retro`. |

## Malformed handoff context

| Symptom | Safe recovery |
|---|---|
| Handoff issue lacks source context | Re-run `saga:handoff` from the source artifact, then use `mission-control:issues` to prepare a corrected draft. |
| Handoff maturity looks wrong | Recompute from artifact path or Saga `lifecycle_phase`; do not edit issue labels blindly. |
| Receiver cannot execute without Saga | Add source summary and artifact links through Mission Control's prepared issue flow. |

## Missing durable artifact

| Symptom | Safe recovery |
|---|---|
| Saga points to a missing plan | Search `docs/plans/`, inspect branch history, and re-run `saga:plan` if the plan never existed. |
| Review artifact missing | Run `saga:doc-review` before `saga:work`; same-session memory is not enough after a resume. |
| Work-session missing | Write a concise work-session from git diff, checks, and commits before handing off. |

## Manual repair warning

Manual edits to `.codex/saga/` are allowed only when normal restore/rerun paths cannot reconstruct the thread.

Do not use manual repair to skip `saga:doc-review`, `saga:code-review`, `saga:qa`, `mission-control` mutation previews, or `deploy` confirmation gates.

