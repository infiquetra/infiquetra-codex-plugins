# Validator Evidence State

A selected validator ends in exactly one state:

- `pass`: required command/evidence contract succeeded;
- `warn`: optional signal needs attention but is not a hard failure;
- `hard-fail`: validator found a blocking condition;
- `blocked`: required tool, input, permission, or evidence is unavailable;
- `skipped-by-config`: an explicitly disabled non-required validator;
- `not-applicable`: the step is not a validator.

The Workflow Structure carries `validator_required` and `validator_disabled` explicitly. Reviewer
and root rows use `n/a`. A required validator must report `pass`; `warn` is advisory only for an
optional validator. `skipped-by-config` is valid only when `validator_disabled=true`, and required
plus disabled is invalid before execution.

Required evidence absence is `blocked`, never an implied pass. A missing required tool includes
setup guidance and blocks until the root resolves or explicitly replans the workflow. A validator
cannot be both required and disabled.

Validator evidence is typed and digest-bound. It records the logical role, role digest, declared
command or target, exit status, protected evidence references, findings, and closed gate status.
Tester and scanner claims derive their argv, tool, exit, and status from one-to-one protected
command-output records; a subject, snapshot, prose claim, or caller-supplied success flag is not
command evidence. Command-output records retain hashes and sizes plus a typed deterministic stdout
projection, never raw streams. A deterministic validator also binds the pinned argv,
implementation and schema digests, repository-root cwd, timeout, output ceiling, and no-write
workspace/Git-control audit. Required monitor/deploy evidence is `blocked` until an authenticated
observation adapter exists; a non-required monitor/deploy step may emit only advisory `warn`.
A generic child or protocol fixture is not validator evidence.

Only the root can verify evidence, authorize reruns, apply changes, or decide completion.
