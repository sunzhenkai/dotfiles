"""MCP entry ownership and journaled multi-target commit primitives."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, Mapping

from adapters import ActualDocument, JsonMcpAdapter
from common import entries_equivalent
from dotf_core.atomic import atomic_replace, atomic_write, stage_bytes
from dotf_core.paths import (
    PathBoundaryError,
    ensure_directory,
    open_directory_nofollow,
    open_nofollow,
    open_parent_nofollow,
)
from dotf_core.sanitize import sanitize_for_persistence
from dotf_core.schemas import (
    ACTION_STATES,
    MCP_MANIFEST_SCHEMA_VERSION,
    MCP_TRANSACTION_JOURNAL_SCHEMA_VERSION,
    JournalAction,
    McpEntryPlan,
    McpManagedItem,
    McpManagedManifest,
    McpTransactionJournal,
    SchemaError,
    validate_mcp_managed_manifest,
)

MCP_MANIFEST_NAME = "agents-mcp-manifest.json"
MCP_JOURNAL_DIR = "agent-transactions"
FaultHook = Callable[[str, int, str], None]


@dataclass(frozen=True, slots=True)
class ManifestSnapshot:
    status: Literal["missing", "ok", "malformed"]
    manifest: McpManagedManifest
    digest: str | None


@dataclass(frozen=True, slots=True)
class TransactionOutput:
    label: str
    target: Path
    root: Path
    payload: bytes
    format: str
    mode: int
    sensitive: bool


@dataclass(frozen=True, slots=True)
class TransactionResult:
    run_id: str
    status: Literal["completed", "failed", "interrupted", "failed-rollback"]
    journal: Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def entry_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(payload)


def _empty_manifest() -> McpManagedManifest:
    return McpManagedManifest(
        schema_version=MCP_MANIFEST_SCHEMA_VERSION,
        kind="mcp-managed-manifest",
        generated_at="1970-01-01T00:00:00Z",
        items=(),
    )


def _state_root(home: Path, state_home: Path | None) -> Path:
    if state_home is not None:
        return state_home.expanduser().absolute()
    configured = os.environ.get("XDG_STATE_HOME")
    return Path(configured).expanduser().absolute() if configured else home / ".local" / "state"


def mcp_manifest_path(home: Path, state_home: Path | None = None) -> Path:
    return _state_root(home, state_home) / "dotf" / MCP_MANIFEST_NAME


def journal_path(home: Path, state_home: Path | None, run_id: str) -> Path:
    return _state_root(home, state_home) / "dotf" / MCP_JOURNAL_DIR / f"{run_id}.json"


def _boundary(home: Path, path: Path) -> Path:
    try:
        path.relative_to(home)
    except ValueError:
        return Path("/")
    return home


def _read_fd(fd: int) -> bytes:
    os.lseek(fd, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def read_manifest(home: Path, state_home: Path | None = None) -> ManifestSnapshot:
    path = mcp_manifest_path(home, state_home)
    try:
        fd = open_nofollow(_boundary(home, path), path)
    except FileNotFoundError:
        return ManifestSnapshot("missing", _empty_manifest(), None)
    except (OSError, PathBoundaryError):
        return ManifestSnapshot("malformed", _empty_manifest(), None)
    try:
        item = os.fstat(fd)
        if not stat.S_ISREG(item.st_mode):
            return ManifestSnapshot("malformed", _empty_manifest(), None)
        raw = _read_fd(fd)
    finally:
        os.close(fd)
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
        manifest = validate_mcp_managed_manifest(value)
    except (UnicodeError, json.JSONDecodeError, ValueError, SchemaError, TypeError):
        return ManifestSnapshot("malformed", _empty_manifest(), sha256(raw))
    return ManifestSnapshot("ok", manifest, sha256(raw))


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON member: {key}")
        value[key] = item
    return value


def serialize_manifest(manifest: McpManagedManifest) -> bytes:
    manifest.validate()
    return (json.dumps(manifest.to_dict(), ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def entry_plans(
    *,
    tool: str,
    target: str,
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
    snapshot: ManifestSnapshot,
) -> tuple[McpEntryPlan, ...]:
    """Decide ownership per server id without mutating target or state."""
    if snapshot.status == "malformed":
        return tuple(
            McpEntryPlan(server_id, "owned", entry_hash(value), entry_hash(actual[server_id]) if server_id in actual else None,
                         None, "conflict", "block", "MCP ownership manifest is malformed")
            for server_id, value in sorted(expected.items())
        )
    prior = {
        item.server_id: item
        for item in snapshot.manifest.items
        if item.tool == tool
    }
    decisions: list[McpEntryPlan] = []
    for server_id, value in sorted(expected.items()):
        wanted_hash = entry_hash(value)
        current_hash = entry_hash(actual[server_id]) if server_id in actual else None
        owned = prior.get(server_id)
        if owned is None:
            if server_id in actual:
                decisions.append(McpEntryPlan(
                    server_id, "owned", wanted_hash, current_hash, None,
                    "conflict", "block", "expected MCP id exists without ownership",
                ))
            else:
                decisions.append(McpEntryPlan(server_id, "owned", wanted_hash, None, None, "create", "create", None))
            continue
        if owned.target != target:
            decisions.append(McpEntryPlan(
                server_id, "owned", wanted_hash, current_hash, owned.installed_hash,
                "conflict", "block", "owned MCP target changed",
            ))
        elif server_id not in actual:
            decisions.append(McpEntryPlan(
                server_id, "owned", wanted_hash, None, owned.installed_hash,
                "create", "create", None,
            ))
        elif current_hash != owned.installed_hash:
            decisions.append(McpEntryPlan(
                server_id, "owned", wanted_hash, current_hash, owned.installed_hash,
                "conflict", "block", "owned MCP entry was modified locally",
            ))
        elif wanted_hash == owned.expected_hash and entries_equivalent(value, actual[server_id]):
            decisions.append(McpEntryPlan(
                server_id, "owned", wanted_hash, current_hash, owned.installed_hash,
                "unchanged", "none", None,
            ))
        else:
            decisions.append(McpEntryPlan(
                server_id, "owned", wanted_hash, current_hash, owned.installed_hash,
                "update", "update", None,
            ))
    for server_id, owned in sorted(prior.items()):
        if server_id in expected:
            continue
        current_hash = entry_hash(actual[server_id]) if server_id in actual else None
        if owned.target != target:
            decisions.append(McpEntryPlan(
                server_id, "owned", None, current_hash, owned.installed_hash,
                "conflict", "block", "stale MCP ownership target changed",
            ))
        elif server_id in actual and current_hash != owned.installed_hash:
            decisions.append(McpEntryPlan(
                server_id, "owned", None, current_hash, owned.installed_hash,
                "conflict", "block", "stale owned MCP entry was modified locally",
            ))
        else:
            decisions.append(McpEntryPlan(
                server_id, "owned", None, current_hash, owned.installed_hash,
                "prune", "prune", None,
            ))
    owned_ids = set(prior) | set(expected)
    for server_id in sorted(set(actual) - owned_ids):
        decisions.append(McpEntryPlan(
            server_id, "unowned", None, entry_hash(actual[server_id]), None,
            "unchanged", "none", None,
        ))
    return tuple(sorted(decisions, key=lambda item: item.server_id))


def reconcile_payload(
    adapter: JsonMcpAdapter,
    actual: ActualDocument,
    managed: Mapping[str, Any],
    decisions: Iterable[McpEntryPlan],
) -> bytes:
    pruned = {item.server_id for item in decisions if item.action == "prune"}
    return adapter.reconcile(actual, managed, prune_ids=pruned)


def next_manifest(
    prior: McpManagedManifest,
    *,
    selected_tools: set[str],
    targets: Mapping[str, str],
    expected_entries: Mapping[str, Mapping[str, Any]],
    installed_entries: Mapping[str, Mapping[str, Any]],
    run_id: str,
) -> McpManagedManifest:
    retained = [item for item in prior.items if item.tool not in selected_tools]
    owned: list[McpManagedItem] = []
    for tool in sorted(selected_tools):
        expected = expected_entries.get(tool, {})
        installed = installed_entries.get(tool, {})
        for server_id, value in sorted(expected.items()):
            owned.append(McpManagedItem(
                tool=tool,
                server_id=server_id,
                target=targets[tool],
                expected_hash=entry_hash(value),
                installed_hash=entry_hash(installed[server_id]),
                run_id=run_id,
            ))
    return McpManagedManifest(
        schema_version=MCP_MANIFEST_SCHEMA_VERSION,
        kind="mcp-managed-manifest",
        generated_at=now(),
        items=tuple(sorted(retained + owned, key=lambda item: (item.tool, item.server_id))),
    )


def _ensure_private_directory(home: Path, directory: Path) -> None:
    boundary = _boundary(home, directory)
    current = directory
    missing: list[Path] = []
    while not current.exists():
        missing.append(current)
        current = current.parent
    for path in reversed(missing):
        ensure_directory(boundary, path, mode=0o700)
    if directory.exists():
        fd = open_directory_nofollow(boundary, directory)
        try:
            os.fchmod(fd, 0o700)
        finally:
            os.close(fd)


def _journal_bytes(journal: McpTransactionJournal) -> bytes:
    safe = sanitize_for_persistence(journal.to_dict())
    return (json.dumps(safe, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _write_journal(path: Path, home: Path, journal: McpTransactionJournal) -> None:
    atomic_write(path, _journal_bytes(journal), root=_boundary(home, path), format="json", mode=0o600, sensitive=True)


def _action(label: str, before: str | None, after: str, timestamp: str) -> JournalAction:
    return JournalAction(label, "commit", "pending", timestamp, None, None, None, None, before, after)


def _set_action(journal: McpTransactionJournal, index: int, status: str, reason_code: str | None = None) -> McpTransactionJournal:
    if status not in ACTION_STATES:
        raise ValueError("invalid journal action status")
    timestamp = now()
    actions = list(journal.actions)
    old = actions[index]
    actions[index] = replace(
        old,
        status=status,
        ended_at=timestamp if status not in {"pending", "running"} else None,
        reason_code=reason_code,
        reason=reason_code,
    )
    return replace(journal, updated_at=timestamp, actions=tuple(actions))


def _read_staged_old(staged: Any) -> tuple[bytes | None, int | None]:
    if staged.target_fd is None or staged.target_stat is None:
        return None, None
    return _read_fd(staged.target_fd), stat.S_IMODE(staged.target_stat.st_mode)


def _unlink_created(output: TransactionOutput) -> None:
    parent_fd, name = open_parent_nofollow(output.root, output.target)
    fd: int | None = None
    try:
        item = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISREG(item.st_mode):
            raise RuntimeError("rollback target is not a regular file")
        fd = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd)
        if sha256(_read_fd(fd)) != sha256(output.payload):
            raise RuntimeError("committed target changed before rollback")
        os.unlink(name, dir_fd=parent_fd)
        os.fsync(parent_fd)
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent_fd)


def commit_outputs(
    outputs: Iterable[TransactionOutput],
    *,
    home: Path,
    state_home: Path | None,
    run_id: str,
    fault: FaultHook | None = None,
) -> TransactionResult:
    """Stage every output, persist a sanitized journal, then commit all or reverse rollback."""
    values = tuple(outputs)
    if not values:
        raise ValueError("transaction requires at least one output")
    if len({str(item.target) for item in values}) != len(values):
        raise ValueError("transaction contains duplicate targets")
    staged: list[Any] = []
    old: list[tuple[bytes | None, int | None]] = []
    committed: list[int] = []
    journal_file = journal_path(home, state_home, run_id)
    _ensure_private_directory(home, journal_file.parent)
    started = now()
    journal = McpTransactionJournal(
        schema_version=MCP_TRANSACTION_JOURNAL_SCHEMA_VERSION,
        kind="mcp-transaction-journal",
        run_id=run_id,
        status="running",
        started_at=started,
        updated_at=started,
        plan_version=1,
        actions=tuple(_action(item.label, None, sha256(item.payload), started) for item in values),
    )
    _write_journal(journal_file, home, journal)
    staging_index = 0
    try:
        for staging_index, output in enumerate(values):
            if fault:
                fault("stage", staging_index, output.label)
            handle = stage_bytes(
                output.target, output.payload, root=output.root, format=output.format,
                mode=output.mode, sensitive=output.sensitive,
            )
            staged.append(handle)
            old.append(_read_staged_old(handle))
        actions = tuple(
            replace(action, before_hash=handle.target_digest)
            for action, handle in zip(journal.actions, staged)
        )
        journal = replace(journal, actions=actions, updated_at=now())
        _write_journal(journal_file, home, journal)
    except BaseException:
        for handle in reversed(staged):
            handle.cleanup()
        journal = _set_action(journal, staging_index, "failed", "stage-failed")
        journal = replace(journal, status="failed", updated_at=now())
        _write_journal(journal_file, home, journal)
        raise
    interrupted = False
    failure: BaseException | None = None
    try:
        for index, (output, handle) in enumerate(zip(values, staged)):
            journal = _set_action(journal, index, "running")
            _write_journal(journal_file, home, journal)
            if fault:
                fault("commit", index, output.label)
            atomic_replace(handle, output.target, root=output.root, mode=output.mode, sensitive=output.sensitive)
            committed.append(index)
            journal = _set_action(journal, index, "completed")
            _write_journal(journal_file, home, journal)
    except KeyboardInterrupt as exc:
        interrupted = True
        failure = exc
    except BaseException as exc:
        failure = exc
    if failure is None:
        journal = replace(journal, status="completed", updated_at=now())
        _write_journal(journal_file, home, journal)
        return TransactionResult(run_id, "completed", journal_file)

    rollback_error: BaseException | None = None
    for index in reversed(committed):
        output = values[index]
        before, old_mode = old[index]
        try:
            if fault:
                fault("rollback", index, output.label)
            if before is None:
                _unlink_created(output)
            else:
                atomic_write(
                    output.target, before, root=output.root, format=output.format,
                    mode=old_mode if old_mode is not None else output.mode,
                    sensitive=output.sensitive,
                )
            journal = _set_action(journal, index, "failed", "rolled-back")
        except BaseException as exc:
            rollback_error = exc
            break
    for index, handle in enumerate(staged):
        if index not in committed:
            handle.cleanup()
    status: Literal["failed", "interrupted", "failed-rollback"]
    status = "failed-rollback" if rollback_error is not None else ("interrupted" if interrupted else "failed")
    journal = replace(journal, status=status, updated_at=now())
    _write_journal(journal_file, home, journal)
    if rollback_error is not None:
        rollback_error.add_note(f"original transaction failure: {failure!r}")
        raise rollback_error from failure
    raise failure
