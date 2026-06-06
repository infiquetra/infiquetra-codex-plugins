---
name: deploy-status
description: Show Infiquetra deployment status and version drift across nonprod, staging, and production.
---

# Deploy Status

Report deployment state for an Infiquetra repository.

## Procedure

1. Read `../deploy-state/SKILL.md`.
2. Resolve the repository through `../../scripts/query_deployments.py`.
3. Report the latest `nonprod`, `staging`, and `production` deployment refs.
4. Strip environment prefixes when comparing versions.
5. Call out drift, missing environments, and the GitHub Actions workflow URL.

```bash
python3 plugins/deploy/scripts/query_deployments.py --repo infiquetra/example
```
