#!/usr/bin/env python3
"""Report and verify third-party lock changes without re-deriving install policy.

`changed` answers "did content actually move, or is this a re-pin?" by diffing
the working lock against HEAD. `verify` re-acquires each locked revision over the
network and asks the installer's own planner what should be on disk, so stripped
authoring directories, per-layout rendering, and optional entries can never
drift from what `defaults` actually deploys.

Read-only: neither mode writes to a layout, the lock, or the runtime manifest.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Sequence

_SRC = Path(__file__).resolve().parent.parent
for _path in (_SRC, _SRC / "agents"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from desired_set import resolve_skill_desired_set  # noqa: E402
from layouts import (  # noqa: E402
    LAYOUTS,
    THIRD_PARTY_IDENTITY,
    SkillLayout,
    home_for_target,
    identity_prefix,
    owner_prefix,
    skills_target,
)
from lock_update import load_lock, load_lock_bytes  # noqa: E402
from managed_runtime import (  # noqa: E402
    AgentRuntimeError,
    RuntimeOperation,
    compile_skills_plan,
)
from sync import renderers_for  # noqa: E402
from third_party import (  # noqa: E402
    LockedSkill,
    ThirdPartyLock,
    ThirdPartyLockError,
    acquire_all,
)

LOCK_REL = Path("agents") / "skills.lock.yaml"

# What a skill's own scripts leave behind at runtime; never lock-deployed.
RUN_RESIDUE = frozenset({"__pycache__"})


def _git(args: Sequence[str], *, cwd: Path) -> str:
    proc = subprocess.run(
        list(args), cwd=str(cwd), text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"{' '.join(args)} failed: {detail}")
    return proc.stdout


class ChangeReport:
    def __init__(
        self,
        content: tuple[str, ...],
        revision_only: tuple[str, ...],
        added: tuple[str, ...],
        removed: tuple[str, ...],
    ) -> None:
        self.content = content
        self.revision_only = revision_only
        self.added = added
        self.removed = removed

    @property
    def verification_targets(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.content) | set(self.added)))


def diff_locks(previous: ThirdPartyLock, current: ThirdPartyLock) -> ChangeReport:
    """Compare two locks; ids present on one side only are added/removed."""
    before = {item.id: item for item in previous.skills}
    now = {item.id: item for item in current.skills}
    content: list[str] = []
    revision_only: list[str] = []
    for skill_id, item in now.items():
        old = before.get(skill_id)
        if old is None:
            continue
        if old.content_hash != item.content_hash:
            content.append(skill_id)
        elif old.revision != item.revision:
            revision_only.append(skill_id)
    return ChangeReport(
        tuple(sorted(content)),
        tuple(sorted(revision_only)),
        tuple(sorted(now.keys() - before.keys())),
        tuple(sorted(before.keys() - now.keys())),
    )


def report_changes(root: Path, current: ThirdPartyLock) -> ChangeReport:
    """Diff the working lock against HEAD."""
    try:
        previous_text = _git(["git", "show", f"HEAD:{LOCK_REL.as_posix()}"], cwd=root)
    except RuntimeError:
        return ChangeReport(
            tuple(sorted(item.id for item in current.skills)), (), (), ()
        )
    return diff_locks(load_lock_bytes(previous_text), current)


def print_changes(report: ChangeReport) -> None:
    for skill_id in report.content:
        print(f"~ {skill_id}\tcontent+revision")
    for skill_id in report.revision_only:
        print(f"  {skill_id}\trevision only")
    for skill_id in report.added:
        print(f"+ {skill_id}\tnew locked entry")
    for skill_id in report.removed:
        print(f"- {skill_id}\tdropped locked entry")
    print(
        f"changed_content={len(report.content)} "
        f"changed_revision_only={len(report.revision_only)} "
        f"added={len(report.added)} removed={len(report.removed)}"
    )


def _finding(op: RuntimeOperation, target_root: Path) -> str | None:
    """One line explaining a non-clean operation, or None when nothing to report."""
    relative = Path(op.target).relative_to(target_root).as_posix()
    if op.state == "unchanged":
        return None
    if op.action == "create":
        return f"missing {relative}"
    if op.action == "update":
        return f"content {relative}"
    if op.state == "conflict":
        return f"blocked {relative}: {op.conflict or 'owned target changed'}"
    if op.state == "unsafe":
        return f"unsafe {relative}"
    if op.state == "permission":
        return f"permission {relative}"
    if op.state == "prune":
        return f"prunable {relative}"
    return f"{op.state}/{op.action} {relative}"


def _extra_files(expected: set[str], skill_dir: Path) -> list[Path]:
    """Files under skill_dir that this lock's plan does not own (stale copies, residue)."""
    found: list[Path] = []
    if not skill_dir.is_dir():
        return found
    for current_root, dirs, files in os.walk(skill_dir):
        dirs[:] = [name for name in sorted(dirs) if name not in RUN_RESIDUE]
        found.extend(
            Path(current_root) / name
            for name in sorted(files)
            if str(Path(current_root) / name) not in expected
        )
    return found


