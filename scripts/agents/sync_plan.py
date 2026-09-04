#!/usr/bin/env python3
"""Compile immutable Agent SyncPlan values, then safely apply approved plans."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from adapters import ActualDocument, JsonMcpAdapter, adapter_for  # noqa: E402
from common import Catalog, lookup_env_value  # noqa: E402
from dotf_core.paths import lstat_components, open_directory_nofollow  # noqa: E402
from dotf_core.schemas import (  # noqa: E402
    SYNC_PLAN_SCHEMA_VERSION,
    RuntimeVersion,
    SyncPlan,
    SyncPlanItem,
)


class SyncPlanError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ApplyResult:
    resource_id: str
    target: str
    status: str
    backup: str | None


def _home(home: Path | None) -> Path:
    return (home or Path.home()).expanduser().absolute()


def _risk(profile_risk: str, server_risks: Iterable[str], *, sensitive: bool) -> str:
    if sensitive:
        return "sensitive"
    ranks = {"low": 0, "medium": 1, "high": 2}
    values = [profile_risk, *server_risks]
    return max(values, key=lambda value: ranks[value])


def _runtime_versions(selected: dict[str, dict]) -> tuple[RuntimeVersion, ...]:
    result = []
    for server_id, server in sorted(selected.items()):
        package = server.get("package")
        version = server.get("version")
        if package and version:
            result.append(RuntimeVersion(server_id, package, version))
    return tuple(result)




def _inside(path: Path, root: Path) -> bool:
    candidate = Path(os.path.realpath(path.absolute()))
    boundary = Path(os.path.realpath(root.absolute()))
    try:
        return os.path.commonpath((str(candidate), str(boundary))) == str(boundary)
    except ValueError:
        return False


def _conflict_expected(adapter: JsonMcpAdapter, rendered: dict) -> bytes:
    missing = ActualDocument("missing", adapter.target(Path("/")), None, None, None)
    return adapter.merge(missing, rendered)


def _sensitive_permissions_broad(home: Path, target: Path) -> bool:
    """Inspect every managed component with lstat; HOME itself is not managed."""
    components = lstat_components(home, target, missing_ok=True)
    for index, (_path, item) in enumerate(components):
        if item is None:
            return False
        is_leaf = index == len(components) - 1
        allowed = 0o600 if is_leaf else 0o700
        if stat.S_IMODE(item.st_mode) & ~allowed:
            return True
    return False


@dataclass(frozen=True, slots=True)
class _PinnedEntry:
    parent_fd: int
    name: str
    fd: int
    identity: tuple[int, int]
    directory: bool


def _open_flags(*, directory: bool) -> int:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    if directory:
        flags |= getattr(os, "O_DIRECTORY", 0)
    return flags


def _same_inode(item: os.stat_result, identity: tuple[int, int]) -> bool:
    return (item.st_dev, item.st_ino) == identity


def _pin_sensitive_path(home: Path, target: Path) -> tuple[int, tuple[_PinnedEntry, ...]]:
    """Retain HOME, every ancestor below it, and the no-follow target inode."""
    try:
        relative = target.relative_to(home)
    except ValueError as exc:
        raise SyncPlanError("sensitive target is outside HOME") from exc
    if not relative.parts:
        raise SyncPlanError("sensitive target must be below HOME")

    root_fd = os.open(home, _open_flags(directory=True))
    opened = [root_fd]
    entries: list[_PinnedEntry] = []
    current_fd = root_fd
    try:
        for index, name in enumerate(relative.parts):
            directory = index < len(relative.parts) - 1
            observed = os.stat(name, dir_fd=current_fd, follow_symlinks=False)
            if directory and not stat.S_ISDIR(observed.st_mode):
                raise SyncPlanError("sensitive managed ancestor is not a directory")
            if not directory and not stat.S_ISREG(observed.st_mode):
                raise SyncPlanError("sensitive managed target is not a regular file")
            child_fd = os.open(name, _open_flags(directory=directory), dir_fd=current_fd)
            opened.append(child_fd)
            identity = (observed.st_dev, observed.st_ino)
            if not _same_inode(os.fstat(child_fd), identity):
                raise SyncPlanError("sensitive managed path changed while being retained")
            entries.append(_PinnedEntry(current_fd, name, child_fd, identity, directory))
            current_fd = child_fd
        _verify_pinned_entries(entries)
        return root_fd, tuple(entries)
    except BaseException:
        for fd in reversed(opened):
            os.close(fd)
        raise


def _verify_pinned_entries(entries: Iterable[_PinnedEntry]) -> None:
    for entry in entries:
        retained = os.fstat(entry.fd)
        named = os.stat(entry.name, dir_fd=entry.parent_fd, follow_symlinks=False)
        if not _same_inode(retained, entry.identity) or not _same_inode(named, entry.identity):
            raise SyncPlanError("sensitive managed path changed during permission remediation")
        if entry.directory != stat.S_ISDIR(retained.st_mode):
            raise SyncPlanError("sensitive managed path type changed during permission remediation")


def _read_retained(fd: int) -> bytes:
    os.lseek(fd, 0, os.SEEK_SET)
    chunks = []
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _close_pinned(root_fd: int, entries: Iterable[_PinnedEntry]) -> None:
    values = tuple(entries)
    for entry in reversed(values):
        os.close(entry.fd)
    os.close(root_fd)


def _apply_permission_only(
    item: SyncPlanItem,
    adapter: JsonMcpAdapter,
    catalog: Catalog,
    profile: str,
    home: Path,
) -> bool:
    """Prove approved bytes, then chmod only exact retained sensitive inodes."""
    root_fd, entries = _pin_sensitive_path(home, Path(item.target))
    try:
        target_entry = entries[-1]
        raw = _read_retained(target_entry.fd)
        current_hash = hashlib.sha256(raw).hexdigest()
        actual = ActualDocument("present", Path(item.target), raw, current_hash, None)
        _assert_fresh(item, actual)

        # Recreate the planning payload without expansion. Placeholder-aware
        # equivalence can prove literal-at-apply output structure without ever
        # looking up the credential value.
        selected = catalog.selected_servers(item.adapter, profile)
        rendered = adapter.render(selected)
        expected = adapter.merge(actual, rendered.servers)
        if hashlib.sha256(expected).hexdigest() != item.expected_hash:
            raise SyncPlanError(f"declared content changed after approval: {item.resource_id}")
        if not adapter.equivalent(expected, actual):
            raise SyncPlanError(f"target content changed after approval: {item.resource_id}")

        _verify_pinned_entries(entries)
        desired = [(entry, 0o700 if entry.directory else 0o600) for entry in entries]
        changed = any(stat.S_IMODE(os.fstat(entry.fd).st_mode) != mode for entry, mode in desired)
        for entry, mode in desired:
            if stat.S_IMODE(os.fstat(entry.fd).st_mode) != mode:
                os.fchmod(entry.fd, mode)
            if stat.S_IMODE(os.fstat(entry.fd).st_mode) != mode:
                raise SyncPlanError(f"permission remediation failed verification: {item.resource_id}")
            os.fsync(entry.fd)
        _verify_pinned_entries(entries)
        return changed
    finally:
        _close_pinned(root_fd, entries)


def _secret_resolver(values: list[str]) -> Callable[[str], str]:
    cache: dict[str, str] = {}

    def resolve(name: str) -> str:
        if name not in cache:
            value = lookup_env_value(name)
            if not value:
                raise SyncPlanError(f"required secret is unavailable: {name}")
            cache[name] = value
            values.append(value)
        return cache[name]

    return resolve


def _assert_plan_target(adapter: JsonMcpAdapter, item: SyncPlanItem, home: Path) -> None:
    declared = adapter.target(home)
    if Path(item.target) != declared:
        raise SyncPlanError(f"plan target is not declared for {item.adapter}")


def _assert_fresh(item: SyncPlanItem, actual: ActualDocument) -> None:
    if item.current_hash != actual.current_hash:
        raise SyncPlanError(f"target changed after approval: {item.resource_id}")
    if item.actual_state == "missing" and actual.state != "missing":
        raise SyncPlanError(f"target appeared after approval: {item.resource_id}")
    if actual.state in {"malformed", "unsafe"}:
        raise SyncPlanError(f"target is not safely writable: {item.resource_id}")


def _secure_target_parents(home: Path, target: Path, *, all_ancestors: bool) -> None:
    """Create/open managed parents without links and enforce private modes."""
    relative = target.parent.relative_to(home)
    parents = []
    current = home
    for part in relative.parts:
        current /= part
        parents.append(current)
    selected = parents if all_ancestors else parents[-1:]
    for parent in selected:
        parent_fd = open_directory_nofollow(home, parent, create=True, mode=0o700)
        try:
            os.fchmod(parent_fd, 0o700)
        finally:
            os.close(parent_fd)


def plan_json(plan: SyncPlan) -> str:
    return json.dumps(plan.to_dict(), ensure_ascii=False, sort_keys=True, indent=2)


# Ownership-aware compiler/apply retains task-4 pinned-inode permission remediation.
def _compile_owned_sync_plan(
    catalog: Catalog,
    profile: str | None = None,
    tools: Iterable[str] | None = None,
    *,
    home: Path | None = None,
    state_home: Path | None = None,
) -> SyncPlan:
    from mcp_runtime import entry_plans, read_manifest, reconcile_payload

    profile_doc = catalog.resolve_profile(profile)
    selected_tools = tuple(tools or catalog.vendor_matrix.adapter_tools)
    if len(selected_tools) != len(set(selected_tools)):
        raise SyncPlanError("duplicate tools in sync selection")
    user_home = _home(home)
    snapshot = read_manifest(user_home, state_home)
    items = []
    for tool in selected_tools:
        capability = catalog.vendor_matrix.capability(tool)
        if not capability.mcp:
            continue
        adapter = adapter_for(catalog.vendor_matrix, tool)
        selected = catalog.selected_servers(tool, profile_doc["id"])
        rendered = adapter.render(selected)
        actual = adapter.read_actual(user_home)
        decisions = ()
        conflict = None
        if actual.state in {"present", "missing"}:
            actual_entries = adapter.entries(actual)
            decisions = entry_plans(
                tool=tool,
                target=str(adapter.target(user_home)),
                expected=rendered.servers,
                actual=actual_entries,
                snapshot=snapshot,
            )
            expected = reconcile_payload(adapter, actual, rendered.servers, decisions)
            entry_conflicts = [entry for entry in decisions if entry.state == "conflict"]
            if entry_conflicts:
                state, action = "conflict", "skip"
                conflict = "; ".join(f"{entry.server_id}:{entry.conflict}" for entry in entry_conflicts)
            elif actual.state == "missing":
                state, action = "create", "create"
            elif any(entry.action in {"create", "update", "prune"} for entry in decisions):
                state, action = "update", "update"
            elif adapter.equivalent(expected, actual):
                if capability.sensitive and _sensitive_permissions_broad(user_home, actual.target):
                    state, action = "permission", "chmod"
                else:
                    state, action = "unchanged", "none"
            else:
                state, action = "update", "update"
        else:
            expected = _conflict_expected(adapter, dict(rendered.servers))
            state, action = "conflict", "skip"
            conflict = f"actual-{actual.state}:{actual.error}"
        expected_hash = hashlib.sha256(expected).hexdigest()
        unowned = any(entry.ownership == "unowned" for entry in decisions)
        actual_state = "unowned" if actual.state == "present" and unowned else actual.state
        resource_id = f"agents:mcp:{tool}"
        items.append(
            SyncPlanItem(
                schema_version=SYNC_PLAN_SCHEMA_VERSION,
                kind="sync-plan-item",
                owner="dotf:agents",
                resource_id=resource_id,
                target=str(adapter.target(user_home)),
                adapter=tool,
                risk=_risk(profile_doc["risk"], (srv["risk"] for srv in selected.values()), sensitive=capability.sensitive),
                required_secrets=rendered.required_secrets,
                declared_runtime_versions=_runtime_versions(selected) if capability.runtime_versions else (),
                entries=tuple(decisions),
                expected_hash=expected_hash,
                current_hash=actual.current_hash,
                installed_hash=None,
                actual_state=actual_state,
                state=state,
                action=action,
                conflict=conflict,
                sensitive=capability.sensitive,
                target_mode=0o600,
            )
        )
    return SyncPlan(
        schema_version=SYNC_PLAN_SCHEMA_VERSION,
        kind="sync-plan",
        profile=profile_doc["id"],
        tools=selected_tools,
        ownership_hash=snapshot.digest,
        items=tuple(items),
    )


def compile_sync_plan(
    catalog: Catalog,
    profile: str | None = None,
    tools: Iterable[str] | None = None,
    *,
    home: Path | None = None,
    state_home: Path | None = None,
) -> SyncPlan:
    """Compile target and per-server ownership decisions without side effects."""
    return _compile_owned_sync_plan(
        catalog, profile, tools, home=home, state_home=state_home,
    )


def apply_sync_plan(
    plan: SyncPlan,
    catalog: Catalog,
    *,
    approved: bool,
    home: Path | None = None,
    state_home: Path | None = None,
    fault: Callable[[str, int, str], None] | None = None,
) -> tuple[tuple[ApplyResult, ...], tuple[str, ...]]:
    """Re-plan under the Agent lock, stage every changed target and manifest, then commit."""
    from managed_runtime import AgentManifestLock
    from mcp_runtime import (
        TransactionOutput,
        commit_outputs,
        mcp_manifest_path,
        next_manifest,
        read_manifest,
        reconcile_payload,
        serialize_manifest,
    )
    from dotf_core.backup import generate_run_id

    plan.validate()
    if not approved:
        raise SyncPlanError("sync plan approval is required before apply")
    user_home = _home(home)
    configured_state = os.environ.get("XDG_STATE_HOME")
    state_root = (
        state_home
        or (Path(configured_state) if configured_state else user_home / ".local" / "state")
    ).expanduser().absolute()
    if _inside(state_root, catalog.root):
        raise SyncPlanError("Agent state directory must be outside the repository")
    for item in plan.items:
        adapter = adapter_for(catalog.vendor_matrix, item.adapter)
        _assert_plan_target(adapter, item, user_home)
        if _inside(Path(item.target), catalog.root):
            raise SyncPlanError(f"runtime target must be outside the repository: {item.resource_id}")
    if any(item.state == "conflict" for item in plan.items):
        detail = "; ".join(f"{item.resource_id}:{item.conflict}" for item in plan.items if item.state == "conflict")
        raise SyncPlanError(detail)

    run_id = "agents-" + generate_run_id()
    secret_values: list[str] = []
    resolver = _secret_resolver(secret_values)
    results: list[ApplyResult] = []
    with AgentManifestLock(user_home, state_root):
        current = _compile_owned_sync_plan(
            catalog, plan.profile, plan.tools, home=user_home, state_home=state_root,
        )
        if current != plan:
            raise SyncPlanError("sync targets or ownership changed after approval")
        snapshot = read_manifest(user_home, state_root)
        if snapshot.status == "malformed" or snapshot.digest != plan.ownership_hash:
            raise SyncPlanError("MCP ownership manifest changed after approval")

        # Keep task-4 retained-inode behavior for a pure permission remediation.
        mutating = [item for item in current.items if item.action in {"create", "update"}]
        chmods = [item for item in current.items if item.action == "chmod"]
        if chmods and not mutating:
            for item in current.items:
                if item.action == "chmod":
                    adapter = adapter_for(catalog.vendor_matrix, item.adapter)
                    changed = _apply_permission_only(item, adapter, catalog, plan.profile, user_home)
                    results.append(ApplyResult(item.resource_id, item.target, "changed" if changed else "unchanged", None))
                else:
                    results.append(ApplyResult(item.resource_id, item.target, "unchanged", None))
            return tuple(results), tuple(secret_values)

        outputs: list[TransactionOutput] = []
        expected_by_tool: dict[str, Mapping[str, object]] = {}
        installed_by_tool: dict[str, Mapping[str, object]] = {}
        targets: dict[str, str] = {}
        for item in current.items:
            adapter = adapter_for(catalog.vendor_matrix, item.adapter)
            selected = catalog.selected_servers(item.adapter, current.profile)
            placeholder = adapter.render(selected)
            expected_by_tool[item.adapter] = placeholder.servers
            targets[item.adapter] = item.target
            actual = adapter.read_actual(user_home)
            _assert_fresh(item, actual)
            if item.action == "none":
                installed_by_tool[item.adapter] = adapter.entries(actual)
                results.append(ApplyResult(item.resource_id, item.target, "unchanged", None))
                continue
            capability = catalog.vendor_matrix.capability(item.adapter)
            rendered = adapter.render(
                selected,
                resolver=resolver if capability.secret_mode == "literal-at-apply" else None,
            )
            payload = reconcile_payload(adapter, actual, rendered.servers, item.entries)
            placeholder_payload = reconcile_payload(adapter, actual, placeholder.servers, item.entries)
            if hashlib.sha256(placeholder_payload).hexdigest() != item.expected_hash:
                raise SyncPlanError(f"declared content changed after approval: {item.resource_id}")
            _secure_target_parents(user_home, Path(item.target), all_ancestors=item.sensitive)
            installed_by_tool[item.adapter] = rendered.servers
            outputs.append(TransactionOutput(
                label=item.resource_id,
                target=Path(item.target),
                root=user_home,
                payload=payload,
                format="json",
                mode=item.target_mode,
                sensitive=item.sensitive,
            ))
            results.append(ApplyResult(item.resource_id, item.target, "changed", None))

        if not outputs:
            return tuple(results), tuple(secret_values)
        manifest = next_manifest(
            snapshot.manifest,
            selected_tools={item.adapter for item in current.items},
            targets=targets,
            expected_entries=expected_by_tool,
            installed_entries=installed_by_tool,
            run_id=run_id,
        )
        manifest_target = mcp_manifest_path(user_home, state_root)
        outputs.append(TransactionOutput(
            label="agents:mcp:manifest",
            target=manifest_target,
            root=Path("/") if not _inside(manifest_target, user_home) else user_home,
            payload=serialize_manifest(manifest),
            format="json",
            mode=0o600,
            sensitive=True,
        ))
        commit_outputs(
            outputs,
            home=user_home,
            state_home=state_root,
            run_id=run_id,
            fault=fault,
        )
    return tuple(results), tuple(secret_values)
