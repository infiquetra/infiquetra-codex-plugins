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


OBSERVED_CODEX_VERSION = "0.147.0"


def _receipt(
    content: bytes,
    *,
    case_id: str = "profile-identity",
    codex_cli_version_observed: str = OBSERVED_CODEX_VERSION,
) -> dict[str, object]:
    """Parse a rollout with the harness-stamped fields a real probe would supply."""

    return P.parse_rollout_receipt(
        content,
        case_id=case_id,
        codex_cli_version_observed=codex_cli_version_observed,
    )


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
    path: str = "/root/v2_profile_probe",
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
        "agent_path": "/root/v2_profile_probe",
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
    )

    assert proof["capability_outcome"] == "diagnostic"
    assert proof["tool_namespace"] == "collaboration"
    assert proof["spawn_response_fields"] == ["agent_id", "nickname", "task_name"]
    assert proof["live_invocation_performed"] is False
    assert len(proof["profiles"]) == 7
    assert proof["source_profiles"]["location"] == "plugins/verified-workflows/agents"
    assert proof["source_profiles"]["regular_files_only"] is True
    P.validate_sanitized_proof(proof)


def test_native_model_cache_requires_v2_rows(tmp_path: Path) -> None:
    home = tmp_path / "codex"
    home.mkdir()
    cache = home / "models_cache.json"
    cache.write_text(
        json.dumps(
            {
                "models": [
                    {"slug": "gpt-5.6-sol", "multi_agent_version": "v2"},
                    {"slug": "gpt-5.6-terra", "multi_agent_version": "v1"},
                ]
            }
        ),
        encoding="utf-8",
    )

    path, receipt = P._native_model_cache(home, ("gpt-5.6-sol",))
    assert path == cache
    assert receipt["source"] == "native-model-cache"
    assert receipt["required_v2_models"] == ["gpt-5.6-sol"]
    assert receipt["luna_multi_agent_version"] is None
    with pytest.raises(P.RuntimeProofError, match="not V2"):
        P._native_model_cache(home, ("gpt-5.6-terra",))


