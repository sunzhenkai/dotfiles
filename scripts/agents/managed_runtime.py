"""Ownership-aware first-party Agent runtime planning and apply.

Planning reads source, manifest, and targets only. Apply serializes through a
nofollow lock, re-plans under that lock, then changes only targets whose current
bytes still match the ownership decision.
"""

from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
import stat
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable, Literal

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from dotf_core.atomic import atomic_write  # noqa: E402
from dotf_core.backup import generate_run_id  # noqa: E402
from dotf_core.paths import (  # noqa: E402
    PathBoundaryError,
    assert_no_symlinks,
    assert_path_confined,
    ensure_directory,
    open_directory_nofollow,
    open_nofollow,
    open_parent_nofollow,
)
from dotf_core.schemas import (  # noqa: E402
    MANIFEST_SCHEMA_VERSION,
    ManagedItem,
    ManagedManifest,
    SchemaError,
    validate_managed_manifest,
)
from ensure_pyyaml import ensure_yaml  # noqa: E402

yaml = ensure_yaml()

AGENTS_MANIFEST_NAME = "agents-manifest.json"
AGENTS_LOCK_NAME = "agents-manifest.lock"
RUNTIME_SCHEMA_VERSION = 1
OWNER_PREFIX = "agents:skill:"
_REQUIRED_EXCLUSIONS = frozenset({"patches", "evals", "experience", "evolutions", "authoring"})
RenderSkill = Callable[[Path, str], bytes]


class AgentRuntimeError(RuntimeError):
    """The first-party runtime plan cannot be safely applied."""


class AgentRuntimeConflict(AgentRuntimeError):
    """At least one runtime target must be preserved for user resolution."""


class _DuplicateJSONMember(ValueError):
    """A JSON object repeated a member name and is therefore ambiguous."""


@dataclass(frozen=True, slots=True)
class RuntimePolicy:
    version: int
    files: tuple[str, ...]
    sidecars: tuple[str, ...]
    excluded: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RuntimeFile:
    owner: str
    target: str
    source_identity: str
    expected_hash: str
    content: bytes
    mode: int


@dataclass(frozen=True, slots=True)
class RuntimeOperation:
    state: Literal["unchanged", "create", "update", "prune", "permission", "conflict"]
    action: Literal["none", "create", "update", "prune", "chmod", "block"]
    target: str
    source_identity: str
    expected_hash: str | None
    current_hash: str | None
    installed_hash: str | None
    conflict: str | None
    expected: RuntimeFile | None
    prior: ManagedItem | None
    actual_state: Literal["missing", "present", "unsafe"]


@dataclass(frozen=True, slots=True)
class SkillsPlan:
    schema_version: int
    repo_root: str
    home: str
    state_home: str
    target_root: str
    source_root: str
    owner_prefix: str
    identity_prefix: str
    manifest_status: Literal["missing", "ok", "malformed"]
    manifest_digest: str | None
    prior_manifest: ManagedManifest
    operations: tuple[RuntimeOperation, ...]

    @property
    def conflicts(self) -> tuple[RuntimeOperation, ...]:
        return tuple(item for item in self.operations if item.state == "conflict")

    @property
    def status(self) -> Literal["conflict", "changed", "unchanged"]:
        if self.conflicts:
            return "conflict"
        if any(item.action != "none" for item in self.operations):
            return "changed"
        return "unchanged"


@dataclass(frozen=True, slots=True)
class SkillsApplyResult:
    status: Literal["changed", "unchanged"]
    changed: int
    unchanged: int
    pruned: int
    manifest: Path


@dataclass(frozen=True, slots=True)
class _ManifestSnapshot:
    status: Literal["missing", "ok", "malformed"]
    manifest: ManagedManifest
    digest: str | None
    mode: int | None


@dataclass(frozen=True, slots=True)
class _Actual:
    state: Literal["missing", "present", "unsafe"]
    digest: str | None
    detail: str | None = None
    mode: int | None = None


