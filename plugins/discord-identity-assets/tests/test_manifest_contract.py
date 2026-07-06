from __future__ import annotations

from pathlib import Path

from helpers import load_module, valid_guild_manifest, valid_manifest, write_profiles, write_yaml


def test_discovery_proposes_mimir_manifest_without_headless_targets(tmp_path: Path) -> None:
    mod = load_module()
    write_profiles(tmp_path)

    manifest = mod.discover_manifest(tmp_path, persona="mimir")

    assert manifest["schema_version"] == 1
    assert [target["id"] for target in manifest["targets"]] == ["mimir"]
    target = manifest["targets"][0]
    assert target["token_env"] == "vault_discord_bot_token_mimir"
    assert target["discord"]["expected_bot_user_id"] == "1486896133660868758"
    assert target["discord"]["application_id_candidate"] == "1486896133660868758"
    assert "discord.application_id" in target["missing_fields"]


def test_valid_publish_manifest_passes_contract(tmp_path: Path) -> None:
    mod = load_module()
    write_profiles(tmp_path)
    write_yaml(tmp_path / "identity/discord-identity-assets.yml", valid_manifest())

    assert mod.validate_manifest(tmp_path, mode="publish") == []


def test_preview_plan_summarizes_target_without_final_asset_hashes(tmp_path: Path) -> None:
    mod = load_module()
    write_profiles(tmp_path)
    write_yaml(tmp_path / "identity/discord-identity-assets.yml", valid_manifest())

    plan = mod.preview_plan(tmp_path, "mimir")

    assert plan["surfaces"] == ["avatar", "app_icon", "banner"]
    assert plan["token_env"] == "vault_discord_bot_token_mimir"
    assert plan["asset_paths"]["finals"]["banner"] == "assets/discord/banners/mimir.png"
    assert "Preview only" in plan["note"]
    assert "assets" not in plan


def test_manifest_conflict_with_discovered_bot_user_id_fails(tmp_path: Path) -> None:
    mod = load_module()
    write_profiles(tmp_path)
    write_yaml(
        tmp_path / "identity/discord-identity-assets.yml",
        valid_manifest(bot_user_id="000000000000000000"),
    )

    errors = mod.validate_manifest(tmp_path, mode="publish")

    assert any("conflicts with deploy/team_profiles.yml" in error for error in errors)


def test_token_material_in_manifest_is_rejected(tmp_path: Path) -> None:
    mod = load_module()
    write_profiles(tmp_path)
    manifest = valid_manifest()
    manifest["targets"][0]["token_env"] = "AAAAAAAAAAAAAAAAAAAA.BBBBBB.CCCCCCCCCCCCCCCCCCCC"
    write_yaml(tmp_path / "identity/discord-identity-assets.yml", manifest)

    errors = mod.validate_manifest(tmp_path, mode="publish")

    assert any("token material" in error for error in errors)


def test_opaque_token_material_in_manifest_is_rejected(tmp_path: Path) -> None:
    mod = load_module()
    write_profiles(tmp_path)
    manifest = valid_manifest()
    manifest["targets"][0]["token_env"] = "A" * 60
    write_yaml(tmp_path / "identity/discord-identity-assets.yml", manifest)

    errors = mod.validate_manifest(tmp_path, mode="publish")

    assert any("token material" in error for error in errors)


def test_valid_guild_publish_manifest_passes_contract(tmp_path: Path) -> None:
    mod = load_module()
    write_yaml(tmp_path / "identity/discord-identity-assets.yml", valid_guild_manifest())

    assert mod.validate_manifest(tmp_path, mode="publish", kind="guild") == []


def test_guild_targets_require_schema_v2(tmp_path: Path) -> None:
    mod = load_module()
    manifest = valid_guild_manifest()
    manifest["schema_version"] = 1
    write_yaml(tmp_path / "identity/discord-identity-assets.yml", manifest)

    errors = mod.validate_manifest(tmp_path, mode="publish", kind="guild")

    assert any("schema_version must be 2" in error for error in errors)


def test_guild_manifest_rejects_secret_token_value(tmp_path: Path) -> None:
    mod = load_module()
    manifest = valid_guild_manifest(token_env="A" * 60)
    write_yaml(tmp_path / "identity/discord-identity-assets.yml", manifest)

    errors = mod.validate_manifest(tmp_path, mode="publish", kind="guild")

    assert any("token material" in error for error in errors)


def test_guild_manifest_rejects_bad_profile_color(tmp_path: Path) -> None:
    mod = load_module()
    manifest = valid_guild_manifest()
    manifest["guild_targets"][0]["profile_banner_color"] = "teal"
    write_yaml(tmp_path / "identity/discord-identity-assets.yml", manifest)

    errors = mod.validate_manifest(tmp_path, mode="publish", kind="guild")

    assert any("profile_banner_color" in error for error in errors)


def test_guild_scaffold_appends_v2_target_without_writing_by_default(tmp_path: Path) -> None:
    mod = load_module()
    write_yaml(tmp_path / "identity/discord-identity-assets.yml", valid_manifest())

    manifest = mod.scaffold_guild_manifest(
        tmp_path,
        target_id="asgard",
        display_name="Asgard",
        expected_guild_name="Asgard",
        guild_id_env="ASGARD_GUILD_ID",
        manage_guild_token_env="ASGARD_MANAGE_GUILD_TOKEN",
    )

    assert manifest["schema_version"] == 2
    assert manifest["targets"][0]["id"] == "mimir"
    assert manifest["guild_targets"][0]["id"] == "asgard"
    assert manifest["guild_targets"][0]["missing_fields"] == ["prompts.icon", "prompts.banner"]
    on_disk = mod.load_manifest(tmp_path)
    assert on_disk["schema_version"] == 1
