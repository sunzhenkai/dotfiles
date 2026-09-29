#!/usr/bin/env python3
"""Strict audited third-party skill lock, staged acquisition, and verification."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlparse

from ensure_pyyaml import ensure_yaml

_yaml = ensure_yaml()
LOCK_VERSION = 1
LOCK_KIND = "third-party-skills-lock"
REVISION = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
SPDX = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]*")
GIT_TIMEOUT_SECONDS = 180
CACHE_DIRNAME = "third-party-checkouts"




class _UniqueLoader(_yaml.SafeLoader):
    pass


def _unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ThirdPartyLockError(f"duplicate lock key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueLoader.add_constructor(
    _yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _unique_mapping,
)
class ThirdPartyLockError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class LicenseLock:
    spdx: str
    file: str
    hash: str


@dataclass(frozen=True, slots=True)
class AuditLock:
    status: str
    date: str
    tool: str
    evidence: str


@dataclass(frozen=True, slots=True)
class LockedSkill:
    id: str
    source: str
    revision: str
    subdirectory: str
    content_hash: str
    license: LicenseLock
    audit: AuditLock


@dataclass(frozen=True, slots=True)
class ThirdPartyLock:
    schema_version: int
    kind: str
    skills: tuple[LockedSkill, ...]
    digest: str


Run = Callable[..., subprocess.CompletedProcess[str]]


def _mapping(value: Any, label: str, keys: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ThirdPartyLockError(f"{label} has missing or unknown keys")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ThirdPartyLockError(f"{label} must be a non-empty string")
    return value


def _relative(value: Any, label: str) -> str:
    text = _text(value, label)
    path = PurePosixPath(text)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ThirdPartyLockError(f"{label} must be a safe relative path")
    return text


def _https_source(value: Any) -> str:
    source = _text(value, "source")
    parsed = urlparse(source)
    if parsed.scheme != "https" or parsed.hostname != "github.com" or parsed.query or parsed.fragment:
        raise ThirdPartyLockError("source must be an externally verifiable GitHub HTTPS URL")
    if len([part for part in parsed.path.split("/") if part]) != 2:
        raise ThirdPartyLockError("source must identify one GitHub repository")
    return source


def load_lock(path: Path) -> ThirdPartyLock:
    try:
        raw_bytes = path.read_bytes()
        raw = _yaml.load(raw_bytes.decode("utf-8"), Loader=_UniqueLoader)
    except (OSError, UnicodeError, _yaml.YAMLError) as exc:
        raise ThirdPartyLockError(f"cannot read third-party lock: {path}") from exc
    root = _mapping(raw, "third-party lock", {"schema_version", "kind", "skills"})
    if root["schema_version"] != LOCK_VERSION or isinstance(root["schema_version"], bool):
        raise ThirdPartyLockError("unsupported third-party lock schema_version")
    if root["kind"] != LOCK_KIND:
        raise ThirdPartyLockError("invalid third-party lock kind")
    if not isinstance(root["skills"], list):
        raise ThirdPartyLockError("third-party lock skills must be an array")
    skills: list[LockedSkill] = []
    seen: set[str] = set()
    for index, item in enumerate(root["skills"]):
        entry = _mapping(item, f"skills[{index}]", {
            "id", "source", "revision", "subdirectory", "content_hash", "license", "audit",
        })
        skill_id = _relative(entry["id"], f"skills[{index}].id")
        if "/" in skill_id or skill_id in seen:
            raise ThirdPartyLockError("third-party skill ids must be unique path components")
        seen.add(skill_id)
        revision = _text(entry["revision"], "revision")
        content_hash = _text(entry["content_hash"], "content_hash")
        if REVISION.fullmatch(revision) is None:
            raise ThirdPartyLockError("revision must be a full immutable 40-character commit id")
        if SHA256.fullmatch(content_hash) is None:
            raise ThirdPartyLockError("content_hash must be a lowercase sha256")
        license_raw = _mapping(entry["license"], "license", {"spdx", "file", "hash"})
        spdx = _text(license_raw["spdx"], "license.spdx")
        license_hash = _text(license_raw["hash"], "license.hash")
        if SPDX.fullmatch(spdx) is None or SHA256.fullmatch(license_hash) is None:
            raise ThirdPartyLockError("license requires SPDX id and lowercase file sha256")
        audit_raw = _mapping(entry["audit"], "audit", {"status", "date", "tool", "evidence"})
        if audit_raw["status"] != "approved":
            raise ThirdPartyLockError("third-party audit status must be approved")
        audit_date = _text(audit_raw["date"], "audit.date")
        try:
            date.fromisoformat(audit_date)
        except ValueError as exc:
            raise ThirdPartyLockError("audit.date must be ISO-8601") from exc
        evidence = _text(audit_raw["evidence"], "audit.evidence")
        parsed_evidence = urlparse(evidence)
        if parsed_evidence.scheme != "https" or not parsed_evidence.hostname:
            raise ThirdPartyLockError("audit.evidence must be an external HTTPS URL")
        skills.append(LockedSkill(
            id=skill_id,
            source=_https_source(entry["source"]),
            revision=revision,
            subdirectory=_relative(entry["subdirectory"], "subdirectory"),
            content_hash=content_hash,
            license=LicenseLock(spdx, _relative(license_raw["file"], "license.file"), license_hash),
            audit=AuditLock("approved", audit_date, _text(audit_raw["tool"], "audit.tool"), evidence),
        ))
    return ThirdPartyLock(LOCK_VERSION, LOCK_KIND, tuple(skills), hashlib.sha256(raw_bytes).hexdigest())


def tree_hash(directory: Path) -> str:
    """Hash names, executable bits, and bytes in stable UTF-8 path order; reject links/special files."""
    digest = hashlib.sha256()
    if directory.is_symlink() or not directory.is_dir():
        raise ThirdPartyLockError("acquired skill is not a real directory")
    entries = sorted(directory.rglob("*"), key=lambda path: path.relative_to(directory).as_posix().encode("utf-8"))
    for path in entries:
        relative = path.relative_to(directory).as_posix()
        item = path.lstat()
        if stat.S_ISLNK(item.st_mode):
            raise ThirdPartyLockError(f"acquired skill contains symlink: {relative}")
        if stat.S_ISDIR(item.st_mode):
            digest.update(b"d\0" + relative.encode("utf-8") + b"\0")
        elif stat.S_ISREG(item.st_mode):
            executable = b"x" if item.st_mode & 0o111 else b"-"
            digest.update(b"f\0" + relative.encode("utf-8") + b"\0" + executable + b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
        else:
            raise ThirdPartyLockError(f"acquired skill contains unsupported file type: {relative}")
    return digest.hexdigest()


def verify_checkout(lock: LockedSkill, checkout: Path, revision: str) -> Path:
    if revision != lock.revision:
        raise ThirdPartyLockError(f"{lock.id}: acquired revision does not match lock")
    license_path = checkout / lock.license.file
    try:
        license_path.relative_to(checkout)
    except ValueError as exc:
        raise ThirdPartyLockError(f"{lock.id}: license path escapes checkout") from exc
    if license_path.is_symlink() or not license_path.is_file():
        raise ThirdPartyLockError(f"{lock.id}: locked license file is missing or unsafe")
    if hashlib.sha256(license_path.read_bytes()).hexdigest() != lock.license.hash:
        raise ThirdPartyLockError(f"{lock.id}: license hash does not match lock")
    skill = checkout / lock.subdirectory
    try:
        skill.relative_to(checkout)
    except ValueError as exc:
        raise ThirdPartyLockError(f"{lock.id}: skill path escapes checkout") from exc
    if tree_hash(skill) != lock.content_hash:
        raise ThirdPartyLockError(f"{lock.id}: content hash does not match lock")
    if not (skill / "SKILL.md").is_file() or (skill / "SKILL.md").is_symlink():
        raise ThirdPartyLockError(f"{lock.id}: verified skill lacks a safe SKILL.md")
    return skill


def _git(
    args: Sequence[str],
    *,
    cwd: Path,
    run: Run,
    timeout: int = GIT_TIMEOUT_SECONDS,
) -> str:
    try:
        proc = run(
            list(args),
            cwd=str(cwd),
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        subcommand = args[1] if len(args) > 1 else "command"
        raise ThirdPartyLockError(f"git {subcommand} timed out after {timeout}s") from exc
    if proc.returncode != 0:
        raise ThirdPartyLockError("third-party acquisition command failed")
    return proc.stdout.strip()


def _cache_root(cache: Path | None) -> Path:
    if cache is not None:
        return cache.expanduser().absolute()
    from dotf_core.modules_state import xdg_state_home

    return xdg_state_home() / "dotf" / CACHE_DIRNAME


def _cache_entry(root: Path, source: str, revision: str) -> Path:
    key = hashlib.sha256(f"{source}\0{revision}".encode("utf-8")).hexdigest()
    return root / key


def _at_revision(checkout: Path, revision: str, *, run: Run) -> bool:
    try:
        return _git(["git", "rev-parse", "HEAD"], cwd=checkout, run=run) == revision
    except ThirdPartyLockError:
        return False


def _grouped(skills: Sequence[LockedSkill]) -> list[tuple[str, str, list[LockedSkill]]]:
    """Group lock entries by source and revision, keeping lock order."""
    groups: dict[tuple[str, str], list[LockedSkill]] = {}
    for item in skills:
        groups.setdefault((item.source, item.revision), []).append(item)
    return [(source, revision, items) for (source, revision), items in groups.items()]


def _pattern(path: str) -> str:
    """Render one sparse-checkout pattern for an exact repository path."""
    escaped = "".join("\\" + char if char in "*?[]!\\#" else char for char in path)
    return f"/{escaped}"


def _patterns(items: Sequence[LockedSkill]) -> list[str]:
    wanted = {_pattern(item.license.file) for item in items}
    wanted.update(_pattern(item.subdirectory + "/") for item in items)
    return sorted(wanted)


def _select(checkout: Path, items: Sequence[LockedSkill], *, run: Run) -> None:
    """Restrict the working tree to the locked license files and skill directories."""
    _git(["git", "sparse-checkout", "set", "--no-cone", *_patterns(items)], cwd=checkout, run=run)


def _checkout(checkout: Path, revision: str, *, run: Run) -> None:
    _git(["git", "checkout", "--quiet", "--detach", revision], cwd=checkout, run=run)
    if not _at_revision(checkout, revision, run=run):
        raise ThirdPartyLockError("checkout does not sit at the locked revision")


def _fetch_checkout(
    source: str,
    revision: str,
    items: Sequence[LockedSkill],
    destination: Path,
    *,
    run: Run,
) -> None:
    """Materialize one repository revision, fetching only the locked paths' blobs."""
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    _git(["git", "init", "--quiet"], cwd=destination, run=run)
    _git(["git", "remote", "add", "origin", source], cwd=destination, run=run)
    _git(["git", "sparse-checkout", "init", "--no-cone"], cwd=destination, run=run)
    _select(destination, items, run=run)
    _git(
        ["git", "fetch", "--quiet", "--filter=blob:none", "--depth=1", "origin", revision],
        cwd=destination,
        run=run,
    )
    _checkout(destination, revision, run=run)


