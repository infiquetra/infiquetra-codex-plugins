"""Producer-driven tests for the Codex Hermes profile-evolution adapter."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import shutil
from pathlib import Path
from subprocess import CompletedProcess

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/hermes-profile-evolution"
FIXTURES = PLUGIN / "conformance"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


request = load_module("codex_profile_request", PLUGIN / "scripts/profile_request.py")
advisory = load_module("codex_profile_advisory", PLUGIN / "hooks/advisory.py")
CLASSIFIER_FIXTURE = json.loads((FIXTURES / "profile-change-classifier.v1.json").read_text())
COMMAND_FIXTURE = json.loads((FIXTURES / "profile-request-cli.v1.json").read_text())
REPORTS = {case["id"]: case["expected"] for case in CLASSIFIER_FIXTURE["cases"]}
COMMAND_CASES = {case["case_id"]: case for case in COMMAND_FIXTURE["cases"]}


def completed(
    case_id: str,
    *,
    target: str = "brokkr",
    proposal_id: str | None = None,
    revision_digest: str | None = None,
) -> CompletedProcess[bytes]:
    values = json.loads(json.dumps(COMMAND_CASES[case_id]["expected"]["stdout_json"]))
    if case_id == "doctor":
        values = [
            {
                "credential_available": True,
                "route_registered": True,
                "service_available": True,
                "target": target,
            }
        ]
    elif isinstance(values[-1], dict):
        values[-1]["target"] = target
        if proposal_id is not None and "proposal_id" in values[-1]:
            values[-1]["proposal_id"] = proposal_id
        if revision_digest is not None:
            values[-1]["proposal_revision_digest"] = revision_digest
    stdout = b"\n".join(json.dumps(value).encode() for value in values)
    return CompletedProcess([case_id], 0, stdout, b"")


def test_imported_conformance_bytes_match_closed_provenance() -> None:
    provenance = json.loads((FIXTURES / "provenance.json").read_text())
    assert provenance["closed_schema"] is True
    for artifact in provenance["artifacts"]:
        imported = FIXTURES / Path(artifact["producer_path"]).name
        assert hashlib.sha256(imported.read_bytes()).hexdigest() == artifact["sha256"]


def test_native_plugin_skill_and_hook_surfaces_are_discoverable() -> None:
    manifest = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text())
    hooks = json.loads((PLUGIN / "hooks/hooks.json").read_text())
    assert manifest["skills"] == "./skills/"
    assert manifest["hooks"] == "./hooks/hooks.json"
    assert hooks["hooks"]["PreToolUse"][0]["matcher"] == "apply_patch|Edit|Write"
    assert not (PLUGIN / ".claude-plugin").exists()
    assert not (PLUGIN / "commands").exists()
    assert not (PLUGIN / "hooks/manifest.json").exists()


def test_installed_skill_path_resolves_bundled_adapter_without_plugin_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installed = tmp_path / "cache/infiquetra/hermes-profile-evolution/0.1.1"
    shutil.copytree(PLUGIN, installed)
    skill = installed / "skills/hermes-profile-evolution/SKILL.md"
    monkeypatch.delenv("PLUGIN_ROOT", raising=False)

    assert (skill.parent / "../../scripts/profile_request.py").resolve().is_file()
    assert "$PLUGIN_ROOT" not in skill.read_text(encoding="utf-8")


def test_classifier_report_shape_is_derived_from_producer_fixture() -> None:
    report = REPORTS["target-owned"]
    assert request.validate_classifier_report(report, ["profiles/brokkr/SOUL.md"]) == report
    rejected = {**report, "status": "candidate-only"}
    with pytest.raises(request.AdapterError, match="incompatible"):
        request.validate_classifier_report(rejected, ["profiles/brokkr/SOUL.md"])


def test_ordinary_repository_request_does_not_contact_hermes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(request, "resolve_team_mimir_root", lambda _cwd: Path("/team-mimir"))
    monkeypatch.setattr(request, "classify_paths", lambda *_: REPORTS["ordinary-repository"])
    monkeypatch.setattr(request, "_run_hermes", lambda *_: pytest.fail("Hermes must not run"))
    result = request.suggest(
        "brokkr",
        {
            "schema_version": 1,
            "intent": "Clarify repository documentation.",
            "paths": ["docs/team/README.md"],
            "evidence_references": [],
        },
        cwd="/team-mimir",
    )
    assert result["action"] == "ordinary_repository_edit"


@pytest.mark.parametrize("report_id", ["target-owned", "mixed-target-and-ordinary"])
def test_governed_request_uses_exact_doctor_then_suggest_on_stdin(
    monkeypatch: pytest.MonkeyPatch, report_id: str
) -> None:
    calls: list[tuple[list[str], bytes | None]] = []

    def fake_run(arguments: list[str], payload: bytes | None = None):
        calls.append((arguments, payload))
        if arguments[0] == "doctor":
            return completed("doctor", target=arguments[-1])
        assert payload is not None
        envelope = json.loads(payload)
        return completed(
            "suggest",
            target=envelope["target"],
            proposal_id=envelope["proposal_id"],
            revision_digest=envelope["revision_digest"],
        )

    monkeypatch.setattr(request, "resolve_team_mimir_root", lambda _cwd: Path("/team-mimir"))
    monkeypatch.setattr(request, "classify_paths", lambda *_: REPORTS[report_id])
    monkeypatch.setattr(request, "_run_hermes", fake_run)
    result = request.suggest(
        "brokkr",
        {
            "schema_version": 1,
            "intent": "Consider a review-preference clarification.",
            "paths": [verdict["path"] for verdict in REPORTS[report_id]["paths"]],
            "evidence_references": ["docs/team/README.md"],
        },
        cwd="/team-mimir",
    )
    assert result["action"] == "hermes_dialogue"
    assert calls[0] == (["doctor", "--target", "brokkr"], None)
    assert calls[1][0] == ["suggest"]
    assert calls[1][1] is not None
    envelope = json.loads(calls[1][1])
    assert set(envelope) == set(COMMAND_FIXTURE["contracts"]["proposal_fields"])
    assert envelope["target"] == "brokkr"


def test_classifier_target_must_match_caller_target_before_hermes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(request, "resolve_team_mimir_root", lambda _cwd: Path("/team-mimir"))
    monkeypatch.setattr(request, "classify_paths", lambda *_: REPORTS["target-owned"])
    monkeypatch.setattr(request, "_run_hermes", lambda *_: pytest.fail("Hermes must not run"))

    with pytest.raises(request.AdapterError, match="does not match"):
        request.suggest(
            "eitri",
            {
                "schema_version": 1,
                "intent": "Consider this bounded change.",
                "paths": ["profiles/brokkr/SOUL.md"],
                "evidence_references": [],
            },
            cwd="/team-mimir",
        )


@pytest.mark.parametrize(
    "report_id",
    [
        "external-source-custody",
        "prohibited-secret-file",
        "unknown-path",
        "mixed-target-and-external",
    ],
)
def test_non_dialogue_dispositions_do_not_contact_hermes(
    monkeypatch: pytest.MonkeyPatch, report_id: str
) -> None:
    monkeypatch.setattr(request, "resolve_team_mimir_root", lambda _cwd: Path("/team-mimir"))
    monkeypatch.setattr(request, "classify_paths", lambda *_: REPORTS[report_id])
    monkeypatch.setattr(request, "_run_hermes", lambda *_: pytest.fail("Hermes must not run"))
    report = REPORTS[report_id]

    result = request.suggest(
        "brokkr",
        {
            "schema_version": 1,
            "intent": "Classify this bounded request.",
            "paths": [verdict["path"] for verdict in report["paths"]],
            "evidence_references": [],
        },
        cwd="/team-mimir",
    )

    assert result == {"action": "non_dialogue_disposition", "classification": report}


def test_cross_target_request_fails_closed_before_hermes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(request, "resolve_team_mimir_root", lambda _cwd: Path("/team-mimir"))
    monkeypatch.setattr(request, "classify_paths", lambda *_: REPORTS["cross-target-aggregation"])
    monkeypatch.setattr(request, "_run_hermes", lambda *_: pytest.fail("Hermes must not run"))

    with pytest.raises(request.AdapterError, match="separate request per target"):
        request.suggest(
            "brokkr",
            {
                "schema_version": 1,
                "intent": "Consider both profile changes.",
                "paths": [
                    verdict["path"] for verdict in REPORTS["cross-target-aggregation"]["paths"]
                ],
                "evidence_references": [],
            },
            cwd="/team-mimir",
        )


@pytest.mark.parametrize("field", ["target", "proposal_id", "proposal_revision_digest"])
def test_mismatched_hermes_summary_is_rejected(monkeypatch: pytest.MonkeyPatch, field: str) -> None:
    def fake_run(arguments: list[str], payload: bytes | None = None):
        if arguments[0] == "doctor":
            return completed("doctor", target="brokkr")
        assert payload is not None
        envelope = json.loads(payload)
        values = json.loads(json.dumps(COMMAND_CASES["suggest"]["expected"]["stdout_json"]))
        summary = values[-1]
        summary.update(
            {
                "target": envelope["target"],
                "proposal_id": envelope["proposal_id"],
                "proposal_revision_digest": envelope["revision_digest"],
            }
        )
        summary[field] = "mismatch" if field != "proposal_revision_digest" else "f" * 64
        stdout = b"\n".join(json.dumps(value).encode() for value in values)
        return CompletedProcess([], 0, stdout, b"")

    monkeypatch.setattr(request, "resolve_team_mimir_root", lambda _cwd: Path("/team-mimir"))
    monkeypatch.setattr(request, "classify_paths", lambda *_: REPORTS["target-owned"])
    monkeypatch.setattr(request, "_run_hermes", fake_run)

    with pytest.raises(request.AdapterError, match="mismatched"):
        request.suggest(
            "brokkr",
            {
                "schema_version": 1,
                "intent": "Consider this bounded change.",
                "paths": ["profiles/brokkr/SOUL.md"],
                "evidence_references": [],
            },
            cwd="/team-mimir",
        )


@pytest.mark.parametrize(
    "doctor_value",
    [
        {"status": "ok", "schema_version": 1},
        {"target": "brokkr", "route_registered": True, "credential_available": True},
        {
            "target": "brokkr",
            "route_registered": True,
            "credential_available": True,
            "service_available": True,
            "invented": True,
        },
    ],
)
def test_candidate_or_invented_doctor_fields_are_rejected(
    monkeypatch: pytest.MonkeyPatch, doctor_value: dict[str, object]
) -> None:
    monkeypatch.setattr(
        request,
        "_run_hermes",
        lambda *_: CompletedProcess([], 0, json.dumps(doctor_value).encode(), b""),
    )
    with pytest.raises(request.AdapterError, match="unavailable or incompatible"):
        request.doctor("brokkr")


@pytest.mark.parametrize("target", ["x", "default", "-bad", "UPPER", "a" * 65])
def test_invalid_targets_are_rejected_from_producer_bounds(target: str) -> None:
    with pytest.raises(request.AdapterError):
        request.validate_target(target)


def test_secret_oversized_and_malformed_requests_fail_without_echo(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    secret = "api_key=abcdefghijklmnop"
    with pytest.raises(request.AdapterError, match="secret-bearing"):
        request.build_envelope("brokkr", secret, [])
    with pytest.raises(request.AdapterError, match="outside producer bounds"):
        request.build_envelope("brokkr", "x" * 8193, [])
    monkeypatch.setattr(request.sys, "stdin", io.TextIOWrapper(io.BytesIO(b"{not-json")))
    assert request.main(["suggest", "brokkr"]) == 2
    assert secret not in capsys.readouterr().err


def test_classifier_subprocess_failure_and_output_drift_do_not_leak_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sensitive_path = "profiles/brokkr/private-name.txt"
    classifier = tmp_path / "scripts/classify_profile_change.py"
    classifier.parent.mkdir()
    classifier.write_text("raise SystemExit(1)\n", encoding="utf-8")
    monkeypatch.setattr(
        request.subprocess,
        "run",
        lambda *_args, **_kwargs: CompletedProcess([], 1, b"", b"sensitive producer error"),
    )
    with pytest.raises(request.AdapterError, match="did not complete") as exc:
        request.classify_paths([sensitive_path], tmp_path)
    assert sensitive_path not in str(exc.value)


def test_service_failure_and_unexpected_output_are_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(request, "_run_hermes", lambda *_: CompletedProcess([], 1, b"", b"private"))
    with pytest.raises(request.AdapterError, match="did not complete"):
        request._validated_output("suggest", request._run_hermes([]))
    with pytest.raises(request.AdapterError, match="unexpected output"):
        request._validated_output("suggest", CompletedProcess([], 0, b'{"invented":true}', b""))


def test_adapter_timeout_does_not_preempt_the_producer_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def fake_run(*args, **kwargs):
        observed.update(kwargs)
        return CompletedProcess(args[0], 0, b"", b"")

    monkeypatch.setattr(request.subprocess, "run", fake_run)

    request._run_hermes(["doctor", "--target", "brokkr"])

    assert observed["timeout"] == 45
    assert request.COMMAND_TIMEOUT_SECONDS > 30


def test_reply_resume_and_status_follow_producer_command_shapes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], bytes | None]] = []

    def fake_run(arguments: list[str], payload: bytes | None = None):
        calls.append((arguments, payload))
        if arguments[0] == "doctor":
            return completed("doctor", target=arguments[-1])
        if arguments[0] == "status":
            return completed("status", target=arguments[-1], revision_digest=arguments[-3])
        assert payload is not None
        proposal = json.loads(payload)
        return completed(
            arguments[0],
            target=proposal["target"],
            proposal_id=proposal["proposal_id"],
            revision_digest=proposal["revision_digest"],
        )

    monkeypatch.setattr(request, "_run_hermes", fake_run)
    envelope = request.build_envelope("brokkr", "Consider this change.", [])
    reply = request.continue_dialogue(
        "reply", {"schema_version": 1, "proposal": envelope, "message": "Please compare it."}
    )
    resume = request.continue_dialogue("resume", {"schema_version": 1, "proposal": envelope})
    status = request.status("proposal-12345678", "a" * 64, "brokkr")
    assert reply["action"] == resume["action"] == "hermes_dialogue"
    assert status and calls[-1][0][0] == "status"
    assert calls[1][0] == ["reply", "--message", "Please compare it."]
    assert calls[1][1] is not None


def recompute_revision(proposal: dict[str, object]) -> None:
    body = {
        key: proposal[key]
        for key in (
            "schema_version",
            "target",
            "requester",
            "delegation_chain",
            "intent",
            "evidence_references",
        )
    }
    proposal["revision_digest"] = hashlib.sha256(request._canonical(body)).hexdigest()


@pytest.mark.parametrize("action", ["reply", "resume"])
@pytest.mark.parametrize("actor_location", ["requester", "delegation_chain"])
def test_continuation_rejects_nested_secret_actor_before_hermes(
    monkeypatch: pytest.MonkeyPatch, action: str, actor_location: str
) -> None:
    secret = "token=abcdefghijklmnop"
    proposal = request.build_envelope("brokkr", "Consider this change.", [])
    if actor_location == "requester":
        proposal["requester"]["actor_id"] = secret
    else:
        proposal["delegation_chain"][0]["actor_id"] = secret
    recompute_revision(proposal)
    payload = {"schema_version": 1, "proposal": proposal}
    if action == "reply":
        payload["message"] = "Please compare it."
    monkeypatch.setattr(request, "_run_hermes", lambda *_: pytest.fail("Hermes must not run"))

    with pytest.raises(request.AdapterError, match="secret-bearing") as exc:
        request.continue_dialogue(action, payload)
    assert secret not in str(exc.value)


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("extra_requester_field", "closed producer schema"),
        ("invalid_actor_kind", "is invalid"),
        ("excessive_chain", "outside producer bounds"),
        ("verified_profile", "cannot claim verified profile"),
    ],
)
def test_continuation_rejects_invalid_actor_contract_before_hermes(
    monkeypatch: pytest.MonkeyPatch, mutation: str, error: str
) -> None:
    proposal = request.build_envelope("brokkr", "Consider this change.", [])
    if mutation == "extra_requester_field":
        proposal["requester"]["extra"] = "unsupported"
    elif mutation == "invalid_actor_kind":
        proposal["requester"]["actor_kind"] = "invented"
    elif mutation == "excessive_chain":
        proposal["delegation_chain"] = proposal["delegation_chain"] * 33
    else:
        proposal["requester"] = {
            "actor_kind": "profile",
            "actor_id": "eitri",
            "verification": "verified",
            "source_event_digest": "a" * 64,
        }
    recompute_revision(proposal)
    monkeypatch.setattr(request, "_run_hermes", lambda *_: pytest.fail("Hermes must not run"))

    with pytest.raises(request.AdapterError, match=error):
        request.continue_dialogue("resume", {"schema_version": 1, "proposal": proposal})


def hook_payload(path: str) -> dict[str, object]:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "apply_patch",
        "cwd": "/team-mimir",
        "tool_input": {"command": f"*** Begin Patch\n*** Update File: {path}\n*** End Patch"},
    }


def run_hook(monkeypatch: pytest.MonkeyPatch, payload: bytes, report: dict[str, object]) -> int:
    fake_adapter = type(
        "FakeAdapter",
        (),
        {
            "AdapterError": request.AdapterError,
            "resolve_team_mimir_root": staticmethod(lambda _cwd: Path("/team-mimir")),
            "validate_paths": staticmethod(lambda paths: paths),
            "classify_paths": staticmethod(lambda *_: report),
        },
    )
    monkeypatch.setattr(advisory, "_adapter", lambda: fake_adapter)
    monkeypatch.setattr(advisory.sys, "stdin", io.TextIOWrapper(io.BytesIO(payload)))
    return advisory.main()


def test_hook_allows_ordinary_edit_without_hermes_or_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        run_hook(
            monkeypatch,
            json.dumps(hook_payload("docs/team/README.md")).encode(),
            REPORTS["ordinary-repository"],
        )
        == 0
    )
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("report_id", ["target-owned", "mixed-target-and-ordinary"])
def test_hook_advisory_stop_is_native_bounded_and_truthful(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], report_id: str
) -> None:
    path = REPORTS[report_id]["paths"][0]["path"]
    assert run_hook(monkeypatch, json.dumps(hook_payload(path)).encode(), REPORTS[report_id]) == 0
    output = json.loads(capsys.readouterr().out)
    specific = output["hookSpecificOutput"]
    assert specific["hookEventName"] == "PreToolUse"
    assert specific["permissionDecision"] == "deny"
    reason = specific["permissionDecisionReason"]
    assert "hermes-profile-evolution skill" in reason and "`brokkr`" in reason
    assert "same-user" in reason and "root" in reason and "advisory" in reason


def test_malformed_hook_input_stops_without_leaking_input(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    private = b'{"private":"do-not-print"'
    monkeypatch.setattr(advisory.sys, "stdin", io.TextIOWrapper(io.BytesIO(private)))
    assert advisory.main() == 0
    output = capsys.readouterr().out
    assert "do-not-print" not in output
    assert json.loads(output)["hookSpecificOutput"]["permissionDecision"] == "deny"


def make_team_mimir_root(root: Path) -> None:
    (root / "profiles").mkdir(parents=True)
    (root / "deploy").mkdir()
    (root / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
    (root / "deploy/team_profiles.yml").write_text("profiles: []\n", encoding="utf-8")


def test_hook_allows_unrelated_repository_when_classifier_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = hook_payload("README.md")
    payload["cwd"] = str(tmp_path)
    monkeypatch.delenv("HERMES_TEAM_MIMIR_ROOT", raising=False)
    monkeypatch.setattr(advisory, "_adapter", lambda: request)
    monkeypatch.setattr(
        advisory.sys, "stdin", io.TextIOWrapper(io.BytesIO(json.dumps(payload).encode()))
    )

    assert advisory.main() == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("failure", ["missing", "failing"])
def test_hook_denies_recognized_team_mimir_when_classifier_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    make_team_mimir_root(tmp_path)
    payload = hook_payload("profiles/brokkr/SOUL.md")
    payload["cwd"] = str(tmp_path)
    monkeypatch.delenv("HERMES_TEAM_MIMIR_ROOT", raising=False)
    monkeypatch.setattr(advisory, "_adapter", lambda: request)
    if failure == "failing":
        monkeypatch.setattr(
            request,
            "classify_paths",
            lambda *_: (_ for _ in ()).throw(request.AdapterError("classifier failed")),
        )
    monkeypatch.setattr(
        advisory.sys, "stdin", io.TextIOWrapper(io.BytesIO(json.dumps(payload).encode()))
    )

    assert advisory.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_adapter_source_has_no_copied_classifier_or_invented_doctor_schema() -> None:
    source = (PLUGIN / "scripts/profile_request.py").read_text()
    assert "DISPOSITION_BY_CATEGORY" not in source
    assert "hooks/manifest.json" not in source
    assert 'required = {"target", "route_registered"' not in source
