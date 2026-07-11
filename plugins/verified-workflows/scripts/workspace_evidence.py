"""Git, subject, workspace-snapshot, and mutation-audit evidence."""

from __future__ import annotations

from protected_store import (
    Any,
    DispatchReceiptError,
    GIT_OID,
    HEX64,
    MAX_AUDIT_BYTES,
    MAX_AUDIT_FILES,
    MAX_SUBJECT_BYTES,
    MAX_SUBJECT_FILES,
    MAX_SUBJECT_PATHS,
    MAX_SUBJECT_PATH_BYTES,
    Mapping,
    Path,
    PurePosixPath,
    _canonical_bytes,
    _parse_time,
    _sha256,
    _timestamp_now,
    dispatch,
    hashlib,
    hook_receipt,
    load_protected_record,
    os,
    persist_protected_record,
    re,
    stat,
    subprocess,
)

def _subject_path(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value.encode("utf-8")) > 255
        or value.startswith("/")
        or any(ord(character) < 32 for character in value)
    ):
        raise DispatchReceiptError("subject path is not a safe repository-relative path")
    parsed = PurePosixPath(value)
    if any(part in {"", ".", ".."} for part in parsed.parts):
        raise DispatchReceiptError("subject path is not a safe repository-relative path")
    normalized = parsed.as_posix()
    if (
        normalized != value
        or parsed.parts[0].casefold() == ".git"
    ):
        raise DispatchReceiptError("subject path is not a safe repository-relative path")
    return normalized


