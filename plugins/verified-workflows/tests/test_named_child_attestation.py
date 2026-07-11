from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import dispatch_receipt as facade  # noqa: E402
import named_child_attestation as attestation  # noqa: E402


def test_facade_preserves_named_child_join_api() -> None:
    assert facade.join_subagent_receipt is attestation.join_subagent_receipt


def test_named_child_attestation_remains_bounded() -> None:
    assert len(Path(attestation.__file__).read_text(encoding="utf-8").splitlines()) < 500
