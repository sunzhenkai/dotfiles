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
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path, PurePosixPath

_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import catalog_edit  # noqa: E402
from skills_catalog import (  # noqa: E402
    SkillsCatalogError,
    load_skills_catalog,
    parse_catalog,
)
from third_party import (  # noqa: E402
    FETCH_ATTEMPTS,
    FETCH_RETRY_SECONDS,
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

from ensure_pyyaml import ensure_yaml  # noqa: E402

_yaml = ensure_yaml()

Run = Callable[..., subprocess.CompletedProcess[str]]
Audit = Callable[[Path], tuple[int, str]]

LOCK_REL = Path("agents") / "skills.lock.yaml"
AUDIT_REL = Path("agents") / "skills" / "skills-store" / "scripts" / "audit-skill.sh"
# source checkout 自带的 skills-store（first-party 迁出后，审计脚本随被锁 revision 走）
CHECKOUT_AUDIT_REL = Path("skills") / "skills-store" / "scripts" / "audit-skill.sh"
# 本机受管安装副本（经 lock 校验后下发；checkout 不含 skills-store 的 source 用它兜底）
INSTALLED_AUDIT_REL = Path("~") / ".agents" / "skills" / "skills-store" / "scripts" / "audit-skill.sh"
AUDIT_TOOL = AUDIT_REL.as_posix()
LOCK_HEADER = (
    "# Strict third-party skills lock. Do not add an entry without externally\n"
    "# verifiable license and audit evidence for the exact immutable revision/hash.\n"
)


# 阻断原因要活到 stdout 末尾：审计输出可达数百行，而 checkout 是 TemporaryDirectory，
# 跑完即删，尾部读不到原因就只能重新取上游。
MAX_BLOCKED_FINDINGS = 8
MAX_BLOCKED_REPORTED = 5


class LockUpdateError(RuntimeError):
    pass


class AuditBlocked(LockUpdateError):
    """Critical audit finding; this skill must stay on its locked revision."""

    def __init__(self, message: str, *, findings: Sequence[str] = ()) -> None:
        super().__init__(message)
        self.findings: tuple[str, ...] = tuple(findings)


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


def _yaml_scalar(value: str) -> str:
    if value and all(ch.isalnum() or ch in "-_./:@" for ch in value):
        return value
    return "'" + value.replace("'", "''") + "'"


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
                f"  - id: {_yaml_scalar(item.id)}",
                f"    source: {_yaml_scalar(item.source)}",
                f"    revision: {_yaml_scalar(item.revision)}",
                f"    subdirectory: {_yaml_scalar(item.subdirectory)}",
                f"    content_hash: {_yaml_scalar(item.content_hash)}",
                "    license:",
                f"      spdx: {_yaml_scalar(item.license.spdx)}",
                f"      file: {_yaml_scalar(item.license.file)}",
                f"      hash: {_yaml_scalar(item.license.hash)}",
                "    audit:",
                f"      status: {_yaml_scalar(item.audit.status)}",
                f"      date: '{item.audit.date}'",
                f"      tool: {_yaml_scalar(item.audit.tool)}",
                f"      evidence: {_yaml_scalar(item.audit.evidence)}",
            ]
        )
    return "\n".join(lines) + "\n"


def _git(
    args: Sequence[str], *, cwd: Path, run: Run, attempts: int = 1
) -> str:
    """Run one git command; `attempts` > 1 retries transient network failures.

    取上游是整条流程唯一的网络成本，一次 TLS 抖动就让整轮从头再来，所以网络
    命令都带重试（与 third_party 的取回路径一致）。
    """
    detail = "no attempt was made"
    for attempt in range(1, attempts + 1):
        proc = run(list(args), cwd=str(cwd), text=True, capture_output=True, check=False)
        if proc.returncode == 0:
            return proc.stdout.strip()
        detail = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        if attempt < attempts:
            time.sleep(FETCH_RETRY_SECONDS[min(attempt, len(FETCH_RETRY_SECONDS)) - 1])
    raise LockUpdateError(f"{' '.join(args)} failed: {detail}")


