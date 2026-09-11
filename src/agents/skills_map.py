#!/usr/bin/env python3
"""Resolve `dotf skills -i/-r <name>` inputs against the unified skill catalog.

Priority: match a group name (expand to its ids) -> match a catalogued skill id
-> pass the raw name through to `npx skills` (search). A name that is both a
group and a skill id resolves as the group, with a notice to stderr.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from ensure_pyyaml import ensure_yaml
from skills_catalog import SkillsCatalogError, parse_catalog

_yaml = ensure_yaml()

CATALOG_REL = Path("agents") / "skills.yaml"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _fail(message: str) -> tuple[list[str], int]:
    print(f"error: skills map: {message}", file=sys.stderr)
    return [], 1


def resolve(
    catalog_path: Path, name: str, *, for_remove: bool = False
) -> tuple[list[str], int]:
    """Resolve one input name to `npx skills add/remove` arguments.

    Order: group -> skill id -> passthrough. A raw npx package spec or an
    unknown name is passed through unchanged.
    """
    catalog = _load_catalog_file(catalog_path)
    if catalog is None:
        return [name], 0
    packages = {entry.id: (entry.package or "") for entry in catalog.skills}
    groups = {group.name: group.ids for group in catalog.groups}

    # 1. group (a name expanding to its member ids)
    if name in groups:
        ids = list(groups[name])
        collision = name in packages
        if collision:
            print(
                f"note: '{name}' is both a group and a skill id; using the group's "
                f"{len(ids)} skills. Use -s <id> for a single skill.",
                file=sys.stderr,
            )
        if for_remove:
            return ids, 0
        args: list[str] = []
        seen_package: str | None = None
        for skill_id in ids:
            pkg = packages.get(skill_id, "")
            if not pkg:
                return _fail(
                    f"group '{name}' contains first-party skill '{skill_id}', which is "
                    "installed from the repo, not via npx; use `dotf agents skill apply "
                    f"{skill_id}`"
                )
            if seen_package is None:
                seen_package = pkg
                args.append(pkg)
            elif pkg != seen_package:
                return _fail(
                    f"group '{name}' mixes packages ({seen_package} vs {pkg}); "
                    "install its skills individually with -s <id>"
                )
            args += ["-s", skill_id]
        return args, 0

    # 2. skill id (must be third-party to install via npx)
    if name in packages:
        pkg = packages[name]
        if not pkg:
            return _fail(
                f"'{name}' is a first-party skill installed from the repo, not via npx; "
                f"use `dotf agents skill apply {name}`"
            )
        if for_remove:
            return [name], 0
        return [pkg, "-s", name], 0

    # 3. passthrough to npx skills (its own search/registry resolution)
    return [name], 0


def _load_catalog_file(catalog_path: Path):
    """Parse the catalog at *catalog_path* directly (supports --map tests)."""
    if not catalog_path.is_file():
        return None
    try:
        data = _yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, _yaml.YAMLError) as exc:
        raise SkillsCatalogError(f"skills catalog: cannot read {catalog_path}: {exc}") from exc
    return parse_catalog(data)


def expand_group(catalog_path: Path, name: str) -> tuple[list[str], int]:
    """Return the catalogue ids a group expands to, or [] if *name* is not a group."""
    catalog = _load_catalog_file(catalog_path)
    if catalog is None:
        return [], 0
    for group in catalog.groups:
        if group.name == name:
            return list(group.ids), 0
    return [], 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve dotf skills short names")
    parser.add_argument("name", help="skill group, skill id, or raw npx package spec")
    parser.add_argument("--remove", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--map", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--expand-group", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    catalog_path = args.map if args.map is not None else repo_root() / CATALOG_REL
    if args.expand_group:
        members, rc = expand_group(catalog_path, args.name)
        if rc != 0:
            return rc
        for item in members:
            print(item)
        return 0
    resolved, rc = resolve(catalog_path, args.name, for_remove=args.remove)
    if rc != 0:
        return rc
    for item in resolved:
        print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
