"""Resolve the machine-local Skill Desired Set from catalog + overlay."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from defaults import load_catalog
from skills_catalog import SkillsCatalog, SkillsCatalogError, load_skills_catalog
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


def _canonical_skill_names(
    catalog: SkillsCatalog, names: frozenset[str]
) -> tuple[frozenset[str], list[str]]:
    resolved: set[str] = set()
    unknown: list[str] = []
    for name in names:
        canonical = catalog.canonical_id(name)
        if canonical is None:
            unknown.append(name)
        else:
            resolved.add(canonical)
    return frozenset(resolved), sorted(unknown)


def resolve_skill_desired_set(
    root: Path,
    *,
    home: Path | None = None,
    overlay_agents: Mapping[str, Any] | None = None,
) -> frozenset[str]:
    """非 optional 编目 id ∪ overlay 启用 − overlay 停用。

    Catalogued `optional: true` entries are approved but stay out of the default
    Desired Set; overlay enabled_skills (or `dotf agents skill apply`) brings
    them in on demand. Opting out entirely is done by commenting the entry out
    of the catalog, so overlay may only enable/disable catalogued ids.
    """
    catalog = load_skills_catalog(root)
    known = frozenset(
        entry.id for entry in catalog.skills if not entry.id.startswith("openspec-")
    )
    defaults = frozenset(
        entry.id
        for entry in catalog.skills
        if not entry.optional and not entry.id.startswith("openspec-")
    )
    agents = dict(overlay_agents) if overlay_agents is not None else _overlay_agents(root, home)
    enabled, enabled_unknown = _canonical_skill_names(
        catalog, frozenset(agents.get("enabled_skills") or [])
    )
    disabled, disabled_unknown = _canonical_skill_names(
        catalog, frozenset(agents.get("disabled_skills") or [])
    )
    unknown = sorted(set(enabled_unknown) | set(disabled_unknown) | ((enabled | disabled) - known))
    openspec = sorted(item for item in enabled | disabled if item.startswith("openspec-"))
    if openspec:
        raise DesiredSetError("OpenSpec skills cannot enter Desired Set: " + ", ".join(openspec))
    if unknown:
        raise DesiredSetError("unlocked or unknown skills cannot enter Desired Set: " + ", ".join(unknown))
    return (defaults | enabled) - disabled
