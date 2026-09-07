"""Read-only state fusion for the TUI manager.

Composes three sources without writing any of them:
- ``modules-state.yaml`` for module install / config facts (owned by this change)
- ``agents-manifest.json`` for config hash / target / mode (owned by ``agents``)
- ``agents/env/overlay.*.yaml`` for Skill / MCP Desired Set (owned by ``agents``)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

import sys

from dotf_core import modules_state
from dotf_core.overlays import catalog_from_repo, load_overlays  # noqa: F401  (lazy)

# scripts/agents/ is a flat module directory (no __init__.py); expose it for
# desired_set / overlays / managed_status lazy imports below.
_AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"
if str(_AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENTS_DIR))


@dataclass(frozen=True, slots=True)
class ModuleRow:
    name: str
    capabilities: tuple[str, ...]  # subset of ("install", "config", "doctor", "uninstall")
    installed: bool
    configured: bool
    last_install_at: str | None
    last_config_at: str | None
    version: str | None
    path: str | None
    drift: Literal["unchanged", "changed", "missing", "conflict", "permission", "unknown"]
    installed_unknown: bool
    configured_unknown: bool

    @property
    def status_text(self) -> str:
        if self.installed_unknown and self.configured_unknown:
            return "unknown"
        parts: list[str] = []
        if self.installed:
            parts.append("installed")
        if self.configured:
            parts.append("configured")
        if not parts:
            return "unknown"
        return "+".join(parts)

    @property
    def drift_text(self) -> str:
        return self.drift if self.drift != "unchanged" else ""

    @property
    def actions_text(self) -> str:
        icons = {
            "install": "I",
            "config": "C",
            "doctor": "D",
            "uninstall": "U",
            "deconfig": "X",
        }
        return "".join(icons[c] for c in self.capabilities if c in icons)


@dataclass(frozen=True, slots=True)
class SkillRow:
    skill_id: str
    source: Literal["desired", "available", "disabled"]
    in_desired: bool

    @property
    def status_text(self) -> str:
        return self.source

    @property
    def actions_text(self) -> str:
        return "A" if self.in_desired else "a/X"


@dataclass(frozen=True, slots=True)
class McpRow:
    tool: str
    server: str
    enabled: bool | None  # None means unknown / not in overlay

    @property
    def status_text(self) -> str:
        if self.enabled is None:
            return "catalog"
        return "enabled" if self.enabled else "disabled"

    @property
    def actions_text(self) -> str:
        return "A/X"


def _manifest_drift(manifest_status: str) -> str:
    if manifest_status in {"unchanged", "changed", "missing", "conflict", "permission"}:
        return manifest_status
    return "unknown"


def _manifest_status_for_module(
    module: str,
    manifest_path: Path,
    owner_prefix: str,
) -> str:
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return "unknown"
    items = raw.get("items") if isinstance(raw, dict) else None
    if not isinstance(items, list):
        return "unknown"
    owner_match = f"{owner_prefix}:{module}"
    owners = [it for it in items if isinstance(it, dict) and it.get("owner", "").startswith(owner_match)]
    if not owners:
        return "missing"
    # Map known fields to drift status; fall back to unchanged.
    statuses = {it.get("status", "unchanged") for it in owners}
    if "changed" in statuses:
        return "changed"
    if "missing" in statuses:
        return "missing"
    if "conflict" in statuses:
        return "conflict"
    if "permission" in statuses:
        return "permission"
    return "unchanged"


def load_modules(root: Path, *, state_home: Path | None = None) -> list[ModuleRow]:
    """Build a module row for every applicable module.

    ``state_home`` defaults to ``XDG_STATE_HOME`` (or ``~/.local/state``).
    """
    import modules as mods

    registry = mods.load_registry()
    os_id = mods.detect_os()
    records = modules_state.load_state(state_home=state_home)
    manifest_path = (state_home or modules_state.xdg_state_home()) / "dotf" / "agents-manifest.json"

    rows: list[ModuleRow] = []
    for mod in mods.filter_modules(registry, os_id=os_id):
        name = str(mod["name"])
        capabilities: list[str] = []
        if mods.has_install(mod):
            capabilities.append("install")
        if mods.has_config(mod):
            capabilities.append("config")
        if mods.has_doctor(mod):
            capabilities.append("doctor")
        if mods.has_uninstall(mod):
            capabilities.append("uninstall")
        # deconfig is implicit whenever config is declared
        if mods.has_config(mod):
            capabilities.append("deconfig")

        record = records.get(name)
        installed = bool(record and record.installed)
        configured = bool(record and record.configured)
        installed_unknown = record is None
        configured_unknown = record is None
        drift = _manifest_status_for_module(name, manifest_path, owner_prefix="config")

        rows.append(
            ModuleRow(
                name=name,
                capabilities=tuple(capabilities),
                installed=installed,
                configured=configured,
                last_install_at=(record.last_install_at if record else None),
                last_config_at=(record.last_config_at if record else None),
                version=(record.version if record else None),
                path=(record.path if record else None),
                drift=_manifest_drift(drift),
                installed_unknown=installed_unknown,
                configured_unknown=configured_unknown,
            )
        )
    return rows


def load_skills(root: Path) -> list[SkillRow]:
    """Build a Skill row from approved + desired Skill ids, excluding OpenSpec skill."""
    from desired_set import approved_skill_ids, resolve_skill_desired_set

    listed = approved_skill_ids(root)
    try:
        desired = resolve_skill_desired_set(root)
    except Exception:
        desired = frozenset()
    rows: list[SkillRow] = []
    for skill_id in sorted(item for item in listed if not item.startswith("openspec-")):
        in_desired = skill_id in desired
        source: Literal["desired", "available", "disabled"] = "desired" if in_desired else "available"
        rows.append(SkillRow(skill_id=skill_id, source=source, in_desired=in_desired))
    return rows


def load_mcp(root: Path) -> list[McpRow]:
    """Build an MCP ``(tool, server)`` row from catalog + overlay."""
    catalog = catalog_from_repo(root)
    try:
        loaded = load_overlays(repo_root=root, catalog=catalog)
    except Exception:
        loaded = None
    enabled_set: set[str] = set()
    disabled_set: set[str] = set()
    if loaded is not None:
        agents = loaded.agents
        enabled_set = set(agents.get("enabled_servers") or [])
        disabled_set = set(agents.get("disabled_servers") or [])
    rows: list[McpRow] = []
    for tool in sorted(catalog.tools):
        for server in sorted(catalog.servers):
            if server in enabled_set:
                enabled: bool | None = True
            elif server in disabled_set:
                enabled = False
            else:
                enabled = None
            rows.append(McpRow(tool=tool, server=server, enabled=enabled))
    return rows


def load_journal_failures(state_home: Path | None = None) -> list[str]:
    """Return a deduplicated list of module names whose latest action was failed."""
    runs_dir = (state_home or modules_state.xdg_state_home()) / "dotf" / "runs"
    if not runs_dir.is_dir():
        return []
    failed: set[str] = set()
    for path in sorted(runs_dir.glob("run-*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        actions = data.get("actions") if isinstance(data, dict) else None
        if not isinstance(actions, list):
            continue
        for action in actions:
            if not isinstance(action, dict):
                continue
            if action.get("result_status") == "failed":
                name = action.get("module")
                if isinstance(name, str) and name:
                    failed.add(name)
    return sorted(failed)
