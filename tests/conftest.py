"""Shared pytest fixtures and frozen-source port-contract support."""

from __future__ import annotations

import json
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


# --- Codex execution-environment fixtures -----------------------------------------------------
#
# Two skill mechanisms this repository has previously conflated. Both shapes below were settled
# empirically against the installed 0.147.0 binary, after two rounds of cross-review found
# earlier drafts modelling things that do not exist:
#
#   host-installed   a skill shipped inside a plugin, discovered from a SkillScope Codex already
#                    knows about — `user`, `repo`, `system` or `admin`. Reading it needs no
#                    additional permission.
#   executor-backed  a resource owned by an execution environment. The client names the root at
#                    thread start as a SelectedCapabilityRoot, and the resource is addressed by
#                    handles resolved through `skills.list` and `skills.read` over the app server.
#
# The executor shape below is read from tagged source at `rust-v0.147.0`, after three rounds of
# cross-review found three successive drafts modelling something that does not exist:
#
#   the root's `path` must be an execution-environment PLUGIN TREE, not a directory of documents:
#     <path>/.codex-plugin/plugin.json     {"name": "<plugin name>"}
#     <path>/skills/<name>/SKILL.md        with `name` and `description` frontmatter
#   codex-rs/app-server/tests/suite/v2/executor_skills.rs:145-200
#
#   the AUTHORITY IS THE ROOT ID. `SkillAuthority::new(SkillSourceKind::Executor, selected_root_id)`
#   and `handle_prefix = format!("skill://{selected_root_id}/")` — an earlier draft used separate
#   values for the two, which cannot resolve.
#   codex-rs/ext/skills/src/provider/executor.rs:189-225
#
#   a handle is `skill://<root id>/<environment path, leading slash trimmed>`, so it EMBEDS the
#   path rather than hiding it, and its segment count varies with directory depth. An earlier
#   draft invented a fixed `skill://authority/package/resource` triple and asserted three
#   segments, which is wrong in both respects.
#
#   `skills.read` takes THREE SEPARATE arguments — `authority` (an object), `package` and
#   `resource` — not one URI string. `skills.list` takes `{"authority": {"kind": "executor"}}`.
#   codex-rs/app-server/tests/suite/v2/executor_skills.rs:269-311
#
# The permission shape is the one the binary actually accepts, not the app-server request schema
# it resembles. Confirmed by feeding candidates to `codex --strict-config`:
#
#   [permissions.<id>.filesystem] with "path" = "access" mappings   ACCEPTED
#   [permissions.<id>.filesystem] with read = [...] arrays          REJECTED, "data did not match
#                                                                   any variant of untagged enum
#                                                                   FilesystemPermissionToml"
#   [permissions.<id>.fileSystem] (camelCase)                       silently ignored, which is
#                                                                   worse than rejected
#
# `read`, `write` and `deny` are canonical; `read-write`, `read_write` and `full` are rejected.
# `none` is accepted only as a LEGACY INPUT ALIAS for `deny`, marked in source as retained
# temporarily for compatibility, so these fixtures write `deny` and accept `none` on input:
#   codex-rs/protocol/src/permissions.rs:110-118
# A profile table also requires a top-level `default_permissions`.
#
# These fixtures build shapes and assert nothing about behaviour: what the binary does with them
# is what the proof units observe.

FILESYSTEM_ACCESS_CANONICAL = ("read", "write", "deny")
# Accepted on input and rewritten to the canonical spelling before anything is written to disk.
FILESYSTEM_ACCESS_ALIASES = {"none": "deny"}


@pytest.fixture
def isolated_codex_home(tmp_path: Path) -> Path:
    """An empty Codex home a probe may populate and discard, never the operator's real one."""

    home = tmp_path / "codex-home"
    home.mkdir(mode=0o700)
    return home


