#!/usr/bin/env python3
"""Pure MCP adapter rendering, actual-state reads, and non-reconciling merges."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from catalog import VendorCapability, VendorMatrix
from common import PLACEHOLDER_OK, entries_equivalent, render_server_for_tool

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in os.sys.path:
    os.sys.path.insert(0, str(_SCRIPTS))

from dotf_core.paths import PathBoundaryError, assert_no_symlinks, open_nofollow  # noqa: E402

ACTUAL_STATES = frozenset({"missing", "present", "malformed", "unsafe"})
SecretResolver = Callable[[str], str]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _get_block(document: Mapping[str, Any], path: tuple[str, ...]) -> dict[str, Any]:
    current: Any = document
    for component in path:
        if not isinstance(current, dict):
            raise ValueError("managed MCP parent is not an object")
        if component not in current:
            return {}
        current = current[component]
    if not isinstance(current, dict):
        raise ValueError("managed MCP block is not an object")
    return current


def _put_block(document: Mapping[str, Any], path: tuple[str, ...], block: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(document)
    current = result
    for component in path[:-1]:
        child = current.get(component)
        child_copy = dict(child) if isinstance(child, dict) else {}
        current[component] = child_copy
        current = child_copy
    current[path[-1]] = dict(block)
    return result


def _materialize(value: Any, resolver: SecretResolver) -> Any:
    if isinstance(value, dict):
        return {key: _materialize(item, resolver) for key, item in value.items()}
    if isinstance(value, list):
        return [_materialize(item, resolver) for item in value]
    if not isinstance(value, str):
        return value

    def replace(match: Any) -> str:
        token = match.group(0)
        name = token[2:-1] if token.startswith("${") else token[5:-1]
        resolved = resolver(name)
        if not resolved:
            raise ValueError(f"required secret is unavailable: {name}")
        return resolved

    return PLACEHOLDER_OK.sub(replace, value)


@dataclass(frozen=True, slots=True)
class ActualDocument:
    state: str
    target: Path
    raw: bytes | None
    current_hash: str | None
    error: str | None

    def __post_init__(self) -> None:
        if self.state not in ACTUAL_STATES:
            raise ValueError(f"unsupported actual state: {self.state}")
        if self.state == "missing" and (self.raw is not None or self.current_hash is not None):
            raise ValueError("missing actual document cannot contain bytes")
        if self.state == "present" and (self.raw is None or self.current_hash is None):
            raise ValueError("present actual document requires bytes and hash")
        if self.state in {"malformed", "unsafe"} and not self.error:
            raise ValueError("invalid actual document requires a stable error category")

    def document(self) -> dict[str, Any]:
        if self.state != "present" or self.raw is None:
            raise ValueError(f"actual document is not readable: {self.state}")
        value = json.loads(self.raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("target root is not an object")
        return value


@dataclass(frozen=True, slots=True)
class RenderedAdapter:
    servers: Mapping[str, Any]
    required_secrets: tuple[str, ...]


class JsonMcpAdapter:
    """Adapter behavior parameterized by one vendor capability record."""

    __slots__ = ("capability",)

    def __init__(self, capability: VendorCapability) -> None:
        if not capability.mcp or capability.adapter == "none":
            raise ValueError(f"vendor {capability.id} has no MCP adapter")
        self.capability = capability

    @property
    def tool(self) -> str:
        return self.capability.id

    def target(self, home: Path) -> Path:
        assert self.capability.target is not None
        relative = self.capability.target[2:]
        return home / relative

    def read_actual(self, home: Path) -> ActualDocument:
        target = self.target(home)
        try:
            assert_no_symlinks(home, target, missing_ok=True)
            item = os.lstat(target)
        except FileNotFoundError:
            return ActualDocument("missing", target, None, None, None)
        except (PathBoundaryError, NotADirectoryError) as exc:
            return ActualDocument("unsafe", target, None, None, type(exc).__name__)
        if not stat.S_ISREG(item.st_mode):
            return ActualDocument("malformed", target, None, None, "not-regular-file")
        try:
            fd = open_nofollow(home, target)
            try:
                chunks = []
                while True:
                    chunk = os.read(fd, 1024 * 1024)
                    if not chunk:
                        break
                    chunks.append(chunk)
                raw = b"".join(chunks)
            finally:
                os.close(fd)
            value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_json_object)
            if not isinstance(value, dict):
                raise ValueError("root-not-object")
            _get_block(value, self.capability.block_path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            return ActualDocument("malformed", target, None, None, type(exc).__name__)
        return ActualDocument("present", target, raw, _sha256(raw), None)

    def render(
        self,
        selected_servers: Mapping[str, Mapping[str, Any]],
        *,
        resolver: SecretResolver | None = None,
    ) -> RenderedAdapter:
        rendered: dict[str, Any] = {}
        required: set[str] = set()
        for server_id, server in selected_servers.items():
            transport = server.get("transport")
            if transport not in self.capability.transports:
                raise ValueError(f"vendor {self.tool} does not support transport {transport}")
            auth = server.get("auth") or {}
            if isinstance(auth.get("env"), str):
                required.add(auth["env"])
            entry = render_server_for_tool(server_id, dict(server), self.tool)
            for token in _collect_tokens(entry):
                required.add(token)
            rendered[server_id] = entry
        if resolver is not None:
            if self.capability.secret_mode != "literal-at-apply":
                raise ValueError(f"vendor {self.tool} does not materialize secrets")
            rendered = _materialize(rendered, resolver)
        return RenderedAdapter(rendered, tuple(sorted(required)))

    def entries(self, actual: ActualDocument) -> dict[str, Any]:
        """Return a detached MCP block for entry-level ownership decisions."""
        if actual.state == "missing":
            return {}
        if actual.state != "present":
            raise ValueError(f"cannot read entries from {actual.state} target")
        return dict(_get_block(actual.document(), self.capability.block_path))

    def reconcile(
        self,
        actual: ActualDocument,
        managed: Mapping[str, Any],
        *,
        prune_ids: set[str] | frozenset[str] = frozenset(),
    ) -> bytes:
        """Preserve unowned ids, prune only caller-proven stale owned ids, and update managed ids."""
        if actual.state == "missing":
            document: dict[str, Any] = {}
        elif actual.state == "present":
            document = actual.document()
        else:
            raise ValueError(f"cannot reconcile {actual.state} target")
        existing = _get_block(document, self.capability.block_path)
        merged = {key: value for key, value in existing.items() if key not in prune_ids}
        merged.update(managed)
        return _json_bytes(_put_block(document, self.capability.block_path, merged))

    def merge(self, actual: ActualDocument, managed: Mapping[str, Any]) -> bytes:
        """Compatibility merge that never prunes entries without ownership proof."""
        return self.reconcile(actual, managed)

    def unowned_ids(self, actual: ActualDocument, selected_ids: set[str]) -> tuple[str, ...]:
        if actual.state != "present":
            return ()
        block = _get_block(actual.document(), self.capability.block_path)
        return tuple(sorted(set(block) - selected_ids))

    def equivalent(self, expected: bytes, actual: ActualDocument) -> bool:
        if actual.state != "present" or actual.raw is None:
            return False
        try:
            expected_doc = json.loads(expected.decode("utf-8"))
            actual_doc = json.loads(actual.raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            return False
        return entries_equivalent(expected_doc, actual_doc)


def _collect_tokens(value: Any) -> tuple[str, ...]:
    found: set[str] = set()

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)
        elif isinstance(item, str):
            for match in PLACEHOLDER_OK.finditer(item):
                token = match.group(0)
                found.add(token[2:-1] if token.startswith("${") else token[5:-1])

    visit(value)
    return tuple(sorted(found))


def adapter_for(matrix: VendorMatrix, tool: str) -> JsonMcpAdapter:
    return JsonMcpAdapter(matrix.capability(tool))
