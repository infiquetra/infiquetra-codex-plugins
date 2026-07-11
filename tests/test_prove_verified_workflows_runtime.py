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


def test_dry_run_is_inline_only_and_sanitized() -> None:
    value, digest = snapshot()
    proof = P.build_proof(
        snapshot=value,
        snapshot_sha256=digest,
        live=False,
        codex_home=None,
        authenticated_isolated_home=False,
    )
    assert proof["capability_outcome"] == "inline-only"
    assert proof["spawn_surface"] == "generic"
    assert proof["live_invocation_performed"] is False
    assert proof["runtime_receipt_ref"] is None
    assert len(proof["profiles"]) == 5
    assert proof["project_discovery"]["location"] == ".codex/agents"
    assert proof["project_discovery"]["source_bytes_match"] is True
    assert len(proof["project_discovery"]["files"]) == 5
    P.validate_sanitized_proof(proof)


def test_live_requires_explicit_isolated_home_and_acknowledgement() -> None:
    value, digest = snapshot()
    with pytest.raises(P.RuntimeProofError, match="requires an explicit isolated"):
        P.build_proof(
            snapshot=value,
            snapshot_sha256=digest,
            live=True,
            codex_home=None,
            authenticated_isolated_home=False,
        )


def test_missing_isolated_login_is_auth_unavailable_without_reading_auth(tmp_path: Path) -> None:
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


def test_default_profile_tree_is_rejected() -> None:
    with pytest.raises(P.RuntimeProofError, match="default Codex profile"):
        P._validate_isolated_home(Path.home() / ".codex")


@pytest.mark.parametrize("flag", ["--snapshot", "--live-envelope"])
def test_cli_rejects_default_profile_inputs_before_any_file_read(
    monkeypatch: pytest.MonkeyPatch,
    flag: str,
) -> None:
    reads: list[Path] = []

    def forbidden_read(path: Path, where: str, limit: int = P.MAX_BYTES) -> bytes:
        reads.append(path)
        raise AssertionError((where, limit))

    monkeypatch.setattr(P, "_read_regular", forbidden_read)
    args = [flag, str(Path.home() / ".codex" / "auth.json")]
    if flag == "--live-envelope":
        args += ["--codex-home", str(Path.home() / ".codex")]

    assert P.main(args) == 1
    assert reads == []


def test_secret_or_absolute_path_fails_proof_validation() -> None:
    with pytest.raises(P.RuntimeProofError, match="secret-shaped"):
        P.validate_sanitized_proof({"api_token": "redacted"})
    with pytest.raises(P.RuntimeProofError, match="path"):
        P.validate_sanitized_proof({"value": "/Users/example"})
    with pytest.raises(P.RuntimeProofError, match="secret-shaped"):
        P.validate_sanitized_proof({"value": "sk-exampleSecret123456"})


def test_empty_auth_file_is_not_login_metadata(tmp_path: Path) -> None:
    home = tmp_path / "isolated-home"
    home.mkdir(mode=0o700)
    auth = home / "auth.json"
    auth.write_bytes(b"")
    auth.chmod(0o600)

    assert P._validate_isolated_home(home) is False


def test_isolated_install_readback_proves_only_installed_bytes(
    tmp_path: Path,
) -> None:
    value, digest = snapshot()
    home = tmp_path / "isolated-home"
    home.mkdir(mode=0o700)
    auth = home / "auth.json"
    auth.write_bytes(b"present")
    auth.chmod(0o600)
    installed_plugin = home / "plugins" / "verified-workflows"
    installed_hooks = installed_plugin / "hooks"
    installed_agents = home / "agents"
    installed_hooks.mkdir(parents=True)
    installed_agents.mkdir()
    for name in ("hooks.json", "agent_receipt.py"):
        installed_hooks.joinpath(name).write_bytes(
            (ROOT / "plugins" / "verified-workflows" / "hooks" / name).read_bytes()
        )
    for fact in P._profile_facts():
        name = f"{fact['runtime_agent_name']}.toml"
        installed_agents.joinpath(name).write_bytes(
            (ROOT / "plugins" / "verified-workflows" / "agents" / name).read_bytes()
        )
    envelope = P.build_live_envelope(home, "root-task:" + "a" * 64)
    envelope_path = tmp_path / "envelope.json"
    envelope_path.write_text(json.dumps(envelope, sort_keys=True))
    loaded = P._load_live_envelope(envelope_path, home)

    proof = P.build_proof(
        snapshot=value,
        snapshot_sha256=digest,
        live=True,
        codex_home=home,
        authenticated_isolated_home=True,
        live_envelope=loaded,
    )

    assert proof["mode"] == "isolated-readback"
    assert proof["capability_outcome"] == "inline-only"
    assert proof["live_invocation_performed"] is False
    assert proof["root_mediated_task_reported"] is False
    assert proof["hook_capabilities"]["installed_bytes_readback"] is True
    assert proof["hook_capabilities"]["trust_readback"] == "unobserved"


def test_legacy_fresh_task_claim_is_rejected(tmp_path: Path) -> None:
    home = tmp_path / "isolated-home"
    home.mkdir(mode=0o700)
    auth = home / "auth.json"
    auth.write_bytes(b"present")
    auth.chmod(0o600)
    envelope_path = tmp_path / "envelope.json"
    envelope_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "claim": "root-accountability-fresh-session",
                "install": {},
                "fresh_task": {"task_ref": "root-task:" + "b" * 64},
            },
            sort_keys=True,
        )
    )

    with pytest.raises(P.RuntimeProofError, match="fields are not closed"):
        P._load_live_envelope(envelope_path, home)


def test_snapshot_projection_rejects_unexpected_request_field() -> None:
    value, _digest = snapshot()
    value["collaboration"]["spawn"]["request_fields"] = ["sk-secret123456"]  # type: ignore[index]

    with pytest.raises(P.RuntimeProofError, match="request fields drifted"):
        P._snapshot_projection(value)


def test_harness_has_no_codex_subprocess_launcher() -> None:
    source = SCRIPT.read_text()
    assert "subprocess" not in source
    assert "codex exec" not in source