def origin_url(source: str, aliases: Mapping[str, str] | None) -> str:
    if aliases and source in aliases:
        return aliases[source]
    return source


def resolve_tip(origin: str, *, cwd: Path, run: Run) -> str:
    output = _git(
        ["git", "ls-remote", origin, "HEAD"],
        cwd=cwd,
        run=run,
        attempts=FETCH_ATTEMPTS,
    )
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
        attempts=FETCH_ATTEMPTS,
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
    tool: str = AUDIT_TOOL,
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
            tool=tool,
            evidence=f"{item.source}/commit/{revision}",
        ),
    )
    verify_checkout(promoted, checkout, revision)
    return promoted


def discover_skills(checkout: Path, items: Sequence[LockedSkill]) -> dict[str, str]:
    """Upstream skill directories next to the locked ones, as {subdirectory: id}.

    Scope is the parent directories already represented in the lock: a sibling
    directory with its own SKILL.md is a new skill, while `in-progress/`,
    `misc/` and other sibling trees stay out of discovery.
    """
    parents = {PurePosixPath(item.subdirectory).parent for item in items}
    known = {item.subdirectory for item in items}
    taken = {item.id for item in items}
    found: dict[str, str] = {}
    for parent in parents:
        directory = checkout if parent == PurePosixPath(".") else checkout / parent
        if not directory.is_dir() or directory.is_symlink():
            continue
        for child in sorted(directory.iterdir()):
            subdirectory = (parent / child.name).as_posix()
            if subdirectory in known:
                continue
            if (
                not child.is_dir()
                or child.is_symlink()
                or not (child / "SKILL.md").is_file()
            ):
                continue
            if child.name in taken:
                raise LockUpdateError(
                    f"discovered {subdirectory!r} reuses the locked id {child.name!r}"
                )
            found[subdirectory] = child.name
    return found


def _seed_lock(
    skill_id: str, source: str, subdirectory: str, donor: LockedSkill
) -> LockedSkill:
    """Placeholder entry for a discovered directory; _promote fills the hashes."""
    return LockedSkill(
        skill_id,
        source,
        donor.revision,
        subdirectory,
        "",
        LicenseLock(donor.license.spdx, donor.license.file, ""),
        AuditLock(
            donor.audit.status, donor.audit.date, donor.audit.tool, donor.audit.evidence
        ),
    )


def _apply_catalog(
    root: Path, added: Mapping[str, Sequence[str]], removed: Sequence[LockedSkill]
) -> None:
    """Add discovered ids to their source's group; drop removed ones.

    Optional keeps discovery visible without widening the default install: a
    promoted upstream directory never reaches an agent home unannounced.
    """
    if not added and not removed:
        return
    path = root / catalog_edit.CATALOG_REL
    if not path.is_file() or path.is_symlink():
        raise LockUpdateError(f"missing {catalog_edit.CATALOG_REL}: {path}")
    try:
        catalog = load_skills_catalog(root)
    except SkillsCatalogError as exc:
        raise LockUpdateError(str(exc)) from exc
    group_for_source: dict[str, str] = {}
    for entry in catalog.skills:
        if entry.package:
            group_for_source.setdefault(entry.package, entry.group)
    by_id = catalog.by_id()
    text = path.read_text(encoding="utf-8")
    for source, skill_ids in added.items():
        group = group_for_source.get(source)
        if group is None:
            print(
                f"warning: no catalog group for {source}; "
                f"{', '.join(skill_ids)} left lock-only"
            )
            continue
        for skill_id in skill_ids:
            if skill_id not in catalog_edit.member_ids(text, group):
                text = catalog_edit.add_optional_member(text, group, skill_id)
    for item in removed:
        entry = by_id.get(item.id)
        if entry is not None and item.id in catalog_edit.member_ids(text, entry.group):
            text = catalog_edit.remove_member(text, entry.group, item.id)
    try:
        parse_catalog(_yaml.safe_load(text))
    except SkillsCatalogError as exc:
        raise LockUpdateError(
            f"catalog edit produced an invalid catalogue: {exc}"
        ) from exc
    path.write_text(text, encoding="utf-8")


