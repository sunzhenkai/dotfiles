"""Resolve the machine-local Skill Desired Set from catalog + overlay."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from defaults import first_party_skill_ids, load_catalog, selected_default_ids
from dotf_core.overlays import OverlayError, catalog_from_repo, load_overlays
from third_party import ThirdPartyLockError


class DesiredSetError(ValueError):
    """Desired Set cannot be resolved without writing or installing."""


def _overlay_agents(root: Path, home: Path | None) -> dict[str, Any]:
    try:
        return dict(load_overlays(repo_root=root, catalog=catalog_from_repo(root), home=home).agents)
    except (OverlayError, OSError, FileNotFoundError):
        return {}


def locked_skill_ids(root: Path) -> frozenset[str]:
    try:
        return frozenset(item.id for item in load_catalog(root).skills)
    except (ThirdPartyLockError, OSError, UnicodeError):
        return frozenset()


def approved_skill_ids(root: Path) -> frozenset[str]:
    first = frozenset(item for item in first_party_skill_ids(root) if not item.startswith("openspec-"))
    return first | locked_skill_ids(root)


def resolve_skill_desired_set(
    root: Path,
    *,
    home: Path | None = None,
    overlay_agents: Mapping[str, Any] | None = None,
) -> frozenset[str]:
    """一手 catalog ∪ 默认选中第三方 ∪ overlay 启用 − 停用。"""
    first = frozenset(item for item in first_party_skill_ids(root) if not item.startswith("openspec-"))
    try:
        defaults = frozenset(selected_default_ids(root))
    except (ThirdPartyLockError, OSError, UnicodeError, TypeError):
        defaults = frozenset()
    locked = locked_skill_ids(root)
    agents = dict(overlay_agents) if overlay_agents is not None else _overlay_agents(root, home)
    enabled = frozenset(agents.get("enabled_skills") or [])
    disabled = frozenset(agents.get("disabled_skills") or [])
    unknown = sorted((enabled | disabled) - first - locked)
    openspec = sorted(item for item in enabled | disabled if item.startswith("openspec-"))
    if openspec:
        raise DesiredSetError("OpenSpec skills cannot enter Desired Set: " + ", ".join(openspec))
    if unknown:
        raise DesiredSetError("unlocked or unknown skills cannot enter Desired Set: " + ", ".join(unknown))
    return (first | defaults | enabled) - disabled
