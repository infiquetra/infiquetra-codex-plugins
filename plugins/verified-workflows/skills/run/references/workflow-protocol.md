# Workflow Protocol

`## Workflow Contract` is the one operator-editable execution surface. It contains three compact tables and no plugin-owned runtime task tree.

## Assignments

The exact columns are:

```text
id | depends | parent | role | profile | model | effort | context | writes | completion | fallback
```

- `id` and `depends` form one acyclic graph.
- `parent` is `root`, a dependency ancestor, or bootstrap-only `fresh-root:<same-id>` for an independent read-only reviewer.
- Root rows use a reserved `root ...` role, `profile=root`, and `context=root`.
- Delegated rows use one maintained role ID and one of `review_max`, `review_high`, `work_high`, `test_medium`, `scan_low`, or `monitor_low`.
- `model` and `effort` must exactly match the selected profile. Ultra is root-only.
- Delegated `context` is `none` or `turns:<positive-int>` and compiles to V2 `fork_turns`.
- `writes` is `none` or a comma-delimited repository-relative allowlist. Read-only profiles cannot write; delegated rows cannot target Git metadata or own Git commands.
- Concurrent assignments cannot own equal, ancestor, or descendant write paths.
- `fallback` is `none` or an ordered `profile@condition` list. A fallback must remain inside the role's allowed profiles and preserve workspace and external boundaries.

## Blocking Checks

The exact columns are:

```text
id | owner | after | command-or-proof | blocking | failure
```

Every `after` value names an assignment. At least one check is blocking, and one blocking reviewer-assurance check must cover at least one `fresh-root` independent reviewer. Checks are root decisions; model messages cannot release them.

## External Actions

The exact columns are:

```text
id | purpose | provider | model | egress | context | sensitivity | cost |
writes-or-artifact | requiredness | authority
```

Use the literal `External actions: []` when no external action is approved. Otherwise every field is required, context is `none` or a comma-delimited repository-relative allowlist, requiredness is `best-effort` or `required`, and authority is exactly `non-gating`. External actions remain under Saga's approval, egress, provider, and root-adjudication lifecycle.

## Compilation And Approval

The compiler validates the three tables, sorts non-semantic sets and rows, and produces one canonical contract digest. A separate authority digest binds the role registry, selected role-lens bytes, generated profile bytes, and exact reviewer mandate roster. The approval binding covers both digests plus the explicit approved plan revision. Whitespace, row order, and unordered-list order do not alter the contract digest; authority, ownership, graph, profile, model, effort, context, fallback order, check, external-action, registry, lens, profile-byte, or mandate changes invalidate approval.

The compiler emits root-owned launch specifications only. It does not create intents, subjects, snapshots, receipts, barriers, retries, runtime status, or a second executable DAG. Codex V2 remains authoritative for hierarchy, liveness, messages, waits, interruption, and restoration.

Requested launch fields are not proof. Before accepting strict work, the root validates the exact agent path, profile or agent type, model, effort, provider, effective permission, and V2 mode from `session_meta` plus `turn_context`. Mismatch fails visibly. The root alone integrates changes, runs Git, releases checks, records remediation, and decides completion.
