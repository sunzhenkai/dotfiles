#!/usr/bin/env python3
"""Promote third-party lock entries to each source's current HEAD.

Install still consumes only the lock. This command rewrites the lock in the
repository after fetching, hashing, and auditing the new revision.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tempfile
from collections import OrderedDict
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Callable, Mapping, Sequence

_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from third_party import (  # noqa: E402
    LOCK_KIND,
    LOCK_VERSION,
    REVISION,
    AuditLock,
    LicenseLock,
    LockedSkill,
    ThirdPartyLock,
    ThirdPartyLockError,
    load_lock,
    tree_hash,
    verify_checkout,
)

Run = Callable[..., subprocess.CompletedProcess[str]]
Audit = Callable[[Path], tuple[int, str]]

LOCK_REL = Path("agents") / "skills.lock.yaml"
AUDIT_REL = Path("agents") / "skills" / "skills-store" / "scripts" / "audit-skill.sh"
AUDIT_TOOL = AUDIT_REL.as_posix()
LOCK_HEADER = (
    "# Strict third-party skills lock. Do not add an entry without externally\n"
    "# verifiable license and audit evidence for the exact immutable revision/hash.\n"
)


class LockUpdateError(RuntimeError):
    pass


class AuditBlocked(LockUpdateError):
    """Critical audit finding; this skill must stay on its locked revision."""


@dataclass(frozen=True, slots=True)
class SourceUpdate:
    source: str
    previous: str
    revision: str
    skill_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UpdateResult:
    updated: tuple[SourceUpdate, ...]
    current: tuple[str, ...]
    blocked: tuple[str, ...]
    wrote: bool


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def dump_lock(skills: Sequence[LockedSkill]) -> str:
    lines = [
        LOCK_HEADER.rstrip("\n"),
        f"schema_version: {LOCK_VERSION}",
        f"kind: {LOCK_KIND}",
        "skills:",
    ]
    for item in skills:
        lines.extend(
            [
                f"  - id: {item.id}",
                f"    source: {item.source}",
                f"    revision: {item.revision}",
                f"    subdirectory: {item.subdirectory}",
                f"    content_hash: {item.content_hash}",
                "    license:",
                f"      spdx: {item.license.spdx}",
                f"      file: {item.license.file}",
                f"      hash: {item.license.hash}",
                "    audit:",
                f"      status: {item.audit.status}",
                f"      date: '{item.audit.date}'",
                f"      tool: {item.audit.tool}",
                f"      evidence: {item.audit.evidence}",
            ]
        )
    return "\n".join(lines) + "\n"


def _git(args: Sequence[str], *, cwd: Path, run: Run) -> str:
    proc = run(list(args), cwd=str(cwd), text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise LockUpdateError(f"{' '.join(args)} failed: {detail}")
    return proc.stdout.strip()


def origin_url(source: str, aliases: Mapping[str, str] | None) -> str:
    if aliases and source in aliases:
        return aliases[source]
    return source


def resolve_tip(origin: str, *, cwd: Path, run: Run) -> str:
    output = _git(["git", "ls-remote", origin, "HEAD"], cwd=cwd, run=run)
    for line in output.splitlines():
        sha, sep, ref = line.partition("\t")
        if not sep or ref != "HEAD":
            continue
        if REVISION.fullmatch(sha) is None:
            raise LockUpdateError(f"{origin}: HEAD is not a full commit id: {sha}")
        return sha
    raise LockUpdateError(f"{origin}: git ls-remote did not report HEAD")


def materialize(origin: str, destination: Path, revision: str, *, run: Run) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    _git(["git", "init", "--quiet"], cwd=destination, run=run)
    _git(["git", "remote", "add", "origin", origin], cwd=destination, run=run)
    _git(
        ["git", "fetch", "--quiet", "--depth=1", "origin", revision],
        cwd=destination,
        run=run,
    )
    _git(["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"], cwd=destination, run=run)
    got = _git(["git", "rev-parse", "HEAD"], cwd=destination, run=run)
    if got != revision:
        raise LockUpdateError(f"{origin}: fetched {got}, expected {revision}")


def _promote(
    item: LockedSkill,
    checkout: Path,
    revision: str,
    *,
    today: str,
) -> LockedSkill:
    license_path = checkout / item.license.file
    try:
        license_path.relative_to(checkout)
    except ValueError as exc:
        raise LockUpdateError(f"{item.id}: license path escapes checkout") from exc
    if license_path.is_symlink() or not license_path.is_file():
        raise LockUpdateError(f"{item.id}: license file is missing at {revision}")
    skill = checkout / item.subdirectory
    try:
        skill.relative_to(checkout)
    except ValueError as exc:
        raise LockUpdateError(f"{item.id}: skill path escapes checkout") from exc
    if skill.is_symlink() or not skill.is_dir():
        raise LockUpdateError(f"{item.id}: subdirectory missing at {revision}")
    if not (skill / "SKILL.md").is_file() or (skill / "SKILL.md").is_symlink():
        raise LockUpdateError(f"{item.id}: SKILL.md missing at {revision}")
    promoted = replace(
        item,
        revision=revision,
        content_hash=tree_hash(skill),
        license=replace(
            item.license,
            hash=hashlib.sha256(license_path.read_bytes()).hexdigest(),
        ),
        audit=replace(
            item.audit,
            status="approved",
            date=today,
            tool=AUDIT_TOOL,
            evidence=f"{item.source}/commit/{revision}",
        ),
    )
    verify_checkout(promoted, checkout, revision)
    return promoted


def _default_audit(skill_dir: Path, script: Path) -> tuple[int, str]:
    if not script.is_file():
        raise LockUpdateError(f"audit script missing: {script}")
    proc = subprocess.run(
        [str(script), str(skill_dir)],
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()


def _audit_skill(
    item: LockedSkill,
    checkout: Path,
    *,
    accept_warn: bool,
    audit: Audit,
) -> None:
    rc, output = audit(checkout / item.subdirectory)
    if output:
        print(output)
    if rc == 0:
        return
    if rc == 1 and accept_warn:
        print(f"warning: {item.id}: audit warnings accepted")
        return
    if rc == 1:
        raise LockUpdateError(
            f"{item.id}: audit reported warnings; re-run without --fail-on-warn after review"
        )
    raise AuditBlocked(f"{item.id}: audit failed (exit {rc})")


def update_lock(
    root: Path,
    *,
    dry_run: bool = False,
    accept_warn: bool = True,
    run: Run = subprocess.run,
    audit: Audit | None = None,
    today: str | None = None,
    aliases: Mapping[str, str] | None = None,
    workdir: Path | None = None,
) -> UpdateResult:
    lock_path = root / LOCK_REL
    try:
        lock = load_lock(lock_path)
    except ThirdPartyLockError as exc:
        raise LockUpdateError(str(exc)) from exc
    grouped: OrderedDict[str, list[LockedSkill]] = OrderedDict()
    for item in lock.skills:
        grouped.setdefault(item.source, []).append(item)

    audit_fn = audit or (lambda skill_dir: _default_audit(skill_dir, root / AUDIT_REL))
    day = today or date.today().isoformat()
    by_id = {item.id: item for item in lock.skills}
    updated: list[SourceUpdate] = []
    current: list[str] = []
    blocked: list[str] = []

    def _refresh(staging: Path) -> None:
        for source, items in grouped.items():
            origin = origin_url(source, aliases)
            print(f"==> lock-update  {source}", flush=True)
            tip = resolve_tip(origin, cwd=root, run=run)
            locked_revisions = sorted({item.revision for item in items})
            if all(item.revision == tip for item in items):
                print(f"    current  {tip[:12]}  ({len(items)} skills)")
                current.append(source)
                continue
            previous = ",".join(rev[:12] for rev in locked_revisions)
            print(f"    {previous} → {tip[:12]}  ({len(items)} skills)")
            checkout = staging / hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
            materialize(origin, checkout, tip, run=run)
            promoted_ids: list[str] = []
            for item in items:
                try:
                    promoted = _promote(item, checkout, tip, today=day)
                    _audit_skill(item, checkout, accept_warn=accept_warn, audit=audit_fn)
                except AuditBlocked as exc:
                    print(f"    keep {item.id} @ {item.revision[:12]}  ({exc})")
                    blocked.append(item.id)
                    continue
                by_id[item.id] = promoted
                promoted_ids.append(item.id)
            if not promoted_ids:
                print(f"    skipped write for {source}: every skill blocked")
                continue
            updated.append(
                SourceUpdate(
                    source=source,
                    previous=locked_revisions[0] if len(locked_revisions) == 1 else previous,
                    revision=tip,
                    skill_ids=tuple(promoted_ids),
                )
            )

    if workdir is None:
        with tempfile.TemporaryDirectory(prefix="dotf-lock-update-") as temporary:
            _refresh(Path(temporary))
    else:
        _refresh(workdir)

    skills = tuple(by_id[item.id] for item in lock.skills)
    if not updated:
        print("  done lock-update: already current")
        return UpdateResult(
            updated=(), current=tuple(current), blocked=tuple(blocked), wrote=False
        )

    payload = dump_lock(skills)
    load_lock_bytes(payload)
    if dry_run:
        print(
            f"  done lock-update (plan): sources={len(updated)} "
            f"blocked={len(blocked)} writes=none"
        )
        return UpdateResult(
            updated=tuple(updated),
            current=tuple(current),
            blocked=tuple(blocked),
            wrote=False,
        )
    lock_path.write_text(payload, encoding="utf-8")
    print(f"  wrote {LOCK_REL}  sources={len(updated)} blocked={len(blocked)}")
    return UpdateResult(
        updated=tuple(updated),
        current=tuple(current),
        blocked=tuple(blocked),
        wrote=True,
    )


def load_lock_bytes(payload: str) -> ThirdPartyLock:
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", encoding="utf-8", delete=False) as handle:
        handle.write(payload)
        path = Path(handle.name)
    try:
        return load_lock(path)
    finally:
        path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch each lock source HEAD, audit, and rewrite agents/skills.lock.yaml"
    )
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--fail-on-warn",
        action="store_true",
        help="stop when audit-skill.sh exits 1 (warnings only); default is to accept warnings",
    )
    parser.add_argument(
        "--accept-warn",
        action="store_true",
        help="deprecated no-op; warnings are accepted by default",
    )
    args = parser.parse_args(argv)
    root = (args.root or repo_root()).resolve()
    try:
        update_lock(root, dry_run=args.dry_run, accept_warn=not args.fail_on_warn)
    except LockUpdateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
