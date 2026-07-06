from __future__ import annotations

from pathlib import Path

import yaml

from helpers import prepare_publishable_guild_repo, prepare_publishable_repo


class MockDiscord:
    def __init__(
        self,
        *,
        wrong_user: bool = False,
        empty_banner: bool = False,
        current_app_patch_status: int = 200,
    ) -> None:
        self.calls: list[tuple[str, str, dict[str, str], bytes | None]] = []
        self.wrong_user = wrong_user
        self.empty_banner = empty_banner
        self.current_app_patch_status = current_app_patch_status

    def __call__(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes | None,
    ) -> tuple[int, dict]:
        self.calls.append((method, path, headers, body))
        if (method, path) == ("GET", "/users/@me"):
            return 200, {"id": "wrong" if self.wrong_user else "1486896133660868758"}
        if (method, path) == ("GET", "/applications/@me"):
            return 200, {"id": "1486896133660868758"}
        if method == "PATCH" and path == "/users/@me":
            text = (body or b"").decode()
            if "avatar" in text:
                return 200, {"avatar": "avatar-hash", "banner": "existing-banner"}
            return 200, {"avatar": "avatar-hash", "banner": "" if self.empty_banner else "banner-hash"}
        if (method, path) == ("PATCH", "/applications/@me"):
            if self.current_app_patch_status != 200:
                return self.current_app_patch_status, {"message": "current application patch unavailable"}
            return 200, {"icon": "icon-hash"}
        if (method, path) == ("PATCH", "/applications/1486896133660868758"):
            return 200, {"icon": "icon-hash"}
        return 404, {"message": "unexpected"}


class MockGuildDiscord:
    def __init__(
        self,
        *,
        wrong_actor: bool = False,
        wrong_guild_name: bool = False,
        banner_feature: bool = True,
        icon_patch_status: int = 200,
        banner_patch_status: int = 200,
    ) -> None:
        self.calls: list[tuple[str, str, dict[str, str], bytes | None]] = []
        self.wrong_actor = wrong_actor
        self.wrong_guild_name = wrong_guild_name
        self.banner_feature = banner_feature
        self.icon_patch_status = icon_patch_status
        self.banner_patch_status = banner_patch_status

    def __call__(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes | None,
    ) -> tuple[int, dict]:
        self.calls.append((method, path, headers, body))
        if (method, path) == ("GET", "/users/@me"):
            return 200, {"id": "wrong" if self.wrong_actor else "1466648500124123146"}
        if (method, path) == ("GET", "/guilds/1503058365335736549"):
            features = ["BANNER"] if self.banner_feature else []
            return 200, {"id": "1503058365335736549", "name": "Wrong" if self.wrong_guild_name else "Asgard", "features": features}
        if (method, path) == ("PATCH", "/guilds/1503058365335736549"):
            text = (body or b"").decode()
            if "icon" in text:
                if self.icon_patch_status != 200:
                    return self.icon_patch_status, {"message": "missing manage guild"}
                return 200, {"name": "Asgard", "icon": "guild-icon-hash", "banner": "old-banner"}
            if self.banner_patch_status != 200:
                return self.banner_patch_status, {"message": "missing banner feature"}
            return 200, {"name": "Asgard", "icon": "guild-icon-hash", "banner": "guild-banner-hash"}
        return 404, {"message": "unexpected"}


def test_publish_success_records_all_three_remote_identifiers(tmp_path: Path) -> None:
    mod, repo, plan = prepare_publishable_repo(tmp_path)
    transport = MockDiscord()

    result = mod.publish_assets(
        repo,
        "mimir",
        plan["confirmation_id"],
        do_publish=True,
        environ={"vault_discord_bot_token_mimir": "A" * 60},
        transport=transport,
    )

    assert result["mode"] == "publish"
    assert result["remote"]["avatar"]["hash"] == "avatar-hash"
    assert result["remote"]["app_icon"]["hash"] == "icon-hash"
    assert result["remote"]["banner"]["hash"] == "banner-hash"
    assert [call[:2] for call in transport.calls] == [
        ("GET", "/users/@me"),
        ("GET", "/applications/@me"),
        ("PATCH", "/users/@me"),
        ("PATCH", "/applications/@me"),
        ("PATCH", "/users/@me"),
    ]


def test_wrong_bot_identity_blocks_before_patch(tmp_path: Path) -> None:
    mod, repo, plan = prepare_publishable_repo(tmp_path)
    transport = MockDiscord(wrong_user=True)

    try:
        mod.publish_assets(
            repo,
            "mimir",
            plan["confirmation_id"],
            do_publish=True,
            environ={"vault_discord_bot_token_mimir": "A" * 60},
            transport=transport,
        )
    except mod.PublishError as exc:
        assert "wrong bot user" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected PublishError")

    assert [call[:2] for call in transport.calls] == [("GET", "/users/@me")]


def test_application_icon_publish_uses_legacy_fallback_when_allowed(tmp_path: Path) -> None:
    mod, repo, plan = prepare_publishable_repo(tmp_path)
    transport = MockDiscord(current_app_patch_status=403)

    result = mod.publish_assets(
        repo,
        "mimir",
        plan["confirmation_id"],
        do_publish=True,
        environ={"vault_discord_bot_token_mimir": "A" * 60},
        transport=transport,
    )

    assert result["remote"]["app_icon"] == {
        "endpoint": "/applications/1486896133660868758",
        "hash": "icon-hash",
    }
    assert ("PATCH", "/applications/1486896133660868758") in [
        call[:2] for call in transport.calls
    ]


