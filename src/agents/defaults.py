#!/usr/bin/env python3
"""Install only strictly locked, audited third-party skills through runtime ownership."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence
import sys

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from ensure_pyyaml import ensure_yaml
from managed_runtime import AgentRuntimeConflict, apply_skills_plan, compile_skills_plan
from skills_catalog import (
    SkillsCatalogError,
    load_skills_catalog,
    validate_first_party_coverage,
)
from sync import kiro_skills_target, render_kiro_skill_bytes, render_skill_bytes, skills_target
from third_party import ThirdPartyLock, ThirdPartyLockError, acquire_all, load_lock

_yaml = ensure_yaml()
CATALOG_REL = Path("agents") / "skills.yaml"
LOCK_REL = Path("agents") / "skills.lock.yaml"
THIRD_PARTY_OWNER = "agents:third-party:"
KIRO_THIRD_PARTY_OWNER = "agents:kiro-third-party:"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def skills_target() -> Path:
    return Path.home() / ".agents" / "skills"


def first_party_skill_ids(root: Path) -> List[str]:
    """First-party ids per the catalog (the single source of truth)."""
    return load_skills_catalog(root).first_party_ids()


def catalog_skill_ids(root: Path) -> List[str]:
    """Every catalogued id; the automatic full install installs all of them.

    Opting out is done by commenting an entry out of the catalog, so there is
    no per-entry default switch."""
    return load_skills_catalog(root).ids()


def load_skills_lock(root: Path) -> ThirdPartyLock:
    """Load the strict third-party lock referenced by the catalog."""
    return load_lock(root / LOCK_REL)


def load_catalog(root: Path) -> ThirdPartyLock:
    """Validate the unified catalog against the strict lock and return the lock.

    Invariants:
    - first-party directories and catalogued first-party ids must agree;
    - every third-party catalogue id must be covered by the strict lock;
    - no first-party id may appear in the lock (no source confusion).
    """
    try:
        catalog = load_skills_catalog(root)
    except SkillsCatalogError as exc:
        raise ThirdPartyLockError(str(exc)) from exc
    validate_first_party_coverage(root, catalog)
    lock = load_lock(root / LOCK_REL)
    locked_ids = {item.id for item in lock.skills}
    third_party = set(catalog.third_party_ids())
    first_party = set(catalog.first_party_ids())

    missing = sorted(third_party - locked_ids)
    if missing:
        raise ThirdPartyLockError(
            "third-party catalogue entries must be covered by the strict lock "
            f"(unlocked={missing})"
        )
    confusion = sorted(first_party & locked_ids)
    if confusion:
        raise ThirdPartyLockError(
            "first-party skills must not appear in the strict lock: " + ", ".join(confusion)
        )
    return lock


def _home_for_target(destination: Path) -> Path:
    destination = destination.expanduser().absolute()
    if destination.name == "skills" and destination.parent.name == ".agents":
        return destination.parent.parent
    if destination.name == "skills" and destination.parent.name == ".kiro":
        return destination.parent.parent
    return Path.home().expanduser().absolute()


def _destination_specs(
    dest_roots: Optional[Sequence[Path]],
) -> tuple[tuple[Path, str, str], ...]:
    if dest_roots is not None:
        result = []
        for destination in dest_roots:
            destination = destination.expanduser().absolute()
            if destination.parent.name == ".kiro":
                result.append((destination, KIRO_THIRD_PARTY_OWNER, "kiro"))
            else:
                result.append((destination, THIRD_PARTY_OWNER, "shared"))
        return tuple(result)
    return (
        (skills_target(), THIRD_PARTY_OWNER, "shared"),
        (kiro_skills_target(), KIRO_THIRD_PARTY_OWNER, "kiro"),
    )


def install_defaults(
    root: Path,
    *,
    dry_run: bool = False,
    dest_root: Optional[Path] = None,
    dest_roots: Optional[Sequence[Path]] = None,
) -> int:
    """Verify the strict lock; apply only bytes acquired and checked in private staging."""
    lock = load_catalog(root)
    from desired_set import resolve_skill_desired_set

    desired = resolve_skill_desired_set(root)
    selected = tuple(item for item in lock.skills if item.id in desired)
    destinations = (
        _destination_specs((dest_root,))
        if dest_root is not None
        else _destination_specs(dest_roots)
    )
    if dry_run:
        for destination, _, layout in destinations:
            print(f"==> locked default skills ({layout}) → {destination}")
            for item in selected:
                print(
                    f"    {item.id} revision={item.revision} content={item.content_hash} "
                    f"license={item.license.spdx} audit={item.audit.status}@{item.audit.date}/{item.audit.tool}"
                )
            print(f"  done defaults ({layout}, plan): locked={len(selected)} network=none writes=none")
        return 0

    try:
        with tempfile.TemporaryDirectory(prefix="dotf-third-party-") as temporary:
            staging = Path(temporary) / "acquired"
            from dataclasses import replace

            filtered = replace(lock, skills=selected)
            source_root = acquire_all(filtered, staging) if selected else staging / "empty"
            if not selected:
                source_root.mkdir(parents=True, exist_ok=True)
            for destination, owner_prefix, layout in destinations:
                home = _home_for_target(destination)
                renderer = render_kiro_skill_bytes if layout == "kiro" else render_skill_bytes
                identity_suffix = ":kiro" if layout == "kiro" else ""
                plan = compile_skills_plan(
                    root,
                    renderer,
                    home=home,
                    target_root=destination,
                    source_root=source_root,
                    owner_prefix=owner_prefix,
                    identity_prefix=(
                        f"agents/skills.lock.yaml@{lock.digest}{identity_suffix}"
                    ),
                    include_unlisted=True,
                    only_ids=frozenset(item.id for item in selected),
                )
                result = apply_skills_plan(plan, renderer)
                print(
                    f"  done defaults ({layout}): locked={len(lock.skills)} changed={result.changed} "
                    f"pruned={result.pruned} unchanged={result.unchanged}"
                )
    except (ThirdPartyLockError, AgentRuntimeConflict, OSError, ValueError) as exc:
        print(f"error: locked third-party skills: {exc}", file=__import__("sys").stderr)
        return 1
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Install audited third-party skills from the strict lock")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    root = args.root.resolve() if args.root else repo_root()
    try:
        return install_defaults(root, dry_run=args.dry_run)
    except ThirdPartyLockError as exc:
        print(f"error: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