class _UniqueLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise AgentRuntimeError(f"runtime allowlist contains duplicate key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


def _strict_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJSONMember(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _empty_manifest() -> ManagedManifest:
    return ManagedManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        kind="managed-manifest",
        generated_at="1970-01-01T00:00:00Z",
        items=(),
    )


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _read_fd(fd: int) -> bytes:
    chunks: list[bytes] = []
    while True:
        block = os.read(fd, 1024 * 1024)
        if not block:
            return b"".join(chunks)
        chunks.append(block)


def _state_home(home: Path, state_home: Path | None) -> Path:
    if state_home is not None:
        return state_home.expanduser().absolute()
    configured = os.environ.get("XDG_STATE_HOME")
    return Path(configured).expanduser().absolute() if configured else home / ".local" / "state"


def manifest_path(home: Path | None = None, state_home: Path | None = None) -> Path:
    base_home = (home or Path.home()).expanduser().absolute()
    return _state_home(base_home, state_home) / "dotf" / AGENTS_MANIFEST_NAME


def lock_path(home: Path | None = None, state_home: Path | None = None) -> Path:
    return manifest_path(home, state_home).with_name(AGENTS_LOCK_NAME)


def _boundary(home: Path, path: Path) -> Path:
    try:
        path.relative_to(home)
    except ValueError:
        return Path("/")
    return home


def _validate_name(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise AgentRuntimeError(f"{label} must be a non-empty path name")
    path = PurePosixPath(value)
    if path.is_absolute() or len(path.parts) != 1 or value in {".", ".."}:
        raise AgentRuntimeError(f"{label} must be one safe path component")
    return value


def _string_list(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise AgentRuntimeError(f"{label} must be an array")
    result = tuple(_validate_name(item, f"{label} item") for item in value)
    if len(result) != len(set(result)):
        raise AgentRuntimeError(f"{label} contains duplicates")
    return result


def load_runtime_policy(root: Path) -> RuntimePolicy:
    path = root / "agents" / "runtime.yaml"
    try:
        raw = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueLoader)
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise AgentRuntimeError(f"cannot load runtime allowlist: {path}") from exc
    if not isinstance(raw, dict) or set(raw) != {"version", "skills"}:
        raise AgentRuntimeError("runtime allowlist requires exactly version and skills")
    version = raw["version"]
    if isinstance(version, bool) or version != RUNTIME_SCHEMA_VERSION:
        raise AgentRuntimeError("runtime allowlist version is unsupported")
    skills = raw["skills"]
    if not isinstance(skills, dict) or set(skills) != {"files", "sidecars", "excluded"}:
        raise AgentRuntimeError("runtime skills requires exactly files, sidecars, and excluded")
    files = _string_list(skills["files"], "runtime skills.files")
    sidecars = _string_list(skills["sidecars"], "runtime skills.sidecars")
    excluded = _string_list(skills["excluded"], "runtime skills.excluded")
    if "SKILL.md" not in files:
        raise AgentRuntimeError("runtime skills.files must declare SKILL.md")
    if set(files) & set(sidecars) or set(files + sidecars) & set(excluded):
        raise AgentRuntimeError("runtime allowlist include/exclude entries overlap")
    if not _REQUIRED_EXCLUSIONS.issubset(excluded):
        raise AgentRuntimeError("runtime allowlist must exclude authoring directories")
    return RuntimePolicy(version, files, sidecars, excluded)


def _source_files(directory: Path) -> list[Path]:
    result: list[Path] = []

    def visit(current: Path) -> None:
        with os.scandir(current) as entries:
            for entry in sorted(entries, key=lambda item: item.name):
                path = current / entry.name
                if entry.is_symlink():
                    raise AgentRuntimeError(f"runtime source contains symlink: {path}")
                if entry.is_dir(follow_symlinks=False):
                    if entry.name == "__pycache__":
                        continue
                    visit(path)
                elif entry.is_file(follow_symlinks=False):
                    if path.suffix not in {".pyc", ".pyo"}:
                        result.append(path)
                else:
                    raise AgentRuntimeError(f"runtime source contains unsupported entry: {path}")

    visit(directory)
    return result


def collect_runtime_files(
    root: Path,
    home: Path,
    target_root: Path,
    render_skill: RenderSkill,
    *,
    source_root: Path | None = None,
    owner_prefix: str = OWNER_PREFIX,
    identity_prefix: str = "agents/skills",
) -> tuple[RuntimeFile, ...]:
    policy = load_runtime_policy(root)
    source_root = source_root or root / "agents" / "skills"
    if not source_root.is_dir():
        raise AgentRuntimeError(f"missing first-party skills source: {source_root}")
    target_base = assert_path_confined(home, target_root)
    result: list[RuntimeFile] = []
    targets: set[str] = set()
    for skill_dir in sorted(source_root.iterdir()):
        if not skill_dir.is_dir() or skill_dir.is_symlink():
            continue
        skill_id = skill_dir.name
        marker = skill_dir / "SKILL.md"
        if not marker.is_file() or marker.is_symlink():
            continue
        owner = owner_prefix + skill_id
        for filename in policy.files:
            source = skill_dir / filename
            if not source.is_file() or source.is_symlink():
                if filename == "SKILL.md":
                    raise AgentRuntimeError(f"runtime file is missing or unsafe: {source}")
                continue
            content = render_skill(skill_dir, skill_id) if filename == "SKILL.md" else source.read_bytes()
            relative = PurePosixPath(skill_id) / filename
            target = assert_path_confined(home, target_base / Path(relative))
            try:
                target.relative_to(target_base)
            except ValueError as exc:
                raise AgentRuntimeError(f"runtime target escapes skills root: {target}") from exc
            identity = (Path(identity_prefix) / Path(relative)).as_posix()
            mode = 0o755 if source.stat().st_mode & 0o111 else 0o644
            item = RuntimeFile(owner, str(target), identity, _sha256(content), content, mode)
            if item.target in targets:
                raise AgentRuntimeError(f"runtime allowlist produced duplicate target: {item.target}")
            targets.add(item.target)
            result.append(item)
        for sidecar in policy.sidecars:
            source_dir = skill_dir / sidecar
            if not source_dir.exists():
                continue
            if source_dir.is_symlink() or not source_dir.is_dir():
                raise AgentRuntimeError(f"runtime sidecar is not a real directory: {source_dir}")
            for source in _source_files(source_dir):
                nested = source.relative_to(source_dir)
                relative = PurePosixPath(skill_id) / sidecar / PurePosixPath(nested.as_posix())
                target = assert_path_confined(home, target_base / Path(relative))
                try:
                    target.relative_to(target_base)
                except ValueError as exc:
                    raise AgentRuntimeError(f"runtime target escapes skills root: {target}") from exc
                identity = (Path(identity_prefix) / Path(relative)).as_posix()
                content = source.read_bytes()
                mode = 0o755 if source.stat().st_mode & 0o111 else 0o644
                item = RuntimeFile(owner, str(target), identity, _sha256(content), content, mode)
                if item.target in targets:
                    raise AgentRuntimeError(f"runtime allowlist produced duplicate target: {item.target}")
                targets.add(item.target)
                result.append(item)
    return tuple(sorted(result, key=lambda item: item.target))


def _read_manifest(home: Path, state_home: Path) -> _ManifestSnapshot:
    path = manifest_path(home, state_home)
    boundary = _boundary(home, path)
    try:
        assert_no_symlinks(boundary, path)
        fd = open_nofollow(boundary, path)
    except FileNotFoundError:
        return _ManifestSnapshot("missing", _empty_manifest(), None, None)
    except (OSError, PathBoundaryError):
        return _ManifestSnapshot("malformed", _empty_manifest(), None, None)
    try:
        item = os.fstat(fd)
        mode = stat.S_IMODE(item.st_mode)
        if not stat.S_ISREG(item.st_mode):
            return _ManifestSnapshot("malformed", _empty_manifest(), None, mode)
        raw = _read_fd(fd)
    finally:
        os.close(fd)
    try:
        value = json.loads(raw, object_pairs_hook=_strict_json_object)
        manifest = validate_managed_manifest(value)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        _DuplicateJSONMember,
        SchemaError,
        TypeError,
    ):
        return _ManifestSnapshot("malformed", _empty_manifest(), _sha256(raw), mode)
    return _ManifestSnapshot("ok", manifest, _sha256(raw), mode)


def _read_actual(home: Path, target: Path) -> _Actual:
    try:
        assert_no_symlinks(home, target)
        fd = open_nofollow(home, target)
    except FileNotFoundError:
        return _Actual("missing", None)
    except (OSError, PathBoundaryError) as exc:
        return _Actual("unsafe", None, str(exc))
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            return _Actual("unsafe", None, "target is not a regular file")
        content = _read_fd(fd)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_mode) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_mode,
        ):
            return _Actual("unsafe", None, "target changed while reading")
        return _Actual("present", _sha256(content), mode=stat.S_IMODE(after.st_mode))
    finally:
        os.close(fd)


