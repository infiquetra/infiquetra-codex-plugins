from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import json
import sys
import tomllib
from pathlib import Path

import pytest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
RENDERER_PATH = PLUGIN_ROOT / "scripts" / "render_codex_agents.py"


def _load_renderer():
    name = "verified_workflows_u3_tier_renderer"
    spec = importlib.util.spec_from_file_location(name, RENDERER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


R = _load_renderer()


def _bundle():
    return R.render_bundle(R.load_role_registry(), R.load_catalog_snapshot())


def _raw_model(
    slug: str,
    efforts: tuple[str, ...],
    *,
    visibility: str = "list",
    supported: bool = True,
) -> dict:
    return {
        "slug": slug,
        "default_reasoning_level": efforts[0],
        "supported_reasoning_levels": [{"effort": effort} for effort in efforts],
        "visibility": visibility,
        "supported_in_api": supported,
    }


def _canary_receipt(*eligible: str, **overrides) -> dict:
    """Build a well-formed per-profile canary receipt naming exactly `eligible` as promotable."""

    payload = {
        "claim": R.LUNA_CANARY_CLAIM,
        "codex_cli_version_observed": "0.147.0",
        "criteria": {R.LUNA_DECIDING_CRITERION: {"measured": True, "how": "fixture"}},
        "profiles": {
            profile_id: {
                "verdict": (
                    R.LUNA_ELIGIBLE_VERDICT if profile_id in eligible else "not-assessed"
                ),
                "needs_collaboration_tools": False,
                **(
                    {R.LUNA_DECIDING_CRITERION: "pass"}
                    if profile_id in eligible
                    else {}
                ),
            }
            for profile_id in sorted(R.LUNA_PROMOTION_CANDIDATES)
        },
    }
    payload.update(overrides)
    return payload


def _receipt(*eligible: str, **overrides) -> R.LunaCanaryReceipt:
    return R.parse_luna_canary_receipt(
        _canary_receipt(*eligible, **overrides), sha256="0" * 64
    )


def _catalog_with_luna(**luna_fields) -> object:
    """A fixture catalog whose Luna row carries the given deviations from a healthy entry."""

    luna = {
        **_raw_model(
            "gpt-5.6-luna",
            luna_fields.pop("efforts", ("low", "medium", "high", "max")),
            visibility=luna_fields.pop("visibility", "list"),
            supported=luna_fields.pop("supported", True),
        ),
        **luna_fields,
    }
    payload = {
        "models": [
            _raw_model("gpt-5.6-sol", ("low", "medium", "high", "max")),
            _raw_model("gpt-5.6-terra", ("low", "medium", "high", "max")),
            _raw_model("gpt-5.5", ("low", "medium", "high")),
            luna,
        ]
    }
    return R.CATALOG.normalize_catalog(payload, source="fixture")


def _class_policy_expectation() -> dict[str, tuple[str, str]]:
    """What each rendered profile must carry, read from Fleet Core rather than restated here."""

    expectation = {}
    for profile_id, execution_class in R.PROFILE_EXECUTION_CLASSES.items():
        policy = R.TIER_PALETTE.execution_class_policy(execution_class)
        expectation[profile_id] = (policy.preferred.model, policy.preferred.effort)
    return expectation


def test_full_catalog_renders_profiles_bound_to_their_execution_class() -> None:
    bundle = _bundle()
    expected = _class_policy_expectation()

    assert {profile.profile_id for profile in bundle.profiles} == set(expected)
    for profile in bundle.profiles:
        payload = tomllib.loads(profile.content.decode("utf-8"))
        model, effort = expected[profile.profile_id]
        assert payload["name"] == R.RUNTIME_AGENT_NAMES[profile.profile_id]
        assert profile.runtime_agent_name == payload["name"]
        assert profile.filename == f"{payload['name']}.toml"
        assert payload["model"] == model
        assert payload["model_reasoning_effort"] == effort
        assert (
            f'# catalog_sha256 = "{bundle.catalog.normalized_sha256}"'
            in profile.content.decode("utf-8")
        )
        assert "logical-role identity" in payload["developer_instructions"]
        assert "Runtime identity and permissions come from Codex" in payload["developer_instructions"]
        assert "sandbox_mode" not in payload
        assert effort != "ultra"


def test_scan_and_monitor_remain_distinct_at_the_same_model_effort() -> None:
    bundle = _bundle()
    profiles = {profile.profile_id: profile for profile in bundle.profiles}
    scan = tomllib.loads(profiles["scan_low"].content.decode("utf-8"))
    monitor = tomllib.loads(profiles["monitor_low"].content.decode("utf-8"))

    assert scan["model"] == monitor["model"] == "gpt-5.6-terra"
    assert scan["model_reasoning_effort"] == monitor["model_reasoning_effort"] == "low"
    assert "`scan_low`" in scan["developer_instructions"]
    assert "`monitor_low`" in monitor["developer_instructions"]
    assert profiles["scan_low"].sha256 != profiles["monitor_low"].sha256


def test_a_v1_luna_promotes_because_the_override_filter_not_the_version_decides() -> None:
    """The branch the old predicate made unreachable.

    The shipped Luna row reports `v1`, and the old gate required the raw catalog field to equal
    `"v2"`, so this path could never run against any catalog Codex has published. Codex 0.147.0
    gates on "not disabled" instead, which the U2 projection exposes as
    `passes_multi_agent_v2_override_filter`.
    """

    catalog = R.load_catalog_snapshot()
    assert catalog.model("gpt-5.6-luna").multi_agent_version == "v1"
    assert catalog.model("gpt-5.6-luna").passes_multi_agent_v2_override_filter

    bundle = R.render_bundle(
        R.load_role_registry(), catalog, luna_canary=_receipt("scan_low", "monitor_low")
    )
    resolutions = {profile.profile_id: profile.resolution for profile in bundle.profiles}
    for profile_id in ("scan_low", "monitor_low"):
        assert resolutions[profile_id].model == "gpt-5.6-luna"
        assert resolutions[profile_id].policy_deviation == "luna-v2-canary"


def test_without_a_receipt_both_low_profiles_stay_on_their_execution_class_model() -> None:
    bundle = R.render_bundle(R.load_role_registry(), R.load_catalog_snapshot())
    resolutions = {profile.profile_id: profile.resolution for profile in bundle.profiles}

    for profile_id in ("scan_low", "monitor_low"):
        assert resolutions[profile_id].model == "gpt-5.6-terra"
        assert resolutions[profile_id].policy_deviation is None


@pytest.mark.parametrize(
    ("promoted", "held"),
    [("scan_low", "monitor_low"), ("monitor_low", "scan_low")],
)
def test_an_asymmetric_receipt_promotes_exactly_one_low_profile(
    promoted: str, held: str
) -> None:
    """The whole point of replacing the pair-wide boolean: the two can now disagree."""

    bundle = R.render_bundle(
        R.load_role_registry(), R.load_catalog_snapshot(), luna_canary=_receipt(promoted)
    )
    resolutions = {profile.profile_id: profile.resolution for profile in bundle.profiles}

    assert resolutions[promoted].model == "gpt-5.6-luna"
    assert resolutions[promoted].policy_deviation == "luna-v2-canary"
    assert resolutions[held].model == "gpt-5.6-terra"
    assert resolutions[held].policy_deviation is None


def test_a_disabled_luna_entry_refuses_promotion() -> None:
    catalog = _catalog_with_luna(multi_agent_version="disabled")
    with pytest.raises(R.RoleRegistryError, match="override filter"):
        R.render_bundle(R.load_role_registry(), catalog, luna_canary=_receipt("scan_low"))


def test_a_non_selectable_luna_entry_refuses_promotion() -> None:
    catalog = _catalog_with_luna(visibility="hide")
    with pytest.raises(R.RoleRegistryError, match="selectable gpt-5.6-luna"):
        R.render_bundle(R.load_role_registry(), catalog, luna_canary=_receipt("scan_low"))


def test_a_luna_entry_missing_the_requested_effort_refuses_promotion() -> None:
    catalog = _catalog_with_luna(efforts=("medium", "high"))
    with pytest.raises(R.RoleRegistryError, match="effort 'low' is unsupported"):
        R.render_bundle(R.load_role_registry(), catalog, luna_canary=_receipt("scan_low"))


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda p: p.update(claim="something-else"), "claims 'something-else'"),
        (lambda p: p.update(codex_cli_version_observed="unknown"), "no observed Codex version"),
        (lambda p: p.update(criteria={}), "declares no criteria"),
        (
            lambda p: p.update(criteria={"quality": {"measured": False}}),
            "unmeasured with no reason",
        ),
        (
            lambda p: p.update(
                criteria={"quality": {"measured": True}},
            ),
            "did not measure 'collaboration-tools-offered'",
        ),
        (
            lambda p: p["profiles"]["scan_low"].update(verdict="looks-fine"),
            "carries verdict 'looks-fine'",
        ),
        (
            lambda p: p["profiles"]["scan_low"].update({"instruction-adherence": "pass"}),
            "does not record as measured",
        ),
        (
            lambda p: p["profiles"]["scan_low"].update(needs_collaboration_tools=True),
            "needs no collaboration tools",
        ),
        (
            lambda p: p["profiles"].update(
                {
                    "work_high": {
                        "verdict": R.LUNA_ELIGIBLE_VERDICT,
                        "needs_collaboration_tools": False,
                        R.LUNA_DECIDING_CRITERION: "pass",
                    }
                }
            ),
            "only \\['monitor_low', 'scan_low'\\]",
        ),
    ],
)
def test_a_receipt_that_overclaims_is_refused(mutate, expected: str) -> None:
    """A forged or overreaching receipt never reaches the gate.

    Each case here is the round's central defect in miniature: a receipt asserting more than it
    measured would turn one runtime observation into standing policy.
    """

    payload = _canary_receipt("scan_low")
    mutate(payload)
    with pytest.raises(R.RoleRegistryError, match=expected):
        R.parse_luna_canary_receipt(payload, sha256="0" * 64)


