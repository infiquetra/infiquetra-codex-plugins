#!/usr/bin/env python3
"""Deterministic Discord visual identity asset workflow.

Codex owns image generation. This script validates manifests, normalizes files,
builds publish plans, publishes with explicit confirmation, verifies readback,
and writes redacted receipts.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


DISCORD_API_BASE = "https://discord.com/api/v10"
MANIFEST_REL = Path("identity/discord-identity-assets.yml")
SCHEMA_VERSION = 1
CURRENT_MANIFEST_SCHEMA_VERSION = 2
SUPPORTED_MANIFEST_SCHEMA_VERSIONS = {1, 2}
AVATAR_SIZE = (512, 512)
BANNER_SIZE = (960, 540)
GUILD_ICON_SIZE = (512, 512)
GUILD_BANNER_SIZE = (960, 540)
MAX_IMAGE_BYTES = 10 * 1024 * 1024
BOT_SURFACES = ("avatar", "app_icon", "banner")
GUILD_SURFACES = ("icon", "banner")
SECRET_VALUE_RE = re.compile(
    r"(?:Bot\s+)?[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{20,}"
)
TOKEN_RE = re.compile(
    r"(?:[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{20,}|"
    r"[A-Za-z0-9_-]{50,})"
)
ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SNOWFLAKE_RE = re.compile(r"^\d{17,20}$")


class DiscordIdentityError(ValueError):
    """Base error for deterministic workflow failures."""


class DependencyError(DiscordIdentityError):
    """A required optional dependency is unavailable."""


class ManifestError(DiscordIdentityError):
    """A manifest is missing or invalid."""


class PublishError(DiscordIdentityError):
    """Publishing or verification failed."""


class DiscordApiError(PublishError):
    """Discord returned a non-success HTTP status."""

    def __init__(self, method: str, path: str, status: int, detail: str = "") -> None:
        self.method = method
        self.path = path
        self.status = status
        message = f"Discord {method} {path} failed with status {status}"
        if detail:
            message = f"{message}: {detail}"
        super().__init__(message)


@dataclass(frozen=True)
class AssetInfo:
    path: str
    sha256: str
    width: int
    height: int
    bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "width": self.width,
            "height": self.height,
            "bytes": self.bytes,
        }


def _require_yaml() -> Any:
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised by CLI dependency checks
        raise DependencyError("PyYAML is required. Install with: uv add --dev PyYAML") from exc
    return yaml


def _require_pillow() -> tuple[Any, Any]:
    try:
        from PIL import Image, ImageOps  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised by CLI dependency checks
        raise DependencyError("Pillow is required. Install with: uv add --dev Pillow") from exc
    return Image, ImageOps


def _read_yaml(path: Path) -> dict[str, Any]:
    yaml = _require_yaml()
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestError(f"manifest not found: {path}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ManifestError(f"{path}: expected a YAML mapping")
    return data


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    yaml = _require_yaml()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _repo_path(repo: Path, rel: str | Path) -> Path:
    candidate = Path(rel)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ManifestError(f"path `{rel}` must be repo-relative")
    return repo / candidate


def _rel(repo: Path, path: Path) -> str:
    return path.resolve().relative_to(repo.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_hash(data: dict[str, Any]) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for key, item in value.items():
            out.extend(_walk_strings(key))
            out.extend(_walk_strings(item))
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(_walk_strings(item))
        return out
    return []


def _assert_no_secret_values(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for text in _walk_strings(data):
        if SECRET_VALUE_RE.search(text) or TOKEN_RE.fullmatch(text):
            errors.append("manifest appears to contain token material")
            break
    return errors


def manifest_path(repo: Path) -> Path:
    return repo / MANIFEST_REL


def load_manifest(repo: Path) -> dict[str, Any]:
    return _read_yaml(manifest_path(repo))


def target_by_id(manifest: dict[str, Any], target_id: str) -> dict[str, Any]:
    targets = manifest.get("targets")
    if not isinstance(targets, list):
        raise ManifestError("manifest field `targets` must be a list")
    for target in targets:
        if isinstance(target, dict) and target.get("id") == target_id:
            return target
    raise ManifestError(f"target `{target_id}` not found")


def guild_target_by_id(manifest: dict[str, Any], target_id: str) -> dict[str, Any]:
    targets = manifest.get("guild_targets")
    if not isinstance(targets, list):
        raise ManifestError("manifest field `guild_targets` must be a list")
    for target in targets:
        if isinstance(target, dict) and target.get("id") == target_id:
            return target
    raise ManifestError(f"guild target `{target_id}` not found")


def target_for_kind(manifest: dict[str, Any], target_id: str, kind: str) -> dict[str, Any]:
    if kind == "bot":
        return target_by_id(manifest, target_id)
    if kind == "guild":
        return guild_target_by_id(manifest, target_id)
    raise ManifestError("kind must be `bot` or `guild`")


def _team_profiles(repo: Path) -> list[dict[str, Any]]:
    path = repo / "deploy/team_profiles.yml"
    if not path.exists():
        return []
    payload = _read_yaml(path)
    profiles = payload.get("hermes_team_profiles", [])
    if not isinstance(profiles, list):
        raise ManifestError("deploy/team_profiles.yml field `hermes_team_profiles` must be a list")
    return [profile for profile in profiles if isinstance(profile, dict)]


def _existing_prompt_sources(repo: Path, profile: dict[str, Any]) -> list[str]:
    name = str(profile.get("name") or "")
    persona = str(profile.get("persona") or name)
    candidates = [
        "deploy/team_profiles.yml",
        f"profiles/{name}/SOUL.md" if name else "",
        f"profiles/{persona}/SOUL.md" if persona else "",
        "identity/README.md",
        "identity/SOUL.md",
        "docs/team/README.md",
        "docs/team/roster.md",
        "STRATEGY.md",
        "README.md",
    ]
    sources = []
    for rel in candidates:
        if rel and rel not in sources and (repo / rel).exists():
            sources.append(rel)
    return sources or ["deploy/team_profiles.yml"]


def discover_manifest(repo: Path, persona: str | None = None) -> dict[str, Any]:
    profiles = _team_profiles(repo)
    visible = [
        profile
        for profile in profiles
        if not profile.get("headless")
        and profile.get("discord_token_var")
        and profile.get("bot_user_id")
        and (persona is None or profile.get("persona") == persona)
    ]
    if not visible:
        raise ManifestError("no visible Discord-backed team profile found")

    targets = []
    for profile in visible:
        target_id = str(profile.get("persona") or profile.get("name"))
        bot_user_id = str(profile["bot_user_id"])
        sources = _existing_prompt_sources(repo, profile)
        targets.append(
            {
                "id": target_id,
                "display_name": str(target_id).replace("-", " ").title(),
                "persona": target_id,
                "profile": str(profile.get("name")),
                "prompt_sources": sources,
                "prompts": {
                    "avatar": "",
                    "banner": "",
                },
                "asset_paths": {
                    "originals": {
                        "avatar": f"assets/discord/originals/{target_id}-avatar.png",
                        "banner": f"assets/discord/originals/{target_id}-banner.png",
                    },
                    "finals": {
                        "avatar": f"assets/discord/avatars/{target_id}.png",
                        "app_icon": f"assets/discord/avatars/{target_id}.png",
                        "banner": f"assets/discord/banners/{target_id}.png",
                    },
                    "prompt_record": f"assets/discord/prompts/{target_id}.yml",
                },
                "discord": {
                    "application_id": "",
                    "application_id_candidate": bot_user_id,
                    "expected_bot_user_id": bot_user_id,
                    "allow_legacy_application_endpoint": True,
                },
                "token_env": str(profile["discord_token_var"]),
                "evidence": {
                    "receipt_dir": "docs/runbooks/discord-identity-assets",
                },
                "mode_defaults": {
                    "generate_only": True,
                },
                "missing_fields": [
                    "prompts.avatar",
                    "prompts.banner",
                    "discord.application_id",
                ],
            }
        )
    return {"schema_version": SCHEMA_VERSION, "targets": targets}


def _default_guild_prompt_sources(repo: Path) -> list[str]:
    candidates = [
        "identity/README.md",
        "identity/SOUL.md",
        "docs/team/README.md",
        "docs/team/roster.md",
        "STRATEGY.md",
        "README.md",
        "deploy/team_profiles.yml",
    ]
    sources = [rel for rel in candidates if (repo / rel).exists()]
    return sources or ["README.md"]


def scaffold_guild_manifest(
    repo: Path,
    *,
    target_id: str,
    display_name: str,
    expected_guild_name: str,
    guild_id_env: str,
    manage_guild_token_env: str,
    expected_actor_user_id: str = "",
    profile_banner_color: str = "",
    force: bool = False,
) -> dict[str, Any]:
    if manifest_path(repo).exists():
        manifest = load_manifest(repo)
    else:
        manifest = {"schema_version": CURRENT_MANIFEST_SCHEMA_VERSION, "targets": []}
    manifest["schema_version"] = CURRENT_MANIFEST_SCHEMA_VERSION
    targets = manifest.setdefault("guild_targets", [])
    if not isinstance(targets, list):
        raise ManifestError("manifest field `guild_targets` must be a list")
    if any(isinstance(target, dict) and target.get("id") == target_id for target in targets):
        if not force:
            raise ManifestError(f"guild target `{target_id}` already exists; pass --force to replace")
        targets[:] = [
            target
            for target in targets
            if not (isinstance(target, dict) and target.get("id") == target_id)
        ]

    target = {
        "id": target_id,
        "display_name": display_name,
        "prompt_sources": _default_guild_prompt_sources(repo),
        "prompts": {
            "icon": "",
            "banner": "",
        },
        "profile_banner_color": profile_banner_color,
        "asset_paths": {
            "originals": {
                "icon": f"assets/discord/guilds/{target_id}/originals/icon.png",
                "banner": f"assets/discord/guilds/{target_id}/originals/banner.png",
            },
            "finals": {
                "icon": f"assets/discord/guilds/{target_id}/icon.png",
                "banner": f"assets/discord/guilds/{target_id}/banner.png",
            },
            "prompt_record": f"assets/discord/guilds/{target_id}/prompts.yml",
        },
        "discord": {
            "expected_guild_name": expected_guild_name,
        },
        "guild_id_env": guild_id_env,
        "manage_guild_token_env": manage_guild_token_env,
        "expected_actor_user_id": expected_actor_user_id,
        "evidence": {
            "receipt_dir": "docs/runbooks/discord-identity-assets",
        },
        "mode_defaults": {
            "generate_only": True,
        },
        "missing_fields": [
            "prompts.icon",
            "prompts.banner",
        ],
    }
    targets.append(target)
    return manifest


def _get_nested(data: dict[str, Any], dotted: str) -> Any:
    current: Any = data
    for part in dotted.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _validate_required_fields(
    errors: list[str],
    target: dict[str, Any],
    label: str,
    fields: list[str],
) -> None:
    for field in fields:
        value = _get_nested(target, field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{label}: missing required field `{field}`")


def _validate_env_field(errors: list[str], target: dict[str, Any], label: str, field: str) -> None:
    value = _get_nested(target, field)
    if isinstance(value, str) and value:
        if not ENV_NAME_RE.match(value):
            errors.append(f"{label}: {field} must be an environment variable name")
        if SECRET_VALUE_RE.search(value) or TOKEN_RE.fullmatch(value):
            errors.append(f"{label}: {field} contains token material")


def _validate_repo_paths(
    errors: list[str],
    repo: Path,
    target: dict[str, Any],
    label: str,
    fields: list[str],
) -> None:
    for field in fields:
        value = _get_nested(target, field)
        if isinstance(value, str) and value:
            try:
                _repo_path(repo, value)
            except ManifestError as exc:
                errors.append(f"{label}: {exc}")


def _validate_bot_targets(
    repo: Path,
    manifest: dict[str, Any],
    mode: str,
    errors: list[str],
) -> None:
    targets = manifest.get("targets")
    if not isinstance(targets, list) or not targets:
        errors.append("targets must be a non-empty list")
        return

    discovered_by_persona = {
        str(profile.get("persona")): profile
        for profile in _team_profiles(repo)
        if profile.get("persona")
    }

    for idx, target in enumerate(targets):
        if not isinstance(target, dict):
            errors.append(f"targets[{idx}] must be a mapping")
            continue
        label = str(target.get("id") or f"targets[{idx}]")
        required_generate = [
            "id",
            "persona",
            "prompts.avatar",
            "prompts.banner",
            "asset_paths.originals.avatar",
            "asset_paths.originals.banner",
            "asset_paths.finals.avatar",
            "asset_paths.finals.app_icon",
            "asset_paths.finals.banner",
            "asset_paths.prompt_record",
            "evidence.receipt_dir",
        ]
        required_publish = [
            *required_generate,
            "discord.application_id",
            "discord.expected_bot_user_id",
            "token_env",
            "evidence.receipt_dir",
        ]
        _validate_required_fields(
            errors,
            target,
            label,
            required_publish if mode == "publish" else required_generate,
        )
        _validate_env_field(errors, target, label, "token_env")

        persona = str(target.get("persona") or "")
        discovered = discovered_by_persona.get(persona)
        expected_bot_user_id = _get_nested(target, "discord.expected_bot_user_id")
        if discovered and expected_bot_user_id:
            local_bot_user_id = str(discovered.get("bot_user_id"))
            if local_bot_user_id and str(expected_bot_user_id) != local_bot_user_id:
                errors.append(
                    f"{label}: manifest bot user id {expected_bot_user_id} conflicts with "
                    f"deploy/team_profiles.yml {local_bot_user_id}"
                )

        _validate_repo_paths(
            errors,
            repo,
            target,
            label,
            [
                "asset_paths.originals.avatar",
                "asset_paths.originals.banner",
                "asset_paths.finals.avatar",
                "asset_paths.finals.app_icon",
                "asset_paths.finals.banner",
                "asset_paths.prompt_record",
                "evidence.receipt_dir",
            ],
        )


def _validate_guild_targets(
    repo: Path,
    manifest: dict[str, Any],
    mode: str,
    errors: list[str],
) -> None:
    targets = manifest.get("guild_targets")
    if not isinstance(targets, list) or not targets:
        errors.append("guild_targets must be a non-empty list")
        return

    for idx, target in enumerate(targets):
        if not isinstance(target, dict):
            errors.append(f"guild_targets[{idx}] must be a mapping")
            continue
        label = str(target.get("id") or f"guild_targets[{idx}]")
        required_generate = [
            "id",
            "display_name",
            "prompts.icon",
            "prompts.banner",
            "asset_paths.originals.icon",
            "asset_paths.originals.banner",
            "asset_paths.finals.icon",
            "asset_paths.finals.banner",
            "asset_paths.prompt_record",
            "evidence.receipt_dir",
        ]
        required_publish = [
            *required_generate,
            "discord.expected_guild_name",
            "guild_id_env",
            "manage_guild_token_env",
        ]
        _validate_required_fields(
            errors,
            target,
            label,
            required_publish if mode == "publish" else required_generate,
        )
        _validate_env_field(errors, target, label, "guild_id_env")
        _validate_env_field(errors, target, label, "manage_guild_token_env")

        expected_actor = target.get("expected_actor_user_id")
        if isinstance(expected_actor, str) and expected_actor and not SNOWFLAKE_RE.match(expected_actor):
            errors.append(f"{label}: expected_actor_user_id must be a Discord snowflake")

        profile_color = target.get("profile_banner_color")
        if isinstance(profile_color, str) and profile_color:
            if not re.fullmatch(r"#[0-9A-Fa-f]{6}", profile_color):
                errors.append(f"{label}: profile_banner_color must be a hex color like #2F555A")

        _validate_repo_paths(
            errors,
            repo,
            target,
            label,
            [
                "asset_paths.originals.icon",
                "asset_paths.originals.banner",
                "asset_paths.finals.icon",
                "asset_paths.finals.banner",
                "asset_paths.prompt_record",
                "evidence.receipt_dir",
            ],
        )


def validate_manifest(repo: Path, mode: str = "generate", kind: str = "bot") -> list[str]:
    errors: list[str] = []
    try:
        manifest = load_manifest(repo)
    except DiscordIdentityError as exc:
        return [str(exc)]

    schema_version = manifest.get("schema_version")
    if schema_version not in SUPPORTED_MANIFEST_SCHEMA_VERSIONS:
        errors.append(
            f"schema_version must be one of {sorted(SUPPORTED_MANIFEST_SCHEMA_VERSIONS)}"
        )
    if kind == "guild" and schema_version != CURRENT_MANIFEST_SCHEMA_VERSION:
        errors.append(f"schema_version must be {CURRENT_MANIFEST_SCHEMA_VERSION} for guild targets")
    if manifest.get("guild_targets") and schema_version != CURRENT_MANIFEST_SCHEMA_VERSION:
        errors.append(f"schema_version must be {CURRENT_MANIFEST_SCHEMA_VERSION} when guild_targets exist")

    errors.extend(_assert_no_secret_values(manifest))
    if kind == "bot":
        _validate_bot_targets(repo, manifest, mode, errors)
    elif kind == "guild":
        _validate_guild_targets(repo, manifest, mode, errors)
    else:
        errors.append("kind must be `bot` or `guild`")
    return errors


def preview_plan(repo: Path, target_id: str, kind: str = "bot") -> dict[str, Any]:
    errors = validate_manifest(repo, mode="generate", kind=kind)
    if errors:
        raise ManifestError("; ".join(errors))
    manifest = load_manifest(repo)
    target = target_for_kind(manifest, target_id, kind)
    basis = {
        "kind": kind,
        "target_id": target_id,
        "manifest_sha256": sha256_file(manifest_path(repo)),
        "asset_paths": target["asset_paths"],
        "discord": target.get("discord", {}),
        "token_env": target.get("token_env") or target.get("manage_guild_token_env", ""),
    }
    if kind == "guild":
        return {
            "kind": kind,
            "target_id": target_id,
            "preview_id": _json_hash(basis)[:16],
            "surfaces": list(GUILD_SURFACES),
            "prompt_sources": target.get("prompt_sources", []),
            "prompts": target.get("prompts", {}),
            "asset_paths": target["asset_paths"],
            "discord": {
                "expected_guild_name": _get_nested(target, "discord.expected_guild_name") or "",
                "guild_id_env": target.get("guild_id_env", ""),
                "banner_feature_required": "BANNER",
            },
            "manage_guild_token_env": target.get("manage_guild_token_env", ""),
            "profile_banner_color": target.get("profile_banner_color", ""),
            "evidence": target.get("evidence", {}),
            "note": (
                "Preview only. Server Profile color is recorded metadata; "
                "image banner publish requires Discord guild BANNER support."
            ),
        }
    return {
        "kind": kind,
        "target_id": target_id,
        "preview_id": _json_hash(basis)[:16],
        "surfaces": list(BOT_SURFACES),
        "prompt_sources": target.get("prompt_sources", []),
        "prompts": target.get("prompts", {}),
        "asset_paths": target["asset_paths"],
        "discord": {
            "application_id": _get_nested(target, "discord.application_id") or "",
            "expected_bot_user_id": _get_nested(target, "discord.expected_bot_user_id") or "",
        },
        "token_env": target.get("token_env", ""),
        "evidence": target.get("evidence", {}),
        "note": "Preview only. A post-processing publish plan signs final asset hashes before live publish.",
    }


def _asset_info(repo: Path, path: Path) -> AssetInfo:
    Image, _ImageOps = _require_pillow()
    with Image.open(path) as img:
        width, height = img.size
    return AssetInfo(
        path=_rel(repo, path),
        sha256=sha256_file(path),
        width=width,
        height=height,
        bytes=path.stat().st_size,
    )


def _check_original(path: Path) -> None:
    if not path.exists():
        raise ManifestError(f"missing original image: {path}")
    if path.stat().st_size == 0:
        raise ManifestError(f"original image is empty: {path}")
    if path.stat().st_size > MAX_IMAGE_BYTES:
        raise ManifestError(f"original image exceeds {MAX_IMAGE_BYTES} bytes: {path}")
    Image, _ImageOps = _require_pillow()
    try:
        with Image.open(path) as img:
            img.verify()
    except Exception as exc:
        raise ManifestError(f"unreadable image: {path}") from exc


def _normalize_png(src: Path, dst: Path, size: tuple[int, int]) -> None:
    Image, ImageOps = _require_pillow()
    _check_original(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as img:
        converted = img.convert("RGBA")
        fitted = ImageOps.fit(converted, size, method=Image.Resampling.LANCZOS)
        fitted.save(dst, format="PNG", optimize=True)


def _prompt_consistency_from_record(repo: Path, target: dict[str, Any]) -> str:
    record_rel = _get_nested(target, "asset_paths.prompt_record")
    if not isinstance(record_rel, str) or not record_rel:
        return ""
    record_path = _repo_path(repo, record_rel)
    if not record_path.exists():
        return ""
    payload = _read_yaml(record_path)
    value = payload.get("prompt_consistency")
    if isinstance(value, str):
        return value
    return ""


def postprocess_assets(repo: Path, target_id: str, kind: str = "bot") -> dict[str, Any]:
    if kind == "guild":
        return postprocess_guild_assets(repo, target_id)
    errors = validate_manifest(repo, mode="generate", kind="bot")
    if errors:
        raise ManifestError("; ".join(errors))
    manifest = load_manifest(repo)
    target = target_by_id(manifest, target_id)
    originals = target.get("asset_paths", {}).get("originals", {})
    finals = target.get("asset_paths", {}).get("finals", {})
    avatar_original = _repo_path(repo, originals["avatar"])
    banner_original = _repo_path(repo, originals["banner"])
    avatar_final = _repo_path(repo, finals["avatar"])
    app_icon_final = _repo_path(repo, finals["app_icon"])
    banner_final = _repo_path(repo, finals["banner"])

    if avatar_final.resolve() == banner_final.resolve():
        raise ManifestError("avatar and banner final paths must not be the same")

    _normalize_png(avatar_original, avatar_final, AVATAR_SIZE)
    if app_icon_final.resolve() != avatar_final.resolve():
        _normalize_png(avatar_original, app_icon_final, AVATAR_SIZE)
    _normalize_png(banner_original, banner_final, BANNER_SIZE)

    infos = {
        "avatar": _asset_info(repo, avatar_final).to_dict(),
        "app_icon": _asset_info(repo, app_icon_final).to_dict(),
        "banner": _asset_info(repo, banner_final).to_dict(),
    }
    prompt_record_rel = target["asset_paths"]["prompt_record"]
    prompt_record_path = _repo_path(repo, prompt_record_rel)
    existing_consistency = _prompt_consistency_from_record(repo, target)
    prompt_record = {
        "schema_version": SCHEMA_VERSION,
        "kind": "bot",
        "target_id": target_id,
        "persona": target.get("persona", ""),
        "prompt_sources": target.get("prompt_sources", []),
        "prompts": target.get("prompts", {}),
        "prompt_consistency": existing_consistency or "pending",
        "assets": infos,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _write_yaml(prompt_record_path, prompt_record)
    receipt_plan = build_generate_receipt_plan(repo, target_id, infos, kind="bot")
    receipt = write_receipt(repo, target, "generate-only", receipt_plan)
    runbook = write_runbook(repo, target, plan=receipt_plan, last_receipt=receipt)
    return {
        "target_id": target_id,
        "assets": infos,
        "prompt_record": prompt_record_rel,
        "receipt": receipt,
        "runbook": runbook,
    }


def postprocess_guild_assets(repo: Path, target_id: str) -> dict[str, Any]:
    errors = validate_manifest(repo, mode="generate", kind="guild")
    if errors:
        raise ManifestError("; ".join(errors))
    manifest = load_manifest(repo)
    target = guild_target_by_id(manifest, target_id)
    originals = target.get("asset_paths", {}).get("originals", {})
    finals = target.get("asset_paths", {}).get("finals", {})
    icon_original = _repo_path(repo, originals["icon"])
    banner_original = _repo_path(repo, originals["banner"])
    icon_final = _repo_path(repo, finals["icon"])
    banner_final = _repo_path(repo, finals["banner"])

    if icon_final.resolve() == banner_final.resolve():
        raise ManifestError("guild icon and banner final paths must not be the same")

    _normalize_png(icon_original, icon_final, GUILD_ICON_SIZE)
    _normalize_png(banner_original, banner_final, GUILD_BANNER_SIZE)

    infos = {
        "icon": _asset_info(repo, icon_final).to_dict(),
        "banner": _asset_info(repo, banner_final).to_dict(),
    }
    prompt_record_rel = target["asset_paths"]["prompt_record"]
    prompt_record_path = _repo_path(repo, prompt_record_rel)
    existing_consistency = _prompt_consistency_from_record(repo, target)
    prompt_record = {
        "schema_version": SCHEMA_VERSION,
        "kind": "guild",
        "target_id": target_id,
        "prompt_sources": target.get("prompt_sources", []),
        "prompts": target.get("prompts", {}),
        "prompt_consistency": existing_consistency or "pending",
        "profile_banner_color": target.get("profile_banner_color", ""),
        "assets": infos,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _write_yaml(prompt_record_path, prompt_record)
    receipt_plan = build_generate_receipt_plan(repo, target_id, infos, kind="guild")
    receipt = write_receipt(repo, target, "generate-only", receipt_plan)
    runbook = write_runbook(repo, target, plan=receipt_plan, last_receipt=receipt)
    return {
        "kind": "guild",
        "target_id": target_id,
        "assets": infos,
        "prompt_record": prompt_record_rel,
        "receipt": receipt,
        "runbook": runbook,
    }


def build_generate_receipt_plan(
    repo: Path,
    target_id: str,
    assets: dict[str, dict[str, Any]],
    kind: str = "bot",
) -> dict[str, Any]:
    manifest = load_manifest(repo)
    target = target_for_kind(manifest, target_id, kind)
    basis = {
        "kind": kind,
        "target_id": target_id,
        "manifest_sha256": sha256_file(manifest_path(repo)),
        "assets": {surface: info["sha256"] for surface, info in assets.items()},
        "prompts": target.get("prompts", {}),
    }
    if kind == "guild":
        return {
            "kind": kind,
            "target_id": target_id,
            "confirmation_id": _json_hash(basis)[:16],
            "surfaces": list(GUILD_SURFACES),
            "manifest_sha256": basis["manifest_sha256"],
            "assets": assets,
            "discord": {
                "expected_guild_name": _get_nested(target, "discord.expected_guild_name") or "",
                "guild_id_env": target.get("guild_id_env", ""),
                "banner_feature_required": "BANNER",
            },
            "manage_guild_token_env": target.get("manage_guild_token_env", ""),
            "profile_banner_color": target.get("profile_banner_color", ""),
        }
    return {
        "kind": kind,
        "target_id": target_id,
        "confirmation_id": _json_hash(basis)[:16],
        "surfaces": list(BOT_SURFACES),
        "manifest_sha256": basis["manifest_sha256"],
        "assets": assets,
        "discord": {
            "application_id": _get_nested(target, "discord.application_id") or "",
            "expected_bot_user_id": _get_nested(target, "discord.expected_bot_user_id") or "",
        },
        "token_env": target.get("token_env", ""),
    }


def build_publish_plan(repo: Path, target_id: str, kind: str = "bot") -> dict[str, Any]:
    errors = validate_manifest(repo, mode="publish", kind=kind)
    if errors:
        raise ManifestError("; ".join(errors))
    manifest_file = manifest_path(repo)
    manifest = load_manifest(repo)
    target = target_for_kind(manifest, target_id, kind)
    finals = target["asset_paths"]["finals"]
    assets = {
        surface: _asset_info(repo, _repo_path(repo, path)).to_dict()
        for surface, path in finals.items()
    }
    basis = {
        "kind": kind,
        "target_id": target_id,
        "manifest_sha256": sha256_file(manifest_file),
        "assets": {surface: info["sha256"] for surface, info in assets.items()},
        "discord": target.get("discord", {}),
    }
    confirmation_id = _json_hash(basis)[:16]
    if kind == "guild":
        return {
            "kind": kind,
            "target_id": target_id,
            "confirmation_id": confirmation_id,
            "surfaces": list(GUILD_SURFACES),
            "manifest_sha256": basis["manifest_sha256"],
            "assets": assets,
            "discord": {
                "expected_guild_name": target["discord"]["expected_guild_name"],
                "guild_id_env": target["guild_id_env"],
                "banner_feature_required": "BANNER",
            },
            "manage_guild_token_env": target["manage_guild_token_env"],
            "expected_actor_user_id": target.get("expected_actor_user_id", ""),
            "profile_banner_color": target.get("profile_banner_color", ""),
        }
    return {
        "kind": kind,
        "target_id": target_id,
        "confirmation_id": confirmation_id,
        "surfaces": list(BOT_SURFACES),
        "manifest_sha256": basis["manifest_sha256"],
        "assets": assets,
        "discord": {
            "application_id": target["discord"]["application_id"],
            "expected_bot_user_id": target["discord"]["expected_bot_user_id"],
        },
        "token_env": target["token_env"],
    }


def resolve_token(env_name: str, environ: dict[str, str] | None = None) -> str:
    environ = environ if environ is not None else os.environ
    if not ENV_NAME_RE.match(env_name):
        raise PublishError("token_env must be an environment variable name")
    raw = environ.get(env_name)
    if raw is None:
        raise PublishError(f"required token environment variable is absent: {env_name}")
    if raw != raw.strip():
        raise PublishError(f"{env_name} contains leading or trailing whitespace")
    if "\n" in raw or "\r" in raw:
        raise PublishError(f"{env_name} contains multiline token material")
    if not raw:
        raise PublishError(f"{env_name} is empty")
    if raw.startswith("Bot "):
        raise PublishError(f"{env_name} must contain only the token, not an Authorization header")
    if not TOKEN_RE.fullmatch(raw):
        raise PublishError(f"{env_name} does not look like a Discord bot token")
    return raw


def resolve_snowflake_env(
    env_name: str,
    *,
    label: str,
    environ: dict[str, str] | None = None,
) -> str:
    environ = environ if environ is not None else os.environ
    if not ENV_NAME_RE.match(env_name):
        raise PublishError(f"{label} environment variable name is invalid")
    raw = environ.get(env_name)
    if raw is None:
        raise PublishError(f"required {label} environment variable is absent: {env_name}")
    if raw != raw.strip():
        raise PublishError(f"{env_name} contains leading or trailing whitespace")
    if "\n" in raw or "\r" in raw:
        raise PublishError(f"{env_name} contains multiline material")
    if not SNOWFLAKE_RE.match(raw):
        raise PublishError(f"{env_name} must contain a Discord snowflake")
    return raw


def _data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


Transport = Callable[[str, str, dict[str, str], bytes | None], tuple[int, dict[str, Any]]]


class DiscordClient:
    def __init__(self, token: str, transport: Transport | None = None) -> None:
        self._token = token
        self._transport = transport or self._urllib_transport

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bot {self._token}",
            "Content-Type": "application/json",
            "User-Agent": "InfiquetraDiscordIdentityAssets/0.1",
        }

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        status, data = self._transport(method, path, self._headers(), body)
        if not 200 <= status < 300:
            raise DiscordApiError(method, path, status)
        return data

    @staticmethod
    def _urllib_transport(
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes | None,
    ) -> tuple[int, dict[str, Any]]:
        request = urllib.request.Request(
            DISCORD_API_BASE + path,
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
                payload = response.read().decode("utf-8") or "{}"
                return response.status, json.loads(payload)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise DiscordApiError(method, path, exc.code, detail) from exc
        except urllib.error.URLError as exc:
            raise PublishError(f"Discord {method} {path} failed: {exc}") from exc

    def get_user(self) -> dict[str, Any]:
        return self._request("GET", "/users/@me")

    def patch_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PATCH", "/users/@me", payload)

    def get_current_application(self) -> dict[str, Any]:
        return self._request("GET", "/applications/@me")

    def patch_current_application(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PATCH", "/applications/@me", payload)

    def patch_application(self, application_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PATCH", f"/applications/{application_id}", payload)

    def get_guild(self, guild_id: str) -> dict[str, Any]:
        return self._request("GET", f"/guilds/{guild_id}")

    def patch_guild(self, guild_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PATCH", f"/guilds/{guild_id}", payload)


def _ensure_prompt_gate(repo: Path, target: dict[str, Any]) -> None:
    state = _prompt_consistency_from_record(repo, target)
    if state != "passed":
        raise PublishError("prompt consistency must be recorded as `passed` before publish")


def _git_output(repo: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def git_state(repo: Path) -> dict[str, Any]:
    git_dir = _git_output(repo, "rev-parse", "--git-dir")
    if not git_dir:
        return {"is_git_repo": False}
    status = _git_output(repo, "status", "--porcelain")
    return {
        "is_git_repo": True,
        "branch": _git_output(repo, "branch", "--show-current"),
        "head_sha": _git_output(repo, "rev-parse", "HEAD"),
        "upstream": _git_output(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"),
        "dirty": bool(status),
        "status_porcelain": status.splitlines() if status else [],
    }


def repo_identity(repo: Path) -> str:
    top_level = _git_output(repo, "rev-parse", "--show-toplevel")
    if top_level:
        return Path(top_level).name
    return repo.name or "."


def _target_kind(target: dict[str, Any], plan: dict[str, Any] | None = None) -> str:
    if plan and plan.get("kind") in {"bot", "guild"}:
        return str(plan["kind"])
    if "guild_id_env" in target or "manage_guild_token_env" in target:
        return "guild"
    return "bot"


def write_receipt(
    repo: Path,
    target: dict[str, Any],
    mode: str,
    plan: dict[str, Any],
    remote: dict[str, Any] | None = None,
    partial_failure: dict[str, Any] | None = None,
) -> dict[str, str]:
    receipt_dir = _repo_path(repo, target["evidence"]["receipt_dir"])
    receipt_dir.mkdir(parents=True, exist_ok=True)
    target_id = str(target["id"])
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    base = receipt_dir / f"{stamp}-{target_id}-{mode}"
    prompt_record = _repo_path(repo, target["asset_paths"]["prompt_record"])
    payload = {
        "schema_version": SCHEMA_VERSION,
        "kind": _target_kind(target, plan),
        "mode": mode,
        "target_id": target_id,
        "target_repo": repo_identity(repo),
        "target_repo_git": git_state(repo),
        "manifest_sha256": plan.get("manifest_sha256", ""),
        "prompt_record_sha256": sha256_file(prompt_record) if prompt_record.exists() else "",
        "local_assets": plan.get("assets", {}),
        "publish_plan": {
            "confirmation_id": plan.get("confirmation_id", ""),
            "surfaces": plan.get("surfaces", []),
        },
        "remote": remote or {},
        "partial_failure": partial_failure or {},
    }
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    lines = [
        f"# Discord Identity Assets Receipt: {target_id}",
        "",
        f"- Mode: `{mode}`",
        f"- Target: `{target_id}`",
        f"- Confirmation ID: `{plan.get('confirmation_id', '')}`",
        f"- Manifest SHA-256: `{payload['manifest_sha256']}`",
        f"- Prompt Record SHA-256: `{payload['prompt_record_sha256']}`",
        "",
        "## Target Repo Git",
        "",
        f"- Is Git Repo: `{payload['target_repo_git'].get('is_git_repo')}`",
        f"- Branch: `{payload['target_repo_git'].get('branch', '')}`",
        f"- HEAD: `{payload['target_repo_git'].get('head_sha', '')}`",
        f"- Dirty: `{payload['target_repo_git'].get('dirty', '')}`",
        "",
        "## Local Assets",
        "",
    ]
    for surface, info in payload["local_assets"].items():
        lines.append(
            f"- `{surface}`: `{info['path']}` {info['width']}x{info['height']} "
            f"sha256=`{info['sha256']}`"
        )
    lines.extend(["", "## Remote Readback", ""])
    if payload["remote"]:
        for surface, info in payload["remote"].items():
            lines.append(f"- `{surface}`: `{info}`")
    else:
        lines.append("- No live Discord mutation was performed.")
    if payload["partial_failure"]:
        lines.extend(["", "## Partial Failure", "", json.dumps(payload["partial_failure"], indent=2)])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"markdown": _rel(repo, md_path), "json": _rel(repo, json_path)}


def write_runbook(
    repo: Path,
    target: dict[str, Any],
    *,
    plan: dict[str, Any] | None = None,
    last_receipt: dict[str, str] | None = None,
) -> str:
    receipt_dir_rel = _get_nested(target, "evidence.receipt_dir")
    if not isinstance(receipt_dir_rel, str) or not receipt_dir_rel:
        return ""
    receipt_dir = _repo_path(repo, receipt_dir_rel)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    target_id = str(target["id"])
    kind = _target_kind(target, plan)
    runbook_path = receipt_dir / f"{target_id}-checklist.md"
    finals = target.get("asset_paths", {}).get("finals", {})
    originals = target.get("asset_paths", {}).get("originals", {})
    prompt_record = target.get("asset_paths", {}).get("prompt_record", "")
    if kind == "guild":
        return write_guild_runbook(
            repo,
            target,
            plan=plan,
            last_receipt=last_receipt,
            runbook_path=runbook_path,
            finals=finals,
            originals=originals,
            prompt_record=prompt_record,
        )
    plan_lines = []
    if plan:
        plan_lines.extend(
            [
                f"- Confirmation ID: `{plan.get('confirmation_id', '')}`",
                f"- Application ID: `{plan.get('discord', {}).get('application_id', '')}`",
                f"- Expected bot user ID: `{plan.get('discord', {}).get('expected_bot_user_id', '')}`",
            ]
        )
    else:
        plan_lines.append("- Publish plan: not built yet.")

    receipt_lines = []
    if last_receipt:
        receipt_lines.extend(
            [
                f"- Markdown receipt: `{last_receipt.get('markdown', '')}`",
                f"- JSON receipt: `{last_receipt.get('json', '')}`",
            ]
        )
    else:
        receipt_lines.append("- Receipt: not written yet.")

    lines = [
        f"# Discord Identity Assets Checklist: {target_id}",
        "",
        "## Scope",
        "",
        "- This bot target publishes only the bot avatar, application icon, and bot profile banner.",
        "- This bot target does not create Discord applications, reset tokens, invite bots, or update guild/server art.",
        "- Resolves token material only from the named environment variable at publish time.",
        "",
        "## Target",
        "",
        f"- Persona: `{target.get('persona', '')}`",
        f"- Profile: `{target.get('profile', '')}`",
        f"- Token environment variable: `{target.get('token_env', '')}`",
        f"- Manifest: `{MANIFEST_REL.as_posix()}`",
        "",
        "## Assets",
        "",
        f"- Avatar original: `{originals.get('avatar', '')}`",
        f"- Banner original: `{originals.get('banner', '')}`",
        f"- Avatar final: `{finals.get('avatar', '')}`",
        f"- Application icon final: `{finals.get('app_icon', '')}`",
        f"- Banner final: `{finals.get('banner', '')}`",
        f"- Prompt record: `{prompt_record}`",
        "",
        "## Publish Plan",
        "",
        *plan_lines,
        "",
        "## Evidence",
        "",
        *receipt_lines,
        "",
        "## Rerun",
        "",
        "```bash",
        "SCRIPT=<path-to-installed-discord_identity_assets.py>",
        'python3 "$SCRIPT" validate --repo <team-repo> --mode publish',
        f'python3 "$SCRIPT" postprocess --repo <team-repo> --target {target_id}',
        f'python3 "$SCRIPT" plan-publish --repo <team-repo> --target {target_id}',
        f'python3 "$SCRIPT" publish --repo <team-repo> --target {target_id} --confirmation-id <id> --publish',
        "```",
        "",
        "## Checklist",
        "",
        "- [ ] Manifest validates in publish mode.",
        "- [ ] Prompt record says `prompt_consistency: passed`.",
        "- [ ] Publish plan confirmation ID matches the approved plan.",
        "- [ ] Receipt records non-empty Discord readback identifiers for all published surfaces.",
    ]
    runbook_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return _rel(repo, runbook_path)


def write_guild_runbook(
    repo: Path,
    target: dict[str, Any],
    *,
    plan: dict[str, Any] | None,
    last_receipt: dict[str, str] | None,
    runbook_path: Path,
    finals: dict[str, Any],
    originals: dict[str, Any],
    prompt_record: str,
) -> str:
    plan_lines = []
    if plan:
        plan_lines.extend(
            [
                f"- Confirmation ID: `{plan.get('confirmation_id', '')}`",
                f"- Expected guild name: `{plan.get('discord', {}).get('expected_guild_name', '')}`",
                f"- Guild ID environment variable: `{target.get('guild_id_env', '')}`",
                f"- Manage Guild token environment variable: `{target.get('manage_guild_token_env', '')}`",
                f"- Required guild feature for image banner: `{plan.get('discord', {}).get('banner_feature_required', 'BANNER')}`",
            ]
        )
    else:
        plan_lines.append("- Publish plan: not built yet.")

    receipt_lines = []
    if last_receipt:
        receipt_lines.extend(
            [
                f"- Markdown receipt: `{last_receipt.get('markdown', '')}`",
                f"- JSON receipt: `{last_receipt.get('json', '')}`",
            ]
        )
    else:
        receipt_lines.append("- Receipt: not written yet.")

    lines = [
        f"# Discord Guild Identity Assets Checklist: {target.get('id', '')}",
        "",
        "## Scope",
        "",
        "- Publishes only the Discord server icon and image banner.",
        "- Does not create servers, channels, roles, invites, or bot applications.",
        "- Records Server Profile banner color as metadata only; it does not automate that UI color setting.",
        "- Resolves guild ID and token material only from named environment variables at publish time.",
        "",
        "## Target",
        "",
        f"- Display name: `{target.get('display_name', '')}`",
        f"- Expected guild name: `{target.get('discord', {}).get('expected_guild_name', '')}`",
        f"- Guild ID environment variable: `{target.get('guild_id_env', '')}`",
        f"- Manage Guild token environment variable: `{target.get('manage_guild_token_env', '')}`",
        f"- Server Profile color recommendation: `{target.get('profile_banner_color', '')}`",
        f"- Manifest: `{MANIFEST_REL.as_posix()}`",
        "",
        "## Assets",
        "",
        f"- Icon original: `{originals.get('icon', '')}`",
        f"- Banner original: `{originals.get('banner', '')}`",
        f"- Icon final: `{finals.get('icon', '')}`",
        f"- Banner final: `{finals.get('banner', '')}`",
        f"- Prompt record: `{prompt_record}`",
        "",
        "## Publish Plan",
        "",
        *plan_lines,
        "",
        "## Evidence",
        "",
        *receipt_lines,
        "",
        "## Rerun",
        "",
        "```bash",
        "SCRIPT=<path-to-installed-discord_identity_assets.py>",
        'python3 "$SCRIPT" validate --repo <team-repo> --kind guild --mode publish',
        f'python3 "$SCRIPT" postprocess --repo <team-repo> --kind guild --target {target.get("id", "")}',
        f'python3 "$SCRIPT" plan-publish --repo <team-repo> --kind guild --target {target.get("id", "")}',
        f'python3 "$SCRIPT" publish --repo <team-repo> --kind guild --target {target.get("id", "")} --confirmation-id <id> --publish',
        "```",
        "",
        "## Checklist",
        "",
        "- [ ] Manifest validates in guild publish mode.",
        "- [ ] Prompt record says `prompt_consistency: passed`.",
        "- [ ] Publish plan confirmation ID matches the approved plan.",
        "- [ ] Receipt records Discord readback identifiers for every published surface.",
        "- [ ] If the guild lacks the `BANNER` feature, the receipt records the icon-only partial state.",
    ]
    runbook_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return _rel(repo, runbook_path)


def publish_assets(
    repo: Path,
    target_id: str,
    confirmation_id: str | None = None,
    *,
    do_publish: bool = False,
    kind: str = "bot",
    transport: Transport | None = None,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    if kind == "guild":
        return publish_guild_assets(
            repo,
            target_id,
            confirmation_id,
            do_publish=do_publish,
            transport=transport,
            environ=environ,
        )
    plan = build_publish_plan(repo, target_id, kind="bot")
    manifest = load_manifest(repo)
    target = target_by_id(manifest, target_id)
    if not do_publish:
        receipt = write_receipt(repo, target, "dry-run", plan)
        runbook = write_runbook(repo, target, plan=plan, last_receipt=receipt)
        return {"mode": "dry-run", "publish_plan": plan, "receipt": receipt, "runbook": runbook}

    if confirmation_id != plan["confirmation_id"]:
        raise PublishError("confirmation id does not match the current publish plan")
    _ensure_prompt_gate(repo, target)

    token = resolve_token(str(target["token_env"]), environ=environ)
    client = DiscordClient(token, transport=transport)
    expected_user_id = str(target["discord"]["expected_bot_user_id"])
    application_id = str(target["discord"]["application_id"])
    user = client.get_user()
    if str(user.get("id")) != expected_user_id:
        raise PublishError("resolved token belongs to the wrong bot user")
    app = client.get_current_application()
    if str(app.get("id")) != application_id:
        raise PublishError("resolved token belongs to the wrong application")

    finals = target["asset_paths"]["finals"]
    changed: list[str] = []
    remote: dict[str, Any] = {}
    failed_surface = "unknown"
    try:
        failed_surface = "avatar"
        avatar = client.patch_user({"avatar": _data_uri(_repo_path(repo, finals["avatar"]))})
        avatar_hash = avatar.get("avatar")
        if not avatar_hash:
            raise PublishError("avatar readback hash was empty")
        changed.append("avatar")
        remote["avatar"] = {"endpoint": "/users/@me", "hash": avatar_hash}

        app_icon_endpoint = "/applications/@me"
        failed_surface = "app_icon"
        try:
            app_icon = client.patch_current_application(
                {"icon": _data_uri(_repo_path(repo, finals["app_icon"]))}
            )
        except DiscordApiError as exc:
            if (
                not target.get("discord", {}).get("allow_legacy_application_endpoint")
                or exc.status not in {403, 404, 405}
            ):
                raise
            app_icon_endpoint = f"/applications/{application_id}"
            app_icon = client.patch_application(
                application_id,
                {"icon": _data_uri(_repo_path(repo, finals["app_icon"]))},
            )
        icon_hash = app_icon.get("icon")
        if not icon_hash:
            raise PublishError("application icon readback hash was empty")
        changed.append("app_icon")
        remote["app_icon"] = {"endpoint": app_icon_endpoint, "hash": icon_hash}

        failed_surface = "banner"
        banner = client.patch_user({"banner": _data_uri(_repo_path(repo, finals["banner"]))})
        banner_hash = banner.get("banner")
        if not banner_hash:
            raise PublishError("banner readback hash was empty")
        changed.append("banner")
        remote["banner"] = {"endpoint": "/users/@me", "hash": banner_hash}
    except Exception as exc:
        partial = {
            "changed_surfaces": changed,
            "failed_surface": failed_surface,
            "failed": str(exc),
        }
        receipt = write_receipt(repo, target, "partial-failure", plan, remote=remote, partial_failure=partial)
        write_runbook(repo, target, plan=plan, last_receipt=receipt)
        raise PublishError(f"publish stopped after partial state; receipt={receipt}: {exc}") from exc

    receipt = write_receipt(repo, target, "publish", plan, remote=remote)
    runbook = write_runbook(repo, target, plan=plan, last_receipt=receipt)
    return {"mode": "publish", "publish_plan": plan, "remote": remote, "receipt": receipt, "runbook": runbook}


def _redact_value(text: str, value: str) -> str:
    return text.replace(value, "<redacted>") if value else text


def publish_guild_assets(
    repo: Path,
    target_id: str,
    confirmation_id: str | None = None,
    *,
    do_publish: bool = False,
    transport: Transport | None = None,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    plan = build_publish_plan(repo, target_id, kind="guild")
    manifest = load_manifest(repo)
    target = guild_target_by_id(manifest, target_id)
    if not do_publish:
        receipt = write_receipt(repo, target, "dry-run", plan)
        runbook = write_runbook(repo, target, plan=plan, last_receipt=receipt)
        return {"mode": "dry-run", "publish_plan": plan, "receipt": receipt, "runbook": runbook}

    if confirmation_id != plan["confirmation_id"]:
        raise PublishError("confirmation id does not match the current publish plan")
    _ensure_prompt_gate(repo, target)

    token = resolve_token(str(target["manage_guild_token_env"]), environ=environ)
    guild_id = resolve_snowflake_env(
        str(target["guild_id_env"]),
        label="guild id",
        environ=environ,
    )
    client = DiscordClient(token, transport=transport)
    expected_actor_user_id = str(target.get("expected_actor_user_id") or "")
    actor = client.get_user()
    if expected_actor_user_id and str(actor.get("id")) != expected_actor_user_id:
        raise PublishError("resolved token belongs to the wrong Discord actor")

    guild = client.get_guild(guild_id)
    expected_name = str(target["discord"]["expected_guild_name"])
    if str(guild.get("name")) != expected_name:
        raise PublishError("resolved guild id points at the wrong guild name")
    features = guild.get("features", [])
    if not isinstance(features, list):
        features = []

    finals = target["asset_paths"]["finals"]
    changed: list[str] = []
    remote: dict[str, Any] = {}
    failed_surface = "unknown"
    try:
        failed_surface = "icon"
        icon = client.patch_guild(guild_id, {"icon": _data_uri(_repo_path(repo, finals["icon"]))})
        icon_hash = icon.get("icon")
        if not icon_hash:
            raise PublishError("guild icon readback hash was empty")
        changed.append("icon")
        remote["icon"] = {
            "endpoint": "/guilds/{guild_id}",
            "hash": icon_hash,
            "guild_name": icon.get("name", expected_name),
        }

        if "BANNER" not in {str(feature) for feature in features}:
            partial = {
                "changed_surfaces": changed,
                "failed_surface": "banner",
                "failed": "guild does not report BANNER feature; image banner was not attempted",
                "guild_features": [str(feature) for feature in features],
            }
            receipt = write_receipt(
                repo,
                target,
                "partial-failure",
                plan,
                remote=remote,
                partial_failure=partial,
            )
            runbook = write_runbook(repo, target, plan=plan, last_receipt=receipt)
            return {
                "mode": "partial-failure",
                "publish_plan": plan,
                "remote": remote,
                "partial_failure": partial,
                "receipt": receipt,
                "runbook": runbook,
            }

        failed_surface = "banner"
        banner = client.patch_guild(
            guild_id,
            {"banner": _data_uri(_repo_path(repo, finals["banner"]))},
        )
        banner_hash = banner.get("banner")
        if not banner_hash:
            raise PublishError("guild banner readback hash was empty")
        changed.append("banner")
        remote["banner"] = {
            "endpoint": "/guilds/{guild_id}",
            "hash": banner_hash,
            "guild_name": banner.get("name", expected_name),
        }
    except Exception as exc:
        partial = {
            "changed_surfaces": changed,
            "failed_surface": failed_surface,
            "failed": _redact_value(str(exc), guild_id),
        }
        receipt = write_receipt(repo, target, "partial-failure", plan, remote=remote, partial_failure=partial)
        write_runbook(repo, target, plan=plan, last_receipt=receipt)
        raise PublishError(f"publish stopped after partial state; receipt={receipt}: {partial['failed']}") from exc

    receipt = write_receipt(repo, target, "publish", plan, remote=remote)
    runbook = write_runbook(repo, target, plan=plan, last_receipt=receipt)
    return {"mode": "publish", "publish_plan": plan, "remote": remote, "receipt": receipt, "runbook": runbook}


def verify_receipt(repo: Path, receipt: Path) -> dict[str, Any]:
    path = receipt if receipt.is_absolute() else repo / receipt
    data = json.loads(path.read_text(encoding="utf-8"))
    required = (
        "mode",
        "target_id",
        "target_repo",
        "target_repo_git",
        "manifest_sha256",
        "prompt_record_sha256",
        "local_assets",
        "publish_plan",
        "remote",
        "partial_failure",
    )
    missing = [field for field in required if field not in data]
    if data.get("mode") == "publish":
        remote = data.get("remote", {})
        surfaces = GUILD_SURFACES if data.get("kind") == "guild" else BOT_SURFACES
        for surface in surfaces:
            if not isinstance(remote, dict) or not remote.get(surface, {}).get("hash"):
                missing.append(f"remote.{surface}.hash")
    if data.get("mode") == "partial-failure":
        partial_failure = data.get("partial_failure", {})
        for field in ("changed_surfaces", "failed_surface", "failed"):
            if not isinstance(partial_failure, dict) or field not in partial_failure:
                missing.append(f"partial_failure.{field}")
    return {"valid": not missing, "missing": missing, "receipt": _rel(repo, path), "data": data}


def _cmd_discover(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    manifest = discover_manifest(repo, persona=args.persona)
    path = manifest_path(repo)
    if args.write:
        if path.exists() and not args.force:
            raise ManifestError(f"{path} already exists; pass --force to overwrite")
        _write_yaml(path, manifest)
    print(json.dumps({"manifest": MANIFEST_REL.as_posix(), "data": manifest}, indent=2))
    return 0


def _cmd_scaffold_guild(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    manifest = scaffold_guild_manifest(
        repo,
        target_id=args.target,
        display_name=args.display_name,
        expected_guild_name=args.expected_guild_name,
        guild_id_env=args.guild_id_env,
        manage_guild_token_env=args.manage_guild_token_env,
        expected_actor_user_id=args.expected_actor_user_id or "",
        profile_banner_color=args.profile_banner_color or "",
        force=args.force,
    )
    if args.write:
        _write_yaml(manifest_path(repo), manifest)
    print(json.dumps({"manifest": MANIFEST_REL.as_posix(), "data": manifest}, indent=2))
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    errors = validate_manifest(Path(args.repo).resolve(), mode=args.mode, kind=args.kind)
    print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
    return 0 if not errors else 1


def _cmd_preview_plan(args: argparse.Namespace) -> int:
    result = preview_plan(Path(args.repo).resolve(), args.target, kind=args.kind)
    print(json.dumps(result, indent=2))
    return 0


def _cmd_postprocess(args: argparse.Namespace) -> int:
    result = postprocess_assets(Path(args.repo).resolve(), args.target, kind=args.kind)
    print(json.dumps(result, indent=2))
    return 0


def _cmd_plan_publish(args: argparse.Namespace) -> int:
    plan = build_publish_plan(Path(args.repo).resolve(), args.target, kind=args.kind)
    print(json.dumps(plan, indent=2))
    return 0


def _cmd_publish(args: argparse.Namespace) -> int:
    result = publish_assets(
        Path(args.repo).resolve(),
        args.target,
        args.confirmation_id,
        do_publish=args.publish,
        kind=args.kind,
    )
    print(json.dumps(result, indent=2))
    return 0


def _cmd_verify_receipt(args: argparse.Namespace) -> int:
    result = verify_receipt(Path(args.repo).resolve(), Path(args.receipt))
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("discover")
    p.add_argument("--repo", required=True)
    p.add_argument("--persona")
    p.add_argument("--write", action="store_true")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=_cmd_discover)

    p = sub.add_parser("scaffold-guild")
    p.add_argument("--repo", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--display-name", required=True)
    p.add_argument("--expected-guild-name", required=True)
    p.add_argument("--guild-id-env", required=True)
    p.add_argument("--manage-guild-token-env", required=True)
    p.add_argument("--expected-actor-user-id", default="")
    p.add_argument("--profile-banner-color", default="")
    p.add_argument("--write", action="store_true")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=_cmd_scaffold_guild)

    p = sub.add_parser("validate")
    p.add_argument("--repo", required=True)
    p.add_argument("--kind", choices=["bot", "guild"], default="bot")
    p.add_argument("--mode", choices=["generate", "publish"], default="generate")
    p.set_defaults(func=_cmd_validate)

    p = sub.add_parser("preview-plan")
    p.add_argument("--repo", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--kind", choices=["bot", "guild"], default="bot")
    p.set_defaults(func=_cmd_preview_plan)

    p = sub.add_parser("postprocess")
    p.add_argument("--repo", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--kind", choices=["bot", "guild"], default="bot")
    p.set_defaults(func=_cmd_postprocess)

    p = sub.add_parser("plan-publish")
    p.add_argument("--repo", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--kind", choices=["bot", "guild"], default="bot")
    p.set_defaults(func=_cmd_plan_publish)

    p = sub.add_parser("publish")
    p.add_argument("--repo", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--kind", choices=["bot", "guild"], default="bot")
    p.add_argument("--confirmation-id")
    p.add_argument("--publish", action="store_true")
    p.set_defaults(func=_cmd_publish)

    p = sub.add_parser("verify-receipt")
    p.add_argument("--repo", required=True)
    p.add_argument("--receipt", required=True)
    p.set_defaults(func=_cmd_verify_receipt)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except DiscordIdentityError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