def _conflict(
    target: str,
    source_identity: str,
    expected_hash: str | None,
    actual: _Actual,
    installed_hash: str | None,
    reason: str,
    expected: RuntimeFile | None,
    prior: ManagedItem | None,
) -> RuntimeOperation:
    return RuntimeOperation(
        "conflict", "block", target, source_identity, expected_hash,
        actual.digest, installed_hash, reason, expected, prior, actual.state,
    )


def compile_skills_plan(
    root: Path,
    render_skill: RenderSkill,
    *,
    home: Path | None = None,
    state_home: Path | None = None,
    target_root: Path | None = None,
    source_root: Path | None = None,
    owner_prefix: str = OWNER_PREFIX,
    identity_prefix: str = "agents/skills",
) -> SkillsPlan:
    """Compile expected first-party runtime and ownership decisions without writes."""
    repo = root.expanduser().absolute()
    base_home = (home or Path.home()).expanduser().absolute()
    state = _state_home(base_home, state_home)
    base_target = (target_root or base_home / ".agents" / "skills").expanduser().absolute()
    base_target = assert_path_confined(base_home, base_target)
    resolved_source_root = (source_root or repo / "agents" / "skills").expanduser().absolute()
    expected = collect_runtime_files(
        repo, base_home, base_target, render_skill,
        source_root=resolved_source_root,
        owner_prefix=owner_prefix,
        identity_prefix=identity_prefix,
    )
    snapshot = _read_manifest(base_home, state)
    prior_by_target = {
        item.target: item
        for item in snapshot.manifest.items
        if item.owner.startswith(owner_prefix)
    }
    operations: list[RuntimeOperation] = []
    expected_targets = {item.target for item in expected}

    if snapshot.status == "malformed":
        for item in expected:
            actual = _read_actual(base_home, Path(item.target))
            operations.append(_conflict(
                item.target, item.source_identity, item.expected_hash, actual, None,
                "agents manifest is malformed or incompatible", item, None,
            ))
    else:
        for item in expected:
            actual = _read_actual(base_home, Path(item.target))
            prior = prior_by_target.get(item.target)
            if prior is None:
                if actual.state == "missing":
                    operations.append(RuntimeOperation(
                        "create", "create", item.target, item.source_identity,
                        item.expected_hash, None, None, None, item, None, "missing",
                    ))
                else:
                    operations.append(_conflict(
                        item.target, item.source_identity, item.expected_hash, actual, None,
                        "target exists without agents ownership", item, None,
                    ))
                continue
            if prior.owner != item.owner or prior.source_identity != item.source_identity:
                operations.append(_conflict(
                    item.target, item.source_identity, item.expected_hash, actual,
                    prior.installed_hash, "manifest ownership identity differs", item, prior,
                ))
            elif actual.state == "unsafe":
                operations.append(_conflict(
                    item.target, item.source_identity, item.expected_hash, actual,
                    prior.installed_hash, "target path contains a symlink or unsafe type", item, prior,
                ))
            elif actual.state == "missing":
                operations.append(RuntimeOperation(
                    "create", "create", item.target, item.source_identity,
                    item.expected_hash, None, prior.installed_hash, None, item, prior, "missing",
                ))
            elif actual.digest != prior.installed_hash:
                operations.append(_conflict(
                    item.target, item.source_identity, item.expected_hash, actual,
                    prior.installed_hash, "owned target was modified locally", item, prior,
                ))
            elif actual.mode != prior.mode:
                operations.append(_conflict(
                    item.target, item.source_identity, item.expected_hash, actual,
                    prior.installed_hash, "owned target mode was modified locally", item, prior,
                ))
            elif actual.digest == item.expected_hash and actual.mode == item.mode:
                operations.append(RuntimeOperation(
                    "unchanged", "none", item.target, item.source_identity,
                    item.expected_hash, actual.digest, prior.installed_hash, None,
                    item, prior, "present",
                ))
            elif actual.digest == item.expected_hash:
                operations.append(RuntimeOperation(
                    "permission", "chmod", item.target, item.source_identity,
                    item.expected_hash, actual.digest, prior.installed_hash, None,
                    item, prior, "present",
                ))
            else:
                operations.append(RuntimeOperation(
                    "update", "update", item.target, item.source_identity,
                    item.expected_hash, actual.digest, prior.installed_hash, None,
                    item, prior, "present",
                ))

        for prior in sorted(prior_by_target.values(), key=lambda value: value.target):
            if prior.target in expected_targets:
                continue
            target = Path(prior.target)
            try:
                normalized = assert_path_confined(base_home, target)
                normalized.relative_to(base_target)
            except (OSError, PathBoundaryError, ValueError):
                actual = _Actual("unsafe", None)
                operations.append(_conflict(
                    prior.target, prior.source_identity, None, actual, prior.installed_hash,
                    "stale manifest target is outside the skills root", None, prior,
                ))
                continue
            actual = _read_actual(base_home, normalized)
            if actual.state == "unsafe":
                operations.append(_conflict(
                    prior.target, prior.source_identity, None, actual, prior.installed_hash,
                    "stale target path contains a symlink or unsafe type", None, prior,
                ))
            elif actual.state == "present" and actual.digest != prior.installed_hash:
                operations.append(_conflict(
                    prior.target, prior.source_identity, None, actual, prior.installed_hash,
                    "stale owned target was modified locally", None, prior,
                ))
            else:
                operations.append(RuntimeOperation(
                    "prune", "prune", prior.target, prior.source_identity, None,
                    actual.digest, prior.installed_hash, None, None, prior, actual.state,
                ))

    return SkillsPlan(
        MANIFEST_SCHEMA_VERSION,
        str(repo),
        str(base_home),
        str(state),
        str(base_target),
        str(resolved_source_root),
        owner_prefix,
        identity_prefix,
        snapshot.status,
        snapshot.digest,
        snapshot.manifest,
        tuple(sorted(operations, key=lambda item: (item.target, item.action))),
    )


