"""Tests for the offline Codex capability probes.

Binary-touching tests skip when Codex is absent, because a missing binary is an environment fact
rather than a defect here. The parsing and extraction tests always run: they are grounded in a
committed fixture taken from a real Codex 0.147.0 child turn, so they keep working without the
binary and still assert against something that genuinely happened.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "codex_capability_probe.py"
FIXTURE = ROOT / "tests" / "fixtures" / "codex-0147-child-additional-tools.json"
SPEC = importlib.util.spec_from_file_location("codex_capability_probe", SCRIPT)
assert SPEC and SPEC.loader
PROBE = importlib.util.module_from_spec(SPEC)
sys.modules["codex_capability_probe"] = PROBE
SPEC.loader.exec_module(PROBE)

# Captured independently by the cross-review engine and reproduced by this harness. Two probes
# that never shared code agreeing on this digest is what makes the capture trustworthy.
CHILD_DEFINITIONS_SHA256 = "88de1982b61f7fbc41713c11015a380be43100b2d977531b42fa7424b6490a29"

needs_codex = pytest.mark.skipif(
    shutil.which("codex") is None, reason="the codex executable is not installed"
)


def captured_child_request() -> dict[str, object]:
    """Rebuild a request body around the committed additional_tools item."""

    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {
        "input": [fixture["additional_tools"]],
        "model": fixture["model"],
        "reasoning": {"effort": fixture["reasoning_effort"]},
        "client_metadata": {PROBE.PARENT_THREAD_METADATA_KEY: "parent-thread"},
    }


@pytest.fixture
def probe_workspace(tmp_path: Path) -> tuple[Path, Path]:
    home = PROBE.isolated_probe_home(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return home, workspace


def test_the_real_home_is_protected_even_when_codex_home_points_elsewhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CODEX_HOME is mutable, so deriving the protected path from it protects nothing.

    Anything that sets it to a temporary directory could otherwise hand the operator's real home
    to a probe. The default location is protected unconditionally.
    """

    decoy = PROBE.isolated_probe_home(tmp_path)
    monkeypatch.setenv("CODEX_HOME", str(decoy))
    real_home = Path.home() / ".codex"
    if not real_home.is_dir():
        pytest.skip("no real Codex home on this machine to protect")

    with pytest.raises(PROBE.CapabilityProbeError, match="refusing to probe against the real"):
        PROBE._assert_disposable_home(real_home, "guard")

    # The decoy named by the environment is protected too, and so are its descendants.
    with pytest.raises(PROBE.CapabilityProbeError, match="refusing to probe against the real"):
        PROBE._assert_disposable_home(decoy, "guard")


