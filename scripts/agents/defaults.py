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
from sync import kiro_skills_target, render_kiro_skill_bytes, render_skill_bytes, skills_target
from third_party import ThirdPartyLock, ThirdPartyLockError, acquire_all, load_lock

_yaml = ensure_yaml()
CATALOG_REL = Path("agents") / "skills-defaults.yaml"
LOCK_REL = Path("agents") / "skills-defaults.lock.yaml"
THIRD_PARTY_OWNER = "agents:third-party:"
KIRO_THIRD_PARTY_OWNER = "agents:kiro-third-party:"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def skills_target() -> Path:
    return Path.home() / ".agents" / "skills"


def first_party_skill_ids(root: Path) -> List[str]:
    skills_root = root / "agents" / "skills"
    if not skills_root.is_dir():
        return []
    return sorted(path.name for path in skills_root.iterdir() if path.is_dir() and (path / "SKILL.md").is_file())


def load_catalog(root: Path) -> ThirdPartyLock:
    catalog_path = root / CATALOG_REL
    lock_path = root / LOCK_REL
    try:
        catalog = _yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, _yaml.YAMLError) as exc:
        raise ThirdPartyLockError(f"cannot read third-party defaults catalog: {catalog_path}") from exc
    if not isinstance(catalog, dict) or set(catalog) != {"version", "lock", "skills"}:
        raise ThirdPartyLockError("third-party defaults catalog has missing or unknown keys")
    if catalog["version"] != 2 or catalog["lock"] != LOCK_REL.name or not isinstance(catalog["skills"], list):
        raise ThirdPartyLockError("third-party defaults catalog version/lock/skills is invalid")
    ids = catalog["skills"]
    if any(not isinstance(item, str) or not item for item in ids) or len(ids) != len(set(ids)):
        raise ThirdPartyLockError("third-party defaults catalog skill ids are invalid or duplicate")
    lock = load_lock(lock_path)
    locked_ids = [item.id for item in lock.skills]
    if ids != locked_ids:
        missing = sorted(set(ids) - set(locked_ids))
        extra = sorted(set(locked_ids) - set(ids))
        raise ThirdPartyLockError(
            "third-party defaults must exactly match the strict lock "
            f"(unlocked={missing}, unselected={extra})"
        )
    overlap = sorted(set(ids).intersection(first_party_skill_ids(root)))
    if overlap:
        raise ThirdPartyLockError("third-party defaults overlap first-party skills: " + ", ".join(overlap))
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
    destinations = (
        _destination_specs((dest_root,))
        if dest_root is not None
        else _destination_specs(dest_roots)
    )
    if dry_run:
        for destination, _, layout in destinations:
            print(f"==> locked default skills ({layout}) → {destination}")
            for item in lock.skills:
                print(
                    f"  + {item.id} revision={item.revision} content={item.content_hash} "
                    f"license={item.license.spdx} audit={item.audit.status}@{item.audit.date}/{item.audit.tool}"
                )
            print(f"  done defaults ({layout}, plan): locked={len(lock.skills)} network=none writes=none")
        return 0

    try:
        with tempfile.TemporaryDirectory(prefix="dotf-third-party-") as temporary:
            staging = Path(temporary) / "acquired"
            source_root = acquire_all(lock, staging)
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
                        f"agents/skills-defaults.lock.yaml@{lock.digest}{identity_suffix}"
                    ),
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