def _ensure_state(home: Path, state_home: Path) -> Path:
    directory = manifest_path(home, state_home).parent
    boundary = _boundary(home, directory)
    ensure_directory(boundary, state_home, mode=0o700)
    ensure_directory(boundary, directory, mode=0o700)
    fd = open_directory_nofollow(boundary, directory)
    try:
        os.fchmod(fd, 0o700)
    finally:
        os.close(fd)
    return directory


class AgentManifestLock:
    """Cross-process exclusive lock with nofollow creation and strict mode."""

    def __init__(self, home: Path, state_home: Path) -> None:
        self.home = home
        self.state_home = state_home
        self.fd: int | None = None

    def __enter__(self) -> "AgentManifestLock":
        _ensure_state(self.home, self.state_home)
        path = lock_path(self.home, self.state_home)
        self.fd = open_nofollow(
            _boundary(self.home, path), path, os.O_RDWR | os.O_CREAT, 0o600,
        )
        if stat.S_IMODE(os.fstat(self.fd).st_mode) != 0o600:
            os.fchmod(self.fd, 0o600)
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.fd is not None:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
            self.fd = None


def _expected_signature(plan: SkillsPlan) -> tuple[tuple[str, str, str, int], ...]:
    return tuple(sorted(
        (op.target, op.source_identity, op.expected_hash or "", op.expected.mode)
        for op in plan.operations
        if op.expected is not None
    ))


