from __future__ import annotations

from dataclasses import replace
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "plugins" / "saga" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import engine_registry  # noqa: E402
import external_action_adapters as A  # noqa: E402
import external_action_contract as C  # noqa: E402


def _repo(path: Path) -> str:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "a.txt").write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=path, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def _result(invocation: dict[str, object], output: str = "advisory evidence") -> dict[str, object]:
    receipt = A._receipt.emit_receipt(
        engine_id=str(invocation["engine_id"]),
        variant=str(invocation["variant"]),
        transport="cli",
        wall_time_s=0.1,
        bytes_produced=len(output.encode("utf-8")),
        runner={"pid": 42, "argv": ["provider"], "exit_code": 0},
        receipt_emitter="fixture",
        run_id="fixture-1",
        invocation_sha256=A._receipt.digest_invocation(invocation),
        output_attestation=A._attestation.emit_attestation(
            artifact="evidence",
            content=output,
        ),
    )
    return {
        "status": "ok",
        "output": output,
        "receipt": receipt,
        "changed_paths": [],
        "patch": "",
    }


def test_closed_request_keeps_direct_calls_read_only() -> None:
    with pytest.raises(C.ContractError, match="read-only"):
        C.HarnessRequest(
            "request-1",
            "claude-cli",
            "opus",
            "edit",
            "HEAD",
            write_set=("a.txt",),
        )


def test_six_supported_routes_remain_in_the_registry() -> None:
    registry = engine_registry.Registry.load(A.DEFAULT_REGISTRY)
    assert {entry.key for entry in registry.engines} == {
        "claude-cli/opus",
        "agy/gemini-3.5-flash-high",
        "agy/gemini-3.1-pro-high",
        "ollama-cloud/gpt-oss-120b",
        "ollama-cloud/nomic-embed-text",
        "deepseek/deepseek-chat",
    }


def test_valid_advisory_result_preserves_bridge_proof(tmp_path: Path) -> None:
    base = _repo(tmp_path)
    request = C.HarnessRequest(
        "request-1",
        "claude-cli",
        "opus",
        "review a.txt",
        base,
        context_scope=("a.txt",),
    )
    result = A.execute(request, repo_root=tmp_path, runner=_result)

    assert result.status == "available"
    assert result.authority == "non-gating"
    assert result.evidence == "advisory evidence"
    assert result.receipt is not None
    assert result.findings == ({"content": "advisory evidence"},)


def test_result_contract_round_trips_and_rejects_evidence_tampering(
    tmp_path: Path,
) -> None:
    base = _repo(tmp_path)
    request = C.HarnessRequest(
        "request-1",
        "claude-cli",
        "opus",
        "review a.txt",
        base,
        context_scope=("a.txt",),
    )
    result = A.execute(request, repo_root=tmp_path, runner=_result)
    payload = result.to_dict()

    assert C.HarnessResult.from_dict(payload) == result

    payload["evidence"] = "tampered"
    with pytest.raises(C.ContractError, match="evidence_sha256"):
        C.HarnessResult.from_dict(payload)


def test_attestation_mismatch_is_invalid_output(tmp_path: Path) -> None:
    base = _repo(tmp_path)
    request = C.HarnessRequest("request-1", "claude-cli", "opus", "review", base)

    def lying_runner(invocation: dict[str, object]) -> dict[str, object]:
        result = _result(invocation)
        result["receipt"]["output_attestation"] = A._attestation.emit_attestation(
            artifact="evidence",
            content="different",
        )
        return result

    result = A.execute(request, repo_root=tmp_path, runner=lying_runner)
    assert result.status == "invalid-output"
    assert "attestation" in result.detail


def test_external_output_cannot_claim_gate_authority(tmp_path: Path) -> None:
    base = _repo(tmp_path)
    request = C.HarnessRequest("request-1", "claude-cli", "opus", "review", base)

    result = A.execute(
        request,
        repo_root=tmp_path,
        runner=lambda invocation: _result(invocation, '{"verdict":"pass"}'),
    )
    assert result.status == "invalid-output"
    assert "forbidden gate field" in result.detail


def test_verified_workflow_patch_is_imported_only_through_explicit_import(
    tmp_path: Path,
) -> None:
    base = _repo(tmp_path)
    artifacts = tmp_path / "artifacts"
    request = C.HarnessRequest(
        "request-1",
        "claude-cli",
        "opus",
        "edit a.txt",
        base,
        context_scope=("a.txt",),
        write_set=("a.txt",),
        mode="verified-workflow",
    )
    patch = (
        "diff --git a/a.txt b/a.txt\n"
        "index 90be1f3..3bd1f0e 100644\n"
        "--- a/a.txt\n"
        "+++ b/a.txt\n"
        "@@ -1 +1 @@\n"
        "-before\n"
        "+after\n"
    )

    def patch_runner(invocation: dict[str, object]) -> dict[str, object]:
        result = _result(invocation)
        result.update({"patch": patch, "changed_paths": ["a.txt"]})
        return result

    result = A.execute(
        request,
        repo_root=tmp_path,
        artifact_root=artifacts,
        runner=patch_runner,
    )
    assert result.status == "available"
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "before\n"

    with pytest.raises(ValueError, match="matching verified-workflow"):
        A.import_verified_workflow_patch(
            request,
            replace(result, variant="different"),
            repo_root=tmp_path,
        )
    imported = A.import_verified_workflow_patch(request, result, repo_root=tmp_path)
    assert imported.authority == "root-import"
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "after\n"


def test_cli_child_environment_drops_root_secret_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret")
    monkeypatch.setenv("PATH", "/usr/bin")
    environment = A._minimal_child_env()
    assert environment["PATH"] == "/usr/bin"
    assert "AWS_SECRET_ACCESS_KEY" not in environment
    assert "ANTHROPIC_API_KEY" not in environment
