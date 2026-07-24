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
                    "arguments": {"task_name": child},
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


@pytest.mark.parametrize("command", ["git status --short", "env git diff", "/usr/bin/git log -1"])
def test_worker_git_invocation_fails(command: str) -> None:
    receipt = P.parse_runtime_receipt(rollout(command=command))
    with pytest.raises(P.ProtocolProbeError, match="prohibited Git invocation"):
        validate(receipt)


def test_undeclared_descendant_fails() -> None:
    receipt = P.parse_runtime_receipt(rollout(children=["nested"]))
    with pytest.raises(P.ProtocolProbeError, match="undeclared descendant"):
        validate(receipt)
    child = P.parse_runtime_receipt(
        rollout(path="/root/test/nested", parent="child-thread", terminal=True)
    )
    validate(
        receipt,
        declared_descendant_paths=("/root/test/nested",),
        descendant_receipts=(child,),
    )


def test_spawn_requires_real_v2_task_name() -> None:
    content = rollout(children=["nested"]).replace(b'"task_name": "nested"', b'"agent_path": "/root/test/nested"')
    with pytest.raises(P.ProtocolProbeError, match="arguments.task_name"):
        P.parse_runtime_receipt(content)


def test_spawn_requires_authoritative_matching_child_receipt() -> None:
    receipt = P.parse_runtime_receipt(rollout(children=["nested"]))
    with pytest.raises(P.ProtocolProbeError, match="missing=.*nested"):
        validate(receipt, declared_descendant_paths=("/root/test/nested",))
    wrong_parent = P.parse_runtime_receipt(
        rollout(path="/root/test/nested", parent="different-thread")
    )
    with pytest.raises(P.ProtocolProbeError, match="parent thread"):
        validate(
            receipt,
            declared_descendant_paths=("/root/test/nested",),
            descendant_receipts=(wrong_parent,),
        )


def test_cli_projects_receipt_without_claiming_result(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "rollout.jsonl"
    path.write_bytes(rollout())
    assert P.main(["--rollout", str(path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["agent_type"] == "test_medium"
    assert "result" not in payload
