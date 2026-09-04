"""Strict immutable schemas shared by config, Agent sync, and the runner."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, ClassVar, Mapping, TypeVar

PLAN_SCHEMA_VERSION = 1
MANIFEST_SCHEMA_VERSION = 1
MCP_TRANSACTION_JOURNAL_SCHEMA_VERSION = 1

PLAN_STATES = frozenset({"unchanged", "create", "update", "prune", "permission", "conflict", "blocked", "failed"})
PLAN_ACTIONS = frozenset({"none", "create", "update", "prune", "chmod", "skip", "block"})
STRATEGIES = frozenset({"copy", "merge", "render", "symlink", "install", "config", "doctor"})
RISKS = frozenset({"low", "medium", "high", "sensitive"})
RUN_STATES = frozenset({"pending", "running", "completed", "failed", "interrupted", "failed-rollback"})
ACTION_STATES = frozenset({"pending", "running", "completed", "failed", "blocked", "interrupted"})


class SchemaError(ValueError):
    """Input does not match a supported dotf schema exactly."""


def _type(value: Any, expected: type | tuple[type, ...], name: str) -> None:
    if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
        raise SchemaError(f"{name} has invalid type")


def _text(value: Any, name: str, *, optional: bool = False) -> None:
    if optional and value is None:
        return
    _type(value, str, name)
    if not value:
        raise SchemaError(f"{name} must not be empty")


def _hash(value: Any, name: str, *, optional: bool = False) -> None:
    if optional and value is None:
        return
    _text(value, name)
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise SchemaError(f"{name} must be a lowercase sha256")


def _mode(value: Any, name: str, *, optional: bool = False) -> None:
    if optional and value is None:
        return
    _type(value, int, name)
    if value < 0 or value > 0o777:
        raise SchemaError(f"{name} must be an integer permission mode")


def _enum(value: Any, allowed: frozenset[str], name: str) -> None:
    _text(value, name)
    if value not in allowed:
        raise SchemaError(f"{name} is unsupported: {value}")


T = TypeVar("T", bound="StrictSchema")


@dataclass(frozen=True, slots=True)
class StrictSchema:
    KIND: ClassVar[str]
    VERSION: ClassVar[int]

    def __post_init__(self) -> None:
        self.validate()

    @classmethod
    def from_dict(cls: type[T], value: Mapping[str, Any]) -> T:
        if not isinstance(value, Mapping):
            raise SchemaError(f"{cls.KIND} must be an object")
        expected = {f.name for f in fields(cls)}
        actual = set(value)
        if actual != expected:
            missing = sorted(expected - actual)
            unknown = sorted(actual - expected)
            parts = []
            if missing:
                parts.append("missing: " + ", ".join(missing))
            if unknown:
                parts.append("unknown: " + ", ".join(unknown))
            raise SchemaError(f"invalid {cls.KIND} keys ({'; '.join(parts)})")
        converted = cls._convert(dict(value))
        item = cls(**converted)
        item.validate()
        return item

    @classmethod
    def _convert(cls, value: dict[str, Any]) -> dict[str, Any]:
        return value

    def validate(self) -> None:
        _type(getattr(self, "schema_version"), int, "schema_version")
        if getattr(self, "schema_version") != self.VERSION:
            raise SchemaError(f"unsupported {self.KIND} schema_version")
        if getattr(self, "kind") != self.KIND:
            raise SchemaError(f"invalid kind for {self.KIND}")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PlanItem(StrictSchema):
    KIND: ClassVar[str] = "plan-item"
    VERSION: ClassVar[int] = PLAN_SCHEMA_VERSION

    schema_version: int
    kind: str
    owner: str
    source_identity: str
    expected_hash: str | None
    target: str
    strategy: str
    risk: str
    state: str
    action: str
    conflict_reason: str | None
    required_secrets: tuple[str, ...]
    target_mode: int | None
    sensitive: bool

    @classmethod
    def _convert(cls, value: dict[str, Any]) -> dict[str, Any]:
        secrets = value.get("required_secrets")
        if not isinstance(secrets, (list, tuple)):
            raise SchemaError("required_secrets must be an array")
        value["required_secrets"] = tuple(secrets)
        return value

    def validate(self) -> None:
        StrictSchema.validate(self)
        for name in ("owner", "source_identity", "target"):
            _text(getattr(self, name), name)
        _hash(self.expected_hash, "expected_hash", optional=True)
        _enum(self.strategy, STRATEGIES, "strategy")
        _enum(self.risk, RISKS, "risk")
        _enum(self.state, PLAN_STATES, "state")
        _enum(self.action, PLAN_ACTIONS, "action")
        if self.conflict_reason is not None:
            _text(self.conflict_reason, "conflict_reason")
        _type(self.required_secrets, tuple, "required_secrets")
        if len(set(self.required_secrets)) != len(self.required_secrets):
            raise SchemaError("required_secrets contains duplicates")
        for secret in self.required_secrets:
            _text(secret, "required_secrets item")
        _mode(self.target_mode, "target_mode", optional=True)
        _type(self.sensitive, bool, "sensitive")
        if self.sensitive and self.target_mode is not None and self.target_mode & ~0o600:
            raise SchemaError("sensitive target_mode contains bits outside 0600")
        if self.state == "conflict" and self.conflict_reason is None:
            raise SchemaError("conflict state requires conflict_reason")


@dataclass(frozen=True, slots=True)
class ManagedItem:
    owner: str
    target: str
    source_identity: str
    expected_hash: str
    installed_hash: str
    strategy: str
    mode: int
    run_id: str
    sensitive: bool

    def __post_init__(self) -> None:
        self.validate()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ManagedItem":
        if not isinstance(value, Mapping):
            raise SchemaError("managed item must be an object")
        expected = {f.name for f in fields(cls)}
        if set(value) != expected:
            raise SchemaError("managed item has missing or unknown keys")
        item = cls(**dict(value))
        item.validate()
        return item

    def validate(self) -> None:
        for name in ("owner", "target", "source_identity", "run_id"):
            _text(getattr(self, name), name)
        _hash(self.expected_hash, "expected_hash")
        _hash(self.installed_hash, "installed_hash")
        _enum(self.strategy, STRATEGIES, "strategy")
        _mode(self.mode, "mode")
        _type(self.sensitive, bool, "sensitive")
        if self.sensitive and self.mode & ~0o600:
            raise SchemaError("sensitive managed mode contains bits outside 0600")


@dataclass(frozen=True, slots=True)
class ManagedManifest(StrictSchema):
    KIND: ClassVar[str] = "managed-manifest"
    VERSION: ClassVar[int] = MANIFEST_SCHEMA_VERSION

    schema_version: int
    kind: str
    generated_at: str
    items: tuple[ManagedItem, ...]

    @classmethod
    def _convert(cls, value: dict[str, Any]) -> dict[str, Any]:
        raw = value.get("items")
        if not isinstance(raw, (list, tuple)):
            raise SchemaError("items must be an array")
        value["items"] = tuple(item if isinstance(item, ManagedItem) else ManagedItem.from_dict(item) for item in raw)
        return value

    def validate(self) -> None:
        StrictSchema.validate(self)
        _text(self.generated_at, "generated_at")
        _type(self.items, tuple, "items")
        targets = []
        for item in self.items:
            if not isinstance(item, ManagedItem):
                raise SchemaError("items contains invalid value")
            item.validate()
            targets.append(item.target)
        if len(set(targets)) != len(targets):
            raise SchemaError("manifest contains duplicate targets")


@dataclass(frozen=True, slots=True)
class JournalAction:
    module: str
    action: str
    status: str
    started_at: str
    ended_at: str | None
    duration_ms: int | None
    reason_code: str | None
    reason: str | None
    before_hash: str | None
    after_hash: str | None

    def __post_init__(self) -> None:
        self.validate()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "JournalAction":
        if not isinstance(value, Mapping) or set(value) != {f.name for f in fields(cls)}:
            raise SchemaError("journal action has missing or unknown keys")
        item = cls(**dict(value))
        item.validate()
        return item

    def validate(self) -> None:
        _text(self.module, "module")
        _text(self.action, "action")
        _enum(self.status, ACTION_STATES, "action status")
        _text(self.started_at, "started_at")
        if self.ended_at is not None:
            _text(self.ended_at, "ended_at")
        if self.duration_ms is not None:
            _type(self.duration_ms, int, "duration_ms")
            if self.duration_ms < 0:
                raise SchemaError("duration_ms must be non-negative")
        for name in ("reason_code", "reason"):
            if getattr(self, name) is not None:
                _text(getattr(self, name), name)
        _hash(self.before_hash, "before_hash", optional=True)
        _hash(self.after_hash, "after_hash", optional=True)


@dataclass(frozen=True, slots=True)
class McpTransactionJournal(StrictSchema):
    KIND: ClassVar[str] = "mcp-transaction-journal"
    VERSION: ClassVar[int] = MCP_TRANSACTION_JOURNAL_SCHEMA_VERSION

    schema_version: int
    kind: str
    run_id: str
    status: str
    started_at: str
    updated_at: str
    plan_version: int
    actions: tuple[JournalAction, ...]

    @classmethod
    def _convert(cls, value: dict[str, Any]) -> dict[str, Any]:
        raw = value.get("actions")
        if not isinstance(raw, (list, tuple)):
            raise SchemaError("actions must be an array")
        value["actions"] = tuple(item if isinstance(item, JournalAction) else JournalAction.from_dict(item) for item in raw)
        return value

    def validate(self) -> None:
        StrictSchema.validate(self)
        for name in ("run_id", "started_at", "updated_at"):
            _text(getattr(self, name), name)
        _enum(self.status, RUN_STATES, "status")
        _type(self.plan_version, int, "plan_version")
        if self.plan_version < 1:
            raise SchemaError("plan_version must be positive")
        _type(self.actions, tuple, "actions")
        for action in self.actions:
            if not isinstance(action, JournalAction):
                raise SchemaError("actions contains invalid value")
            action.validate()


def validate_plan_item(value: Mapping[str, Any]) -> PlanItem:
    return PlanItem.from_dict(value)


def validate_managed_manifest(value: Mapping[str, Any]) -> ManagedManifest:
    return ManagedManifest.from_dict(value)


def validate_mcp_transaction_journal(value: Mapping[str, Any]) -> McpTransactionJournal:
    return McpTransactionJournal.from_dict(value)


SYNC_PLAN_SCHEMA_VERSION = 1
MCP_MANIFEST_SCHEMA_VERSION = 1
SYNC_ACTUAL_STATES = frozenset({"missing", "present", "unowned", "malformed", "unsafe"})
MCP_OWNERSHIP_STATES = frozenset({"owned", "unowned"})


@dataclass(frozen=True, slots=True)
class McpManagedItem:
    tool: str
    server_id: str
    target: str
    expected_hash: str
    installed_hash: str
    run_id: str

    def __post_init__(self) -> None:
        self.validate()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "McpManagedItem":
        if not isinstance(value, Mapping) or set(value) != {f.name for f in fields(cls)}:
            raise SchemaError("MCP managed item has missing or unknown keys")
        return cls(**dict(value))

    def validate(self) -> None:
        for name in ("tool", "server_id", "target", "run_id"):
            _text(getattr(self, name), name)
        _hash(self.expected_hash, "expected_hash")
        _hash(self.installed_hash, "installed_hash")


@dataclass(frozen=True, slots=True)
class McpManagedManifest(StrictSchema):
    KIND: ClassVar[str] = "mcp-managed-manifest"
    VERSION: ClassVar[int] = MCP_MANIFEST_SCHEMA_VERSION

    schema_version: int
    kind: str
    generated_at: str
    items: tuple[McpManagedItem, ...]

    @classmethod
    def _convert(cls, value: dict[str, Any]) -> dict[str, Any]:
        raw = value.get("items")
        if not isinstance(raw, (list, tuple)):
            raise SchemaError("items must be an array")
        value["items"] = tuple(
            item if isinstance(item, McpManagedItem) else McpManagedItem.from_dict(item)
            for item in raw
        )
        return value

    def validate(self) -> None:
        StrictSchema.validate(self)
        _text(self.generated_at, "generated_at")
        _type(self.items, tuple, "items")
        keys: list[tuple[str, str]] = []
        for item in self.items:
            if not isinstance(item, McpManagedItem):
                raise SchemaError("items contains invalid MCP managed item")
            item.validate()
            keys.append((item.tool, item.server_id))
        if len(keys) != len(set(keys)):
            raise SchemaError("MCP manifest contains duplicate tool/server ownership")


@dataclass(frozen=True, slots=True)
class McpEntryPlan:
    server_id: str
    ownership: str
    expected_hash: str | None
    current_hash: str | None
    installed_hash: str | None
    state: str
    action: str
    conflict: str | None

    def __post_init__(self) -> None:
        self.validate()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "McpEntryPlan":
        if not isinstance(value, Mapping) or set(value) != {f.name for f in fields(cls)}:
            raise SchemaError("MCP entry plan has missing or unknown keys")
        return cls(**dict(value))

    def validate(self) -> None:
        _text(self.server_id, "server_id")
        _enum(self.ownership, MCP_OWNERSHIP_STATES, "ownership")
        _hash(self.expected_hash, "expected_hash", optional=True)
        _hash(self.current_hash, "current_hash", optional=True)
        _hash(self.installed_hash, "installed_hash", optional=True)
        _enum(self.state, PLAN_STATES, "MCP entry state")
        _enum(self.action, PLAN_ACTIONS, "MCP entry action")
        if self.conflict is not None:
            _text(self.conflict, "conflict")
        if self.state == "conflict" and self.conflict is None:
            raise SchemaError("MCP entry conflict requires conflict")
        if self.state != "conflict" and self.conflict is not None:
            raise SchemaError("only MCP entry conflicts may contain conflict")
        if self.ownership == "unowned" and (self.action != "none" or self.state != "unchanged"):
            raise SchemaError("unowned MCP entries must be preserved unchanged")


def validate_mcp_managed_manifest(value: Mapping[str, Any]) -> McpManagedManifest:
    return McpManagedManifest.from_dict(value)


@dataclass(frozen=True, slots=True)
class RuntimeVersion:
    resource_id: str
    package: str
    version: str

    def __post_init__(self) -> None:
        self.validate()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RuntimeVersion":
        if not isinstance(value, Mapping) or set(value) != {"resource_id", "package", "version"}:
            raise SchemaError("runtime version has missing or unknown keys")
        return cls(**dict(value))

    def validate(self) -> None:
        _text(self.resource_id, "runtime resource_id")
        _text(self.package, "runtime package")
        _text(self.version, "runtime version")


@dataclass(frozen=True, slots=True)
class SyncPlanItem(StrictSchema):
    """One immutable Agent target decision; it never contains secret values."""

    KIND: ClassVar[str] = "sync-plan-item"
    VERSION: ClassVar[int] = SYNC_PLAN_SCHEMA_VERSION

    schema_version: int
    kind: str
    owner: str
    resource_id: str
    target: str
    adapter: str
    risk: str
    required_secrets: tuple[str, ...]
    declared_runtime_versions: tuple[RuntimeVersion, ...]
    entries: tuple[McpEntryPlan, ...]
    expected_hash: str
    current_hash: str | None
    installed_hash: str | None
    actual_state: str
    state: str
    action: str
    conflict: str | None
    sensitive: bool
    target_mode: int

    @classmethod
    def _convert(cls, value: dict[str, Any]) -> dict[str, Any]:
        secrets = value.get("required_secrets")
        runtimes = value.get("declared_runtime_versions")
        entries = value.get("entries")
        if not isinstance(secrets, (list, tuple)):
            raise SchemaError("required_secrets must be an array")
        if not isinstance(runtimes, (list, tuple)):
            raise SchemaError("declared_runtime_versions must be an array")
        if not isinstance(entries, (list, tuple)):
            raise SchemaError("entries must be an array")
        value["required_secrets"] = tuple(secrets)
        value["declared_runtime_versions"] = tuple(
            item if isinstance(item, RuntimeVersion) else RuntimeVersion.from_dict(item)
            for item in runtimes
        )
        value["entries"] = tuple(
            item if isinstance(item, McpEntryPlan) else McpEntryPlan.from_dict(item)
            for item in entries
        )
        return value

    def validate(self) -> None:
        StrictSchema.validate(self)
        for name in ("owner", "resource_id", "target", "adapter"):
            _text(getattr(self, name), name)
        _enum(self.risk, RISKS, "risk")
        _type(self.required_secrets, tuple, "required_secrets")
        if len(set(self.required_secrets)) != len(self.required_secrets):
            raise SchemaError("required_secrets contains duplicates")
        for secret in self.required_secrets:
            _text(secret, "required_secrets item")
            if not secret.replace("_", "A").isalnum() or secret.upper() != secret:
                raise SchemaError("required_secrets items must be environment variable names")
        _type(self.declared_runtime_versions, tuple, "declared_runtime_versions")
        runtime_ids = []
        for runtime in self.declared_runtime_versions:
            if not isinstance(runtime, RuntimeVersion):
                raise SchemaError("declared_runtime_versions contains invalid value")
            runtime.validate()
            runtime_ids.append(runtime.resource_id)
        if len(runtime_ids) != len(set(runtime_ids)):
            raise SchemaError("declared_runtime_versions contains duplicate resource ids")
        _type(self.entries, tuple, "entries")
        entry_ids = []
        for entry in self.entries:
            if not isinstance(entry, McpEntryPlan):
                raise SchemaError("entries contains invalid MCP entry plan")
            entry.validate()
            entry_ids.append(entry.server_id)
        if len(entry_ids) != len(set(entry_ids)):
            raise SchemaError("entries contains duplicate MCP server ids")
        _hash(self.expected_hash, "expected_hash")
        _hash(self.current_hash, "current_hash", optional=True)
        _hash(self.installed_hash, "installed_hash", optional=True)
        _enum(self.actual_state, SYNC_ACTUAL_STATES, "actual_state")
        _enum(self.state, PLAN_STATES, "state")
        _enum(self.action, PLAN_ACTIONS, "action")
        if self.conflict is not None:
            _text(self.conflict, "conflict")
        if self.state == "conflict" and self.conflict is None:
            raise SchemaError("conflict state requires conflict")
        if self.state != "conflict" and self.conflict is not None:
            raise SchemaError("only conflict state may contain conflict")
        if (self.state == "permission") != (self.action == "chmod"):
            raise SchemaError("permission state requires chmod action")
        _type(self.sensitive, bool, "sensitive")
        if self.action == "chmod" and not self.sensitive:
            raise SchemaError("chmod action requires a sensitive target")
        _mode(self.target_mode, "target_mode")
        if self.sensitive and self.target_mode & ~0o600:
            raise SchemaError("sensitive target_mode contains bits outside 0600")


@dataclass(frozen=True, slots=True)
class SyncPlan(StrictSchema):
    """Machine-readable side-effect-free Agent sync plan."""

    KIND: ClassVar[str] = "sync-plan"
    VERSION: ClassVar[int] = SYNC_PLAN_SCHEMA_VERSION

    schema_version: int
    kind: str
    profile: str
    tools: tuple[str, ...]
    ownership_hash: str | None
    items: tuple[SyncPlanItem, ...]

    @classmethod
    def _convert(cls, value: dict[str, Any]) -> dict[str, Any]:
        tools = value.get("tools")
        items = value.get("items")
        if not isinstance(tools, (list, tuple)):
            raise SchemaError("tools must be an array")
        if not isinstance(items, (list, tuple)):
            raise SchemaError("items must be an array")
        value["tools"] = tuple(tools)
        value["items"] = tuple(
            item if isinstance(item, SyncPlanItem) else SyncPlanItem.from_dict(item)
            for item in items
        )
        return value

    def validate(self) -> None:
        StrictSchema.validate(self)
        _text(self.profile, "profile")
        _type(self.tools, tuple, "tools")
        if len(self.tools) != len(set(self.tools)):
            raise SchemaError("tools contains duplicates")
        for tool in self.tools:
            _text(tool, "tools item")
        _hash(self.ownership_hash, "ownership_hash", optional=True)
        _type(self.items, tuple, "items")
        resource_ids = []
        targets = []
        for item in self.items:
            if not isinstance(item, SyncPlanItem):
                raise SchemaError("items contains invalid value")
            item.validate()
            resource_ids.append(item.resource_id)
            targets.append(item.target)
        if len(resource_ids) != len(set(resource_ids)):
            raise SchemaError("sync plan contains duplicate resource ids")
        if len(targets) != len(set(targets)):
            raise SchemaError("sync plan contains duplicate targets")


def validate_sync_plan(value: Mapping[str, Any]) -> SyncPlan:
    return SyncPlan.from_dict(value)
