---
name: deploy
description: Promote an Infiquetra repository by minting a policy-compliant deployment tag. Use for nonprod, staging, production, and rollback tag-promotion flows.
---

# Deploy

Promote an Infiquetra repository through tag-promotion deployment.

## Procedure

1. Read `../deploy-state/SKILL.md`.
2. Confirm the target repository resolves to `github.com/infiquetra/*`.
3. Confirm the target environment is `nonprod`, `staging`, or `production`.
4. Preview the tag, source ref, confirmation id, and workflow URL before mutation.
5. Use `../../scripts/mint_tag.py` for deterministic tag naming.
6. For any non-dry-run promotion, require `--confirm-plan` matching the previewed
   repo, tag, and ref. Do not push a tag from skill text alone.

## Dry Run

```bash
python3 plugins/deploy/scripts/mint_tag.py \
  --env nonprod \
  --version 1.2.3 \
  --repo infiquetra/example \
  --dry-run
```

## Mutation

Run the same command without `--dry-run` only after the operator confirms the
exact printed plan id:

```bash
python3 plugins/deploy/scripts/mint_tag.py \
  --env staging \
  --version 1.2.3 \
  --repo infiquetra/example \
  --confirm-plan <printed-confirmation-id>
```
