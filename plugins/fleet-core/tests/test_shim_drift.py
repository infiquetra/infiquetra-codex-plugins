"""Drift guard: every vendored fleet_commons_shim.py must be byte-identical to the canonical.

Consumer plugins vendor a copy of the resolution shim into their own scripts/ (unifi vendors
into each skill's scripts/). This test compares every vendored copy against the canonical
plugins/fleet-core/scripts/fleet_commons_shim.py, byte-for-byte. A drifted copy fails here
rather than resolving fleet-core differently at run time in one plugin.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CANONICAL = _REPO_ROOT / "plugins" / "fleet-core" / "scripts" / "fleet_commons_shim.py"

# The exact set of expected vendored copies. Kept explicit (not globbed) so that a *missing*
# vendored copy also fails, not just a drifted one.
_EXPECTED_VENDORED = (
    "plugins/saga/scripts/fleet_commons_shim.py",
    "plugins/team-execution/scripts/fleet_commons_shim.py",
    "plugins/verified-workflows/scripts/fleet_commons_shim.py",
    "plugins/mission-control/scripts/fleet_commons_shim.py",
    "plugins/unifi/skills/unifi-network/scripts/fleet_commons_shim.py",
    "plugins/unifi/skills/unifi-protect/scripts/fleet_commons_shim.py",
)


def test_canonical_shim_exists() -> None:
    assert _CANONICAL.is_file(), f"canonical shim missing at {_CANONICAL}"


def test_every_expected_vendored_copy_is_byte_identical() -> None:
    canonical_bytes = _CANONICAL.read_bytes()
    for rel in _EXPECTED_VENDORED:
        copy = _REPO_ROOT / rel
        assert copy.is_file(), f"expected vendored shim missing: {rel}"
        assert copy.read_bytes() == canonical_bytes, (
            f"vendored shim drifted from canonical: {rel} "
            "(re-copy plugins/fleet-core/scripts/fleet_commons_shim.py)"
        )


def test_no_unexpected_vendored_copies() -> None:
    """Any fleet_commons_shim.py in the tree must be the canonical or a registered copy."""
    known = {_CANONICAL.resolve()} | {
        (_REPO_ROOT / rel).resolve() for rel in _EXPECTED_VENDORED
    }
    found = {
        p.resolve()
        for p in (_REPO_ROOT / "plugins").rglob("fleet_commons_shim.py")
    }
    unexpected = found - known
    assert not unexpected, f"unregistered vendored shim copies: {sorted(map(str, unexpected))}"
