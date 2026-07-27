# Worker And Result Manifest

The approved assignment row binds its dependencies, role, profile, exact model and effort, write
paths, completion condition, and fallback.

The typed result is evidence, not authority. Only root validates it and releases dependencies.

Before work counts, root validates the child's runtime receipt. Each attempt then returns
`assignment-result.v1`; reviewers return `reviewer-result.v1`. Root validates identity, terminal
status, actual changed paths, checks, findings, residual risk, and reviewer arithmetic.

Changed paths must stay inside the assignment's approved write paths. Concurrent writers have
disjoint write sets; dependency-ordered writers may share a path. Only
`git-integration-operator` may run Git commands.

Messages coordinate an attempt but do not complete it. A retry, the single remediation, and the
single targeted recheck each use a fresh attempt ID and canonical path.
