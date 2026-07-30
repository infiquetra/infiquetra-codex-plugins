# Workflow Protocol

`## Workflow Contract` is the operator-approved execution surface. It contains assignments, blocking
checks, and optional non-gating external actions.

## Assignments

The exact columns are:

```text
id | depends | role | profile | writes | completion | fallback
```

- `id` and `depends` form one acyclic graph.
- Every row is executable by a managed role; root rows are forbidden.
- `profile` must be explicit. Model and effort are derived from the maintained profile.
- `writes` is `none` or a repository-relative allowlist. Read-only profiles cannot write.
- Concurrent writers must have disjoint write sets. Shared paths require dependency ordering or one
  combined assignment.
- Only `git-integration-operator` may own Git commands, and its completion condition must include the
  final `git diff --name-only` validation.
- `fallback` is `none` or an ordered `profile@condition` list within the role's allowed profiles and
  permission boundary.

Every assignment launches as a direct child of root with `fork_turns=none`. The independent
reviewer is therefore a sibling of the implementation workers rather than their descendant.

## Blocking Checks

The exact columns are:

```text
id | owner | after | command-or-proof | blocking | failure
```

Every owner and `after` value names an executable assignment. Root cannot own a check. At least one
check is blocking, including one reviewer-assurance check covering the independent reviewer.

## External Actions

The exact columns are:

```text
id | purpose | provider | model | egress | context | sensitivity | cost |
writes-or-artifact | requiredness | authority
```

Use `External actions: []` when none are approved. Authority is always `non-gating`; a material route,
cost, egress, context, or write change returns to operator approval.

## Compilation And Approval

The compiler validates the tables and binds the canonical contract, role registry, role lenses,
profiles, reviewer mandates, and approved plan revision. A new assignment, write set, role, profile,
reviewer, fallback, or material scope change invalidates approval.

Profile resolution and requested launch fields are not runtime proof. Root accepts an assignment only after
`session_meta` and `turn_context` confirm the approved path, profile, model, effort, provider,
permission profile, sandbox, and V2 mode.
