#!/usr/bin/env python3
"""Resolve dotf skills short names to npx skills add arguments."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from ensure_pyyaml import ensure_yaml

_yaml = ensure_yaml()

MAP_REL = Path("agents") / "skills-map.yaml"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _fail(message: str) -> tuple[list[str], int]:
    print(f"error: skills map: {message}", file=sys.stderr)
    return [], 1


def _skill_selector_values(
    name: str, entry: dict[object, object]
) -> tuple[list[str], int]:
    if "skill" in entry and "skills" in entry:
        return _fail(f"skill '{name}' cannot use both 'skill' and 'skills'")

    if "skills" in entry:
        selectors = entry.get("skills")
        if (
            not isinstance(selectors, list)
            or not selectors
            or not all(isinstance(item, str) and item for item in selectors)
        ):
            return _fail(
                f"skill '{name}' requires a non-empty list of 'skills' selectors"
            )
        return selectors, 0

    selector = entry.get("skill")
    if selector is None:
        return [], 0
    if not isinstance(selector, str) or not selector:
        return _fail(f"skill '{name}' has an invalid 'skill' selector")
    return [selector], 0


def resolve(
    map_path: Path, name: str, *, for_remove: bool = False
) -> tuple[list[str], int]:
    """Return npx skills add/remove arguments; unmapped names pass through."""
    if not map_path.is_file():
        return [name], 0
    try:
        data = _yaml.safe_load(map_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, _yaml.YAMLError) as exc:
        return _fail(f"cannot read {map_path}: {exc}")
    if data is None:
        return [name], 0
    if not isinstance(data, dict):
        return _fail(f"{map_path}: top level must be a mapping")
    version = data.get("version", 1)
    if version != 1:
        return _fail(f"{map_path}: unsupported version {version!r}")
    skills = data.get("skills") or {}
    if not isinstance(skills, dict):
        return _fail(f"{map_path}: 'skills' must be a mapping")
    entry = skills.get(name)
    if entry is None:
        return [name], 0
    if isinstance(entry, str):
        if not entry:
            return _fail(f"skill '{name}' maps to an empty package")
        if for_remove:
            return [name], 0
        return [entry], 0
    if isinstance(entry, dict):
        package = entry.get("package")
        if not isinstance(package, str) or not package:
            return _fail(f"skill '{name}' requires a non-empty 'package'")
        selectors, rc = _skill_selector_values(name, entry)
        if rc != 0:
            return [], rc
        if for_remove:
            if not selectors:
                return [name], 0
            return selectors, 0
        args = [package]
        for selector in selectors:
            args += ["-s", selector]
        return args, 0
    return _fail(f"skill '{name}' entry must be a string or mapping")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve dotf skills short names")
    parser.add_argument("name", help="skill short name or raw package spec")
    parser.add_argument("--remove", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--map", type=Path, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    map_path = args.map if args.map is not None else repo_root() / MAP_REL
    resolved, rc = resolve(map_path, args.name, for_remove=args.remove)
    if rc != 0:
        return rc
    for item in resolved:
        print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
