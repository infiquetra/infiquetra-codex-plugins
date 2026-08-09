#!/usr/bin/env python3
"""Offline captures of what the installed Codex binary actually offers a model.

Everything here runs against a disposable ``CODEX_HOME`` and an unauthenticated local provider.
No probe reaches OpenAI, makes a real model call, or spends quota. That is deliberate: a
capability fact that can only be learned by spending a live turn gets observed rarely and
therefore stale-ly, and this whole alignment round exists because stale observations were stored
as permanent policy.

Two captures:

``capture_feature_flags``
    ``codex features list`` reports every known feature with its stage and its effective state
    under the configuration in play. It honours ``--enable``/``--disable``, so the effective
    state can be captured under exactly the configuration a plugin ships. This is evidence of
    feature state and nothing more; it is NOT evidence about tools.

``capture_tool_specification``
    The model-visible tool specification, which is the set of tool definitions a turn is
    actually offered. Codex assembles it through ``router.model_visible_specs`` and, under
    Responses Lite, serializes it as an ``additional_tools`` developer input item while leaving
    the request's top-level ``tools`` property empty. Capturing it therefore means reading an
    outbound request body, which this module does by pointing Codex at a local Responses API
    stand-in that records what it receives and replays a fixed script.

    Two earlier candidates were rejected on evidence rather than taste. ``codex debug
    prompt-input`` renders prompt messages whose collaboration prose is present even when the
    collaboration tools are not offered, so using it as a tool-plan substitute would be worse
    than recording nothing. The app-server protocol schema carries no tool list on any thread or
    turn surface, because the specification never travels through that protocol at all.

Only a reduced projection ever leaves this module: namespaces, tool names, and a digest over the
canonical definitions. Raw request bodies carry prompts, machine identifiers, and — against a
real provider — credentials in headers. They are never returned and never written down.
"""

from __future__ import annotations

import hashlib
import json
import os
import pwd
import re
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CAPABILITY_SNAPSHOT = (
    REPO_ROOT / "docs" / "validation" / "codex-runtime-capability-snapshot.json"
)
PROBE_TIMEOUT_SECONDS = 180
MAX_PROBE_BYTES = 8 * 1024 * 1024
MAX_REQUEST_BYTES = 16 * 1024 * 1024
# `codex features list` prints fixed-width columns: name, stage, effective state.
FEATURE_ROW = re.compile(
    r"^(?P<name>[a-z0-9_]+)\s{2,}(?P<stage>[a-z ]+?)\s{2,}(?P<state>true|false)\s*$"
)
# Every stage Codex 0.147.0 reports. Kept closed on purpose: a stage this harness has never seen
# is a change in how the binary classifies its own features, which is worth failing on rather
# than silently recording.
FEATURE_STAGES = frozenset(
    {"stable", "experimental", "under development", "deprecated", "removed"}
)
MAX_PROJECTION_BYTES = 8 * 1024
# `model` and `reasoning_effort` are checked against closed sets rather than patterns. That is
# drift detection, not sanitisation: a capture reporting a model this repository has never
# recorded means the catalog moved, which is worth failing on.
SCALAR_EFFORTS = frozenset({"low", "medium", "high", "xhigh", "max", "ultra"})
SECRET_KEY = re.compile(
    r"(?i)(token|secret|password|credential|authorization|api[_-]?key|auth_json)"
)
SECRET_VALUE = re.compile(
    r"(?i)(?:\bsk-[A-Za-z0-9_-]{8,}|\bgh[pousr]_[A-Za-z0-9]{8,}|"
    r"\bBearer\s+[A-Za-z0-9._~-]{8,}|\beyJ[A-Za-z0-9_-]{8,}\."
    r"[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})"
)
# The input item that carries the specification under Responses Lite.
ADDITIONAL_TOOLS_ITEM = "additional_tools"
# Present in a request's client metadata only when the turn belongs to a spawned child.
PARENT_THREAD_METADATA_KEY = "x-codex-parent-thread-id"


class CapabilityProbeError(RuntimeError):
    """Raised when a probe cannot run, or when its result contradicts a recorded finding."""


def _codex_executable() -> str:
    found = shutil.which("codex")
    if found is None:
        raise CapabilityProbeError("the codex executable is not on PATH")
    return found


