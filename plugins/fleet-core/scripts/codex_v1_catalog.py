#!/usr/bin/env python3
"""Generate and install a temporary MultiAgent V1 Codex model catalog.

The complete live catalog is preserved. Only the allowlisted Sol and Terra
``multi_agent_version`` fields are changed to ``v1``.
"""

from __future__ import annotations

import argparse
import codecs
import copy
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

COMMONS_DIR = Path(__file__).resolve().parent / "fleet_commons"
if str(COMMONS_DIR) not in sys.path:
    sys.path.insert(0, str(COMMONS_DIR))

import codex_model_catalog as catalog  # noqa: E402

TARGET_MODELS = ("gpt-5.6-sol", "gpt-5.6-terra")
CATALOG_RELATIVE_PATH = Path("model-catalogs") / "infiquetra-v1.json"
BACKUP_SUFFIX = ".infiquetra-v1.bak"
TABLE_HEADER_RE = re.compile(r"^\s*\[([^]]+)]\s*(?:#.*)?$")
ROOT_KEY_RE = re.compile(r"^\s*model_catalog_json\s*=")
FEATURE_KEY_RE = {
    "multi_agent": re.compile(r"^\s*multi_agent\s*="),
    "multi_agent_v2": re.compile(r"^\s*multi_agent_v2\s*="),
}


class V1CatalogError(RuntimeError):
    """Raised when catalog transformation or installation cannot be proved safe."""


@dataclass(frozen=True, slots=True)
class RenderedCatalog:
    source: str
    source_sha256: str
    rendered_sha256: str
    payload: dict[str, Any]
    raw_bytes: bytes
    changed_models: tuple[str, ...]
    ultra_warning: bool


def _models(payload: Any) -> list[dict[str, Any]]:
    rows = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows:
        raise V1CatalogError("model catalog must be an object with a non-empty models list")
    if not all(isinstance(row, dict) for row in rows):
        raise V1CatalogError("every model catalog row must be an object")
    return rows


