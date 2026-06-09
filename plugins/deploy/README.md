# deploy

Deployment commands for Infiquetra repositories that use tag-promotion workflows.

Deploy participates in the Saga family after readiness, QA, or hotfix routing
calls for deployment mutation. The full lifecycle guide is
`../../docs/saga/README.md`.

## Codex Skills

- `deploy` previews or pushes `nonprod`, `staging`, `production`, and rollback tags.
- `deploy-status` reports environment status and version drift.
- `deploy-notes` previews release notes for a candidate range.
- `deploy-hotfix` prepares hotfix tags and evidence.

## Guardrails

- Mutating commands must resolve the target repository to `github.com/infiquetra/*`.
- Dry runs never push tags.
- All non-dry-run tag pushes require `--confirm-plan` matching the printed repo,
  tag, and ref.
- Long-lived policy is linked from the Infiquetra context library, especially ADR-0004.
- Forward promotions refuse snapshots marked with `unhealthy-v<version>` unless an explicit
  audited override is supplied.
- If no version is supplied, nonprod infers from the latest `v*` snapshot, staging infers from
  current nonprod, and production infers from current staging.

## Helpers

```bash
python3 plugins/deploy/scripts/mint_tag.py \
  --env nonprod \
  --version 1.2.3 \
  --dry-run
```

```bash
python3 plugins/deploy/scripts/query_deployments.py --repo campps-service
```
