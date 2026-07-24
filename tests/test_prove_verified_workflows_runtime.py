from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "prove_verified_workflows_runtime.py"
SPEC = importlib.util.spec_from_file_location("prove_verified_workflows_runtime", SCRIPT)
assert SPEC and SPEC.loader
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)


def snapshot() -> tuple[dict[str, object], str]:
    return P._load_json(
        ROOT / "docs" / "validation" / "codex-runtime-capability-snapshot.json",
        "snapshot",
    )


def rollout(
    *,
    model: str = "gpt-5.6-sol",
    effort: str = "high",
    provider: str = "openai",
    approval: str = "never",
    sandbox: str = "read-only",
    permission: str = "managed",
    role: str = "review_high",
    path: str = "/root/u1_probe",
    parent: str | None = "root-thread",
    marker: str = P.TERMINAL_MARKER,
    include_parent_marker: bool = False,
) -> bytes:
    rows = [
        {
            "type": "session_meta",
            "payload": {
                "id": "child-thread" if parent else "root-thread",
                "parent_thread_id": parent,
                "agent_role": role if parent else None,
                "agent_path": path if parent else "/root",
                "model_provider": provider,
                "multi_agent_version": "v2",
                "history_mode": "legacy",
                "source": {},
            },
        },
        {
            "type": "turn_context",
            "payload": {
                "model": model,
                "effort": effort,
                "approval_policy": approval,
                "sandbox_policy": {"type": sandbox, "ignored": "/Users/private"},
                "permission_profile": {"type": permission, "ignored": "/Users/private"},
                "multi_agent_version": "v2",
            },
        },
        {
            "type": "response_item",
            "payload": {"type": "function_call", "name": "agents.spawn_agent"},
        },
        {
            "type": "event_msg",
            "payload": {"type": "task_complete", "last_agent_message": marker},
        },
    ]
    if include_parent_marker:
        rows.insert(
            -1,
            {
                "type": "response_item",
                "payload": {"type": "message", "content": P.PARENT_ONLY_MARKER},
            },
        )
    return ("\n".join(json.dumps(row) for row in rows) + "\n").encode()


def expected() -> dict[str, object]:
    return {
        "agent_path": "/root/u1_probe",
        "agent_role": "review_high",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "high",
        "model_provider": "openai",
        "approval_policy": "never",
        "sandbox_mode": "read-only",
        "permission_profile": "managed",
        "multi_agent_version": "v2",
    }


def test_dry_run_is_v2_diagnostic_and_sanitized() -> None:
    value, digest = snapshot()
    proof = P.build_proof(
        snapshot=value,
        snapshot_sha256=digest,
        live=False,
        codex_home=None,
        authenticated_isolated_home=False,
    )

    assert proof["capability_outcome"] == "diagnostic"
    assert proof["tool_namespace"] == "agents"
    assert proof["spawn_response_fields"] == ["nickname", "task_name"]
    assert proof["live_invocation_performed"] is False
    assert len(proof["profiles"]) == 5
    assert proof["project_discovery"]["location"] == ".codex/agents"
    assert proof["project_discovery"]["source_bytes_match"] is True
    P.validate_sanitized_proof(proof)


def test_rollout_parser_combines_session_meta_and_turn_context() -> None:
    receipt = P.parse_rollout_receipt(rollout())

    assert receipt == {
        "session_id": "child-thread",
        "parent_thread_id": "root-thread",
        "parent_thread_present": True,
        "agent_path": "/root/u1_probe",
        "agent_role": "review_high",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "high",
        "model_provider": "openai",
        "approval_policy": "never",
        "sandbox_mode": "read-only",
        "permission_profile": "managed",
        "multi_agent_version": "v2",
        "history_mode": "legacy",
        "parent_context_marker_observed": False,
        "terminal_status": "completed",
        "terminal_marker_observed": True,
        "operations_observed": ["spawn_agent"],
    }
    P.validate_runtime_receipt(receipt, expected())


@pytest.mark.parametrize(
    ("field", "kwargs"),
    [
        ("model", {"model": "gpt-5.6-luna"}),
        ("reasoning_effort", {"effort": "medium"}),
        ("model_provider", {"provider": "other"}),
        ("sandbox_mode", {"sandbox": "workspace-write"}),
        ("permission_profile", {"permission": "disabled"}),
        ("agent_role", {"role": "review_max"}),
        ("agent_path", {"path": "/root/other"}),
    ],
)
def test_runtime_receipt_mismatch_fails(field: str, kwargs: dict[str, str]) -> None:
    receipt = P.parse_rollout_receipt(rollout(**kwargs))

    with pytest.raises(P.RuntimeProofError, match=field):
        P.validate_runtime_receipt(receipt, expected())


