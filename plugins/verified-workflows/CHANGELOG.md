# Changelog - verified-workflows

All notable changes to this plugin are documented here.

## [1.0.0] - Unreleased

### Added

- Establish the unpublished Verified Workflows Codex package identity.
- Add `run` and `appsec-audit` skill surfaces.
- Define the root-owned workflow DAG and compatibility boundaries.

### Migration

- Adapt behavior from the upstream `team-execution` lineage without claiming byte parity.
- Read exact legacy vocabulary through fleet-core and write only canonical Verified Workflows
  vocabulary.
- Keep Team Execution `2.3.0` as the sole active marketplace package until U8 cutover proof.