def _protected_codex_homes() -> tuple[Path, ...]:
    """Directories a probe must never touch, whatever the environment currently says.

    Three sources, all additive, because each can be redirected on its own:

    - the account's home directory read from the operating system's user database, which
      ``$HOME`` cannot move;
    - ``Path.home()``, which honours ``$HOME`` and so covers a deliberately relocated home;
    - ``CODEX_HOME``, which names whatever home is currently in use.

    Deriving the protected path from any single one of these is what let a decoy value hand the
    operator's real home to a probe.
    """

    candidates: list[Path] = []
    try:
        account_home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    except (KeyError, OSError):  # pragma: no cover - no user database entry
        account_home = None
    if account_home is not None:
        candidates.append(account_home / ".codex")
    candidates.append(Path.home() / ".codex")
    configured = os.environ.get("CODEX_HOME")
    if configured:
        candidates.append(Path(configured).expanduser())

    resolved: list[Path] = []
    for home in candidates:
        resolved.append(home)
        try:
            resolved.append(home.resolve())
        except OSError:  # pragma: no cover - unreadable path is not a probe target either
            pass
    return tuple(dict.fromkeys(resolved))


def _assert_disposable_home(codex_home: Path, where: str) -> Path:
    """Return the resolved probe home, or refuse it.

    The resolved path is what callers must hand to Codex. Passing the unresolved original would
    leave a window in which an accepted symlink is retargeted at a protected directory between
    the check and the run.

    This guard exists to stop a probe from writing into the operator's real Codex home by
    accident -- a wrong path, a stale environment variable, a symbolic link. It is an
    accident guard, not a security boundary: anything running as this user can reach that
    directory anyway.
    """

    if codex_home.is_symlink():
        raise CapabilityProbeError(
            f"{where}: a probe home must be a real directory, not a symbolic link"
        )
    if not codex_home.is_dir():
        raise CapabilityProbeError(f"{where}: the probe home {codex_home} is not a directory")
    candidate = codex_home.resolve()
    for protected in _protected_codex_homes():
        # Equality is not enough: a probe pointed inside the real home would still write there,
        # and one pointed at an ancestor would contain it.
        if (
            candidate == protected
            or protected in candidate.parents
            or candidate in protected.parents
        ):
            raise CapabilityProbeError(
                f"{where}: refusing to probe against the real Codex home or anything containing it"
            )
    return candidate


