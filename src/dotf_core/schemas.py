"""Strict immutable schemas shared by config deployment and the runner."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, ClassVar, Mapping, TypeVar

PLAN_SCHEMA_VERSION = 1
MANIFEST_SCHEMA_VERSION = 1

PLAN_STATES = frozenset({"unchanged", "create", "update", "prune", "permission", "conflict", "blocked", "failed"})
PLAN_ACTIONS = frozenset({"none", "create", "update", "prune", "chmod", "adopt", "skip", "block"})
STRATEGIES = frozenset({"copy", "merge", "render", "symlink", "install", "config", "doctor"})
RISKS = frozenset({"low", "medium", "high", "sensitive"})


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


def validate_plan_item(value: Mapping[str, Any]) -> PlanItem:
    return PlanItem.from_dict(value)


def validate_managed_manifest(value: Mapping[str, Any]) -> ManagedManifest:
    return ManagedManifest.from_dict(value)