def _actual_matches(operation: RuntimeOperation, actual: _Actual) -> bool:
    expected_mode = operation.expected.mode if operation.action == "chmod" and operation.prior is None else (
        operation.prior.mode if operation.prior is not None else None
    )
    return (
        actual.state == operation.actual_state
        and actual.digest == operation.current_hash
        and (actual.state != "present" or actual.mode == expected_mode)
    )


def _chmod_owned(
    home: Path,
    target: Path,
    installed_hash: str,
    current_mode: int,
    desired_mode: int,
) -> None:
    parent_fd, name = open_parent_nofollow(home, target)
    fd: int | None = None
    try:
        item = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if stat.S_ISLNK(item.st_mode) or not stat.S_ISREG(item.st_mode):
            raise AgentRuntimeConflict(f"unsafe owned target: {target}")
        fd = os.open(
            name,
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino) != (item.st_dev, item.st_ino):
            raise AgentRuntimeConflict(f"owned target changed while opening: {target}")
        if stat.S_IMODE(opened.st_mode) != current_mode:
            raise AgentRuntimeConflict(f"owned target mode changed after planning: {target}")
        if _sha256(_read_fd(fd)) != installed_hash:
            raise AgentRuntimeConflict(f"owned target changed after planning: {target}")
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (current.st_dev, current.st_ino, current.st_mode) != (
            item.st_dev,
            item.st_ino,
            item.st_mode,
        ):
            raise AgentRuntimeConflict(f"owned target changed while reading: {target}")
        os.fchmod(fd, desired_mode)
        os.fsync(fd)
        final = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (final.st_dev, final.st_ino) != (item.st_dev, item.st_ino):
            raise AgentRuntimeConflict(f"owned target changed during chmod: {target}")
        if stat.S_IMODE(final.st_mode) != desired_mode:
            raise AgentRuntimeConflict(f"owned target mode remediation failed: {target}")
    except FileNotFoundError as exc:
        raise AgentRuntimeConflict(f"owned target disappeared: {target}") from exc
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise AgentRuntimeConflict(f"unsafe owned target: {target}") from exc
        raise
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent_fd)


