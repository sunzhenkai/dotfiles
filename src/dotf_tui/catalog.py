"""Read-only inventory for the TUI. Never writes HOME or the repository."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
if str(_SCRIPTS / "agents") not in sys.path:
    sys.path.insert(0, str(_SCRIPTS / "agents"))

from dotf_core import registry as modules  # noqa: E402
from desired_set import approved_skill_ids, resolve_skill_desired_set  # noqa: E402
from dotf_core.overlays import catalog_from_repo  # noqa: E402


MODULE_ACTIONS = ("install", "config", "doctor", "uninstall", "deconfig")
SKILL_ACTIONS = ("skill.apply", "skill.remove")
MCP_ACTIONS = ("mcp.apply", "mcp.remove")


@dataclass(frozen=True, slots=True)
class Selectable:
    label: str
    action: str
    selector: str
    zone: str
    status: str = ""


def _module_actions(mod: dict) -> tuple[str, ...]:
    out: list[str] = []
    if modules.has_install(mod):
        out.append("install")
    if modules.has_config(mod):
        out.extend(("config", "deconfig"))
    if modules.has_doctor(mod):
        out.append("doctor")
    if modules.has_uninstall(mod):
        out.append("uninstall")
    return tuple(out)


def list_module_selectables(os_id: str | None = None) -> list[Selectable]:
    resolved = os_id or modules.detect_os()
    items: list[Selectable] = []
    for mod in modules.filter_modules(modules.load_registry(), os_id=resolved):
        name = str(mod["name"])
        for action in _module_actions(mod):
            items.append(
                Selectable(
                    label=f"{name} / {action}",
                    action=action,
                    selector=name,
                    zone="modules",
                    status="ready",
                )
            )
    return items


def list_agent_selectables(root: Path, *, home: Path | None = None) -> list[Selectable]:
    catalog = catalog_from_repo(root)
    try:
        desired = resolve_skill_desired_set(root, home=home)
    except Exception:
        desired = frozenset()
    listed = approved_skill_ids(root) | desired
    items: list[Selectable] = []
    for skill_id in sorted(item for item in listed if not item.startswith("openspec-")):
        state = "desired" if skill_id in desired else "available"
        for action in SKILL_ACTIONS:
            items.append(
                Selectable(
                    label=f"{skill_id} / {action}",
                    action=action,
                    selector=f"skill:{skill_id}",
                    zone="agent",
                    status=state,
                )
            )
    for tool in sorted(catalog.tools):
        for server_id in sorted(catalog.servers):
            for action in MCP_ACTIONS:
                items.append(
                    Selectable(
                        label=f"{tool}/{server_id} / {action}",
                        action=action,
                        selector=f"mcp:{tool}/{server_id}",
                        zone="agent",
                        status="catalog",
                    )
                )
    return items


def all_selectables(root: Path, *, os_id: str | None = None, home: Path | None = None) -> list[Selectable]:
    return list_module_selectables(os_id) + list_agent_selectables(root, home=home)
