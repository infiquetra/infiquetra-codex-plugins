"""Codex model-catalog projection, fallback, bounds, and immutability tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import ModuleType

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_MODULE = _ROOT / "plugins/fleet-core/scripts/fleet_commons/codex_model_catalog.py"
_SNAPSHOT = _ROOT / "docs/validation/codex-runtime-capability-snapshot.json"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("catalog_under_test", _MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


catalog = _load()


def _raw_row(
    slug: str = "gpt-5.6-sol",
    efforts: tuple[str, ...] = ("low", "medium", "high", "xhigh", "max", "ultra"),
    *,
    visibility: str = "list",
    supported_in_api: bool = True,
    multi_agent_version: str | None = "v2",
) -> dict:
    return {
        "slug": slug,
        "default_reasoning_level": efforts[0],
        "supported_reasoning_levels": [
            {"effort": effort, "description": f"ignored-{effort}"} for effort in efforts
        ],
        "visibility": visibility,
        "supported_in_api": supported_in_api,
        "multi_agent_version": multi_agent_version,
        "base_instructions": "must never survive normalization",
        "unknown": {"nested": "dropped"},
    }


def _result(payload: object, returncode: int = 0, stderr: bytes = b""):
    return catalog.CommandResult(
        returncode=returncode,
        stdout=json.dumps(payload).encode(),
        stderr=stderr,
    )


def test_normalization_allowlists_fields_and_accepts_both_shapes() -> None:
    for payload in ([_raw_row()], {"models": [_raw_row()]}):
        snapshot = catalog.normalize_catalog(payload, source="fixture")
        assert len(snapshot.models) == 1
        projected = snapshot.models[0].to_jsonable()
        assert set(projected) == {
            "slug",
            "default_effort",
            "supported_efforts",
            "visibility",
            "supported_in_api",
            "multi_agent_version",
            "multi_agent_v2_override_filter",
            "multi_agent_v2_collaboration",
        }
        assert projected["multi_agent_v2_override_filter"] == {
            "rule": "codex-0.147.0/model-supports-multi-agent-backend",
            "passes": True,
        }
        assert projected["multi_agent_v2_collaboration"] == {
            "rule": "codex-0.147.0/collab-tools-enabled",
            "as_root": True,
            "as_child": True,
        }
        rendered = json.dumps(snapshot.to_jsonable())
        assert "base_instructions" not in rendered
        assert "must never survive" not in rendered
        assert "unknown" not in rendered


@pytest.mark.parametrize(
    ("multi_agent_version", "passes_override_filter", "collaborates_as_child"),
    [
        ("v1", True, False),
        ("v2", True, True),
        ("disabled", False, False),
        (None, True, False),
    ],
)
def test_multi_agent_v2_projections_cover_every_catalog_wire_value(
    multi_agent_version: str | None,
    passes_override_filter: bool,
    collaborates_as_child: bool,
) -> None:
    snapshot = catalog.normalize_catalog(
        {"models": [_raw_row(multi_agent_version=multi_agent_version)]},
        source="fixture",
    )
    projected = snapshot.models[0].to_jsonable()

    assert projected["multi_agent_v2_override_filter"] == {
        "rule": "codex-0.147.0/model-supports-multi-agent-backend",
        "passes": passes_override_filter,
    }
    assert projected["multi_agent_v2_collaboration"] == {
        "rule": "codex-0.147.0/collab-tools-enabled",
        "as_root": True,
        "as_child": collaborates_as_child,
    }


def test_normalized_digest_matches_committed_capability_snapshot() -> None:
    committed = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))["catalog"]
    raw_models = []
    for row in committed["models"]:
        raw = _raw_row(
            row["slug"],
            tuple(row["supported_efforts"]),
            visibility=row["visibility"],
            supported_in_api=row["supported_in_api"],
            multi_agent_version=row["multi_agent_version"],
        )
        raw["default_reasoning_level"] = row["default_effort"]
        raw_models.append(raw)
    snapshot = catalog.normalize_catalog({"models": raw_models}, source="fixture")
    assert snapshot.normalized_sha256 == committed["normalized_sha256"]


def test_snapshot_is_immutable_and_reused_deterministically() -> None:
    snapshot = catalog.normalize_catalog({"models": [_raw_row()]}, source="fixture")
    assert isinstance(snapshot.models, tuple)
    assert isinstance(snapshot.models[0].supported_efforts, tuple)
    assert snapshot.model("gpt-5.6-sol") is snapshot.models[0]
    assert snapshot.model("missing") is None
    with pytest.raises(FrozenInstanceError):
        snapshot.source = "bundled"


def test_refreshed_success_calls_once() -> None:
    calls: list[tuple[str, ...]] = []

    def run(argv, _timeout, _limit):
        calls.append(tuple(argv))
        return _result({"models": [_raw_row()]})

    snapshot = catalog.read_catalog(run)
    assert snapshot.source == "refreshed"
    assert calls == [("codex", "debug", "models")]


def test_full_document_preserves_validated_catalog_bytes() -> None:
    payload = {"models": [_raw_row()]}
    raw = json.dumps(payload, indent=2).encode()

    def run(_argv, _timeout, _limit):
        return catalog.CommandResult(returncode=0, stdout=raw, stderr=b"")

    document = catalog.read_catalog_document(run)

    assert document.source == "refreshed"
    assert document.raw_bytes == raw
    assert document.snapshot.model("gpt-5.6-sol") is not None


def test_bundled_document_bypasses_refreshed_catalog() -> None:
    calls: list[tuple[str, ...]] = []

    def run(argv, _timeout, _limit):
        calls.append(tuple(argv))
        return _result({"models": [_raw_row()]})

    document = catalog.read_bundled_catalog_document(run)

    assert document.source == "bundled"
    assert calls == [("codex", "debug", "models", "--bundled")]


@pytest.mark.parametrize("first_failure", ["exit", "invalid", "timeout", "oversize"])
def test_refreshed_failure_tries_bundled_once(first_failure: str) -> None:
    calls: list[tuple[str, ...]] = []

    def run(argv, _timeout, limit):
        calls.append(tuple(argv))
        if len(calls) == 1:
            if first_failure == "exit":
                return catalog.CommandResult(2, b"", b"failed")
            if first_failure == "invalid":
                return catalog.CommandResult(0, b"{", b"")
            if first_failure == "timeout":
                raise catalog.CatalogCommandError("catalog command timed out")
            return catalog.CommandResult(0, b"x" * (limit + 1), b"")
        return _result({"models": [_raw_row()]})

    snapshot = catalog.read_catalog(run)
    assert snapshot.source == "bundled"
    assert calls == [
        ("codex", "debug", "models"),
        ("codex", "debug", "models", "--bundled"),
    ]


@pytest.mark.parametrize(
    "payload,match",
    [
        ({"models": []}, "non-empty"),
        ({"models": [_raw_row(), _raw_row()]}, "duplicate slug"),
        (
            {"models": [_raw_row(efforts=("low", "low"))]},
            "repeats effort",
        ),
        (
            {"models": [_raw_row(efforts=("low", "future"))]},
            "malformed reasoning level",
        ),
        ({"models": [_raw_row(slug="bad\nslug")]}, "missing or duplicate slug"),
        (
            {"models": [_raw_row(multi_agent_version="future")]},
            "unsupported multi-agent version",
        ),
    ],
)
def test_malformed_projection_fails_loud(payload: object, match: str) -> None:
    with pytest.raises(catalog.CatalogError, match=match):
        catalog.normalize_catalog(payload, source="fixture")


def test_default_effort_must_be_one_of_the_supported_levels() -> None:
    row = _raw_row(efforts=("medium", "high"))
    row["default_reasoning_level"] = "low"
    with pytest.raises(catalog.CatalogError, match="default effort is not"):
        catalog.normalize_catalog({"models": [row]}, source="fixture")


def test_both_catalog_sources_failing_is_one_loud_error() -> None:
    def run(_argv, _timeout, _limit):
        return catalog.CommandResult(1, b"", b"not available")

    with pytest.raises(catalog.CatalogError, match="both Codex model catalog sources failed"):
        catalog.read_catalog(run)


def test_default_runner_enforces_timeout_and_combined_output_bound() -> None:
    with pytest.raises(catalog.CatalogCommandError, match="timed out"):
        catalog._run_bounded(
            (sys.executable, "-c", "import time; time.sleep(1)"),
            0.01,
            1024,
        )
    with pytest.raises(catalog.CatalogCommandError, match="output ceiling"):
        catalog._run_bounded(
            (sys.executable, "-c", "import sys; sys.stdout.write('x'*20); sys.stderr.write('y'*20)"),
            2.0,
            32,
        )
