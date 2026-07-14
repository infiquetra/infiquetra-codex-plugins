# Plan review: Mission Control assign-to-Mimir Codex port

Decision: APPROVE

The plan is bounded to one released canonical delta and preserves the repository's authority split. The behavior-bearing script and fixtures must match Claude commit `9adb971`; Codex-only differences are limited to `.codex-plugin`, `.codex` state paths, packaged script locations, existing preview/confirmation and target-allowlist controls, version lineage, and generated inventory.

The specialized `port_contract.py validate` constants cannot truthfully validate a second concurrent contract. Bootstrapping with its generic `init` path plus an exact focused test is acceptable for this cycle because it keeps the historical sealed contract unchanged and creates a reproducible blocking classification gate for every new source row. The test must fail on ref, inventory, treatment, target, or evidence drift.

Required review checks:

- Compare callable behavior and fixture coverage, not whole-file bytes.
- Reject any Codex-only credential, label, coverage, authority, or mutation semantic.
- Preserve Codex target allowlist and confirmation behavior outside this command.
- Require installed-cache execution and a fresh-thread discovery boundary after merge.
