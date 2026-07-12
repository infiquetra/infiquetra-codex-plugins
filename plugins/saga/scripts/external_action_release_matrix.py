#!/usr/bin/env python3
"""Run the attended external-action provider and lifecycle release matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

import external_action_adapters as adapters  # noqa: E402
import external_action_contract as contract  # noqa: E402
import external_action_lifecycle as lifecycle  # noqa: E402
import external_action_policy as action_policy  # noqa: E402
import external_action_runtime as runtime_module  # noqa: E402
import external_action_status as status_module  # noqa: E402
import external_action_store as store_module  # noqa: E402
import reconcile  # noqa: E402
import engine_registry_overlay  # noqa: E402
from engine_registry import EngineEntry, Registry  # noqa: E402

SCHEMA_VERSION = 1
DEFAULT_REGISTRY = Path(__file__).resolve().parent.parent / "references" / "engine-registry.yaml"
DEFAULT_OUTPUT = Path("docs/validation/codex-external-action-runtime-proof.json")
ASSIGNMENTS = (
    ("ideate", "offload", "claude-cli/opus", False),
    ("brainstorm", "second-opinion", "agy/gemini-3.5-flash-high", False),
    ("plan", "offload", "ollama-cloud/gpt-oss-120b", False),
    ("work", "second-opinion", "claude-cli/opus", False),
    ("doc-review", "second-opinion", "agy/gemini-3.5-flash-high", False),
    ("code-review", "second-opinion", "ollama-cloud/gpt-oss-120b", True),
)


class ReleaseMatrixError(RuntimeError):
    pass


def prerequisites(registry: Registry) -> dict[str, Any]:
    ollama = registry.by_key("ollama-cloud/gpt-oss-120b")
    auth = dict(ollama.invocation.get("auth") or {})
    key_env = str(auth.get("key_env") or "")
    return {
        "claude_cli": bool(shutil.which("claude")),
        "agy_cli": bool(shutil.which("agy")),
        "ollama_key_ref": key_env,
        "ollama_key_available": bool(key_env and os.environ.get(key_env)),
    }


def run_matrix(*, repo_root: Path, registry_path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    registry = engine_registry_overlay.load_runtime_registry(registry_path, repo_root)
    checks = prerequisites(registry)
    if not all((checks["claude_cli"], checks["agy_cli"], checks["ollama_key_available"])):
        raise ReleaseMatrixError("live provider prerequisites are incomplete")
    base_revision = _git(repo_root, "rev-parse", "HEAD")
    source_head = base_revision
    recorded_at = datetime.now(UTC).isoformat()
    run_id = (
        "release-"
        + datetime.now(UTC).strftime("%Y%m%dt%H%M%S%f").lower()
        + "-"
        + uuid.uuid4().hex
    )
    evidence_root = repo_root / "docs" / "validation" / "external-action-evidence" / run_id
    evidence_root.mkdir(parents=True, exist_ok=False)
    stages: list[dict[str, Any]] = []
    default_actions = action_policy.load_defaults()

    for index, (stage, intent, engine_key, required) in enumerate(ASSIGNMENTS, start=1):
        bundle = lifecycle.StageBundle(
            stage=stage,
            source="release-defaults",
            actions=default_actions[stage],
        )
        matching = [item for item in bundle.actions if item.intent == intent]
        if len(matching) != 1:
            raise ReleaseMatrixError(f"{stage}: expected one {intent} action")
        action = matching[0]
        if required:
            action = replace(
                action,
                requiredness=contract.Requiredness("required-before-continue"),
            )
            bundle = lifecycle.StageBundle(stage=stage, source="release-matrix", actions=(action,))
        entry = registry.by_key(engine_key)
        route = _route(entry)
        preview = lifecycle.prepare_bundle(
            bundle,
            repo_root=repo_root,
            saga_id="task-external-action-release",
            run_id=f"{run_id}-{index}",
            routes={action.action_id: route},
            payloads={action.action_id: _prompt(stage, intent)},
            cost_classes={action.action_id: entry.cost_class},
            route_egress={action.action_id: _egress(entry)},
            base_revision=base_revision,
            created_at=recorded_at,
            selected_action_ids=[action.action_id],
        )[0]
        lifecycle.approve_bundle(
            [preview],
            operator="attended-operator",
            approved_at=recorded_at,
        )
        execution = lifecycle.execute_bundle(
            [preview],
            executors={
                action.action_id: adapters.executor_for_preview(preview, repo_root=repo_root)
            },
            at=recorded_at,
        )
        outcome = execution.outcomes[action.action_id]
        if outcome.status != "available":
            raise ReleaseMatrixError(
                f"{stage}/{engine_key}: terminal status {outcome.status}"
            )
        if intent == "offload":
            lifecycle.adjudicate_artifact(
                preview,
                accepted=True,
                at=recorded_at,
                detail={"release_matrix": True},
            )
        else:
            findings = reconcile.parse_source_findings(dict(outcome.detail or {}).get("findings"))
            lifecycle.adjudicate_opinion(
                preview,
                outcome,
                decisions={
                    finding.source_finding_id: {
                        "status": "reconciled",
                        "rationale": "attended release-matrix consumption",
                    }
                    for finding in findings
                },
                reconciliation_id=f"reconcile-{run_id}-{index}",
                adjudicator_id="codex/root",
                at=recorded_at,
            )
        lifecycle.consume(
            preview,
            at=recorded_at,
            artifact_ref=f"release-matrix://{stage}/{action.action_id}",
        )
        snapshot = store_module.read_snapshot(preview.store)
        record_root = evidence_root / "actions" / f"{index:02d}-{action.action_id}"
        shutil.copytree(preview.store.root, record_root)
        status = status_module.project(snapshot, evidence_root=record_root)
        if status["state"] != "consumed" or status["receipt_validity"] != "valid":
            raise ReleaseMatrixError(f"{stage}/{engine_key}: invalid terminal status card")
        if snapshot.approval is None:
            raise ReleaseMatrixError(f"{stage}/{engine_key}: consumed action has no approval")
        receipt = _complete_receipt(snapshot.events)
        artifact_bindings = _complete_artifact_bindings(snapshot.events)
        stages.append(
            {
                "stage": stage,
                "action_id": action.action_id,
                "intent": intent,
                "requiredness": action.requiredness.value,
                "engine_key": engine_key,
                "adapter_class": status["adapter_class"],
                "state": status["state"],
                "receipt_validity": status["receipt_validity"],
                "request_sha256": snapshot.request.request_sha256,
                "approval_fingerprint": snapshot.approval.approval_fingerprint,
                "event_chain_tip": snapshot.events[-1]["this_hash"],
                "receipt_sha256": _sha256_json(receipt),
                **artifact_bindings,
                "status_card_sha256": hashlib.sha256(
                    status_module.render(status).encode("utf-8")
                ).hexdigest(),
                "action_record_sha256": _directory_digest(record_root),
                "action_record_ref": record_root.relative_to(repo_root).as_posix(),
            }
        )

    proof: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "recorded_at": recorded_at,
        "source_head": source_head,
        "source_tree": _git(repo_root, "rev-parse", f"{source_head}^{{tree}}"),
        "source_worktree_sha256": _commit_workspace_digest(repo_root, source_head),
        "release_run_id": run_id,
        "evidence_bundle": evidence_root.relative_to(repo_root).as_posix(),
        "status": "passed",
        "prerequisites": checks,
        "providers": sorted({item["engine_key"] for item in stages}),
        "stages": stages,
        "rollback_drill": _rollback_drill(
            repo_root,
            base_revision,
            evidence_root=evidence_root,
            release_run_id=run_id,
        ),
        "sanitization": {
            "credentials": False,
            "prompts_or_transcripts": True,
            "absolute_paths": False,
            "raw_receipts": True,
        },
    }
    proof["content_sha256"] = _sha256_json(proof)
    validate_proof(proof, repo_root=repo_root)
    return proof


def _route(entry: EngineEntry) -> dict[str, Any]:
    return {
        "engine_id": entry.engine_id,
        "variant": entry.variant,
        "protocol": list(entry.prompting_protocol),
        "invocation": dict(entry.invocation),
    }


def _egress(entry: EngineEntry) -> dict[str, Any]:
    base_url = str(entry.invocation.get("base_url") or "")
    host = urlsplit(base_url).hostname if base_url else entry.engine_id
    return {"policy": entry.egress_policy, "host": host or entry.engine_id}


def _prompt(stage: str, intent: str) -> str:
    if intent == "second-opinion":
        return (
            f"For the {stage} release fixture, identify one low-risk concern. "
            "Return concise advisory text only. Do not use tools or modify files."
        )
    return (
        f"For the {stage} release fixture, return one concise bounded artifact sentence. "
        "Do not use tools or modify files."
    )


def _complete_receipt(events: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    for event in reversed(events):
        if event["event"] == "complete":
            receipt = dict(event.get("detail", {})).get("runner_receipt")
            if isinstance(receipt, dict):
                return receipt
    raise ReleaseMatrixError("complete event has no receipt")


def _complete_artifact_bindings(events: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    for event in reversed(events):
        if event["event"] != "complete":
            continue
        detail = dict(event.get("detail", {}))
        evidence_sha256 = detail.get("artifact_sha256")
        evidence_digest = detail.get("evidence_digest")
        finding_count = detail.get("finding_count")
        if (
            not isinstance(evidence_sha256, str)
            or not isinstance(evidence_digest, str)
            or not isinstance(finding_count, int)
        ):
            raise ReleaseMatrixError("complete event has incomplete artifact bindings")
        return {
            "evidence_sha256": evidence_sha256,
            "evidence_digest": evidence_digest,
            "finding_count": finding_count,
        }
    raise ReleaseMatrixError("complete event has no artifact bindings")


def _rollback_drill(
    repo_root: Path,
    base_revision: str,
    *,
    evidence_root: Path | None = None,
    release_run_id: str | None = None,
) -> dict[str, Any]:
    release_run_id = release_run_id or f"release-{base_revision[:12]}"
    evidence_root = evidence_root or (
        repo_root / "docs" / "validation" / "external-action-evidence" / release_run_id
    )
    command_root = evidence_root / "commands"
    command_root.mkdir(parents=True, exist_ok=True)
    source = repo_root / "plugins" / "saga"
    with tempfile.TemporaryDirectory(prefix="saga-isolated-install-") as directory:
        root = Path(directory)
        codex_home = root / "codex-home"
        codex_home.mkdir()
        marketplace = root / "marketplace"
        marketplace_manifest = marketplace / ".agents" / "plugins" / "marketplace.json"
        marketplace_manifest.parent.mkdir(parents=True)
        plugin_source = marketplace / "plugins" / "saga"
        shutil.copytree(source, plugin_source)
        fleet_source = marketplace / "plugins" / "fleet-core"
        shutil.copytree(repo_root / "plugins" / "fleet-core", fleet_source)
        marketplace_manifest.write_text(
            json.dumps(
                {
                    "name": "isolated-external-action",
                    "interface": {"displayName": "Isolated External Action"},
                    "plugins": [
                        {
                            "name": "fleet-core",
                            "source": {"source": "local", "path": "./plugins/fleet-core"},
                            "policy": {
                                "installation": "AVAILABLE",
                                "authentication": "ON_INSTALL",
                            },
                            "category": "Developer Tools",
                        },
                        {
                            "name": "saga",
                            "source": {"source": "local", "path": "./plugins/saga"},
                            "policy": {
                                "installation": "AVAILABLE",
                                "authentication": "ON_INSTALL",
                            },
                            "category": "Developer Tools",
                        }
                    ],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        env = {"PATH": os.environ.get("PATH", ""), "CODEX_HOME": str(codex_home)}
        records: list[dict[str, Any]] = []
        normalized_results: dict[str, Any] = {}
        replacements = {
            sys.executable: "$PYTHON",
            str(codex_home.resolve()): "$CODEX_HOME",
            str(codex_home): "$CODEX_HOME",
            str(marketplace.resolve()): "$MARKETPLACE",
            str(marketplace): "$MARKETPLACE",
            str(root.resolve()): "$ISOLATED_ROOT",
            str(root): "$ISOLATED_ROOT",
            str(repo_root.resolve()): "$REPO_ROOT",
            str(repo_root): "$REPO_ROOT",
        }

        def capture(
            operation: str,
            argv: list[str],
            semantics: Any,
        ) -> Any:
            result, normalized, record = _capture_json_command(
                argv,
                cwd=repo_root,
                env=env,
                command_root=command_root,
                release_run_id=release_run_id,
                sequence=len(records) + 1,
                source_head=base_revision,
                operation=operation,
                replacements=replacements,
                semantics=semantics,
            )
            records.append(record)
            normalized_results[operation] = normalized
            return result

        prior_list = capture(
            "prior-list",
            ["codex", "plugin", "list", "--json"],
            lambda result: {"list_sha256": _sha256_json(result)},
        )
        add_marketplace = capture(
            "marketplace-add",
            ["codex", "plugin", "marketplace", "add", str(marketplace), "--json"],
            lambda _result: {"marketplace_name": "isolated-external-action"},
        )
        fleet_install = capture(
            "fleet-install",
            ["codex", "plugin", "add", "fleet-core@isolated-external-action", "--json"],
            lambda _result: {"plugin_name": "fleet-core"},
        )
        fleet_root = Path(str(fleet_install.get("installedPath") or "")).resolve(strict=False)
        if not fleet_root.is_relative_to(codex_home.resolve()) or not fleet_root.is_dir():
            raise ReleaseMatrixError("isolated fleet-core install path is missing or escaped")
        fleet_candidate_digest = _directory_digest(fleet_root)
        env["FLEET_COMMONS_ROOT"] = str(fleet_root)
        install = capture(
            "saga-install",
            ["codex", "plugin", "add", "saga@isolated-external-action", "--json"],
            lambda _result: {"plugin_name": "saga"},
        )
        installed_list = capture(
            "installed-list",
            ["codex", "plugin", "list", "--json"],
            lambda result: {
                "list_sha256": _sha256_json(result),
                "required_plugins": ["fleet-core", "saga"],
            },
        )
        installed_root = Path(str(install.get("installedPath") or "")).resolve(strict=False)
        if not installed_root.is_relative_to(codex_home.resolve()) or not installed_root.is_dir():
            raise ReleaseMatrixError("isolated Codex install path is missing or escaped")
        candidate_digest = _directory_digest(installed_root)
        readback = capture(
            "fresh-session-probe",
            [
                sys.executable,
                "-I",
                "-c",
                (
                    "import sys; sys.path.insert(0, sys.argv[1]); "
                    "import external_action; raise SystemExit(external_action.main(['probe']))"
                ),
                str(installed_root / "scripts"),
            ],
            lambda _result: {"probe": "external-action"},
        )
        remove = capture(
            "saga-remove",
            ["codex", "plugin", "remove", "saga@isolated-external-action", "--json"],
            lambda _result: {"plugin_name": "saga"},
        )
        fleet_remove = capture(
            "fleet-remove",
            ["codex", "plugin", "remove", "fleet-core@isolated-external-action", "--json"],
            lambda _result: {"plugin_name": "fleet-core"},
        )
        remove_marketplace = capture(
            "marketplace-remove",
            ["codex", "plugin", "marketplace", "remove", "isolated-external-action", "--json"],
            lambda _result: {"marketplace_name": "isolated-external-action"},
        )
        restored_list = capture(
            "restored-list",
            ["codex", "plugin", "list", "--json"],
            lambda result: {"list_sha256": _sha256_json(result)},
        )
        required_operations = {
            "prepare_bundle",
            "approve_bundle",
            "execute_bundle",
            "load_action",
            "interrupt_action",
            "retry_action",
            "adjudicate_artifact",
            "adjudicate_opinion",
            "consume",
        }
        fresh_session_passed = (
            readback.get("schema") == "saga.external-action.probe.v1"
            and set(readback.get("operations", [])) == required_operations
            and "saga" in json.dumps(installed_list)
        )
        restored = json.dumps(restored_list, sort_keys=True) == json.dumps(
            prior_list, sort_keys=True
        ) and not installed_root.exists()
        passed = (
            bool(add_marketplace)
            and bool(install)
            and bool(fleet_install)
            and bool(remove)
            and bool(fleet_remove)
            and bool(remove_marketplace)
            and fresh_session_passed
            and restored
        )
        return {
            "passed": passed,
            "base_revision": base_revision,
            "prior_installed": False,
            "candidate_installed": True,
            "fresh_session_passed": fresh_session_passed,
            "restored": restored,
            "prior_digest": _sha256_json(prior_list),
            "candidate_digest": candidate_digest,
            "fleet_candidate_digest": fleet_candidate_digest,
            "restored_digest": _sha256_json(restored_list),
            "marketplace_add_sha256": _sha256_json(normalized_results["marketplace-add"]),
            "install_receipt_sha256": _sha256_json(normalized_results["saga-install"]),
            "fleet_install_sha256": _sha256_json(normalized_results["fleet-install"]),
            "remove_receipt_sha256": _sha256_json(normalized_results["saga-remove"]),
            "fleet_remove_sha256": _sha256_json(normalized_results["fleet-remove"]),
            "marketplace_remove_sha256": _sha256_json(normalized_results["marketplace-remove"]),
            "fresh_session_sha256": _sha256_json(normalized_results["fresh-session-probe"]),
            "release_run_id": release_run_id,
            "command_records": records,
        }


def _capture_json_command(
    argv: list[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    command_root: Path,
    release_run_id: str,
    sequence: int,
    source_head: str,
    operation: str,
    replacements: Mapping[str, str],
    semantics: Any,
) -> tuple[Any, Any, dict[str, Any]]:
    started_at = datetime.now(UTC).isoformat()
    process = subprocess.run(
        argv,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=False,
        env=dict(env),
    )
    finished_at = datetime.now(UTC).isoformat()
    parse_error = ""
    try:
        result: Any = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        result = None
        parse_error = str(exc)
    normalized = _sanitize_record_value(result, replacements)
    semantic = _sanitize_record_value(semantics(normalized), replacements) if not parse_error else {}
    payload = {
        "schema": "saga.external-action.command-evidence.v2",
        "source_head": source_head,
        "release_run_id": release_run_id,
        "sequence": sequence,
        "operation": operation,
        "started_at": started_at,
        "finished_at": finished_at,
        "cwd": _sanitize_record_value(str(cwd.resolve()), replacements),
        "argv": _sanitize_record_value(argv, replacements),
        "exit_code": process.returncode,
        "stdout_sha256": hashlib.sha256(process.stdout).hexdigest(),
        "stdout_bytes": len(process.stdout),
        "stderr_sha256": hashlib.sha256(process.stderr).hexdigest(),
        "stderr_bytes": len(process.stderr),
        "result": normalized,
        "semantics": semantic,
        "parse_error": parse_error or None,
    }
    payload["content_sha256"] = _sha256_json(payload)
    content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path = command_root / f"{sequence:02d}-{operation}.json"
    path.write_text(content, encoding="utf-8")
    record = {
        "operation": operation,
        "record_ref": path.relative_to(cwd).as_posix(),
        "record_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }
    if parse_error:
        raise ReleaseMatrixError(f"{operation}: command returned malformed JSON: {parse_error}")
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, argv, process.stdout, process.stderr)
    return result, normalized, record


def _commit_workspace_digest(root: Path, revision: str) -> str:
    process = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "-z", revision],
        cwd=root,
        check=True,
        capture_output=True,
    )
    tracked = process.stdout.decode("utf-8").split("\0")
    digest = hashlib.sha256()
    for name in sorted(item for item in tracked if item):
        content = subprocess.run(
            ["git", "show", f"{revision}:{name}"],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
        digest.update(name.encode("utf-8") + b"\0" + content + b"\0")
    return digest.hexdigest()


def _commit_directory_digest(root: Path, revision: str, directory: str) -> str:
    process = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "-z", revision, "--", directory],
        cwd=root,
        check=True,
        capture_output=True,
    )
    names = process.stdout.decode("utf-8").split("\0")
    digest = hashlib.sha256()
    prefix = directory.rstrip("/") + "/"
    for name in sorted(item for item in names if item):
        relative = name.removeprefix(prefix)
        if "__pycache__" in Path(relative).parts or relative.endswith(".pyc") or Path(relative).name == ".lock":
            continue
        content = subprocess.run(
            ["git", "show", f"{revision}:{name}"],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
        digest.update(relative.encode("utf-8") + b"\0" + content + b"\0")
    return digest.hexdigest()


def _git_common_dir(repo_root: Path) -> Path:
    value = _git(repo_root, "rev-parse", "--git-common-dir")
    path = Path(value)
    return (repo_root / path).resolve() if not path.is_absolute() else path.resolve()


def _sanitize_record_value(value: Any, replacements: Mapping[str, str]) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _sanitize_record_value(item, replacements)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_record_value(item, replacements) for item in value]
    if isinstance(value, str):
        sanitized = value
        for source, replacement in replacements.items():
            sanitized = sanitized.replace(source, replacement)
        return sanitized
    return value


def _write_command_record(
    repo_root: Path,
    *,
    base_revision: str,
    operation: str,
    argv: list[str],
    result: Any,
    replacements: Mapping[str, str],
) -> tuple[dict[str, Any], Any]:
    normalized = _sanitize_record_value(result, replacements)
    payload = {
        "schema": "saga.external-action.command-evidence.v1",
        "source_head": base_revision,
        "operation": operation,
        "argv": argv,
        "result": normalized,
    }
    payload["content_sha256"] = _sha256_json(payload)
    root = _git_common_dir(repo_root) / "saga-external-actions" / "release-evidence" / base_revision
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path = root / f"{operation}-{payload['content_sha256']}.json"
    if path.exists() and path.read_text(encoding="utf-8") != content:
        raise ReleaseMatrixError("immutable command evidence differs")
    path.write_text(content, encoding="utf-8")
    os.chmod(path, 0o600)
    return (
        {
            "operation": operation,
            "record_ref": Path(os.path.relpath(path, repo_root)).as_posix(),
            "record_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        },
        normalized,
    )


def _directory_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if "__pycache__" in path.parts or path.name.endswith(".pyc") or path.name == ".lock":
            continue
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8") + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_proof(
    proof: dict[str, Any],
    *,
    repo_root: Path | None = None,
    expected_ref: str | None = None,
    proof_path: Path | None = None,
) -> None:
    """Independently recompute the release proof's closed semantic claims."""
    expected_hash = proof.get("content_sha256")
    unhashed = dict(proof)
    unhashed.pop("content_sha256", None)
    if expected_hash != _sha256_json(unhashed):
        raise ReleaseMatrixError("release proof content_sha256 is invalid")
    if proof.get("status") != "passed" or proof.get("schema_version") != SCHEMA_VERSION:
        raise ReleaseMatrixError("release proof status or schema is invalid")
    if repo_root is not None:
        source_head = str(proof.get("source_head") or "")
        try:
            source_tree = _git(repo_root, "rev-parse", f"{source_head}^{{tree}}")
        except subprocess.SubprocessError as exc:
            raise ReleaseMatrixError("release proof source_head is unavailable") from exc
        if proof.get("source_tree") != source_tree:
            raise ReleaseMatrixError("release proof source tree is invalid")
        if proof.get("source_worktree_sha256") != _commit_workspace_digest(
            repo_root, source_head
        ):
            raise ReleaseMatrixError("release proof source worktree digest is invalid")
        if expected_ref is not None:
            _validate_expected_ref(
                proof,
                repo_root=repo_root,
                expected_ref=expected_ref,
                proof_path=proof_path,
            )
        evidence_root = _evidence_bundle_root(proof, repo_root)
    expected_providers = sorted({item[2] for item in ASSIGNMENTS})
    if proof.get("providers") != expected_providers:
        raise ReleaseMatrixError("release proof provider set is invalid")
    stages = proof.get("stages")
    if not isinstance(stages, list) or len(stages) != len(ASSIGNMENTS):
        raise ReleaseMatrixError("release proof stage matrix is incomplete")
    for observed, expected in zip(stages, ASSIGNMENTS, strict=True):
        stage, intent, engine_key, required = expected
        if (
            observed.get("stage") != stage
            or observed.get("intent") != intent
            or observed.get("engine_key") != engine_key
            or observed.get("requiredness")
            != ("required-before-continue" if required else "best-effort")
            or observed.get("state") != "consumed"
            or observed.get("receipt_validity") != "valid"
        ):
            raise ReleaseMatrixError(f"release proof stage binding failed: {stage}")
        for field in (
            "request_sha256",
            "approval_fingerprint",
            "event_chain_tip",
            "receipt_sha256",
            "evidence_sha256",
            "status_card_sha256",
            "action_record_sha256",
            "evidence_digest",
        ):
            value = observed.get(field)
            if not isinstance(value, str) or len(value) != 64:
                raise ReleaseMatrixError(f"release proof {stage}.{field} is invalid")
        if not isinstance(observed.get("finding_count"), int) or observed["finding_count"] < 0:
            raise ReleaseMatrixError(f"release proof {stage}.finding_count is invalid")
        if repo_root is not None:
            record_ref = observed.get("action_record_ref")
            if not isinstance(record_ref, str):
                raise ReleaseMatrixError(f"release proof {stage}.action_record_ref is invalid")
            record_root = (repo_root / record_ref).resolve(strict=False)
            if not record_root.is_relative_to((evidence_root / "actions").resolve()):
                raise ReleaseMatrixError(f"release proof {stage} action record escapes evidence bundle")
            if not record_root.is_dir() or _directory_digest(record_root) != observed["action_record_sha256"]:
                raise ReleaseMatrixError(f"release proof {stage} action record digest is invalid")
            _validate_action_record(observed, record_root, repo_root=repo_root)
    rollback = proof.get("rollback_drill")
    if not isinstance(rollback, dict) or not all(
        rollback.get(field) is True
        for field in (
            "passed",
            "candidate_installed",
            "fresh_session_passed",
            "restored",
        )
    ):
        raise ReleaseMatrixError("release proof rollback drill is incomplete")
    if rollback.get("prior_installed") is not False:
        raise ReleaseMatrixError("release proof isolated install did not start clean")
    for field in (
        "marketplace_add_sha256",
        "install_receipt_sha256",
        "fleet_install_sha256",
        "remove_receipt_sha256",
        "fleet_remove_sha256",
        "marketplace_remove_sha256",
        "fresh_session_sha256",
    ):
        if not isinstance(rollback.get(field), str) or len(rollback[field]) != 64:
            raise ReleaseMatrixError(f"release proof rollback {field} is invalid")
    if repo_root is not None:
        source_head = str(proof.get("source_head") or "")
        if rollback.get("candidate_digest") != _commit_directory_digest(
            repo_root, source_head, "plugins/saga"
        ):
            raise ReleaseMatrixError("release proof installed Saga digest is invalid")
        if rollback.get("fleet_candidate_digest") != _commit_directory_digest(
            repo_root, source_head, "plugins/fleet-core"
        ):
            raise ReleaseMatrixError("release proof installed fleet-core digest is invalid")
        _validate_command_records(
            rollback,
            repo_root=repo_root,
            source_head=source_head,
            evidence_root=evidence_root,
            release_run_id=str(proof.get("release_run_id") or ""),
        )
    if proof.get("sanitization") != {
        "credentials": False,
        "prompts_or_transcripts": True,
        "absolute_paths": False,
        "raw_receipts": True,
    }:
        raise ReleaseMatrixError("release proof sanitization claims are invalid")