def test_rollout_parser_combines_session_meta_and_turn_context() -> None:
    receipt = _receipt(rollout())

    assert receipt == {
        "case_id": "profile-identity",
        "harness_sha256": P.RUNTIME_PROOF_HARNESS_SHA256,
        "codex_cli_version_observed": OBSERVED_CODEX_VERSION,
        "session_id": "child-thread",
        "parent_thread_id": "root-thread",
        "parent_thread_present": True,
        "agent_path": "/root/v2_profile_probe",
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
    receipt = _receipt(rollout(**kwargs))

    with pytest.raises(P.RuntimeProofError, match=field):
        P.validate_runtime_receipt(receipt, expected())


def test_requested_fields_without_runtime_context_fail() -> None:
    content = json.dumps(
        {
            "type": "session_meta",
            "payload": {
                "id": "child",
                "agent_role": "review_high",
                "agent_path": "/root/v2_profile_probe",
            },
        }
    ).encode()

    with pytest.raises(P.RuntimeProofError, match="turn_context"):
        _receipt(content)


def test_nonterminal_or_wrong_terminal_result_fails() -> None:
    receipt = _receipt(rollout(marker="not-the-contract"))

    with pytest.raises(P.RuntimeProofError, match="terminal result"):
        P.validate_runtime_receipt(receipt, expected())


def test_root_only_context_in_child_rollout_fails() -> None:
    receipt = _receipt(rollout(include_parent_marker=True))

    with pytest.raises(P.RuntimeProofError, match="root-only context"):
        P.validate_runtime_receipt(receipt, expected())


def test_a_receipt_without_a_harness_digest_is_refused() -> None:
    """Absent fails the shape check; present-but-empty fails the identity check."""

    stripped = dict(_receipt(rollout()))
    del stripped["harness_sha256"]
    with pytest.raises(P.RuntimeProofError, match=r"missing receipt fields \['harness_sha256'\]"):
        P.validate_runtime_receipt(stripped, expected())

    blank = dict(_receipt(rollout()))
    blank["harness_sha256"] = ""
    with pytest.raises(P.RuntimeProofError, match=r"empty receipt fields \['harness_sha256'\]"):
        P.validate_runtime_receipt(blank, expected())

    foreign = dict(_receipt(rollout()))
    foreign["harness_sha256"] = "f" * 64
    with pytest.raises(P.RuntimeProofError, match="is not the frozen"):
        P.validate_runtime_receipt(foreign, expected())


def test_an_arbitrary_object_cannot_become_a_supported_live_proof() -> None:
    """"Not absent" is not "is evidence": a live proof is the strongest claim here.

    Aimed at `validate_live_projection` rather than `build_proof`, because the latter now refuses
    a non-isolated interpreter before it reaches any shape check at all.
    """

    with pytest.raises(P.RuntimeProofError, match="keys do not match the published projection"):
        P.validate_live_projection({"not_a_projection": True}, "live proof projection")

    with pytest.raises(P.RuntimeProofError, match="is not a live projection object"):
        P.validate_live_projection(["also", "not", "a", "projection"], "live proof projection")

    # Every required key present but saying nothing. Presence was standing in for content.
    hollow = {field: None for field in P.LIVE_PROJECTION_REQUIRED_FIELDS}
    hollow["case_id"] = "profile-identity"
    hollow["harness_sha256"] = P.RUNTIME_PROOF_HARNESS_SHA256
    hollow["codex_cli_version_observed"] = OBSERVED_CODEX_VERSION
    with pytest.raises(P.RuntimeProofError, match="carries no root identity"):
        P.validate_live_projection(hollow, "live proof projection")

    # Sides present but every identity field unset.
    unset = dict(hollow)
    unset["catalog"] = {"observed": True}
    unset["profile_sha256"] = "0" * 64
    unset["root"] = {"model": None, "reasoning_effort": None}
    unset["child"] = {"agent_path": "/root/probe"}
    with pytest.raises(P.RuntimeProofError, match="keys do not match the published projection"):
        P.validate_live_projection(unset, "live proof projection")

    # The exact shape a third round of cross-review reached `capability_outcome = supported`
    # with. Every required key is present, none is null, and both sides are non-empty mappings,
    # which is everything the previous draft checked.
    fabricated = dict(hollow)
    fabricated["catalog"] = True
    fabricated["root"] = {"fabricated": True}
    fabricated["child"] = {"fabricated": True}
    fabricated["profile_sha256"] = True
    with pytest.raises(P.RuntimeProofError, match="keys do not match the published projection"):
        P.validate_live_projection(fabricated, "live proof projection")

    # And a parsed rollout receipt is not a published projection: the two shapes are distinct.
    with pytest.raises(P.RuntimeProofError, match="keys do not match the published projection"):
        P.validate_live_projection(dict(_receipt(rollout())), "live proof projection")


def test_a_receipt_from_a_different_harness_is_refused() -> None:
    """The freeze is the point: an instrument that moved invalidates its own evidence."""

    receipt = dict(_receipt(rollout()))
    receipt["harness_sha256"] = "f" * 64

    with pytest.raises(P.RuntimeProofError, match="is not the frozen"):
        P.validate_runtime_receipt(receipt, expected())


def test_the_frozen_pin_matches_the_harness_files_on_disk() -> None:
    """A pin that has drifted from the files it names would refuse every honest receipt."""

    assert P.harness_sha256() == P.RUNTIME_PROOF_HARNESS_SHA256
    for relative in P.HARNESS_FILES:
        assert (ROOT / relative).is_file(), relative


def test_a_receipt_without_a_declared_case_is_refused() -> None:
    stripped = dict(_receipt(rollout()))
    del stripped["case_id"]
    with pytest.raises(P.RuntimeProofError, match=r"missing receipt fields \['case_id'\]"):
        P.validate_runtime_receipt(stripped, expected())

    blank = dict(_receipt(rollout()))
    blank["case_id"] = ""
    with pytest.raises(P.RuntimeProofError, match=r"empty receipt fields \['case_id'\]"):
        P.validate_runtime_receipt(blank, expected())


def test_a_receipt_declaring_an_unknown_case_is_refused() -> None:
    receipt = dict(_receipt(rollout()))
    receipt["case_id"] = "case-that-was-never-defined"

    with pytest.raises(P.RuntimeProofError, match="unknown proof case"):
        P.validate_runtime_receipt(receipt, expected())


def test_parsing_refuses_an_unknown_case_before_reading_the_rollout() -> None:
    with pytest.raises(P.RuntimeProofError, match="unknown proof case"):
        _receipt(rollout(), case_id="not-a-case")


def test_a_receipt_of_hollow_fields_is_refused() -> None:
    """Every required key present, every value None: shape without content is not evidence."""

    hollow = {field: None for field in P.RECEIPT_REQUIRED_FIELDS}

    with pytest.raises(P.RuntimeProofError, match="carries empty receipt fields"):
        P.validate_runtime_receipt(hollow, expected())


def test_a_receipt_records_the_observed_codex_version_not_the_target() -> None:
    """KTD2: an expectation must never be recorded where an observation belongs."""

    receipt = _receipt(rollout(), codex_cli_version_observed="0.146.0")
    assert receipt["codex_cli_version_observed"] == "0.146.0"
    assert receipt["codex_cli_version_observed"] != P.CODEX_TARGET_VERSION

    with pytest.raises(P.RuntimeProofError, match="not a version string"):
        _receipt(rollout(), codex_cli_version_observed="whatever-is-installed")

    stripped = dict(receipt)
    del stripped["codex_cli_version_observed"]
    with pytest.raises(
        P.RuntimeProofError, match=r"missing receipt fields \['codex_cli_version_observed'\]"
    ):
        P.validate_runtime_receipt(stripped, expected())

    malformed = dict(receipt)
    malformed["codex_cli_version_observed"] = "0.147"
    with pytest.raises(P.RuntimeProofError, match="no observed Codex version"):
        P.validate_runtime_receipt(malformed, expected())


def test_live_requires_runtime_receipt() -> None:
    value, digest = snapshot()
    with pytest.raises(P.RuntimeProofError, match="requires a runtime receipt"):
        P.build_proof(snapshot=value, snapshot_sha256=digest, live=True)


def test_committed_live_proof_is_supported_and_sanitized() -> None:
    committed = json.loads(
        (
            ROOT
            / "docs"
            / "validation"
            / "codex-v2-orchestration-runtime-proof.json"
        ).read_text(encoding="utf-8")
    )

    assert committed["capability_outcome"] == "supported"
    assert committed["mode"] == "current-session-live"
    assert committed["live_invocation_performed"] is True
    P.validate_sanitized_proof(committed)


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


def test_live_command_reuses_current_auth_with_disposable_source_profiles() -> None:
    source = SCRIPT.read_text()

    assert "shell=True" not in source
    assert 'env["CODEX_HOME"]' in source
    assert '"auth.json"' not in source
    assert '"models_cache.json"' in source
    assert "infiquetra-v1.json" not in source
    assert '"--strict-config"' in source
    assert "TemporaryDirectory" in source
    assert "Path(raw_workspace).resolve()" in source
    assert "isolated_target=True" in source
    assert '"--skip-git-repo-check"' in source


@pytest.fixture
def catalog_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """A disposable CODEX_HOME holding a real model cache, and that cache's real digest.

    An earlier draft of the honest projection used `"a" * 64` as the catalog digest, which passed
    only because the digest was shape-checked rather than bound to bytes. That single placeholder
    masked the defect cross-review then found: an invented catalog reached `supported`. The
    binding is only testable against a cache that actually exists, and it must never be the
    operator's real one.
    """

    home = tmp_path / "codex-home"
    home.mkdir(mode=0o700)
    cache = home / "models_cache.json"
    cache.write_text(
        json.dumps(
            {
                "models": [
                    {"slug": "gpt-5.6-sol", "multi_agent_version": "v2"},
                    {"slug": "gpt-5.6-terra", "multi_agent_version": "v2"},
                ]
            }
        ),
        encoding="utf-8",
    )
    # Two rollout receipts, because configuration agreement is not a rollout. Cross-review
    # published a projection that matched every configuration file and had produced zero
    # rollouts; the receipts are the artefact only a real turn leaves behind.
    sessions = home / "sessions" / "2026" / "08" / "09"
    sessions.mkdir(parents=True)
    root_rollout = sessions / "rollout-root.jsonl"
    child_rollout = sessions / "rollout-child.jsonl"
    root_rollout.write_bytes(rollout(parent=None))
    child_rollout.write_bytes(rollout())
    monkeypatch.setenv("CODEX_HOME", str(home))
    _payload, digest = P._load_json(cache, "native Codex model cache")
    return {
        "catalog_sha256": digest,
        "root_rollout_sha256": P._sha256(root_rollout.read_bytes()),
        "child_rollout_sha256": P._sha256(child_rollout.read_bytes()),
    }


def _honest_projection(home: dict[str, str]) -> dict[str, object]:
    """The shape `run_live_probe` actually publishes, bound to a real source profile."""

    profile = P._source_profile_expectation("review_high")
    projection = {
        "case_id": "profile-identity",
        "harness_sha256": P.RUNTIME_PROOF_HARNESS_SHA256,
        "codex_cli_version_observed": OBSERVED_CODEX_VERSION,
        "catalog": {
            "source": "native-model-cache",
            "sha256": home["catalog_sha256"],
            "required_v2_models": ["gpt-5.6-sol", profile["model"]],
            "luna_multi_agent_version": None,
        },
        "root": {
            "model": "gpt-5.6-sol",
            "reasoning_effort": "max",
            "model_provider": "openai",
            "approval_policy": "never",
            "sandbox_mode": "read-only",
            "permission_profile": None,
            "multi_agent_version": "v2",
            "operations_observed": ["spawn_agent", "list_agents", "wait_agent"],
        },
        "child": {
            "agent_path": "/root/probe",
            "agent_role": "review_high",
            "model": profile["model"],
            "reasoning_effort": profile["reasoning_effort"],
            "model_provider": "openai",
            "approval_policy": "never",
            "sandbox_mode": "read-only",
            "permission_profile": None,
            "multi_agent_version": "v2",
            "history_mode": "none",
            "parent_context_marker_observed": False,
            "terminal_status": "completed",
            "terminal_marker_observed": True,
        },
        "profile_sha256": profile["sha256"],
        "root_rollout_sha256": home["root_rollout_sha256"],
        "child_rollout_sha256": home["child_rollout_sha256"],
    }
    return projection


def test_an_honest_projection_is_still_accepted(catalog_home: dict[str, str]) -> None:
    """The validator must not reject honest proofs while rejecting fabricated ones.

    An earlier draft did exactly that, which is the worst way round: it made the instrument look
    strict while being useless.
    """

    P.validate_live_projection(_honest_projection(catalog_home), "projection")


@pytest.mark.parametrize(
    "mutation, expected",
    [
        ({"profile_sha256": "b" * 64}, "is not the digest of source profile"),
        ({"child": {"model": "gpt-5.6-terra"}}, "disagrees with source profile"),
        ({"child": {"reasoning_effort": "low"}}, "disagrees with source profile"),
        ({"child": {"agent_role": "scan_low"}}, "is not the digest of source profile"),
        ({"child": {"agent_path": "/root"}}, "is not a spawned child path"),
        ({"child": {"terminal_marker_observed": "yes"}}, "must be a boolean"),
        ({"child": {"exfiltrated": "value"}}, "keys do not match"),
        ({"root": {"multi_agent_version": "v1"}}, "does not report the V2 backend"),
        ({"root": {"sandbox_mode": "anything-goes"}}, "is not a Codex sandbox mode"),
        (
            {"root": {"operations_observed": ["spawn_agent"]}},
            "did not observe the required probe operations",
        ),
        # The proper-subset form of that check was backwards: an operation list that shares
        # NOTHING with the required set is not a proper subset of it, so it passed. Cross-review
        # reached `capability_outcome = supported` through exactly this value.
        (
            {"root": {"operations_observed": ["not_a_codex_operation"]}},
            "did not observe the required probe operations",
        ),
        (
            {
                "root": {
                    "operations_observed": [
                        "spawn_agent",
                        "list_agents",
                        "wait_agent",
                        "not_a_codex_operation",
                    ]
                }
            },
            "reports operations Codex does not define",
        ),
        # Outcome fields had types but no required values, so an unfinished child that never
        # returned the contract marker could still be published as supported.
        ({"child": {"terminal_status": "interrupted"}}, "did not reach a completed terminal"),
        ({"child": {"terminal_marker_observed": False}}, "never returned the terminal contract"),
        (
            {"child": {"parent_context_marker_observed": True}},
            "history was not bounded",
        ),
        ({"child": {"approval_policy": "whatever"}}, "is not a Codex policy"),
        ({"root": {"model_provider": "attacker-controlled"}}, "not a provider this repository"),
        ({"child": {"history_mode": "invented"}}, "is not a Codex history mode"),
        ({"catalog": {"sha256": "c" * 64}}, "not the digest of the model cache"),
        ({"catalog": {"source": "hand-written"}}, "does not name the native Codex model cache"),
    ],
)
def test_the_projection_is_bound_to_bytes_on_disk(
    mutation: dict[str, object], expected: str, catalog_home: dict[str, str]
) -> None:
    """A projection cannot claim a profile's identity without that profile's real bytes."""

    projection = _honest_projection(catalog_home)
    for key, value in mutation.items():
        if isinstance(value, dict) and isinstance(projection.get(key), dict):
            projection[key] = {**projection[key], **value}
        else:
            projection[key] = value

    with pytest.raises(P.RuntimeProofError, match=expected):
        P.validate_live_projection(projection, "projection")

def test_an_empty_model_cache_cannot_satisfy_the_catalog_binding(
    catalog_home: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_load_json` accepted any object, so `{}` with its real digest passed the binding."""

    projection = _honest_projection(catalog_home)
    home = tmp_path / "empty-home"
    home.mkdir()
    cache = home / "models_cache.json"
    cache.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("CODEX_HOME", str(home))
    _payload, digest = P._load_json(cache, "cache")
    projection["catalog"] = {**projection["catalog"], "sha256": digest}

    with pytest.raises(P.RuntimeProofError, match="lacks model rows"):
        P.validate_live_projection(projection, "projection")



LUNA_CANARY = json.loads(
    (ROOT / "docs" / "validation" / "codex-0147-luna-canary.json").read_text(encoding="utf-8")
)


def test_the_committed_luna_canary_validates() -> None:
    P.validate_luna_canary(LUNA_CANARY)


def test_the_canary_records_tool_absence_from_the_tool_plan_not_from_behaviour() -> None:
    """KTD7: absence inferred from behaviour is not evidence of absence.

    Luna is offered no collaboration namespace as a spawned child; Terra, captured in the same
    run by the same instrument, is offered all six operations. That comparison is what makes the
    absence a finding rather than a null result.
    """

    luna = LUNA_CANARY["observations"]["gpt-5.6-luna"]
    terra = LUNA_CANARY["observations"]["gpt-5.6-terra"]

    assert LUNA_CANARY["method"]["model_calls"] == 0
    assert luna["spawned_as_child"] is True
    assert luna["collaboration_offered"] is False
    assert "collaboration" not in luna["namespaces_offered"]
    assert terra["collaboration_offered"] is True
    assert len(terra["namespaces_offered"]["collaboration"]) == 6
    assert luna["definitions_sha256"] != terra["definitions_sha256"]


def test_a_profile_cannot_pass_a_criterion_the_canary_never_measured() -> None:
    """The plan's gate: a pass recorded for something no run covered must fail."""

    payload = json.loads(json.dumps(LUNA_CANARY))
    payload["profiles"]["scan_low"]["instruction-adherence"] = "pass"

    with pytest.raises(P.RuntimeProofError, match="does not record as measured"):
        P.validate_luna_canary(payload)


def test_an_unmeasured_criterion_must_say_why() -> None:
    payload = json.loads(json.dumps(LUNA_CANARY))
    payload["criteria"]["instruction-adherence"].pop("reason")

    with pytest.raises(P.RuntimeProofError, match="unmeasured with no reason"):
        P.validate_luna_canary(payload)


def test_eligible_requires_at_least_one_passing_criterion() -> None:
    payload = json.loads(json.dumps(LUNA_CANARY))
    payload["profiles"]["monitor_low"]["collaboration-tools-offered"] = "not-run"

    with pytest.raises(P.RuntimeProofError, match="without passing any criterion"):
        P.validate_luna_canary(payload)


def test_an_unknown_verdict_is_refused() -> None:
    payload = json.loads(json.dumps(LUNA_CANARY))
    payload["profiles"]["scan_low"]["verdict"] = "fine probably"

    with pytest.raises(P.RuntimeProofError, match="expected one of"):
        P.validate_luna_canary(payload)


PERMISSIONS = json.loads(
    (ROOT / "docs" / "validation" / "codex-0147-permission-inheritance.json").read_text(
        encoding="utf-8"
    )
)


def test_the_committed_permission_receipt_validates() -> None:
    P.validate_permission_inheritance(PERMISSIONS)


@pytest.mark.parametrize("case", sorted(P.PERMISSION_CASES))
def test_each_matrix_row_matches_its_expected_tuple(case: str) -> None:
    """One test per row, as the plan requires: a row that drifts fails on its own name."""

    record = PERMISSIONS["cases"][case]
    assert record["observed"] == record["expected"], case
    assert record["matches"] is True


def test_a_missing_matrix_row_fails() -> None:
    payload = json.loads(json.dumps(PERMISSIONS))
    payload["cases"].pop("turn-permission-cold-resume")

    with pytest.raises(P.RuntimeProofError, match="missing matrix rows"):
        P.validate_permission_inheritance(payload)


def test_a_row_the_harness_does_not_define_fails() -> None:
    """A duplicate identifier cannot exist in JSON, so an unknown one is the reachable case."""

    payload = json.loads(json.dumps(PERMISSIONS))
    payload["cases"]["turn-permission-invented"] = payload["cases"]["turn-permission-read-only"]

    with pytest.raises(P.RuntimeProofError, match="does not define"):
        P.validate_permission_inheritance(payload)


def test_a_child_widening_beyond_its_parent_blocks_source_ready() -> None:
    """The observation this row exists to make: a profile cannot raise its own ceiling."""

    assert (
        PERMISSIONS["cases"]["turn-permission-no-widening"]["observed"]["child_sandbox"]
        == "read-only"
    )

    payload = json.loads(json.dumps(PERMISSIONS))
    row = payload["cases"]["turn-permission-no-widening"]
    row["observed"]["child_sandbox"] = "workspace-write"
    row["expected"]["child_sandbox"] = "workspace-write"

    with pytest.raises(P.RuntimeProofError, match="blocks source-ready"):
        P.validate_permission_inheritance(payload)


def test_auto_review_is_never_recorded_as_operator_authority() -> None:
    payload = json.loads(json.dumps(PERMISSIONS))
    payload["cases"]["turn-permission-read-only"]["approvals_reviewer"]["root"] = "auto_review"

    with pytest.raises(P.RuntimeProofError, match="never operator approval"):
        P.validate_permission_inheritance(payload)
