from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / "scripts"
TESTS = Path(__file__).parent
for path in (SCRIPTS, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import protocol_probe as P  # noqa: E402
import workflow_dispatch as W  # noqa: E402
from test_workflow_dispatch import compile_fixture  # noqa: E402


def launch() -> W.LaunchSpec:
    return next(spec for spec in compile_fixture().launch_specs if spec.assignment_id == "test")


def rollout(**overrides: object) -> bytes:
    values: dict[str, object] = {
        "path": "/root/test",
        "role": "test_medium",
        "model": "gpt-5.6-terra",
        "effort": "medium",
        "provider": "openai",
        "permission": "managed",
        "sandbox": "workspace-write",
        "version": "v2",
        "parent": "root-thread",
        "children": [],
        "command": "pytest -q",
        "terminal": True,
    }
    values.update(overrides)
    rows: list[dict[str, object]] = [
        {
            "type": "session_meta",
            "payload": {
                "id": "child-thread",
                "parent_thread_id": values["parent"],
                "agent_path": values["path"],
                "agent_role": values["role"],
                "model_provider": values["provider"],
                "multi_agent_version": values["version"],
            },
        },
        {
            "type": "turn_context",
            "payload": {
                "model": values["model"],
                "effort": values["effort"],
                "approval_policy": "never",
                "permission_profile": {"type": values["permission"]},
                "sandbox_policy": {"type": values["sandbox"]},
                "multi_agent_version": values["version"],
            },
        },
        {
            "type": "response_item",
            "payload": {
                "name": "exec_command",
                "arguments": {"cmd": values["command"]},
            },
        },
    ]
    for child in values["children"]:  # type: ignore[union-attr]
        rows.append(
            {
                "type": "response_item",
                "payload": {
                    "name": "agents.spawn_agent",
                    "arguments": {"agent_path": child},
                },
            }
        )
    if values["terminal"]:
        rows.append({"type": "event_msg", "payload": {"type": "task_complete"}})
    return ("\n".join(json.dumps(row) for row in rows) + "\n").encode()


def validate(receipt: P.RuntimeReceipt, **overrides: object) -> None:
    values: dict[str, object] = {
        "expected_agent_path": "/root/test",
        "expected_provider": "openai",
        "expected_permission_profile": "managed",
        "expected_sandbox_mode": "workspace-write",
        "declared_descendant_paths": (),
    }
    values.update(overrides)
    P.validate_runtime_receipt(receipt, launch(), **values)  # type: ignore[arg-type]


def test_exact_v2_runtime_readback_passes() -> None:
    receipt = P.parse_runtime_receipt(rollout())
    validate(receipt)
    assert receipt.terminal_observed is True
    assert receipt.source_events == ("session_meta", "turn_context")


@pytest.mark.parametrize(
    ("kwargs", "field"),
    [
        ({"path": "/root/other"}, "agent_path"),
        ({"role": "work_high"}, "agent_type"),
        ({"model": "gpt-5.6-sol"}, "model"),
        ({"effort": "high"}, "reasoning_effort"),
        ({"provider": "other"}, "model_provider"),
        ({"permission": "disabled"}, "permission_profile"),
        ({"sandbox": "read-only"}, "sandbox_mode"),
        ({"version": "v1"}, "multi_agent_version"),
    ],
)
def test_runtime_identity_mismatch_fails(kwargs: dict[str, object], field: str) -> None:
    with pytest.raises(P.ProtocolProbeError, match=field):
        validate(P.parse_runtime_receipt(rollout(**kwargs)))


def test_requested_only_identity_is_not_runtime_proof() -> None:
    content = json.dumps(
        {
            "type": "session_meta",
            "payload": {
                "id": "child",
                "parent_thread_id": "root",
                "agent_path": "/root/test",
                "agent_role": "test_medium",
            },
        }
    ).encode()
    with pytest.raises(P.ProtocolProbeError, match="both session_meta and turn_context"):
        P.parse_runtime_receipt(content)


def test_worker_git_mutation_command_fails() -> None:
    receipt = P.parse_runtime_receipt(rollout(command="git commit -am bad"))
    with pytest.raises(P.ProtocolProbeError, match="prohibited Git mutation"):
        validate(receipt)


def test_undeclared_descendant_fails() -> None:
    receipt = P.parse_runtime_receipt(rollout(children=["/root/test/nested"]))
    with pytest.raises(P.ProtocolProbeError, match="undeclared descendant"):
        validate(receipt)
    validate(receipt, declared_descendant_paths=("/root/test/nested",))


def test_cli_projects_receipt_without_claiming_result(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "rollout.jsonl"
    path.write_bytes(rollout())
    assert P.main(["--rollout", str(path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["agent_type"] == "test_medium"
    assert "result" not in payload
