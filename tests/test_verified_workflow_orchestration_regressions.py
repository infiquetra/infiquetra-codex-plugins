"""Cross-surface regressions for Verified Workflows orchestration readiness."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


ROOT = Path(__file__).resolve().parent.parent
SAGA_SCRIPTS = ROOT / "plugins" / "saga" / "scripts"
WORKFLOW_SCRIPTS = ROOT / "plugins" / "verified-workflows" / "scripts"


def _load(name: str, path: Path) -> ModuleType:
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


READINESS = _load(
    "verified_workflow_readiness_regression",
    SAGA_SCRIPTS / "verified_workflow_readiness.py",
)
PROBE = _load("verified_workflow_protocol_probe_regression", WORKFLOW_SCRIPTS / "protocol_probe.py")
DISPATCHER = _load("outcome_dispatcher_regression", SAGA_SCRIPTS / "outcome_dispatcher.py")


def test_metadata_only_plan_ready_workflow_is_blocked(tmp_path: Path) -> None:
    plan = tmp_path / "docs" / "plans" / "metadata-only.md"
    plan.parent.mkdir(parents=True)
    plan.write_text(
        "# Plan\n\nRecommended backend: verified-workflow\n\nNo receipt here.\n",
        encoding="utf-8",
    )

    result = READINESS.validate_verified_workflow_ready(
        tmp_path,
        orchestration_mode="verified-workflow",
        orchestration_ref="docs/plans/metadata-only.md",
        context="plan-ready",
    )

    assert result.status == "blocked"
    assert "Workflow Structure" in result.reason


def test_empty_ref_work_is_blocked_before_mutation(tmp_path: Path) -> None:
    result = READINESS.validate_verified_workflow_ready(
        tmp_path,
        orchestration_mode="verified-workflow",
        orchestration_ref="",
        context="work",
        plan_path="docs/plans/repair.md",
    )

    assert result.status == "blocked"
    assert "docs/plans/repair.md#workflow-structure" in result.repair_hint


def test_absent_spawn_surface_is_truthful_inline_only() -> None:
    payload = PROBE.probe_protocol(
        snapshot={},
        snapshot_sha256="0" * 64,
        spawn_surface="absent",
        hook_pair="absent",
    )

    assert payload["outcome"] == "inline-only"
    assert payload["runtime_proof"] is False
    assert "native child spawn is unavailable" in payload["limitations"]


def test_resume_instructions_cover_contradiction_and_stale_context_repair() -> None:
    body = (ROOT / "plugins" / "saga" / "skills" / "resume" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    for phrase in (
        "generic-subagent",
        ".codex/plugins/cache/",
        "reread current repo skill files",
        "orchestration_downgrade",
        "mixed canonical/legacy roots",
    ):
        assert phrase in body


def test_legacy_workflow_leaf_without_ref_normalizes_then_halts() -> None:
    req = SimpleNamespace(
        outcome_id="ship-x",
        subplot_id="build",
        title="Build",
        backend="team-execution",
        repo_root=Path("."),
        orchestration_ref="",
    )

    result = DISPATCHER.dispatch(req)

    assert result["status"] == "halt"
    assert result["receipt"]["backend"] == "verified-workflow"
    assert "legacy workflow state" in result["receipt"]["reason"]