def _check_layout(
    root: Path,
    layout: SkillLayout,
    lock: ThirdPartyLock,
    items: Sequence[LockedSkill],
    staging: Path,
) -> dict[str, list[str]]:
    """Ask the installer's planner what each layout should hold, and report deviations."""
    destination = skills_target(layout)
    plan = compile_skills_plan(
        root,
        renderers_for(layout),
        home=home_for_target(destination),
        target_root=destination,
        source_root=staging,
        owner_prefix=owner_prefix(layout, "third-party"),
        identity_prefix=identity_prefix(layout, f"{THIRD_PARTY_IDENTITY}@{lock.digest}"),
        include_unlisted=True,
        only_ids=frozenset(item.id for item in items),
    )
    expected = {op.target for op in plan.operations if op.state != "prune"}
    report: dict[str, list[str]] = {}
    for op in plan.operations:
        skill_id = Path(op.target).relative_to(destination).parts[0]
        line = _finding(op, destination)
        if line:
            report.setdefault(skill_id, []).append(line)
    for item in items:
        skill_dir = destination / item.id
        if not skill_dir.is_dir():
            report.setdefault(item.id, []).append(f"absent {item.id}/")
            continue
        for extra in _extra_files(expected, skill_dir):
            report.setdefault(item.id, []).append(
                f"unowned {extra.relative_to(destination).as_posix()}"
            )
    return report


def _acquire(lock: ThirdPartyLock, destination: Path) -> Path:
    """Indirection so tests can stub acquisition without hitting the network."""
    return acquire_all(lock, destination)


def verify(
    root: Path,
    *,
    lock: ThirdPartyLock,
    items: Sequence[LockedSkill],
    desired: frozenset[str],
    verbose: bool = False,
) -> int:
    if not items:
        print("nothing to verify")
        return 0
    outside = [item for item in items if item.id not in desired]
    inside = [item for item in items if item.id in desired]
    sources = len({item.source for item in items})
    print(f"==> verify {len(items)} skill(s) from {sources} source(s) at locked revisions")
    failures = 0
    with tempfile.TemporaryDirectory(prefix="dotf-lock-verify-") as temporary:
        staging_dir = Path(temporary)
        try:
            acquired = _acquire(replace(lock, skills=tuple(items)), staging_dir / "acquired")
        except ThirdPartyLockError as exc:
            print(f"HASH-FAIL {exc}")
            return 1
        print(f"    tree_hash == content_hash: {len(items)}/{len(items)} (license verified)")
        for item in outside:
            print(f"  NOT-INSTALLED {item.id} (outside desired set: optional or overlay-disabled)")
        if not inside:
            return 0
        for layout in LAYOUTS:
            present = [item for item in inside if (skills_target(layout) / item.id).is_dir()]
            absent = [item for item in inside if item not in present]
            report: dict[str, list[str]] = {}
            if present:
                try:
                    report = _check_layout(root, layout, lock, present, acquired)
                except (AgentRuntimeError, ThirdPartyLockError) as exc:
                    print(f"  {layout.key}: PLAN-FAIL {exc}")
                    failures += len(present)
                    continue
            for item in present:
                lines = sorted(set(report.get(item.id, ())))
                if not lines:
                    if verbose:
                        print(f"  {layout.key} {item.id}: ok")
                    continue
                failures += 1
                print(f"  {layout.key} {item.id}: FAIL")
                for line in lines if verbose else lines[:5]:
                    print(f"      {line}")
            for item in absent:
                failures += 1
                print(f"  {layout.key} {item.id}: FAIL (directory absent)")
    print(f"failures={failures}")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("changed", "verify"))
    parser.add_argument("--root", type=Path, default=None, help="repository root (default: git toplevel)")
    parser.add_argument("--ids", default="", help="comma-separated ids to verify (default: content-changed + added)")
    parser.add_argument("--all", action="store_true", help="verify every locked entry")
    parser.add_argument("--verbose", action="store_true", help="print clean skills and all findings")
    args = parser.parse_args(argv)
    root = (args.root or Path(_git(["git", "rev-parse", "--show-toplevel"], cwd=Path.cwd()).strip())).expanduser().absolute()
    try:
        lock = load_lock(root / LOCK_REL)
    except ThirdPartyLockError as exc:
        print(f"lock unreadable: {exc}", file=sys.stderr)
        return 1
    by_id = {item.id: item for item in lock.skills}
    if args.mode == "changed":
        print_changes(report_changes(root, lock))
        return 0
    if args.all:
        selected = list(lock.skills)
    elif args.ids:
        requested = [part.strip() for part in args.ids.split(",") if part.strip()]
        unknown = [skill_id for skill_id in requested if skill_id not in by_id]
        if unknown:
            print(f"not in lock: {', '.join(unknown)}", file=sys.stderr)
            return 1
        selected = [by_id[skill_id] for skill_id in requested]
    else:
        selected = [
            by_id[skill_id] for skill_id in report_changes(root, lock).verification_targets
        ]
    return verify(
        root, lock=lock, items=selected, desired=resolve_skill_desired_set(root),
        verbose=args.verbose,
    )


if __name__ == "__main__":
    raise SystemExit(main())
