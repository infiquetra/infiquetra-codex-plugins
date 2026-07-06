"""Unit tests for team-execution typed artifact pointers — Layer 1/2/3 mechanism (U8).

Ported from the upstream pointer suite, scoped to the Codex adapter: the git-object / CAS mechanism,
its security invariants, and gc — the portable core. Claude-host template/agent/saga-wiring coupling
tests are dropped (those surfaces are not ported here). Store state paths are ``.codex/`` per Codex
host truth. All git behavior runs against real scratch repos in ``tmp_path``; git is never mocked.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PLUGIN_ROOT = Path(__file__).parent.parent
SCRIPT = PLUGIN_ROOT / "scripts" / "artifact_pointer.py"
SKILL_MD = PLUGIN_ROOT / "skills" / "team-execution" / "SKILL.md"
ARTIFACT_POINTERS_DOC = (
    PLUGIN_ROOT / "skills" / "team-execution" / "references" / "artifact-pointers.md"
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load():
    spec = importlib.util.spec_from_file_location("artifact_pointer", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["artifact_pointer"] = module
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    (path / "tracked.txt").write_text("base\n", encoding="utf-8")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "initial")
    return path


def _make_ignored_codex_repo(path: Path) -> Path:
    """A scratch repo whose ``.codex/`` is git-ignored (Step B0a's safe path, Codex host truth)."""
    repo = _init_repo(path)
    (repo / ".gitignore").write_text(".codex/\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-q", "-m", "ignore .codex")
    return repo


# --- contract round-trip --------------------------------------------------------------------


def test_contract_round_trips_all_kinds() -> None:
    ap = _load()
    for kind, locator in (
        ("diff", "refs/team-execution/snapshots/run-1/0"),
        ("file", "src/app.py"),
        ("symbol", "src/app.py#handler"),
    ):
        pointer = ap.ArtifactPointer(
            kind=kind, locator=locator, hash="deadbeef", epoch="3", deref="git diff A B"
        )
        parsed = ap.ArtifactPointer.from_json(pointer.to_json())
        assert parsed == pointer
        assert parsed.kind == kind


def test_from_json_rejects_unknown_kind_and_missing_fields() -> None:
    ap = _load()
    good = {"kind": "diff", "locator": "r", "hash": "h", "epoch": "0", "deref": "git diff A B"}
    try:
        ap.ArtifactPointer.from_json(json.dumps({**good, "kind": "bogus"}))
        raise AssertionError("expected ValueError for unknown kind")
    except ValueError:
        pass
    incomplete = dict(good)
    del incomplete["hash"]
    try:
        ap.ArtifactPointer.from_json(json.dumps(incomplete))
        raise AssertionError("expected ValueError for missing field")
    except ValueError:
        pass


def test_pointer_base_field_round_trips_and_defaults_absent() -> None:
    ap = _load()
    p = ap.ArtifactPointer(
        kind="diff", locator="refs/x", hash="a" * 40, epoch="0", deref="git diff x y", base="b" * 40
    )
    assert ap.ArtifactPointer.from_json(p.to_json()).base == "b" * 40
    legacy = json.dumps(
        {
            "kind": "file",
            "locator": "objects/ab/abcd",
            "hash": "abcd",
            "epoch": "run/0",
            "deref": "x deref",
        }
    )
    assert ap.ArtifactPointer.from_json(legacy).base == ""


# --- Layer 1 (git-object diff pointers) -----------------------------------------------------


def test_snapshot_captures_staged_unstaged_untracked(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    ap = _load()

    (repo / "tracked.txt").write_text("unstaged change\n", encoding="utf-8")
    (repo / "staged.txt").write_text("staged new\n", encoding="utf-8")
    _git(repo, "add", "staged.txt")
    (repo / "untracked.txt").write_text("untracked new\n", encoding="utf-8")

    pointer = ap.snapshot("run-1", "0", repo_root=repo)
    diff = ap.deref(pointer, repo_root=repo)

    assert "unstaged change" in diff
    assert "staged new" in diff
    assert "untracked new" in diff


def test_snapshot_leaves_real_index_and_worktree_untouched(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    ap = _load()

    (repo / "tracked.txt").write_text("unstaged change\n", encoding="utf-8")
    (repo / "staged.txt").write_text("staged new\n", encoding="utf-8")
    _git(repo, "add", "staged.txt")
    (repo / "untracked.txt").write_text("untracked new\n", encoding="utf-8")

    status_before = _git(repo, "status", "--porcelain=v1")
    index_tree_before = _git(repo, "write-tree")

    ap.snapshot("run-1", "0", repo_root=repo)

    assert _git(repo, "status", "--porcelain=v1") == status_before
    assert _git(repo, "write-tree") == index_tree_before
    assert (repo / "tracked.txt").read_text(encoding="utf-8") == "unstaged change\n"


def test_holding_ref_survives_gc(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    ap = _load()

    (repo / "untracked.txt").write_text("keep me\n", encoding="utf-8")
    pointer = ap.snapshot("run-1", "0", repo_root=repo)

    _git(repo, "gc", "--prune=now")

    assert _git(repo, "cat-file", "-t", pointer.hash) == "tree"
    assert "keep me" in ap.deref(pointer, repo_root=repo)


def test_byte_drift_raises_hash_mismatch(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    ap = _load()

    (repo / "untracked.txt").write_text("original\n", encoding="utf-8")
    pointer = ap.snapshot("run-1", "0", repo_root=repo)

    other_tree = _git(repo, "rev-parse", "HEAD^{tree}")
    _git(repo, "update-ref", pointer.locator, other_tree)

    try:
        ap.deref(pointer, repo_root=repo)
        raise AssertionError("expected PointerError")
    except ap.PointerError as exc:
        assert exc.code == ap.ERR_HASH_MISMATCH


def test_superseding_epoch_raises_stale(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    ap = _load()

    (repo / "untracked.txt").write_text("epoch 0\n", encoding="utf-8")
    old_pointer = ap.snapshot("run-1", "0", repo_root=repo)

    (repo / "untracked.txt").write_text("epoch 1\n", encoding="utf-8")
    ap.snapshot("run-1", "1", repo_root=repo)

    assert _git(repo, "rev-parse", old_pointer.locator) == old_pointer.hash
    try:
        ap.deref(old_pointer, repo_root=repo)
        raise AssertionError("expected PointerError")
    except ap.PointerError as exc:
        assert exc.code == ap.ERR_STALE


def test_deref_resolves_from_linked_worktree(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    ap = _load()

    (repo / "untracked.txt").write_text("shared object\n", encoding="utf-8")
    pointer = ap.snapshot("run-1", "0", repo_root=repo)

    worktree = tmp_path / "linked"
    _git(repo, "worktree", "add", "-q", str(worktree), "HEAD")

    assert "shared object" in ap.deref(pointer, repo_root=worktree)


def test_cli_deref_prints_typed_code_to_stderr(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")

    (repo / "untracked.txt").write_text("epoch 0\n", encoding="utf-8")
    snap0 = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(repo), "snapshot", "--run", "r",
         "--epoch", "0"],
        capture_output=True, text=True, check=True,
    )
    pointer_json = snap0.stdout.strip()
    subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(repo), "snapshot", "--run", "r",
         "--epoch", "1"],
        capture_output=True, text=True, check=True,
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(repo), "deref", pointer_json],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "POINTER_STALE" in result.stderr


def test_l1_deref_ignores_tampered_deref_field_no_arbitrary_write(tmp_path: Path) -> None:
    ap = _load()
    repo = _init_repo(tmp_path / "repo")
    (repo / "new.txt").write_text("untracked payload\n", encoding="utf-8")
    pointer = ap.snapshot("run", "0", repo_root=repo)

    evil = tmp_path / "evil.txt"
    tampered = ap.ArtifactPointer(
        kind=pointer.kind,
        locator=pointer.locator,
        hash=pointer.hash,
        epoch=pointer.epoch,
        deref=f"git diff --output={evil} {pointer.base} {pointer.hash}",
        base=pointer.base,
    )
    out = ap.deref(tampered, repo_root=repo)

    assert not evil.exists()
    assert "untracked payload" in out


def test_l1_deref_rejects_non_oid_base(tmp_path: Path) -> None:
    ap = _load()
    repo = _init_repo(tmp_path / "repo")
    pointer = ap.snapshot("run", "0", repo_root=repo)
    hostile = ap.ArtifactPointer(
        kind="diff", locator=pointer.locator, hash=pointer.hash, epoch=pointer.epoch,
        deref=pointer.deref, base="--output=pwned",
    )
    try:
        ap.deref(hostile, repo_root=repo)
    except ap.PointerError as exc:
        assert exc.code == ap.ERR_HASH_MISMATCH
    else:
        raise AssertionError("expected PointerError for non-OID base")


def test_l1_deref_pins_base_across_head_movement(tmp_path: Path) -> None:
    ap = _load()
    repo = _init_repo(tmp_path / "repo")
    (repo / "snap.txt").write_text("snapshot-only content\n", encoding="utf-8")
    pointer = ap.snapshot("run", "0", repo_root=repo)

    (repo / "later.txt").write_text("post-snapshot commit\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "advance HEAD")

    out = ap.deref(pointer, repo_root=repo)
    assert "snapshot-only content" in out
    assert "post-snapshot commit" not in out


def test_l1_non_numeric_epoch_skips_freshness_enforcement(tmp_path: Path) -> None:
    ap = _load()
    repo = _init_repo(tmp_path / "repo")
    (repo / "a.txt").write_text("opaque payload\n", encoding="utf-8")
    opaque = ap.snapshot("run", "opaque", repo_root=repo)
    (repo / "b.txt").write_text("newer\n", encoding="utf-8")
    ap.snapshot("run", "99", repo_root=repo)

    assert "opaque payload" in ap.deref(opaque, repo_root=repo)


def test_l1_deref_rejects_ref_pointing_at_non_tree(tmp_path: Path) -> None:
    ap = _load()
    repo = _init_repo(tmp_path / "repo")
    (repo / "x.txt").write_text("content\n", encoding="utf-8")
    pointer = ap.snapshot("run", "0", repo_root=repo)
    blob = _git(repo, "hash-object", "-w", str(repo / "x.txt"))
    hostile = ap.ArtifactPointer(
        kind="diff", locator=pointer.locator, hash=blob, epoch=pointer.epoch,
        deref=pointer.deref, base=pointer.base,
    )
    try:
        ap.deref(hostile, repo_root=repo)
    except ap.PointerError as exc:
        assert exc.code == ap.ERR_HASH_MISMATCH
    else:
        raise AssertionError("expected HASH_MISMATCH for non-tree hash")


def test_snapshot_rejects_ref_unsafe_run_id_and_epoch(tmp_path: Path) -> None:
    ap = _load()
    repo = _init_repo(tmp_path / "repo")
    for bad in ("../evil", "a b", "run/../x"):
        try:
            ap.snapshot(bad, "0", repo_root=repo)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for unsafe run id {bad!r}")
    try:
        ap.snapshot("run", "0 1", repo_root=repo)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for unsafe epoch")


def test_snapshot_rejects_sparse_checkout_worktree(tmp_path: Path) -> None:
    ap = _load()
    repo = _init_repo(tmp_path / "repo")
    _git(repo, "config", "core.sparseCheckout", "true")
    try:
        ap.snapshot("run", "0", repo_root=repo)
    except ap.GitError as exc:
        assert "sparse" in str(exc).lower()
    else:
        raise AssertionError("expected GitError for a sparse-checkout worktree")


# --- Layer 2 (content-addressed store) ------------------------------------------------------


def test_store_write_once_dedups_identical_bytes(tmp_path: Path) -> None:
    repo = _make_ignored_codex_repo(tmp_path / "repo")
    ap = _load()

    artifact = tmp_path / "a.txt"
    artifact.write_text("same content\n", encoding="utf-8")

    p1 = ap.store("run-1", "0", artifact, repo_root=repo)
    p2 = ap.store("run-2", "5", artifact, repo_root=repo)

    assert p1.hash == p2.hash
    assert p1.locator == p2.locator
    store_root = ap.resolve_store_root(repo)
    cas_files = [f for f in (store_root / "objects").rglob("*") if f.is_file()]
    assert len(cas_files) == 1


def test_store_different_bytes_get_different_paths(tmp_path: Path) -> None:
    repo = _make_ignored_codex_repo(tmp_path / "repo")
    ap = _load()

    a = tmp_path / "a.txt"
    a.write_text("content A\n", encoding="utf-8")
    b = tmp_path / "b.txt"
    b.write_text("content B\n", encoding="utf-8")

    p1 = ap.store("run-1", "0", a, repo_root=repo)
    p2 = ap.store("run-1", "1", b, repo_root=repo)

    assert p1.hash != p2.hash
    assert p1.locator != p2.locator


def test_store_deref_round_trips_content(tmp_path: Path) -> None:
    repo = _make_ignored_codex_repo(tmp_path / "repo")
    ap = _load()

    artifact = tmp_path / "a.txt"
    artifact.write_text("stored content\n", encoding="utf-8")
    pointer = ap.store("run-1", "0", artifact, repo_root=repo)

    assert ap.deref(pointer, repo_root=repo) == "stored content\n"


def test_store_falls_back_to_home_when_codex_dir_not_ignored(tmp_path: Path, monkeypatch) -> None:
    """When ``.codex`` is NOT git-ignored, the store falls back to the home-dir namespace
    (Step B0a safety) rather than writing under the repo's ``.codex/``."""
    repo = _init_repo(tmp_path / "repo")
    ap = _load()

    fake_home = tmp_path / "fake-home"
    fake_home.mkdir()
    monkeypatch.setattr(ap.Path, "home", classmethod(lambda cls: fake_home))

    store_root = ap.resolve_store_root(repo)
    assert str(fake_home) in str(store_root)
    assert not (repo / ".codex" / "team-execution" / "artifacts").exists()


def test_tampered_stored_file_raises_hash_mismatch(tmp_path: Path) -> None:
    repo = _make_ignored_codex_repo(tmp_path / "repo")
    ap = _load()

    artifact = tmp_path / "a.txt"
    artifact.write_text("original\n", encoding="utf-8")
    pointer = ap.store("run-1", "0", artifact, repo_root=repo)

    store_root = ap.resolve_store_root(repo)
    (store_root / pointer.locator).write_text("tampered\n", encoding="utf-8")

    try:
        ap.deref(pointer, repo_root=repo)
        raise AssertionError("expected PointerError")
    except ap.PointerError as exc:
        assert exc.code == ap.ERR_HASH_MISMATCH


def test_l2_deref_rejects_path_traversal_locator(tmp_path: Path) -> None:
    repo = _make_ignored_codex_repo(tmp_path / "repo")
    ap = _load()

    secret = tmp_path / "secret.txt"
    secret.write_text("TOP SECRET\n", encoding="utf-8")
    secret_digest = hashlib.sha256(secret.read_bytes()).hexdigest()

    for locator in (str(secret), f"../../../../{secret.name}"):
        pointer = ap.ArtifactPointer(
            kind="file", locator=locator, hash=secret_digest, epoch="0", deref="cat"
        )
        try:
            ap.deref(pointer, repo_root=repo)
            raise AssertionError(f"expected PointerError for hostile locator {locator!r}")
        except ap.PointerError as exc:
            assert exc.code == ap.ERR_HASH_MISMATCH
            assert "TOP SECRET" not in exc.detail


def test_l2_deref_rejects_non_hex_hash(tmp_path: Path) -> None:
    repo = _make_ignored_codex_repo(tmp_path / "repo")
    ap = _load()

    pointer = ap.ArtifactPointer(
        kind="file", locator="objects/xx/not-a-digest", hash="not-a-digest", epoch="0", deref="cat"
    )
    try:
        ap.deref(pointer, repo_root=repo)
        raise AssertionError("expected PointerError for non-hex hash")
    except ap.PointerError as exc:
        assert exc.code == ap.ERR_HASH_MISMATCH


def test_l2_deref_rejects_symlink_in_store(tmp_path: Path) -> None:
    ap = _load()
    repo = _make_ignored_codex_repo(tmp_path / "repo")
    payload = repo / "artifact.txt"
    payload.write_text("real artifact\n", encoding="utf-8")
    pointer = ap.store("run", "0", payload, repo_root=repo)

    store_root = ap.resolve_store_root(repo)
    cas_path = store_root / pointer.locator
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP SECRET\n", encoding="utf-8")
    cas_path.unlink()
    cas_path.symlink_to(secret)
    try:
        ap.deref(pointer, repo_root=repo)
    except ap.PointerError as exc:
        assert exc.code == ap.ERR_HASH_MISMATCH
        assert "TOP SECRET" not in exc.detail
    else:
        raise AssertionError("expected symlink rejection")


def test_superseded_l2_epoch_raises_stale(tmp_path: Path) -> None:
    repo = _make_ignored_codex_repo(tmp_path / "repo")
    ap = _load()

    a0 = tmp_path / "a0.txt"
    a0.write_text("epoch 0 content\n", encoding="utf-8")
    old_pointer = ap.store("run-1", "0", a0, repo_root=repo)

    a1 = tmp_path / "a1.txt"
    a1.write_text("epoch 1 content\n", encoding="utf-8")
    ap.store("run-1", "1", a1, repo_root=repo)

    try:
        ap.deref(old_pointer, repo_root=repo)
        raise AssertionError("expected PointerError")
    except ap.PointerError as exc:
        assert exc.code == ap.ERR_STALE


# --- Layer 3 (symbol pointers) --------------------------------------------------------------


def test_deref_symbol_pointer_rejected_with_clear_message(tmp_path: Path) -> None:
    ap = _load()
    repo = _init_repo(tmp_path / "repo")
    sym = ap.ArtifactPointer(
        kind="symbol", locator="path/to/file.py#my_func", hash="", epoch="0", deref="grep -n my_func"
    )
    try:
        ap.deref(sym, repo_root=repo)
    except ValueError as exc:
        assert "grep/read" in str(exc)
    else:
        raise AssertionError("expected ValueError for symbol pointer deref")


# --- gc -------------------------------------------------------------------------------------


def _backdate_reflog_entry(reflog_path: Path, seconds_ago: float) -> None:
    old_ts = str(int(time.time() - seconds_ago))
    out = []
    for line in reflog_path.read_text(encoding="utf-8").splitlines():
        prefix, _, msg = line.partition("\t")
        parts = prefix.split()
        parts[-2] = old_ts
        out.append(" ".join(parts) + "\t" + msg)
    reflog_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def test_gc_reclaims_stale_cas_entries_and_snapshot_refs_younger_survive(tmp_path: Path) -> None:
    repo = _make_ignored_codex_repo(tmp_path / "repo")
    ap = _load()

    old_artifact = tmp_path / "old.txt"
    old_artifact.write_text("old artifact\n", encoding="utf-8")
    old_pointer = ap.store("run-old", "0", old_artifact, repo_root=repo)
    ap.snapshot("run-old", "0", repo_root=repo)

    new_artifact = tmp_path / "new.txt"
    new_artifact.write_text("new artifact\n", encoding="utf-8")
    new_pointer = ap.store("run-new", "0", new_artifact, repo_root=repo)
    new_snapshot = ap.snapshot("run-new", "0", repo_root=repo)

    store_root = ap.resolve_store_root(repo)
    old_cas_path = store_root / old_pointer.locator
    old_ref_path = repo / ".git" / "refs" / "team-execution" / "snapshots" / "run-old" / "0"
    old_reflog_path = (
        repo / ".git" / "logs" / "refs" / "team-execution" / "snapshots" / "run-old" / "0"
    )
    stale_ts = time.time() - (10 * 86400)
    os.utime(old_cas_path, (stale_ts, stale_ts))
    _backdate_reflog_entry(old_reflog_path, 10 * 86400)

    result = ap.gc(repo_root=repo, max_age_days=7)

    assert result["artifacts_removed"] == 1
    assert result["snapshot_refs_removed"] == 1
    assert not old_cas_path.exists()
    assert not old_ref_path.exists()

    assert (store_root / new_pointer.locator).exists()
    assert ap.deref(new_pointer, repo_root=repo) == "new artifact\n"
    assert _git(repo, "rev-parse", "--verify", new_snapshot.locator) == new_snapshot.hash

    index = ap._read_index(store_root)
    assert "run-old" not in index


def test_gc_dates_snapshot_refs_by_reflog_entry_surviving_real_git_gc(tmp_path: Path) -> None:
    ap = _load()
    repo = _init_repo(tmp_path / "repo")
    (repo / "old.txt").write_text("old\n", encoding="utf-8")
    ap.snapshot("run-old", "0", repo_root=repo)
    (repo / "new.txt").write_text("new\n", encoding="utf-8")
    ap.snapshot("run-new", "0", repo_root=repo)

    old_reflog = repo / ".git" / "logs" / "refs" / "team-execution" / "snapshots" / "run-old" / "0"
    _backdate_reflog_entry(old_reflog, 10 * 86400)
    _git(repo, "gc")

    result = ap.gc(repo_root=repo, max_age_days=7)
    assert result["snapshot_refs_removed"] == 1
    remaining = _git(repo, "for-each-ref", "--format=%(refname)", "refs/team-execution/snapshots/")
    assert "run-old" not in remaining
    assert "run-new" in remaining


def test_cli_store_and_gc_round_trip(tmp_path: Path) -> None:
    repo = _make_ignored_codex_repo(tmp_path / "repo")
    artifact = tmp_path / "cli.txt"
    artifact.write_text("cli content\n", encoding="utf-8")

    store_result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(repo), "store", "--run", "cli-run",
         "--epoch", "0", str(artifact)],
        capture_output=True, text=True, check=True,
    )
    pointer_json = store_result.stdout.strip()
    assert '"kind":"file"' in pointer_json

    deref_result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(repo), "deref", pointer_json],
        capture_output=True, text=True, check=True,
    )
    assert deref_result.stdout == "cli content\n"

    gc_result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(repo), "gc", "--max-age-days", "7"],
        capture_output=True, text=True, check=True,
    )
    payload = json.loads(gc_result.stdout)
    assert payload["artifacts_removed"] == 0
    assert payload["snapshot_refs_removed"] == 0


# --- doc packaging (in-scope reference wiring) ----------------------------------------------


def test_artifact_pointers_doc_is_packaged_and_linked() -> None:
    """``artifact-pointers.md`` exists and is linked from the team-execution SKILL.md."""
    assert ARTIFACT_POINTERS_DOC.exists()
    assert "artifact-pointers.md" in _read_text(SKILL_MD)


def test_artifact_pointers_doc_states_full_dereference_and_ktd7_fallback() -> None:
    doc = _read_text(ARTIFACT_POINTERS_DOC)
    assert "always dereference and read the FULL artifact" in doc
    assert "not allowed" in doc
    assert "capability-keyed" in doc
    assert "falls back to inlined content" in doc
    assert "POINTER_HASH_MISMATCH" in doc
    assert "POINTER_STALE" in doc


def test_symbol_pointers_light_form_documented_in_artifact_pointers_md() -> None:
    doc = _read_text(ARTIFACT_POINTERS_DOC)
    assert "Layer 3 — symbol pointers" in doc
    assert "<repo-relative-path>#<symbol-name>" in doc
    assert "no formal resolver" in doc
    assert "grep/read tools" in doc