def test_a_directory_inside_or_containing_a_protected_home_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Equality alone would let a probe write inside the real home, or contain it."""

    protected = tmp_path / "home" / ".codex"
    protected.mkdir(parents=True, mode=0o700)
    monkeypatch.setenv("CODEX_HOME", str(protected))

    inside = protected / "sessions"
    inside.mkdir()
    containing = protected.parent

    for candidate in (inside, containing):
        with pytest.raises(PROBE.CapabilityProbeError, match="refusing to probe"):
            PROBE._assert_disposable_home(candidate, "guard")


def test_an_allowlisted_field_cannot_smuggle_a_credential(tmp_path: Path) -> None:
    """An allowlist is not sanitisation: `model` and `effort` are caller-controlled."""

    for field, payload in (
        ("model", {"Authorization": "Bearer abcdefghijklmnop"}),
        ("model", "Bearer abcdefghijklmnop"),
        ("model", "sk-abcdefghijklmnop"),
    ):
        body = captured_child_request()
        body[field] = payload
        with pytest.raises(PROBE.CapabilityProbeError):
            PROBE.extract_tool_specification(body)

    body = captured_child_request()
    body["reasoning"] = {"effort": {"authorization": "Bearer abcdefghijklmnop"}}
    with pytest.raises(PROBE.CapabilityProbeError, match="must be a string"):
        PROBE.extract_tool_specification(body)


def test_the_stub_answers_by_who_is_asking_not_by_arrival_order() -> None:
    """Codex starts the child asynchronously; a global counter makes replies scheduler-dependent.

    Drives the real server with the child overtaking the root's second request — the interleaving
    an arrival-order stub gets wrong — and asserts the child still receives the child reply.
    """

    root_scripts, child_script = PROBE.spawn_script(task_name="probe", agent_type="scan_low")

    def post(url: str, body: dict) -> str:
        payload = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read().decode("utf-8")

    with PROBE._RecordingResponsesApi(root_scripts, child_script) as stub:
        url = f"{stub.base_url}/responses"
        first_root = post(url, {"client_metadata": {"thread_id": "root"}})
        # The child arrives before the root's next request.
        child = post(url, {"client_metadata": {PROBE.PARENT_THREAD_METADATA_KEY: "root"}})
        second_root = post(url, {"client_metadata": {"thread_id": "root"}})

    assert "spawn_agent" in first_root
    assert child == child_script
    assert "spawn_agent" not in child
    assert "wait_agent" not in child
    # The root's own sequence is unaffected by the child having been served in between.
    assert "wait_agent" in second_root


def test_the_extraction_returns_definitions_not_a_call_list() -> None:
    """The distinction U5 exists to make: names alone are a call list, not a specification."""

    specification = PROBE.extract_tool_specification(captured_child_request())

    assert specification["namespaces"] == {
        "collaboration": [
            "followup_task",
            "interrupt_agent",
            "list_agents",
            "send_message",
            "spawn_agent",
            "wait_agent",
        ],
        "functions": ["exec", "request_user_input", "wait"],
    }
    assert specification["definitions_sha256"] == CHILD_DEFINITIONS_SHA256
    assert specification["model"] == "gpt-5.6-terra"
    assert specification["reasoning_effort"] == "low"
    assert specification["turn_is_spawned_child"] is True
def test_a_bare_name_list_is_rejected_as_a_specification() -> None:
    """A tool with no description, parameters, or format is a call list entry."""

    body = {
        "input": [
            {
                "type": "additional_tools",
                "role": "developer",
                "tools": [
                    {
                        "type": "namespace",
                        "name": "collaboration",
                        "tools": [{"type": "custom", "name": "spawn_agent"}],
                    }
                ],
            }
        ]
    }

    with pytest.raises(PROBE.CapabilityProbeError, match="carries no definition"):
        PROBE.extract_tool_specification(body)


def test_a_request_without_the_specification_item_fails_rather_than_inferring() -> None:
    body = {"input": [{"type": "message", "role": "user", "content": "hello"}]}

    with pytest.raises(PROBE.CapabilityProbeError, match="carries no additional_tools item"):
        PROBE.extract_tool_specification(body)


def test_the_extraction_carries_no_machine_identifier_or_prompt() -> None:
    """Only the reduced projection leaves the probe; request bodies are not evidence carriers."""

    body = captured_child_request()
    body["client_metadata"]["x-codex-installation-id"] = "b8cbdfde-0000-0000-0000-000000000000"
    body["input"].append({"type": "message", "role": "user", "content": "SECRET_PROMPT_TEXT"})

    rendered = json.dumps(PROBE.extract_tool_specification(body))

    assert "SECRET_PROMPT_TEXT" not in rendered
    assert "b8cbdfde" not in rendered
    assert "client_metadata" not in rendered


def test_the_committed_fixture_carries_no_credential_or_host_path() -> None:
    text = FIXTURE.read_text(encoding="utf-8")

    assert "/Users/" not in text
    assert "Authorization" not in text
    assert "Bearer " not in text


def test_a_root_and_a_child_request_are_distinguishable() -> None:
    child = PROBE.extract_tool_specification(captured_child_request())
    root_body = captured_child_request()
    root_body["client_metadata"] = {"thread_id": "root-thread"}
    root = PROBE.extract_tool_specification(root_body)

    assert child["turn_is_spawned_child"] is True
    assert root["turn_is_spawned_child"] is False


def test_config_overrides_render_as_toml_not_json() -> None:
    """Codex parses a `-c` value as TOML; JSON object syntax is rejected by the binary."""

    rendered = PROBE._toml_inline_table(
        {"name": "probe", "base_url": "http://127.0.0.1:1/v1", "request_max_retries": 0}
    )

    assert rendered == (
        '{ name = "probe", base_url = "http://127.0.0.1:1/v1", request_max_retries = 0 }'
    )
    assert ":" not in rendered.replace("http://127.0.0.1:1/v1", "")


def test_an_unknown_feature_stage_fails_rather_than_being_recorded() -> None:
    """A new stage means Codex reclassified its own features; that is worth stopping on."""

    known = PROBE.FEATURE_ROW.match("multi_agent_v2                       stable             false")
    assert known is not None and known.group("stage").strip() in PROBE.FEATURE_STAGES

    unknown = PROBE.FEATURE_ROW.match("some_feature                         brand new          true")
    assert unknown is not None and unknown.group("stage").strip() not in PROBE.FEATURE_STAGES


@needs_codex
def test_the_installed_binary_reports_its_feature_stages(
    probe_workspace: tuple[Path, Path]
) -> None:
    home, workspace = probe_workspace
    features = PROBE.capture_feature_flags(codex_home=home, cwd=workspace)

    assert len(features) > 50
    assert set(features["multi_agent"]) == {"stage", "enabled"}
    assert features["multi_agent"]["stage"] in PROBE.FEATURE_STAGES


@needs_codex
def test_the_feature_capture_reflects_configuration_rather_than_a_fixed_answer(
    probe_workspace: tuple[Path, Path]
) -> None:
    """If --enable did not move the captured state, the capture would be decoration."""

    home, workspace = probe_workspace
    off = PROBE.capture_feature_flags(
        codex_home=home, cwd=workspace, disable=("multi_agent_v2",)
    )
    on = PROBE.capture_feature_flags(codex_home=home, cwd=workspace, enable=("multi_agent_v2",))

    assert off["multi_agent_v2"]["enabled"] is False
    assert on["multi_agent_v2"]["enabled"] is True


@needs_codex
def test_a_spawned_child_specification_is_captured_offline(
    probe_workspace: tuple[Path, Path]
) -> None:
    """The capture that matters: what a named child profile is actually offered.

    Runs against a local unauthenticated stand-in, so it costs no quota and reaches no provider.
    The digest is compared against a capture taken independently, by different code, from the
    same binary: agreement is what makes this a measurement rather than a self-report.
    """

    home, workspace = probe_workspace
    specifications = PROBE.capture_tool_specification(
        codex_home=home,
        workspace=workspace,
        child_profile="scan_low",
        child_profile_config=(
            ROOT / "plugins" / "verified-workflows" / "agents" / "scan_low.toml"
        ),
    )

    children = [item for item in specifications if item["turn_is_spawned_child"]]
    assert len(children) == 1
    child = children[0]
    assert child["model"] == "gpt-5.6-terra"
    assert child["reasoning_effort"] == "low"
    assert child["namespaces"]["collaboration"] == [
        "followup_task",
        "interrupt_agent",
        "list_agents",
        "send_message",
        "spawn_agent",
        "wait_agent",
    ]
    assert child["definitions_sha256"] == CHILD_DEFINITIONS_SHA256
def test_a_requested_child_capture_cannot_silently_become_root_only() -> None:
    """"Some request was recorded" is not "the requested capture happened".

    With an unreadable child profile this returned three root turns and reported success, so a
    proof unit asking about a CHILD's tool specification would have been handed the root's.
    """

    root_only = [{"turn_is_spawned_child": False} for _ in range(3)]

    with pytest.raises(PROBE.CapabilityProbeError, match="the child never spawned"):
        PROBE._require_requested_child(root_only, child_requested=True)

    # A root-only capture nobody asked for a child from is not a failure.
    PROBE._require_requested_child(root_only, child_requested=False)

    # One child among several root turns is what a real spawn produces.
    PROBE._require_requested_child(
        [*root_only, {"turn_is_spawned_child": True}], child_requested=True
    )