def _run(argv: Sequence[str], *, codex_home: Path, cwd: Path, where: str) -> str:
    """Run one Codex subcommand against a disposable home and return its stdout."""

    # The RESOLVED path goes to Codex. Handing it the original would leave a window in which
    # an accepted symlink is retargeted at a protected directory before the process starts.
    resolved_home = _assert_disposable_home(codex_home, where)
    env = os.environ.copy()
    env["CODEX_HOME"] = str(resolved_home)
    try:
        result = subprocess.run(
            [_codex_executable(), *argv],
            check=False,
            # Codex reads stdin when it is a terminal or an open pipe, so a probe launched from a
            # script hangs until its timeout while the same probe launched from a heredoc
            # succeeds -- the heredoc happens to hand it EOF. Closing stdin makes the probe behave
            # the same way whoever runs it.
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=PROBE_TIMEOUT_SECONDS,
            cwd=str(cwd),
            env=env,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CapabilityProbeError(f"{where}: probe did not run: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
        raise CapabilityProbeError(
            f"{where}: probe exited {result.returncode}: {detail[-1] if detail else 'no detail'}"
        )
    if len(result.stdout) > MAX_PROBE_BYTES:
        raise CapabilityProbeError(f"{where}: probe output exceeds the probe ceiling")
    return result.stdout.decode("utf-8", "replace")


def _flag_arguments(enable: Iterable[str], disable: Iterable[str]) -> list[str]:
    argv: list[str] = []
    for feature in sorted(set(enable)):
        argv += ["--enable", feature]
    for feature in sorted(set(disable)):
        argv += ["--disable", feature]
    return argv


def capture_feature_flags(
    *,
    codex_home: Path,
    cwd: Path,
    enable: Iterable[str] = (),
    disable: Iterable[str] = (),
) -> dict[str, dict[str, Any]]:
    """Return {feature: {"stage": str, "enabled": bool}} as the installed binary reports it."""

    stdout = _run(
        ["features", "list", *_flag_arguments(enable, disable)],
        codex_home=codex_home,
        cwd=cwd,
        where="feature flags",
    )
    features: dict[str, dict[str, Any]] = {}
    for line in stdout.splitlines():
        if not line.strip():
            continue
        match = FEATURE_ROW.match(line.rstrip())
        if match is None:
            raise CapabilityProbeError(f"feature flags: unparsed row {line.strip()[:80]!r}")
        stage = match.group("stage").strip()
        if stage not in FEATURE_STAGES:
            raise CapabilityProbeError(f"feature flags: unknown stage {stage!r}")
        name = match.group("name")
        if name in features:
            raise CapabilityProbeError(f"feature flags: duplicate feature {name!r}")
        features[name] = {"stage": stage, "enabled": match.group("state") == "true"}
    if not features:
        raise CapabilityProbeError("feature flags: the binary reported no features")
    return features


def _describe(value: object) -> str:
    """Describe a rejected value without reproducing it.

    Echoing the offending value into an exception message re-leaks exactly what the check just
    refused: an error string travels into logs, receipts, and terminals.
    """

    if isinstance(value, str):
        return f"a {len(value)}-character string"
    return f"a value of type {type(value).__name__}"


def _closed_choice(value: object, allowed: Iterable[str], where: str) -> str:
    """Accept only a member of a closed set.

    A pattern cannot separate a model slug from an identifier-shaped credential -- an AWS access
    key identifier and a model name have the same shape. Membership can.
    """

    if not isinstance(value, str):
        raise CapabilityProbeError(f"tool specification: {where} must be a string, got {_describe(value)}")
    if value not in set(allowed):
        raise CapabilityProbeError(
            f"tool specification: {where} is not a value this harness recognises "
            f"({_describe(value)})"
        )
    return value


def _tool_name(value: object, where: str) -> str:
    """Accept a name Codex actually emitted, so a malformed capture fails instead of
    silently projecting nonsense."""

    if not isinstance(value, str) or not value:
        raise CapabilityProbeError(
            f"tool specification: {where} must be a non-empty string, got {value!r}"
        )
    return value


def _reject_secret_shaped(projection: dict[str, Any]) -> None:
    """Last gate before a projection leaves this module."""

    rendered = json.dumps(projection, sort_keys=True)
    if SECRET_KEY.search(rendered) or SECRET_VALUE.search(rendered):
        raise CapabilityProbeError("tool specification: projection contains a secret-shaped value")
    if len(rendered) > MAX_PROJECTION_BYTES:
        raise CapabilityProbeError("tool specification: projection exceeds the projection ceiling")


def _capability_snapshot() -> dict[str, Any]:
    """Read the committed capability snapshot.

    Takes no path argument on purpose. An earlier draft let the caller supply the closed model
    set, which made the set an argument rather than a closed set: passing
    ``{"AKIAIOSFODNN7EXAMPLE"}`` put that value straight into a published projection. The only
    authority for what this repository has observed is the file this repository committed.
    """

    try:
        payload = json.loads(DEFAULT_CAPABILITY_SNAPSHOT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CapabilityProbeError(f"capability snapshot is unreadable: {exc}") from exc
    if not isinstance(payload, dict):
        raise CapabilityProbeError("capability snapshot is not an object")
    return payload


def capability_snapshot_sha256() -> str:
    """Digest of the snapshot that supplies every closed set this module checks against.

    Carried in the projection so the closed set is identified rather than assumed. A projection
    that names no snapshot cannot be checked against the set that produced it.
    """

    try:
        return hashlib.sha256(DEFAULT_CAPABILITY_SNAPSHOT.read_bytes()).hexdigest()
    except OSError as exc:
        raise CapabilityProbeError(f"capability snapshot is unreadable: {exc}") from exc


def known_tool_names() -> dict[str, frozenset[str]]:
    """Namespaces mapped to the tool names the committed capability snapshot records.

    The snapshot records the ``collaboration`` namespace and its operations. It deliberately does
    not record ``functions`` -- the namespace Codex uses for the shell tools -- because this
    repository has never made a claim about that namespace's contents. Names outside this set are
    reduced rather than copied; recording one is a snapshot change, which is where a claim about
    a name belongs.
    """

    payload = _capability_snapshot()
    collaboration = payload.get("collaboration")
    if not isinstance(collaboration, dict):
        raise CapabilityProbeError("capability snapshot records no collaboration surface")
    spawn = collaboration.get("spawn")
    namespace = spawn.get("tool_namespace") if isinstance(spawn, dict) else None
    operations = collaboration.get("operations")
    if not isinstance(namespace, str) or not namespace:
        raise CapabilityProbeError("capability snapshot records no collaboration tool namespace")
    if not isinstance(operations, list) or not operations:
        raise CapabilityProbeError("capability snapshot records no collaboration operations")
    names = frozenset(name for name in operations if isinstance(name, str) and name)
    if len(names) != len(operations):
        raise CapabilityProbeError("capability snapshot records a malformed collaboration operation")
    return {namespace: names}


def known_model_slugs() -> frozenset[str]:
    """Model slugs the committed capability snapshot names.

    A closed set, because pattern-matching cannot tell a model slug from an identifier-shaped
    credential. If a capture reports a slug this repository has never observed, that is worth
    failing on rather than copying into a projection.
    """

    payload = _capability_snapshot()
    catalog = payload.get("catalog")
    models = catalog.get("models") if isinstance(catalog, dict) else None
    if not isinstance(models, list) or not models:
        raise CapabilityProbeError("capability snapshot names no models")
    slugs = {row.get("slug") for row in models if isinstance(row, dict)}
    resolved = frozenset(slug for slug in slugs if isinstance(slug, str) and slug)
    if not resolved:
        raise CapabilityProbeError("capability snapshot names no usable model slug")
    return resolved


def extract_tool_specification(request_body: dict[str, Any]) -> dict[str, Any]:
    """Reduce one outbound request to the tool specification it offered.

    Returns namespaces mapped to their tool names, plus a digest over the canonical definitions.
    The definitions themselves are digested rather than returned because they run to tens of
    kilobytes of prose that no receipt should carry, and because a digest is what makes drift
    between two captures detectable.

    Takes no closed-set overrides. Every set this function checks against is read from the
    committed capability snapshot, so a caller cannot widen what counts as recognised.
    """

    if not isinstance(request_body, dict):
        raise CapabilityProbeError("tool specification: request body must be an object")
    known_models = known_model_slugs()
    items = request_body.get("input")
    if not isinstance(items, list):
        raise CapabilityProbeError("tool specification: request carries no input list")
    matches = [
        item
        for item in items
        if isinstance(item, dict) and item.get("type") == ADDITIONAL_TOOLS_ITEM
    ]
    if not matches:
        raise CapabilityProbeError(
            "tool specification: request carries no additional_tools item; this is a "
            "specification capture, not an inferred call list, so an absent item is a failure"
        )
    if len(matches) > 1:
        raise CapabilityProbeError("tool specification: request repeats the additional_tools item")
    namespaces_raw = matches[0].get("tools")
    if not isinstance(namespaces_raw, list) or not namespaces_raw:
        raise CapabilityProbeError("tool specification: additional_tools carries no namespaces")

    namespaces: dict[str, list[str]] = {}
    for index, namespace in enumerate(namespaces_raw):
        if not isinstance(namespace, dict) or namespace.get("type") != "namespace":
            raise CapabilityProbeError("tool specification: expected a namespace entry")
        # Recorded or reduced before it is copied. A namespace or tool name is as much
        # caller-controlled input as the model slug is, and an absolute path or an opaque
        # credential reaches a projection just as easily through a name as through a field.
        # Every message below addresses a name by its POSITION, never by its value: an error
        # string travels into logs and terminals, and echoing the name re-leaks precisely what
        # the reduction was there to prevent.
        name = _tool_name(namespace.get("name"), f"namespace {index}")
        tools = namespace.get("tools")
        if not isinstance(tools, list):
            raise CapabilityProbeError(f"tool specification: namespace {index} carries no tools")
        if name in namespaces:
            raise CapabilityProbeError(f"tool specification: namespace {index} is a duplicate")
        tool_names: list[str] = []
        for position, tool in enumerate(tools):
            if not isinstance(tool, dict):
                raise CapabilityProbeError(
                    f"tool specification: namespace {index} tool {position} is malformed"
                )
            tool_name = _tool_name(tool.get("name"), f"namespace {index} tool {position}")
            # A name with no description and no schema is a call list entry, not a definition.
            if "description" not in tool and "parameters" not in tool and "format" not in tool:
                raise CapabilityProbeError(
                    f"tool specification: namespace {index} tool {position} carries no definition"
                )
            tool_names.append(tool_name)
        namespaces[name] = sorted(tool_names)

    canonical = json.dumps(namespaces_raw, sort_keys=True, separators=(",", ":")).encode("utf-8")
    metadata = request_body.get("client_metadata")
    is_child = isinstance(metadata, dict) and PARENT_THREAD_METADATA_KEY in metadata
    reasoning = request_body.get("reasoning")
    effort = reasoning.get("effort") if isinstance(reasoning, dict) else None
    projection = {
        "namespaces": {name: namespaces[name] for name in sorted(namespaces)},
        "definitions_sha256": hashlib.sha256(canonical).hexdigest(),
        # Which closed set was in force. Without it a reader cannot tell whether a name was
        # copied because this repository records it or reduced because it does not, and a later
        # snapshot revision would silently change what the same capture projects to.
        "snapshot_sha256": capability_snapshot_sha256(),
        "model": _closed_choice(request_body.get("model"), known_models, "model"),
        "reasoning_effort": (
            None if effort is None else _closed_choice(effort, SCALAR_EFFORTS, "reasoning_effort")
        ),
        "turn_is_spawned_child": is_child,
    }
    _reject_secret_shaped(projection)
    return projection


class _RecordingResponsesApi:
    """A local, unauthenticated stand-in for the Responses API.

    Records every request body and replays a fixed list of server-sent-event scripts. It exists
    so a tool specification can be read out of a real Codex turn without a real model call.
    """

    def __init__(self, root_scripts: Sequence[str], child_script: str) -> None:
        self.requests: list[dict[str, Any]] = []
        self._root_scripts = list(root_scripts)
        self._child_script = child_script
        self._root_index = 0
        self._lock = threading.Lock()
        probe = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's contract
                length = int(self.headers.get("Content-Length") or 0)
                if length > MAX_REQUEST_BYTES:
                    self.send_response(413)
                    self.end_headers()
                    return
                raw = self.rfile.read(length)
                with probe._lock:
                    try:
                        body = json.loads(raw)
                    except json.JSONDecodeError:
                        body = {}
                    probe.requests.append(body)
                    # Dispatch on who is asking, not on arrival order. Codex starts the child
                    # asynchronously after the scripted spawn, so a global counter makes the
                    # reply a child receives depend on the scheduler: if the child's request
                    # overtakes the root's next one, the child is handed the root's script.
                    metadata = body.get("client_metadata")
                    is_child = (
                        isinstance(metadata, dict) and PARENT_THREAD_METADATA_KEY in metadata
                    )
                    if is_child:
                        script = probe._child_script
                    else:
                        index = min(probe._root_index, len(probe._root_scripts) - 1)
                        probe._root_index += 1
                        script = probe._root_scripts[index]
                body = script.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args: Any) -> None:
                return

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}/v1"

    def __enter__(self) -> "_RecordingResponsesApi":
        self._thread.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=10)


