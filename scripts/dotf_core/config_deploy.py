"""Registry-driven, side-effect-free config planning and safety-owned apply.

Specialized merge/render producers are pure callbacks: they receive immutable
source/actual bytes and return expected bytes or structured data.  They never
receive an apply capability; every resulting file still passes through this
module's confinement, validation, backup, atomic-write, and manifest path.
"""

from __future__ import annotations

import argparse
import errno
import fcntl
import hashlib
import json
import os
import stat
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Literal

from .atomic import Format, atomic_write, validate_content
from .backup import backup_target, generate_run_id
from .paths import (
    PathBoundaryError,
    assert_no_symlinks,
    assert_path_confined,
    ensure_directory,
    open_directory_nofollow,
    open_nofollow,
    open_parent_nofollow,
)
from .schemas import (
    MANIFEST_SCHEMA_VERSION,
    PLAN_SCHEMA_VERSION,
    ManagedItem,
    ManagedManifest,
    PlanItem,
    SchemaError,
    validate_managed_manifest,
)

CONFIG_MANIFEST_NAME = "config-manifest.json"
CONFIG_LOCK_NAME = "config-manifest.lock"
_OWNER_PREFIX = "config:"


class ConfigDeployError(RuntimeError):
    """A config plan cannot be safely produced or applied."""


class ConfigConflictError(ConfigDeployError):
    """The plan contains a target that is not safe to modify by default."""


class MalformedConfigManifest(SchemaError):
    """The on-disk config ownership manifest is malformed or incompatible."""


class UnsafeConfigHandlerError(ConfigDeployError):
    """A supposedly pure producer mutated source, target, or state."""


@dataclass(frozen=True, slots=True)
class ProducedContent:
    """One specialized producer result; mode may only narrow registry policy."""

    content: bytes | str | Mapping[str, Any] | Sequence[Any]
    format: Format = None
    mode: int | None = None
    reconcile_owned: bool = False


@dataclass(frozen=True, slots=True)
class ProducedFile:
    path: str
    content: bytes | str | Mapping[str, Any] | Sequence[Any]
    format: Format = None
    mode: int | None = None
    reconcile_owned: bool = False


@dataclass(frozen=True, slots=True)
class ProducerContext:
    owner: str
    strategy: Literal["merge", "render"]
    source: str
    target: str
    source_files: Mapping[str, bytes]
    actual_files: Mapping[str, bytes]


ContentProducer = Callable[
    [ProducerContext],
    ProducedContent
    | bytes
    | str
    | Mapping[str, Any]
    | Sequence[ProducedFile],
]


@dataclass(frozen=True, slots=True)
class ConfigDeclaration:
    owner: str
    source: Path
    target: Path
    strategy: Literal["copy", "merge", "render", "symlink"]
    writable: bool
    sensitive: bool
    target_mode: int
    preserve: tuple[str, ...]
    exclude: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConfigOperation:
    """An immutable operation plus internal expected bytes for safe apply."""

    operation: Literal["create-root", "migrate-link", "write", "prune"]
    item: PlanItem
    relative_path: str | None = None
    content: bytes | None = None
    format: Format = None
    mode: int | None = None
    expected_link: str | None = None
    proven_owned_link: bool = False
    accepted_actual_hash: str | None = None
    metadata_only: bool = False

    def public_dict(self) -> dict[str, Any]:
        value = self.item.to_dict()
        value.update(
            operation=self.operation,
            relative_path=self.relative_path,
            metadata_only=self.metadata_only,
        )
        return value


@dataclass(frozen=True, slots=True)
class ConfigPlan:
    schema_version: int
    owner: str
    strategy: str
    source: str
    target: str
    source_digest: str
    source_ignored: tuple[str, ...]
    manifest_digest: str | None
    operations: tuple[ConfigOperation, ...]
    prior_manifest: ManagedManifest
    target_root_mode: int
    sensitive: bool

    @property
    def conflicts(self) -> tuple[PlanItem, ...]:
        return tuple(op.item for op in self.operations if op.item.state == "conflict")

    @property
    def status(self) -> Literal["conflict", "changed", "unchanged"]:
        if self.conflicts:
            return "conflict"
        if any(op.item.action != "none" for op in self.operations):
            return "changed"
        return "unchanged"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": "config-plan",
            "owner": self.owner,
            "strategy": self.strategy,
            "source": self.source,
            "target": self.target,
            "source_digest": self.source_digest,
            "manifest_digest": self.manifest_digest,
            "status": self.status,
            "operations": [op.public_dict() for op in self.operations],
        }


@dataclass(frozen=True, slots=True)
class ConfigApplyResult:
    status: Literal["changed", "unchanged"]
    changed: int
    unchanged: int
    pruned: int
    backups: tuple[Path, ...]
    manifest: Path


@dataclass(frozen=True, slots=True)
class _ExpectedFile:
    relative: str
    content: bytes
    format: Format
    mode: int
    reconcile_owned: bool = False


@dataclass(frozen=True, slots=True)
class _PathSnapshot:
    digest: str


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _read_fd(fd: int) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


def _read_regular(root: Path, path: Path) -> tuple[bytes, os.stat_result]:
    fd = open_nofollow(root, path)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ConfigDeployError(f"managed path is not a regular file: {path}")
        content = _read_fd(fd)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise ConfigDeployError(f"managed file changed while reading: {path}")
        return content, after
    finally:
        os.close(fd)


