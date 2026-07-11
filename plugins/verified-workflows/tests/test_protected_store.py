from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import dispatch_receipt as facade  # noqa: E402
import protected_store as store  # noqa: E402


def test_facade_preserves_protected_store_api() -> None:
    assert facade.persist_protected_record is store.persist_protected_record
    assert facade.load_protected_record is store.load_protected_record
    assert facade.load_raw_pair is store.load_raw_pair
    assert facade.DispatchReceiptError is store.DispatchReceiptError


def test_protected_store_remains_bounded() -> None:
    assert len(Path(store.__file__).read_text(encoding="utf-8").splitlines()) < 750
