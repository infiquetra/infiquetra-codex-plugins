from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import render_codex_agents as renderer  # noqa: E402
import workflow_dispatch as dispatch  # noqa: E402
import workflow_feasibility as feasibility  # noqa: E402

SNAPSHOT = Path(__file__).parents[3] / "docs" / "validation" / "codex-runtime-capability-snapshot.json"


def _profile(execution_class: str) -> tuple[str, str, str]:
    runtime_agent_name = renderer.RUNTIME_AGENT_NAMES[execution_class]
    content = (PLUGIN_ROOT / "agents" / f"{runtime_agent_name}.toml").read_bytes()
    payload = tomllib.loads(content.decode("utf-8"))
    return hashlib.sha256(content).hexdigest(), payload["model"], payload["model_reasoning_effort"]


def _row(
    step_id: str,
    role_id: str = "security-reviewer",
    *,
    independence: str = "preferred",
    vehicle: str = "inline",
) -> list[str]:
    if role_id == "root":
        return [
            step_id,
            "-",
            "-",
            "root",
            "root",
            "n/a",
            "-",
            "-",
            "root",
            "root-only",
            "root-evidence",
            "-",
            "-",
            "-",
            "-",
            "n/a",
            "n/a",
            "-",
        ]
    role = renderer.load_role_registry().role(role_id)
    digest, model, effort = _profile("review-high")
    return [
        step_id,
        "-",
        "-",
        role_id,
        role.kind,
        independence,
        "review-high",
        "review_high",
        vehicle,
        "none",
        "review-evidence",
        str(role.lens_sha256),
        digest,
        model,
        effort,
        "n/a",
        "n/a",
        "-",
    ]


def _plan(*rows: list[str]) -> str:
    header = "| " + " | ".join(dispatch.HEADERS) + " |"
    separator = "| " + " | ".join("---" for _ in dispatch.HEADERS) + " |"
    body = "\n".join("| " + " | ".join(row) + " |" for row in rows)
    return f"# Plan\n\n## Workflow Structure\n\n{header}\n{separator}\n{body}\n"


def _write_plan(tmp_path: Path, *rows: list[str]) -> Path:
    plan = tmp_path / "plan.md"
    plan.write_text(_plan(*rows), encoding="utf-8")
    return plan


def test_inline_plan_is_ready_without_child_claim(tmp_path: Path) -> None:
    result = feasibility.review_workflow(
        plan=_write_plan(tmp_path, _row("root", "root"), _row("review")),
        snapshot_path=SNAPSHOT,
    )

    assert result["outcome"] == "ready"
    assert result["runtime_proof"] is False
    assert result["findings"] == []
    review = next(row for row in result["rows"] if row["step_id"] == "review")
    assert review["disposition"] == "gate-authoritative-root-inline"
    assert "model" not in review
    assert "effort" not in review


@pytest.mark.parametrize("vehicle", ["auto", "subagent"])
def test_child_vehicle_requires_inline_gate_contract(tmp_path: Path, vehicle: str) -> None:
    result = feasibility.review_workflow(
        plan=_write_plan(tmp_path, _row("review", vehicle=vehicle)),
        snapshot_path=SNAPSHOT,
    )

    assert result["outcome"] == "requires-inline"
    assert result["findings"] == [
        {
            "step_id": "review",
            "role_kind": "agent-lens",
            "vehicle": vehicle,
            "independence": "preferred",
            "requested_execution_class": "review-high",
            "runtime_agent_name": "review_high",
            "spawn_surface": "named",
            "disposition": "advisory-child-only",
            "required_amendment": "change vehicle to inline for gate authority",
            "limitation": (
                "a native child may provide advisory evidence, but this capability projection does not "
                "prove host-issued child attestation"
            ),
        }
    ]


def test_required_independence_remains_strictly_unavailable(tmp_path: Path) -> None:
    result = feasibility.review_workflow(
        plan=_write_plan(
            tmp_path,
            _row("review", independence="required", vehicle="subagent"),
        ),
        snapshot_path=SNAPSHOT,
    )

    assert result["outcome"] == "strict-unavailable"
    assert result["findings"][0]["disposition"] == "strict-child-unavailable"
    assert result["findings"][0]["required_amendment"] == (
        "provide host-issued child attestation or remove the strict contract"
    )


def test_cli_uses_nonzero_exit_for_required_amendment(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    plan = _write_plan(tmp_path, _row("review", vehicle="subagent"))

    assert feasibility.main(["--plan", str(plan), "--snapshot", str(SNAPSHOT)]) == 1

    result = json.loads(capsys.readouterr().out)
    assert result["outcome"] == "requires-inline"


def test_rejects_non_object_capability_snapshot(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text("[]\n", encoding="utf-8")

    with pytest.raises(feasibility.WorkflowFeasibilityError, match="must be an object"):
        feasibility.review_workflow(
            plan=_write_plan(tmp_path, _row("review")),
            snapshot_path=snapshot,
        )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"collaboration": []}, "collaboration must be an object"),
        ({"collaboration": {"spawn": []}}, "collaboration.spawn must be an object"),
        (
            {"collaboration": {"spawn": {"host_issued_child_attestation": True}}},
            "host-issued child attestation is unsupported",
        ),
    ],
)
def test_rejects_malformed_or_unsupported_capability_claims(
    tmp_path: Path,
    payload: dict[str, object],
    message: str,
) -> None:
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(feasibility.WorkflowFeasibilityError, match=message):
        feasibility.review_workflow(
            plan=_write_plan(tmp_path, _row("review")),
            snapshot_path=snapshot,
        )


def test_explicit_unavailable_attestation_remains_root_inline_capable(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(
        json.dumps({"collaboration": {"spawn": {"host_issued_child_attestation": False}}}),
        encoding="utf-8",
    )

    result = feasibility.review_workflow(
        plan=_write_plan(tmp_path, _row("review")),
        snapshot_path=snapshot,
    )

    assert result["outcome"] == "ready"


def test_analyzer_never_launches_or_configures_children() -> None:
    source = Path(feasibility.__file__).read_text(encoding="utf-8")

    assert "subprocess" not in source
    assert "spawn_agent" not in source
    assert "codex_v1_catalog" not in source