def _sse(*events: dict[str, Any]) -> str:
    return "".join(
        f"event: {event['type']}\ndata: {json.dumps(event)}\n\n" for event in events
    )


def _toml_inline_table(values: dict[str, Any]) -> str:
    """Render a `-c key=value` override. Codex parses the value as TOML, not as JSON."""

    rendered = []
    for key, value in values.items():
        if isinstance(value, bool):
            literal = "true" if value else "false"
        elif isinstance(value, int):
            literal = str(value)
        elif isinstance(value, str):
            literal = json.dumps(value)  # TOML basic strings match JSON string syntax
        else:
            raise CapabilityProbeError(f"cannot render {key!r} as a TOML value")
        rendered.append(f"{key} = {literal}")
    return "{ " + ", ".join(rendered) + " }"


def _usage_zero() -> dict[str, Any]:
    return {
        "input_tokens": 0,
        "input_tokens_details": None,
        "output_tokens": 0,
        "output_tokens_details": None,
        "total_tokens": 0,
    }


def spawn_script(*, task_name: str, agent_type: str) -> tuple[list[str], str]:
    """Replies for the root turn, and the single reply any child turn receives.

    Returned separately rather than as one ordered list, because the child's request is
    scheduled asynchronously and must be answered by who is asking rather than by when.
    """

    spawn_arguments = json.dumps(
        {
            "task_name": task_name,
            "message": "Return the single token PROBE_CHILD_OK and nothing else.",
            "agent_type": agent_type,
            "fork_turns": "none",
        }
    )
    spawn = _sse(
        {"type": "response.created", "response": {"id": "probe-root-spawn"}},
        {
            "type": "response.output_item.done",
            "item": {
                "type": "function_call",
                "call_id": "probe-spawn-call",
                "namespace": "collaboration",
                "name": "spawn_agent",
                "arguments": spawn_arguments,
            },
        },
        {
            "type": "response.completed",
            "response": {"id": "probe-root-spawn", "usage": _usage_zero()},
        },
    )
    wait = _sse(
        {"type": "response.created", "response": {"id": "probe-root-wait"}},
        {
            "type": "response.output_item.done",
            "item": {
                "type": "function_call",
                "call_id": "probe-wait-call",
                "namespace": "collaboration",
                "name": "wait_agent",
                "arguments": json.dumps({"timeout_ms": 10000}),
            },
        },
        {
            "type": "response.completed",
            "response": {"id": "probe-root-wait", "usage": _usage_zero()},
        },
    )
    done = _sse(
        {"type": "response.created", "response": {"id": "probe-done"}},
        {
            "type": "response.output_item.done",
            "item": {
                "type": "message",
                "role": "assistant",
                "id": "probe-done-message",
                "content": [{"type": "output_text", "text": "PROBE_CHILD_OK"}],
            },
        },
        {"type": "response.completed", "response": {"id": "probe-done", "usage": _usage_zero()}},
    )
    return [spawn, wait, done], done