def test_application_icon_publish_does_not_fallback_on_rate_limit(tmp_path: Path) -> None:
    mod, repo, plan = prepare_publishable_repo(tmp_path)
    transport = MockDiscord(current_app_patch_status=429)

    try:
        mod.publish_assets(
            repo,
            "mimir",
            plan["confirmation_id"],
            do_publish=True,
            environ={"vault_discord_bot_token_mimir": "A" * 60},
            transport=transport,
        )
    except mod.PublishError as exc:
        assert "partial state" in str(exc)
        assert "status 429" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected PublishError")

    calls = [call[:2] for call in transport.calls]
    assert ("PATCH", "/applications/1486896133660868758") not in calls
    receipts = sorted((repo / "docs/runbooks/discord-identity-assets").glob("*partial-failure.json"))
    assert receipts
    payload = yaml.safe_load(receipts[-1].read_text())
    assert payload["partial_failure"]["changed_surfaces"] == ["avatar"]
    assert payload["partial_failure"]["failed_surface"] == "app_icon"


def test_partial_failure_receipt_records_changed_surface(tmp_path: Path) -> None:
    mod, repo, plan = prepare_publishable_repo(tmp_path)

    try:
        mod.publish_assets(
            repo,
            "mimir",
            plan["confirmation_id"],
            do_publish=True,
            environ={"vault_discord_bot_token_mimir": "A" * 60},
            transport=MockDiscord(empty_banner=True),
        )
    except mod.PublishError as exc:
        assert "partial state" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected PublishError")

    receipts = sorted((repo / "docs/runbooks/discord-identity-assets").glob("*partial-failure.json"))
    assert receipts
    payload = yaml.safe_load(receipts[-1].read_text())
    assert payload["partial_failure"]["changed_surfaces"] == ["avatar", "app_icon"]
    assert payload["partial_failure"]["failed_surface"] == "banner"


def test_guild_publish_success_records_icon_and_banner(tmp_path: Path) -> None:
    mod, repo, plan = prepare_publishable_guild_repo(tmp_path)
    transport = MockGuildDiscord()

    result = mod.publish_assets(
        repo,
        "asgard",
        plan["confirmation_id"],
        do_publish=True,
        kind="guild",
        environ={"ASGARD_MANAGE_GUILD_TOKEN": "A" * 60, "ASGARD_GUILD_ID": "1503058365335736549"},
        transport=transport,
    )

    assert result["mode"] == "publish"
    assert result["remote"]["icon"]["hash"] == "guild-icon-hash"
    assert result["remote"]["banner"]["hash"] == "guild-banner-hash"
    assert [call[:2] for call in transport.calls] == [
        ("GET", "/users/@me"),
        ("GET", "/guilds/1503058365335736549"),
        ("PATCH", "/guilds/1503058365335736549"),
        ("PATCH", "/guilds/1503058365335736549"),
    ]
    receipt_text = (repo / result["receipt"]["json"]).read_text(encoding="utf-8")
    assert "1503058365335736549" not in receipt_text
    assert "/guilds/{guild_id}" in receipt_text


def test_guild_publish_blocks_wrong_actor_before_patch(tmp_path: Path) -> None:
    mod, repo, plan = prepare_publishable_guild_repo(tmp_path)
    transport = MockGuildDiscord(wrong_actor=True)

    try:
        mod.publish_assets(
            repo,
            "asgard",
            plan["confirmation_id"],
            do_publish=True,
            kind="guild",
            environ={"ASGARD_MANAGE_GUILD_TOKEN": "A" * 60, "ASGARD_GUILD_ID": "1503058365335736549"},
            transport=transport,
        )
    except mod.PublishError as exc:
        assert "wrong Discord actor" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected PublishError")

    assert [call[:2] for call in transport.calls] == [("GET", "/users/@me")]


def test_guild_publish_records_icon_only_when_banner_feature_missing(tmp_path: Path) -> None:
    mod, repo, plan = prepare_publishable_guild_repo(tmp_path)
    transport = MockGuildDiscord(banner_feature=False)

    result = mod.publish_assets(
        repo,
        "asgard",
        plan["confirmation_id"],
        do_publish=True,
        kind="guild",
        environ={"ASGARD_MANAGE_GUILD_TOKEN": "A" * 60, "ASGARD_GUILD_ID": "1503058365335736549"},
        transport=transport,
    )

    assert result["mode"] == "partial-failure"
    assert result["remote"]["icon"]["hash"] == "guild-icon-hash"
    assert result["partial_failure"]["changed_surfaces"] == ["icon"]
    assert result["partial_failure"]["failed_surface"] == "banner"
    assert ("PATCH", "/guilds/1503058365335736549") in [call[:2] for call in transport.calls]
    assert [call[:2] for call in transport.calls].count(("PATCH", "/guilds/1503058365335736549")) == 1


def test_guild_publish_records_permission_failure_without_guild_id(tmp_path: Path) -> None:
    mod, repo, plan = prepare_publishable_guild_repo(tmp_path)
    transport = MockGuildDiscord(icon_patch_status=403)

    try:
        mod.publish_assets(
            repo,
            "asgard",
            plan["confirmation_id"],
            do_publish=True,
            kind="guild",
            environ={"ASGARD_MANAGE_GUILD_TOKEN": "A" * 60, "ASGARD_GUILD_ID": "1503058365335736549"},
            transport=transport,
        )
    except mod.PublishError as exc:
        assert "partial state" in str(exc)
        assert "1503058365335736549" not in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected PublishError")

    receipts = sorted((repo / "docs/runbooks/discord-identity-assets").glob("*partial-failure.json"))
    payload = yaml.safe_load(receipts[-1].read_text())
    assert "1503058365335736549" not in receipts[-1].read_text()
    assert payload["partial_failure"]["changed_surfaces"] == []
    assert payload["partial_failure"]["failed_surface"] == "icon"
