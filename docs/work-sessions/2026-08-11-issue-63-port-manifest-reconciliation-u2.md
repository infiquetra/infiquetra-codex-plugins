# 2026-08-11 — Issue 63 port-manifest reconciliation through U2

Branch `fix/issue-63-port-manifest-reconciliation`, based on reviewed plan parent `43b1847`.
Work stops after U2 for independent Saga code review; U3 evidence, tags, publication, pull-request,
and merge work have not started.

## Completed units

U1a added the version-2 reconciliation substrate in `3f7c7a5`. U1b initialized and passed the
active self-host gate in `99cfdf3`. The active manifest uses the existing capability schema
`docs/validation/codex-runtime-capability-snapshot.schema-r4.json`; this is the implementation-time
correction from the stale schema path in the original plan, and no schema was added or changed.

The corrected plan preserves the issue 57 version-1 manifest and regression test instead of
migrating them. Commit `d8abf4e` prospectively rebound the active issue 63 manifest to corrected plan
digest `7ff974bf7d293e170c30ff79cef9b52f6dbfccc7c9a55e52e1508582c690c4e7` and bound the original review
and independent re-review exactly once. The generated classification was rendered and validated but
remained byte-identical because it does not display plan or review digests, so Git recorded the three
changed authority files rather than an artificial classification edit.

U2 commit `745774a` added only the declared-source checkout resolver and focused tests. It honors
`CODEX_PORT_SOURCE_REPO` before Git-common-directory sibling discovery, verifies normalized GitHub
origin and exact source `HEAD`, and containment-checks relative harness paths. Evidence artifacts and
`repo_head` remain Codex-owned. Commit `40c5dce` immediately updated the active reconciliation
rationale, rendered the classification, and passed classification validation before any further
work.

The issue 54 and issue 57 manifests and regression tests retain their pre-U2 SHA-256 digests. No
historical tag was created or backfilled.

## Checks

| Check | Result |
|---|---|
| Corrected authority cardinality and explicit classification validation | Passed |
| Exact disposable Claude checkout origin, `HEAD`, and contained harness proof | Passed at `b53827bb055e08ccc6aa547cade04aedf4385456` |
| Focused Ruff check and `git diff --check` | Passed |
| Focused port-contract and historical regression tests | `90 passed` |
| Repository plugin validation | Failed: U3-owned legacy-workflow digests for `scripts/port_contract.py` and `tests/test_port_contract.py` drifted, and the tracked U4 runtime proof is stale |
| Full suite in the existing repository virtual environment | Completed with 9 failures: three stale U1b capability-snapshot/0.147 bindings and six U3-owned legacy-inventory/runtime-proof assertions |
| Plain system-Python full-suite attempt | Collection stopped because that interpreter lacks Pillow; no dependency was installed |

The focused historical tests used the preserved ordinary Claude checkout because it contains the
older issue 54 and issue 57 commits. The issue 63 resolver proof used only the disposable exact-target
checkout at `/tmp/issue-63-claude-source.ugUwXG`.

## Boundary

The resolver behavior and active issue 63 classification gate are complete and current. The
repository-wide failures cannot be repaired inside reviewed U2: the corrected plan assigns the
legacy-workflow inventory and validator binding to U3, while the stale capability snapshot bindings
are outside the U2 file list and are not assigned to an implementation unit. Expanding either area
before independent review would violate the corrected boundary.

Next step: run independent Saga code review over the branch through U2 and resolve the recorded plan
constraint before authorizing U3.
