from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


def load_saga() -> ModuleType:
    script = Path(__file__).parents[1] / "scripts" / "saga.py"
    spec = importlib.util.spec_from_file_location("saga_state_engine", script)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


saga = load_saga()


def quiet_git_runner(*_args: object, **_kwargs: object) -> SimpleNamespace:
    return SimpleNamespace(returncode=1, stdout="", stderr="")


def test_saga_state_uses_codex_root(tmp_path: Path) -> None:
    assert saga.STATE_DIR == Path(".codex/saga")
    assert saga.ORCHESTRATION_MODES == ("inline", "manual", "verified-workflow")

    result = saga.save(
        tmp_path,
        saga.Saga(
            saga_id="task-codex-port",
            kind="task",
            id="codex-port",
            lifecycle_phase="plan",
            orchestration_mode="team-execution",
            summary="Codex port state test",
        ),
        now=datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC),
        runner=quiet_git_runner,
    )

    envelope_path = Path(result["envelope_path"])
    state_path = Path(result["state_path"])
    assert envelope_path.is_file()
    assert state_path.is_file()
    assert ".codex/saga" in envelope_path.as_posix()
    assert ".claude" not in envelope_path.as_posix()

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["active_saga_id"] == "task-codex-port"
    assert state["sagas"]["task-codex-port"]["orchestration_mode"] == "verified-workflow"


def test_goal_continuation_requires_stable_goal_identifier() -> None:
    base = saga.Saga(saga_id="task-goal", kind="task", id="goal")
    assert saga.bind_goal_continuation(base, {"title": "not an id"}).continuation_mode == "turn"
    bound = saga.bind_goal_continuation(base, {"goal_id": "goal-123"})
    assert (bound.continuation_mode, bound.continuation_ref) == ("goal", "goal-123")


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"continuation_mode": "goal", "continuation_ref": ""}, "stable continuation_ref"),
        (
            {"continuation_mode": "goal", "continuation_ref": "goal-123"},
            "successful Goal tool result",
        ),
        ({"continuation_mode": "turn", "continuation_ref": "goal-123"}, "must not carry"),
        ({"identity_mode": "logical-role-attested"}, "protected role-result adapter"),
    ],
)
def test_save_rejects_unbacked_continuation_or_identity(
    tmp_path: Path, changes: dict[str, str], message: str
) -> None:
    candidate = saga.Saga(saga_id="task-invalid", kind="task", id="invalid")
    candidate = saga._replace(candidate, **changes)
    with pytest.raises(ValueError, match=message):
        saga.save(tmp_path, candidate, runner=quiet_git_runner)


def test_save_binds_new_goal_only_from_supplied_tool_result(tmp_path: Path) -> None:
    candidate = saga.Saga(
        saga_id="task-goal-save",
        kind="task",
        id="goal-save",
        continuation_mode="goal",
    )
    saga.save(
        tmp_path,
        candidate,
        runner=quiet_git_runner,
        goal_result={"goal_id": "goal-123"},
    )
    restored = saga.restore(tmp_path, "task-goal-save")
    assert restored is not None
    assert (restored.continuation_mode, restored.continuation_ref) == ("goal", "goal-123")


def test_goal_result_without_explicit_request_is_rejected(tmp_path: Path) -> None:
    candidate = saga.Saga(saga_id="task-goal-implicit", kind="task", id="goal-implicit")
    with pytest.raises(ValueError, match="explicit goal continuation request"):
        saga.save(
            tmp_path,
            candidate,
            runner=quiet_git_runner,
            goal_result={"goal_id": "goal-123"},
        )


