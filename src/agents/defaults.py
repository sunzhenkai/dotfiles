#!/usr/bin/env python3
"""Install only strictly locked, audited third-party skills through runtime ownership."""

from __future__ import annotations

import argparse
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import List, Optional, Sequence

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from layouts import (
    LAYOUTS,
    SHARED_LAYOUT,
    THIRD_PARTY_IDENTITY,
    SkillLayout,
    home_for_target,
    identity_prefix,
    layout_for_target,
    owner_prefix,
    skills_target,
)
from managed_runtime import (
    AgentRuntimeConflict,
    OnConflict,
    OnTakeover,
    adoptable_equivalent,
    apply_skills_plan,
    compile_skills_plan,
    on_conflict_from_env,
    on_takeover_from_env,
    skill_id_from_target,
)
from skills_catalog import (
    SkillsCatalogError,
    load_skills_catalog,
    validate_first_party_coverage,
)
from sync import SyncOutcome, renderers_for
from third_party import (
    ThirdPartyLock,
    ThirdPartyLockError,
    acquire_all,
    load_lock,
    resolve_locked_skills,
)

_DEFAULT_ACQUIRE_ALL = acquire_all
CATALOG_REL = Path("agents") / "skills.yaml"
LOCK_REL = Path("agents") / "skills.lock.yaml"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def first_party_skill_ids(root: Path) -> List[str]:
    """First-party ids per the catalog (the single source of truth)."""
    return load_skills_catalog(root).first_party_ids()


def catalog_skill_ids(root: Path) -> List[str]:
    """Every catalogued id, including `optional` ones."""
    return load_skills_catalog(root).ids()


def load_skills_lock(root: Path) -> ThirdPartyLock:
    """Load the strict third-party lock referenced by the catalog."""
    return load_lock(root / LOCK_REL)


def load_catalog(root: Path) -> ThirdPartyLock:
    """Validate the unified catalog against the strict lock and return the lock."""
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


def _destination_specs(
    dest_roots: Optional[Sequence[Path]],
) -> tuple[tuple[SkillLayout, Path], ...]:
    """Explicit destinations keep their layout when recognisable, else shared."""
    if dest_roots is not None:
        return tuple(
            (layout_for_target(destination) or SHARED_LAYOUT, destination.expanduser().absolute())
            for destination in dest_roots
        )
    return tuple((layout, skills_target(layout)) for layout in LAYOUTS)