def test_promotion_makes_a_profile_a_non_delegating_leaf_by_derivation() -> None:
    """Recorded as a consequence of the effective model, never stored on the profile."""

    catalog = R.load_catalog_snapshot()
    bundle = R.render_bundle(R.load_role_registry(), catalog, luna_canary=_receipt("scan_low"))
    rows = {row["profile_id"]: row for row in bundle.delegation_expectations()}

    assert rows["scan_low"]["model"] == "gpt-5.6-luna"
    assert rows["scan_low"]["as_root"] is True
    assert rows["scan_low"]["as_child"] is False
    assert rows["scan_low"]["non_delegating_leaf"] is True
    # An unpromoted sibling on the same run is not a leaf, so the property tracks the model.
    assert rows["monitor_low"]["non_delegating_leaf"] is False
    assert rows["work_high"]["non_delegating_leaf"] is False
    # And nothing about it is written into the profile bytes.
    scan = tomllib.loads(
        next(p for p in bundle.profiles if p.profile_id == "scan_low").content.decode()
    )
    assert "non_delegating_leaf" not in scan
    assert "delegation" not in scan["developer_instructions"]


def test_missing_exact_profile_model_fails_without_hidden_fallback() -> None:
    payload = {
        "models": [
            _raw_model("gpt-5.6-terra", ("low", "medium", "high", "max")),
            _raw_model("gpt-5.6-luna", ("low", "medium", "high", "max")),
            _raw_model("gpt-5.5", ("low", "medium", "high")),
            _raw_model("gpt-5.4-mini", ("low", "medium")),
        ]
    }
    snapshot = R.CATALOG.normalize_catalog(payload, source="fixture")
    with pytest.raises(R.RoleRegistryError, match="gpt-5.6-sol.*not selectable"):
        R.render_bundle(R.load_role_registry(), snapshot)


