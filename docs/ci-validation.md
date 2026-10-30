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

Only uv's download cache is archived, under the runner's temporary directory;
lockfile, platform, interpreter and uv policy distinguish cache entries. The
environment, tool installations and source checkouts are recreated each run.
Installs and validation commands execute regardless of cache hits.

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
