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
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

import external_action_adapters as adapters  # noqa: E402
import external_action_contract as contract  # noqa: E402
import external_action_lifecycle as lifecycle  # noqa: E402
import external_action_policy as action_policy  # noqa: E402
import external_action_status as status_module  # noqa: E402
import external_action_store as store_module  # noqa: E402
import reconcile  # noqa: E402
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
    registry = Registry.load(registry_path)
    checks = prerequisites(registry)
    if not all((checks["claude_cli"], checks["agy_cli"], checks["ollama_key_available"])):
        raise ReleaseMatrixError("live provider prerequisites are incomplete")
    base_revision = _git(repo_root, "rev-parse", "HEAD")
    source_head = base_revision
    recorded_at = datetime.now(UTC).isoformat()
    run_id = "release-" + datetime.now(UTC).strftime("%Y%m%dt%H%M%Sz").lower()
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
        status = status_module.project(snapshot)
        if status["state"] != "consumed" or status["receipt_validity"] != "valid":
            raise ReleaseMatrixError(f"{stage}/{engine_key}: invalid terminal status card")
        if snapshot.approval is None:
            raise ReleaseMatrixError(f"{stage}/{engine_key}: consumed action has no approval")
        receipt = _complete_receipt(snapshot.events)
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
                "evidence_sha256": str(dict(outcome.detail or {}).get("artifact_sha256") or ""),
                "status_card_sha256": hashlib.sha256(
                    status_module.render(status).encode("utf-8")
                ).hexdigest(),
                "action_record_sha256": _directory_digest(preview.store.root),
            }
        )

    proof: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "recorded_at": recorded_at,
        "source_head": source_head,
        "source_worktree_sha256": _workspace_digest(repo_root),
        "status": "passed",
        "prerequisites": checks,
        "providers": sorted({item["engine_key"] for item in stages}),
        "stages": stages,
        "rollback_drill": _rollback_drill(repo_root, base_revision),
        "sanitization": {
            "credentials": False,
            "prompts_or_transcripts": False,
            "absolute_paths": False,
            "raw_receipts": False,
        },
    }
    proof["content_sha256"] = _sha256_json(proof)
    validate_proof(proof)
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


def _rollback_drill(repo_root: Path, base_revision: str) -> dict[str, Any]:
    source = repo_root / "plugins" / "saga"
    with tempfile.TemporaryDirectory(prefix="saga-isolated-install-") as directory:
        codex_home = Path(directory) / "codex-home"
        installed = codex_home / "plugins" / "saga"
        installed.mkdir(parents=True)
        (installed / "prior-state.json").write_text(
            json.dumps({"version": "prior", "base_revision": base_revision}) + "\n",
            encoding="utf-8",
        )
        prior_digest = _directory_digest(installed)
        backup = codex_home / "plugins" / "saga.rollback"
        installed.rename(backup)
        shutil.copytree(source, installed)
        candidate_digest = _directory_digest(installed)
        probe = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                (
                    "import json,sys; sys.path.insert(0,sys.argv[1]); "
                    "import external_action_runtime as r, external_action_lifecycle as l; "
                    "print(json.dumps({'prepare':callable(r.prepare),'retry':callable(r.retry),"
                    "'execute_bundle':callable(l.execute_bundle)}))"
                ),
                str(installed / "scripts"),
            ],
            check=True,
            capture_output=True,
            text=True,
            env={"PATH": os.environ.get("PATH", "")},
        )
        readback = json.loads(probe.stdout)
        shutil.rmtree(installed)
        backup.rename(installed)
        restored_digest = _directory_digest(installed)
        passed = (
            all(readback.values())
            and candidate_digest != prior_digest
            and restored_digest == prior_digest
        )
        return {
            "passed": passed,
            "base_revision": base_revision,
            "prior_installed": True,
            "candidate_installed": True,
            "fresh_session_passed": all(readback.values()),
            "restored": restored_digest == prior_digest,
            "prior_digest": prior_digest,
            "candidate_digest": candidate_digest,
            "restored_digest": restored_digest,
        }


def _workspace_digest(root: Path) -> str:
    tracked = _git(root, "ls-files", "-z").split("\0")
    digest = hashlib.sha256()
    for name in sorted(item for item in tracked if item):
        path = root / name
        digest.update(name.encode("utf-8") + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


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


def validate_proof(proof: dict[str, Any]) -> None:
    """Independently recompute the release proof's closed semantic claims."""
    expected_hash = proof.get("content_sha256")
    unhashed = dict(proof)
    unhashed.pop("content_sha256", None)
    if expected_hash != _sha256_json(unhashed):
        raise ReleaseMatrixError("release proof content_sha256 is invalid")
    if proof.get("status") != "passed" or proof.get("schema_version") != SCHEMA_VERSION:
        raise ReleaseMatrixError("release proof status or schema is invalid")
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
        ):
            value = observed.get(field)
            if not isinstance(value, str) or len(value) != 64:
                raise ReleaseMatrixError(f"release proof {stage}.{field} is invalid")
    rollback = proof.get("rollback_drill")
    if not isinstance(rollback, dict) or not all(
        rollback.get(field) is True
        for field in (
            "passed",
            "prior_installed",
            "candidate_installed",
            "fresh_session_passed",
            "restored",
        )
    ):
        raise ReleaseMatrixError("release proof rollback drill is incomplete")
    if proof.get("sanitization") != {
        "credentials": False,
        "prompts_or_transcripts": False,
        "absolute_paths": False,
        "raw_receipts": False,
    }:
        raise ReleaseMatrixError("release proof sanitization claims are invalid")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--attended", action="store_true")
    args = parser.parse_args(argv)
    registry = Registry.load(args.registry)
    if args.check:
        print(json.dumps(prerequisites(registry), indent=2, sort_keys=True))
        return 0
    if args.verify:
        try:
            proof = json.loads(Path(args.output).read_text(encoding="utf-8"))
            validate_proof(proof)
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