def sync_defaults(
    root: Path,
    *,
    dry_run: bool = False,
    dest_root: Optional[Path] = None,
    dest_roots: Optional[Sequence[Path]] = None,
    on_conflict: OnConflict | None = None,
    on_takeover: OnTakeover | None = None,
) -> list[SyncOutcome]:
    """Verify the strict lock and install selected third-party skills; return per-layout outcomes."""
    lock = load_catalog(root)
    from desired_set import resolve_skill_desired_set

    policy = on_conflict if on_conflict is not None else on_conflict_from_env()
    takeover = on_takeover if on_takeover is not None else on_takeover_from_env()
    desired = resolve_skill_desired_set(root)
    selected = tuple(item for item in lock.skills if item.id in desired)
    destinations = (
        _destination_specs((dest_root,))
        if dest_root is not None
        else _destination_specs(dest_roots)
    )
    if dry_run:
        outcomes: list[SyncOutcome] = []
        for layout, destination in destinations:
            print(f"==> locked default skills ({layout.key}) → {destination}")
            for item in selected:
                print(
                    f"    {item.id} revision={item.revision} content={item.content_hash} "
                    f"license={item.license.spdx} audit={item.audit.status}@{item.audit.date}/{item.audit.tool}"
                )
            print(f"  done defaults ({layout.key}, plan): locked={len(selected)} network=none writes=none")
            outcomes.append(SyncOutcome(f"defaults ({layout.key})", 0))
        return outcomes

    outcomes = []
    only_ids = frozenset(item.id for item in selected)

    def _apply_for_destinations(
        *, source_root: Path | None = None, skill_dirs: dict[str, Path] | None = None
    ) -> None:
        for layout, destination in destinations:
            print(f"==> defaults  {layout.key}  planning…", flush=True)
            home = home_for_target(destination)
            renderer = renderers_for(layout)
            try:
                plan = compile_skills_plan(
                    root,
                    renderer,
                    home=home,
                    target_root=destination,
                    source_root=source_root,
                    skill_dirs=skill_dirs,
                    owner_prefix=owner_prefix(layout, "third-party"),
                    identity_prefix=identity_prefix(layout, THIRD_PARTY_IDENTITY),
                    include_unlisted=True,
                    only_ids=only_ids,
                    on_conflict=policy,
                    on_takeover=takeover,
                )
                adoptable = {item.target for item in adoptable_equivalent(plan)}
                blocking = [op for op in plan.conflicts if op.target not in adoptable]
                blocked_reasons: dict[str, str] = {}
                for operation in blocking:
                    sid = skill_id_from_target(operation.target, destination) or "?"
                    blocked_reasons.setdefault(sid, operation.conflict or "conflict")
                    print(
                        f"  ✗ {operation.target}: {operation.conflict or 'conflict'}",
                        file=sys.stderr,
                        flush=True,
                    )
                result = apply_skills_plan(plan, renderer)
                skipped = ",".join(result.skipped_skills) if result.skipped_skills else ""
                print(
                    f"  done defaults ({layout.key}): locked={len(selected)} changed={result.changed} "
                    f"pruned={result.pruned} unchanged={result.unchanged}"
                    + (f" skipped={skipped}" if skipped else ""),
                    flush=True,
                )
                if result.skipped_skills:
                    first_sid = result.skipped_skills[0]
                    detail = f"{first_sid}: {blocked_reasons.get(first_sid, 'conflict')}"
                    print(f"error: defaults ({layout.key}): {detail}", file=sys.stderr, flush=True)
                    outcomes.append(SyncOutcome(f"defaults ({layout.key})", 1, detail))
                else:
                    outcomes.append(SyncOutcome(f"defaults ({layout.key})", 0))
            except (AgentRuntimeConflict, OSError, ValueError) as exc:
                print(f"error: defaults ({layout.key}): {exc}", file=sys.stderr)
                outcomes.append(SyncOutcome(f"defaults ({layout.key})", 1, str(exc)))

    try:
        filtered = replace(lock, skills=selected)
        if not selected:
            with tempfile.TemporaryDirectory(prefix="dotf-third-party-") as temporary:
                empty_root = Path(temporary) / "empty"
                empty_root.mkdir(parents=True, exist_ok=True)
                _apply_for_destinations(source_root=empty_root)
        elif acquire_all is _DEFAULT_ACQUIRE_ALL:
            skill_dirs = resolve_locked_skills(filtered)
            _apply_for_destinations(skill_dirs=skill_dirs)
        else:
            with tempfile.TemporaryDirectory(prefix="dotf-third-party-") as temporary:
                staging = Path(temporary) / "acquired"
                source_root = acquire_all(filtered, staging)
                _apply_for_destinations(source_root=source_root)
    except (ThirdPartyLockError, OSError, ValueError) as exc:
        print(f"error: defaults: {exc}", file=sys.stderr)
        return [SyncOutcome("defaults", 1, str(exc))]
    return outcomes


def install_defaults(
    root: Path,
    *,
    dry_run: bool = False,
    dest_root: Optional[Path] = None,
    dest_roots: Optional[Sequence[Path]] = None,
    on_conflict: OnConflict | None = None,
    on_takeover: OnTakeover | None = None,
) -> int:
    """Verify the strict lock; apply selected third-party skills."""
    outcomes = sync_defaults(
        root,
        dry_run=dry_run,
        dest_root=dest_root,
        dest_roots=dest_roots,
        on_conflict=on_conflict,
        on_takeover=on_takeover,
    )
    return max((item.rc for item in outcomes), default=0)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Install audited third-party skills from the strict lock")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--on-conflict", choices=("block", "backup"), default=None)
    parser.add_argument("--takeover", choices=("skip", "backup"), default=None, dest="on_takeover")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    root = args.root.resolve() if args.root else repo_root()
    try:
        return install_defaults(
            root,
            dry_run=args.dry_run,
            on_conflict=args.on_conflict,
            on_takeover=args.on_takeover,
        )
    except ThirdPartyLockError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
