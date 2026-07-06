from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml
from PIL import Image


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "discord_identity_assets.py"


def load_module():
    spec = importlib.util.spec_from_file_location("discord_identity_assets", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def write_profiles(repo: Path) -> None:
    write_yaml(
        repo / "deploy/team_profiles.yml",
        {
            "hermes_team_profiles": [
                {
                    "name": "mimir-engineer",
                    "persona": "mimir",
                    "discord_token_var": "vault_discord_bot_token_mimir",
                    "bot_user_id": "1486896133660868758",
                },
                {
                    "name": "s-ivaldi-developer",
                    "persona": "s-ivaldi-developer",
                    "headless": True,
                },
            ]
        },
    )


def valid_manifest(bot_user_id: str = "1486896133660868758") -> dict:
    return {
        "schema_version": 1,
        "targets": [
            {
                "id": "mimir",
                "display_name": "Mimir",
                "persona": "mimir",
                "profile": "mimir-engineer",
                "prompt_sources": ["deploy/team_profiles.yml"],
                "prompts": {"avatar": "wise portrait", "banner": "well of wisdom"},
                "asset_paths": {
                    "originals": {
                        "avatar": "assets/discord/originals/mimir-avatar.png",
                        "banner": "assets/discord/originals/mimir-banner.png",
                    },
                    "finals": {
                        "avatar": "assets/discord/avatars/mimir.png",
                        "app_icon": "assets/discord/avatars/mimir.png",
                        "banner": "assets/discord/banners/mimir.png",
                    },
                    "prompt_record": "assets/discord/prompts/mimir.yml",
                },
                "discord": {
                    "application_id": "1486896133660868758",
                    "expected_bot_user_id": bot_user_id,
                    "allow_legacy_application_endpoint": True,
                },
                "token_env": "vault_discord_bot_token_mimir",
                "evidence": {"receipt_dir": "docs/runbooks/discord-identity-assets"},
            }
        ],
    }


def valid_guild_manifest(
    *,
    guild_id_env: str = "ASGARD_GUILD_ID",
    token_env: str = "ASGARD_MANAGE_GUILD_TOKEN",
    expected_actor_user_id: str = "1466648500124123146",
) -> dict:
    return {
        "schema_version": 2,
        "targets": [],
        "guild_targets": [
            {
                "id": "asgard",
                "display_name": "Asgard",
                "prompt_sources": ["README.md"],
                "prompts": {"icon": "bright hall icon", "banner": "wide hall banner"},
                "profile_banner_color": "#2F555A",
                "asset_paths": {
                    "originals": {
                        "icon": "assets/discord/guilds/asgard/originals/icon.png",
                        "banner": "assets/discord/guilds/asgard/originals/banner.png",
                    },
                    "finals": {
                        "icon": "assets/discord/guilds/asgard/icon.png",
                        "banner": "assets/discord/guilds/asgard/banner.png",
                    },
                    "prompt_record": "assets/discord/guilds/asgard/prompts.yml",
                },
                "discord": {
                    "expected_guild_name": "Asgard",
                },
                "guild_id_env": guild_id_env,
                "manage_guild_token_env": token_env,
                "expected_actor_user_id": expected_actor_user_id,
                "evidence": {"receipt_dir": "docs/runbooks/discord-identity-assets"},
            }
        ],
    }


def make_image(path: Path, size: tuple[int, int], color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path, format="PNG")


def make_repo(tmp_path: Path, manifest: dict | None = None) -> Path:
    write_profiles(tmp_path)
    write_yaml(tmp_path / "identity/discord-identity-assets.yml", manifest or valid_manifest())
    make_image(tmp_path / "assets/discord/originals/mimir-avatar.png", (1200, 900), (10, 20, 30))
    make_image(tmp_path / "assets/discord/originals/mimir-banner.png", (1800, 800), (20, 30, 40))
    return tmp_path


def make_guild_repo(tmp_path: Path, manifest: dict | None = None) -> Path:
    write_yaml(tmp_path / "identity/discord-identity-assets.yml", manifest or valid_guild_manifest())
    make_image(
        tmp_path / "assets/discord/guilds/asgard/originals/icon.png",
        (1200, 900),
        (10, 90, 90),
    )
    make_image(
        tmp_path / "assets/discord/guilds/asgard/originals/banner.png",
        (1800, 800),
        (20, 100, 120),
    )
    return tmp_path


def prepare_publishable_repo(tmp_path: Path):
    mod = load_module()
    repo = make_repo(tmp_path)
    mod.postprocess_assets(repo, "mimir")
    prompt_path = repo / "assets/discord/prompts/mimir.yml"
    prompt_record = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))
    prompt_record["prompt_consistency"] = "passed"
    prompt_path.write_text(yaml.safe_dump(prompt_record, sort_keys=False), encoding="utf-8")
    plan = mod.build_publish_plan(repo, "mimir")
    return mod, repo, plan


def prepare_publishable_guild_repo(tmp_path: Path):
    mod = load_module()
    repo = make_guild_repo(tmp_path)
    mod.postprocess_assets(repo, "asgard", kind="guild")
    prompt_path = repo / "assets/discord/guilds/asgard/prompts.yml"
    prompt_record = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))
    prompt_record["prompt_consistency"] = "passed"
    prompt_path.write_text(yaml.safe_dump(prompt_record, sort_keys=False), encoding="utf-8")
    plan = mod.build_publish_plan(repo, "asgard", kind="guild")
    return mod, repo, plan
