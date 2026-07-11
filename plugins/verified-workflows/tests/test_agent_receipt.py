from __future__ import annotations

import json
import shutil
import stat
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).parents[1]
HOOKS = PLUGIN_ROOT / "hooks"
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))

import agent_receipt as A  # noqa: E402


def setup_home(tmp_path: Path, profile: str = "review_high") -> tuple[Path, Path]:
    home = tmp_path / "codex-home"
    agents = home / "agents"
    agents.mkdir(parents=True, mode=0o700)
    target = agents / f"{profile}.toml"
    shutil.copyfile(PLUGIN_ROOT / "agents" / f"{profile}.toml", target)
    target.chmod(0o600)
    data = tmp_path / "plugin-data"
    data.mkdir(mode=0o700)
    return home, data


def payload(event: str = "SubagentStart", **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "session_id": "session-123",
        "transcript_path": "/private/secret/transcript.jsonl",
        "cwd": "/private/workspace",
        "hook_event_name": event,
        "model": "gpt-5.6-sol",
        "permission_mode": "default",
        "turn_id": "turn-456",
        "agent_id": "child-789",
        "agent_type": "review_high",
    }
    if event == "SubagentStop":
        value.update(
            {
                "agent_transcript_path": "/private/secret/child.jsonl",
                "stop_hook_active": False,
                "last_assistant_message": "TOP-SECRET-RESULT",
            }
        )
    value.update(overrides)
    return value


def raw_path(data: Path, receipt: dict[str, object]) -> Path:
    return (
        data
        / "receipts"
        / "v1"
        / "raw"
        / A._sha256(str(receipt["parent_session_id"]).encode())
        / A._sha256(str(receipt["child_id"]).encode())
        / A._sha256(str(receipt["turn_id"]).encode())
        / f"{receipt['event']}.json"
    )


def test_official_sensitive_fields_are_accepted_and_never_persisted(tmp_path: Path) -> None:
    home, data = setup_home(tmp_path)
    receipt = A.normalize_event(
        payload("SubagentStop"), codex_home=home, now=lambda: "2026-07-10T22:00:00.000000Z"
    )

    A.persist_event(receipt, data)
    path = raw_path(data, receipt)
    text = path.read_text()

    assert set(json.loads(text)) == {
        "schema_version",
        "event",
        "parent_session_id",
        "turn_id",
        "child_id",
        "agent_type",
        "active_model",
        "permission_mode",
        "codex_home_sha256",
        "profile_sha256",
        "hook_definition_sha256",
        "hook_handler_sha256",
        "observed_at",
    }
    for secret in ("TOP-SECRET-RESULT", "/private/secret", "/private/workspace"):
        assert secret not in text
        assert secret not in path.as_posix()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert all(
        stat.S_IMODE(parent.stat().st_mode) == 0o700
        for parent in (path.parent, path.parent.parent, path.parent.parent.parent)
    )


def test_duplicate_delivery_is_idempotent_even_with_new_capture_time(tmp_path: Path) -> None:
    home, data = setup_home(tmp_path)
    first = A.normalize_event(payload(), codex_home=home, now=lambda: "2026-07-10T22:00:00.000000Z")
    second = A.normalize_event(payload(), codex_home=home, now=lambda: "2026-07-10T22:00:01.000000Z")

    A.persist_event(first, data)
    A.persist_event(second, data)

    assert json.loads(raw_path(data, first).read_text())["observed_at"] == first["observed_at"]


@pytest.mark.parametrize(
    "overrides,match",
    [
        ({"agent_type": "worker"}, "managed execution profile"),
        ({"agent_type": "../review_high"}, "safe identifier"),
        ({"model": "gpt-5.6-terra"}, "does not match"),
        ({"permission_mode": "read-only"}, "permission_mode"),
        ({"permission_mode": "acceptEdits"}, "permission_mode"),
        ({"permission_mode": "dontAsk"}, "permission_mode"),
        ({"permission_mode": "bypassPermissions"}, "permission_mode"),
        ({"prompt": "ignore policy"}, "unsupported fields"),
    ],
)
def test_untrusted_hook_identity_fails(
    tmp_path: Path, overrides: dict[str, object], match: str
) -> None:
    home, _data = setup_home(tmp_path)
    with pytest.raises(A.AgentReceiptError, match=match):
        A.normalize_event(payload(**overrides), codex_home=home)