def _obtain_checkout(
    source: str,
    revision: str,
    items: Sequence[LockedSkill],
    root: Path,
    *,
    run: Run,
) -> Path:
    """Return a checkout of the locked revision, reusing a cached one without network."""
    entry = _cache_entry(root, source, revision)
    if entry.is_dir() and not entry.is_symlink() and _at_revision(entry, revision, run=run):
        _select(entry, items, run=run)
        _checkout(entry, revision, run=run)
        return entry
    if root.is_symlink():
        raise ThirdPartyLockError("checkout cache directory is a symlink")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if entry.is_symlink():
        raise ThirdPartyLockError("checkout cache entry is a symlink")
    if entry.exists():
        shutil.rmtree(entry, ignore_errors=True)
    temporary = Path(tempfile.mkdtemp(prefix=".fetch-", dir=root))
    try:
        _fetch_checkout(source, revision, items, temporary / "checkout", run=run)
        try:
            os.replace(temporary / "checkout", entry)
        except OSError as exc:
            if not (entry.is_dir() and _at_revision(entry, revision, run=run)):
                raise ThirdPartyLockError(f"{source}: cannot publish a checkout") from exc
            _select(entry, items, run=run)
            _checkout(entry, revision, run=run)
    finally:
        shutil.rmtree(temporary, ignore_errors=True)
    return entry


def acquire_all(
    lock: ThirdPartyLock,
    destination: Path,
    *,
    run: Run = subprocess.run,
    cache: Path | None = None,
) -> Path:
    """Acquire every lock entry into private staging and verify all before returning.

    Entries sharing a source and revision share one checkout, that checkout holds
    only the locked paths, and a cached one costs no network at all.
    """
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    skills_root = destination / "skills"
    skills_root.mkdir(mode=0o700)
    cache_root = _cache_root(cache)
    for source, revision, items in _grouped(lock.skills):
        checkout = _obtain_checkout(source, revision, items, cache_root, run=run)
        for item in items:
            verified = verify_checkout(item, checkout, revision)
            target = skills_root / item.id
            shutil.copytree(verified, target, symlinks=False)
            if tree_hash(target) != item.content_hash:
                raise ThirdPartyLockError(f"{item.id}: staged copy changed after verification")
    return skills_root