def test_no_compatible_catalog_fails_loud() -> None:
    payload = {
        "models": [
            _raw_model("gpt-5.6-sol", ("ultra",), visibility="hide"),
        ]
    }
    snapshot = R.CATALOG.normalize_catalog(payload, source="fixture")

    with pytest.raises(R.RoleRegistryError, match="not selectable"):
        R.render_bundle(R.load_role_registry(), snapshot)


def _repoint_class(
    monkeypatch: pytest.MonkeyPatch,
    execution_class: str,
    *,
    model: str | None = None,
    effort: str | None = None,
) -> None:
    """Change one Fleet Core execution class in place, touching no renderer code."""

    real = R.TIER_PALETTE.execution_class_policy

    def patched(name: str):
        policy = real(name)
        if name != execution_class:
            return policy
        preferred = dataclasses.replace(
            policy.preferred,
            model=model or policy.preferred.model,
            effort=effort or policy.preferred.effort,
        )
        return dataclasses.replace(policy, preferred=preferred)

    monkeypatch.setattr(R.TIER_PALETTE, "execution_class_policy", patched)


def test_ultra_is_rejected_as_a_child_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ultra reaching a leaf would now have to come from Fleet Core policy, so that is where
    # the rejection is provoked. The renderer must refuse it rather than inherit it.
    _repoint_class(monkeypatch, "work-high", effort="ultra")

    with pytest.raises(R.RoleRegistryError, match="Ultra is root-only"):
        R.render_bundle(R.load_role_registry(), R.load_catalog_snapshot())