@pytest.fixture(scope="session")
def app_server_thread_start_schema(tmp_path_factory) -> dict[str, Any]:
    """The installed binary's OWN schema for `thread/start` parameters.

    Cross-review's objection to the executor fixture was not that its shape was wrong -- by this
    point the shape had been read out of tagged source -- but that nothing put the object through
    Codex, leaving a hand-written assertion checking a hand-written fixture. This closes that
    without a live session: `codex app-server generate-json-schema` makes the binary emit its own
    definition, so the adjudicator is Codex rather than this repository's opinion of Codex.

    Session-scoped because generating the bundle costs a subprocess and the result cannot vary
    within a run. Requires no model, no network and no credentials.
    """

    home = tmp_path_factory.mktemp("schema-codex-home")
    out = tmp_path_factory.mktemp("schema-bundle")
    result = subprocess.run(
        [
            "codex",
            "app-server",
            "generate-json-schema",
            "--experimental",
            "--out",
            str(out),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
        env={**os.environ, "CODEX_HOME": str(home)},
    )
    # Failing, not skipping. `needs_codex` already covers the only legitimate absence -- no
    # binary installed. An installed Codex that stops emitting its schema, or emits no
    # ThreadStartParams, is the protocol disappearing underneath U8, which is exactly the drift
    # these tests exist to catch; skipping there would report success for a harness that can no
    # longer check anything.
    if result.returncode != 0:
        raise AssertionError(
            f"the installed codex could not generate its app-server schema "
            f"(exit {result.returncode})"
        )
    document = out / "v2" / "ThreadStartParams.json"
    if not document.is_file():
        raise AssertionError("the generated schema bundle carries no v2 ThreadStartParams")
    return json.loads(document.read_text(encoding="utf-8"))


@pytest.fixture
def host_installed_skill(isolated_codex_home: Path) -> dict[str, Any]:
    """A plugin-shipped skill discovered from an ordinary scope, needing no extra permission."""

    root = isolated_codex_home / "skills" / "verified-workflows-probe"
    root.mkdir(parents=True)
    document = root / "SKILL.md"
    document.write_text(
        "---\n"
        "name: verified-workflows-probe\n"
        "description: Host-installed probe skill for runtime proof fixtures.\n"
        "---\n\n"
        "Return the single token HOST_INSTALLED_SKILL_OK and nothing else.\n",
        encoding="utf-8",
    )
    return {
        "mechanism": "host-installed",
        "name": "verified-workflows-probe",
        "scope": "user",
        "root": root,
        "document": document,
        "marker": "HOST_INSTALLED_SKILL_OK",
    }


@pytest.fixture
def executor_capability_root(tmp_path: Path) -> Callable[..., dict[str, Any]]:
    """Build a SelectedCapabilityRoot and the `skill://` handle that addresses its resource.

    The backing directory sits outside the Codex home, because that separation is what makes the
    permission boundary observable: a read that succeeds without the root being granted has
    proved nothing about the executor-backed mechanism, since a host-installed read would have
    succeeded too.
    """

    def _build(
        root_id: str = "probe-plugin@1",
        environment_id: str = "probe-env",
        plugin_name: str = "probe-plugin",
        skill_name: str = "executor_probe",
    ) -> dict[str, Any]:
        # A plugin tree, because that is what the executor's discovery walks. A directory holding
        # one Markdown file — three earlier drafts of this fixture — is not discoverable at all.
        plugin_dir = tmp_path / "executor-environment" / plugin_name
        manifest = plugin_dir / ".codex-plugin" / "plugin.json"
        skill_dir = plugin_dir / "skills" / skill_name
        manifest.parent.mkdir(parents=True)
        skill_dir.mkdir(parents=True)
        manifest.write_text(json.dumps({"name": plugin_name}), encoding="utf-8")
        document = skill_dir / "SKILL.md"
        document.write_text(
            f"---\n"
            f"name: {skill_name}\n"
            f"description: Executor-backed probe resource for runtime proof fixtures.\n"
            f"---\n\n"
            f"Return the single token EXECUTOR_BACKED_RESOURCE_OK and nothing else.\n",
            encoding="utf-8",
        )

        # `skill://<root id>/<environment path with the leading slash trimmed>`. The authority is
        # the root identifier itself, and the handle embeds the path rather than replacing it.
        def handle(path: Path) -> str:
            return f"skill://{root_id}/{path.as_posix().lstrip('/')}"

        return {
            "mechanism": "executor-backed",
            "selected_capability_root": {
                "id": root_id,
                "location": {
                    "type": "environment",
                    "environmentId": environment_id,
                    "path": str(plugin_dir),
                },
            },
            "authority": {"kind": "executor", "id": root_id},
            "package": handle(skill_dir),
            "main_resource": handle(document),
            # The two calls, with the arguments each actually takes. `skills.read` receives the
            # authority, package and resource as three separate values.
            "list_arguments": {"authority": {"kind": "executor"}},
            "read_arguments": {
                "authority": {"kind": "executor", "id": root_id},
                "package": handle(skill_dir),
                "resource": handle(document),
            },
            "resolution_route": ("skills.list", "skills.read"),
            "plugin_root": plugin_dir,
            "manifest": manifest,
            "backing_path": skill_dir,
            "document": document,
            "marker": "EXECUTOR_BACKED_RESOURCE_OK",
        }

    return _build


@pytest.fixture
def permission_profile_writer(isolated_codex_home: Path) -> Callable[..., Path]:
    """Write a named permission profile in the shape Codex 0.147.0 actually accepts.

    Omitting a path is the negative case: the read must fail closed rather than return partial
    or unsandboxed content. A path mapped to `none` is the explicit denial case, which is a
    different thing from an absent entry and worth being able to express separately.
    """

    def _write(
        profile_id: str,
        *,
        filesystem: Mapping[Path | str, str] | None = None,
        network: bool = False,
        make_default: bool = True,
    ) -> Path:
        entries = dict(filesystem or {})
        allowed = set(FILESYSTEM_ACCESS_CANONICAL) | set(FILESYSTEM_ACCESS_ALIASES)
        unknown = sorted(set(entries.values()) - allowed)
        if unknown:
            raise ValueError(
                f"Codex 0.147.0 accepts only {FILESYSTEM_ACCESS_CANONICAL} as filesystem access "
                f"(with {sorted(FILESYSTEM_ACCESS_ALIASES)} as a legacy alias), got {unknown}"
            )
        lines: list[str] = []
        if make_default:
            lines.append(f'default_permissions = "{profile_id}"')
        lines.append(f"[permissions.{profile_id}.filesystem]")
        for path, access in entries.items():
            # Written canonically even when the caller passed the legacy alias. A fixture that
            # emits a spelling source marks as temporary is a trap with a delayed fuse.
            canonical = FILESYSTEM_ACCESS_ALIASES.get(access, access)
            lines.append(f'"{Path(path).as_posix()}" = "{canonical}"')
        lines.append(f"[permissions.{profile_id}.network]")
        lines.append(f"enabled = {'true' if network else 'false'}")

        config = isolated_codex_home / "config.toml"
        existing = config.read_text(encoding="utf-8") if config.is_file() else ""
        config.write_text(existing + "\n".join(lines) + "\n", encoding="utf-8")
        return config

    return _write
