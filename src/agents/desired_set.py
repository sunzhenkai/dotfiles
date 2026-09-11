"""Resolve the machine-local Skill Desired Set from catalog + overlay."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from defaults import load_catalog
from skills_catalog import SkillsCatalogError, load_skills_catalog
from dotf_core.overlays import OverlayError, catalog_from_repo, load_overlays
from third_party import ThirdPartyLockError


class DesiredSetError(ValueError):
    """Desired Set cannot be resolved without writing or installing."""


def _overlay_agents(root: Path, home: Path | None) -> dict[str, Any]:
    try:
        return dict(load_overlays(repo_root=root, catalog=catalog_from_repo(root), home=home).agents)
    except (OverlayError, OSError, FileNotFoundError):
        return {}


def approved_skill_ids(root: Path) -> frozenset[str]:
    """All catalogued ids are approved: first-party from the repo, third-party
    only if the strict lock covers them (validated by load_catalog)."""
    try:
        load_catalog(root)
        catalog = load_skills_catalog(root)
    except (ThirdPartyLockError, SkillsCatalogError, OSError, UnicodeError):
        return frozenset()
    return frozenset(item for item in catalog.ids() if not item.startswith("openspec-"))


def resolve_skill_desired_set(
    root: Path,
    *,
    home: Path | None = None,
    overlay_agents: Mapping[str, Any] | None = None,
) -> frozenset[str]:
    """编目内全部 id ∪ overlay 启用 − overlay 停用。

    There is no per-entry default: everything catalogued is installed by the
    automatic full install. Opting out is done by commenting the entry out of
    the catalog, so overlay may only enable/disable catalogued ids.
    """
    catalog = load_skills_catalog(root)
    known = frozenset(
        entry.id for entry in catalog.skills if not entry.id.startswith("openspec-")
    )
    agents = dict(overlay_agents) if overlay_agents is not None else _overlay_agents(root, home)
    enabled = frozenset(agents.get("enabled_skills") or [])
    disabled = frozenset(agents.get("disabled_skills") or [])
    unknown = sorted((enabled | disabled) - known)
    openspec = sorted(item for item in enabled | disabled if item.startswith("openspec-"))
    if openspec:
        raise DesiredSetError("OpenSpec skills cannot enter Desired Set: " + ", ".join(openspec))
    if unknown:
        raise DesiredSetError("unlocked or unknown skills cannot enter Desired Set: " + ", ".join(unknown))
    return (known | enabled) - disabled