def _parse_source(raw_bytes: bytes, source: str) -> dict[str, Any]:
    if raw_bytes.startswith(codecs.BOM_UTF8):
        raise V1CatalogError(f"{source} model catalog must be UTF-8 without BOM")
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise V1CatalogError(f"{source} model catalog is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise V1CatalogError("model catalog root must be an object")
    try:
        catalog.normalize_catalog(payload, source="fixture", input_bytes=raw_bytes)
    except catalog.CatalogError as exc:
        raise V1CatalogError(str(exc)) from exc
    return payload


def transform_catalog(raw_bytes: bytes, *, source: str) -> RenderedCatalog:
    """Return a canonical full catalog with only the two V1 selectors changed."""
    original = _parse_source(raw_bytes, source)
    transformed = copy.deepcopy(original)
    rows = _models(transformed)
    found: dict[str, dict[str, Any]] = {}
    changed: list[str] = []
    for row in rows:
        slug = row.get("slug")
        if slug not in TARGET_MODELS:
            continue
        if slug in found:
            raise V1CatalogError(f"model catalog repeats target model {slug!r}")
        version = row.get("multi_agent_version")
        if version not in {"v1", "v2"}:
            raise V1CatalogError(
                f"target model {slug!r} has unsupported multi_agent_version {version!r}"
            )
        found[slug] = row
        if version != "v1":
            row["multi_agent_version"] = "v1"
            changed.append(slug)
    missing = [slug for slug in TARGET_MODELS if slug not in found]
    if missing:
        raise V1CatalogError(f"model catalog is missing target models: {', '.join(missing)}")

    rendered = (json.dumps(transformed, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if rendered.startswith(codecs.BOM_UTF8):
        raise AssertionError("UTF-8 renderer unexpectedly emitted a BOM")
    ultra_warning = any(
        any(level.get("effort") == "ultra" for level in row.get("supported_reasoning_levels", []))
        for row in found.values()
    )
    return RenderedCatalog(
        source=source,
        source_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        rendered_sha256=hashlib.sha256(rendered).hexdigest(),
        payload=transformed,
        raw_bytes=rendered,
        changed_models=tuple(changed),
        ultra_warning=ultra_warning,
    )


def _cache_catalog(raw_bytes: bytes) -> bytes:
    payload = _parse_source(raw_bytes, "cached")
    return (json.dumps({"models": _models(payload)}, ensure_ascii=False) + "\n").encode("utf-8")


def read_source(
    source_json: Path | None = None, *, codex_home: Path | None = None
) -> tuple[str, bytes]:
    if source_json is not None:
        try:
            return "file", source_json.read_bytes()
        except OSError as exc:
            raise V1CatalogError(f"could not read source catalog: {source_json}") from exc
    home = _codex_home(codex_home)
    cache_path = home / "models_cache.json"
    cache_error: Exception | None = None
    if cache_path.is_file():
        try:
            return "cache", _cache_catalog(cache_path.read_bytes())
        except (OSError, V1CatalogError) as exc:
            cache_error = exc
    try:
        document = catalog.read_bundled_catalog_document()
        return document.source, document.raw_bytes
    except catalog.CatalogError as exc:
        detail = f"cache: {cache_error}; " if cache_error is not None else ""
        raise V1CatalogError(detail + str(exc)) from exc


def render_live_catalog(
    source_json: Path | None = None, *, codex_home: Path | None = None
) -> RenderedCatalog:
    source, raw_bytes = read_source(source_json, codex_home=codex_home)
    return transform_catalog(raw_bytes, source=source)


def _atomic_write(path: Path, content: bytes, *, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            temporary.unlink(missing_ok=True)
        finally:
            raise


def write_catalog(path: Path, rendered: RenderedCatalog) -> None:
    _atomic_write(path, rendered.raw_bytes, mode=0o600)


def _table_name(line: str) -> str | None:
    match = TABLE_HEADER_RE.match(line)
    return match.group(1).strip() if match else None


def _remove_v2_settings_table(lines: list[str]) -> list[str]:
    result: list[str] = []
    skipping = False
    for line in lines:
        table = _table_name(line)
        if table is not None:
            skipping = table == "features.multi_agent_v2"
        if not skipping:
            result.append(line)
    return result


def _replace_root_catalog_key(lines: list[str], catalog_path: Path) -> list[str]:
    value = f"model_catalog_json = {json.dumps(str(catalog_path))}\n"
    first_table = next(
        (index for index, line in enumerate(lines) if _table_name(line) is not None), len(lines)
    )
    indexes = [index for index, line in enumerate(lines[:first_table]) if ROOT_KEY_RE.match(line)]
    if len(indexes) > 1:
        raise V1CatalogError("config contains duplicate top-level model_catalog_json keys")
    if indexes:
        lines[indexes[0]] = value
        return lines
    prefix = [] if first_table == 0 or not lines[:first_table] else ["\n"]
    lines[first_table:first_table] = [value, *prefix]
    return lines


def _replace_features(lines: list[str]) -> list[str]:
    if any(re.match(r"^\s*features\s*=\s*\{", line) for line in lines):
        raise V1CatalogError("inline top-level features tables are not supported; use [features]")
    table_indexes = [index for index, line in enumerate(lines) if _table_name(line) == "features"]
    if len(table_indexes) > 1:
        raise V1CatalogError("config contains duplicate [features] tables")
    if not table_indexes:
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.extend(["[features]\n", "multi_agent = true\n", "multi_agent_v2 = false\n"])
        return lines

    start = table_indexes[0]
    end = next(
        (index for index in range(start + 1, len(lines)) if _table_name(lines[index]) is not None),
        len(lines),
    )
    section = lines[start + 1 : end]
    for key, value in (("multi_agent", "true"), ("multi_agent_v2", "false")):
        indexes = [index for index, line in enumerate(section) if FEATURE_KEY_RE[key].match(line)]
        if len(indexes) > 1:
            raise V1CatalogError(f"config contains duplicate features.{key} keys")
        replacement = f"{key} = {value}\n"
        if indexes:
            section[indexes[0]] = replacement
        else:
            section.append(replacement)
    lines[start + 1 : end] = section
    return lines


def render_config(config_bytes: bytes, catalog_path: Path) -> bytes:
    if config_bytes.startswith(codecs.BOM_UTF8):
        raise V1CatalogError("Codex config must be UTF-8 without BOM")
    try:
        text = config_bytes.decode("utf-8")
        tomllib.loads(text or "")
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise V1CatalogError("Codex config is not valid UTF-8 TOML") from exc

    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith(("\n", "\r")):
        lines[-1] += "\n"
    lines = _remove_v2_settings_table(lines)
    lines = _replace_root_catalog_key(lines, catalog_path.resolve())
    lines = _replace_features(lines)
    rendered = "".join(lines).encode("utf-8")
    try:
        parsed = tomllib.loads(rendered.decode("utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise V1CatalogError("generated Codex config is invalid TOML") from exc
    features = parsed.get("features")
    if not isinstance(features, dict):
        raise V1CatalogError("generated Codex config is missing [features]")
    if features.get("multi_agent") is not True or features.get("multi_agent_v2") is not False:
        raise V1CatalogError("generated Codex config does not select MultiAgent V1")
    if parsed.get("model_catalog_json") != str(catalog_path.resolve()):
        raise V1CatalogError("generated Codex config does not select the V1 catalog")
    return rendered


def install_config(config_path: Path, catalog_path: Path) -> Path | None:
    try:
        original = config_path.read_bytes() if config_path.exists() else b""
    except OSError as exc:
        raise V1CatalogError(f"could not read Codex config: {config_path}") from exc
    rendered = render_config(original, catalog_path)
    backup = config_path.with_name(config_path.name + BACKUP_SUFFIX)
    if original and not backup.exists():
        original_mode = stat.S_IMODE(config_path.stat().st_mode)
        _atomic_write(backup, original, mode=original_mode)
    mode = stat.S_IMODE(config_path.stat().st_mode) if config_path.exists() else 0o600
    _atomic_write(config_path, rendered, mode=mode)
    return backup if original else None


def rollback_config(config_path: Path) -> Path:
    backup = config_path.with_name(config_path.name + BACKUP_SUFFIX)
    try:
        original = backup.read_bytes()
    except OSError as exc:
        raise V1CatalogError(f"V1 config backup is unavailable: {backup}") from exc
    if original.startswith(codecs.BOM_UTF8):
        raise V1CatalogError("V1 config backup must be UTF-8 without BOM")
    try:
        tomllib.loads(original.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise V1CatalogError("V1 config backup is not valid UTF-8 TOML") from exc
    mode = stat.S_IMODE(config_path.stat().st_mode) if config_path.exists() else 0o600
    _atomic_write(config_path, original, mode=mode)
    return backup


def validate_installed(catalog_path: Path, config_path: Path) -> dict[str, Any]:
    try:
        raw_catalog = catalog_path.read_bytes()
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise V1CatalogError("installed V1 catalog or Codex config could not be read") from exc
    payload = _parse_source(raw_catalog, "installed")
    versions = {
        row.get("slug"): row.get("multi_agent_version")
        for row in _models(payload)
        if row.get("slug") in TARGET_MODELS
    }
    if versions != {slug: "v1" for slug in TARGET_MODELS}:
        raise V1CatalogError("installed catalog does not select V1 for both target models")
    features = config.get("features")
    if not isinstance(features, dict):
        raise V1CatalogError("Codex config is missing [features]")
    if features.get("multi_agent") is not True or features.get("multi_agent_v2") is not False:
        raise V1CatalogError("Codex config does not enable V1 and disable V2")
    if config.get("model_catalog_json") != str(catalog_path.resolve()):
        raise V1CatalogError("Codex config does not point at the installed V1 catalog")
    return {
        "catalog_path": str(catalog_path.resolve()),
        "config_path": str(config_path.resolve()),
        "catalog_sha256": hashlib.sha256(raw_catalog).hexdigest(),
        "target_versions": versions,
        "status": "valid",
    }


def _codex_home(value: Path | None) -> Path:
    if value is not None:
        return value.expanduser().resolve()
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()


def _paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    home = _codex_home(args.codex_home)
    catalog_path = (args.output or home / CATALOG_RELATIVE_PATH).expanduser().resolve()
    config_path = (args.config or home / "config.toml").expanduser().resolve()
    return home, catalog_path, config_path


def _receipt(rendered: RenderedCatalog, catalog_path: Path) -> dict[str, Any]:
    return {
        "catalog_path": str(catalog_path),
        "changed_models": list(rendered.changed_models),
        "rendered_sha256": rendered.rendered_sha256,
        "source": rendered.source,
        "source_sha256": rendered.source_sha256,
        "target_versions": {slug: "v1" for slug in TARGET_MODELS},
        "ultra_status": "unverified-under-v1" if rendered.ultra_warning else "not-advertised",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path, help="override CODEX_HOME")
    parser.add_argument("--output", type=Path, help="catalog output path")
    parser.add_argument("--config", type=Path, help="Codex config path")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("render", "install"):
        command = subparsers.add_parser(name)
        command.add_argument("--source-json", type=Path, help="use a saved full catalog")
    subparsers.add_parser("check")
    subparsers.add_parser("rollback")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    home, catalog_path, config_path = _paths(args)
    try:
        if args.command == "check":
            print(json.dumps(validate_installed(catalog_path, config_path), indent=2, sort_keys=True))
            return 0
        if args.command == "rollback":
            backup = rollback_config(config_path)
            print(
                json.dumps(
                    {
                        "backup_path": str(backup),
                        "config_path": str(config_path),
                        "restart_required": True,
                        "status": "rolled-back",
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        rendered = render_live_catalog(args.source_json, codex_home=home)
        write_catalog(catalog_path, rendered)
        receipt = _receipt(rendered, catalog_path)
        if args.command == "install":
            backup = install_config(config_path, catalog_path)
            receipt.update(validate_installed(catalog_path, config_path))
            receipt["backup_path"] = str(backup) if backup is not None else None
            receipt["restart_required"] = True
        else:
            receipt["status"] = "rendered"
        print(json.dumps(receipt, indent=2, sort_keys=True))
        if rendered.ultra_warning:
            print(
                "WARNING: Ultra automatic delegation is unverified while Sol/Terra are forced to V1.",
                file=sys.stderr,
            )
        return 0
    except (V1CatalogError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