def resolve_audit_script(root: Path, checkout: Path | None) -> tuple[Path, str]:
    """审计脚本来源回退链，返回 (脚本路径, lock tool 字段标签)。

    仓内 first-party 副本优先（first-party 概念保留，未来可落回）；缺省时用本次
    checkout 自带的 skills-store（版本与被锁 revision 自洽）；checkout 不含
    skills-store 的 source 退回本机受管安装副本。
    """
    candidates: list[tuple[Path, Path, str]] = [(root, root / AUDIT_REL, AUDIT_TOOL)]
    if checkout is not None:
        candidates.append(
            (
                checkout,
                checkout / CHECKOUT_AUDIT_REL,
                CHECKOUT_AUDIT_REL.as_posix() + " (source checkout)",
            )
        )
    installed = INSTALLED_AUDIT_REL.expanduser()
    candidates.append(
        (installed.parent, installed, INSTALLED_AUDIT_REL.as_posix())
    )
    for base, script, label in candidates:
        if script.is_symlink() or not script.is_file():
            continue
        try:
            if not script.resolve().is_relative_to(base.resolve()):
                continue
        except OSError:
            continue
        return script, label
    raise LockUpdateError(
        "audit script not found; expected one of: "
        + ", ".join(str(script) for script, _ in candidates)
    )


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


def blocking_findings(
    output: str, limit: int = MAX_BLOCKED_FINDINGS
) -> tuple[str, ...]:
    lines = output.splitlines()
    kept: list[str] = []
    total = shown = 0
    for index, line in enumerate(lines):
        if not line.startswith("[BLOCK]"):
            continue
        total += 1
        if shown >= limit:
            continue
        shown += 1
        kept.append(line)
        evidence = lines[index + 1] if index + 1 < len(lines) else ""
        if evidence[:1].isspace():
            kept.append(evidence.strip())
    if not kept:
        non_empty = [line.strip() for line in lines if line.strip()]
        return tuple(non_empty[-limit:])
    if total > shown:
        kept.append(f"({total - shown} more blocking findings)")
    return tuple(kept)


