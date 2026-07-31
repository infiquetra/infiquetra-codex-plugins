"""Shared pytest fixtures and frozen-source port-contract support."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest


PORT_SOURCE_REPO_ENV = "CODEX_PORT_SOURCE_REPO"


class PortSourceResolutionError(RuntimeError):
    """A frozen-source oracle could not find the source checkout it must verify."""


def resolve_port_source_repo(
    repo_root: Path,
    expected_repository_id: str,
    *,
    environ: Mapping[str, str] | None = None,
    runner: Callable[..., Any] | None = None,
) -> Path:
    """Return a Git-verified source checkout for a frozen-source port oracle.

    ``CODEX_PORT_SOURCE_REPO`` takes precedence for nonstandard layouts. Otherwise the source
    checkout is the sibling of the primary clone identified by Git's worktree-stable common
    directory. A matching GitHub ``origin`` is required before a caller can read frozen refs.
    """

    expected = _expected_repository_id(expected_repository_id)
    configured = (os.environ if environ is None else environ).get(PORT_SOURCE_REPO_ENV)
    if configured:
        candidate = Path(configured)
        route = f"the {PORT_SOURCE_REPO_ENV} override"
    else:
        try:
            common_dir = _git_output(
                repo_root,
                "rev-parse",
                "--path-format=absolute",
                "--git-common-dir",
                runner=runner,
            )
        except PortSourceResolutionError as error:
            raise _resolution_error(
                expected,
                f"Git could not determine the common directory from {repo_root}",
            ) from error
        common_path = Path(common_dir)
        if not common_path.is_absolute() or common_path.name != ".git":
            raise _resolution_error(
                expected,
                "Git did not report an absolute primary-clone .git common directory",
            )
        candidate = common_path.parent.parent / expected.rsplit("/", maxsplit=1)[1]
        route = f"automatic sibling discovery at {candidate}"

    _require_git_worktree(candidate, expected, route, runner=runner)
    observed = _origin_repository_id(candidate, expected, route, runner=runner)
    if observed != expected:
        raise _resolution_error(
            expected,
            f"{route} resolved {candidate}, whose origin is {observed!r}",
        )
    return candidate


def require_port_source_repo(repo_root: Path, expected_repository_id: str) -> Path:
    """Return the verified source checkout or fail the calling pytest oracle loudly."""

    try:
        return resolve_port_source_repo(repo_root, expected_repository_id)
    except PortSourceResolutionError as error:
        pytest.fail(str(error))


@pytest.fixture
def port_source_resolver() -> Callable[..., Path]:
    """Expose the directly testable resolver to pytest modules."""

    return resolve_port_source_repo


@pytest.fixture
def port_source_oracle() -> Callable[[Path, str], Path]:
    """Expose fail-closed source resolution to frozen-source contract tests."""

    return require_port_source_repo


@pytest.fixture
def port_source_resolution_error() -> type[PortSourceResolutionError]:
    """Expose the resolver's specific exception type to its focused tests."""

    return PortSourceResolutionError


def _expected_repository_id(repository_id: str) -> str:
    parts = repository_id.strip("/").split("/")
    if len(parts) != 2 or any(part in {"", ".", ".."} for part in parts):
        raise PortSourceResolutionError(
            f"Frozen-source port oracle received invalid expected repository identity "
            f"{repository_id!r}; set {PORT_SOURCE_REPO_ENV} only after fixing the manifest."
        )
    return "/".join(parts)


def _git_output(
    repo_root: Path,
    *args: str,
    runner: Callable[..., Any] | None,
) -> str:
    run = subprocess.run if runner is None else runner
    try:
        result = run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        raise _resolution_error(
            None,
            f"Git is unavailable while resolving the source checkout from {repo_root}",
        ) from None
    if getattr(result, "returncode", 1) != 0 or not isinstance(
        getattr(result, "stdout", None), str
    ):
        raise _resolution_error(
            None,
            f"Git could not resolve the source checkout from {repo_root}",
        )
    return result.stdout.strip()


def _require_git_worktree(
    candidate: Path,
    expected: str,
    route: str,
    *,
    runner: Callable[..., Any] | None,
) -> None:
    try:
        is_worktree = _git_output(
            candidate,
            "rev-parse",
            "--is-inside-work-tree",
            runner=runner,
        )
    except PortSourceResolutionError as error:
        raise _resolution_error(
            expected,
            f"{route} did not resolve a usable Git worktree at {candidate}",
        ) from error
    if is_worktree != "true":
        raise _resolution_error(
            expected,
            f"{route} did not resolve a Git worktree at {candidate}",
        )


def _origin_repository_id(
    candidate: Path,
    expected: str,
    route: str,
    *,
    runner: Callable[..., Any] | None,
) -> str:
    try:
        origin = _git_output(
            candidate,
            "config",
            "--get",
            "remote.origin.url",
            runner=runner,
        )
    except PortSourceResolutionError as error:
        raise _resolution_error(
            expected,
            f"{route} has no readable origin at {candidate}",
        ) from error

    if origin.startswith("https://github.com/"):
        path = origin.removeprefix("https://github.com/")
    elif origin.startswith("ssh://git@github.com/"):
        path = origin.removeprefix("ssh://git@github.com/")
    elif origin.startswith("git@github.com:"):
        path = origin.removeprefix("git@github.com:")
    else:
        raise _resolution_error(
            expected,
            f"{route} has an unrecognized GitHub origin at {candidate}",
        )

    parts = path.removesuffix(".git").strip("/").split("/")
    if len(parts) != 2 or any(not part for part in parts):
        raise _resolution_error(
            expected,
            f"{route} has a malformed GitHub origin at {candidate}",
        )
    return "/".join(parts)


def _resolution_error(expected: str | None, reason: str) -> PortSourceResolutionError:
    expected_text = f" Expected repository identity: {expected}." if expected else ""
    return PortSourceResolutionError(
        f"Frozen-source port oracle cannot resolve a verified source checkout: {reason}."
        f"{expected_text} Set {PORT_SOURCE_REPO_ENV} to a Git checkout whose origin matches the "
        "expected repository identity."
    )


@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Mock subprocess.run for runner command execution."""
    mock = MagicMock()
    mock.return_value.returncode = 0
    mock.return_value.stdout = "Success"
    mock.return_value.stderr = ""
    monkeypatch.setattr("subprocess.run", mock)
    return mock