# Captured from the renderer immediately before the policy source collapse, while the model and
# effort were still literals in this plugin. The collapse is only correct if it moved nothing.
PRE_COLLAPSE_PROFILE_SHA256 = {
    "review_max": "3bb3abe289a7dbb832c0f6e8aa2cd214205e998113ab699678f8cc188fe9a6db",
    "review_high": "86b2f2e0f6f1f3471f427077827bf007c141b15e238f0d5bcebddd7fedb296b8",
    "work_high": "8eb7257833aceb87f4094f267f9f32ef2ef60326b97571c04573fa6a15d10c17",
    "work_medium": "a7cd86f520fcb554a70fd01bdf0be59e5e15eb0671470d71281387011b5dc41d",
    "test_medium": "9b80ca6f220dc68588c52fd13967f968c109c0db195ebed6bdf1af87a2f3fb8b",
    "scan_low": "c5aec84ee0e8b3b03be31abcb46e7a55f6057b3cdabf42953322c4fe659148ff",
    "monitor_low": "1ffcc126fef9a0f697df39a95e119c5549daa5abf9e8a48d2afe0a13e599352a",
}


def test_policy_collapse_left_every_rendered_profile_byte_identical() -> None:
    bundle = _bundle()
    rendered = {
        profile.profile_id: hashlib.sha256(profile.content).hexdigest()
        for profile in bundle.profiles
    }

    assert rendered == PRE_COLLAPSE_PROFILE_SHA256


def test_the_renderer_reads_class_policy_rather_than_a_local_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Repointing the class alone must move the profile. If the renderer still held its own
    # model/effort literals this would render the old bytes and pass nothing.
    _repoint_class(monkeypatch, "work-high", model="gpt-5.6-terra", effort="medium")
    profiles = {profile.profile_id: profile for profile in _bundle().profiles}
    moved = tomllib.loads(profiles["work_high"].content.decode("utf-8"))

    assert (moved["model"], moved["model_reasoning_effort"]) == ("gpt-5.6-terra", "medium")
    assert (
        hashlib.sha256(profiles["work_high"].content).hexdigest()
        != PRE_COLLAPSE_PROFILE_SHA256["work_high"]
    )
    # Only the repointed class moves; the others still render their pre-collapse bytes.
    for profile_id, profile in profiles.items():
        if profile_id == "work_high":
            continue
        assert hashlib.sha256(profile.content).hexdigest() == (
            PRE_COLLAPSE_PROFILE_SHA256[profile_id]
        )


