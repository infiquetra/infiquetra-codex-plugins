"""Focused branch coverage for U6 trust boundaries and degraded read paths."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).parent.parent
SCRIPT_DIR = ROOT / "plugins" / "saga" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import engine_bridge_http as HTTP  # noqa: E402
import engine_registry as REG  # noqa: E402
import engine_resolver as RES  # noqa: E402
import outcome_github as GH  # noqa: E402
import workflow_emitter as WE  # noqa: E402

REGISTRY_PATH = ROOT / "plugins" / "saga" / "references" / "engine-registry.yaml"


def _result(out: str = "", *, rc: int = 0, err: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=rc, stdout=out, stderr=err)


def _runner(out: str = "", *, rc: int = 0, err: str = "") -> Any:
    return lambda *_args, **_kwargs: _result(out, rc=rc, err=err)


def _registry_data() -> dict[str, Any]:
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _registry() -> REG.Registry:
    return REG.Registry.load(REGISTRY_PATH)


def test_run_gh_covers_success_failure_and_process_errors() -> None:
    assert GH._run_gh(["x"], runner=_runner(" ok \n", err=" note ")) == (0, "ok", "note")
    assert GH._run_gh(["x"], runner=_runner("ignored", rc=3, err=" bad ")) == (1, "", "bad")

    def raises(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("missing")

    assert GH._run_gh(["x"], runner=raises) == (1, "", "missing")

    def times_out(*_args: Any, **_kwargs: Any) -> None:
        raise subprocess.TimeoutExpired("gh", 20)

    assert GH._run_gh(["x"], runner=times_out)[0] == 1


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"state": "OPEN", "mergedAt": "2026-01-01"}, "merged"),
        ({"state": "MERGED", "mergedAt": None}, "merged"),
        ({"state": "CLOSED"}, "closed"),
        ({"state": "OPEN"}, "open"),
        ({"state": "ODD"}, "unknown"),
        ([], "unknown"),
    ],
)
def test_pr_state_variants(payload: Any, expected: str) -> None:
    assert GH.pr_state("owner/repo#1", runner=_runner(json.dumps(payload))) == expected


@pytest.mark.parametrize("out", ["", "{", "null"])
def test_pr_state_degrades_on_empty_or_malformed_data(out: str) -> None:
    assert GH.pr_state("1", runner=_runner(out)) == "unknown"
    assert GH.pr_state("1", runner=_runner(rc=1)) == "unknown"


@pytest.mark.parametrize(
    ("payload", "expected"),
    [({"state": "CLOSED"}, "closed"), ({"state": "OPEN"}, "open"), ({}, "unknown"), ([], "unknown")],
)
def test_issue_state_variants(payload: Any, expected: str) -> None:
    assert GH.issue_state("owner/repo#2", runner=_runner(json.dumps(payload))) == expected


@pytest.mark.parametrize("out", ["", "{", "null"])
def test_issue_state_degrades_on_bad_reads(out: str) -> None:
    assert GH.issue_state("2", runner=_runner(out)) == "unknown"


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"projectItems": [{"title": "Operations", "status": {"name": "Done"}}]}, "Done"),
        ({"projectItems": [None, {"title": "Other", "status": {"name": "Done"}}]}, ""),
        ({"projectItems": [{"title": "operations", "status": None}]}, ""),
        ({"projectItems": [{"title": "operations", "status": {"name": ""}}]}, ""),
        ({"projectItems": {}}, ""),
        ([], ""),
    ],
)
def test_board_status_variants(payload: Any, expected: str) -> None:
    assert GH.board_status("o/r#3", project=" operations ", runner=_runner(json.dumps(payload))) == expected


@pytest.mark.parametrize("out", ["", "{", "null"])
def test_board_status_degrades_on_bad_reads(out: str) -> None:
    assert GH.board_status("3", project="x", runner=_runner(out)) == ""


def test_closed_by_uses_last_valid_close_actor() -> None:
    events = [
        {"event": "closed", "actor": {"login": "first"}},
        {"event": "reopened", "actor": {"login": "other"}},
        {"event": "closed", "actor": {}},
        {"event": "closed", "actor": {"login": "last"}},
    ]
    assert GH._closed_by("o/r#4", runner=_runner(json.dumps(events))) == "last"
    assert GH._closed_by("4", runner=_runner(json.dumps(events))) == ""


@pytest.mark.parametrize("out", ["", "{", "{}"])
def test_closed_by_degrades_on_bad_event_reads(out: str) -> None:
    assert GH._closed_by("o/r#4", runner=_runner(out)) == ""
    assert GH._closed_by("o/r#4", runner=_runner(rc=1)) == ""


def test_issue_close_info_normalizes_reason_and_actor() -> None:
    calls = 0

    def runner(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _result(json.dumps({"state": "CLOSED", "stateReason": "NOT_PLANNED"}))
        return _result(json.dumps([{"event": "closed", "actor": {"login": "closer"}}]))

    assert GH.issue_close_info("o/r#5", runner=runner) == {
        "state": "closed",
        "state_reason": "not_planned",
        "closed_by": "closer",
    }
    assert GH.issue_close_info("5", runner=_runner(json.dumps({"state": "OPEN", "stateReason": "REOPENED"}))) == {
        "state": "open",
        "state_reason": "reopened",
        "closed_by": "",
    }


@pytest.mark.parametrize("out", ["", "{", "[]", "{}"])
def test_issue_close_info_degrades_on_bad_reads(out: str) -> None:
    result = GH.issue_close_info("5", runner=_runner(out, rc=0 if out else 1))
    assert result["state"] == "unknown"
    assert result["state_reason"] == "unknown"


@pytest.mark.parametrize("function,key", [(GH.base_ref_oid, "baseRefOid"), (GH.head_ref_oid, "headRefOid")])
def test_pr_oid_reads_cover_success_and_degraded_shapes(function: Any, key: str) -> None:
    assert function("1", runner=_runner(json.dumps({key: "abc"}))) == "abc"
    assert function("1", runner=_runner(json.dumps([]))) == ""
    assert function("1", runner=_runner("{")) == ""
    assert function("1", runner=_runner(rc=1)) == ""


@pytest.mark.parametrize("state", list(GH.MERGE_STATES))
def test_merge_state_accepts_closed_vocabulary(state: str) -> None:
    assert GH.merge_state("1", runner=_runner(json.dumps({"mergeStateStatus": state.upper()}))) == state


@pytest.mark.parametrize("out", ["", "{", "[]", '{"mergeStateStatus":"weird"}'])
def test_merge_state_degrades_on_bad_reads(out: str) -> None:
    assert GH.merge_state("1", runner=_runner(out, rc=0 if out else 1)) == "unknown"


def test_branch_update_merge_and_cli_paths(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert GH.branch_exists("feat", runner=_runner("refs/heads/feat"))
    assert not GH.branch_exists("feat", runner=_runner(rc=1, err="not found"))
    assert GH.branch_exists("feat", runner=_runner(rc=1, err="temporary"))
    assert GH.update_branch("1", runner=_runner())
    assert not GH.update_branch("1", runner=_runner(rc=1))
    assert GH.squash_merge("1", expected_head="abc", runner=_runner()) == "merged"
    assert GH.squash_merge("1", runner=_runner(rc=1)) == "error"

    monkeypatch.setattr(GH, "pr_state", lambda _ref: "merged")
    assert GH.main(["pr-state", "1"]) == 0
    assert json.loads(capsys.readouterr().out)["state"] == "merged"
    monkeypatch.setattr(GH, "issue_state", lambda _ref: "closed")
    assert GH.main(["issue-state", "2"]) == 0
    assert json.loads(capsys.readouterr().out)["state"] == "closed"


def _valid_verdict() -> dict[str, Any]:
    return {
        "refuted": [],
        "upheld": [],
        "verifier_identity": "seat-1",
        "fallback_depth": 0,
        "examined_sha": "a" * 40,
        "workspace_clean": True,
    }


def test_workflow_intent_helpers_cover_errors_and_selector_shapes() -> None:
    assert WE.merge_engine_intents([]) is None
    assert WE.merge_engine_intents([None, "offload", "divergence"]) == "divergence"
    with pytest.raises(ValueError, match="unknown"):
        WE.merge_engine_intents(["bad"])
    assert WE.external_engine_marker(engine=None, capability=None, intent=None) is None
    with pytest.raises(ValueError, match="mutually"):
        WE.external_engine_marker(engine="a", capability="b", intent=None)
    with pytest.raises(ValueError, match="requires"):
        WE.external_engine_marker(engine=None, capability=None, intent="offload")
    with pytest.raises(ValueError, match="unknown"):
        WE.external_engine_marker(engine="a", capability=None, intent="bad")
    assert "engine=a" in str(WE.external_engine_marker(engine="a", capability=None, intent=None))
    assert "capability=c" in str(WE.external_engine_marker(engine=None, capability="c", intent="second-opinion"))
    assert WE.external_engine_record(unit_id="u", engine=None, capability=None, intent=None) is None
    assert WE.external_engine_record(unit_id="u", engine="a", capability=None, intent=None)["engine"] == "a"
    assert WE.external_engine_record(unit_id="u", engine=None, capability="c", intent=None)["capability"] == "c"


@pytest.mark.parametrize(
    "changes",
    [
        None,
        {"refuted": "bad"},
        {"upheld": "bad"},
        {"verifier_identity": ""},
        {"fallback_depth": True},
        {"fallback_depth": -1},
        {"examined_sha": "z" * 40},
        {"workspace_clean": False},
    ],
)
def test_verifier_verdict_rejects_each_invalid_shape(changes: dict[str, Any] | None) -> None:
    candidate: object = None
    if changes is not None:
        candidate = {**_valid_verdict(), **changes}
    assert not WE.valid_verifier_verdict(candidate)


def test_verifier_verdict_expected_bindings_and_fallback_marker() -> None:
    value = _valid_verdict()
    assert WE.valid_verifier_verdict(value, expected_identity="seat-1", expected_fallback_depth=0, expected_examined_sha="a" * 40)
    assert not WE.valid_verifier_verdict(value, expected_identity="other")
    assert not WE.valid_verifier_verdict(value, expected_fallback_depth=1)
    assert not WE.valid_verifier_verdict(value, expected_examined_sha="b" * 40)
    assert WE.render_fallback_tier_marker([value]) == ""
    assert WE.render_fallback_tier_marker([
        {"fallback_depth": True, "verifier_identity": "skip"},
        {"fallback_depth": "1", "verifier_identity": "skip"},
        {"fallback_depth": 2, "verifier_identity": ""},
        {"fallback_depth": 1, "verifier_identity": "seat"},
    ]) == " — fallback tier 2 (unknown-verifier); fallback tier 1 (seat)"


def test_registry_closed_capability_and_date_validation_branches() -> None:
    data = _registry_data()
    for capabilities, match in [([1], "not a string"), (["unknown"], "unknown"), ([*REG.CAPABILITIES, REG.CAPABILITIES[0]], "duplicate"), (list(REG.CAPABILITIES[:-1]), "missing")]:
        bad = dict(data)
        bad["capabilities"] = capabilities
        with pytest.raises(REG.RegistryError, match=match):
            REG.Registry.from_dict(bad)
    assert REG._parse_date(datetime(2026, 1, 1), "x") == date(2026, 1, 1)
    assert REG._parse_date(date(2026, 1, 2), "x") == date(2026, 1, 2)
    with pytest.raises(REG.RegistryError, match="ISO"):
        REG._parse_date("bad", "x")
    with pytest.raises(REG.RegistryError, match="ISO"):
        REG._parse_date(1, "x")


def test_registry_profile_family_and_http_url_validation_branches() -> None:
    with pytest.raises(REG.RegistryError, match="at least"):
        REG._parse_capability_profile({}, "x")
    with pytest.raises(REG.RegistryError, match="unknown"):
        REG._parse_capability_profile({"bad": {"rating": "STRONG"}}, "x")
    with pytest.raises(REG.RegistryError, match="rating"):
        REG._parse_capability_profile({REG.CAPABILITIES[0]: {"rating": "BAD"}}, "x")
    with pytest.raises(REG.RegistryError, match="model identity"):
        REG._parse_model_families({"model_families": {1: {}}})
    family = {"model_families": {"m": {"capability_profile": {REG.CAPABILITIES[0]: {"rating": "STRONG"}}}}}
    parsed = REG._parse_model_families(family)
    assert REG._materialize_family_defaults({"model_identity": "other"}, parsed, "x")["model_identity"] == "other"
    merged = REG._materialize_family_defaults({"model_identity": "m", "capability_profile": {REG.CAPABILITIES[0]: {"rating": "MODERATE"}}}, parsed, "x")
    assert merged["capability_profile"][REG.CAPABILITIES[0]]["rating"] == "MODERATE"
    for url in ["https://user@example.com", "https://example.com?x=1", "https://localhost", "https://10.0.0.1"]:
        with pytest.raises(REG.RegistryError, match="base_url"):
            REG._validate_http_base_url(url, "x")


def test_registry_auth_parsing_branches() -> None:
    with pytest.raises(REG.RegistryError, match="missing"):
        REG._parse_auth({"cli": "x"}, "cli", "x")
    with pytest.raises(REG.RegistryError, match="closed vocabulary"):
        REG._parse_auth({"cli": "x", "auth": {"mode": "bad"}}, "cli", "x")
    with pytest.raises(REG.RegistryError, match="requires"):
        REG._parse_auth({"auth": {"mode": "env", "key_env": "K"}}, "http", "x")
    with pytest.raises(REG.RegistryError, match="must not be empty"):
        REG._parse_auth({"cli": "x", "auth": {"mode": "files", "paths": []}}, "cli", "x")
    with pytest.raises(REG.RegistryError, match=r"paths\[0\]"):
        REG._parse_auth({"cli": "x", "auth": {"mode": "files", "paths": [""]}}, "cli", "x")
    assert REG._parse_auth({"cli": "x", "auth": {"mode": "files", "paths": ["a"]}}, "cli", "x")["paths"] == ["a"]
    assert REG._parse_auth({"cli": "x", "auth": {"mode": "env", "key_env": "KEY"}}, "cli", "x")["mode"] == "env"
    assert REG._parse_auth({"cli": "x", "auth": {"mode": "secret-ref", "ref": "r"}}, "cli", "x")["ref"] == "r"


def test_registry_lookup_and_panel_validation_branches() -> None:
    registry = _registry()
    with pytest.raises(REG.RegistryError, match="unknown engine"):
        registry.by_engine("missing")
    with pytest.raises(REG.RegistryError, match="unknown role"):
        registry.by_role("missing")
    role = registry.by_role("cross-family-review-panel")
    assert role.members
    assert REG.validate_panel_role("panel-name") is None
    with pytest.raises(REG.RegistryError, match="normalized"):
        REG.validate_panel_role("Bad Name", registry=registry)
    with pytest.raises(REG.RegistryError, match="zero members"):
        REG.validate_panel_role(
            "zero",
            registry=REG.Registry(
                registry.capabilities,
                registry.engines,
                {"zero": replace(role, name="zero", members=[])},
            ),
        )
    with pytest.raises(REG.RegistryError, match="PANEL_N_CAP"):
        REG.validate_panel_role(
            "many",
            registry=REG.Registry(
                registry.capabilities,
                registry.engines,
                {"many": replace(role, name="many", members=role.members * 4)},
            ),
        )
    with pytest.raises(REG.RegistryError, match="advisory"):
        REG.validate_panel_role(
            "bad",
            registry=REG.Registry(
                registry.capabilities,
                registry.engines,
                {"bad": replace(role, name="bad", verdict="gate")},
            ),
        )
    with pytest.raises(REG.RegistryError, match="Codex root"):
        REG.validate_panel_role(
            "bad",
            registry=REG.Registry(
                registry.capabilities,
                registry.engines,
                {"bad": replace(role, name="bad", verifier="other")},
            ),
        )


def test_resolver_preflight_auth_and_memo_branches() -> None:
    registry = _registry()
    cli = next(entry for entry in registry.engines if entry.transport == "cli")
    http = next(entry for entry in registry.engines if entry.transport == "http")
    memo = RES.RunMemo()
    first = RES.preflight(http.engine_id, entry=http, env_get=lambda _key: "token", memo=memo)
    second = RES.preflight(http.engine_id, entry=http, env_get=lambda _key: None, memo=memo)
    assert first == second and first["available"]
    assert not RES.preflight(cli.engine_id, entry=cli, which=lambda _name: None)["available"]
    assert RES._legacy_config_preflight("x", config_exists=lambda _name: True)["available"]
    assert not RES._legacy_config_preflight("x", config_exists=lambda _name: False)["available"]
    assert RES._auth_preflight("x", {"mode": "files", "paths": ["a"]}, file_exists=lambda _p: True, env_get=None, secret_ref_resolves=None)["available"]
    assert not RES._auth_preflight("x", {"mode": "files", "paths": ["a"]}, file_exists=lambda _p: False, env_get=None, secret_ref_resolves=None)["available"]
    assert RES._auth_preflight("x", {"mode": "env", "key_env": "K"}, file_exists=None, env_get=lambda _k: "v", secret_ref_resolves=None)["available"]
    assert not RES._auth_preflight("x", {"mode": "bearer", "key_env": "K"}, file_exists=None, env_get=lambda _k: None, secret_ref_resolves=None)["available"]
    assert not RES._auth_preflight("x", {"mode": "secret-ref", "ref": "r"}, file_exists=None, env_get=None, secret_ref_resolves=None)["available"]
    assert RES._auth_preflight("x", {"mode": "secret-ref", "ref": "r"}, file_exists=None, env_get=None, secret_ref_resolves=lambda _r: True)["available"]
    assert not RES._auth_preflight("x", {"mode": "secret-ref", "ref": "r"}, file_exists=None, env_get=None, secret_ref_resolves=lambda _r: False)["available"]
    assert not RES._auth_preflight("x", {"mode": "bad"}, file_exists=None, env_get=None, secret_ref_resolves=None)["available"]


def test_resolver_payload_cache_and_validation_branches() -> None:
    memo = RES.RunMemo()
    context = {"context": "body", "unit_id": "u"}
    first = RES._assemble_payload_for_unit(["p1", "p2"], context, memo=memo)
    assert RES._assemble_payload_for_unit(["p1", "p2"], context, memo=memo) == first
    assert memo.last_payload_cache_status == "hit"
    assert RES._assemble_payload_for_unit(["p"], {"context": None}, memo=memo) == "p"
    assert memo.last_payload_cache_status == ""
    with pytest.raises(RES.RegistryError, match="context"):
        RES._context_text({"context": 1})
    with pytest.raises(RES.RegistryError, match="unit_id"):
        RES._payload_unit_id({"unit_id": ""})
    with pytest.raises(RES.RegistryError, match="protocol"):
        RES._assert_protocol_preserved(["one", "two"], "oneXtwo")


def test_resolver_entry_selection_and_release_date_branches(tmp_path: Path) -> None:
    registry = _registry()
    entry = registry.engines[0]
    assert RES._entry_for_engine_request(entry.key, registry=registry, task_context={}) == entry
    assert RES._entry_for_engine_request(entry.engine_id, registry=registry, task_context={"variant": entry.variant}) == entry
    with pytest.raises(RES.RegistryError, match="does not belong"):
        RES._entry_for_engine_request(entry.engine_id, registry=registry, task_context={"variant": registry.engines[-1].key})
    with pytest.raises(RES.RegistryError, match="no variant"):
        RES._entry_for_engine_request(entry.engine_id, registry=registry, task_context={"effort": "missing"})
    with pytest.raises(RES.RegistryError, match="unknown engine variant"):
        RES._entry_for_engine_request("missing/value", registry=registry, task_context={})

    missing = tmp_path / "missing.yaml"
    assert RES._load_release_dates(missing) == {}
    for value in ([], {"model_releases": []}):
        path = tmp_path / f"{len(list(tmp_path.iterdir()))}.yaml"
        path.write_text(yaml.safe_dump(value), encoding="utf-8")
        assert RES._load_release_dates(path) == {}


def test_http_bridge_remaining_degraded_branches() -> None:
    assert HTTP._extract_output(b"{}") is None
    assert HTTP._extract_tokens(b"{}") == 0.0
    assert HTTP._extract_tokens(b'{"usage":{"total_tokens":true}}') == 0.0
    assert HTTP._extract_tokens(b'{"usage":{"total_tokens":-1}}') == 0.0
    for url in ["not a url", "http://example.com", "https://localhost", "https://10.0.0.1", "https://user@example.com"]:
        assert HTTP._base_url_error(url)
    assert HTTP._base_url_error("https://example.com") is None
    with pytest.raises(ValueError, match="finite"):
        HTTP.runner(timeout=float("nan"))
