---
name: handoff
description: Route durable Infiquetra lifecycle artifacts into mission-control prepared issue drafts.
---

# Handoff

Use this when the user wants another team, agent team, or later session to pick up work from an
Infiquetra lifecycle artifact.

## Boundary

`saga` owns the handoff moment:

- select the durable source artifact or active pointer;
- infer lifecycle phase and handoff maturity;
- capture why the work is being handed off, blockers, open questions, target team, and target
  repository when known;
- route to `mission-control`.

`mission-control` owns the issue artifact:

- issue body sections;
- prepared draft markdown and JSON sidecar;
- readiness checks;
- labels, project fields, board placement, and GitHub mutation;
- create-after-confirmation mutation plan.

Do not copy SDLC issue templates into this skill.

## Workflow

1. Prefer an explicit source path or URL from the command arguments.
2. If no source is explicit, inspect `.codex/saga/state.json` and durable docs.
3. Build the envelope:

   ```bash
   python3 plugins/saga/scripts/handoff_envelope.py \
     --source docs/plans/example.md \
     --target-team Asgard \
     --target-repo infiquetra-codex-plugins
   ```

4. If the helper finds no source, ask for one.
5. If multiple durable artifacts are plausible, ask the user to choose.
6. Route with the envelope's `recommended_skill` (`mission-control:issues`) and
   `handoff_payload`.
7. Review the prepared issue draft before mutation.
8. Use `issue create-prepared` only after mission-control renders a fresh
   mutation plan and the user confirms that exact plan.

## Maturity

- `docs/ideation/` -> `idea-ready`
- `docs/product-reviews/` -> frontmatter `maturity` when present, otherwise `experiment-ready`
- `docs/brainstorms/` -> `requirements-ready`
- `docs/specs/` -> `requirements-ready`
- `docs/plans/` or `docs/reviews/` -> `plan-ready`
- `docs/work-sessions/` or branch refs -> `resume-ready`
- `platform-specs/06-service-implementations/` or `platform-specs/06-feature-modules/` -> `requirements-ready`
- explicit preserve/defer language -> `deferred-context` when the user says execution should wait

## Recipient Guidance

Prepared issues must be self-contained for recipients without `saga`.

When a recipient does have `saga`, the issue may suggest:

- `saga:plan` for `idea-ready` or `requirements-ready`;
- `saga:plan` for `experiment-ready` scoped experiment work;
- `saga:work` for `plan-ready` or `resume-ready`.

Do not suggest `saga:loop` for normal team handoff.