def record_offline_turn(
    *,
    codex_home: Path,
    workspace: Path,
    root_model: str = "gpt-5.6-sol",
    child_profile: str | None = None,
    child_profile_config: Path | None = None,
    task_name: str = "probe_child",
    where: str = "offline turn",
) -> list[dict[str, Any]]:
    """Drive one offline Codex turn and return every outbound request body, unreduced.

    Split out so that callers asking different questions of the same turn share one driver. A
    reduced projection answers "which tools were offered"; the raw body is what answers "what
    text reached the model context", and reducing before both questions are asked would throw
    away the evidence for the second.
    """

    _assert_disposable_home(codex_home, where)  # fail early, before the stub
    if (child_profile is None) != (child_profile_config is None):
        raise CapabilityProbeError(f"{where}: a child profile needs both a name and a config file")
    root_scripts, child_script = spawn_script(
        task_name=task_name, agent_type=child_profile or ""
    )
    with _RecordingResponsesApi(root_scripts, child_script) as stub:
        provider = {
            "name": "Offline probe provider",
            "base_url": stub.base_url,
            "wire_api": "responses",
            "request_max_retries": 0,
            "stream_max_retries": 0,
        }
        argv = [
            "--ask-for-approval",
            "never",
            "--sandbox",
            "read-only",
            "--enable",
            "multi_agent",
            "--enable",
            "multi_agent_v2",
            "--model",
            root_model,
            "-c",
            f"model_providers.offlineprobe={_toml_inline_table(provider)}",
            "-c",
            'model_provider="offlineprobe"',
        ]
        if child_profile is not None and child_profile_config is not None:
            agent = {
                "description": "Offline probe child profile",
                "config_file": str(child_profile_config),
            }
            argv += ["-c", f"agents.{child_profile}={_toml_inline_table(agent)}"]
        argv += [
            "exec",
            "--ephemeral",
            "--skip-git-repo-check",
            "-C",
            str(workspace),
            "Invoke the requested offline child probe.",
        ]
        _run(argv, codex_home=codex_home, cwd=workspace, where=where)
        recorded = list(stub.requests)
    if not recorded:
        raise CapabilityProbeError(f"{where}: the probe recorded no outbound request")
    return recorded


