"""Exercise the execution-environment fixtures against the installed binary.

An unused fixture is a trap set for whichever unit eventually picks it up: two rounds of
cross-review found earlier drafts of these modelling shapes that do not exist, and nothing failed
because nothing consumed them. These tests consume them, so a fixture that stops matching the
binary fails here rather than in the middle of a proof unit.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

needs_codex = pytest.mark.skipif(
    shutil.which("codex") is None, reason="the codex executable is not installed"
)


def _strict_config_error(codex_home: Path, workspace: Path) -> str:
    """Load a config under --strict-config and return whatever Codex complained about.

    Uses a deliberately absent model provider as the stopping point, so configuration parsing is
    the only thing that can fail earlier. Reaching the provider error means the configuration was
    accepted; anything else is the parser rejecting it.
    """

    result = subprocess.run(
        [
            "codex",
            "--strict-config",
            "exec",
            "--skip-git-repo-check",
            "--ephemeral",
            "-c",
            'model_provider="absent_probe_provider"',
            "probe",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(workspace),
        env={**dict(__import__("os").environ), "CODEX_HOME": str(codex_home)},
    )
    return (result.stdout + result.stderr).strip()


@needs_codex
def test_the_permission_writer_emits_a_configuration_codex_accepts(
    isolated_codex_home: Path,
    permission_profile_writer,
    executor_capability_root,
    tmp_path: Path,
) -> None:
    """The shape was settled empirically; this keeps it settled."""

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    resource = executor_capability_root()
    permission_profile_writer("probe", filesystem={resource["backing_path"]: "read"})

    complaint = _strict_config_error(isolated_codex_home, workspace)

    assert "absent_probe_provider" in complaint, complaint
    assert "FilesystemPermissionToml" not in complaint
    assert "permissions" not in complaint.lower() or "absent_probe_provider" in complaint


@needs_codex
def test_an_absent_entry_and_an_explicit_denial_are_different_configurations(
    isolated_codex_home: Path,
    permission_profile_writer,
    executor_capability_root,
    tmp_path: Path,
) -> None:
    """`none` is an explicit denial; omitting the path is silence. U8 needs both separately."""

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    resource = executor_capability_root()
    config = permission_profile_writer("probe", filesystem={resource["backing_path"]: "deny"})
    denied = config.read_text(encoding="utf-8")

    assert '= "deny"' in denied
    assert _strict_config_error(isolated_codex_home, workspace).find("absent_probe_provider") >= 0

    config.write_text("", encoding="utf-8")
    permission_profile_writer("probe", filesystem={})
    absent = config.read_text(encoding="utf-8")
    assert '= "deny"' not in absent
    assert absent != denied


def test_an_unsupported_access_value_is_refused_before_it_reaches_codex(
    permission_profile_writer,
) -> None:
    """`read-write` and `full` are rejected by the binary; the fixture refuses them first."""

    for rejected in ("read-write", "read_write", "full", "rw"):
        with pytest.raises(ValueError, match="accepts only"):
            permission_profile_writer("probe", filesystem={"/tmp/probe": rejected})


def test_the_legacy_denial_alias_is_written_in_its_canonical_spelling(
    permission_profile_writer,
) -> None:
    """`none` is a legacy input alias for `deny`, retained temporarily by source.

    Both spellings load, so a fixture emitting the legacy one fails on nobody's clock but the day
    Codex withdraws it. It is accepted on input and written canonically.
    """

    canonical = permission_profile_writer("probe", filesystem={"/tmp/probe": "deny"})
    assert '= "deny"' in canonical.read_text(encoding="utf-8")

    canonical.write_text("", encoding="utf-8")
    aliased = permission_profile_writer("probe", filesystem={"/tmp/probe": "none"})
    body = aliased.read_text(encoding="utf-8")
    assert '= "deny"' in body
    assert '= "none"' not in body


def test_the_executor_plugin_tree_is_the_layout_discovery_walks(
    executor_capability_root,
) -> None:
    """A directory of documents is not discoverable; a plugin tree is."""

    resource = executor_capability_root()
    plugin_root = resource["plugin_root"]

    assert (plugin_root / ".codex-plugin" / "plugin.json").is_file()
    assert resource["document"].parent.parent.name == "skills"
    assert resource["document"].name == "SKILL.md"
    assert json.loads(resource["manifest"].read_text(encoding="utf-8"))["name"]
    # The root's path is the plugin directory, not the skill directory inside it.
    assert resource["selected_capability_root"]["location"]["path"] == str(plugin_root)


def test_the_authority_is_the_root_identifier_itself(executor_capability_root) -> None:
    """`SkillAuthority::new(SkillSourceKind::Executor, selected_root_id)` — one value, not two."""

    resource = executor_capability_root()
    root_id = resource["selected_capability_root"]["id"]

    assert resource["authority"] == {"kind": "executor", "id": root_id}
    assert resource["package"].startswith(f"skill://{root_id}/")
    assert resource["main_resource"].startswith(f"skill://{root_id}/")
    # The handle embeds the environment path with its leading slash trimmed. An earlier draft
    # asserted the opposite — that the path was absent — and a fixed three-segment handle.
    assert resource["main_resource"].endswith(resource["document"].as_posix().lstrip("/"))


def test_the_read_call_takes_three_separate_arguments(executor_capability_root) -> None:
    """`skills.read` receives authority, package and resource separately, not one URI."""

    resource = executor_capability_root()

    assert set(resource["read_arguments"]) == {"authority", "package", "resource"}
    assert resource["read_arguments"]["authority"] == resource["authority"]
    assert resource["read_arguments"]["resource"] == resource["main_resource"]
    assert resource["list_arguments"] == {"authority": {"kind": "executor"}}
    assert resource["resolution_route"] == ("skills.list", "skills.read")


def test_the_capability_root_carries_the_shape_thread_start_accepts(
    executor_capability_root,
) -> None:
    root = executor_capability_root()["selected_capability_root"]

    assert set(root) == {"id", "location"}
    assert set(root["location"]) == {"type", "environmentId", "path"}
    assert root["location"]["type"] == "environment"


def test_the_two_mechanisms_are_never_the_same_object(
    host_installed_skill, executor_capability_root, isolated_codex_home: Path
) -> None:
    """Conflating them is a repeat finding in this repository."""

    executor = executor_capability_root()

    assert host_installed_skill["mechanism"] == "host-installed"
    assert executor["mechanism"] == "executor-backed"
    # The host-installed skill lives in the Codex home; the executor resource deliberately does
    # not, because that is what makes the permission boundary observable.
    assert isolated_codex_home in host_installed_skill["root"].parents
    assert isolated_codex_home not in executor["backing_path"].parents


@needs_codex
def test_the_capability_root_validates_against_the_binarys_own_schema(
    executor_capability_root,
    app_server_thread_start_schema,
) -> None:
    """Codex adjudicates the fixture's shape, not this repository's opinion of Codex.

    Every other assertion about the executor shape in this file compares a hand-written fixture
    against a hand-written expectation. This one compares it against the definition the installed
    binary emits for itself, so a shape change in a future Codex fails here instead of in U8.
    """

    definitions = app_server_thread_start_schema["definitions"]
    root_schema = definitions["SelectedCapabilityRoot"]
    location_schema = definitions["CapabilityRootLocation"]
    root = executor_capability_root()["selected_capability_root"]

    assert set(root_schema["required"]) <= set(root)
    assert set(root) == set(root_schema["properties"])
    assert isinstance(root["id"], str)

    # CapabilityRootLocation is a tagged union; find the variant matching our discriminator
    # rather than assuming it is the only one, so a future Codex adding variants still passes.
    variants = [
        variant
        for variant in location_schema["oneOf"]
        if root["location"]["type"] in variant["properties"]["type"]["enum"]
    ]
    assert len(variants) == 1, "the fixture's location type matches no schema variant"
    [environment_variant] = variants
    assert set(environment_variant["required"]) <= set(root["location"])
    assert set(root["location"]) == set(environment_variant["properties"])
    for field in ("environmentId", "path"):
        assert isinstance(root["location"][field], str)
    # The schema calls this an absolute path; a relative one would resolve against whatever the
    # execution environment happened to be pointing at.
    assert Path(root["location"]["path"]).is_absolute()


@needs_codex
def test_the_thread_start_schema_still_accepts_selected_capability_roots(
    app_server_thread_start_schema,
) -> None:
    """U8 depends on this parameter existing. If Codex withdraws it, fail here and not there."""

    properties = app_server_thread_start_schema["properties"]

    assert "selectedCapabilityRoots" in properties
    assert "SelectedCapabilityRoot" in app_server_thread_start_schema["definitions"]
