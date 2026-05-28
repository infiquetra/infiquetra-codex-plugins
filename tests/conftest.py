"""Shared pytest fixtures."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Mock subprocess.run for runner command execution."""
    mock = MagicMock()
    mock.return_value.returncode = 0
    mock.return_value.stdout = "Success"
    mock.return_value.stderr = ""
    monkeypatch.setattr("subprocess.run", mock)
    return mock