def capture_tool_specification(
    *,
    codex_home: Path,
    workspace: Path,
    root_model: str = "gpt-5.6-sol",
    child_profile: str | None = None,
    child_profile_config: Path | None = None,
    task_name: str = "probe_child",
) -> list[dict[str, Any]]:
    """Drive one offline Codex turn and return the reduced specification for every request.

    When ``child_profile`` is given, the root is scripted to spawn that profile, so the returned
    list contains a child entry whose ``turn_is_spawned_child`` is true. That child entry is the
    one worth having: a root's tool set says nothing about what a spawned profile is offered.
    """

    recorded = record_offline_turn(
        codex_home=codex_home,
        workspace=workspace,
        root_model=root_model,
        child_profile=child_profile,
        child_profile_config=child_profile_config,
        task_name=task_name,
        where="tool specification",
    )
    projections = [extract_tool_specification(body) for body in recorded]
    _require_requested_child(projections, child_requested=child_profile is not None)
    return projections


def capture_context_injection(
    *,
    codex_home: Path,
    workspace: Path,
    markers: Mapping[str, str],
    root_model: str = "gpt-5.6-sol",
) -> dict[str, bool]:
    """Report, per named marker, whether its text reached a real turn's model context.

    Codex decides which skills to inject, so the only honest way to ask "is this skill offered
    to the model?" is to assemble a turn and read what actually went out. Absence alone proves
    nothing -- a marker missing from a request that carried no skills at all would look the same
    as one deliberately withheld. What makes an absence evidence is a marker that DOES appear in
    the same request (KTD7), which is why callers pass several at once and compare.
    """

    if not markers:
        raise CapabilityProbeError("context injection: no markers to look for")
    for name, text in markers.items():
        if not isinstance(text, str) or not text:
            raise CapabilityProbeError(f"context injection: marker {name!r} has no text")
    recorded = record_offline_turn(
        codex_home=codex_home,
        workspace=workspace,
        root_model=root_model,
        where="context injection",
    )
    haystack = "\n".join(
        json.dumps(body, sort_keys=True, ensure_ascii=False) for body in recorded
    )
    return {name: text in haystack for name, text in markers.items()}


