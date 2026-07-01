from __future__ import annotations

from pathlib import Path

import yaml

from helpers import load_module, make_repo, valid_manifest


def test_postprocess_preserves_originals_and_writes_final_assets(tmp_path: Path) -> None:
    mod = load_module()
    repo = make_repo(tmp_path)
    avatar_original = repo / "assets/discord/originals/mimir-avatar.png"
    original_hash = mod.sha256_file(avatar_original)

    result = mod.postprocess_assets(repo, "mimir")

    assert mod.sha256_file(avatar_original) == original_hash
    assert result["assets"]["avatar"]["width"] == 512
    assert result["assets"]["avatar"]["height"] == 512
    assert result["assets"]["banner"]["width"] == 960
    assert result["assets"]["banner"]["height"] == 540
    prompt_record = yaml.safe_load((repo / "assets/discord/prompts/mimir.yml").read_text())
    assert prompt_record["prompt_consistency"] == "pending"
    assert prompt_record["prompts"]["avatar"] == "wise portrait"
    assert (repo / result["receipt"]["json"]).is_file()
    assert (repo / result["receipt"]["markdown"]).is_file()
    assert (repo / result["runbook"]).is_file()


def test_postprocess_rejects_missing_original(tmp_path: Path) -> None:
    mod = load_module()
    repo = make_repo(tmp_path)
    (repo / "assets/discord/originals/mimir-avatar.png").unlink()

    try:
        mod.postprocess_assets(repo, "mimir")
    except mod.ManifestError as exc:
        assert "missing original image" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ManifestError")


def test_postprocess_rejects_avatar_and_banner_same_final_path(tmp_path: Path) -> None:
    mod = load_module()
    manifest = valid_manifest()
    manifest["targets"][0]["asset_paths"]["finals"]["banner"] = "assets/discord/avatars/mimir.png"
    repo = make_repo(tmp_path, manifest)

    try:
        mod.postprocess_assets(repo, "mimir")
    except mod.ManifestError as exc:
        assert "avatar and banner final paths" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ManifestError")


def test_publish_requires_passed_prompt_consistency(tmp_path: Path) -> None:
    mod = load_module()
    repo = make_repo(tmp_path)
    mod.postprocess_assets(repo, "mimir")
    plan = mod.build_publish_plan(repo, "mimir")

    try:
        mod.publish_assets(
            repo,
            "mimir",
            plan["confirmation_id"],
            do_publish=True,
            environ={"vault_discord_bot_token_mimir": "A" * 60},
            transport=lambda *_args: (200, {}),
        )
    except mod.PublishError as exc:
        assert "prompt consistency" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected PublishError")
