from __future__ import annotations

import json
from pathlib import Path

from helpers import prepare_publishable_repo


def test_verify_receipt_reads_required_fields(tmp_path: Path) -> None:
    mod, repo, _plan = prepare_publishable_repo(tmp_path)
    result = mod.publish_assets(repo, "mimir", do_publish=False)

    verification = mod.verify_receipt(repo, Path(result["receipt"]["json"]))

    assert verification["valid"] is True
    assert verification["missing"] == []
    assert verification["data"]["target_repo"] == repo.name
    assert str(tmp_path) not in json.dumps(verification["data"])
    assert "target_repo_git" in verification["data"]


def test_verify_receipt_rejects_missing_schema_fields(tmp_path: Path) -> None:
    mod, repo, _plan = prepare_publishable_repo(tmp_path)
    path = repo / "docs/runbooks/discord-identity-assets/bad.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "mode": "publish",
                "target_id": "mimir",
                "local_assets": {},
                "publish_plan": {},
            }
        ),
        encoding="utf-8",
    )

    verification = mod.verify_receipt(repo, path)

    assert verification["valid"] is False
    assert "target_repo" in verification["missing"]
    assert "remote.avatar.hash" in verification["missing"]


def test_publish_writes_secret_safe_runbook_checklist(tmp_path: Path) -> None:
    mod, repo, _plan = prepare_publishable_repo(tmp_path)
    secret = "A" * 60

    result = mod.publish_assets(
        repo,
        "mimir",
        do_publish=False,
        environ={"vault_discord_bot_token_mimir": secret},
    )

    runbook = repo / result["runbook"]
    text = runbook.read_text(encoding="utf-8")
    assert secret not in text
    assert "plugins/discord-identity-assets/scripts" not in text
    assert "SCRIPT=<path-to-installed-discord_identity_assets.py>" in text
    assert "vault_discord_bot_token_mimir" in text
    assert "Does not create Discord applications" in text
    assert "Receipt records non-empty Discord readback identifiers" in text