def _require_requested_child(
    projections: Sequence[dict[str, Any]], *, child_requested: bool
) -> None:
    """Fail when a child capture was asked for and no child turn was recorded.

    "Some request was recorded" is not "the requested capture happened". With an unreadable child
    profile this returned three root turns and no child turn while reporting success, so a proof
    unit asking about a CHILD's tool specification would have been handed the root's instead --
    quietly proving the wrong thing, which is worse than failing.

    Whether a turn is a child is decided by the parent-thread key in its own client metadata, not
    by arrival order. Split out from the capture so it can be tested without driving Codex into
    the failure it detects.
    """

    if not child_requested:
        return
    if not any(one["turn_is_spawned_child"] for one in projections):
        raise CapabilityProbeError(
            f"tool specification: a child capture was requested but all {len(projections)} "
            f"recorded turns are root turns; the child never spawned"
        )


TURN_ENVIRONMENT_FIELDS = (
    "cwd",
    "workspace_roots",
    "approval_policy",
    "approvals_reviewer",
    "sandbox_policy",
    "permission_profile",
)


def capture_turn_environment(
    *,
    codex_home: Path,
    workspace: Path,
    sandbox: str = "read-only",
    extra_roots: Sequence[Path] = (),
    child_profile_config: Path | None = None,
    config_overrides: Sequence[str] = (),
    resume_last: bool = False,
    task_name: str = "probe_child",
) -> dict[str, Any]:
    """Run one offline turn and return the effective permission tuple for root and child.

    The turn is real -- Codex applies the sandbox, resolves workspace roots, and writes rollouts
    -- but the model is a local stand-in, so nothing is called and no quota is spent. Rollouts are
    what carry `turn_context`, so this deliberately does NOT pass `--ephemeral`.

    The returned tuples come from what Codex recorded, never from what was requested. That
    distinction is the whole point of the unit: a requested sandbox is an intention, and a
    recorded one is the permission the turn actually ran under.
    """

    resolved_home = _assert_disposable_home(codex_home, "turn environment")
    before = set((resolved_home / "sessions").glob("**/rollout-*.jsonl"))
    # Always a spawning turn, even when only the root's tuple is wanted. A scripted turn that
    # ends with a plain assistant message did not reliably terminate against this stand-in, and
    # the root's permission tuple is unaffected by a child existing, so the spawn path -- which
    # is exercised constantly and known to complete -- is used for every row.
    if child_profile_config is None:
        raise CapabilityProbeError("turn environment: a child profile config is required")
    spawning = True
    root_scripts, child_script = spawn_script(task_name=task_name, agent_type=task_name)
    with _RecordingResponsesApi(root_scripts, child_script) as stub:
        provider = {
            "name": "offline",
            "base_url": stub.base_url,
            "wire_api": "responses",
            "requires_openai_auth": False,
        }
        argv = [
            "--ask-for-approval", "never",
            "--sandbox", sandbox,
            "--enable", "multi_agent",
            "--enable", "multi_agent_v2",
            "--model", "gpt-5.6-sol",
            "-c", f"model_providers.offlineprobe={_toml_inline_table(provider)}",
            "-c", 'model_provider="offlineprobe"',
        ]
        for override in config_overrides:
            argv += ["-c", override]
        if spawning:
            agent = {"description": "Offline probe child", "config_file": str(child_profile_config)}
            argv += ["-c", f"agents.{task_name}={_toml_inline_table(agent)}"]
        if resume_last:
            # A resumed session is the only way to observe what a LATER turn ran under, which is
            # what the cold-resume and later-update rows are about. `exec resume` takes neither
            # `-C` nor `--skip-git-repo-check`: its signature is [OPTIONS] [SESSION_ID] [PROMPT],
            # and the working directory comes from the session being resumed.
            argv += ["exec", "resume", "--last", "Invoke the requested offline child probe."]
        else:
            argv += ["exec", "--skip-git-repo-check", "-C", str(workspace)]
            for root in extra_roots:
                argv += ["--add-dir", str(root)]
            argv += ["Invoke the requested offline child probe."]
        _run(argv, codex_home=resolved_home, cwd=workspace, where="turn environment")

    after = set((resolved_home / "sessions").glob("**/rollout-*.jsonl"))
    # A resumed session APPENDS to the rollout it resumed rather than writing a new one, so a
    # before/after diff finds nothing and the row silently has no evidence. Resume therefore
    # reads every rollout and takes the LAST turn context in each -- which is the resumed turn.
    considered = sorted(after) if resume_last else sorted(after - before)
    if not considered:
        raise CapabilityProbeError("turn environment: the probe wrote no rollout receipt")
    turns: list[dict[str, Any]] = []
    for path in considered:
        meta: dict[str, Any] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row.get("type") == "session_meta":
                payload = row.get("payload", {})
                meta["agent_path"] = payload.get("agent_path")
                meta["parent_thread_id"] = payload.get("parent_thread_id")
            elif row.get("type") == "turn_context":
                payload = row.get("payload", {})
                # Last one wins: the final turn context is the permission the turn actually
                # finished under, which is the whole question for the later-update row.
                meta["environment"] = {
                    field: payload.get(field) for field in TURN_ENVIRONMENT_FIELDS
                }
        if "environment" in meta:
            turns.append(meta)
    roots = [t for t in turns if t.get("parent_thread_id") is None]
    children = [t for t in turns if t.get("parent_thread_id") is not None]
    if not roots:
        raise CapabilityProbeError("turn environment: no root turn was recorded")
    if spawning and not children:
        raise CapabilityProbeError(
            "turn environment: a child was requested but no child turn was recorded"
        )
    return {"root": roots[0]["environment"], "child": children[0]["environment"] if children else None}


def isolated_probe_home(parent: Path) -> Path:
    """Create an empty Codex home under `parent` for a probe to populate and discard."""

    home = parent / "codex-home"
    home.mkdir(mode=0o700)
    return home
