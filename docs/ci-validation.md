# Adapter CI

`Adapter CI` runs on pull requests and pushes to `main`. Its single hosted Linux
job, `Adapter validation (Python 3.12)`, uses read-only repository permissions,
uv 0.13.6 and the existing lockfile at the declared Python floor. Replaced PR
runs cancel within this workflow; main pushes use independent run groups.

The gate checks changed-line whitespace, validates registered manifests and
inventory, exercises the quality runner's dry-run command, and runs
`python3 -m pytest` once through uv. Pytest retains the configured import mode
and all eight test paths in `pyproject.toml`; the dry run does not substitute for
the real suite. Test conditions and assertions remain repository-owned.

The adapter checkout includes history and tags because validation reads frozen
historical evidence. Port-oracle tests also require an upstream Git checkout.
CI fetches the exact frozen commit `b464d090fccb59d0ff862f273902f1653f1d8835`
from the historical upstream repository identity, verifies all five required
commit objects, and passes that checkout through `CODEX_PORT_SOURCE_REPO`.
No moving-branch fallback or installed plugin cache supplies the oracle.

uv's dependency cache is archived under the runner's temporary directory. It can
contain downloaded package data, metadata and wheels built from source; pruning
does not make it a downloads-only archive. Lockfile, platform, uv version and the
Python 3.12 policy distinguish entries. The setup action discovers its key's Python
identity before the later explicit test-interpreter install, so that key does not
attest the eventual interpreter patch. The environment, runtime installations and
uncached source oracle are recreated each run. Locked installs and all validation
commands execute regardless of cache hits. GitHub PR-ref isolation and the absence
of a privileged consumer bound reuse; this cache is not release evidence.

The job has a fifteen-minute deadline, with separate bounds for entrypoints and
pytest. Pytest reports slow cases and skip/failure summaries; its JUnit file is
retained for seven days even when the suite fails. Command failures propagate
to the job. No provider credentials or live model acceptance are configured.

This adds validation compute. Hosted success, cache reuse and useful timeout
headroom require measurement. A required-check policy is a separate operator
decision after the exact candidate is green; adding this workflow alone does
not change branch protection or publish releases.

Rollback removes this workflow and note. Preserve the existing test commands,
assertions and source inventory while repairing any prerequisite failure.

The baseline needs three owned migration-fixture corrections: select the intended
saved decision by identity, supply actual legacy state before asserting its
diagnostic, and provide deterministic read-only provider metadata for the static
proof. The proof still executes the real preview/refusal path and rejects any
unexpected provider invocation. Existing assertions remain; only the three
corresponding current-inventory hashes change. Runtime, vendored implementations,
profiles, manifests and frozen historical proof objects retain their bytes.