def test_requested_fields_without_runtime_context_fail() -> None:
    content = json.dumps(
        {
            "type": "session_meta",
            "payload": {
                "id": "child",
                "agent_role": "review_high",
                "agent_path": "/root/u1_probe",
            },
        }
    ).encode()

    with pytest.raises(P.RuntimeProofError, match="turn_context"):
        P.parse_rollout_receipt(content)


def test_nonterminal_or_wrong_terminal_result_fails() -> None:
    receipt = P.parse_rollout_receipt(rollout(marker="not-the-contract"))

    with pytest.raises(P.RuntimeProofError, match="terminal result"):
        P.validate_runtime_receipt(receipt, expected())


def test_root_only_context_in_child_rollout_fails() -> None:
    receipt = P.parse_rollout_receipt(rollout(include_parent_marker=True))

    with pytest.raises(P.RuntimeProofError, match="root-only context"):
        P.validate_runtime_receipt(receipt, expected())


def test_live_requires_explicit_isolated_home_and_acknowledgement(tmp_path: Path) -> None:
    value, digest = snapshot()
    with pytest.raises(P.RuntimeProofError, match="requires an explicit isolated"):
        P.build_proof(
            snapshot=value,
            snapshot_sha256=digest,
            live=True,
            codex_home=None,
            authenticated_isolated_home=False,
        )
    home = tmp_path / "isolated-home"
    home.mkdir(mode=0o700)
    auth = home / "auth.json"
    auth.write_bytes(b"present")
    auth.chmod(0o600)
    with pytest.raises(P.RuntimeProofError, match="acknowledgement"):
        P.build_proof(
            snapshot=value,
            snapshot_sha256=digest,
            live=True,
            codex_home=home,
            authenticated_isolated_home=False,
        )


def test_missing_isolated_login_is_auth_unavailable(tmp_path: Path) -> None:
    value, digest = snapshot()
    home = tmp_path / "isolated-home"
    home.mkdir(mode=0o700)

    proof = P.build_proof(
        snapshot=value,
        snapshot_sha256=digest,
        live=True,
        codex_home=home,
        authenticated_isolated_home=True,
    )

    assert proof["capability_outcome"] == "auth-unavailable"
    assert proof["isolated_login_metadata_present"] is False


def test_committed_auth_unavailable_preflight_is_current(tmp_path: Path) -> None:
    value, digest = snapshot()
    home = tmp_path / "isolated-home"
    home.mkdir(mode=0o700)

    proof = P.build_proof(
        snapshot=value,
        snapshot_sha256=digest,
        live=True,
        codex_home=home,
        authenticated_isolated_home=True,
    )
    committed = json.loads(
        (
            ROOT
            / "docs"
            / "validation"
            / "codex-v2-orchestration-runtime-proof.json"
        ).read_text(encoding="utf-8")
    )

    assert committed == proof


def test_default_profile_tree_is_rejected() -> None:
    with pytest.raises(P.RuntimeProofError, match="default Codex profile"):
        P._validate_isolated_home(Path.home() / ".codex")


def test_secret_or_absolute_host_path_fails_proof_validation() -> None:
    with pytest.raises(P.RuntimeProofError, match="secret-shaped"):
        P.validate_sanitized_proof({"api_token": "redacted"})
    with pytest.raises(P.RuntimeProofError, match="path"):
        P.validate_sanitized_proof({"value": "/Users/example"})
    with pytest.raises(P.RuntimeProofError, match="secret-shaped"):
        P.validate_sanitized_proof({"value": "sk-exampleSecret123456"})


def test_snapshot_projection_rejects_requested_only_readback() -> None:
    value, _digest = snapshot()
    value["collaboration"]["spawn"]["selection_readback_fields"] = [  # type: ignore[index]
        "agent_type",
        "model",
    ]

    with pytest.raises(P.RuntimeProofError, match="readback fields drifted"):
        P._snapshot_projection(value)


def test_snapshot_projection_records_inherited_not_per_child_sandbox() -> None:
    value, _digest = snapshot()
    value["collaboration"]["spawn"]["per_child_sandbox"] = True  # type: ignore[index]

    with pytest.raises(P.RuntimeProofError, match="per-child sandbox"):
        P._snapshot_projection(value)


def test_live_command_is_closed_and_does_not_copy_default_auth() -> None:
    source = SCRIPT.read_text()

    assert "shutil.copy" not in source
    assert "shell=True" not in source
    assert 'env["CODEX_HOME"]' in source
    assert '"--strict-config"' in source
