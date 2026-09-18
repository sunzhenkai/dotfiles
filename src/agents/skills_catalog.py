#!/usr/bin/env python3
"""Parse the unified Skill catalog (agents/skills.yaml).

One file is the single source of truth for every Skill, organised by group.
Each group declares its source attributes and lists member install ids; the
group name doubles as a CLI expansion unit. A member is either a plain id
(string) or a mapping `- id: <id>` with `optional: true` and optional
`aliases: [<name>]`. Optional entries stay catalogued (overlay / agents apply
may enable them on demand) but are excluded from the default full install.
Aliases are extra CLI names for the same catalog id; overlay / lock / Desired
Set still store the canonical id. Everything else catalogued is installed by
`dotf agents -c`; opting out entirely means commenting the entry out of the
catalog.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from ensure_pyyaml import ensure_yaml

_yaml = ensure_yaml()

CATALOG_REL = Path("agents") / "skills.yaml"
LOCK_REL = Path("agents") / "skills.lock.yaml"
FIRST_PARTY = "first-party"
THIRD_PARTY = "third-party"
SOURCE_REGISTRY = "registry"
SOURCE_GITHUB = "github"
_GROUP_KEYS = {"type", "source", "package", "skills"}
_MEMBER_KEYS = {"id", "optional", "aliases"}
_THIRD_PARTY_SOURCES = {SOURCE_REGISTRY, SOURCE_GITHUB}


class SkillsCatalogError(ValueError):
    """The unified skill catalog is missing, malformed, or inconsistent."""


@dataclass(frozen=True, slots=True)
class SkillEntry:
    id: str
    group: str
    type: str
    package: Optional[str] = None
    source: Optional[str] = None
    optional: bool = False
    aliases: tuple[str, ...] = ()

    @property
    def is_first_party(self) -> bool:
        return self.type == FIRST_PARTY


@dataclass(frozen=True, slots=True)
class SkillGroup:
    name: str
    type: str
    ids: tuple[str, ...]
    package: Optional[str] = None
    source: Optional[str] = None
    optional_ids: tuple[str, ...] = ()
    aliases_by_id: tuple[tuple[str, tuple[str, ...]], ...] = ()

    @property
    def is_first_party(self) -> bool:
        return self.type == FIRST_PARTY


@dataclass(frozen=True, slots=True)
class SkillsCatalog:
    version: int
    lock: str
    skills: tuple[SkillEntry, ...]
    groups: tuple[SkillGroup, ...]

    def by_id(self) -> dict[str, SkillEntry]:
        return {entry.id: entry for entry in self.skills}

    def group_by_name(self) -> dict[str, SkillGroup]:
        return {group.name: group for group in self.groups}

    def ids(self) -> List[str]:
        return [entry.id for entry in self.skills]

    def default_ids(self) -> List[str]:
        """Catalogued ids that enter the default Desired Set (non-optional)."""
        return [entry.id for entry in self.skills if not entry.optional]

    def first_party_ids(self) -> List[str]:
        return [entry.id for entry in self.skills if entry.is_first_party]

    def third_party_ids(self) -> List[str]:
        return [entry.id for entry in self.skills if not entry.is_first_party]

    def group_ids(self, name: str) -> Optional[tuple[str, ...]]:
        group = self.group_by_name().get(name)
        return group.ids if group is not None else None

    def alias_to_id(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for entry in self.skills:
            for alias in entry.aliases:
                mapping[alias] = entry.id
        return mapping

    def canonical_id(self, name: str) -> Optional[str]:
        """Return the catalog id for a skill id or alias; None if unknown."""
        if name in self.by_id():
            return name
        return self.alias_to_id().get(name)


def _fail(message: str) -> SkillsCatalogError:
    return SkillsCatalogError(f"skills catalog: {message}")


def _parse_id_token(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise _fail(f"{label} must be a non-empty skill id")
    if "/" in value:
        raise _fail(f"{label} must not contain '/'")
    return value


def _parse_aliases(raw: object, label: str) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise _fail(f"{label} must be a list of skill ids")
    aliases: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        alias = _parse_id_token(item, f"{label}[{index}]")
        if alias in seen:
            raise _fail(f"{label} has duplicate alias {alias!r}")
        seen.add(alias)
        aliases.append(alias)
    return tuple(aliases)


def _parse_member(group: str, index: int, member: object) -> tuple[str, bool, tuple[str, ...]]:
    """One skills list entry: a plain id string or an {id, optional, aliases} mapping."""
    label = f"group {group!r}.skills[{index}]"
    if isinstance(member, str):
        return _parse_id_token(member, f"{label} id"), False, ()
    if isinstance(member, dict):
        unknown = set(member) - _MEMBER_KEYS
        if unknown:
            raise _fail(f"{label} has unknown keys: {', '.join(sorted(unknown))}")
        skill_id = _parse_id_token(member.get("id"), f"{label} id")
        optional = member.get("optional", False)
        if not isinstance(optional, bool):
            raise _fail(f"{label}.optional must be a boolean")
        aliases = _parse_aliases(member.get("aliases"), f"{label}.aliases")
        if skill_id in aliases:
            raise _fail(f"{label}.aliases must not repeat the skill id {skill_id!r}")
        return skill_id, optional, aliases
    raise _fail(f"{label} must be a non-empty skill id or a mapping with id/optional/aliases")



def _parse_group(name: str, raw: object) -> SkillGroup:
    if not isinstance(name, str) or not name:
        raise _fail("group names must be non-empty strings")
    if not isinstance(raw, dict):
        raise _fail(f"group {name!r} must be a mapping")
    unknown = set(raw) - _GROUP_KEYS
    if unknown:
        raise _fail(f"group {name!r} has unknown keys: {', '.join(sorted(unknown))}")
    if set(raw) < {"type", "skills"}:
        raise _fail(f"group {name!r} requires type and skills")

    kind = raw.get("type")
    if kind not in {FIRST_PARTY, THIRD_PARTY}:
        raise _fail(f"group {name!r}.type must be {FIRST_PARTY!r} or {THIRD_PARTY!r}")

    package = raw.get("package")
    source = raw.get("source")
    if kind == THIRD_PARTY:
        if not isinstance(package, str) or not package:
            raise _fail(f"group {name!r} ({THIRD_PARTY}) requires a non-empty package")
        if source not in _THIRD_PARTY_SOURCES:
            raise _fail(
                f"group {name!r}.source must be one of "
                + ", ".join(sorted(_THIRD_PARTY_SOURCES))
            )
    else:
        if package is not None or source is not None:
            raise _fail(f"group {name!r} ({FIRST_PARTY}) must not declare package/source")
        package = None
        source = None

    members = raw.get("skills")
    if not isinstance(members, list):
        raise _fail(f"group {name!r} requires a skills list")
    ids: list[str] = []
    optionals: list[str] = []
    aliases_by_id: list[tuple[str, tuple[str, ...]]] = []
    for index, member in enumerate(members):
        skill_id, optional, aliases = _parse_member(name, index, member)
        ids.append(skill_id)
        if optional:
            optionals.append(skill_id)
        if aliases:
            aliases_by_id.append((skill_id, aliases))
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        raise _fail(f"group {name!r} has duplicate skill ids: " + ", ".join(duplicates))

    return SkillGroup(
        name=name,
        type=kind,
        ids=tuple(ids),
        package=package,
        source=source,
        optional_ids=tuple(optionals),
        aliases_by_id=tuple(aliases_by_id),
    )


def parse_catalog(data: object) -> SkillsCatalog:
    if not isinstance(data, dict):
        raise _fail("top level must be a mapping")
    unknown = set(data) - {"version", "lock", "groups"}
    if unknown:
        raise _fail("unknown top-level keys: " + ", ".join(sorted(unknown)))
    if set(data) < {"version", "lock", "groups"}:
        raise _fail("catalog requires version, lock, and groups")
    if data["version"] != 3:
        raise _fail(f"unsupported version {data['version']!r}")
    if data["lock"] != LOCK_REL.name:
        raise _fail(f"lock must reference {LOCK_REL.name!r}")

    raw_groups = data["groups"]
    if not isinstance(raw_groups, dict):
        raise _fail("groups must be a mapping")
    groups = tuple(_parse_group(name, raw) for name, raw in raw_groups.items())

    entries: list[SkillEntry] = []
    seen: set[str] = set()
    reserved = {group.name for group in groups}
    for group in groups:
        optional_set = set(group.optional_ids)
        aliases_for = dict(group.aliases_by_id)
        for skill_id in group.ids:
            if skill_id in seen:
                raise _fail(f"duplicate skill id across groups: {skill_id}")
            seen.add(skill_id)
            entries.append(
                SkillEntry(
                    id=skill_id,
                    group=group.name,
                    type=group.type,
                    package=group.package,
                    source=group.source,
                    optional=skill_id in optional_set,
                    aliases=aliases_for.get(skill_id, ()),
                )
            )

    alias_owner: dict[str, str] = {}
    for entry in entries:
        for alias in entry.aliases:
            if alias in seen:
                raise _fail(f"alias {alias!r} collides with skill id {alias!r}")
            if alias in reserved:
                raise _fail(f"alias {alias!r} collides with group name {alias!r}")
            owner = alias_owner.get(alias)
            if owner is not None:
                raise _fail(f"duplicate alias {alias!r} for {owner} and {entry.id}")
            alias_owner[alias] = entry.id

    return SkillsCatalog(version=data["version"], lock=data["lock"], skills=tuple(entries), groups=groups)


def load_skills_catalog(root: Path) -> SkillsCatalog:
    path = root / CATALOG_REL
    try:
        data = _yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise _fail(f"missing {CATALOG_REL}: {path}") from exc
    except (OSError, UnicodeError, _yaml.YAMLError) as exc:
        raise _fail(f"cannot read {path}: {exc}") from exc
    return parse_catalog(data)


def _discover_first_party_dirs(root: Path) -> set[str]:
    skills_root = root / "agents" / "skills"
    if not skills_root.is_dir():
        return set()
    return {
        path.name
        for path in skills_root.iterdir()
        if path.is_dir()
        and not path.is_symlink()
        and (path / "SKILL.md").is_file()
        and not path.name.startswith("openspec-")
    }


def validate_first_party_coverage(root: Path, catalog: SkillsCatalog) -> None:
    """Every first-party directory must be catalogued; every catalogued
    first-party id must have a directory. Fail closed on either side."""
    declared = set(catalog.first_party_ids())
    discovered = _discover_first_party_dirs(root)
    uncatalogued = sorted(discovered - declared)
    if uncatalogued:
        raise _fail(
            "first-party skill directories are missing from the catalog: "
            + ", ".join(uncatalogued)
        )
    missing_dirs = sorted(name for name in declared if name not in discovered)
    if missing_dirs:
        raise _fail(
            "catalogued first-party skills have no agents/skills/<id>/ directory: "
            + ", ".join(missing_dirs)
        )
