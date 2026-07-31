"""Tests for the fail-closed frozen-source port-oracle checkout resolver."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
import subprocess

import pytest


EXPECTED_SOURCE = "infiquetra/infiquetra-claude-plugins"
PORT_SOURCE_REPO_ENV = "CODEX_PORT_SOURCE_REPO"
ROOT = Path(__file__).resolve().parents[1]


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _repository(path: Path, origin: str) -> Path:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    _git(path, "config", "user.name", "Port Resolver Test")
    _git(path, "config", "user.email", "port-resolver@example.invalid")
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(path, "add", "README.md")
    _git(path, "commit", "-qm", "fixture")
    _git(path, "remote", "add", "origin", origin)
    return path


def _linked_worktree_layout(tmp_path: Path) -> tuple[Path, Path]:
    layout = tmp_path / "primary-layout"
    primary = _repository(
        layout / "infiquetra-codex-plugins",
        "https://github.com/infiquetra/infiquetra-codex-plugins.git",
    )
    source = _repository(
        layout / "infiquetra-claude-plugins",
        "git@github.com:infiquetra/infiquetra-claude-plugins.git",
    )
    detached = tmp_path / "outside-layout" / "detached-worktree"
    _git(primary, "worktree", "add", "--detach", str(detached))
    return detached, source


def test_detached_worktree_resolves_a_valid_sibling_checkout(
    tmp_path: Path,
    port_source_resolver: Callable[..., Path],
) -> None:
    detached, source = _linked_worktree_layout(tmp_path)

    assert port_source_resolver(detached, EXPECTED_SOURCE, environ={}) == source


def test_explicit_override_wins_over_automatic_discovery(
    tmp_path: Path,
    port_source_resolver: Callable[..., Path],
) -> None:
    detached, _ = _linked_worktree_layout(tmp_path)
    override = _repository(
        tmp_path / "nonstandard-source",
        "https://github.com/infiquetra/infiquetra-claude-plugins.git",
    )

    assert port_source_resolver(
        detached,
        EXPECTED_SOURCE,
        environ={PORT_SOURCE_REPO_ENV: str(override)},
    ) == override


def test_missing_automatic_candidate_fails_with_the_override_remedy(
    tmp_path: Path,
    port_source_resolver: Callable[..., Path],
    port_source_resolution_error: type[RuntimeError],
) -> None:
    primary = _repository(
        tmp_path / "layout" / "infiquetra-codex-plugins",
        "https://github.com/infiquetra/infiquetra-codex-plugins.git",
    )
    detached = tmp_path / "elsewhere" / "detached-worktree"
    _git(primary, "worktree", "add", "--detach", str(detached))

    with pytest.raises(port_source_resolution_error, match=PORT_SOURCE_REPO_ENV):
        port_source_resolver(detached, EXPECTED_SOURCE, environ={})


def test_unavailable_git_command_fails_with_the_override_remedy(
    tmp_path: Path,
    port_source_resolver: Callable[..., Path],
    port_source_resolution_error: type[RuntimeError],
) -> None:
    def unavailable_git(*args, **kwargs):
        raise OSError("git unavailable")

    with pytest.raises(port_source_resolution_error, match=PORT_SOURCE_REPO_ENV):
        port_source_resolver(
            tmp_path,
            EXPECTED_SOURCE,
            environ={},
            runner=unavailable_git,
        )


def test_malformed_common_directory_fails_with_the_override_remedy(
    tmp_path: Path,
    port_source_resolver: Callable[..., Path],
    port_source_resolution_error: type[RuntimeError],
) -> None:
    def malformed_git(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout="relative/.git\n", stderr="")

    with pytest.raises(port_source_resolution_error, match=PORT_SOURCE_REPO_ENV):
        port_source_resolver(
            tmp_path,
            EXPECTED_SOURCE,
            environ={},
            runner=malformed_git,
        )


def test_mismatched_origin_reports_expected_and_observed_identities(
    tmp_path: Path,
    port_source_resolver: Callable[..., Path],
    port_source_resolution_error: type[RuntimeError],
) -> None:
    wrong = _repository(
        tmp_path / "wrong-source",
        "https://github.com/example/not-the-claude-source.git",
    )

    with pytest.raises(port_source_resolution_error) as error:
        port_source_resolver(
            tmp_path,
            EXPECTED_SOURCE,
            environ={PORT_SOURCE_REPO_ENV: str(wrong)},
        )

    assert EXPECTED_SOURCE in str(error.value)
    assert "example/not-the-claude-source" in str(error.value)


@pytest.mark.parametrize(
    "origin",
    [
        "https://github.com/infiquetra/infiquetra-claude-plugins.git",
        "ssh://git@github.com/infiquetra/infiquetra-claude-plugins.git",
    ],
)
def test_normalized_github_origins_are_accepted(
    tmp_path: Path,
    origin: str,
    port_source_resolver: Callable[..., Path],
) -> None:
    source = _repository(tmp_path / "source", origin)

    assert port_source_resolver(
        tmp_path,
        EXPECTED_SOURCE,
        environ={PORT_SOURCE_REPO_ENV: str(source)},
    ) == source


@pytest.mark.parametrize(
    "relative_path",
    [
        "tests/test_lease_registry_forward_compat_port_contract.py",
        "tests/test_codex_627_seam_refreeze_port_contract.py",
    ],
)
def test_frozen_source_contracts_use_the_shared_resolver(relative_path: str) -> None:
    contents = (ROOT / relative_path).read_text(encoding="utf-8")

    assert "port_source_oracle" in contents
    assert "DEFAULT_SOURCE_REPO" not in contents
    assert "pytest.skip" not in contents