def test_class_policy_is_derived_from_the_fleet_core_models_registry(tmp_path: Path) -> None:
    """Close the other half of the chain: the class policy comes from `models.json` on disk."""

    registry_path = R.TIER_PALETTE.MODELS_REGISTRY_PATH
    assert registry_path.name == "models.json"
    assert registry_path.parent.name == "fleet_commons"

    raw = json.loads(registry_path.read_text(encoding="utf-8"))
    assert raw["execution_classes"]["work-high"]["preferred"] == {
        "model": "gpt-5.6-sol",
        "effort": "high",
    }

    # A different registry file yields a different policy, so the derivation reads the file
    # rather than any constant baked into tier_palette.
    raw["execution_classes"]["work-high"]["preferred"] = {
        "model": "gpt-5.6-terra",
        "effort": "medium",
    }
    raw["execution_classes"]["work-high"]["fallbacks"] = [
        {"model": "gpt-5.6-sol", "effort": "medium"}
    ]
    edited = tmp_path / "models.json"
    edited.write_text(json.dumps(raw), encoding="utf-8")

    reloaded = R.TIER_PALETTE._load_registry(edited)
    assert reloaded["execution_classes"]["work-high"]["preferred"]["model"] == "gpt-5.6-terra"


def test_a_hand_built_off_policy_resolution_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """`render_profile` is public, so a caller-supplied resolution must not escape the class."""

    snapshot = R.load_catalog_snapshot()
    registry = R.load_role_registry()

    wrong_model = R.ProfileResolution(
        profile_id="work_high",
        model="gpt-5.4-mini",
        effort="high",
        catalog_sha256=snapshot.normalized_sha256,
    )
    with pytest.raises(R.RoleRegistryError, match="model 'gpt-5.4-mini' does not match"):
        R.render_profile(wrong_model, registry)

    wrong_effort = R.ProfileResolution(
        profile_id="work_high",
        model="gpt-5.6-sol",
        effort="low",
        catalog_sha256=snapshot.normalized_sha256,
    )
    with pytest.raises(R.RoleRegistryError, match="effort 'low' does not match"):
        R.render_profile(wrong_effort, registry)

    invented_reason = R.ProfileResolution(
        profile_id="work_high",
        model="gpt-5.6-terra",
        effort="high",
        catalog_sha256=snapshot.normalized_sha256,
        policy_deviation="because-i-said-so",
    )
    with pytest.raises(R.RoleRegistryError, match="unknown policy deviation"):
        R.render_profile(invented_reason, registry)


def test_the_luna_canary_is_a_declared_deviation_not_an_unexplained_one() -> None:
    catalog = _catalog_with_luna(multi_agent_version="v2")
    bundle = R.render_bundle(
        R.load_role_registry(), catalog, luna_canary=_receipt("scan_low", "monitor_low")
    )
    resolutions = {profile.profile_id: profile.resolution for profile in bundle.profiles}

    for profile_id in ("scan_low", "monitor_low"):
        assert resolutions[profile_id].model == "gpt-5.6-luna"
        assert resolutions[profile_id].policy_deviation == "luna-v2-canary"
        # The class still owns the effort even when it does not own the model.
        execution_class = R.PROFILE_EXECUTION_CLASSES[profile_id]
        policy = R.TIER_PALETTE.execution_class_policy(execution_class)
        assert resolutions[profile_id].effort == policy.preferred.effort

    assert resolutions["work_high"].policy_deviation is None


