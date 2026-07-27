# U6 acceptance evidence — codex#54 lease-registry forward-compatibility

**Bundle:** `docs/validation/2026-07-26-lease-registry-forward-compat-acceptance.json`
(sha256 `01d8a3e68c01efab2b30c975423ca5597d06c898a411bdf592d8ee8b725518a8`)
**Verdict:** `overall_verdict: pass` — **14 / 14**
**Run at:** codex `ec523cc017e2f68716428ed6417e2194962d497b` (the merge commit of PR #60)
× claude `b464d090fccb59d0ff862f273902f1653f1d8835`

## Why this document exists (KTD7 / codex#57)

The port-contract evidence schema cannot express this run's command. Two facts from
`scripts/port_contract.py` constrain it:

- `:1236` — `if entry.get("cwd") != ".": errors.append(...)`. `cwd` is pinned to the literal `"."`.
- `:1196` — `evidence_keys` is a **closed** set (`evidence_id`, `unit`, `kind`, `artifact_path`,
  `artifact_sha256`, `argv`, `cwd`, `exit_code`, `recorded_at`, `repo_head`, plus optional
  `target_paths` / `target_tree_sha256`).

There is therefore no field in the entry able to hold this caveat, and inventing one fails
validation on an unknown key. The harness lives in **infiquetra-claude-plugins**, so the recorded
`argv` will not resolve from a checkout of this repository. That is honest and deliberate: codex#45
set the precedent that an unresolvable-but-true path beats a fabricated-but-valid one. codex#57
tracks the schema gap and is **not** fixed here.

The `argv` recorded in the manifest entry is the real command, reproduced below with its real paths.

## Reproduction

Both runtimes must be **clean detached worktrees at exact SHAs**. `require_clean_pinned` verifies
`HEAD == pin.sha` and refuses a dirty tree — it does **not** check out, and both primary trees are
dirty, so disposable worktrees are mandatory.

```bash
git -C <claude-repo> worktree add --detach /tmp/pin-claude b464d090fccb59d0ff862f273902f1653f1d8835
git -C <codex-repo>  worktree add --detach /tmp/pin-codex  ec523cc017e2f68716428ed6417e2194962d497b
export TMPDIR=$(mktemp -d)

env -u INFIQUETRA_FLEET_LEASE_ENFORCEMENT \
python3 /tmp/pin-claude/tools/run_cross_runtime_outcome_acceptance.py \
  --claude-repo /tmp/pin-claude --claude-sha b464d090fccb59d0ff862f273902f1653f1d8835 \
  --claude-saga-version 0.115.0 --claude-fleet-core-version 0.23.0 \
  --codex-repo /tmp/pin-codex --codex-sha ec523cc017e2f68716428ed6417e2194962d497b \
  --codex-saga-version 0.81.0+codex.20260726234500 \
  --codex-fleet-core-version 0.13.0+codex.20260726234500 \
  --output /tmp/acceptance.json
```

`env -u INFIQUETRA_FLEET_LEASE_ENFORCEMENT` is load-bearing, not hygiene: an acceptance run about
governed leases executed with lease enforcement disabled proves nothing. The session that produced
this bundle had `INFIQUETRA_FLEET_LEASE_ENFORCEMENT=off` set, and the child process was verified to
see it unset before the harness started.

**Do not read the stdout summary.** The harness prints `{"ok": true, "bundle_sha256": …}` on stdout
independently of the verdict — it printed exactly that on the pre-fix run that wrote
`overall_verdict: "fail"`. Read the bundle.

## Result — scenario by scenario against the committed baseline

Compared against the 12/14 baseline committed at `b11d2df3` on branch
`outcome/governed-execution-integrity` in infiquetra-claude-plugins,
`docs/validation/governed-execution-integrity/cross-runtime-acceptance.json`, whose sha256 was
re-verified as `c91eaa385f6f95919082912a93e3ec55bd9b764b9096c28d4303383c397f2b77` before comparing.

Compared **per scenario**, not by count — a count match can hide one regression offsetting one fix.

| Scenario | Baseline | Post-merge | Delta |
|---|---|---|---|
| `discovery-claude-created` | pass | pass | same |
| `discovery-codex-created` | pass | pass | same |
| `fleet-doctor-positions` | pass | pass | same |
| `handoff-claude-issued` | pass | pass | same |
| `handoff-codex-issued` | pass | pass | same |
| **`handoff-negatives-claude-issued`** | **fail** | **pass** | **FIXED** |
| **`handoff-negatives-codex-issued`** | **fail** | **pass** | **FIXED** |
| `legacy-import-refused` | pass | pass | same |
| `race-claude-first` | pass | pass | same |
| `race-codex-first` | pass | pass | same |
| `race-crash-after-effect` | pass | pass | same |
| `race-crash-before-effect` | pass | pass | same |
| `race-simultaneous` | pass | pass | same |
| `teardown-reclaim` | pass | pass | same |

**Regressions: none.** The two scenarios fixed are exactly the two the issue named, and both failed
for the same reason: `RegistryCorruptError: leases.<id>: unknown field(s): isolation` on the codex
read side.

## Why this ran after the merge, not before

This repository merges with merge commits — `d0982fe`, `f79f141`, and `74258be` are all
`Merge pull request …`, and PR #60 landed as `ec523cc`. `require_clean_pinned` pins an **exact**
SHA, so a bundle produced at the branch head `c05fed5` would describe a commit that never shipped.
Objective infiquetra-claude-plugins#639 clause 3 requires the *shipped* state proven, so U6 was
deliberately deferred until `ec523cc` existed.

## What this does and does not discharge

**Discharges** clause 3 of objective infiquetra-claude-plugins#639: cross-runtime acceptance is
green after the codex re-freeze.

**Does not discharge** clause 2 — a governed armed-hook Workflow run completing end to end. That
remains separately unevidenced and is untouched by this work. Objective #639 does not close on this
bundle alone.
