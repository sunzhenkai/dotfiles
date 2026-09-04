#!/usr/bin/env python3
"""Install only strictly locked, audited third-party skills through runtime ownership."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import List, Optional
import sys

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from ensure_pyyaml import ensure_yaml
from managed_runtime import AgentRuntimeConflict, apply_skills_plan, compile_skills_plan
from sync import render_skill_bytes
from third_party import ThirdPartyLock, ThirdPartyLockError, acquire_all, load_lock

_yaml = ensure_yaml()
CATALOG_REL = Path("agents") / "skills-defaults.yaml"
LOCK_REL = Path("agents") / "skills-defaults.lock.yaml"
THIRD_PARTY_OWNER = "agents:third-party:"


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
    return Path.home().expanduser().absolute()


def install_defaults(
    root: Path,
    *,
    dry_run: bool = False,
    dest_root: Optional[Path] = None,
) -> int:
    """Verify the strict lock; apply only bytes acquired and checked in private staging."""
    lock = load_catalog(root)
    destination = (dest_root or skills_target()).expanduser().absolute()
    print(f"==> locked default skills → {destination}")
    if dry_run:
        for item in lock.skills:
            print(
                f"  + {item.id} revision={item.revision} content={item.content_hash} "
                f"license={item.license.spdx} audit={item.audit.status}@{item.audit.date}/{item.audit.tool}"
            )
        print(f"  done defaults (plan): locked={len(lock.skills)} network=none writes=none")
        return 0

    home = _home_for_target(destination)
    try:
        with tempfile.TemporaryDirectory(prefix="dotf-third-party-") as temporary:
            staging = Path(temporary) / "acquired"
            source_root = acquire_all(lock, staging)
            plan = compile_skills_plan(
                root,
                render_skill_bytes,
                home=home,
                target_root=destination,
                source_root=source_root,
                owner_prefix=THIRD_PARTY_OWNER,
                identity_prefix=f"agents/skills-defaults.lock.yaml@{lock.digest}",
            )
            result = apply_skills_plan(plan, render_skill_bytes)
    except (ThirdPartyLockError, AgentRuntimeConflict, OSError, ValueError) as exc:
        print(f"error: locked third-party skills: {exc}", file=__import__("sys").stderr)
        return 1
    print(
        f"  done defaults: locked={len(lock.skills)} changed={result.changed} "
        f"pruned={result.pruned} unchanged={result.unchanged}"
    )
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
