#!/usr/bin/env python3
"""Strict, versioned Agent catalog loader (manifest / tools / env / security / profiles)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import yaml

CATALOG_VERSION = 1
RISKS = frozenset({"low", "medium", "high"})
MODULE_IDS = frozenset({"tools", "env", "security", "agents"})


class CatalogError(ValueError):
    """A committed Agent catalog document violates its exact schema."""


class _UniqueLoader(yaml.SafeLoader):
    pass


def _mapping(loader: _UniqueLoader, node: yaml.nodes.MappingNode, deep: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise CatalogError("catalog mapping keys must be strings")
        if key in result:
            raise CatalogError(f"duplicate key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CatalogError(f"missing catalog document: {path}")
    try:
        value = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueLoader)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise CatalogError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CatalogError(f"{path} must contain an object")
    return value


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CatalogError(f"{label} must be an object")
    actual = set(value)
    if actual != keys:
        missing = sorted(keys - actual)
        unknown = sorted(actual - keys)
        details = []
        if missing:
            details.append("missing keys: " + ", ".join(missing))
        if unknown:
            details.append("unknown keys: " + ", ".join(unknown))
        raise CatalogError(f"{label} has invalid schema ({'; '.join(details)})")
    return value


def _version(doc: Mapping[str, Any], label: str) -> None:
    if type(doc.get("version")) is not int or doc["version"] != CATALOG_VERSION:
        raise CatalogError(f"{label}.version must be {CATALOG_VERSION}")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise CatalogError(f"{label} must be a non-empty string")
    return value


def _boolean(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise CatalogError(f"{label} must be boolean")
    return value


def _strings(value: Any, label: str, *, unique: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise CatalogError(f"{label} must be an array of non-empty strings")
    if unique and len(value) != len(set(value)):
        raise CatalogError(f"{label} contains duplicates")
    return tuple(value)


def _refs(values: tuple[str, ...], known: set[str] | frozenset[str], label: str) -> None:
    unknown = sorted(set(values) - set(known))
    if unknown:
        raise CatalogError(f"{label} references unknown ids: {', '.join(unknown)}")


@dataclass(frozen=True, slots=True)
class CatalogDocuments:
    manifest: Mapping[str, Any]
    tools: Mapping[str, Any]
    env_schema: Mapping[str, Any]
    security: Mapping[str, Any]
    profiles: Mapping[str, Mapping[str, Any]]


def load_manifest_tools(root: Path) -> tuple[str, ...]:
    """Tool id list from manifest.yaml without loading the full catalog."""
    doc = _load(root / "agents" / "env" / "manifest.yaml")
    return _strings(doc.get("tools"), "manifest.tools")


def _validate_manifest(doc: dict[str, Any], profiles: set[str]) -> None:
    _exact(doc, {"version", "tools", "default_profile", "modules"}, "manifest.yaml")
    _version(doc, "manifest.yaml")
    tools = _strings(doc["tools"], "manifest.tools")
    _text(doc["default_profile"], "manifest.default_profile")
    _refs((doc["default_profile"],), profiles, "manifest.default_profile")
    if not isinstance(doc["modules"], dict) or set(doc["modules"]) != MODULE_IDS:
        raise CatalogError("manifest.modules must declare every known module exactly once")
    for module_id, raw in doc["modules"].items():
        item = _exact(raw, {"enabled", "tools", "exclude"}, f"manifest.modules.{module_id}")
        _boolean(item["enabled"], f"manifest.modules.{module_id}.enabled")
        allowed = _strings(item["tools"], f"manifest.modules.{module_id}.tools")
        excluded = _strings(item["exclude"], f"manifest.modules.{module_id}.exclude")
        _refs(allowed + excluded, set(tools), f"manifest.modules.{module_id}")
        if set(allowed) & set(excluded):
            raise CatalogError(f"manifest.modules.{module_id} tools/exclude overlap")


def _validate_profiles(profiles: dict[str, dict[str, Any]]) -> None:
    for profile_id, doc in profiles.items():
        _exact(doc, {"version", "id", "description", "risk", "modules"}, f"profile {profile_id}")
        _version(doc, f"profile {profile_id}")
        if doc["id"] != profile_id:
            raise CatalogError(f"profile {profile_id}.id must match its filename")
        _text(doc["description"], f"profile {profile_id}.description")
        if doc["risk"] not in RISKS:
            raise CatalogError(f"profile {profile_id}.risk is unsupported")
        _refs(_strings(doc["modules"], f"profile {profile_id}.modules"), MODULE_IDS, f"profile {profile_id}.modules")


def _validate_simple_documents(docs: dict[str, dict[str, Any]], tools: set[str], profiles: set[str]) -> None:
    tools_doc = docs["tools"]
    _exact(tools_doc, {"version", "tools"}, "tools.yaml")
    _version(tools_doc, "tools.yaml")
    if not isinstance(tools_doc["tools"], dict):
        raise CatalogError("tools.yaml.tools must be an object")
    tool_keys = {"command", "version_cmd", "required", "profiles", "install_hint"}
    for tool_id, raw in tools_doc["tools"].items():
        item = _exact(raw, tool_keys, f"runtime tool {tool_id}")
        _text(item["command"], f"runtime tool {tool_id}.command")
        _strings(item["version_cmd"], f"runtime tool {tool_id}.version_cmd", unique=False)
        _boolean(item["required"], f"runtime tool {tool_id}.required")
        _refs(_strings(item["profiles"], f"runtime tool {tool_id}.profiles"), profiles, f"runtime tool {tool_id}.profiles")
        _text(item["install_hint"], f"runtime tool {tool_id}.install_hint")

    env = docs["env_schema"]
    _exact(env, {"version", "variables"}, "env.schema.yaml")
    _version(env, "env.schema.yaml")
    if not isinstance(env["variables"], dict):
        raise CatalogError("env.schema.yaml.variables must be an object")
    for name, raw in env["variables"].items():
        item = _allowed_env(raw, f"env variable {name}")
        _text(item["purpose"], f"env variable {name}.purpose")
        _boolean(item["required"], f"env variable {name}.required")
        _boolean(item["sensitive"], f"env variable {name}.sensitive")
        _refs(_strings(item["profiles"], f"env variable {name}.profiles"), profiles, f"env variable {name}.profiles")
        if "tools" in item:
            _refs(_strings(item["tools"], f"env variable {name}.tools"), tools, f"env variable {name}.tools")
        if item["check"] not in {"present", "present_if_set"}:
            raise CatalogError(f"env variable {name}.check is unsupported")
        _text(item["setup_hint"], f"env variable {name}.setup_hint")

    security = docs["security"]
    _exact(
        security,
        {
            "version", "risk_levels", "defaults", "sensitive_patterns",
            "sensitive_backups", "private_runtime", "scan",
        },
        "security.yaml",
    )
    _version(security, "security.yaml")
    if set(security["risk_levels"]) != RISKS:
        raise CatalogError("security.yaml.risk_levels must define low, medium, high")
    for risk, raw in security["risk_levels"].items():
        _exact(raw, {"description"}, f"security risk {risk}")
        _text(raw["description"], f"security risk {risk}.description")
    defaults = _exact(security["defaults"], {"enable_high_risk", "never_commit_secrets"}, "security.defaults")
    for key, value in defaults.items():
        _boolean(value, f"security.defaults.{key}")
    if not isinstance(security["sensitive_patterns"], list):
        raise CatalogError("security.sensitive_patterns must be an array")
    for index, raw in enumerate(security["sensitive_patterns"]):
        item = _exact(raw, {"name", "pattern", "severity"}, f"security pattern {index}")
        _text(item["name"], f"security pattern {index}.name")
        _text(item["pattern"], f"security pattern {index}.pattern")
        if item["severity"] not in {"warn", "fail"}:
            raise CatalogError(f"security pattern {index}.severity is unsupported")

    backups = _exact(
        security["sensitive_backups"],
        {"retention_days", "metadata_filename"},
        "security.sensitive_backups",
    )
    retention = backups["retention_days"]
    if type(retention) is not int or retention < 1 or retention > 365:
        raise CatalogError("security.sensitive_backups.retention_days must be an integer in 1..365")
    metadata_filename = _text(
        backups["metadata_filename"],
        "security.sensitive_backups.metadata_filename",
    )
    if "/" in metadata_filename or metadata_filename in {".", ".."}:
        raise CatalogError("security.sensitive_backups.metadata_filename must be one path component")

    private_runtime = _exact(
        security["private_runtime"],
        {"forbidden_in_repo"},
        "security.private_runtime",
    )
    _strings(
        private_runtime["forbidden_in_repo"],
        "security.private_runtime.forbidden_in_repo",
    )

    scan = _exact(
        security["scan"],
        {"rule_version", "tracked_roots", "text_extensions", "exclude"},
        "security.scan",
    )
    if type(scan["rule_version"]) is not int or scan["rule_version"] < 1:
        raise CatalogError("security.scan.rule_version must be a positive integer")
    tracked_roots = _strings(scan["tracked_roots"], "security.scan.tracked_roots")
    extensions = _strings(scan["text_extensions"], "security.scan.text_extensions")
    _strings(scan["exclude"], "security.scan.exclude")
    if any(root.startswith(("/", "../")) or root in {".", ".."} for root in tracked_roots):
        raise CatalogError("security.scan.tracked_roots must be repository-relative")
    if any(not extension.startswith(".") or "/" in extension for extension in extensions):
        raise CatalogError("security.scan.text_extensions must contain suffixes")


def _allowed_env(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CatalogError(f"{label} must be an object")
    required = {"purpose", "required", "sensitive", "profiles", "check", "setup_hint"}
    optional = {"tools"}
    missing = required - set(value)
    unknown = set(value) - required - optional
    if missing or unknown:
        details = []
        if missing:
            details.append("missing keys: " + ", ".join(sorted(missing)))
        if unknown:
            details.append("unknown keys: " + ", ".join(sorted(unknown)))
        raise CatalogError(f"{label} has invalid schema ({'; '.join(details)})")
    return value


def load_catalog_documents(root: Path) -> CatalogDocuments:
    env_dir = root / "agents" / "env"
    profile_dir = env_dir / "profiles"
    profiles: dict[str, dict[str, Any]] = {}
    for path in sorted(profile_dir.glob("*.yaml"), key=lambda item: item.name.encode("utf-8")):
        if path.stem in profiles:
            raise CatalogError(f"duplicate profile id: {path.stem}")
        profiles[path.stem] = _load(path)
    if not profiles:
        raise CatalogError("no profiles declared")
    docs = {
        "manifest": _load(env_dir / "manifest.yaml"),
        "tools": _load(env_dir / "tools.yaml"),
        "env_schema": _load(env_dir / "env.schema.yaml"),
        "security": _load(env_dir / "security.yaml"),
    }
    _validate_profiles(profiles)
    _validate_manifest(docs["manifest"], set(profiles))
    _validate_simple_documents(docs, set(_strings(docs["manifest"]["tools"], "manifest.tools")), set(profiles))
    return CatalogDocuments(
        MappingProxyType(docs["manifest"]), MappingProxyType(docs["tools"]),
        MappingProxyType(docs["env_schema"]), MappingProxyType(docs["security"]),
        MappingProxyType({key: MappingProxyType(value) for key, value in profiles.items()}),
    )
