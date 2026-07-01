from __future__ import annotations

from pathlib import Path

import yaml

from helpers import prepare_publishable_repo


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
