"""Tests for the OutcomeOrchestrator dispatcher seam (U4).

Pins R5 (single dispatcher seam, HALT-not-degrade receipt), R6 (verified-workflow is the first real
backend), and R23 (a backend that cannot run halts visibly, never a silent substitute) — plus the
team_emitter wiring (R5) and integration with the U3 reconcile loop.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "plugins" / "saga" / "scripts"
TEAM_REF = "docs/plans/x.md#workflow-structure"


def _load(name: str) -> ModuleType:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


D = _load("outcome_dispatcher")
ES = _load("execution_spec")
OUTCOME = _load("outcome")
STORE = _load("outcome_store")


def _req(
    backend: str,
    *,
    outcome_id: str = "ship-x",
    subplot_id: str = "build",
    orchestration_ref: str = "",
    repo_root: Path = Path("."),
) -> Any:
    return SimpleNamespace(
        outcome_id=outcome_id,
        subplot_id=subplot_id,
        title="Build the thing",
        backend=backend,
        repo_root=repo_root,
        orchestration_ref=orchestration_ref,
    )


def _write_team_ref(repo_root: Path) -> str:
    plan = repo_root / "docs" / "plans" / "x.md"
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text("# X\n\n## Workflow Structure\n\nroles\n", encoding="utf-8")
    return TEAM_REF


def _launch_ack(req: Any) -> dict[str, str]:
    return {
        "ack_kind": "launched",
        "dispatch_ack_ref": f"protected:{req.dispatch_intent_id}",
        "leaf_saga_id": f"leaf-{req.outcome_id}-{req.subplot_id}",
        "producer_kind": "verified-workflow",
        "run_identity": f"run-{req.outcome_id}",
        "dispatch_intent_id": req.dispatch_intent_id,
        "outcome_id": req.outcome_id,
        "subplot_id": req.subplot_id,
        "backend": req.backend,
    }


# --------------------------------------------------------------------------- dispatch (R5/R6)


def test_dispatch_prepares_but_does_not_claim_launch(tmp_path: Path) -> None:
    ref = _write_team_ref(tmp_path)
    out = D.dispatch(_req("verified-workflow", orchestration_ref=ref, repo_root=tmp_path))
    assert out["status"] == "prepared"
    assert out["backend"] == "verified-workflow"
    assert out["orchestration_ref"] == ref
    assert out["proposed_leaf_saga_id"] == "leaf-ship-x-build"
    assert "return_channel" not in out


def test_dispatch_team_execution_without_ref_halts() -> None:
    out = D.dispatch(_req("verified-workflow"))

    assert out["status"] == "halt"
    assert out["receipt"]["backend"] == "verified-workflow"
    assert "missing orchestration_ref" in out["receipt"]["reason"]


def test_dispatch_team_execution_invalid_ref_halts(tmp_path: Path) -> None:
    out = D.dispatch(
        _req(
            "verified-workflow",
            orchestration_ref="docs/plans/does-not-exist.md#team-structure",
            repo_root=tmp_path,
        )
    )

    assert out["status"] == "halt"
    assert "orchestration_ref target does not exist" in out["receipt"]["reason"]


def test_dispatch_inline_is_available() -> None:
    assert D.dispatch(_req("inline"))["status"] == "prepared"


@pytest.mark.parametrize(
    # The host-dependent backends are unavailable under the conservative DEFAULT_AVAILABLE floor
    # (inline / verified-workflow / manual). `manual` is now always-available (U9), so it dispatches.
    "backend",
    ["fork", "subagent", "cc-workflows-ultracode", "goal"],
)
def test_dispatch_unavailable_backend_halts_not_substitutes(backend: str) -> None:
    # R5/R23: a chosen-but-unavailable backend HALTS with a visible receipt — never a silent inline.
    out = D.dispatch(_req(backend))
    assert out["status"] == "halt"
    receipt = out["receipt"]
    assert receipt["backend"] == backend
    assert receipt["kind"] == "halt"
    assert "HALT" in receipt["reason"] and "substitute" in receipt["reason"]
    assert receipt["available"] == list(D.DEFAULT_AVAILABLE)


def test_dispatch_unknown_backend_is_rejected() -> None:
    with pytest.raises(D.DispatcherError, match="executor menu"):
        D.dispatch(_req("magic-backend"))


def test_custom_available_set(tmp_path: Path) -> None:
    # If verified-workflow is not in the available set, it too halts (the seam is data-driven).
    ref = _write_team_ref(tmp_path)
    out = D.dispatch(
        _req("verified-workflow", orchestration_ref=ref, repo_root=tmp_path),
        available=("inline",),
    )
    assert out["status"] == "halt"


# --------------------------------------------------------------------------- make_dispatcher adapter


def test_make_dispatcher_returns_only_compatibility_reservation(tmp_path: Path) -> None:
    disp = D.make_dispatcher()
    ref = _write_team_ref(tmp_path)
    assert (
        disp(_req("verified-workflow", orchestration_ref=ref, repo_root=tmp_path))
        == "leaf-ship-x-build"
    )


def test_make_dispatcher_raises_halt_with_receipt() -> None:
    disp = D.make_dispatcher()
    with pytest.raises(D.BackendHaltError) as exc:
        disp(_req("fork"))
    assert exc.value.receipt.backend == "fork"
    assert exc.value.receipt.subplot_id == "build"


# --------------------------------------------------------------------------- team_emitter wiring (R5)


def _execution_spec_dict() -> dict[str, Any]:
    return {
        "name": "leaf-plan",
        "description": "a leaf plan",
        "repo": "/tmp/repo",
        "units": [
            {"unit_id": "U1", "label": "preflight", "tier": {"model": "haiku", "effort": "low"}},
            {
                "unit_id": "U2",
                "label": "build",
                "tier": {"model": "sonnet", "effort": "high"},
                "depends_on": ["U1"],
            },
        ],
    }


def test_team_execution_artifact_wires_team_emitter() -> None:
    spec = ES.ExecutionSpec.from_dict(_execution_spec_dict())
    art = D.team_execution_artifact(spec)
    assert "Team Structure" in art  # produced through recompile_for_tier's team_emitter leg (R5)
    assert "U1" in art and "U2" in art  # units preserved (by unit id)


# --------------------------------------------------------------------------- integration with advance


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    common = tmp_path / ".git"
    common.mkdir()
    monkeypatch.setattr(
        OUTCOME.outcome_store.subprocess,
        "run",
        lambda args, **kw: SimpleNamespace(returncode=0, stdout=str(common) + "\n", stderr=""),
    )
    return tmp_path


def test_advance_dispatches_team_execution_node(repo: Path) -> None:
    _write_team_ref(repo)
    OUTCOME.start(
        repo,
        "ship-x",
        "Ship X",
        nodes=[
            {
                "subplot_id": "build",
                "title": "Build",
                "backend": "verified-workflow",
                "evidence": {"orchestration_ref": TEAM_REF},
            }
        ],
    )
    result = OUTCOME.advance(repo, "ship-x", dispatcher=_launch_ack)
    assert result.dispatched == ["build"]
    assert OUTCOME.attend(repo, "ship-x", "build") == "/resume leaf-ship-x-build"
    store = STORE.Store.for_outcome("ship-x", repo)
    acknowledgements = [
        rec
        for rec in STORE.read_ledger(store)
        if rec.get("phase") == "ack" and rec.get("key") == "dispatch-intent:ship-x:build"
    ]
    assert acknowledgements[0]["orchestration_ref"] == TEAM_REF


def test_advance_dispatches_team_execution_alias_ref(repo: Path) -> None:
    _write_team_ref(repo)
    OUTCOME.start(
        repo,
        "ship-x",
        "Ship X",
        nodes=[
            {
                "subplot_id": "build",
                "title": "Build",
                "backend": "verified-workflow",
                "evidence": {"team_execution_ref": TEAM_REF},
            }
        ],
    )
    result = OUTCOME.advance(repo, "ship-x", dispatcher=_launch_ack)
    assert result.dispatched == ["build"]
    store = STORE.Store.for_outcome("ship-x", repo)
    acknowledgements = [
        rec
        for rec in STORE.read_ledger(store)
        if rec.get("phase") == "ack" and rec.get("key") == "dispatch-intent:ship-x:build"
    ]
    assert acknowledgements[0]["orchestration_ref"] == TEAM_REF


def test_advance_team_execution_without_ref_halts(repo: Path) -> None:
    OUTCOME.start(
        repo,
        "ship-x",
        "Ship X",
        nodes=[{"subplot_id": "build", "title": "Build", "backend": "verified-workflow"}],
    )
    result = OUTCOME.advance(repo, "ship-x", dispatcher=D.make_dispatcher())
    assert result.dispatched == []
    assert len(result.halted) == 1
    assert "missing orchestration_ref" in result.halted[0]["reason"]


def test_advance_team_execution_invalid_ref_halts(repo: Path) -> None:
    OUTCOME.start(
        repo,
        "ship-x",
        "Ship X",
        nodes=[
            {
                "subplot_id": "build",
                "title": "Build",
                "backend": "verified-workflow",
                "evidence": {"orchestration_ref": "docs/plans/does-not-exist.md#team-structure"},
            }
        ],
    )
    result = OUTCOME.advance(repo, "ship-x", dispatcher=D.make_dispatcher())
    assert result.dispatched == []
    assert len(result.halted) == 1
    assert "orchestration_ref target does not exist" in result.halted[0]["reason"]


def test_default_dispatcher_team_execution_without_ref_halts(repo: Path) -> None:
    OUTCOME.start(
        repo,
        "ship-x",
        "Ship X",
        nodes=[{"subplot_id": "build", "title": "Build", "backend": "verified-workflow"}],
    )
    result = OUTCOME.advance(repo, "ship-x")
    assert result.dispatched == []
    assert len(result.halted) == 1
    assert "missing orchestration_ref" in result.halted[0]["reason"]


def test_advance_halts_visibly_on_unavailable_backend_no_silent_substitute(repo: Path) -> None:
    OUTCOME.start(
        repo,
        "ship-x",
        "Ship X",
        nodes=[{"subplot_id": "build", "title": "Build", "backend": "fork"}],
    )
    # The reconcile loop catches the HALT per-leaf: surfaced in result.halted (visible), nothing
    # dispatched, nothing silently substituted to inline.
    result = OUTCOME.advance(repo, "ship-x", dispatcher=D.make_dispatcher())
    assert result.dispatched == []
    assert len(result.halted) == 1 and result.halted[0]["backend"] == "fork"
    store = STORE.Store.for_outcome("ship-x", repo)
    assert STORE.completed_subplots(store) == set()


def test_halt_does_not_leak_dispatch_lease_resurfaces_each_advance(repo: Path) -> None:
    # P1 regression: a HALT must release the per-subplot dispatch lock so the NEXT advance re-attempts
    # and re-surfaces the HALT, rather than the leaked lease silently masking it for the lease TTL.
    OUTCOME.start(
        repo,
        "ship-x",
        "Ship X",
        nodes=[{"subplot_id": "build", "title": "Build", "backend": "fork"}],
    )
    r1 = OUTCOME.advance(repo, "ship-x", dispatcher=D.make_dispatcher())
    r2 = OUTCOME.advance(repo, "ship-x", dispatcher=D.make_dispatcher())
    assert len(r1.halted) == 1 and len(r2.halted) == 1  # re-surfaced, not masked by a leaked lease


def test_halt_does_not_starve_other_runnable_leaves(repo: Path) -> None:
    # P2 regression: one HALT leaf must NOT abort the whole tick — independent runnable leaves still
    # dispatch in the same advance.
    _write_team_ref(repo)
    OUTCOME.start(
        repo,
        "ship-x",
        "Ship X",
        nodes=[
            {
                "subplot_id": "a",
                "title": "A",
                "backend": "verified-workflow",
                "evidence": {"orchestration_ref": TEAM_REF},
            },
            {"subplot_id": "b", "title": "B", "backend": "fork"},
        ],
    )
    result = OUTCOME.advance(
        repo,
        "ship-x",
        dispatcher=lambda req: (
            _launch_ack(req) if req.subplot_id == "a" else D.make_dispatcher()(req)
        ),
    )
    assert result.dispatched == ["a"]  # the runnable leaf dispatched despite b's HALT
    assert [h["subplot_id"] for h in result.halted] == ["b"]


def test_cli_advance_uses_the_real_backend_seam(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # R5: the production /outcome advance routes through the real seam, not the U3 record-only default.
    OUTCOME.start(
        repo,
        "ship-x",
        "Ship X",
        nodes=[{"subplot_id": "build", "title": "Build", "backend": "fork"}],
    )
    # R20 approval gate is upstream of the backend HALT — approve the frontier first so the leaf
    # actually reaches the dispatcher seam (an unapproved leaf is gated, never HALTed).
    assert OUTCOME.main(["--repo-root", str(repo), "approve", "ship-x"]) == 0
    capsys.readouterr()
    rc = OUTCOME.main(["--repo-root", str(repo), "advance", "ship-x"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert (
        out["dispatched"] == [] and len(out["halted"]) == 1
    )  # the seam HALTed fork, didn't dispatch


# --------------------------------------------------------------------------- CLI


def test_cli_dispatch_dry_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_team_ref(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert D.main(["ship-x", "build", "verified-workflow", "--orchestration-ref", TEAM_REF]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "prepared"
    assert out["proposed_leaf_saga_id"] == "leaf-ship-x-build"
    assert "return_channel" not in out
    assert out["orchestration_ref"] == TEAM_REF
    assert D.main(["ship-x", "build", "fork"]) == 0
    halt = json.loads(capsys.readouterr().out)
    assert halt["status"] == "halt"