@pytest.mark.parametrize("flag", ["--continuation-mode", "--continuation-ref", "--identity-mode"])
def test_generic_save_cli_rejects_attestation_flags(tmp_path: Path, flag: str) -> None:
    script = Path(__file__).parents[1] / "scripts" / "saga.py"
    value = "goal" if flag == "--continuation-mode" else "claim"
    result = subprocess.run(
        [sys.executable, str(script), "save", "--kind", "task", "--id", "claim", flag, value],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "unrecognized arguments" in result.stderr


def test_cli_rejects_source_only_backend(tmp_path: Path) -> None:
    script = Path(__file__).parents[1] / "scripts" / "saga.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "save",
            "--kind",
            "task",
            "--id",
            "bad-backend",
            "--orchestration-mode",
            "cc-workflows-ultracode",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "invalid choice" in result.stderr


def test_explicit_default_scalar_replaces_prior_value(tmp_path: Path) -> None:
    """A supplied default must not inherit the previous tick's non-default."""

    initial = saga.Saga(
        saga_id="task-default-scalar",
        kind="task",
        id="default-scalar",
        destination="merge",
        phase_status="complete",
    )
    saga.save(tmp_path, initial, runner=quiet_git_runner)

    args = saga.parse_args(
        [
            "save",
            "--kind",
            "task",
            "--id",
            "default-scalar",
            "--destination=plan-only",
            "--phase-status",
            "pending",
        ]
    )
    saga.save(
        tmp_path,
        saga._build_save_saga(args),
        explicit_scalars=saga._explicit_save_scalars(
            [
                "save",
                "--kind",
                "task",
                "--id",
                "default-scalar",
                "--destination=plan-only",
                "--phase-status",
                "pending",
            ]
        ),
        runner=quiet_git_runner,
    )

    restored = saga.restore(tmp_path, "task-default-scalar")
    assert restored is not None
    assert restored.destination == "plan-only"
    assert restored.phase_status == "pending"


def test_cli_rejects_complete_team_execution_without_ref(tmp_path: Path) -> None:
    script = Path(__file__).parents[1] / "scripts" / "saga.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "save",
            "--kind",
            "task",
            "--id",
            "no-ref",
            "--lifecycle-phase",
            "plan",
            "--phase-status",
            "complete",
            "--orchestration-mode",
            "team-execution",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "missing orchestration_ref" in result.stderr


def test_cli_allows_draft_team_execution_without_ref(tmp_path: Path) -> None:
    script = Path(__file__).parents[1] / "scripts" / "saga.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "save",
            "--kind",
            "task",
            "--id",
            "draft",
            "--lifecycle-phase",
            "plan",
            "--phase-status",
            "pending",
            "--orchestration-mode",
            "team-execution",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0


def _make_branch_saga() -> "saga.Saga":
    return saga.Saga(
        saga_id="issue-42",
        kind="issue",
        id="42",
        lifecycle_phase="work",
        summary="branch-refresh fixture",
    )


def test_save_refreshes_branch_on_later_save(tmp_path: Path) -> None:
    """``branch`` tracks the CURRENT git branch on EVERY save, not just the first (issue #480).

    Mirrors the ``/plan`` mints-on-``main`` then ``/work`` re-saves-on-branch lifecycle: the
    first save captures ``main``; a later save on the work branch must OVERWRITE it, not carry
    ``main`` forward through scalar merge.
    """

    def git_on(branch: str):
        def fake_git(args: list[str], **_kwargs: object) -> SimpleNamespace:
            if "--show-current" in args:
                return SimpleNamespace(returncode=0, stdout=f"{branch}\n", stderr="")
            return SimpleNamespace(returncode=0, stdout="abc1234\n", stderr="")

        return fake_git

    saga.save(
        tmp_path,
        _make_branch_saga(),
        now=datetime(2026, 6, 2, 14, 5, 10, tzinfo=UTC),
        runner=git_on("main"),
    )
    assert saga.restore(tmp_path, "issue-42").branch == "main"

    later = datetime(2026, 6, 2, 14, 12, 33, tzinfo=UTC)
    saga.save(tmp_path, _make_branch_saga(), now=later, runner=git_on("fix/pf-work"))
    assert saga.restore(tmp_path, "issue-42").branch == "fix/pf-work"


def test_save_empty_branch_does_not_clobber_stored_branch(tmp_path: Path) -> None:
    """A detached-HEAD / no-git save (empty ``git branch --show-current``) must NOT wipe a
    previously-stored branch — the ``git["branch"]`` non-empty guard preserves carry-forward
    (issue #480, R2)."""

    def fake_git_on_branch(args: list[str], **_kwargs: object) -> SimpleNamespace:
        if "--show-current" in args:
            return SimpleNamespace(returncode=0, stdout="fix/pf-work\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="abc1234\n", stderr="")

    def fake_git_detached(args: list[str], **_kwargs: object) -> SimpleNamespace:
        if "--show-current" in args:
            return SimpleNamespace(returncode=0, stdout="\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="def5678\n", stderr="")

    saga.save(
        tmp_path,
        _make_branch_saga(),
        now=datetime(2026, 6, 2, 14, 5, 10, tzinfo=UTC),
        runner=fake_git_on_branch,
    )
    assert saga.restore(tmp_path, "issue-42").branch == "fix/pf-work"

    later = datetime(2026, 6, 2, 14, 12, 33, tzinfo=UTC)
    saga.save(tmp_path, _make_branch_saga(), now=later, runner=fake_git_detached)
    assert saga.restore(tmp_path, "issue-42").branch == "fix/pf-work"


def test_save_on_default_branch_preserves_stored_work_branch(tmp_path: Path) -> None:
    """Once a real work branch is recorded, a later save made back on ``main`` must NOT
    overwrite it (issue #480). ``ship_ceremony.py``'s ``checkout_main`` progress-save runs on
    ``main`` right before ``branch_delete`` still needs the work branch — this mirrors that
    exact sequence and guards against downgrading the real branch to the default one.
    """

    def git_on(branch: str):
        def fake_git(args: list[str], **_kwargs: object) -> SimpleNamespace:
            if "--show-current" in args:
                return SimpleNamespace(returncode=0, stdout=f"{branch}\n", stderr="")
            return SimpleNamespace(returncode=0, stdout="abc1234\n", stderr="")

        return fake_git

    saga.save(
        tmp_path,
        _make_branch_saga(),
        now=datetime(2026, 6, 2, 14, 5, 10, tzinfo=UTC),
        runner=git_on("feat/pf-throwaway-345"),
    )
    assert saga.restore(tmp_path, "issue-42").branch == "feat/pf-throwaway-345"

    later = datetime(2026, 6, 2, 14, 12, 33, tzinfo=UTC)
    saga.save(tmp_path, _make_branch_saga(), now=later, runner=git_on("main"))
    assert saga.restore(tmp_path, "issue-42").branch == "feat/pf-throwaway-345"


def test_save_refreshes_head_and_last_commit_on_later_save(tmp_path: Path) -> None:
    """``head_sha``/``last_commit_sha`` refresh on EVERY save (the #480 follow-up). SHAs have
    no default-branch downgrade concern, so a plain non-empty guard suffices."""

    def git_at(short: str, full: str):
        def fake_git(args: list[str], **_kwargs: object) -> SimpleNamespace:
            if "--show-current" in args:
                return SimpleNamespace(returncode=0, stdout="feat/work\n", stderr="")
            if "--short" in args:
                return SimpleNamespace(returncode=0, stdout=f"{short}\n", stderr="")
            return SimpleNamespace(returncode=0, stdout=f"{full}\n", stderr="")

        return fake_git

    saga.save(
        tmp_path,
        _make_branch_saga(),
        now=datetime(2026, 6, 2, 14, 5, 10, tzinfo=UTC),
        runner=git_at("aaa1111", "aaa1111ffff"),
    )
    first = saga.restore(tmp_path, "issue-42")
    assert first.head_sha == "aaa1111"
    assert first.last_commit_sha == "aaa1111ffff"

    later = datetime(2026, 6, 2, 14, 12, 33, tzinfo=UTC)
    saga.save(tmp_path, _make_branch_saga(), now=later, runner=git_at("bbb2222", "bbb2222ffff"))
    second = saga.restore(tmp_path, "issue-42")
    assert second.head_sha == "bbb2222"
    assert second.last_commit_sha == "bbb2222ffff"


def test_cli_accepts_complete_verified_workflow_with_plan_ref(tmp_path: Path) -> None:
    plan = tmp_path / "docs" / "plans" / "repair.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("# Repair\n\n## Workflow Structure\n\nroles\n", encoding="utf-8")
    script = Path(__file__).parents[1] / "scripts" / "saga.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "save",
            "--kind",
            "task",
            "--id",
            "ready",
            "--lifecycle-phase",
            "plan",
            "--phase-status",
            "complete",
            "--plan-path",
            "docs/plans/repair.md",
            "--orchestration-mode",
            "verified-workflow",
            "--orchestration-ref",
            "docs/plans/repair.md#workflow-structure",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