def _unlink_owned(home: Path, target: Path, installed_hash: str) -> None:
    parent_fd, name = open_parent_nofollow(home, target)
    fd: int | None = None
    try:
        item = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if stat.S_ISLNK(item.st_mode) or not stat.S_ISREG(item.st_mode):
            raise AgentRuntimeConflict(f"unsafe stale target: {target}")
        fd = os.open(
            name,
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino) != (item.st_dev, item.st_ino):
            raise AgentRuntimeConflict(f"stale target changed while opening: {target}")
        content = _read_fd(fd)
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (item.st_dev, item.st_ino):
            raise AgentRuntimeConflict(f"stale target changed while reading: {target}")
        if _sha256(content) != installed_hash:
            raise AgentRuntimeConflict(f"stale target was modified locally: {target}")
        os.unlink(name, dir_fd=parent_fd)
        os.fsync(parent_fd)
    except FileNotFoundError:
        return
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise AgentRuntimeConflict(f"unsafe stale target: {target}") from exc
        raise
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent_fd)


def _remove_empty_parents(home: Path, target_root: Path, start: Path) -> None:
    current = start
    while current != target_root and current != home:
        try:
            parent_fd, name = open_parent_nofollow(home, current)
        except (FileNotFoundError, OSError):
            return
        try:
            item = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if not stat.S_ISDIR(item.st_mode) or stat.S_ISLNK(item.st_mode):
                return
            os.rmdir(name, dir_fd=parent_fd)
            os.fsync(parent_fd)
        except (FileNotFoundError, OSError) as exc:
            if isinstance(exc, OSError) and exc.errno not in (errno.ENOENT, errno.ENOTEMPTY, errno.EEXIST):
                raise
            return
        finally:
            os.close(parent_fd)
        current = current.parent