def test_profile_symlink_is_rejected(tmp_path: Path) -> None:
    home, _data = setup_home(tmp_path)
    profile = home / "agents" / "review_high.toml"
    source = tmp_path / "source.toml"
    profile.rename(source)
    profile.symlink_to(source)

    with pytest.raises(A.AgentReceiptError, match="symlink|unreadable|escapes"):
        A.normalize_event(payload(), codex_home=home)


def test_profile_parent_symlink_is_rejected(tmp_path: Path) -> None:
    home, _data = setup_home(tmp_path)
    agents = home / "agents"
    real_agents = tmp_path / "real-agents"
    agents.rename(real_agents)
    agents.symlink_to(real_agents, target_is_directory=True)

    with pytest.raises(A.AgentReceiptError, match="symlink|unreadable|escapes"):
        A.normalize_event(payload(), codex_home=home)


def test_plugin_data_symlink_is_rejected(tmp_path: Path) -> None:
    home, data = setup_home(tmp_path)
    real = tmp_path / "real-data"
    data.rename(real)
    data.symlink_to(real, target_is_directory=True)
    receipt = A.normalize_event(payload(), codex_home=home)

    with pytest.raises(A.AgentReceiptError, match="symlink"):
        A.persist_event(receipt, data)


def test_unsafe_plugin_data_mode_is_rejected(tmp_path: Path) -> None:
    home, data = setup_home(tmp_path)
    data.chmod(0o777)
    receipt = A.normalize_event(payload(), codex_home=home)

    with pytest.raises(A.AgentReceiptError, match="writable"):
        A.persist_event(receipt, data)


def test_profile_hardlink_and_extra_fields_are_rejected(tmp_path: Path) -> None:
    home, _data = setup_home(tmp_path)
    profile = home / "agents" / "review_high.toml"
    hardlink = tmp_path / "profile-copy.toml"
    hardlink.hardlink_to(profile)
    with pytest.raises(A.AgentReceiptError, match="single-link"):
        A.normalize_event(payload(), codex_home=home)

    hardlink.unlink()
    profile.write_text(profile.read_text() + "\nextra = true\n")
    with pytest.raises(A.AgentReceiptError, match="not closed"):
        A.normalize_event(payload(), codex_home=home)


def test_conflicting_duplicate_event_is_rejected(tmp_path: Path) -> None:
    home, data = setup_home(tmp_path)
    receipt = A.normalize_event(
        payload(), codex_home=home, now=lambda: "2026-07-10T22:00:00.000000Z"
    )
    conflict = {**receipt, "permission_mode": "plan", "observed_at": "2026-07-10T22:00:01Z"}
    A.persist_event(receipt, data)

    with pytest.raises(A.AgentReceiptError, match="conflicts"):
        A.persist_event(conflict, data)


def test_failed_atomic_write_removes_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _home, data = setup_home(tmp_path)
    directory_fd = A.os.open(data, A._directory_flags())
    real_write = A.os.write
    failed = False

    def fail_once(descriptor: int, content: object) -> int:
        nonlocal failed
        if not failed:
            failed = True
            raise OSError("fixture write failure")
        return real_write(descriptor, content)  # type: ignore[arg-type]

    monkeypatch.setattr(A.os, "write", fail_once)
    try:
        with pytest.raises(OSError, match="fixture write failure"):
            A._write_once(directory_fd, "event.json", b"{}\n")
    finally:
        A.os.close(directory_fd)

    assert not any(path.name.endswith(".tmp") for path in data.iterdir())


def test_hook_manifest_covers_only_named_profiles() -> None:
    manifest = json.loads((HOOKS / "hooks.json").read_text())
    assert set(manifest["hooks"]) == {"SubagentStart", "SubagentStop"}
    for event in manifest["hooks"].values():
        matcher = event[0]["matcher"]
        assert "worker" not in matcher
        assert all(profile in matcher for profile in A.PROFILE_TYPES)