def test_a_profile_with_no_mapped_execution_class_fails_loud(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping = dict(R.PROFILE_EXECUTION_CLASSES)
    del mapping["work_high"]
    monkeypatch.setattr(R, "PROFILE_EXECUTION_CLASSES", mapping)

    with pytest.raises(R.RoleRegistryError, match="execution-class roster drifted"):
        R.render_bundle(R.load_role_registry(), R.load_catalog_snapshot())


def test_a_profile_naming_an_undefined_execution_class_fails_loud(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping = dict(R.PROFILE_EXECUTION_CLASSES)
    mapping["work_high"] = "work-enormous"
    monkeypatch.setattr(R, "PROFILE_EXECUTION_CLASSES", mapping)

    with pytest.raises(R.RoleRegistryError, match="Fleet Core does not define"):
        R.render_bundle(R.load_role_registry(), R.load_catalog_snapshot())


def test_generated_profiles_are_current_and_repeatable() -> None:
    first = _bundle()
    second = _bundle()

    assert [profile.content for profile in first.profiles] == [
        profile.content for profile in second.profiles
    ]
    assert R.bundle_receipt(first) == R.bundle_receipt(second)
    R.check_generated(first)


def test_committed_catalog_loader_rejects_duplicate_slugs(tmp_path: Path) -> None:
    payload = json.loads(R.DEFAULT_CATALOG_SNAPSHOT.read_text(encoding="utf-8"))
    payload["catalog"]["models"].append(dict(payload["catalog"]["models"][0]))
    snapshot = tmp_path / "catalog.json"
    snapshot.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(R.RoleRegistryError, match="duplicate slug"):
        R.load_catalog_snapshot(snapshot)


def test_source_writer_recovers_owned_residue_and_committed_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agents = tmp_path / "agents"
    transaction = tmp_path / ".agents-render-transaction"
    agents.mkdir()
    (agents / ".review_high.toml.deadbeef").write_bytes(b"")
    monkeypatch.setattr(R, "DEFAULT_AGENTS_DIR", agents)
    monkeypatch.setattr(R, "SOURCE_TRANSACTION_DIR", transaction)
    bundle = _bundle()

    R.write_generated(bundle, agents)
    R.check_generated(bundle, agents)
    assert not (agents / ".review_high.toml.deadbeef").exists()

    cleanup = R._cleanup_source_transaction
    failed = False

    def fail_committed_cleanup(path):
        nonlocal failed
        if Path(path) == transaction and not failed:
            failed = True
            raise OSError("injected cleanup failure")
        return cleanup(path)

    monkeypatch.setattr(R, "_cleanup_source_transaction", fail_committed_cleanup)
    with pytest.raises(OSError, match="injected cleanup failure"):
        R.write_generated(bundle, agents)
    assert transaction.exists()

    monkeypatch.setattr(R, "_cleanup_source_transaction", cleanup)
    R.write_generated(bundle, agents)
    R.check_generated(bundle, agents)
    assert not transaction.exists()


def test_source_writer_recovers_preparing_and_bootstrap_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agents = tmp_path / "agents"
    transaction = tmp_path / ".agents-render-transaction"
    agents.mkdir()
    monkeypatch.setattr(R, "DEFAULT_AGENTS_DIR", agents)
    monkeypatch.setattr(R, "SOURCE_TRANSACTION_DIR", transaction)
    bundle = _bundle()
    states = {
        profile.filename: {
            "present": False,
            "before_sha256": None,
            "after_sha256": profile.sha256,
            "mode": None,
        }
        for profile in bundle.profiles
    }
    transaction.mkdir(mode=0o700)
    R._write_source_manifest(
        transaction,
        {"schema_version": 1, "state": "preparing", "profiles": states},
    )
    stage = transaction / "stage"
    stage.mkdir(mode=0o700)
    R._write_exclusive(stage / bundle.profiles[0].filename, b"partial", 0o600)

    R.write_generated(bundle, agents)
    R.check_generated(bundle, agents)
    assert not transaction.exists()

    for child in agents.iterdir():
        child.unlink()
    transaction.mkdir(mode=0o700)
    R._write_exclusive(transaction / ".manifest.json.tmp", b"partial", 0o600)

    R.write_generated(bundle, agents)
    R.check_generated(bundle, agents)
    assert not transaction.exists()
