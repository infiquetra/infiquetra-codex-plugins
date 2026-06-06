"""Tests for deploy tag minting."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest


def load_mint_tag() -> ModuleType:
    module_name = "deploy_mint_tag"
    if module_name in sys.modules:
        return sys.modules[module_name]
    script = Path(__file__).resolve().parents[1] / "scripts" / "mint_tag.py"
    spec = importlib.util.spec_from_file_location(module_name, script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


mint_tag = load_mint_tag()


def test_build_tag_name_supports_hotfix_and_rollback() -> None:
    assert mint_tag.build_tag_name("nonprod", "v1.2.3") == "nonprod-v1.2.3"
    assert mint_tag.build_tag_name("production", "1.2.3.1") == "production-v1.2.3.1"
    assert (
        mint_tag.build_tag_name("production", "1.2.3", rollback=True)
        == "rollback-production-v1.2.3"
    )


def test_resolve_repo_rejects_non_infiquetra_owner() -> None:
    with pytest.raises(SystemExit, match="expected github.com/infiquetra"):
        mint_tag.resolve_repo("other/example")


def test_dry_run_prints_plan_without_mutation(capsys) -> None:
    def fake_tag_exists(tag: str) -> bool:
        return tag == "v1.2.3"

    with patch.object(mint_tag, "tag_exists", side_effect=fake_tag_exists):
        assert (
            mint_tag.main(
                [
                    "--env",
                    "nonprod",
                    "--version",
                    "1.2.3",
                    "--repo",
                    "infiquetra/example",
                    "--dry-run",
                ]
            )
            == 0
        )

    output = capsys.readouterr().out
    assert "DRY RUN: infiquetra/example" in output
    assert "tag: nonprod-v1.2.3" in output
    assert "confirmation id:" in output
    assert "[dry-run] would: git push origin nonprod-v1.2.3" in output


def test_non_dry_run_requires_matching_confirmation() -> None:
    def fake_tag_exists(tag: str) -> bool:
        return tag == "v1.2.3"

    with (
        patch.object(mint_tag, "tag_exists", side_effect=fake_tag_exists),
        patch.object(mint_tag, "run") as mock_run,
        pytest.raises(SystemExit, match="refusing to mutate without matching --confirm-plan"),
    ):
        mint_tag.main(
            [
                "--env",
                "nonprod",
                "--version",
                "1.2.3",
                "--repo",
                "infiquetra/example",
            ]
        )

    mock_run.assert_not_called()


def test_matching_confirmation_pushes_tag() -> None:
    calls: list[list[str]] = []

    def fake_tag_exists(tag: str) -> bool:
        return tag == "v1.2.3"

    def fake_run(cmd: list[str], **_: object) -> str:
        calls.append(cmd)
        if cmd[:2] == ["git", "rev-parse"]:
            return "abc123"
        return ""

    confirm = mint_tag.confirmation_id(
        repo="infiquetra/example",
        tag="nonprod-v1.2.3",
        ref="v1.2.3",
    )
    with (
        patch.object(mint_tag, "tag_exists", side_effect=fake_tag_exists),
        patch.object(mint_tag, "run", side_effect=fake_run),
    ):
        assert (
            mint_tag.main(
                [
                    "--env",
                    "nonprod",
                    "--version",
                    "1.2.3",
                    "--repo",
                    "infiquetra/example",
                    "--confirm-plan",
                    confirm,
                ]
            )
            == 0
        )

    assert ["git", "tag", "-a", "nonprod-v1.2.3", "abc123", "-m", "Infiquetra nonprod deployment nonprod-v1.2.3"] in calls
    assert ["git", "push", "origin", "nonprod-v1.2.3"] in calls


def test_unhealthy_marker_blocks_forward_promotion() -> None:
    def fake_tag_exists(tag: str) -> bool:
        return tag in {"v1.2.3", "unhealthy-v1.2.3"}

    with (
        patch.object(mint_tag, "tag_exists", side_effect=fake_tag_exists),
        pytest.raises(SystemExit, match="refusing to promote"),
    ):
        mint_tag.main(
            [
                "--env",
                "nonprod",
                "--version",
                "1.2.3",
                "--repo",
                "infiquetra/example",
                "--dry-run",
            ]
        )