def _validate_expected_ref(
    proof: Mapping[str, Any],
    *,
    repo_root: Path,
    expected_ref: str,
    proof_path: Path | None,
) -> None:
    if proof_path is None:
        raise ReleaseMatrixError("expected evidence ref validation requires the proof path")
    source_head = str(proof.get("source_head") or "")
    expected_commit = _git(repo_root, "rev-parse", f"{expected_ref}^{{commit}}")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_head, expected_commit],
        cwd=repo_root,
        check=False,
    )
    if ancestor.returncode:
        raise ReleaseMatrixError("release proof source_head is not contained by evidence ref")
    try:
        relative = proof_path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise ReleaseMatrixError("release proof path is outside the repository") from exc
    process = subprocess.run(
        ["git", "show", f"{expected_ref}:{relative}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode:
        raise ReleaseMatrixError("expected evidence ref does not contain the release proof")
    try:
        tagged_proof = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise ReleaseMatrixError("tagged release proof is malformed") from exc
    if tagged_proof != dict(proof):
        raise ReleaseMatrixError("expected evidence ref contains a different release proof")
    for record_ref in _referenced_bundle_paths(proof):
        local = (repo_root / record_ref).resolve(strict=False)
        if not local.exists():
            raise ReleaseMatrixError("release proof referenced evidence is unavailable")
        try:
            relative = local.relative_to(repo_root.resolve()).as_posix()
        except ValueError as exc:
            raise ReleaseMatrixError("release proof referenced evidence escapes repository") from exc
        if local.is_dir():
            local_files = [
                item
                for item in local.rglob("*")
                if item.is_file() and item.name != ".lock"
            ]
        else:
            local_files = [local]
        for local_file in local_files:
            file_relative = local_file.relative_to(repo_root).as_posix()
            bundled = subprocess.run(
                ["git", "show", f"{expected_ref}:{file_relative}"],
                cwd=repo_root,
                check=False,
                capture_output=True,
            )
            if bundled.returncode or bundled.stdout != local_file.read_bytes():
                raise ReleaseMatrixError(
                    f"expected evidence ref does not contain bundled evidence: {relative}"
                )


def _evidence_bundle_root(proof: Mapping[str, Any], repo_root: Path) -> Path:
    run_id = proof.get("release_run_id")
    bundle_ref = proof.get("evidence_bundle")
    if not isinstance(run_id, str) or not run_id or not isinstance(bundle_ref, str):
        raise ReleaseMatrixError("release proof evidence bundle binding is invalid")
    evidence_root = (repo_root / bundle_ref).resolve(strict=False)
    expected_parent = (repo_root / "docs" / "validation" / "external-action-evidence").resolve()
    if not evidence_root.is_relative_to(expected_parent) or evidence_root.name != run_id:
        raise ReleaseMatrixError("release proof evidence bundle escapes durable evidence root")
    return evidence_root


def _referenced_bundle_paths(proof: Mapping[str, Any]) -> list[str]:
    references: list[str] = []
    stages = proof.get("stages")
    if isinstance(stages, list):
        for stage in stages:
            if isinstance(stage, Mapping) and isinstance(stage.get("action_record_ref"), str):
                references.append(str(stage["action_record_ref"]))
    rollback = proof.get("rollback_drill")
    records = rollback.get("command_records") if isinstance(rollback, Mapping) else None
    if isinstance(records, list):
        for record in records:
            if isinstance(record, Mapping) and isinstance(record.get("record_ref"), str):
                references.append(str(record["record_ref"]))
    return references


def _validate_action_record(
    observed: Mapping[str, Any],
    record_root: Path,
    *,
    repo_root: Path,
) -> None:
    snapshot = store_module.read_snapshot(store_module.Store(record_root, repo_root))
    approval = snapshot.approval
    if approval is None:
        raise ReleaseMatrixError("release action record has no approval")
    complete = next(
        (event for event in snapshot.events if event.get("event") == "complete"),
        None,
    )
    if complete is None:
        raise ReleaseMatrixError("release action record has no completion event")
    detail = dict(complete.get("detail", {}))
    evidence_ref = detail.get("evidence_ref")
    if not isinstance(evidence_ref, str):
        raise ReleaseMatrixError("release action record has no evidence reference")
    evidence_name = Path(evidence_ref).name
    evidence_path = record_root / evidence_name
    if not evidence_name or not evidence_path.is_file():
        raise ReleaseMatrixError("release action evidence is unavailable in copied record")
    try:
        artifact, artifact_sha256 = runtime_module._validate_evidence_artifact(
            snapshot, approval, evidence_path
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ReleaseMatrixError("release action evidence artifact is invalid") from exc
    if (
        detail.get("artifact_sha256") != artifact_sha256
        or detail.get("evidence_digest") != artifact["evidence_digest"]
        or detail.get("runner_receipt") != artifact["runner_receipt"]
        or detail.get("finding_count") != len(artifact["findings"])
    ):
        raise ReleaseMatrixError("release action evidence semantics are invalid")
    projected = status_module.project(snapshot, evidence_root=record_root)
    route = dict(approval.route)
    invocation = route.get("invocation")
    invocation = dict(invocation) if isinstance(invocation, Mapping) else {}
    adapter_class = invocation.get("via") or route.get("adapter_class")
    expected = {
        "action_id": snapshot.request.action_id,
        "stage": snapshot.request.stage,
        "intent": snapshot.request.intent,
        "requiredness": snapshot.request.requiredness.value,
        "engine_key": f"{approval.route.get('engine_id')}/{approval.route.get('variant')}",
        "adapter_class": adapter_class,
        "state": projected["state"],
        "receipt_validity": projected["receipt_validity"],
        "request_sha256": snapshot.request.request_sha256,
        "approval_fingerprint": approval.approval_fingerprint,
        "event_chain_tip": snapshot.events[-1]["this_hash"],
        "receipt_sha256": _sha256_json(_complete_receipt(snapshot.events)),
        "evidence_sha256": artifact_sha256,
        "evidence_digest": artifact["evidence_digest"],
        "finding_count": len(artifact["findings"]),
        "status_card_sha256": hashlib.sha256(
            status_module.render(projected).encode("utf-8")
        ).hexdigest(),
        "action_record_sha256": _directory_digest(record_root),
    }
    for field, value in expected.items():
        if observed.get(field) != value:
            raise ReleaseMatrixError(f"release action record {field} binding is invalid")


def _validate_command_records(
    rollback: Mapping[str, Any],
    *,
    repo_root: Path,
    source_head: str,
    evidence_root: Path | None = None,
    release_run_id: str | None = None,
) -> None:
    operations = (
        "prior-list",
        "marketplace-add",
        "fleet-install",
        "saga-install",
        "installed-list",
        "fresh-session-probe",
        "saga-remove",
        "fleet-remove",
        "marketplace-remove",
        "restored-list",
    )
    records = rollback.get("command_records")
    if not isinstance(records, list) or [item.get("operation") for item in records] != list(operations):
        raise ReleaseMatrixError("release proof command evidence matrix is incomplete")
    release_run_id = release_run_id or str(rollback.get("release_run_id") or "")
    if not release_run_id or rollback.get("release_run_id") != release_run_id:
        raise ReleaseMatrixError("release proof command evidence run binding is invalid")
    evidence_root = evidence_root or (
        repo_root / "docs" / "validation" / "external-action-evidence" / release_run_id
    )
    command_root = (evidence_root / "commands").resolve()
    results: dict[str, Any] = {}
    previous_finished_at = ""
    for sequence, item in enumerate(records, start=1):
        ref = item.get("record_ref")
        if not isinstance(ref, str):
            raise ReleaseMatrixError("release proof command evidence reference is invalid")
        path = (repo_root / ref).resolve(strict=False)
        expected_name = f"{sequence:02d}-{item['operation']}.json"
        if (
            not path.is_relative_to(command_root)
            or path.name != expected_name
            or not path.is_file()
        ):
            raise ReleaseMatrixError("release proof command evidence is unavailable or escaped")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != item.get("record_sha256"):
            raise ReleaseMatrixError("release proof command evidence digest is invalid")
        try:
            record = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ReleaseMatrixError("release proof command evidence is malformed") from exc
        claimed = dict(record)
        claimed_hash = claimed.pop("content_sha256", None)
        if (
            record.get("schema") != "saga.external-action.command-evidence.v2"
            or record.get("source_head") != source_head
            or record.get("release_run_id") != release_run_id
            or record.get("sequence") != sequence
            or record.get("operation") != item.get("operation")
            or claimed_hash != _sha256_json(claimed)
        ):
            raise ReleaseMatrixError("release proof command evidence binding is invalid")
        for field in ("started_at", "finished_at", "cwd", "stdout_sha256", "stderr_sha256"):
            if not isinstance(record.get(field), str) or not record[field]:
                raise ReleaseMatrixError("release proof command evidence metadata is invalid")
        if record["started_at"] > record["finished_at"] or (
            previous_finished_at and previous_finished_at > record["started_at"]
        ):
            raise ReleaseMatrixError("release proof command evidence chronology is invalid")
        previous_finished_at = record["finished_at"]
        if (
            not isinstance(record.get("argv"), list)
            or not isinstance(record.get("exit_code"), int)
            or record["exit_code"] != 0
            or not isinstance(record.get("stdout_bytes"), int)
            or record["stdout_bytes"] < 0
            or not isinstance(record.get("stderr_bytes"), int)
            or record["stderr_bytes"] < 0
            or not isinstance(record.get("semantics"), Mapping)
            or record.get("parse_error") is not None
        ):
            raise ReleaseMatrixError("release proof command evidence execution is invalid")
        _validate_command_semantics(record, operation=str(item["operation"]))
        results[str(item["operation"])] = record.get("result")
    if results["prior-list"] != results["restored-list"]:
        raise ReleaseMatrixError("release proof plugin state was not restored")
    if "$CODEX_HOME/" not in str(results["saga-install"].get("installedPath", "")):
        raise ReleaseMatrixError("release proof Saga install path is invalid")
    if "$CODEX_HOME/" not in str(results["fleet-install"].get("installedPath", "")):
        raise ReleaseMatrixError("release proof fleet install path is invalid")
    installed = json.dumps(results["installed-list"], sort_keys=True)
    if "saga" not in installed or "fleet-core" not in installed:
        raise ReleaseMatrixError("release proof installed plugin readback is incomplete")
    probe = results["fresh-session-probe"]
    required_operations = {
        "prepare_bundle",
        "approve_bundle",
        "execute_bundle",
        "load_action",
        "interrupt_action",
        "retry_action",
        "adjudicate_artifact",
        "adjudicate_opinion",
        "consume",
    }
    if (
        not isinstance(probe, dict)
        or probe.get("schema") != "saga.external-action.probe.v1"
        or set(probe.get("operations", [])) != required_operations
    ):
        raise ReleaseMatrixError("release proof fresh-session probe is invalid")
    result_hash_fields = {
        "marketplace_add_sha256": "marketplace-add",
        "install_receipt_sha256": "saga-install",
        "fleet_install_sha256": "fleet-install",
        "remove_receipt_sha256": "saga-remove",
        "fleet_remove_sha256": "fleet-remove",
        "marketplace_remove_sha256": "marketplace-remove",
        "fresh_session_sha256": "fresh-session-probe",
    }
    for field, operation in result_hash_fields.items():
        if rollback.get(field) != _sha256_json(results[operation]):
            raise ReleaseMatrixError(f"release proof rollback {field} binding is invalid")


def _validate_command_semantics(record: Mapping[str, Any], *, operation: str) -> None:
    argv = record["argv"]
    semantics = record["semantics"]
    expected_argv = {
        "prior-list": ["codex", "plugin", "list", "--json"],
        "marketplace-add": ["codex", "plugin", "marketplace", "add", "$MARKETPLACE", "--json"],
        "fleet-install": ["codex", "plugin", "add", "fleet-core@isolated-external-action", "--json"],
        "saga-install": ["codex", "plugin", "add", "saga@isolated-external-action", "--json"],
        "installed-list": ["codex", "plugin", "list", "--json"],
        "saga-remove": ["codex", "plugin", "remove", "saga@isolated-external-action", "--json"],
        "fleet-remove": ["codex", "plugin", "remove", "fleet-core@isolated-external-action", "--json"],
        "marketplace-remove": ["codex", "plugin", "marketplace", "remove", "isolated-external-action", "--json"],
        "restored-list": ["codex", "plugin", "list", "--json"],
    }
    if operation in expected_argv and argv != expected_argv[operation]:
        raise ReleaseMatrixError("release proof command argv semantics are invalid")
    if operation == "fresh-session-probe":
        if argv[:3] != ["$PYTHON", "-I", "-c"] or not str(argv[-1]).endswith("/scripts"):
            raise ReleaseMatrixError("release proof fresh-session argv semantics are invalid")
        if semantics != {"probe": "external-action"}:
            raise ReleaseMatrixError("release proof fresh-session semantics are invalid")
        return
    if operation in {"prior-list", "restored-list"}:
        if semantics != {"list_sha256": _sha256_json(record.get("result"))}:
            raise ReleaseMatrixError("release proof list transition semantics are invalid")
        return
    if operation == "installed-list":
        if semantics != {
            "list_sha256": _sha256_json(record.get("result")),
            "required_plugins": ["fleet-core", "saga"],
        }:
            raise ReleaseMatrixError("release proof installed-list semantics are invalid")
        return
    expected_name = {
        "marketplace-add": ("marketplace_name", "isolated-external-action"),
        "marketplace-remove": ("marketplace_name", "isolated-external-action"),
        "fleet-install": ("plugin_name", "fleet-core"),
        "fleet-remove": ("plugin_name", "fleet-core"),
        "saga-install": ("plugin_name", "saga"),
        "saga-remove": ("plugin_name", "saga"),
    }.get(operation)
    if expected_name is None or semantics != {expected_name[0]: expected_name[1]}:
        raise ReleaseMatrixError("release proof command operation semantics are invalid")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--expected-ref")
    parser.add_argument("--attended", action="store_true")
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    registry = engine_registry_overlay.load_runtime_registry(args.registry, repo_root)
    if args.check:
        print(json.dumps(prerequisites(registry), indent=2, sort_keys=True))
        return 0
    if args.verify:
        try:
            proof = json.loads(Path(args.output).read_text(encoding="utf-8"))
            validate_proof(
                proof,
                repo_root=repo_root,
                expected_ref=args.expected_ref,
                proof_path=Path(args.output),
            )
        except (OSError, ValueError, ReleaseMatrixError) as exc:
            print(f"external action release proof invalid: {exc}", file=sys.stderr)
            return 1
        print(json.dumps({"status": "passed", "content_sha256": proof["content_sha256"]}))
        return 0
    if not args.attended:
        print("error: live release matrix requires --attended", file=sys.stderr)
        return 2
    try:
        proof = run_matrix(repo_root=Path(args.repo_root).resolve(), registry_path=Path(args.registry))
    except (OSError, ValueError, ReleaseMatrixError, subprocess.SubprocessError) as exc:
        print(f"external action release matrix failed: {exc}", file=sys.stderr)
        return 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": proof["status"], "content_sha256": proof["content_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
