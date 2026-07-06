"""Tests for the U4 (#279) mission-control issue-write verbs — the mission-control half of the
certificate-gated /outcome board-sync loop: close / reopen / comment / label-add / label-remove.

Each verb is the sink for a reversibility-authorized op-kind and must be idempotent so the saga
consumer's bounded retry (and its separate idempotency ledger) is safe to re-drive. All REST calls
are patched at the sdlc_manager module level — no real ``gh`` ever fires.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sdlc_manager  # noqa: E402

ORG = sdlc_manager.ORG


def test_issue_close_patches_state_closed() -> None:
    with patch.object(sdlc_manager, "_rest_patch") as m:
        sdlc_manager.issue_close("saga", 42, fmt="json")
    m.assert_called_once_with(f"repos/{ORG}/saga/issues/42", {"state": "closed"})


def test_issue_reopen_patches_state_open() -> None:
    with patch.object(sdlc_manager, "_rest_patch") as m:
        sdlc_manager.issue_reopen("saga", 42, fmt="json")
    m.assert_called_once_with(f"repos/{ORG}/saga/issues/42", {"state": "open"})


def test_issue_comment_posts_body() -> None:
    with patch.object(sdlc_manager, "_rest_post", return_value={"id": 7}) as m:
        sdlc_manager.issue_comment("saga", 42, "progress", fmt="json")
    m.assert_called_once_with(f"repos/{ORG}/saga/issues/42/comments", {"body": "progress"})


def test_issue_label_add_posts_label_list() -> None:
    with patch.object(sdlc_manager, "_rest_post", return_value=[]) as m:
        sdlc_manager.issue_label_add("saga", 42, "blocked", fmt="json")
    m.assert_called_once_with(f"repos/{ORG}/saga/issues/42/labels", {"labels": ["blocked"]})


def test_issue_label_remove_url_encodes_label() -> None:
    """A label with a space must be percent-encoded into the DELETE path (never a raw space)."""
    with patch.object(sdlc_manager, "_rest_delete") as m:
        sdlc_manager.issue_label_remove("saga", 42, "good first issue", fmt="json")
    called_path = m.call_args[0][0]
    assert called_path == f"repos/{ORG}/saga/issues/42/labels/good%20first%20issue"
    assert " " not in called_path


def test_issue_label_remove_treats_404_as_idempotent_success() -> None:
    """A 404 (label already absent) is swallowed as an idempotent no-op, not re-raised."""

    def _raise_404(path: str) -> Any:
        raise sdlc_manager.ApiNotFoundError("not found", status_code=404)

    with patch.object(sdlc_manager, "_rest_delete", side_effect=_raise_404):
        # Must NOT raise — the consumer's retry would otherwise treat a settled removal as a failure.
        sdlc_manager.issue_label_remove("saga", 42, "blocked", fmt="json")


def test_issue_label_remove_propagates_non_404() -> None:
    """A non-404 error (e.g. auth) propagates so the consumer's fail-loud retry path engages."""

    def _raise_auth(path: str) -> Any:
        raise sdlc_manager.ApiAuthError("forbidden", status_code=403)

    with patch.object(sdlc_manager, "_rest_delete", side_effect=_raise_auth):
        try:
            sdlc_manager.issue_label_remove("saga", 42, "blocked", fmt="json")
        except sdlc_manager.ApiAuthError:
            return
    raise AssertionError("issue_label_remove must propagate a non-404 error")


def test_rest_delete_returns_empty_on_no_content() -> None:
    """A 204 No Content (empty body) must not blow up json.loads."""
    with patch.object(sdlc_manager, "_gh", return_value="") as m:
        result = sdlc_manager._rest_delete("repos/x/y/issues/1/labels/z")
    assert result == ""
    m.assert_called_once()