def _git_control_file_identity(
    workspace_root: Path,
    git_path_name: str,
    where: str,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(workspace_root),
                "rev-parse",
                "--git-path",
                git_path_name,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        raw_path = completed.stdout.decode("utf-8").strip()
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError) as exc:
        raise DispatchReceiptError(
            f"workflow run requires a readable Git {where} path"
        ) from exc
    if not raw_path or len(raw_path) > 4096:
        raise DispatchReceiptError(f"workflow run Git {where} path is invalid")
    control_path = Path(raw_path)
    if not control_path.is_absolute():
        control_path = workspace_root / control_path
    try:
        hook_receipt._assert_no_symlink_components(control_path.parent)
        resolved_parent = control_path.parent.resolve(strict=True)
        git_dir = Path(
            subprocess.run(
                ["git", "-C", str(workspace_root), "rev-parse", "--absolute-git-dir"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            ).stdout.decode("utf-8").strip()
        ).resolve(strict=True)
        resolved_parent.relative_to(git_dir)
        metadata = control_path.lstat()
    except FileNotFoundError:
        return {"state": "missing", "mode": None, "sha256": None, "size": 0}
    except (
        hook_receipt.AgentReceiptError,
        OSError,
        subprocess.SubprocessError,
        UnicodeDecodeError,
        ValueError,
    ) as exc:
        raise DispatchReceiptError(
            f"workflow run Git {where} is missing or unsafe"
        ) from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise DispatchReceiptError(
            f"workflow run Git {where} must be a regular file"
        )
    try:
        content = hook_receipt._read_regular(
            control_path, f"workflow run Git {where}", MAX_AUDIT_BYTES
        )
    except hook_receipt.AgentReceiptError as exc:
        raise DispatchReceiptError(f"workflow run Git {where} is unreadable") from exc
    return {
        "state": "file",
        "mode": stat.S_IMODE(metadata.st_mode),
        "sha256": _sha256(content),
        "size": len(content),
    }


def _git_index_identity(workspace_root: Path) -> dict[str, Any]:
    return _git_control_file_identity(workspace_root, "index", "index")


def _git_head_identity(workspace_root: Path) -> dict[str, Any]:
    return {
        "head": _git_control_file_identity(workspace_root, "HEAD", "HEAD"),
        "head_log": _git_control_file_identity(
            workspace_root, "logs/HEAD", "HEAD log"
        ),
    }


def _valid_git_control_identity(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "state",
        "mode",
        "sha256",
        "size",
    }:
        return False
    if value["state"] == "missing":
        return value == {"state": "missing", "mode": None, "sha256": None, "size": 0}
    return bool(
        value["state"] == "file"
        and isinstance(value["mode"], int)
        and not isinstance(value["mode"], bool)
        and 0 <= value["mode"] <= 0o7777
        and isinstance(value["sha256"], str)
        and HEX64.fullmatch(value["sha256"])
        and isinstance(value["size"], int)
        and not isinstance(value["size"], bool)
        and 0 <= value["size"] <= MAX_AUDIT_BYTES
    )


def _git_scope(workspace_root: Path, base_ref: str) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}", base_ref):
        raise DispatchReceiptError("subject base revision is invalid")

    def run(*args: str) -> bytes:
        try:
            completed = subprocess.run(
                ["git", "-C", str(workspace_root), *args],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise DispatchReceiptError("subject scope requires a valid local Git worktree") from exc
        if len(completed.stdout) > MAX_SUBJECT_BYTES:
            raise DispatchReceiptError("subject Git scope exceeds the byte ceiling")
        return completed.stdout

    try:
        base_revision = run("rev-parse", "--verify", f"{base_ref}^{{commit}}").decode().strip()
        head_revision = run("rev-parse", "--verify", "HEAD^{commit}").decode().strip()
        changed = run(
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            base_revision,
            "--",
        )
        untracked = run("ls-files", "--others", "--exclude-standard", "-z")
        raw_paths = (changed + untracked).decode("utf-8").split("\0")
    except UnicodeDecodeError as exc:
        raise DispatchReceiptError("subject Git scope contains a non-UTF-8 path") from exc
    if not GIT_OID.fullmatch(base_revision) or not GIT_OID.fullmatch(head_revision):
        raise DispatchReceiptError("subject Git revisions are invalid")
    paths = sorted({_subject_path(value) for value in raw_paths if value})
    if len(paths) > MAX_SUBJECT_PATHS:
        raise DispatchReceiptError(
            f"subject Git scope exceeds {MAX_SUBJECT_PATHS} changed paths"
        )
    if sum(len(path.encode("utf-8")) for path in paths) > MAX_SUBJECT_PATH_BYTES:
        raise DispatchReceiptError("subject Git scope path bytes exceed the ceiling")
    if len(paths) != len({value.casefold() for value in paths}):
        raise DispatchReceiptError("subject Git scope has a case-insensitive collision")
    entries: list[dict[str, Any]] = []
    for path in paths:
        target = workspace_root / PurePosixPath(path)
        try:
            metadata = target.lstat()
        except FileNotFoundError:
            entries.append(
                {"path": path, "state": "missing", "mode": None, "sha256": None}
            )
            continue
        if stat.S_ISLNK(metadata.st_mode):
            content = os.readlink(target).encode()
            state_value = "symlink"
        elif stat.S_ISREG(metadata.st_mode):
            try:
                content = hook_receipt._read_regular(
                    target, f"Git scope file {path}", MAX_SUBJECT_BYTES
                )
            except hook_receipt.AgentReceiptError as exc:
                raise DispatchReceiptError(f"Git scope file {path} is unsafe") from exc
            state_value = "file"
        elif stat.S_ISDIR(metadata.st_mode):
            content = _canonical_bytes(_subject_snapshot(workspace_root, [path]))
            state_value = "directory"
        else:
            raise DispatchReceiptError(f"Git scope path {path} is unsafe")
        entries.append(
            {
                "path": path,
                "state": state_value,
                "mode": stat.S_IMODE(metadata.st_mode),
                "sha256": _sha256(content),
            }
        )
    return {
        "base_revision": base_revision,
        "head_revision": head_revision,
        "scope_sha256": _sha256(_canonical_bytes(entries)),
        "paths": paths,
        "entries": entries,
    }


def _subject_snapshot(workspace_root: Path, subject_paths: list[str]) -> dict[str, Any]:
    if not workspace_root.is_absolute():
        raise DispatchReceiptError("workspace root must be absolute")
    try:
        hook_receipt._assert_no_symlink_components(workspace_root)
        root = workspace_root.resolve(strict=True)
        root_stat = root.stat()
    except (hook_receipt.AgentReceiptError, FileNotFoundError, OSError) as exc:
        raise DispatchReceiptError("workspace root is missing or unsafe") from exc
    if not stat.S_ISDIR(root_stat.st_mode) or root_stat.st_uid != os.getuid():
        raise DispatchReceiptError("workspace root must be a user-owned directory")
    paths = [_subject_path(value) for value in subject_paths]
    if (
        not paths
        or len(paths) > MAX_SUBJECT_PATHS
        or len(paths) != len(set(paths))
        or sum(len(path.encode("utf-8")) for path in paths)
        > MAX_SUBJECT_PATH_BYTES
    ):
        raise DispatchReceiptError("subject paths must be a bounded unique list")
    if len(paths) != len({value.casefold() for value in paths}):
        raise DispatchReceiptError("subject paths contain a case-insensitive collision")
    files: dict[str, dict[str, Any]] = {}
    byte_count = 0

    def add_file(relative: str, path: Path) -> None:
        nonlocal byte_count
        relative = _subject_path(relative)
        try:
            path.resolve(strict=True).relative_to(root)
            content = hook_receipt._read_regular(
                path, f"subject file {relative}", MAX_SUBJECT_BYTES
            )
        except (ValueError, hook_receipt.AgentReceiptError, OSError) as exc:
            raise DispatchReceiptError(f"subject file {relative} is unsafe") from exc
        byte_count += len(content)
        if len(files) >= MAX_SUBJECT_FILES or byte_count > MAX_SUBJECT_BYTES:
            raise DispatchReceiptError("subject snapshot exceeds its file or byte ceiling")
        entry = {
            "path": relative,
            "state": "file",
            "mode": stat.S_IMODE(path.stat().st_mode),
            "sha256": _sha256(content),
            "size": len(content),
        }
        existing = files.get(relative.casefold())
        if existing is not None and existing != entry:
            raise DispatchReceiptError("subject snapshot contains a path collision")
        files[relative.casefold()] = entry

    for relative in paths:
        target = root / PurePosixPath(relative)
        try:
            target.resolve(strict=False).relative_to(root)
            metadata = target.lstat()
        except FileNotFoundError:
            entry = {
                "path": relative,
                "state": "missing",
                "mode": None,
                "sha256": None,
                "size": 0,
            }
            existing = files.get(relative.casefold())
            if existing is not None and existing != entry:
                raise DispatchReceiptError("subject snapshot contains a path collision")
            files[relative.casefold()] = entry
            continue
        except (ValueError, OSError) as exc:
            raise DispatchReceiptError(f"subject path {relative} is unsafe") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise DispatchReceiptError(f"subject path {relative} must not be a symlink")
        if stat.S_ISREG(metadata.st_mode):
            add_file(relative, target)
            continue
        if not stat.S_ISDIR(metadata.st_mode):
            raise DispatchReceiptError(f"subject path {relative} is not a file or directory")
        for directory, directory_names, file_names in os.walk(target, followlinks=False):
            directory_path = Path(directory)
            for name in list(directory_names):
                child = directory_path / name
                if child.is_symlink():
                    raise DispatchReceiptError("subject directory contains a symlink")
            for name in sorted(file_names):
                child = directory_path / name
                if child.is_symlink():
                    raise DispatchReceiptError("subject directory contains a symlink")
                child_relative = child.relative_to(root).as_posix()
                add_file(child_relative, child)
    ordered_files = sorted(files.values(), key=lambda item: item["path"].casefold())
    core = {
        "repository_sha256": _sha256(str(root).encode()),
        "paths": paths,
        "files": ordered_files,
    }
    return {**core, "content_sha256": _sha256(_canonical_bytes(core))}


def _validate_git_entries(value: object, where: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > MAX_SUBJECT_PATHS:
        raise DispatchReceiptError(f"{where} must be a bounded list")
    entries: list[dict[str, Any]] = []
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != {
            "path",
            "state",
            "mode",
            "sha256",
        }:
            raise DispatchReceiptError(f"{where} fields are not closed")
        path = _subject_path(entry["path"])
        state_value = entry["state"]
        mode = entry["mode"]
        digest = entry["sha256"]
        if state_value not in {"file", "symlink", "directory", "missing"} or (
            state_value == "missing"
            and (digest is not None or mode is not None)
            or state_value != "missing"
            and (
                not isinstance(digest, str)
                or not HEX64.fullmatch(digest)
                or isinstance(mode, bool)
                or not isinstance(mode, int)
                or not 0 <= mode <= 0o7777
            )
        ):
            raise DispatchReceiptError(f"{where} entry is invalid")
        entries.append(
            {"path": path, "state": state_value, "mode": mode, "sha256": digest}
        )
    if entries != sorted(entries, key=lambda item: item["path"]):
        raise DispatchReceiptError(f"{where} must be sorted")
    if len(entries) != len({entry["path"].casefold() for entry in entries}):
        raise DispatchReceiptError(f"{where} contains a path collision")
    return entries


def _create_git_baseline_record(
    plugin_data: Path,
    scope: Mapping[str, Any],
    *,
    repository_sha256: str,
    created_at: str,
) -> str:
    reference = persist_protected_record(
        plugin_data,
        {
            "schema_version": 1,
            "record_type": "git-baseline",
            "repository_sha256": repository_sha256,
            "base_revision": scope["base_revision"],
            "head_revision": scope["head_revision"],
            "entries": scope["entries"],
            "scope_sha256": scope["scope_sha256"],
            "created_at": created_at,
        },
    )
    _load_git_baseline_record(plugin_data, reference)
    return reference


def _load_git_baseline_record(
    plugin_data: Path,
    reference: str,
) -> tuple[dict[str, Any], bytes]:
    record, content = load_protected_record(plugin_data, reference, "git-baseline")
    if set(record) != {
        "schema_version",
        "record_type",
        "repository_sha256",
        "base_revision",
        "head_revision",
        "entries",
        "scope_sha256",
        "created_at",
    }:
        raise DispatchReceiptError("Git baseline fields are not closed")
    entries = _validate_git_entries(record["entries"], "Git baseline entries")
    if (
        not isinstance(record["repository_sha256"], str)
        or not HEX64.fullmatch(record["repository_sha256"])
        or not isinstance(record["base_revision"], str)
        or not GIT_OID.fullmatch(record["base_revision"])
        or not isinstance(record["head_revision"], str)
        or not GIT_OID.fullmatch(record["head_revision"])
        or record["scope_sha256"] != _sha256(_canonical_bytes(entries))
    ):
        raise DispatchReceiptError("Git baseline identity is invalid")
    _parse_time(record["created_at"], "Git baseline.created_at")
    return record, content


def _scope_delta(
    baseline_entries: list[dict[str, Any]],
    current_entries: list[dict[str, Any]],
) -> list[str]:
    baseline = {entry["path"]: entry for entry in baseline_entries}
    current = {entry["path"]: entry for entry in current_entries}
    return sorted(
        path
        for path in set(baseline) | set(current)
        if baseline.get(path) != current.get(path)
    )


def _scope_covers(authorized_paths: list[str], delta_paths: list[str]) -> bool:
    return all(
        any(path == allowed or path.startswith(allowed.rstrip("/") + "/") for allowed in authorized_paths)
        for path in delta_paths
    )


def create_workflow_run_record(
    plugin_data: Path,
    workflow: dispatch.Workflow,
    *,
    workspace_root: Path,
    created_at: str,
    nonce: str,
) -> str:
    _assert_plugin_data_outside_workspace(plugin_data, workspace_root)
    scope = _git_scope(workspace_root, "HEAD")
    if scope["base_revision"] != scope["head_revision"]:
        raise DispatchReceiptError("workflow run must start from the current HEAD")
    _parse_time(created_at, "workflow run.created_at")
    if not re.fullmatch(r"[0-9a-f]{32}", nonce):
        raise DispatchReceiptError("workflow run nonce is invalid")
    repository_sha256 = _sha256(str(workspace_root.resolve(strict=True)).encode())
    baseline_ref = _create_git_baseline_record(
        plugin_data,
        scope,
        repository_sha256=repository_sha256,
        created_at=created_at,
    )
    baseline, baseline_bytes = _load_git_baseline_record(plugin_data, baseline_ref)
    snapshot_ref = create_workspace_snapshot_record(
        plugin_data,
        workspace_root=workspace_root,
        created_at=created_at,
    )
    snapshot, snapshot_bytes = _load_workspace_snapshot_record(
        plugin_data, snapshot_ref
    )
    initial_index = _git_index_identity(workspace_root)
    initial_head = _git_head_identity(workspace_root)
    reference = persist_protected_record(
        plugin_data,
        {
            "schema_version": 1,
            "record_type": "workflow-run",
            "workflow_sha256": workflow.sha256,
            "repository_sha256": repository_sha256,
            "base_revision": scope["base_revision"],
            "head_revision": scope["head_revision"],
            "baseline_ref": baseline_ref,
            "baseline_sha256": _sha256(baseline_bytes),
            "git_scope_sha256": baseline["scope_sha256"],
            "initial_snapshot_ref": snapshot_ref,
            "initial_snapshot_sha256": _sha256(snapshot_bytes),
            "initial_tree_sha256": snapshot["tree_sha256"],
            "initial_git_control_sha256": snapshot["git_control_sha256"],
            "initial_index": initial_index,
            "initial_head": initial_head,
            "run_nonce": nonce,
            "git_mutation_policy": "no-commit-checkout-or-index-change-until-final-gate",
            "created_at": created_at,
        },
    )
    _load_workflow_run_record(
        plugin_data,
        reference,
        workflow=workflow,
        workspace_root=workspace_root,
    )
    return reference


def _load_workflow_run_record(
    plugin_data: Path,
    reference: str,
    *,
    workflow: dispatch.Workflow | None = None,
    workspace_root: Path | None = None,
    require_pristine: bool = False,
    enforce_git_policy: bool = False,
) -> tuple[dict[str, Any], bytes]:
    record, content = load_protected_record(plugin_data, reference, "workflow-run")
    if set(record) != {
        "schema_version",
        "record_type",
        "workflow_sha256",
        "repository_sha256",
        "base_revision",
        "head_revision",
        "baseline_ref",
        "baseline_sha256",
        "git_scope_sha256",
        "initial_snapshot_ref",
        "initial_snapshot_sha256",
        "initial_tree_sha256",
        "initial_git_control_sha256",
        "initial_index",
        "initial_head",
        "run_nonce",
        "git_mutation_policy",
        "created_at",
    }:
        raise DispatchReceiptError("workflow run fields are not closed")
    baseline, baseline_bytes = _load_git_baseline_record(
        plugin_data, record["baseline_ref"]
    )
    snapshot, snapshot_bytes = _load_workspace_snapshot_record(
        plugin_data, record["initial_snapshot_ref"]
    )
    initial_index = record["initial_index"]
    initial_head = record["initial_head"]
    if (
        not isinstance(record["workflow_sha256"], str)
        or not HEX64.fullmatch(record["workflow_sha256"])
        or not isinstance(record["repository_sha256"], str)
        or not HEX64.fullmatch(record["repository_sha256"])
        or not isinstance(record["base_revision"], str)
        or not GIT_OID.fullmatch(record["base_revision"])
        or record["head_revision"] != record["base_revision"]
        or record["baseline_sha256"] != _sha256(baseline_bytes)
        or baseline["repository_sha256"] != record["repository_sha256"]
        or baseline["base_revision"] != record["base_revision"]
        or baseline["head_revision"] != record["head_revision"]
        or record["git_scope_sha256"] != baseline["scope_sha256"]
        or record["initial_snapshot_sha256"] != _sha256(snapshot_bytes)
        or snapshot["repository_sha256"] != record["repository_sha256"]
        or record["initial_tree_sha256"] != snapshot["tree_sha256"]
        or record["initial_git_control_sha256"] != snapshot["git_control_sha256"]
        or not _valid_git_control_identity(initial_index)
        or not isinstance(initial_head, dict)
        or set(initial_head) != {"head", "head_log"}
        or not _valid_git_control_identity(initial_head["head"])
        or not _valid_git_control_identity(initial_head["head_log"])
        or not isinstance(record["run_nonce"], str)
        or not re.fullmatch(r"[0-9a-f]{32}", record["run_nonce"])
        or record["git_mutation_policy"]
        != "no-commit-checkout-or-index-change-until-final-gate"
    ):
        raise DispatchReceiptError("workflow run identity is invalid")
    _parse_time(record["created_at"], "workflow run.created_at")
    if workflow is not None and record["workflow_sha256"] != workflow.sha256:
        raise DispatchReceiptError("workflow run belongs to another workflow")
    if workspace_root is not None:
        _assert_plugin_data_outside_workspace(plugin_data, workspace_root)
        scope = _git_scope(workspace_root, record["base_revision"])
        if (
            scope["head_revision"] != record["head_revision"]
            or _sha256(str(workspace_root.resolve(strict=True)).encode())
            != record["repository_sha256"]
        ):
            raise DispatchReceiptError("workflow run Git identity changed")
        if require_pristine:
            if scope["scope_sha256"] != record["git_scope_sha256"]:
                raise DispatchReceiptError(
                    "workflow run Git scope changed before the initial subject"
                )
            _load_workspace_snapshot_record(
                plugin_data,
                record["initial_snapshot_ref"],
                workspace_root=workspace_root,
            )
        if enforce_git_policy and _git_index_identity(workspace_root) != initial_index:
            raise DispatchReceiptError(
                "workflow run Git index changed before the final gate"
            )
        if enforce_git_policy and _git_head_identity(workspace_root) != initial_head:
            raise DispatchReceiptError(
                "workflow run Git HEAD controls changed before the final gate"
            )
        if (
            enforce_git_policy
            and _git_control_snapshot(workspace_root)["git_control_sha256"]
            != record["initial_git_control_sha256"]
        ):
            raise DispatchReceiptError(
                "workflow run Git controls changed before the final gate"
            )
    return record, content


def create_subject_record(
    plugin_data: Path,
    *,
    workspace_root: Path,
    subject_paths: list[str],
    workflow_run_ref: str,
    parent_refs: list[str] | None = None,
    created_at: str | None = None,
) -> str:
    normalized_parents = tuple(parent_refs or ())
    workflow_run, workflow_run_bytes = _load_workflow_run_record(
        plugin_data,
        workflow_run_ref,
        workspace_root=workspace_root,
        require_pristine=not normalized_parents,
    )
    scope = _git_scope(workspace_root, workflow_run["base_revision"])
    normalized_paths = sorted(_subject_path(value) for value in subject_paths)
    if (
        not normalized_paths
        or len(normalized_paths) > MAX_SUBJECT_PATHS
        or sum(len(path.encode("utf-8")) for path in normalized_paths)
        > MAX_SUBJECT_PATH_BYTES
        or len(normalized_paths) != len(set(normalized_paths))
        or len(normalized_paths) != len({value.casefold() for value in normalized_paths})
    ):
        raise DispatchReceiptError(
            f"authorized subject scope must contain 1-{MAX_SUBJECT_PATHS} unique bounded paths"
        )
    outside_scope_workspace_sha256 = _sha256(
        _canonical_bytes(
            _workspace_snapshot(
                workspace_root,
                excluded_paths=tuple(normalized_paths),
            )
        )
    )
    created_at = created_at or _timestamp_now()
    subject_created_at = _parse_time(created_at, "subject.created_at")
    if subject_created_at < _parse_time(
        workflow_run["created_at"], "workflow run.created_at"
    ):
        raise DispatchReceiptError("subject predates its workflow run")
    snapshot = _subject_snapshot(workspace_root, normalized_paths)
    if len(normalized_parents) != len(set(normalized_parents)):
        raise DispatchReceiptError("subject parent references contain duplicates")
    parents: list[dict[str, Any]] = []
    for parent_ref in normalized_parents:
        parent, _parent_bytes = _load_subject_record(plugin_data, parent_ref)
        parents.append(parent)
        if (
            parent["repository_sha256"] != snapshot["repository_sha256"]
            or parent["paths"] != snapshot["paths"]
            or parent["workflow_run_ref"] != workflow_run_ref
            or parent["base_revision"] != scope["base_revision"]
            or parent["head_revision"] != scope["head_revision"]
            or parent["outside_scope_workspace_sha256"]
            != outside_scope_workspace_sha256
        ):
            raise DispatchReceiptError(
                "subject parent changes repository, scope, or outside-scope workspace"
            )
    if parents:
        baseline_ref = parents[0]["baseline_ref"]
        if any(parent["baseline_ref"] != baseline_ref for parent in parents):
            raise DispatchReceiptError("subject parents use different Git baselines")
    else:
        baseline_ref = workflow_run["baseline_ref"]
    baseline, baseline_bytes = _load_git_baseline_record(plugin_data, baseline_ref)
    delta_paths = _scope_delta(baseline["entries"], scope["entries"])
    if not _scope_covers(normalized_paths, delta_paths):
        raise DispatchReceiptError("Git changes escape the authorized subject scope")
    reference = persist_protected_record(
        plugin_data,
        {
            "schema_version": 1,
            "record_type": "subject",
            **snapshot,
            "workflow_run_ref": workflow_run_ref,
            "workflow_run_sha256": _sha256(workflow_run_bytes),
            "base_revision": scope["base_revision"],
            "head_revision": scope["head_revision"],
            "baseline_ref": baseline_ref,
            "baseline_sha256": _sha256(baseline_bytes),
            "git_entries": scope["entries"],
            "git_scope_sha256": scope["scope_sha256"],
            "delta_paths": delta_paths,
            "delta_sha256": _sha256(_canonical_bytes(delta_paths)),
            "outside_scope_workspace_sha256": outside_scope_workspace_sha256,
            "parent_refs": list(normalized_parents),
            "created_at": created_at,
        },
    )
    _load_subject_record(plugin_data, reference)
    return reference


def _load_subject_record(
    plugin_data: Path,
    reference: str,
    *,
    workspace_root: Path | None = None,
) -> tuple[dict[str, Any], bytes]:
    record, content = load_protected_record(plugin_data, reference, "subject")
    if set(record) != {
        "schema_version",
        "record_type",
        "repository_sha256",
        "workflow_run_ref",
        "workflow_run_sha256",
        "paths",
        "files",
        "content_sha256",
        "base_revision",
        "head_revision",
        "baseline_ref",
        "baseline_sha256",
        "git_entries",
        "git_scope_sha256",
        "delta_paths",
        "delta_sha256",
        "outside_scope_workspace_sha256",
        "parent_refs",
        "created_at",
    }:
        raise DispatchReceiptError("subject record fields are not closed")
    paths = record["paths"]
    files = record["files"]
    parent_refs = record["parent_refs"]
    delta_paths = record["delta_paths"]
    git_entries = _validate_git_entries(record["git_entries"], "subject Git entries")
    workflow_run, workflow_run_bytes = _load_workflow_run_record(
        plugin_data, record["workflow_run_ref"]
    )
    if (
        not isinstance(paths, list)
        or [_subject_path(value) for value in paths] != paths
        or len(paths) != len(set(paths))
        or not isinstance(files, list)
        or len(files) > MAX_SUBJECT_FILES
        or not isinstance(parent_refs, list)
        or len(parent_refs) > 128
        or len(parent_refs) != len(set(parent_refs))
        or not isinstance(delta_paths, list)
        or [_subject_path(value) for value in delta_paths] != delta_paths
        or delta_paths != sorted(set(delta_paths))
    ):
        raise DispatchReceiptError("subject record paths are invalid")
    normalized_files: list[dict[str, Any]] = []
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {
            "path",
            "state",
            "mode",
            "sha256",
            "size",
        }:
            raise DispatchReceiptError("subject file fields are not closed")
        path = _subject_path(entry["path"])
        state_value = entry["state"]
        mode = entry["mode"]
        size = entry["size"]
        if (
            state_value not in {"file", "missing"}
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or (
                state_value == "file"
                and (
                    isinstance(mode, bool)
                    or not isinstance(mode, int)
                    or not 0 <= mode <= 0o7777
                )
            )
            or (
                state_value == "file"
                and (
                    not isinstance(entry["sha256"], str)
                    or not HEX64.fullmatch(entry["sha256"])
                )
            )
            or (
                state_value == "missing"
                and (mode is not None or entry["sha256"] is not None or size != 0)
            )
        ):
            raise DispatchReceiptError("subject file entry is invalid")
        normalized_files.append({**entry, "path": path})
    core = {
        "repository_sha256": record["repository_sha256"],
        "paths": paths,
        "files": normalized_files,
    }
    if (
        not isinstance(record["repository_sha256"], str)
        or not HEX64.fullmatch(record["repository_sha256"])
        or record["workflow_run_sha256"] != _sha256(workflow_run_bytes)
        or workflow_run["repository_sha256"] != record["repository_sha256"]
        or record["content_sha256"] != _sha256(_canonical_bytes(core))
    ):
        raise DispatchReceiptError("subject record content digest is invalid")
    if (
        not isinstance(record["base_revision"], str)
        or not GIT_OID.fullmatch(record["base_revision"])
        or not isinstance(record["head_revision"], str)
        or not GIT_OID.fullmatch(record["head_revision"])
        or record["git_scope_sha256"] != _sha256(_canonical_bytes(git_entries))
        or record["delta_sha256"] != _sha256(_canonical_bytes(delta_paths))
        or not isinstance(record["outside_scope_workspace_sha256"], str)
        or not HEX64.fullmatch(record["outside_scope_workspace_sha256"])
    ):
        raise DispatchReceiptError("subject Git scope binding is invalid")
    baseline, baseline_bytes = _load_git_baseline_record(
        plugin_data, record["baseline_ref"]
    )
    if (
        record["baseline_sha256"] != _sha256(baseline_bytes)
        or baseline["repository_sha256"] != record["repository_sha256"]
        or baseline["base_revision"] != record["base_revision"]
        or baseline["head_revision"] != record["head_revision"]
        or delta_paths != _scope_delta(baseline["entries"], git_entries)
        or not _scope_covers(paths, delta_paths)
    ):
        raise DispatchReceiptError("subject Git baseline binding is invalid")
    subject_created_at = _parse_time(record["created_at"], "subject.created_at")
    if subject_created_at < _parse_time(
        workflow_run["created_at"], "workflow run.created_at"
    ):
        raise DispatchReceiptError("subject predates its workflow run")
    for parent_ref in parent_refs:
        parent, _parent_bytes = _load_subject_record(plugin_data, parent_ref)
        if (
            parent["repository_sha256"] != record["repository_sha256"]
            or parent["paths"] != paths
            or parent["workflow_run_ref"] != record["workflow_run_ref"]
            or parent["base_revision"] != record["base_revision"]
            or parent["head_revision"] != record["head_revision"]
            or parent["baseline_ref"] != record["baseline_ref"]
            or parent["outside_scope_workspace_sha256"]
            != record["outside_scope_workspace_sha256"]
        ):
            raise DispatchReceiptError("subject parent changes repository or scope")
    if workspace_root is not None:
        _load_workflow_run_record(
            plugin_data,
            record["workflow_run_ref"],
            workspace_root=workspace_root,
        )
        current_scope = _git_scope(workspace_root, record["base_revision"])
        current_delta = _scope_delta(baseline["entries"], current_scope["entries"])
        if (
            current_scope["head_revision"] != record["head_revision"]
            or current_scope["scope_sha256"] != record["git_scope_sha256"]
            or current_delta != delta_paths
            or not _scope_covers(paths, current_delta)
        ):
            raise DispatchReceiptError("subject Git change scope changed after execution")
        current = _subject_snapshot(workspace_root, list(paths))
        if current != {**core, "content_sha256": record["content_sha256"]}:
            raise DispatchReceiptError("subject content changed after evidence was recorded")
        current_outside_scope_sha256 = _sha256(
            _canonical_bytes(
                _workspace_snapshot(
                    workspace_root,
                    excluded_paths=tuple(paths),
                )
            )
        )
        if current_outside_scope_sha256 != record["outside_scope_workspace_sha256"]:
            raise DispatchReceiptError(
                "workspace outside the authorized subject scope changed"
            )
    return record, content


AUDIT_EXCLUSIONS = (".git",)
GIT_CONTROL_DIRECTORIES = (
    "hooks",
    "info",
    "logs",
    "refs",
    "rebase-apply",
    "rebase-merge",
    "sequencer",
)


def _git_control_snapshot(workspace_root: Path) -> dict[str, Any]:
    def git_path(*args: str) -> Path:
        try:
            completed = subprocess.run(
                ["git", "-C", str(workspace_root), "rev-parse", *args],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise DispatchReceiptError(
                "workspace audit requires a valid local Git worktree"
            ) from exc
        if len(completed.stdout) > 4096:
            raise DispatchReceiptError("Git control path output is oversized")
        try:
            value = completed.stdout.decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise DispatchReceiptError("Git control path is not UTF-8") from exc
        path = Path(value)
        if not path.is_absolute():
            path = workspace_root / path
        try:
            hook_receipt._assert_no_symlink_components(path)
            resolved = path.resolve(strict=True)
            metadata = resolved.stat()
        except (hook_receipt.AgentReceiptError, FileNotFoundError, OSError) as exc:
            raise DispatchReceiptError("Git control path is missing or unsafe") from exc
        if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise DispatchReceiptError("Git control path must be a user-owned directory")
        return resolved

    roots: list[tuple[str, Path]] = []
    for label, path in (
        ("git-dir", git_path("--absolute-git-dir")),
        ("common-dir", git_path("--path-format=absolute", "--git-common-dir")),
    ):
        if path not in {existing for _existing_label, existing in roots}:
            roots.append((label, path))

    entries: list[dict[str, Any]] = []
    byte_count = 0
    metadata_item_count = 0

    def add_entry(label: str, root: Path, path: Path) -> None:
        nonlocal byte_count
        relative = path.relative_to(root).as_posix() if path != root else "."
        metadata = path.lstat()
        if stat.S_ISDIR(metadata.st_mode):
            kind = "directory"
            content = b""
            digest: str | None = None
        elif stat.S_ISLNK(metadata.st_mode):
            raise DispatchReceiptError("Git control paths must not be symlinks")
        elif stat.S_ISREG(metadata.st_mode):
            kind = "file"
            try:
                content = hook_receipt._read_regular(
                    path,
                    f"Git control file {label}/{relative}",
                    MAX_AUDIT_BYTES,
                )
            except hook_receipt.AgentReceiptError as exc:
                raise DispatchReceiptError("Git control file is unsafe") from exc
            digest = _sha256(content)
        else:
            raise DispatchReceiptError("Git control path has an unsafe file type")
        byte_count += len(content)
        entries.append(
            {
                "path": f"{label}/{relative}",
                "kind": kind,
                "mode": stat.S_IMODE(metadata.st_mode),
                "sha256": digest,
            }
        )
        if (
            len(entries) + metadata_item_count > MAX_AUDIT_FILES
            or byte_count > MAX_AUDIT_BYTES
        ):
            raise DispatchReceiptError("Git control audit exceeds its file or byte ceiling")

    def add_metadata_summary(label: str, root: Path, directory: Path) -> None:
        nonlocal byte_count, metadata_item_count
        children: list[dict[str, Any]] = []
        for child in directory.iterdir():
            metadata = child.lstat()
            if not (
                stat.S_ISREG(metadata.st_mode) or stat.S_ISDIR(metadata.st_mode)
            ):
                raise DispatchReceiptError("Git object metadata has an unsafe file type")
            item = {
                "name": child.name,
                "kind": (
                    "directory"
                    if stat.S_ISDIR(metadata.st_mode)
                        else "file"
                ),
                "mode": stat.S_IMODE(metadata.st_mode),
                "size": metadata.st_size,
                "mtime_ns": metadata.st_mtime_ns,
            }
            metadata_item_count += 1
            byte_count += len(_canonical_bytes(item))
            if (
                len(entries) + metadata_item_count > MAX_AUDIT_FILES
                or byte_count > MAX_AUDIT_BYTES
            ):
                raise DispatchReceiptError(
                    "Git object metadata exceeds its file or byte ceiling"
                )
            children.append(item)
        children.sort(key=lambda item: str(item["name"]))
        relative = directory.relative_to(root).as_posix()
        entries.append(
            {
                "path": f"{label}/{relative}/.metadata-summary",
                "kind": "metadata-summary",
                "mode": stat.S_IMODE(directory.stat().st_mode),
                "sha256": _sha256(_canonical_bytes(children)),
            }
        )
        if len(entries) + metadata_item_count > MAX_AUDIT_FILES:
            raise DispatchReceiptError("Git control audit exceeds its file ceiling")

    for label, root in roots:
        add_entry(label, root, root)
        for child in sorted(root.iterdir(), key=lambda item: item.name):
            if child.name == "objects" and child.is_dir() and not child.is_symlink():
                add_entry(label, root, child)
                for object_child in sorted(child.iterdir(), key=lambda item: item.name):
                    if object_child.name == "info":
                        for directory, directory_names, file_names in os.walk(
                            object_child, followlinks=False
                        ):
                            directory_path = Path(directory)
                            add_entry(label, root, directory_path)
                            for name in sorted(directory_names):
                                nested = directory_path / name
                                if nested.is_symlink():
                                    add_entry(label, root, nested)
                                    directory_names.remove(name)
                            for name in sorted(file_names):
                                add_entry(label, root, directory_path / name)
                    elif object_child.is_dir() and not object_child.is_symlink():
                        add_entry(label, root, object_child)
                        add_metadata_summary(label, root, object_child)
                    else:
                        add_entry(label, root, object_child)
            elif child.name in GIT_CONTROL_DIRECTORIES:
                if child.is_symlink():
                    add_entry(label, root, child)
                    continue
                for directory, directory_names, file_names in os.walk(
                    child, followlinks=False
                ):
                    directory_path = Path(directory)
                    add_entry(label, root, directory_path)
                    for name in sorted(directory_names):
                        nested = directory_path / name
                        if nested.is_symlink():
                            add_entry(label, root, nested)
                            directory_names.remove(name)
                    for name in sorted(file_names):
                        add_entry(label, root, directory_path / name)
            elif child.is_file() or child.is_symlink():
                add_entry(label, root, child)
    entries.sort(key=lambda item: item["path"])
    return {
        "git_control_sha256": _sha256(_canonical_bytes(entries)),
        "git_control_file_count": len(entries) + metadata_item_count,
        "git_control_byte_count": byte_count,
    }


def _assert_plugin_data_outside_workspace(
    plugin_data: Path,
    workspace_root: Path,
) -> None:
    try:
        data = plugin_data.resolve(strict=True)
        workspace = workspace_root.resolve(strict=True)
    except OSError as exc:
        raise DispatchReceiptError("plugin data or workspace root is missing") from exc
    if data == workspace or workspace in data.parents:
        raise DispatchReceiptError(
            "gate-authoritative plugin data must be outside the repository workspace"
        )


def _read_workspace_file(path: Path, where: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise DispatchReceiptError(f"{where} is unreadable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.getuid()
            or before.st_size > MAX_AUDIT_BYTES
        ):
            raise DispatchReceiptError(f"{where} has unsafe metadata")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        after = os.fstat(descriptor)
        if (
            len(content) != before.st_size
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        ):
            raise DispatchReceiptError(f"{where} changed while it was read")
        return content
    except OSError as exc:
        raise DispatchReceiptError(f"{where} is unreadable") from exc
    finally:
        os.close(descriptor)


def _read_workspace_file_at(
    directory_fd: int,
    name: str,
    where: str,
) -> tuple[bytes, os.stat_result]:
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except OSError as exc:
        raise DispatchReceiptError(f"{where} is unreadable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.getuid()
            or before.st_size > MAX_AUDIT_BYTES
        ):
            raise DispatchReceiptError(f"{where} has unsafe metadata")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        after = os.fstat(descriptor)
        if (
            len(content) != before.st_size
            or (
                before.st_dev,
                before.st_ino,
                before.st_nlink,
                before.st_mode,
                before.st_size,
                before.st_mtime_ns,
            )
            != (
                after.st_dev,
                after.st_ino,
                after.st_nlink,
                after.st_mode,
                after.st_size,
                after.st_mtime_ns,
            )
        ):
            raise DispatchReceiptError(f"{where} changed while it was read")
        return content, after
    finally:
        os.close(descriptor)


def _workspace_snapshot(
    workspace_root: Path,
    *,
    excluded_paths: tuple[str, ...] = (),
) -> dict[str, Any]:
    if not workspace_root.is_absolute():
        raise DispatchReceiptError("workspace root must be absolute")
    try:
        root = workspace_root.resolve(strict=True)
        root_fd = hook_receipt._open_plugin_data(root)
    except (hook_receipt.AgentReceiptError, FileNotFoundError, OSError) as exc:
        raise DispatchReceiptError("workspace root is missing or unsafe") from exc
    root_metadata = os.fstat(root_fd)
    hasher = hashlib.sha256()
    file_count = 1
    byte_count = 0
    hasher.update(
        _canonical_bytes(
            {
                "path": ".",
                "kind": "directory",
                "mode": stat.S_IMODE(root_metadata.st_mode),
                "device": root_metadata.st_dev,
                "inode": root_metadata.st_ino,
                "links": root_metadata.st_nlink,
                "sha256": None,
            }
        )
    )

    normalized_exclusions = tuple(_subject_path(value) for value in excluded_paths)

    def excluded(relative: str) -> bool:
        return any(
            relative == prefix or relative.startswith(prefix + "/")
            for prefix in AUDIT_EXCLUSIONS
        ) or any(
            relative == prefix or relative.startswith(prefix + "/")
            for prefix in normalized_exclusions
        )

    try:
        for directory, directory_names, file_names, directory_fd in os.fwalk(
            ".", topdown=True, follow_symlinks=False, dir_fd=root_fd
        ):
            relative_directory = "" if directory == "." else PurePosixPath(directory).as_posix()
            kept_directories: list[str] = []
            for name in sorted(directory_names):
                relative = f"{relative_directory}/{name}".lstrip("/")
                if excluded(relative):
                    continue
                metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if stat.S_ISLNK(metadata.st_mode):
                    content = os.readlink(name, dir_fd=directory_fd).encode()
                    kind = "symlink"
                elif stat.S_ISDIR(metadata.st_mode):
                    content = b""
                    kind = "directory"
                    kept_directories.append(name)
                else:
                    raise DispatchReceiptError(
                        f"workspace audit path {relative} is not a directory or symlink"
                    )
                hasher.update(
                    _canonical_bytes(
                        {
                            "path": relative,
                            "kind": kind,
                            "mode": stat.S_IMODE(metadata.st_mode),
                            "device": metadata.st_dev,
                            "inode": metadata.st_ino,
                            "links": metadata.st_nlink,
                            "sha256": _sha256(content) if kind == "symlink" else None,
                        }
                    )
                )
                file_count += 1
                byte_count += len(content)
                if file_count > MAX_AUDIT_FILES or byte_count > MAX_AUDIT_BYTES:
                    raise DispatchReceiptError("workspace audit exceeds its file or byte ceiling")
            directory_names[:] = kept_directories
            for name in sorted(file_names):
                relative = f"{relative_directory}/{name}".lstrip("/")
                if excluded(relative):
                    continue
                metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if stat.S_ISLNK(metadata.st_mode):
                    content = os.readlink(name, dir_fd=directory_fd).encode()
                    final_metadata = os.stat(
                        name, dir_fd=directory_fd, follow_symlinks=False
                    )
                    kind = "symlink"
                elif stat.S_ISREG(metadata.st_mode):
                    content, final_metadata = _read_workspace_file_at(
                        directory_fd, name, f"workspace audit file {relative}"
                    )
                    kind = "file"
                else:
                    raise DispatchReceiptError(
                        f"workspace audit path {relative} is not a regular file or symlink"
                    )
                if (
                    metadata.st_dev,
                    metadata.st_ino,
                    metadata.st_nlink,
                    metadata.st_mode,
                ) != (
                    final_metadata.st_dev,
                    final_metadata.st_ino,
                    final_metadata.st_nlink,
                    final_metadata.st_mode,
                ):
                    raise DispatchReceiptError(
                        f"workspace audit path {relative} changed during traversal"
                    )
                file_count += 1
                byte_count += len(content)
                if file_count > MAX_AUDIT_FILES or byte_count > MAX_AUDIT_BYTES:
                    raise DispatchReceiptError("workspace audit exceeds its file or byte ceiling")
                hasher.update(
                    _canonical_bytes(
                        {
                            "path": relative,
                            "kind": kind,
                            "mode": stat.S_IMODE(final_metadata.st_mode),
                            "device": final_metadata.st_dev,
                            "inode": final_metadata.st_ino,
                            "links": final_metadata.st_nlink,
                            "sha256": _sha256(content),
                        }
                    )
                )
    finally:
        os.close(root_fd)
    return {
        "repository_sha256": _sha256(str(root).encode()),
        "tree_sha256": hasher.hexdigest(),
        "file_count": file_count,
        "byte_count": byte_count,
        "exclusions": list(AUDIT_EXCLUSIONS),
        **_git_control_snapshot(root),
    }


def create_workspace_snapshot_record(
    plugin_data: Path,
    *,
    workspace_root: Path,
    created_at: str | None = None,
) -> str:
    _assert_plugin_data_outside_workspace(plugin_data, workspace_root)
    created_at = created_at or _timestamp_now()
    _parse_time(created_at, "workspace snapshot.created_at")
    reference = persist_protected_record(
        plugin_data,
        {
            "schema_version": 1,
            "record_type": "workspace-snapshot",
            **_workspace_snapshot(workspace_root),
            "created_at": created_at,
        },
    )
    _load_workspace_snapshot_record(plugin_data, reference)
    return reference


def _load_workspace_snapshot_record(
    plugin_data: Path,
    reference: str,
    *,
    workspace_root: Path | None = None,
) -> tuple[dict[str, Any], bytes]:
    record, content = load_protected_record(
        plugin_data, reference, "workspace-snapshot"
    )
    if set(record) != {
        "schema_version",
        "record_type",
        "repository_sha256",
        "tree_sha256",
        "file_count",
        "byte_count",
        "git_control_sha256",
        "git_control_file_count",
        "git_control_byte_count",
        "exclusions",
        "created_at",
    }:
        raise DispatchReceiptError("workspace snapshot fields are not closed")
    if (
        not isinstance(record["repository_sha256"], str)
        or not HEX64.fullmatch(record["repository_sha256"])
        or not isinstance(record["tree_sha256"], str)
        or not HEX64.fullmatch(record["tree_sha256"])
        or isinstance(record["file_count"], bool)
        or not isinstance(record["file_count"], int)
        or not 0 <= record["file_count"] <= MAX_AUDIT_FILES
        or isinstance(record["byte_count"], bool)
        or not isinstance(record["byte_count"], int)
        or not 0 <= record["byte_count"] <= MAX_AUDIT_BYTES
        or not isinstance(record["git_control_sha256"], str)
        or not HEX64.fullmatch(record["git_control_sha256"])
        or isinstance(record["git_control_file_count"], bool)
        or not isinstance(record["git_control_file_count"], int)
        or not 0 <= record["git_control_file_count"] <= MAX_AUDIT_FILES
        or isinstance(record["git_control_byte_count"], bool)
        or not isinstance(record["git_control_byte_count"], int)
        or not 0 <= record["git_control_byte_count"] <= MAX_AUDIT_BYTES
        or record["exclusions"] != list(AUDIT_EXCLUSIONS)
    ):
        raise DispatchReceiptError("workspace snapshot identity is invalid")
    _parse_time(record["created_at"], "workspace snapshot.created_at")
    if workspace_root is not None:
        _assert_plugin_data_outside_workspace(plugin_data, workspace_root)
        current = _workspace_snapshot(workspace_root)
        if current != {
            "repository_sha256": record["repository_sha256"],
            "tree_sha256": record["tree_sha256"],
            "file_count": record["file_count"],
            "byte_count": record["byte_count"],
            "git_control_sha256": record["git_control_sha256"],
            "git_control_file_count": record["git_control_file_count"],
            "git_control_byte_count": record["git_control_byte_count"],
            "exclusions": record["exclusions"],
        }:
            raise DispatchReceiptError("workspace changed after the audit snapshot")
    return record, content


def create_mutation_audit_record(
    plugin_data: Path,
    *,
    before_ref: str,
    after_ref: str,
    recorded_at: str | None = None,
) -> str:
    before, _before_bytes = _load_workspace_snapshot_record(plugin_data, before_ref)
    after, _after_bytes = _load_workspace_snapshot_record(plugin_data, after_ref)
    if before["repository_sha256"] != after["repository_sha256"]:
        raise DispatchReceiptError("mutation audit snapshots belong to different repositories")
    if before_ref == after_ref or _parse_time(
        after["created_at"], "workspace snapshot.created_at"
    ) <= _parse_time(before["created_at"], "workspace snapshot.created_at"):
        raise DispatchReceiptError("mutation audit requires a fresh later snapshot")
    recorded_at = recorded_at or _timestamp_now()
    if _parse_time(recorded_at, "mutation audit.recorded_at") < _parse_time(
        after["created_at"], "workspace snapshot.created_at"
    ):
        raise DispatchReceiptError("mutation audit predates its after snapshot")
    reference = persist_protected_record(
        plugin_data,
        {
            "schema_version": 1,
            "record_type": "mutation-audit",
            "before_ref": before_ref,
            "after_ref": after_ref,
            "repository_sha256": before["repository_sha256"],
            "mutation_observed": (
                before["tree_sha256"] != after["tree_sha256"]
                or before["git_control_sha256"] != after["git_control_sha256"]
            ),
            "recorded_at": recorded_at,
        },
    )
    _load_mutation_audit_record(plugin_data, reference)
    return reference


def _load_mutation_audit_record(
    plugin_data: Path,
    reference: str,
) -> tuple[dict[str, Any], bytes]:
    record, content = load_protected_record(plugin_data, reference, "mutation-audit")
    if set(record) != {
        "schema_version",
        "record_type",
        "before_ref",
        "after_ref",
        "repository_sha256",
        "mutation_observed",
        "recorded_at",
    }:
        raise DispatchReceiptError("mutation audit fields are not closed")
    before, _before_bytes = _load_workspace_snapshot_record(
        plugin_data, record["before_ref"]
    )
    after, _after_bytes = _load_workspace_snapshot_record(
        plugin_data, record["after_ref"]
    )
    if (
        before["repository_sha256"] != after["repository_sha256"]
        or record["repository_sha256"] != before["repository_sha256"]
        or record["mutation_observed"]
        is not (
            before["tree_sha256"] != after["tree_sha256"]
            or before["git_control_sha256"] != after["git_control_sha256"]
        )
        or record["before_ref"] == record["after_ref"]
        or _parse_time(after["created_at"], "workspace snapshot.created_at")
        <= _parse_time(before["created_at"], "workspace snapshot.created_at")
    ):
        raise DispatchReceiptError("mutation audit does not bind its snapshots")
    if _parse_time(record["recorded_at"], "mutation audit.recorded_at") < _parse_time(
        after["created_at"], "workspace snapshot.created_at"
    ):
        raise DispatchReceiptError("mutation audit predates its after snapshot")
    return record, content
