# Worker And Result Manifest

The approved assignment row is the worker manifest. It binds assignment, dependencies, parent, role, profile, exact model and effort, context, writes, completion, and ordered fallback. The compiler turns it into one root-owned V2 launch specification.

Before strict work counts, the root validates the child's `session_meta` plus `turn_context`: canonical path, profile or agent type, model, effort, provider, effective permission, sandbox, and V2 mode. Requested fields, profile bytes, prompt text, self-report, and hooks are not identity evidence.

Each attempt returns `assignment-result.v1`; reviewers return its `reviewer-result.v1` extension. The root validates the attempt and path, role and profile, terminal status, summary, changed paths or explicit no-change, checks, typed findings, residual risk, reviewer dimensions, exclusions, denominator, arithmetic, verdict, and hard-stop flag.

Messages coordinate one attempt but do not complete it. `followup_task` restores the same nonterminal attempt on the same canonical path. Retry, remediation, and revalidation use a fresh attempt ID and fresh path after partial edits are classified as cleanup or carry-forward.

Writable attempts are enclosed by the lightweight root-owned workspace and Git audit. The root rejects out-of-scope paths, dirty overlap, worker Git commands, and changes to HEAD, branch, index, refs, config, or hooks. Concurrent writable attempts require native per-agent mutation attribution; otherwise they run sequentially with the root quiescent.

One bounded run record retains only the approved binding, validated runtime identity, typed outcomes, checks, findings, remediation count, and root decision. It does not copy Codex events, messages, transcripts, prompts, tool arguments, stdout, stderr, credentials, or raw model output.