def _safe_relative(value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ConfigDeployError("producer path must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or value == ".":
        raise ConfigDeployError(f"unsafe producer path: {value!r}")
    normalized = str(PurePosixPath(os.path.normpath(value)))
    if normalized == ".." or normalized.startswith("../"):
        raise ConfigDeployError(f"unsafe producer path: {value!r}")
    return normalized


def _matches_path(relative: str, rules: tuple[str, ...]) -> bool:
    return any(relative == rule or relative.startswith(rule + "/") for rule in rules)


def _scan_tree(root: Path, path: Path, *, ignored: tuple[str, ...] = ()) -> dict[str, tuple[bytes, os.stat_result]]:
    """Read a regular-file tree without following any source/target symlink."""
    assert_no_symlinks(root, path, missing_ok=False)
    result: dict[str, tuple[bytes, os.stat_result]] = {}

    def visit(directory: Path, prefix: str) -> None:
        directory_fd = open_directory_nofollow(root, directory)
        try:
            names = sorted(os.listdir(directory_fd))
            for name in names:
                relative = f"{prefix}/{name}" if prefix else name
                if _matches_path(relative, ignored):
                    continue
                item = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                child = directory / name
                if stat.S_ISLNK(item.st_mode):
                    raise PathBoundaryError(errno.ELOOP, "unexpected symlink in managed tree", str(child))
                if stat.S_ISDIR(item.st_mode):
                    visit(child, relative)
                elif stat.S_ISREG(item.st_mode):
                    content, verified = _read_regular(root, child)
                    if (verified.st_dev, verified.st_ino) != (item.st_dev, item.st_ino):
                        raise ConfigDeployError(f"managed source changed while scanning: {child}")
                    result[relative] = (content, verified)
                else:
                    raise ConfigDeployError(f"unsupported managed source entry: {child}")
        finally:
            os.close(directory_fd)

    visit(path, "")
    return result


def _content_tree_digest(files: Mapping[str, tuple[bytes, os.stat_result]] | Mapping[str, bytes]) -> str:
    digest = hashlib.sha256(b"config-tree\0")
    for relative in sorted(files):
        value = files[relative]
        content = value[0] if isinstance(value, tuple) else value
        digest.update(relative.encode("utf-8") + b"\0" + _sha256(content).encode("ascii") + b"\0")
    return digest.hexdigest()


def _snapshot_path(path: Path, *, ignored: tuple[str, ...] = ()) -> _PathSnapshot:
    """Audit a callback boundary without following links or preserved subtrees."""
    digest = hashlib.sha256(b"snapshot-v1\0")

    def visit(current: Path, relative: str) -> None:
        try:
            item = current.lstat()
        except FileNotFoundError:
            digest.update(relative.encode() + b"\0missing\0")
            return
        if relative and _matches_path(relative, ignored):
            return
        metadata = (
            f"{relative}\0{stat.S_IFMT(item.st_mode)}\0{stat.S_IMODE(item.st_mode)}\0"
            f"{item.st_dev}\0{item.st_ino}\0{item.st_size}\0{item.st_mtime_ns}\0"
        ).encode()
        digest.update(metadata)
        if stat.S_ISLNK(item.st_mode):
            digest.update(os.fsencode(os.readlink(current)) + b"\0")
        elif stat.S_ISREG(item.st_mode):
            fd = os.open(current, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            try:
                digest.update(_read_fd(fd))
            finally:
                os.close(fd)
        elif stat.S_ISDIR(item.st_mode):
            for name in sorted(os.listdir(current)):
                visit(current / name, f"{relative}/{name}" if relative else name)

    visit(path, "")
    return _PathSnapshot(digest.hexdigest())


def _parse_mode(value: Any) -> int:
    if isinstance(value, bool):
        raise ConfigDeployError("target_mode must be an octal permission mode")
    if isinstance(value, int):
        mode = value
    elif isinstance(value, str):
        text = value[2:] if value.lower().startswith("0o") else value
        if not text or any(char not in "01234567" for char in text):
            raise ConfigDeployError("target_mode must be an octal permission mode")
        mode = int(text, 8)
    else:
        raise ConfigDeployError("target_mode must be an octal permission mode")
    if mode < 0 or mode > 0o777:
        raise ConfigDeployError("target_mode is outside 0000..0777")
    return mode


def declaration_from_registry(
    module: Mapping[str, Any], *, repo_root: os.PathLike[str] | str, home: os.PathLike[str] | str
) -> ConfigDeclaration:
    """Compile one already-validated registry module without module-name policy."""
    name = module.get("name")
    config = module.get("config")
    if not isinstance(name, str) or not name or not isinstance(config, Mapping):
        raise ConfigDeployError("module has no valid config declaration")
    strategy = config.get("strategy")
    if strategy not in {"copy", "merge", "render", "symlink"}:
        raise ConfigDeployError("registry config strategy is unsupported")
    writable = config.get("writable")
    sensitive = config.get("sensitive")
    if not isinstance(writable, bool) or not isinstance(sensitive, bool):
        raise ConfigDeployError("registry config safety booleans are invalid")
    source_raw = config.get("source")
    target_raw = config.get("target")
    if not isinstance(source_raw, str) or not isinstance(target_raw, str):
        raise ConfigDeployError("registry config paths are invalid")
    repo = Path(repo_root).absolute()
    home_path = Path(home).absolute()
    source = Path(source_raw)
    if not source.is_absolute():
        source = repo / source
    if target_raw == "~":
        target = home_path
    elif target_raw.startswith("~/"):
        target = home_path / target_raw[2:]
    else:
        target = Path(target_raw)
        if not target.is_absolute():
            target = home_path / target
    source = assert_path_confined(repo, source)
    target = assert_path_confined(home_path, target)
    try:
        target.relative_to(repo)
    except ValueError:
        pass
    else:
        raise ConfigDeployError("config target must not be inside the repository")
    mode_keys = [key for key in ("target_mode", "mode") if key in config]
    if len(mode_keys) != 1:
        raise ConfigDeployError("registry config requires exactly one target mode")
    preserve = tuple(_safe_relative(item) for item in config.get("preserve", ()))
    exclude = tuple(_safe_relative(item) for item in config.get("exclude", ()))
    return ConfigDeclaration(
        owner=f"{_OWNER_PREFIX}{name}",
        source=source,
        target=target,
        strategy=strategy,
        writable=writable,
        sensitive=sensitive,
        target_mode=_parse_mode(config[mode_keys[0]]),
        preserve=preserve,
        exclude=exclude,
    )


def _state_home(home: Path, state_home: os.PathLike[str] | str | None) -> Path:
    if state_home is not None:
        return Path(state_home).absolute()
    configured = os.environ.get("XDG_STATE_HOME")
    return Path(configured).absolute() if configured else home / ".local" / "state"


def _boundary_for(home: Path, path: Path) -> Path:
    try:
        path.relative_to(home)
    except ValueError:
        return Path("/")
    return home


def _empty_manifest() -> ManagedManifest:
    return ManagedManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        kind="managed-manifest",
        generated_at="1970-01-01T00:00:00Z",
        items=(),
    )


def _manifest_paths(home: Path, state_home: Path) -> tuple[Path, Path, Path]:
    directory = state_home / "dotf"
    return directory, directory / CONFIG_MANIFEST_NAME, directory / CONFIG_LOCK_NAME


def _read_manifest(home: Path, state_home: Path) -> tuple[ManagedManifest, str | None]:
    _directory, manifest_path, _lock = _manifest_paths(home, state_home)
    boundary = _boundary_for(home, manifest_path)
    try:
        assert_no_symlinks(boundary, manifest_path)
        fd = open_nofollow(boundary, manifest_path)
    except FileNotFoundError:
        return _empty_manifest(), None
    try:
        item = os.fstat(fd)
        if not stat.S_ISREG(item.st_mode):
            raise MalformedConfigManifest("config manifest is not a regular file")
        raw = _read_fd(fd)
    finally:
        os.close(fd)
    try:
        value = json.loads(raw)
        manifest = validate_managed_manifest(value)
    except (UnicodeDecodeError, json.JSONDecodeError, SchemaError, TypeError) as exc:
        raise MalformedConfigManifest("config manifest is malformed or incompatible") from exc
    return manifest, _sha256(raw)


def _serialize_manifest(manifest: ManagedManifest) -> bytes:
    manifest.validate()
    return (json.dumps(manifest.to_dict(), ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _ensure_state_directory(home: Path, state_home: Path) -> Path:
    boundary = _boundary_for(home, state_home)
    ensure_directory(boundary, state_home, mode=0o700)
    directory, _manifest, _lock = _manifest_paths(home, state_home)
    ensure_directory(boundary, directory, mode=0o700)
    fd = open_directory_nofollow(boundary, directory)
    try:
        os.fchmod(fd, 0o700)
    finally:
        os.close(fd)
    return directory


class _ManifestLock:
    def __init__(self, home: Path, state_home: Path) -> None:
        self.home = home
        self.state_home = state_home
        self.fd: int | None = None

    def __enter__(self) -> "_ManifestLock":
        _directory, _manifest, lock_path = _manifest_paths(self.home, self.state_home)
        _ensure_state_directory(self.home, self.state_home)
        boundary = _boundary_for(self.home, lock_path)
        self.fd = open_nofollow(
            boundary,
            lock_path,
            os.O_RDWR | os.O_CREAT,
            0o600,
        )
        os.fchmod(self.fd, 0o600)
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.fd is not None:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
            self.fd = None


def _format_for(path: str, declared: Format = None) -> Format:
    if declared is not None:
        return declared
    suffix = PurePosixPath(path).suffix.lower()
    return {".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml"}.get(suffix)


def _render_content(value: ProducedContent, path: str) -> tuple[bytes, Format, int | None]:
    format_value = _format_for(path, value.format)
    content = value.content
    if isinstance(content, bytes):
        payload = content
    elif isinstance(content, str):
        payload = content.encode()
    elif format_value == "json":
        payload = (json.dumps(content, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    elif format_value == "yaml":
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover - project bootstrap requires PyYAML
            raise ConfigDeployError("YAML producer output requires PyYAML") from exc
        payload = yaml.safe_dump(content, allow_unicode=True, sort_keys=True).encode()
    else:
        raise ConfigDeployError("structured producer data requires a JSON or YAML target")
    return payload, format_value, value.mode


def _producer_expected(
    declaration: ConfigDeclaration,
    source_is_dir: bool,
    source_files: Mapping[str, tuple[bytes, os.stat_result]],
    actual_files: Mapping[str, bytes],
    producer: ContentProducer,
    state_manifest_path: Path,
) -> list[_ExpectedFile]:
    # Producers are reviewed in-repo callbacks. Audit their declared inputs and
    # outputs, rather than recursively hashing unrelated runtime data preserved
    # under a writable target (sessions, caches, credentials, and plugins).
    before = (
        _snapshot_path(declaration.source),
        _snapshot_path(
            declaration.target,
            ignored=declaration.preserve + declaration.exclude,
        ),
        _snapshot_path(state_manifest_path),
    )
    context = ProducerContext(
        owner=declaration.owner,
        strategy=declaration.strategy,  # type: ignore[arg-type]
        source=str(declaration.source),
        target=str(declaration.target),
        source_files=MappingProxyType({key: value[0] for key, value in source_files.items()}),
        actual_files=MappingProxyType(dict(actual_files)),
    )
    callback_error: BaseException | None = None
    try:
        output = producer(context)
    except BaseException as exc:
        callback_error = exc
        output = b""

    raw_files: list[ProducedFile]
    if source_is_dir:
        if isinstance(output, Mapping):
            raw_files = [
                value if isinstance(value, ProducedFile) else ProducedFile(str(path), value)
                for path, value in output.items()
            ]
        elif isinstance(output, Sequence) and not isinstance(output, (str, bytes)) and all(
            isinstance(value, ProducedFile) for value in output
        ):
            raw_files = list(output)
        else:
            raw_files = []
            if callback_error is None:
                raise ConfigDeployError("directory merge/render producer must return path-mapped outputs")
    else:
        value = output if isinstance(output, ProducedContent) else ProducedContent(output)
        raw_files = [
            ProducedFile(
                ".",
                value.content,
                value.format,
                value.mode,
                value.reconcile_owned,
            )
        ]

    expected: list[_ExpectedFile] = []
    seen: set[str] = set()
    for produced in raw_files:
        relative = "." if not source_is_dir and produced.path == "." else _safe_relative(produced.path)
        if relative in seen:
            raise ConfigDeployError(f"producer returned duplicate target: {relative}")
        if relative != "." and _matches_path(relative, declaration.preserve + declaration.exclude):
            raise ConfigDeployError(f"producer returned preserved or excluded target: {relative}")
        seen.add(relative)
        render_path = declaration.target.name if relative == "." else relative
        payload, format_value, requested_mode = _render_content(
            ProducedContent(produced.content, produced.format, produced.mode), render_path
        )
        mode = requested_mode if requested_mode is not None else _default_file_mode(declaration, None)
        _validate_output_mode(declaration, mode)
        expected.append(
            _ExpectedFile(
                relative,
                payload,
                format_value,
                mode,
                produced.reconcile_owned,
            )
        )

    after = (
        _snapshot_path(declaration.source),
        _snapshot_path(
            declaration.target,
            ignored=declaration.preserve + declaration.exclude,
        ),
        _snapshot_path(state_manifest_path),
    )
    if before != after:
        error = UnsafeConfigHandlerError(
            "specialized config producer performed a direct source, target, or state write"
        )
        if callback_error is not None:
            raise error from callback_error
        raise error
    if callback_error is not None:
        raise callback_error
    return sorted(expected, key=lambda item: item.relative)


def _default_file_mode(declaration: ConfigDeclaration, source_stat: os.stat_result | None) -> int:
    if declaration.sensitive:
        return 0o600
    if source_stat is None:
        return 0o600 if declaration.target_mode & 0o111 == 0 else 0o700
    return stat.S_IMODE(source_stat.st_mode) & 0o777


def _validate_output_mode(declaration: ConfigDeclaration, mode: int) -> None:
    if isinstance(mode, bool) or not isinstance(mode, int) or mode < 0 or mode > 0o777:
        raise ConfigDeployError("producer output mode is invalid")
    allowed = 0o600 if declaration.sensitive else declaration.target_mode
    if mode & ~allowed:
        raise ConfigDeployError("producer output mode broadens registry permission policy")


def _actual_files_for_producer(
    home: Path,
    declaration: ConfigDeclaration,
    *,
    source_is_dir: bool,
    legacy_directory_links: tuple[str, ...] = (),
) -> dict[str, bytes]:
    """Return immutable actual bytes using the same relative keys as source files.

    A missing target is represented by an empty mapping. For a single-file
    declaration, an existing regular target is read through the descriptor-
    relative no-follow path and exposed as ``actual_files["."]``. Directory
    declarations retain their path-mapped tree view. A single-file target
    symlink is never presented to a producer because merge/render must not
    inspect or derive output through an undeclared link boundary.
    """
    try:
        target_stat = declaration.target.lstat()
    except FileNotFoundError:
        return {}
    if source_is_dir:
        if stat.S_ISLNK(target_stat.st_mode) or not stat.S_ISDIR(target_stat.st_mode):
            return {}
        scanned = _scan_tree(
            home,
            declaration.target,
            ignored=declaration.preserve + declaration.exclude + legacy_directory_links,
        )
        return {relative: value[0] for relative, value in scanned.items()}
    if stat.S_ISLNK(target_stat.st_mode):
        raise PathBoundaryError(
            errno.ELOOP,
            "single-file merge/render target must not be a symbolic link",
            str(declaration.target),
        )
    if not stat.S_ISREG(target_stat.st_mode):
        return {}
    content, verified = _read_regular(home, declaration.target)
    if (verified.st_dev, verified.st_ino) != (target_stat.st_dev, target_stat.st_ino):
        raise ConfigDeployError(
            f"managed target changed while collecting producer input: {declaration.target}"
        )
    return {".": content}


def _exact_nested_directory_links(
    repo_root: Path,
    home: Path,
    declaration: ConfigDeclaration,
) -> tuple[str, ...]:
    """Find nested target directory links that exactly mirror source directories.

    This is intentionally derived only from the registry source/target pair. It
    never follows a target link, and foreign links are left for normal boundary
    validation to reject. The root link remains handled by the existing root
    migration path.
    """
    source_stat = declaration.source.lstat()
    if not stat.S_ISDIR(source_stat.st_mode):
        return ()
    try:
        target_stat = declaration.target.lstat()
    except FileNotFoundError:
        return ()
    if stat.S_ISLNK(target_stat.st_mode) or not stat.S_ISDIR(target_stat.st_mode):
        return ()
    assert_no_symlinks(home, declaration.target, missing_ok=False)
    found: list[str] = []

    def visit(source_directory: Path, target_directory: Path, prefix: str) -> None:
        source_fd = open_directory_nofollow(repo_root, source_directory)
        target_fd = open_directory_nofollow(home, target_directory)
        try:
            for name in sorted(os.listdir(source_fd)):
                source_item = os.stat(name, dir_fd=source_fd, follow_symlinks=False)
                if not stat.S_ISDIR(source_item.st_mode):
                    continue
                relative = f"{prefix}/{name}" if prefix else name
                source_child = source_directory / name
                target_child = target_directory / name
                try:
                    target_item = os.stat(name, dir_fd=target_fd, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                if stat.S_ISLNK(target_item.st_mode):
                    if _link_points_to(target_child, source_child):
                        found.append(relative)
                    continue
                if stat.S_ISDIR(target_item.st_mode):
                    visit(source_child, target_child, relative)
        finally:
            os.close(target_fd)
            os.close(source_fd)

    visit(declaration.source, declaration.target, "")
    return tuple(found)


def _expected_files(
    declaration: ConfigDeclaration,
    repo_root: Path,
    home: Path,
    producer: ContentProducer | None,
    manifest_path: Path,
    legacy_directory_links: tuple[str, ...] = (),
) -> tuple[list[_ExpectedFile], str, bool]:
    assert_no_symlinks(repo_root, declaration.source, missing_ok=False)
    source_stat = declaration.source.lstat()
    if stat.S_ISREG(source_stat.st_mode):
        content, verified = _read_regular(repo_root, declaration.source)
        source_files = {".": (content, verified)}
        source_is_dir = False
    elif stat.S_ISDIR(source_stat.st_mode):
        source_files = _scan_tree(
            repo_root,
            declaration.source,
            ignored=declaration.exclude + declaration.preserve,
        )
        source_is_dir = True
    else:
        raise ConfigDeployError("config source must be a regular file or directory")
    source_digest = _content_tree_digest(source_files)

    if declaration.strategy == "copy":
        expected = [
            _ExpectedFile(
                relative,
                value[0],
                "binary",
                declaration.target_mode if not source_is_dir else _default_file_mode(declaration, value[1]),
            )
            for relative, value in sorted(source_files.items())
        ]
    elif declaration.strategy in {"merge", "render"}:
        if producer is None:
            raise ConfigDeployError(
                f"strategy {declaration.strategy} requires a pure expected-content producer"
            )
        expected = _producer_expected(
            declaration,
            source_is_dir,
            source_files,
            _actual_files_for_producer(
                home,
                declaration,
                source_is_dir=source_is_dir,
                legacy_directory_links=legacy_directory_links,
            ),
            producer,
            manifest_path,
        )
    else:
        raise ConfigDeployError("generic managed-file deployer does not install symlink strategy")
    for item in expected:
        _validate_output_mode(declaration, item.mode)
        validate_content(item.content, item.format)
    return expected, source_digest, source_is_dir


def _link_value(path: Path) -> str:
    return os.readlink(path)


def _link_points_to(path: Path, source: Path) -> bool:
    value = _link_value(path)
    resolved = Path(value) if os.path.isabs(value) else path.parent / value
    return Path(os.path.abspath(resolved)) == Path(os.path.abspath(source))


def _item_by_target(manifest: ManagedManifest) -> dict[str, ManagedItem]:
    return {item.target: item for item in manifest.items}


def _plan_item(
    declaration: ConfigDeclaration,
    *,
    source_identity: str,
    expected_hash: str | None,
    target: Path,
    state: str,
    action: str,
    conflict_reason: str | None = None,
    mode: int | None = None,
) -> PlanItem:
    return PlanItem(
        schema_version=PLAN_SCHEMA_VERSION,
        kind="plan-item",
        owner=declaration.owner,
        source_identity=source_identity,
        expected_hash=expected_hash,
        target=str(target),
        strategy=declaration.strategy,
        risk="sensitive" if declaration.sensitive else ("medium" if declaration.writable else "low"),
        state=state,
        action=action,
        conflict_reason=conflict_reason,
        required_secrets=(),
        target_mode=mode,
        sensitive=declaration.sensitive,
    )


def _target_for(declaration: ConfigDeclaration, source_is_dir: bool, relative: str) -> Path:
    return declaration.target / relative if source_is_dir else declaration.target


def _inspect_expected_target(
    home: Path,
    target: Path,
) -> tuple[str, bytes | None, os.stat_result | None]:
    try:
        assert_no_symlinks(home, target)
        item = target.lstat()
    except FileNotFoundError:
        return "missing", None, None
    except PathBoundaryError:
        return "symlink", None, None
    if not stat.S_ISREG(item.st_mode):
        return "other", None, item
    content, verified = _read_regular(home, target)
    return "file", content, verified


def compile_config_plan(
    module: Mapping[str, Any],
    *,
    repo_root: os.PathLike[str] | str,
    home: os.PathLike[str] | str,
    state_home: os.PathLike[str] | str | None = None,
    producer: ContentProducer | None = None,
) -> ConfigPlan:
    """Compile a plan without creating directories, locks, backups, or files."""
    repo = Path(repo_root).absolute()
    home_path = Path(home).absolute()
    declaration = declaration_from_registry(module, repo_root=repo, home=home_path)
    state = _state_home(home_path, state_home)
    state_dir, manifest_path, _lock_path = _manifest_paths(home_path, state)
    manifest, manifest_digest = _read_manifest(home_path, state)
    assert_no_symlinks(home_path, declaration.target, allow_leaf_symlink=True)
    legacy_directory_links = _exact_nested_directory_links(
        repo, home_path, declaration
    )
    expected, source_digest, source_is_dir = _expected_files(
        declaration,
        repo,
        home_path,
        producer,
        state_dir,
        legacy_directory_links,
    )
    owned = _item_by_target(manifest)
    operations: list[ConfigOperation] = []
    root_virtual_missing = False

    try:
        target_stat = declaration.target.lstat()
    except FileNotFoundError:
        target_stat = None
    if source_is_dir:
        if target_stat is None:
            operations.append(
                ConfigOperation(
                    "create-root",
                    _plan_item(
                        declaration,
                        source_identity=str(declaration.source),
                        expected_hash=source_digest,
                        target=declaration.target,
                        state="create",
                        action="create",
                        mode=None,
                    ),
                )
            )
            root_virtual_missing = True
        elif stat.S_ISLNK(target_stat.st_mode):
            root_owned = owned.get(str(declaration.target))
            proven_owned = bool(
                root_owned
                and root_owned.owner == declaration.owner
                and root_owned.source_identity == str(declaration.source)
                and root_owned.strategy == "symlink"
            )
            if _link_points_to(declaration.target, declaration.source) or proven_owned:
                operations.append(
                    ConfigOperation(
                        "migrate-link",
                        _plan_item(
                            declaration,
                            source_identity=str(declaration.source),
                            expected_hash=source_digest,
                            target=declaration.target,
                            state="update",
                            action="update",
                            mode=None,
                        ),
                        expected_link=_link_value(declaration.target),
                        proven_owned_link=proven_owned,
                    )
                )
                root_virtual_missing = True
            else:
                operations.append(
                    ConfigOperation(
                        "migrate-link",
                        _plan_item(
                            declaration,
                            source_identity=str(declaration.source),
                            expected_hash=source_digest,
                            target=declaration.target,
                            state="conflict",
                            action="block",
                            conflict_reason="foreign-directory-symlink",
                            mode=None,
                        ),
                        expected_link=_link_value(declaration.target),
                    )
                )
        elif not stat.S_ISDIR(target_stat.st_mode):
            operations.append(
                ConfigOperation(
                    "create-root",
                    _plan_item(
                        declaration,
                        source_identity=str(declaration.source),
                        expected_hash=source_digest,
                        target=declaration.target,
                        state="conflict",
                        action="block",
                        conflict_reason="unowned-real-target",
                        mode=None,
                    ),
                )
            )
        else:
            assert_no_symlinks(home_path, declaration.target, missing_ok=False)
            if stat.S_IMODE(target_stat.st_mode) != declaration.target_mode:
                operations.append(
                    ConfigOperation(
                        "create-root",
                        _plan_item(
                            declaration,
                            source_identity=str(declaration.source),
                            expected_hash=source_digest,
                            target=declaration.target,
                            state="update",
                            action="update",
                            mode=None,
                        ),
                        metadata_only=True,
                    )
                )
            for relative in legacy_directory_links:
                source_directory = declaration.source / relative
                target_directory = declaration.target / relative
                operations.append(
                    ConfigOperation(
                        "migrate-link",
                        _plan_item(
                            declaration,
                            source_identity=str(source_directory),
                            expected_hash=source_digest,
                            target=target_directory,
                            state="update",
                            action="update",
                            mode=None,
                        ),
                        relative_path=relative,
                        expected_link=_link_value(target_directory),
                    )
                )
    elif target_stat is not None and stat.S_ISLNK(target_stat.st_mode):
        operations.append(
            ConfigOperation(
                "write",
                _plan_item(
                    declaration,
                    source_identity=str(declaration.source),
                    expected_hash=_sha256(expected[0].content),
                    target=declaration.target,
                    state="conflict",
                    action="block",
                    conflict_reason="foreign-file-symlink",
                    mode=expected[0].mode,
                ),
                relative_path=".",
                content=expected[0].content,
                format=expected[0].format,
                mode=expected[0].mode,
            )
        )

    root_conflict = any(
        op.item.state == "conflict" and op.item.target == str(declaration.target)
        for op in operations
    )
    expected_targets: set[str] = set()
    for expected_file in expected:
        target = _target_for(declaration, source_is_dir, expected_file.relative)
        target_key = str(target)
        expected_targets.add(target_key)
        expected_hash = _sha256(expected_file.content)
        source_identity = (
            str(declaration.source / expected_file.relative)
            if source_is_dir
            else str(declaration.source)
        )
        prior = owned.get(target_key)
        if root_conflict:
            continue
        under_legacy_link = any(
            expected_file.relative == relative
            or expected_file.relative.startswith(relative + "/")
            for relative in legacy_directory_links
        )
        if root_virtual_missing or under_legacy_link:
            target_kind, actual_content, actual_stat = "missing", None, None
        else:
            target_kind, actual_content, actual_stat = _inspect_expected_target(home_path, target)

        state = "create"
        action = "create"
        reason: str | None = None
        metadata_only = False
        accepted_actual_hash: str | None = None
        if target_kind == "symlink":
            state, action, reason = "conflict", "block", "unexpected-target-symlink"
        elif target_kind == "other":
            state, action, reason = "conflict", "block", "unowned-real-target"
        elif target_kind == "file":
            assert actual_content is not None and actual_stat is not None
            actual_hash = _sha256(actual_content)
            accepted_actual_hash = actual_hash
            if prior is None:
                state, action, reason = "conflict", "block", "unowned-real-target"
            elif prior.owner != declaration.owner:
                state, action, reason = "conflict", "block", "foreign-managed-owner"
            elif actual_hash == expected_hash:
                metadata_changed = (
                    prior.expected_hash != expected_hash
                    or prior.installed_hash != expected_hash
                    or prior.source_identity != source_identity
                    or prior.strategy != declaration.strategy
                    or prior.mode != expected_file.mode
                    or prior.sensitive != declaration.sensitive
                    or stat.S_IMODE(actual_stat.st_mode) != expected_file.mode
                )
                if metadata_changed:
                    state, action, metadata_only = "update", "update", True
                else:
                    state, action = "unchanged", "none"
            elif actual_hash == prior.installed_hash:
                state, action = "update", "update"
            elif expected_file.reconcile_owned:
                # The reviewed producer explicitly performed field-level
                # reconciliation against these pinned actual bytes.
                state, action = "update", "update"
            else:
                state, action, reason = "conflict", "block", "managed-target-modified"
        operations.append(
            ConfigOperation(
                "write",
                _plan_item(
                    declaration,
                    source_identity=source_identity,
                    expected_hash=expected_hash,
                    target=target,
                    state=state,
                    action=action,
                    conflict_reason=reason,
                    mode=expected_file.mode,
                ),
                relative_path=expected_file.relative,
                content=expected_file.content,
                format=expected_file.format,
                mode=expected_file.mode,
                accepted_actual_hash=accepted_actual_hash,
                metadata_only=metadata_only,
            )
        )

    # Reconcile only this module's prior file ownership. Preserve/exclude paths
    # are deliberately outside ownership and are never stale-pruned here.
    migration_targets = {
        op.item.target for op in operations if op.operation == "migrate-link" and op.item.action != "block"
    }
    for prior in sorted(manifest.items, key=lambda item: item.target):
        if (
            prior.owner != declaration.owner
            or prior.target in expected_targets
            or prior.target in migration_targets
        ):
            continue
        stale_target = Path(prior.target)
        try:
            stale_target.relative_to(declaration.target if source_is_dir else declaration.target.parent)
        except ValueError:
            reason = "owned-target-outside-current-root"
            state, action = "conflict", "block"
        else:
            relative = (
                str(stale_target.relative_to(declaration.target)) if source_is_dir else stale_target.name
            )
            if source_is_dir and _matches_path(relative, declaration.preserve + declaration.exclude):
                continue
            kind, content, _item = _inspect_expected_target(home_path, stale_target)
            if kind == "missing":
                reason, state, action = None, "prune", "prune"
            elif kind == "file" and content is not None and _sha256(content) == prior.installed_hash:
                reason, state, action = None, "prune", "prune"
            else:
                reason, state, action = "stale-target-modified-or-unsafe", "conflict", "block"
        operations.append(
            ConfigOperation(
                "prune",
                _plan_item(
                    declaration,
                    source_identity=prior.source_identity,
                    expected_hash=prior.expected_hash,
                    target=stale_target,
                    state=state,
                    action=action,
                    conflict_reason=reason,
                    mode=prior.mode,
                ),
                mode=prior.mode,
            )
        )

    return ConfigPlan(
        schema_version=PLAN_SCHEMA_VERSION,
        owner=declaration.owner,
        strategy=declaration.strategy,
        source=str(declaration.source),
        target=str(declaration.target),
        source_digest=source_digest,
        source_ignored=declaration.exclude + declaration.preserve,
        manifest_digest=manifest_digest,
        operations=tuple(operations),
        prior_manifest=manifest,
        target_root_mode=declaration.target_mode,
        sensitive=declaration.sensitive,
    )


def _manifest_equivalent(left: ManagedManifest, right: ManagedManifest) -> bool:
    return left.to_dict() == right.to_dict()


def _secure_directory(home: Path, path: Path, mode: int) -> None:
    ensure_directory(home, path, mode=mode)
    fd = open_directory_nofollow(home, path)
    try:
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally:
        os.close(fd)


def _migrate_exact_link(
    home: Path,
    target: Path,
    source: Path,
    expected_link: str,
    mode: int,
    *,
    proven_owned: bool = False,
) -> None:
    """Unlink only the exact leaf symlink, then create a real directory."""
    parent_fd, name = open_parent_nofollow(home, target)
    original: os.stat_result | None = None
    try:
        original = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISLNK(original.st_mode):
            raise ConfigConflictError("legacy migration target is no longer a symlink")
        link_value = os.readlink(name, dir_fd=parent_fd)
        if link_value != expected_link or (
            not proven_owned and not _link_points_to(target, source)
        ):
            raise ConfigConflictError(
                "legacy migration symlink no longer matches declared source or proven ownership"
            )
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino):
            raise ConfigConflictError("legacy migration symlink changed before unlink")
        os.unlink(name, dir_fd=parent_fd)
        try:
            os.mkdir(name, mode=mode, dir_fd=parent_fd)
            directory_fd = os.open(
                name,
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=parent_fd,
            )
            try:
                os.fchmod(directory_fd, mode)
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            os.fsync(parent_fd)
        except BaseException:
            try:
                os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                os.symlink(link_value, name, dir_fd=parent_fd)
                os.fsync(parent_fd)
            raise
    finally:
        os.close(parent_fd)


def _source_digest_now(plan: ConfigPlan, repo_root: Path) -> str:
    source = Path(plan.source)
    source_stat = source.lstat()
    if stat.S_ISREG(source_stat.st_mode):
        content, verified = _read_regular(repo_root, source)
        files = {".": (content, verified)}
    elif stat.S_ISDIR(source_stat.st_mode):
        files = _scan_tree(repo_root, source, ignored=plan.source_ignored)
    else:
        raise ConfigDeployError("config source type changed after planning")
    return _content_tree_digest(files)


def _write_manifest(home: Path, state_home: Path, manifest: ManagedManifest) -> Path:
    _directory, manifest_path, _lock_path = _manifest_paths(home, state_home)
    boundary = _boundary_for(home, manifest_path)
    result = atomic_write(
        manifest_path,
        _serialize_manifest(manifest),
        root=boundary,
        format="json",
        mode=0o600,
        sensitive=True,
    )
    del result
    return manifest_path


def _assert_operation_fresh(
    operation: ConfigOperation,
    home: Path,
    prior_by_target: Mapping[str, ManagedItem],
) -> None:
    """Reconcile the live leaf with the exact state accepted by the plan."""
    item = operation.item
    target = Path(item.target)
    if operation.operation == "create-root":
        try:
            current = target.lstat()
        except FileNotFoundError:
            if item.action == "create":
                return
            raise ConfigConflictError("config root disappeared after planning")
        if item.action == "update" and stat.S_ISDIR(current.st_mode) and not stat.S_ISLNK(current.st_mode):
            assert_no_symlinks(home, target, missing_ok=False)
            return
        raise ConfigConflictError("config root changed after planning")
    if operation.operation == "migrate-link":
        return  # _migrate_exact_link pins identity and value itself

    kind, content, target_stat = _inspect_expected_target(home, target)
    prior = prior_by_target.get(str(target))
    if operation.operation == "write":
        if item.action == "create":
            if kind != "missing":
                raise ConfigConflictError(f"target appeared after planning: {target}")
            return
        if kind != "file" or content is None or prior is None or prior.owner != item.owner:
            raise ConfigConflictError(f"managed target changed type or ownership: {target}")
        actual_hash = _sha256(content)
        if item.action == "none":
            if (
                actual_hash != item.expected_hash
                or target_stat is None
                or item.target_mode is None
                or stat.S_IMODE(target_stat.st_mode) != item.target_mode
            ):
                raise ConfigConflictError(f"unchanged target changed after planning: {target}")
        elif item.action == "update":
            accepted_hashes = {item.expected_hash, prior.installed_hash}
            if operation.accepted_actual_hash is not None:
                accepted_hashes.add(operation.accepted_actual_hash)
            if actual_hash not in accepted_hashes:
                raise ConfigConflictError(f"managed target changed after planning: {target}")
        return

    if operation.operation == "prune":
        if kind == "missing":
            return
        if (
            kind != "file"
            or content is None
            or prior is None
            or prior.owner != item.owner
            or _sha256(content) != prior.installed_hash
        ):
            raise ConfigConflictError(f"stale target changed after planning: {target}")


def apply_config_plan(
    plan: ConfigPlan,
    *,
    repo_root: os.PathLike[str] | str,
    home: os.PathLike[str] | str,
    state_home: os.PathLike[str] | str | None = None,
    run_id: str | None = None,
) -> ConfigApplyResult:
    """Apply an immutable plan while retaining all write safety ownership here."""
    if not isinstance(plan, ConfigPlan) or plan.schema_version != PLAN_SCHEMA_VERSION:
        raise ConfigDeployError("unsupported config plan")
    if plan.conflicts:
        reasons = ", ".join(
            f"{item.target}: {item.conflict_reason}" for item in plan.conflicts
        )
        raise ConfigConflictError(reasons)
    repo = Path(repo_root).absolute()
    home_path = Path(home).absolute()
    state = _state_home(home_path, state_home)
    run = run_id or generate_run_id()
    backup_root = home_path / ".local" / "state" / "dotf" / "backups"
    changed = 0
    unchanged = 0
    pruned = 0
    backups: list[Path] = []

    with _ManifestLock(home_path, state):
        current_manifest, current_digest = _read_manifest(home_path, state)
        if current_digest != plan.manifest_digest or not _manifest_equivalent(
            current_manifest, plan.prior_manifest
        ):
            raise ConfigConflictError("config manifest changed after planning")
        if _source_digest_now(plan, repo) != plan.source_digest:
            raise ConfigConflictError("config source changed after planning")
        source_digest_before = _snapshot_path(Path(plan.source))

        expected_items: list[ManagedItem] = []
        prior_by_target = _item_by_target(current_manifest)
        for operation in plan.operations:
            item = operation.item
            target = Path(item.target)
            _assert_operation_fresh(operation, home_path, prior_by_target)
            if operation.operation == "create-root":
                if item.action in {"create", "update"}:
                    _secure_directory(home_path, target, plan.target_root_mode)
                    changed += 1
            elif operation.operation == "migrate-link":
                assert operation.expected_link is not None
                _migrate_exact_link(
                    home_path,
                    target,
                    Path(item.source_identity),
                    operation.expected_link,
                    plan.target_root_mode,
                    proven_owned=operation.proven_owned_link,
                )
                changed += 1
            elif operation.operation == "write":
                assert operation.content is not None and operation.mode is not None
                if target.parent != home_path:
                    # Ensure every directory path is real and constrained. Root
                    # policy applies to all tree parents; file-only parents stay private.
                    root_target = Path(plan.target)
                    if root_target != target:
                        _secure_directory(home_path, root_target, plan.target_root_mode)
                if item.action == "none":
                    unchanged += 1
                else:
                    result = atomic_write(
                        target,
                        operation.content,
                        root=home_path,
                        format=operation.format,
                        mode=operation.mode,
                        backup_root=backup_root,
                        run_id=run,
                        sensitive=plan.sensitive,
                    )
                    if result.backup is not None:
                        backups.append(result.backup)
                    changed += 1
                expected_hash = _sha256(operation.content)
                prior_item = prior_by_target.get(str(target))
                if item.action == "none" and prior_item is not None:
                    expected_items.append(prior_item)
                else:
                    expected_items.append(
                        ManagedItem(
                            owner=plan.owner,
                            target=str(target),
                            source_identity=item.source_identity,
                            expected_hash=expected_hash,
                            installed_hash=expected_hash,
                            strategy=plan.strategy,
                            mode=operation.mode,
                            run_id=run,
                            sensitive=plan.sensitive,
                        )
                    )
            elif operation.operation == "prune":
                if item.action != "prune":
                    continue
                try:
                    target.lstat()
                except FileNotFoundError:
                    pass
                else:
                    backup = backup_target(
                        target,
                        backup_root,
                        run,
                        home_path,
                        sensitive=plan.sensitive,
                        remove_source=True,
                    )
                    backups.append(backup)
                pruned += 1
                changed += 1

            if _snapshot_path(Path(plan.source)) != source_digest_before:
                raise UnsafeConfigHandlerError("repository config source changed during apply")

        retained = [item for item in current_manifest.items if item.owner != plan.owner]
        new_manifest = ManagedManifest(
            schema_version=MANIFEST_SCHEMA_VERSION,
            kind="managed-manifest",
            generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            items=tuple(sorted(retained + expected_items, key=lambda entry: entry.target)),
        )
        manifest_path = _manifest_paths(home_path, state)[1]
        if new_manifest.items != current_manifest.items:
            _write_manifest(home_path, state, new_manifest)
        if _snapshot_path(Path(plan.source)) != source_digest_before:
            raise UnsafeConfigHandlerError("repository config source changed during manifest update")

    return ConfigApplyResult(
        status="changed" if changed else "unchanged",
        changed=changed,
        unchanged=unchanged,
        pruned=pruned,
        backups=tuple(backups),
        manifest=manifest_path,
    )


def deploy_config(
    module: Mapping[str, Any],
    *,
    repo_root: os.PathLike[str] | str,
    home: os.PathLike[str] | str,
    state_home: os.PathLike[str] | str | None = None,
    producer: ContentProducer | None = None,
    run_id: str | None = None,
) -> ConfigApplyResult:
    plan = compile_config_plan(
        module,
        repo_root=repo_root,
        home=home,
        state_home=state_home,
        producer=producer,
    )
    return apply_config_plan(
        plan,
        repo_root=repo_root,
        home=home,
        state_home=state_home,
        run_id=run_id,
    )


def _load_registry_module(repo_root: Path, name: str) -> Mapping[str, Any]:
    import sys

    scripts = str(repo_root / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import modules

    registry = modules.load_registry(repo_root / "modules.yaml")
    errors = modules.validate_registry(
        registry, profiles_data=modules.load_profiles(repo_root / "profiles.yaml"), strict_handlers=False
    )
    if errors:
        raise ConfigDeployError("invalid config registry: " + "; ".join(errors))
    module = modules.find_module(registry, name)
    if module is None:
        raise ConfigDeployError(f"unknown module: {name}")
    return module


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m dotf_core.config_deploy")
    parser.add_argument("command", choices=("plan", "apply"))
    parser.add_argument("module")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--home", default=os.environ.get("HOME"))
    parser.add_argument("--state-home", default=None)
    parser.add_argument("--run-id", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.home:
        raise SystemExit("HOME is required")
    repo = Path(args.repo_root).absolute()
    module = _load_registry_module(repo, args.module)
    try:
        plan = compile_config_plan(
            module,
            repo_root=repo,
            home=args.home,
            state_home=args.state_home,
        )
        if args.command == "plan":
            print(json.dumps(plan.to_dict(), ensure_ascii=False, sort_keys=True))
            return 1 if plan.conflicts else 0
        result = apply_config_plan(
            plan,
            repo_root=repo,
            home=args.home,
            state_home=args.state_home,
            run_id=args.run_id,
        )
        print(result.status)
        return 0
    except (ConfigDeployError, SchemaError, OSError, ValueError) as exc:
        print(f"config deploy failed: {exc}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