def report_blocked(detail: Sequence[tuple[str, Sequence[str]]]) -> None:
    if not detail:
        return
    print(f"  blocked {len(detail)} skill(s); audit findings:", flush=True)
    for skill_id, findings in detail[:MAX_BLOCKED_REPORTED]:
        print(f"    {skill_id}")
        for finding in findings:
            print(f"      {finding}")
    if len(detail) > MAX_BLOCKED_REPORTED:
        print(f"    ({len(detail) - MAX_BLOCKED_REPORTED} more blocked skills above)")


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
    raise AuditBlocked(
        f"{item.id}: audit failed (exit {rc})",
        findings=blocking_findings(output),
    )


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

    day = today or date.today().isoformat()
    by_id = {item.id: item for item in lock.skills}
    updated: list[SourceUpdate] = []
    current: list[str] = []
    blocked: list[str] = []
    blocked_detail: list[tuple[str, tuple[str, ...]]] = []
    added: list[tuple[str, str, str]] = []
    removed: list[LockedSkill] = []

    def _refresh(staging: Path) -> None:
        for source, items in grouped.items():
            origin = origin_url(source, aliases)
            print(f"==> lock-update  {source}", flush=True)
            tip = resolve_tip(origin, cwd=root, run=run)
            locked_revisions = sorted({item.revision for item in items})
            if not dry_run and all(item.revision == tip for item in items):
                # 锁就写在这个 tip 上：上游没有新提交，锁内各子目录和父目录下的
                # 兄弟目录都不可能变，取整棵树只为再确认一遍。跳过它，「什么都没
                # 变」的一轮就只剩 ls-remote（archify 那种 142MB 的仓尤其明显）。
                # dry-run 例外：它可能算出过新条目却没落盘，跳过就永远发现不了。
                print(f"    current  {tip[:12]}  ({len(items)} skills)")
                current.append(source)
                continue
            checkout = staging / hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
            materialize(origin, checkout, tip, run=run)
            gone = [
                item
                for item in items
                if not (checkout / item.subdirectory / "SKILL.md").is_file()
            ]
            kept = [item for item in items if item not in gone]
            discovered = discover_skills(checkout, kept)
            previous = ",".join(rev[:12] for rev in locked_revisions)
            print(f"    {previous} → {tip[:12]}  ({len(items)} skills)")
            if audit is not None:
                audit_fn: Audit = audit
                tool_label = AUDIT_TOOL
            else:
                script, tool_label = resolve_audit_script(root, checkout)

                def run_audit(
                    skill_dir: Path, _script: Path = script
                ) -> tuple[int, str]:
                    return _default_audit(skill_dir, _script)

                audit_fn = run_audit

            promoted_ids: list[str] = []
            for item in gone:
                print(
                    f"    drop {item.id}  ({item.subdirectory} missing at {tip[:12]})"
                )
                removed.append(item)
                del by_id[item.id]
            for item in kept:
                try:
                    promoted = _promote(item, checkout, tip, today=day, tool=tool_label)
                    _audit_skill(
                        item, checkout, accept_warn=accept_warn, audit=audit_fn
                    )
                except AuditBlocked as exc:
                    print(f"    keep {item.id} @ {item.revision[:12]}  ({exc})")
                    blocked.append(item.id)
                    blocked_detail.append((item.id, exc.findings))
                    continue
                by_id[item.id] = promoted
                promoted_ids.append(item.id)
            for subdirectory, skill_id in discovered.items():
                donor = kept[0]
                if skill_id in by_id:
                    raise LockUpdateError(
                        f"discovered {skill_id!r} collides with a locked entry"
                    )
                try:
                    promoted = _promote(
                        _seed_lock(skill_id, source, subdirectory, donor),
                        checkout,
                        tip,
                        today=day,
                        tool=tool_label,
                    )
                    _audit_skill(
                        promoted, checkout, accept_warn=accept_warn, audit=audit_fn
                    )
                except AuditBlocked as exc:
                    print(f"    skip new {skill_id}  ({exc})")
                    blocked.append(skill_id)
                    blocked_detail.append((skill_id, exc.findings))
                    continue
                by_id[skill_id] = promoted
                promoted_ids.append(skill_id)
                added.append((source, skill_id, subdirectory))
            if not promoted_ids and not removed:
                print(f"    skipped write for {source}: every skill blocked")
                continue
            updated.append(
                SourceUpdate(
                    source=source,
                    previous=locked_revisions[0]
                    if len(locked_revisions) == 1
                    else previous,
                    revision=tip,
                    skill_ids=tuple(promoted_ids),
                )
            )

    if workdir is None:
        with tempfile.TemporaryDirectory(prefix="dotf-lock-update-") as temporary:
            _refresh(Path(temporary))
    else:
        _refresh(workdir)

    report_blocked(blocked_detail)

    for _, skill_id, _ in added:
        print(f"  + {skill_id}\tnew locked entry")
    for item in removed:
        print(f"  - {item.id}\tremoved from lock")

    skills = (
        tuple(by_id[item.id] for item in lock.skills if item.id in by_id)
        + tuple(by_id[skill_id] for _, skill_id, _ in added if skill_id in by_id)
    )
    if not updated and not added and not removed:
        print("  done lock-update: already current")
        return UpdateResult(
            updated=(), current=tuple(current), blocked=tuple(blocked), wrote=False
        )

    payload = dump_lock(skills)
    if skills:
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
    added_by_source: dict[str, list[str]] = {}
    for source, skill_id, _ in added:
        added_by_source.setdefault(source, []).append(skill_id)
    _apply_catalog(root, added_by_source, removed)
    print(f"  wrote {LOCK_REL}  sources={len(updated)} blocked={len(blocked)}")
    return UpdateResult(
        updated=tuple(updated),
        current=tuple(current),
        blocked=tuple(blocked),
        wrote=True,
    )


def load_lock_bytes(payload: str) -> ThirdPartyLock:
    with tempfile.NamedTemporaryFile(
        "w", suffix=".yaml", encoding="utf-8", delete=False
    ) as handle:
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