def _serialize(manifest: ManagedManifest) -> bytes:
    manifest.validate()
    return (json.dumps(manifest.to_dict(), ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _write_manifest(home: Path, state_home: Path, manifest: ManagedManifest) -> Path:
    path = manifest_path(home, state_home)
    atomic_write(
        path,
        _serialize(manifest),
        root=_boundary(home, path),
        format="json",
        mode=0o600,
        sensitive=True,
    )
    return path


def _repair_manifest_mode(
    home: Path,
    state_home: Path,
    snapshot: _ManifestSnapshot,
) -> _ManifestSnapshot:
    if snapshot.status != "ok" or snapshot.mode == 0o600:
        return snapshot
    if snapshot.digest is None or snapshot.mode is None:
        raise AgentRuntimeConflict("agents manifest mode cannot be safely repaired")
    path = manifest_path(home, state_home)
    try:
        fd = open_nofollow(_boundary(home, path), path)
    except (OSError, PathBoundaryError) as exc:
        raise AgentRuntimeConflict("agents manifest became unsafe during mode repair") from exc
    try:
        item = os.fstat(fd)
        if not stat.S_ISREG(item.st_mode) or _sha256(_read_fd(fd)) != snapshot.digest:
            raise AgentRuntimeConflict("agents manifest changed during mode repair")
        os.fchmod(fd, 0o600)
        os.fsync(fd)
    finally:
        os.close(fd)
    verified = _read_manifest(home, state_home)
    if (
        verified.status != "ok"
        or verified.digest != snapshot.digest
        or verified.mode != 0o600
    ):
        raise AgentRuntimeConflict("agents manifest mode remediation could not be verified")
    return verified


def _managed_item(expected: RuntimeFile, run_id: str) -> ManagedItem:
    return ManagedItem(
        owner=expected.owner,
        target=expected.target,
        source_identity=expected.source_identity,
        expected_hash=expected.expected_hash,
        installed_hash=expected.expected_hash,
        strategy="copy",
        mode=expected.mode,
        run_id=run_id,
        sensitive=False,
    )


def apply_skills_plan(
    plan: SkillsPlan,
    render_skill: RenderSkill,
    *,
    run_id: str | None = None,
) -> SkillsApplyResult:
    """Apply a skills plan under the Agent manifest lock.

    A concurrent equivalent run is allowed to turn create/update into unchanged;
    source expectations must remain byte-identical to the caller's plan.
    """
    if not isinstance(plan, SkillsPlan) or plan.schema_version != MANIFEST_SCHEMA_VERSION:
        raise AgentRuntimeError("unsupported skills plan")
    home = Path(plan.home)
    state_home = Path(plan.state_home)
    target_root = Path(plan.target_root)
    run = run_id or generate_run_id()
    changed = 0
    unchanged = 0
    pruned = 0
    manifest_file = manifest_path(home, state_home)

    with AgentManifestLock(home, state_home):
        current = compile_skills_plan(
            Path(plan.repo_root), render_skill, home=home,
            state_home=state_home, target_root=target_root,
            source_root=Path(plan.source_root), owner_prefix=plan.owner_prefix,
            identity_prefix=plan.identity_prefix,
        )
        if _expected_signature(current) != _expected_signature(plan):
            raise AgentRuntimeConflict("runtime source changed after planning")
        if current.manifest_status == "malformed":
            raise AgentRuntimeConflict("agents manifest is malformed or incompatible")
        snapshot = _read_manifest(home, state_home)
        if (
            snapshot.status != current.manifest_status
            or snapshot.digest != current.manifest_digest
        ):
            raise AgentRuntimeConflict("agents manifest changed after planning")
        manifest_mode_changed = snapshot.status == "ok" and snapshot.mode != 0o600
        snapshot = _repair_manifest_mode(home, state_home, snapshot)
        if manifest_mode_changed:
            changed += 1
        if current.conflicts:
            details = "; ".join(f"{item.target}: {item.conflict}" for item in current.conflicts)
            raise AgentRuntimeConflict(details)

        retained = [
            item for item in snapshot.manifest.items
            if not item.owner.startswith(plan.owner_prefix)
        ]
        expected_items: list[ManagedItem] = []
        backup_root = state_home / "dotf" / "backups"
        pruned_parents: list[Path] = []

        for operation in current.operations:
            actual = _read_actual(home, Path(operation.target))
            if not _actual_matches(operation, actual):
                raise AgentRuntimeConflict(f"runtime target changed after planning: {operation.target}")
            if operation.action == "none":
                assert operation.prior is not None
                expected_items.append(operation.prior)
                unchanged += 1
                continue
            if operation.action in {"create", "update"}:
                assert operation.expected is not None
                result = atomic_write(
                    operation.target,
                    operation.expected.content,
                    root=home,
                    format="text" if operation.target.endswith((".md", ".py", ".sh")) else "binary",
                    mode=operation.expected.mode,
                    backup_root=backup_root if operation.action == "update" else None,
                    run_id=run if operation.action == "update" else None,
                    sensitive=False,
                )
                del result
                expected_items.append(_managed_item(operation.expected, run))
                changed += 1
                continue
            if operation.action == "chmod":
                assert operation.expected is not None
                assert operation.prior is not None
                assert actual.mode is not None
                _chmod_owned(
                    home,
                    Path(operation.target),
                    operation.prior.installed_hash,
                    actual.mode,
                    operation.expected.mode,
                )
                if (
                    operation.prior.expected_hash == operation.expected.expected_hash
                    and operation.prior.mode == operation.expected.mode
                ):
                    expected_items.append(operation.prior)
                else:
                    expected_items.append(_managed_item(operation.expected, run))
                changed += 1
                continue
            if operation.action == "prune":
                assert operation.prior is not None
                if actual.state == "present":
                    _unlink_owned(home, Path(operation.target), operation.prior.installed_hash)
                    pruned_parents.append(Path(operation.target).parent)
                pruned += 1
                changed += 1

        for parent in sorted(set(pruned_parents), key=lambda value: len(value.parts), reverse=True):
            _remove_empty_parents(home, target_root, parent)

        new_manifest = ManagedManifest(
            schema_version=MANIFEST_SCHEMA_VERSION,
            kind="managed-manifest",
            generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            items=tuple(sorted(retained + expected_items, key=lambda item: item.target)),
        )
        if new_manifest.items != snapshot.manifest.items:
            manifest_file = _write_manifest(home, state_home, new_manifest)

    return SkillsApplyResult(
        "changed" if changed else "unchanged",
        changed,
        unchanged,
        pruned,
        manifest_file,
    )
