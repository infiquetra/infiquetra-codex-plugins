from __future__ import annotations

from pathlib import Path

from helpers import load_module, prepare_publishable_guild_repo, prepare_publishable_repo
from test_discord_client import MockDiscord


def test_token_resolver_rejects_missing_empty_whitespace_and_bad_shape() -> None:
    mod = load_module()
    cases = [
        {},
        {"TOKEN": ""},
        {"TOKEN": " abc"},
        {"TOKEN": "abc\nxyz"},
        {"TOKEN": "not-a-token"},
        {"TOKEN": "Bot " + "A" * 60},
    ]

    for env in cases:
        try:
            mod.resolve_token("TOKEN", environ=env)
        except mod.PublishError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"expected rejection for {env!r}")


def test_dry_run_receipt_contains_no_token_material(tmp_path: Path) -> None:
    mod, repo, _plan = prepare_publishable_repo(tmp_path)
    secret = "A" * 60

    result = mod.publish_assets(
        repo,
        "mimir",
        do_publish=False,
        environ={"vault_discord_bot_token_mimir": secret},
    )

    receipt_md = repo / result["receipt"]["markdown"]
    receipt_json = repo / result["receipt"]["json"]
    assert secret not in receipt_md.read_text()
    assert secret not in receipt_json.read_text()
    assert "No live Discord mutation was performed" in receipt_md.read_text()


def test_publish_receipt_contains_no_token_material(tmp_path: Path) -> None:
    mod, repo, plan = prepare_publishable_repo(tmp_path)
    secret = "A" * 60

    result = mod.publish_assets(
        repo,
        "mimir",
        plan["confirmation_id"],
        do_publish=True,
        environ={"vault_discord_bot_token_mimir": secret},
        transport=MockDiscord(),
    )

    receipt_md = repo / result["receipt"]["markdown"]
    receipt_json = repo / result["receipt"]["json"]
    assert secret not in receipt_md.read_text()
    assert secret not in receipt_json.read_text()


def test_guild_id_resolver_rejects_missing_whitespace_and_bad_shape() -> None:
    mod = load_module()
    cases = [
        {},
        {"GUILD": ""},
        {"GUILD": " 1503058365335736549"},
        {"GUILD": "1503058365335736549\n"},
        {"GUILD": "not-a-snowflake"},
    ]

    for env in cases:
        try:
            mod.resolve_snowflake_env("GUILD", label="guild id", environ=env)
        except mod.PublishError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"expected rejection for {env!r}")


def test_guild_dry_run_receipt_contains_no_token_or_guild_id(tmp_path: Path) -> None:
    mod, repo, _plan = prepare_publishable_guild_repo(tmp_path)
    secret = "A" * 60
    guild_id = "1503058365335736549"

    result = mod.publish_assets(
        repo,
        "asgard",
        do_publish=False,
        kind="guild",
        environ={"ASGARD_MANAGE_GUILD_TOKEN": secret, "ASGARD_GUILD_ID": guild_id},
    )

    receipt_md = repo / result["receipt"]["markdown"]
    receipt_json = repo / result["receipt"]["json"]
    assert secret not in receipt_md.read_text()
    assert secret not in receipt_json.read_text()
    assert guild_id not in receipt_md.read_text()
    assert guild_id not in receipt_json.read_text()
