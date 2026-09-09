#!/usr/bin/env python3
"""Strict, versioned Agent catalog and vendor capability matrix loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping

import yaml

CATALOG_VERSION = 1
VENDOR_ADAPTERS = frozenset({"cursor", "kiro", "opencode", "kimi-code", "zcode", "none"})
TRANSPORTS = frozenset({"stdio", "streamable-http"})
SECRET_MODES = frozenset({"runtime-placeholder", "environment-reference", "literal-at-apply", "unsupported"})
EXACT_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")
PLACEHOLDER = re.compile(r"\$\{([^}]+)\}|\{env:([^}]+)\}")
RISKS = frozenset({"low", "medium", "high"})
MODULE_IDS = frozenset({"mcp", "browser", "tools", "env", "security", "agents"})


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


def _allowed(value: Any, required: set[str], optional: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CatalogError(f"{label} must be an object")
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


def _placeholder_refs(value: Any) -> tuple[str, ...]:
    """Collect every environment placeholder from a validated catalog value."""
    found: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for nested in item.values():
                visit(nested)
        elif isinstance(item, list):
            for nested in item:
                visit(nested)
        elif isinstance(item, str):
            found.extend(left or right for left, right in PLACEHOLDER.findall(item))

    visit(value)
    return tuple(found)


@dataclass(frozen=True, slots=True)
class VendorCapability:
    id: str
    cli: bool
    mcp: bool
    adapter: str
    target: str | None
    block_path: tuple[str, ...]
    transports: tuple[str, ...]
    secret_mode: str
    runtime_versions: bool
    sensitive: bool
    docs: str


@dataclass(frozen=True, slots=True)
class VendorMatrix:
    version: int
    vendors: Mapping[str, VendorCapability]

    @property
    def cli_tools(self) -> tuple[str, ...]:
        return tuple(name for name, item in self.vendors.items() if item.cli)

    @property
    def adapter_tools(self) -> tuple[str, ...]:
        return tuple(name for name, item in self.vendors.items() if item.mcp)

    def capability(self, tool: str) -> VendorCapability:
        try:
            return self.vendors[tool]
        except KeyError as exc:
            raise CatalogError(f"unknown vendor: {tool}") from exc


@dataclass(frozen=True, slots=True)
class CatalogDocuments:
    manifest: Mapping[str, Any]
    tools: Mapping[str, Any]
    env_schema: Mapping[str, Any]
    security: Mapping[str, Any]
    browser: Mapping[str, Any]
    servers: Mapping[str, Any]
    profiles: Mapping[str, Mapping[str, Any]]
    vendors: VendorMatrix


def load_vendor_matrix(root: Path) -> VendorMatrix:
    path = root / "agents" / "env" / "vendors.yaml"
    doc = _exact(_load(path), {"version", "vendors"}, "vendors.yaml")
    _version(doc, "vendors.yaml")
    if not isinstance(doc["vendors"], dict) or not doc["vendors"]:
        raise CatalogError("vendors.yaml.vendors must be a non-empty object")
    items: dict[str, VendorCapability] = {}
    keys = {"cli", "mcp", "adapter", "target", "block_path", "transports", "secret_mode", "runtime_versions", "sensitive", "docs"}
    for vendor_id, raw in doc["vendors"].items():
        _text(vendor_id, "vendor id")
        item = _exact(raw, keys, f"vendor {vendor_id}")
        cli = _boolean(item["cli"], f"vendor {vendor_id}.cli")
        mcp = _boolean(item["mcp"], f"vendor {vendor_id}.mcp")
        adapter = _text(item["adapter"], f"vendor {vendor_id}.adapter")
        if adapter not in VENDOR_ADAPTERS:
            raise CatalogError(f"vendor {vendor_id}.adapter is unsupported: {adapter}")
        target = item["target"]
        if target is not None:
            _text(target, f"vendor {vendor_id}.target")
            if not target.startswith("~/"):
                raise CatalogError(f"vendor {vendor_id}.target must be a user-level ~/ path")
        block_path = _strings(item["block_path"], f"vendor {vendor_id}.block_path")
        transports = _strings(item["transports"], f"vendor {vendor_id}.transports")
        _refs(transports, TRANSPORTS, f"vendor {vendor_id}.transports")
        secret_mode = _text(item["secret_mode"], f"vendor {vendor_id}.secret_mode")
        if secret_mode not in SECRET_MODES:
            raise CatalogError(f"vendor {vendor_id}.secret_mode is unsupported: {secret_mode}")
        runtime_versions = _boolean(item["runtime_versions"], f"vendor {vendor_id}.runtime_versions")
        sensitive = _boolean(item["sensitive"], f"vendor {vendor_id}.sensitive")
        docs = _text(item["docs"], f"vendor {vendor_id}.docs")
        if mcp:
            if adapter != vendor_id or target is None or not block_path or not transports:
                raise CatalogError(f"vendor {vendor_id} MCP capability is incomplete")
            if secret_mode == "unsupported":
                raise CatalogError(f"vendor {vendor_id} MCP capability cannot use unsupported secrets")
        elif adapter != "none" or target is not None or block_path or transports or secret_mode != "unsupported":
            raise CatalogError(f"vendor {vendor_id} unsupported MCP capability must be empty")
        items[vendor_id] = VendorCapability(vendor_id, cli, mcp, adapter, target, block_path, transports, secret_mode, runtime_versions, sensitive, docs)
    return VendorMatrix(CATALOG_VERSION, MappingProxyType(items))


def render_vendor_docs(matrix: VendorMatrix) -> str:
    lines = [
        "<!-- vendor-capabilities:start -->",
        "| Vendor | MCP | Transports | Secret handling | Runtime versions | Target | Notes |",
        "|---|---:|---|---|---:|---|---|",
    ]
    for vendor_id, item in matrix.vendors.items():
        transports = ", ".join(item.transports) if item.transports else "—"
        target = f"`{item.target}`" if item.target else "—"
        lines.append(f"| `{vendor_id}` | {'yes' if item.mcp else 'no'} | {transports} | `{item.secret_mode}` | {'yes' if item.runtime_versions else 'no'} | {target} | {item.docs} |")
    lines.append("<!-- vendor-capabilities:end -->")
    return "\n".join(lines)


def _validate_docs(root: Path, matrix: VendorMatrix) -> None:
    text = (root / "agents" / "env" / "README.md").read_text(encoding="utf-8")
    expected = render_vendor_docs(matrix)
    if expected not in text:
        raise CatalogError("agents/env/README.md vendor capability table is out of sync with vendors.yaml")


def _validate_manifest(doc: dict[str, Any], matrix: VendorMatrix, profiles: set[str]) -> None:
    _exact(doc, {"version", "tools", "default_profile", "modules", "unsupported"}, "manifest.yaml")
    _version(doc, "manifest.yaml")
    tools = _strings(doc["tools"], "manifest.tools")
    _refs(tools, set(matrix.vendors), "manifest.tools")
    if set(tools) != set(matrix.cli_tools):
        raise CatalogError("manifest.tools must equal vendors.yaml CLI tools")
    _text(doc["default_profile"], "manifest.default_profile")
    _refs((doc["default_profile"],), profiles, "manifest.default_profile")
    if not isinstance(doc["modules"], dict) or set(doc["modules"]) != MODULE_IDS:
        raise CatalogError("manifest.modules must declare every known module exactly once")
    for module_id, raw in doc["modules"].items():
        item = _exact(raw, {"enabled", "tools", "exclude"}, f"manifest.modules.{module_id}")
        _boolean(item["enabled"], f"manifest.modules.{module_id}.enabled")
        allowed = _strings(item["tools"], f"manifest.modules.{module_id}.tools")
        excluded = _strings(item["exclude"], f"manifest.modules.{module_id}.exclude")
        _refs(allowed + excluded, set(matrix.vendors), f"manifest.modules.{module_id}")
        if set(allowed) & set(excluded):
            raise CatalogError(f"manifest.modules.{module_id} tools/exclude overlap")
    mcp_module = doc["modules"]["mcp"]
    if mcp_module["enabled"] is not True:
        raise CatalogError("manifest.modules.mcp must be enabled; vendors.yaml owns MCP capability")
    if set(mcp_module["tools"]) != set(matrix.adapter_tools):
        raise CatalogError("manifest.modules.mcp.tools must equal vendors.yaml MCP tools")
    if set(mcp_module["exclude"]) & set(matrix.adapter_tools):
        raise CatalogError("manifest.modules.mcp.exclude cannot disable vendors.yaml MCP tools")
    if not isinstance(doc["unsupported"], dict):
        raise CatalogError("manifest.unsupported must be an object")
    expected_unsupported = set(matrix.cli_tools) - set(matrix.adapter_tools)
    if set(doc["unsupported"]) != expected_unsupported:
        raise CatalogError("manifest.unsupported must equal vendors without MCP adapters")
    for vendor_id, raw in doc["unsupported"].items():
        item = _exact(raw, {"mcp", "reason"}, f"manifest.unsupported.{vendor_id}")
        if item["mcp"] != "skip":
            raise CatalogError(f"manifest.unsupported.{vendor_id}.mcp must be skip")
        _text(item["reason"], f"manifest.unsupported.{vendor_id}.reason")


def _validate_profiles(profiles: dict[str, dict[str, Any]], servers: set[str]) -> None:
    for profile_id, doc in profiles.items():
        _exact(doc, {"version", "id", "description", "risk", "mcp_servers", "modules"}, f"profile {profile_id}")
        _version(doc, f"profile {profile_id}")
        if doc["id"] != profile_id:
            raise CatalogError(f"profile {profile_id}.id must match its filename")
        _text(doc["description"], f"profile {profile_id}.description")
        if doc["risk"] not in RISKS:
            raise CatalogError(f"profile {profile_id}.risk is unsupported")
        _refs(_strings(doc["mcp_servers"], f"profile {profile_id}.mcp_servers"), servers, f"profile {profile_id}.mcp_servers")
        _refs(_strings(doc["modules"], f"profile {profile_id}.modules"), MODULE_IDS, f"profile {profile_id}.modules")


def _validate_servers(doc: dict[str, Any], matrix: VendorMatrix, profiles: set[str], variables: set[str], runtime_tools: set[str]) -> None:
    _exact(doc, {"version", "servers"}, "mcp/servers.yaml")
    _version(doc, "mcp/servers.yaml")
    if not isinstance(doc["servers"], dict):
        raise CatalogError("mcp/servers.yaml.servers must be an object")
    required = {"transport", "tools", "profiles", "risk", "required_tools"}
    optional = {"url", "command", "args", "auth", "env", "browser_provider", "package", "version", "headers", "cwd"}
    for server_id, raw in doc["servers"].items():
        item = _allowed(raw, required, optional, f"server {server_id}")
        transport = _text(item["transport"], f"server {server_id}.transport")
        if transport not in TRANSPORTS:
            raise CatalogError(f"server {server_id}.transport is unsupported: {transport}")
        tools = _strings(item["tools"], f"server {server_id}.tools")
        _refs(tools, set(matrix.adapter_tools), f"server {server_id}.tools")
        for tool in tools:
            if transport not in matrix.capability(tool).transports:
                raise CatalogError(f"server {server_id} transport unsupported by vendor {tool}")
        _refs(_strings(item["profiles"], f"server {server_id}.profiles"), profiles, f"server {server_id}.profiles")
        if item["risk"] not in RISKS:
            raise CatalogError(f"server {server_id}.risk is unsupported")
        _refs(_strings(item["required_tools"], f"server {server_id}.required_tools"), runtime_tools, f"server {server_id}.required_tools")
        if transport == "stdio":
            _text(item.get("command"), f"server {server_id}.command")
            if "url" in item:
                raise CatalogError(f"server {server_id} stdio cannot declare url")
        else:
            _text(item.get("url"), f"server {server_id}.url")
            if "command" in item:
                raise CatalogError(f"server {server_id} HTTP cannot declare command")
        auth = item.get("auth")
        if auth is not None:
            auth = _exact(auth, {"type", "env"}, f"server {server_id}.auth")
            if auth["type"] != "bearer-env":
                raise CatalogError(f"server {server_id}.auth.type is unsupported")
            _refs((_text(auth["env"], f"server {server_id}.auth.env"),), variables, f"server {server_id}.auth.env")
        env = item.get("env", {})
        if not isinstance(env, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in env.items()):
            raise CatalogError(f"server {server_id}.env must be a string map")
        _refs(tuple(env), variables, f"server {server_id}.env keys")
        for env_value in env.values():
            referenced = tuple(re.findall(r"\$\{([A-Z][A-Z0-9_]*)\}|\{env:([A-Z][A-Z0-9_]*)\}", env_value))
            names = tuple(left or right for left, right in referenced)
            _refs(names, variables, f"server {server_id}.env placeholders")
        if "args" in item:
            _strings(item["args"], f"server {server_id}.args", unique=False)
        if "headers" in item:
            headers = item["headers"]
            if not isinstance(headers, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in headers.items()):
                raise CatalogError(f"server {server_id}.headers must be a string map")
        if "cwd" in item:
            _text(item["cwd"], f"server {server_id}.cwd")
        if "browser_provider" in item:
            _text(item["browser_provider"], f"server {server_id}.browser_provider")
        package, version = item.get("package"), item.get("version")
        if (package is None) != (version is None):
            raise CatalogError(f"server {server_id} package/version must be declared together")
        if package is not None:
            _text(package, f"server {server_id}.package")
            _text(version, f"server {server_id}.version")
            if not EXACT_VERSION.fullmatch(version):
                raise CatalogError(f"server {server_id}.version must be exact")
            args = _strings(item.get("args", []), f"server {server_id}.args", unique=False)
            if f"{package}@{version}" not in args:
                raise CatalogError(f"server {server_id}.args omits declared runtime version")
        _refs(_placeholder_refs(item), variables, f"server {server_id} placeholders")


def _validate_simple_documents(docs: dict[str, dict[str, Any]], matrix: VendorMatrix, profiles: set[str]) -> None:
    tools = docs["tools"]
    _exact(tools, {"version", "tools"}, "tools.yaml")
    _version(tools, "tools.yaml")
    if not isinstance(tools["tools"], dict):
        raise CatalogError("tools.yaml.tools must be an object")
    tool_keys = {"command", "version_cmd", "required", "profiles", "install_hint"}
    for tool_id, raw in tools["tools"].items():
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
        item = _allowed(raw, {"purpose", "required", "sensitive", "profiles", "check", "setup_hint"}, {"tools"}, f"env variable {name}")
        _text(item["purpose"], f"env variable {name}.purpose")
        _boolean(item["required"], f"env variable {name}.required")
        _boolean(item["sensitive"], f"env variable {name}.sensitive")
        _refs(_strings(item["profiles"], f"env variable {name}.profiles"), profiles, f"env variable {name}.profiles")
        if "tools" in item:
            _refs(_strings(item["tools"], f"env variable {name}.tools"), set(matrix.vendors), f"env variable {name}.tools")
        if item["check"] not in {"present", "present_if_set"}:
            raise CatalogError(f"env variable {name}.check is unsupported")
        _text(item["setup_hint"], f"env variable {name}.setup_hint")

    security = docs["security"]
    _exact(
        security,
        {
            "version", "risk_levels", "defaults", "sensitive_patterns",
            "browser_state", "private_boundary", "sensitive_backups",
            "private_runtime", "scan",
        },
        "security.yaml",
    )
    _version(security, "security.yaml")
    if set(security["risk_levels"]) != RISKS:
        raise CatalogError("security.yaml.risk_levels must define low, medium, high")
    for risk, raw in security["risk_levels"].items():
        _exact(raw, {"description"}, f"security risk {risk}")
        _text(raw["description"], f"security risk {risk}.description")
    defaults = _exact(security["defaults"], {"enable_high_risk", "isolate_browser_profile", "never_commit_secrets", "never_commit_browser_state"}, "security.defaults")
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
    for section, keys in (("browser_state", {"protected_kinds", "forbidden_in_repo", "artifact_hint"}), ("private_boundary", {"local_override_files", "allowed_in_local_only", "never_in_repo"})):
        value = _exact(security[section], keys, f"security.{section}")
        for key, entry in value.items():
            if key == "artifact_hint":
                _text(entry, f"security.{section}.{key}")
            else:
                _strings(entry, f"security.{section}.{key}")

    browser = docs["browser"]
    _exact(browser, {"version", "risk", "default_provider", "default_mode", "isolate_profile", "isolated_user_data_dir", "artifact_dir", "providers", "local_override_keys", "warnings"}, "browser.yaml")
    _version(browser, "browser.yaml")
    if browser["risk"] != "high":
        raise CatalogError("browser.yaml.risk must be high")
    _text(browser["default_provider"], "browser.default_provider")
    _text(browser["default_mode"], "browser.default_mode")
    _boolean(browser["isolate_profile"], "browser.isolate_profile")

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
    _text(browser["isolated_user_data_dir"], "browser.isolated_user_data_dir")
    _text(browser["artifact_dir"], "browser.artifact_dir")
    local_override_keys = _strings(browser["local_override_keys"], "browser.local_override_keys")
    _strings(browser["warnings"], "browser.warnings")
    if not isinstance(browser["providers"], dict) or browser["default_provider"] not in browser["providers"]:
        raise CatalogError("browser.providers must include default_provider")
    for provider_id, raw in browser["providers"].items():
        required = {"risk", "tools", "profiles", "checks"}
        optional = {"package", "version", "launch", "headless_arg", "user_data_arg", "required_tools", "deep_check", "enabled_by_default", "opt_in", "notes"}
        item = _allowed(raw, required, optional, f"browser provider {provider_id}")
        if item["risk"] != "high":
            raise CatalogError(f"browser provider {provider_id}.risk must be high")
        _refs(_strings(item["tools"], f"browser provider {provider_id}.tools"), set(matrix.adapter_tools), f"browser provider {provider_id}.tools")
        _refs(_strings(item["profiles"], f"browser provider {provider_id}.profiles"), profiles, f"browser provider {provider_id}.profiles")
        checks = item["checks"]
        if not isinstance(checks, list):
            raise CatalogError(f"browser provider {provider_id}.checks must be an array")
        for index, raw_check in enumerate(checks):
            check = _allowed(raw_check, {"id", "kind", "hint"}, {"command", "keys"}, f"browser provider {provider_id}.checks[{index}]")
            _text(check["id"], f"browser provider {provider_id}.checks[{index}].id")
            if check["kind"] not in {"command", "hint", "env_or_local", "optional_path"}:
                raise CatalogError(f"browser provider {provider_id}.checks[{index}].kind is unsupported")
            _text(check["hint"], f"browser provider {provider_id}.checks[{index}].hint")
            if "command" in check:
                _text(check["command"], f"browser provider {provider_id}.checks[{index}].command")
            if "keys" in check:
                keys = _strings(check["keys"], f"browser provider {provider_id}.checks[{index}].keys")
                _refs(keys, set(env["variables"]) | set(local_override_keys), f"browser provider {provider_id}.checks[{index}].keys")
            if check["kind"] == "command" and ("command" not in check or "keys" in check):
                raise CatalogError(f"browser provider {provider_id}.checks[{index}] command check has invalid fields")
            if check["kind"] in {"env_or_local", "optional_path"} and ("keys" not in check or "command" in check):
                raise CatalogError(f"browser provider {provider_id}.checks[{index}] key check has invalid fields")
            if check["kind"] == "hint" and ("command" in check or "keys" in check):
                raise CatalogError(f"browser provider {provider_id}.checks[{index}] hint check has invalid fields")
        package, version = item.get("package"), item.get("version")
        if (package is None) != (version is None):
            raise CatalogError(f"browser provider {provider_id} package/version must be declared together")
        if package is not None:
            _text(package, f"browser provider {provider_id}.package")
            _text(version, f"browser provider {provider_id}.version")
            if not EXACT_VERSION.fullmatch(version):
                raise CatalogError(f"browser provider {provider_id}.version must be exact")
        if "launch" in item:
            launch = _exact(item["launch"], {"command", "args"}, f"browser provider {provider_id}.launch")
            _text(launch["command"], f"browser provider {provider_id}.launch.command")
            launch_args = _strings(launch["args"], f"browser provider {provider_id}.launch.args", unique=False)
            if package is not None and f"{package}@{version}" not in launch_args:
                raise CatalogError(f"browser provider {provider_id}.launch.args omits declared runtime version")
        elif package is not None:
            raise CatalogError(f"browser provider {provider_id} runtime requires launch")
        if "deep_check" in item:
            deep = _exact(item["deep_check"], {"kind", "command"}, f"browser provider {provider_id}.deep_check")
            _text(deep["kind"], f"browser provider {provider_id}.deep_check.kind")
            _strings(deep["command"], f"browser provider {provider_id}.deep_check.command", unique=False)
        if "required_tools" in item:
            _refs(_strings(item["required_tools"], f"browser provider {provider_id}.required_tools"), set(tools["tools"]), f"browser provider {provider_id}.required_tools")
        for key in ("enabled_by_default", "opt_in"):
            if key in item:
                _boolean(item[key], f"browser provider {provider_id}.{key}")
        for key in ("headless_arg", "user_data_arg", "notes"):
            if key in item:
                _text(item[key], f"browser provider {provider_id}.{key}")


def load_catalog_documents(root: Path, *, validate_docs: bool = True) -> CatalogDocuments:
    env_dir = root / "agents" / "env"
    matrix = load_vendor_matrix(root)
    profile_dir = env_dir / "mcp" / "profiles"
    profiles: dict[str, dict[str, Any]] = {}
    for path in sorted(profile_dir.glob("*.yaml"), key=lambda item: item.name.encode("utf-8")):
        if path.stem in profiles:
            raise CatalogError(f"duplicate profile id: {path.stem}")
        profiles[path.stem] = _load(path)
    if not profiles:
        raise CatalogError("no MCP profiles declared")
    docs = {
        "manifest": _load(env_dir / "manifest.yaml"),
        "tools": _load(env_dir / "tools.yaml"),
        "env_schema": _load(env_dir / "env.schema.yaml"),
        "security": _load(env_dir / "security.yaml"),
        "browser": _load(env_dir / "browser.yaml"),
        "servers": _load(env_dir / "mcp" / "servers.yaml"),
    }
    server_map = docs["servers"].get("servers")
    variable_map = docs["env_schema"].get("variables")
    runtime_map = docs["tools"].get("tools")
    if not isinstance(server_map, dict) or not isinstance(variable_map, dict) or not isinstance(runtime_map, dict):
        raise CatalogError("catalog cross-reference roots must be objects")
    _validate_profiles(profiles, set(server_map))
    _validate_manifest(docs["manifest"], matrix, set(profiles))
    _validate_simple_documents(docs, matrix, set(profiles))
    _validate_servers(docs["servers"], matrix, set(profiles), set(variable_map), set(runtime_map))
    browser_providers = docs["browser"].get("providers")
    if not isinstance(browser_providers, dict):
        raise CatalogError("browser.providers must be an object")
    for server_id, server in server_map.items():
        provider = server.get("browser_provider")
        if provider is not None:
            _refs((provider,), set(browser_providers), f"server {server_id}.browser_provider")
            provider_tools = set(browser_providers[provider]["tools"])
            server_tools = set(server["tools"])
            if provider_tools != server_tools:
                raise CatalogError(f"browser provider {provider}.tools must equal server {server_id}.tools")
    if validate_docs:
        _validate_docs(root, matrix)
    return CatalogDocuments(
        MappingProxyType(docs["manifest"]), MappingProxyType(docs["tools"]),
        MappingProxyType(docs["env_schema"]), MappingProxyType(docs["security"]),
        MappingProxyType(docs["browser"]), MappingProxyType(docs["servers"]),
        MappingProxyType({key: MappingProxyType(value) for key, value in profiles.items()}), matrix,
    )
