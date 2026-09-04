#!/usr/bin/env python3
"""Strict audited third-party skill lock, staged acquisition, and verification."""

from __future__ import annotations

import hashlib
import re
import shutil
import stat
import subprocess
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


def _git(args: Sequence[str], *, cwd: Path, run: Run) -> str:
    proc = run(list(args), cwd=str(cwd), text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise ThirdPartyLockError("third-party acquisition command failed")
    return proc.stdout.strip()


def acquire_all(lock: ThirdPartyLock, destination: Path, *, run: Run = subprocess.run) -> Path:
    """Acquire every lock entry into private staging and verify all before returning."""
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    skills_root = destination / "skills"
    skills_root.mkdir(mode=0o700)
    checkouts = destination / "checkouts"
    checkouts.mkdir(mode=0o700)
    for item in lock.skills:
        checkout = checkouts / item.id
        checkout.mkdir(mode=0o700)
        _git(["git", "init", "--quiet"], cwd=checkout, run=run)
        _git(["git", "remote", "add", "origin", item.source], cwd=checkout, run=run)
        _git(["git", "fetch", "--quiet", "--depth=1", "origin", item.revision], cwd=checkout, run=run)
        _git(["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"], cwd=checkout, run=run)
        revision = _git(["git", "rev-parse", "HEAD"], cwd=checkout, run=run)
        verified = verify_checkout(item, checkout, revision)
        shutil.copytree(verified, skills_root / item.id, symlinks=False)
        if tree_hash(skills_root / item.id) != item.content_hash:
            raise ThirdPartyLockError(f"{item.id}: staged copy changed after verification")
    return skills_root
