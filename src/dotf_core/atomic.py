"""Validated same-filesystem staging and fd-relative atomic replacement."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .backup import backup_target_at, discard_backup_candidate
from .paths import (
    PathBoundaryError,
    assert_path_confined,
    normalize_target_root,
    open_parent_nofollow,
)

Format = Literal["json", "yaml", "toml", "text", "binary", None]


@dataclass(frozen=True, slots=True)
class AtomicWriteResult:
    status: Literal["changed", "unchanged"]
    target: Path
    backup: Path | None = None


def _identity(item: os.stat_result) -> tuple[int, int, int]:
    return item.st_dev, item.st_ino, stat.S_IFMT(item.st_mode)


def _regular_digest(payload: bytes) -> str:
    return hashlib.sha256(b"regular\0" + payload).hexdigest()


def _read_regular_fd(fd: int) -> bytes:
    chunks: list[bytes] = []
    os.lseek(fd, 0, os.SEEK_SET)
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            break
        chunks.append(chunk)
    os.lseek(fd, 0, os.SEEK_SET)
    return b"".join(chunks)


class StagedFile(os.PathLike[str]):
    """A staged leaf and target state coupled to retained descriptors.

    The display path is informational only. Security-sensitive operations use
    retained descriptors and ``name`` with ``dir_fd``. The stage descriptor
    pins the exact validated inode, while its digest pins the validated bytes.
    """

    __slots__ = (
        "target",
        "name",
        "target_name",
        "_parent_fd",
        "_stage_fd",
        "_stage_stat",
        "_stage_digest",
        "_target_fd",
        "_target_stat",
        "_target_digest",
        "_active",
    )

    def __init__(
        self,
        target: Path,
        name: str,
        target_name: str,
        parent_fd: int,
        stage_fd: int,
        stage_stat: os.stat_result,
        stage_digest: str,
        target_fd: int | None,
        target_stat: os.stat_result | None,
        target_digest: str | None,
    ) -> None:
        self.target = target
        self.name = name
        self.target_name = target_name
        self._parent_fd = parent_fd
        self._stage_fd = stage_fd
        self._stage_stat = stage_stat
        self._stage_digest = stage_digest
        self._target_fd = target_fd
        self._target_stat = target_stat
        self._target_digest = target_digest
        self._active = True

    @property
    def path(self) -> Path:
        return self.target.parent / self.name

    @property
    def parent_fd(self) -> int:
        if not self._active:
            raise ValueError("staged file handle is closed")
        return self._parent_fd

    @property
    def target_fd(self) -> int | None:
        if not self._active:
            raise ValueError("staged file handle is closed")
        return self._target_fd

    @property
    def target_stat(self) -> os.stat_result | None:
        if not self._active:
            raise ValueError("staged file handle is closed")
        return self._target_stat

    @property
    def target_digest(self) -> str | None:
        if not self._active:
            raise ValueError("staged file handle is closed")
        return self._target_digest

    def __fspath__(self) -> str:
        return os.fspath(self.path)

    def stat(self) -> os.stat_result:
        if not self._active:
            raise ValueError("staged file handle is closed")
        return os.fstat(self._stage_fd)

    def _close(self) -> None:
        if self._target_fd is not None:
            os.close(self._target_fd)
            self._target_fd = None
        os.close(self._stage_fd)
        os.close(self._parent_fd)
        self._active = False

    def cleanup(self) -> None:
        """Remove only the retained staged inode, then close all descriptors."""
        if not self._active:
            return
        try:
            try:
                current = os.stat(self.name, dir_fd=self._parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                current = None
            if current is not None and _identity(current) == _identity(self._stage_stat):
                os.unlink(self.name, dir_fd=self._parent_fd)
        finally:
            self._close()

    def _committed(self) -> None:
        if self._active:
            self._close()

    def __del__(self) -> None:  # pragma: no cover - deterministic cleanup is tested
        try:
            self.cleanup()
        except Exception:
            pass


def validate_content(content: bytes | str, format: Format) -> None:
    """Parse staged structured content before any target mutation."""
    if format == "binary":
        return
    if format in (None, "text"):
        if isinstance(content, bytes):
            content.decode("utf-8")
        return
    text = content.decode("utf-8") if isinstance(content, bytes) else content
    if format == "json":
        json.loads(text)
    elif format == "toml":
        try:
            import tomllib
        except ImportError as exc:  # pragma: no cover - supported Python is 3.11+
            raise RuntimeError("TOML validation requires Python 3.11+") from exc
        tomllib.loads(text)
    elif format == "yaml":
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover - bootstrap prevents this
            raise RuntimeError("YAML validation requires PyYAML") from exc
        yaml.safe_load(text)
    else:
        raise ValueError(f"unsupported format: {format}")


def _bytes(content: bytes | str) -> bytes:
    return content if isinstance(content, bytes) else content.encode("utf-8")


def _validate_regular_mode(mode: int, *, sensitive: bool) -> None:
    if isinstance(mode, bool) or not isinstance(mode, int) or mode < 0 or mode > 0o777:
        raise ValueError("mode must be an integer permission mode")
    if sensitive and mode & ~0o600:
        raise ValueError("sensitive regular-file mode contains bits outside 0600")


def _leaf_stat(parent_fd: int, name: str) -> os.stat_result | None:
    try:
        item = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(item.st_mode):
        raise PathBoundaryError(errno.ELOOP, "unsafe managed leaf", name)
    return item


def _require_leaf_identity(
    parent_fd: int,
    name: str,
    expected: os.stat_result | None,
    message: str,
) -> None:
    current = _leaf_stat(parent_fd, name)
    if current is None or expected is None:
        if current is not expected:
            raise RuntimeError(message)
        return
    if _identity(current) != _identity(expected):
        raise RuntimeError(message)


def _open_target(parent_fd: int, name: str) -> tuple[os.stat_result | None, int | None, bytes | None, str | None]:
    item = _leaf_stat(parent_fd, name)
    if item is None:
        return None, None, None, None
    if not stat.S_ISREG(item.st_mode):
        raise ValueError("managed target is not a regular file")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(name, flags, dir_fd=parent_fd)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise PathBoundaryError(errno.ELOOP, "unsafe managed leaf", name) from exc
        raise
    try:
        if _identity(os.fstat(fd)) != _identity(item):
            raise RuntimeError("managed target changed while opening")
        payload = _read_regular_fd(fd)
        _require_leaf_identity(parent_fd, name, item, "managed target changed while reading")
        return item, fd, payload, _regular_digest(payload)
    except BaseException:
        os.close(fd)
        raise


def _require_visible_target(
    base: Path,
    target: Path,
    pinned_parent_fd: int,
    expected: os.stat_result | None,
) -> None:
    """Ensure the displayed target still names the pinned parent and leaf."""
    visible_parent_fd, visible_name = open_parent_nofollow(base, target)
    try:
        if _identity(os.fstat(visible_parent_fd)) != _identity(os.fstat(pinned_parent_fd)):
            raise RuntimeError("visible target parent changed before commit")
        _require_leaf_identity(visible_parent_fd, visible_name, expected, "visible target changed before commit")
    finally:
        os.close(visible_parent_fd)


def _stage_at(
    target: Path,
    target_name: str,
    parent_fd: int,
    payload: bytes,
    mode: int,
    target_fd: int | None,
    target_stat: os.stat_result | None,
    target_digest: str | None,
) -> StagedFile:
    flags = (
        os.O_RDWR
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    for _ in range(256):
        name = f".{target_name}.dotf-stage-{secrets.token_hex(12)}"
        try:
            fd = os.open(name, flags, mode, dir_fd=parent_fd)
        except FileExistsError:
            continue
        try:
            os.fchmod(fd, mode)
            view = memoryview(payload)
            while view:
                written = os.write(fd, view)
                view = view[written:]
            os.fsync(fd)
            stage_stat = os.fstat(fd)
            if stage_stat.st_dev != os.fstat(parent_fd).st_dev:
                raise OSError("staging file is not on target filesystem")
            stage_digest = _regular_digest(_read_regular_fd(fd))
            expected_digest = _regular_digest(payload)
            if stage_digest != expected_digest:
                raise RuntimeError("staging content differs from validated content")
            return StagedFile(
                target,
                name,
                target_name,
                parent_fd,
                fd,
                stage_stat,
                expected_digest,
                target_fd,
                target_stat,
                target_digest,
            )
        except BaseException:
            try:
                os.unlink(name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
            os.close(fd)
            raise
    raise FileExistsError("unable to reserve staging file")


def stage_bytes(
    target: os.PathLike[str] | str,
    content: bytes | str,
    *,
    root: os.PathLike[str] | str | None = None,
    format: Format = None,
    mode: int = 0o600,
    sensitive: bool = False,
) -> StagedFile:
    """Validate and stage bytes while retaining target, parent, and stage fds."""
    _validate_regular_mode(mode, sensitive=sensitive)
    target_path = Path(target).expanduser().absolute()
    root_value = root if root is not None else target_path.parent
    base = normalize_target_root(root_value)
    target_path = assert_path_confined(root_value, target_path)
    payload = _bytes(content)
    validate_content(payload, format)
    parent_fd, target_name = open_parent_nofollow(base, target_path, create=True, mode=0o700)
    target_fd: int | None = None
    try:
        target_stat, target_fd, _existing, target_digest = _open_target(parent_fd, target_name)
        return _stage_at(
            target_path,
            target_name,
            parent_fd,
            payload,
            mode,
            target_fd,
            target_stat,
            target_digest,
        )
    except BaseException:
        if target_fd is not None:
            os.close(target_fd)
        os.close(parent_fd)
        raise


def _verify_staged(staged: StagedFile) -> None:
    stage_stat = os.fstat(staged._stage_fd)
    if not stat.S_ISREG(stage_stat.st_mode) or _identity(stage_stat) != _identity(staged._stage_stat):
        raise RuntimeError("retained staging inode changed")
    try:
        named_stage = os.stat(staged.name, dir_fd=staged.parent_fd, follow_symlinks=False)
    except FileNotFoundError as exc:
        raise RuntimeError("staging entry changed before commit") from exc
    if _identity(named_stage) != _identity(staged._stage_stat):
        raise RuntimeError("staging entry changed before commit")
    if _regular_digest(_read_regular_fd(staged._stage_fd)) != staged._stage_digest:
        raise RuntimeError("staging content changed after validation")


def _verify_original_identity(staged: StagedFile) -> None:
    """Pin the leaf identity only; late same-inode bytes are captured after quarantine."""
    _require_leaf_identity(
        staged.parent_fd,
        staged.target_name,
        staged._target_stat,
        "managed target changed before quarantine",
    )
    if staged._target_fd is None:
        return
    if _identity(os.fstat(staged._target_fd)) != _identity(staged._target_stat):
        raise RuntimeError("retained managed target changed before quarantine")


def _unique_transaction_name(parent_fd: int, target_name: str, kind: str) -> str:
    for _ in range(256):
        candidate = f".{target_name}.dotf-{kind}-{secrets.token_hex(12)}"
        try:
            os.stat(candidate, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return candidate
    raise FileExistsError(f"unable to reserve {kind} name")


def _quarantine_original(staged: StagedFile, quarantine_name: str) -> None:
    assert staged._target_stat is not None and staged._target_fd is not None
    _verify_original_identity(staged)
    os.replace(
        staged.target_name,
        quarantine_name,
        src_dir_fd=staged.parent_fd,
        dst_dir_fd=staged.parent_fd,
    )
    quarantined = os.stat(quarantine_name, dir_fd=staged.parent_fd, follow_symlinks=False)
    if _identity(quarantined) != _identity(staged._target_stat):
        raise RuntimeError("quarantined target is not the pinned old target")
    if _leaf_stat(staged.parent_fd, staged.target_name) is not None:
        raise RuntimeError("managed target live name reappeared during quarantine")
    os.fsync(staged.parent_fd)


def _quarantined_digest(staged: StagedFile, quarantine_name: str) -> str:
    assert staged._target_stat is not None and staged._target_fd is not None
    quarantined = os.stat(quarantine_name, dir_fd=staged.parent_fd, follow_symlinks=False)
    if _identity(quarantined) != _identity(staged._target_stat):
        raise RuntimeError("quarantined target changed")
    if _identity(os.fstat(staged._target_fd)) != _identity(staged._target_stat):
        raise RuntimeError("retained quarantined target changed")
    digest = _regular_digest(_read_regular_fd(staged._target_fd))
    quarantined_after = os.stat(quarantine_name, dir_fd=staged.parent_fd, follow_symlinks=False)
    if _identity(quarantined_after) != _identity(staged._target_stat):
        raise RuntimeError("quarantined target changed while hashing")
    if _identity(os.fstat(staged._target_fd)) != _identity(staged._target_stat):
        raise RuntimeError("retained quarantined target changed while hashing")
    return digest


def _verify_committed(staged: StagedFile) -> None:
    stage_stat = os.fstat(staged._stage_fd)
    if not stat.S_ISREG(stage_stat.st_mode) or _identity(stage_stat) != _identity(staged._stage_stat):
        raise RuntimeError("committed target is not the retained staging inode")
    committed = os.stat(staged.target_name, dir_fd=staged.parent_fd, follow_symlinks=False)
    if _identity(committed) != _identity(staged._stage_stat):
        raise RuntimeError("committed target is not the validated staging inode")
    if _regular_digest(_read_regular_fd(staged._stage_fd)) != staged._stage_digest:
        raise RuntimeError("committed target content differs from validated content")
    committed_after = os.stat(staged.target_name, dir_fd=staged.parent_fd, follow_symlinks=False)
    if _identity(committed_after) != _identity(staged._stage_stat):
        raise RuntimeError("committed target changed while verifying")


def _rollback_transaction(staged: StagedFile, quarantine_name: str | None) -> None:
    """Restore the exact old inode, or restore absence for a create transaction."""
    original = staged._target_stat
    if original is None:
        current = _leaf_stat(staged.parent_fd, staged.target_name)
        if current is not None and _identity(current) == _identity(staged._stage_stat):
            os.unlink(staged.target_name, dir_fd=staged.parent_fd)
        os.fsync(staged.parent_fd)
        return

    if quarantine_name is None:
        current = _leaf_stat(staged.parent_fd, staged.target_name)
        if current is None or _identity(current) != _identity(original):
            raise RuntimeError("old target changed before transaction rollback")
        os.fsync(staged.parent_fd)
        return
    try:
        quarantined = os.stat(quarantine_name, dir_fd=staged.parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        current = _leaf_stat(staged.parent_fd, staged.target_name)
        if current is not None and _identity(current) == _identity(original):
            return
        raise RuntimeError("old target quarantine disappeared during rollback")
    if _identity(quarantined) != _identity(original):
        raise RuntimeError("old target quarantine changed during rollback")

    displaced_name: str | None = None
    displaced_stat = _leaf_stat(staged.parent_fd, staged.target_name)
    if displaced_stat is not None:
        displaced_name = _unique_transaction_name(staged.parent_fd, staged.target_name, "failed")
        os.replace(
            staged.target_name,
            displaced_name,
            src_dir_fd=staged.parent_fd,
            dst_dir_fd=staged.parent_fd,
        )
    try:
        os.replace(
            quarantine_name,
            staged.target_name,
            src_dir_fd=staged.parent_fd,
            dst_dir_fd=staged.parent_fd,
        )
    except BaseException:
        if displaced_name is not None:
            os.replace(
                displaced_name,
                staged.target_name,
                src_dir_fd=staged.parent_fd,
                dst_dir_fd=staged.parent_fd,
            )
        raise

    restored = os.stat(staged.target_name, dir_fd=staged.parent_fd, follow_symlinks=False)
    if _identity(restored) != _identity(original):
        raise RuntimeError("old target was not restored exactly")
    if displaced_name is not None and displaced_stat is not None:
        displaced = os.stat(displaced_name, dir_fd=staged.parent_fd, follow_symlinks=False)
        if _identity(displaced) == _identity(staged._stage_stat):
            os.unlink(displaced_name, dir_fd=staged.parent_fd)
    os.fsync(staged.parent_fd)


def _commit_transaction(
    staged: StagedFile,
    target_path: Path,
    base: Path,
    *,
    mode: int,
    sensitive: bool,
    backup_root: os.PathLike[str] | str | None = None,
    run_id: str | None = None,
) -> Path | None:
    quarantine_name: str | None = None
    backup: Path | None = None
    old_digest: str | None = None
    try:
        _verify_original_identity(staged)
        _verify_staged(staged)
        os.fchmod(staged._stage_fd, mode)
        _verify_staged(staged)
        _require_visible_target(base, target_path, staged.parent_fd, staged._target_stat)

        if staged._target_stat is not None:
            quarantine_name = _unique_transaction_name(staged.parent_fd, staged.target_name, "quarantine")
            _quarantine_original(staged, quarantine_name)

        # Re-verify after the old leaf has been detached. A mutation injected at
        # this replace boundary must roll back through the quarantine handle.
        _verify_staged(staged)
        os.replace(
            staged.name,
            staged.target_name,
            src_dir_fd=staged.parent_fd,
            dst_dir_fd=staged.parent_fd,
        )
        _verify_committed(staged)

        if staged._target_stat is not None:
            assert quarantine_name is not None
            old_digest = _quarantined_digest(staged, quarantine_name)
            if backup_root is not None:
                if not run_id:
                    raise ValueError("run_id is required when backup_root is set")
                assert staged._target_fd is not None
                backup = backup_target_at(
                    target_path,
                    backup_root,
                    run_id,
                    base,
                    source_parent_fd=staged.parent_fd,
                    source_name=quarantine_name,
                    source_stat=staged._target_stat,
                    source_fd=staged._target_fd,
                    source_digest=old_digest,
                    sensitive=sensitive,
                )
                if _quarantined_digest(staged, quarantine_name) != old_digest:
                    raise RuntimeError("old target changed after backup")

        # Final decision checks both the visible confinement path and the exact
        # committed inode/content after every hook that can fail or mutate data.
        _require_visible_target(base, target_path, staged.parent_fd, staged._stage_stat)
        _verify_committed(staged)

        if staged._target_stat is not None:
            assert quarantine_name is not None and old_digest is not None
            if _quarantined_digest(staged, quarantine_name) != old_digest:
                raise RuntimeError("old target changed before quarantine cleanup")
            quarantined = os.stat(quarantine_name, dir_fd=staged.parent_fd, follow_symlinks=False)
            if _identity(quarantined) != _identity(staged._target_stat):
                raise RuntimeError("old target quarantine changed before cleanup")
            os.unlink(quarantine_name, dir_fd=staged.parent_fd)
            quarantine_name = None
        os.fsync(staged.parent_fd)
    except BaseException as error:
        try:
            _rollback_transaction(staged, quarantine_name)
        except BaseException as rollback_error:
            rollback_error.add_note(f"original atomic replacement failure: {error!r}")
            staged.cleanup()
            raise rollback_error from error
        if backup is not None:
            backup_matches_restored = False
            if old_digest is not None and staged._target_fd is not None:
                try:
                    backup_matches_restored = (
                        _regular_digest(_read_regular_fd(staged._target_fd)) == old_digest
                    )
                except OSError:
                    backup_matches_restored = False
            if not backup_matches_restored:
                try:
                    discard_backup_candidate(backup, base)
                except BaseException as cleanup_error:
                    error.add_note(f"stale backup cleanup failed: {cleanup_error!r}")
        staged.cleanup()
        raise
    staged._committed()
    return backup


def atomic_replace(
    staged: StagedFile,
    target: os.PathLike[str] | str,
    *,
    root: os.PathLike[str] | str | None = None,
    mode: int = 0o600,
    sensitive: bool = False,
) -> None:
    """Commit the validated stage and restore the quarantined old target on failure."""
    if not isinstance(staged, StagedFile):
        raise TypeError("atomic_replace requires the StagedFile returned by stage_bytes")
    _validate_regular_mode(mode, sensitive=sensitive)
    target_path = Path(target).expanduser().absolute()
    root_value = root if root is not None else target_path.parent
    base = normalize_target_root(root_value)
    target_path = assert_path_confined(root_value, target_path)
    if target_path != staged.target:
        staged.cleanup()
        raise ValueError("staged file belongs to a different target")
    _commit_transaction(staged, target_path, base, mode=mode, sensitive=sensitive)


def _verify_unchanged_final(
    base: Path,
    target_path: Path,
    parent_fd: int,
    target_name: str,
    target_fd: int,
    target_stat: os.stat_result,
    expected_payload: bytes,
    format: Format,
) -> None:
    """Validate the exact bytes named by the target at the unchanged decision."""
    _require_visible_target(base, target_path, parent_fd, target_stat)
    if _identity(os.fstat(target_fd)) != _identity(target_stat):
        raise RuntimeError("retained managed target changed before unchanged decision")
    final_payload = _read_regular_fd(target_fd)
    _require_leaf_identity(parent_fd, target_name, target_stat, "managed target changed before unchanged decision")
    validate_content(final_payload, format)
    if final_payload != expected_payload or _regular_digest(final_payload) != _regular_digest(expected_payload):
        raise RuntimeError("managed target content changed before unchanged decision")
    final_payload_after = _read_regular_fd(target_fd)
    if final_payload_after != final_payload:
        raise RuntimeError("managed target content changed during unchanged decision")
    if _identity(os.fstat(target_fd)) != _identity(target_stat):
        raise RuntimeError("retained managed target changed during unchanged decision")
    _require_leaf_identity(parent_fd, target_name, target_stat, "managed target changed during unchanged decision")


def _enforce_unchanged_sensitive_mode(
    base: Path,
    target_path: Path,
    parent_fd: int,
    target_name: str,
    target_fd: int,
    target_stat: os.stat_result,
    expected_payload: bytes,
    format: Format,
    mode: int,
) -> None:
    """Secure the exact unchanged inode without replacement or backup."""
    original_mode = stat.S_IMODE(os.fstat(target_fd).st_mode)
    if original_mode == mode:
        return
    try:
        os.fchmod(target_fd, mode)
        os.fsync(target_fd)
        if stat.S_IMODE(os.fstat(target_fd).st_mode) != mode:
            raise RuntimeError("sensitive unchanged target mode was not applied")
        _verify_unchanged_final(
            base,
            target_path,
            parent_fd,
            target_name,
            target_fd,
            target_stat,
            expected_payload,
            format,
        )
    except BaseException as error:
        try:
            if stat.S_IMODE(os.fstat(target_fd).st_mode) != original_mode:
                os.fchmod(target_fd, original_mode)
                os.fsync(target_fd)
            if stat.S_IMODE(os.fstat(target_fd).st_mode) != original_mode:
                raise RuntimeError("sensitive unchanged mode rollback failed")
            _require_leaf_identity(
                parent_fd,
                target_name,
                target_stat,
                "managed target changed during sensitive mode rollback",
            )
        except BaseException as rollback_error:
            rollback_error.add_note(f"original sensitive mode failure: {error!r}")
            raise rollback_error from error
        raise


def atomic_write(
    target: os.PathLike[str] | str,
    content: bytes | str,
    *,
    root: os.PathLike[str] | str | None = None,
    format: Format = None,
    mode: int = 0o600,
    backup_root: os.PathLike[str] | str | None = None,
    run_id: str | None = None,
    sensitive: bool = False,
) -> AtomicWriteResult:
    """Validate, stage, quarantine the old leaf, then commit or roll back exactly."""
    _validate_regular_mode(mode, sensitive=sensitive)
    target_path = Path(target).expanduser().absolute()
    root_value = root if root is not None else target_path.parent
    base = normalize_target_root(root_value)
    target_path = assert_path_confined(root_value, target_path)
    payload = _bytes(content)
    validate_content(payload, format)

    parent_fd, target_name = open_parent_nofollow(base, target_path, create=True, mode=0o700)
    target_fd: int | None = None
    try:
        existing, target_fd, existing_payload, target_digest = _open_target(parent_fd, target_name)
        if existing_payload == payload:
            assert existing is not None and target_fd is not None
            _verify_unchanged_final(
                base,
                target_path,
                parent_fd,
                target_name,
                target_fd,
                existing,
                payload,
                format,
            )
            if stat.S_IMODE(os.fstat(target_fd).st_mode) != mode:
                _enforce_unchanged_sensitive_mode(
                    base,
                    target_path,
                    parent_fd,
                    target_name,
                    target_fd,
                    existing,
                    payload,
                    format,
                    mode,
                )
            os.close(target_fd)
            os.close(parent_fd)
            return AtomicWriteResult("unchanged", target_path)
        if existing is not None and backup_root is not None and not run_id:
            raise ValueError("run_id is required when backup_root is set")
        staged = _stage_at(
            target_path,
            target_name,
            parent_fd,
            payload,
            mode,
            target_fd,
            existing,
            target_digest,
        )
        target_fd = None  # ownership transferred to staged
    except BaseException:
        if target_fd is not None:
            os.close(target_fd)
        os.close(parent_fd)
        raise

    backup = _commit_transaction(
        staged,
        target_path,
        base,
        mode=mode,
        sensitive=sensitive,
        backup_root=backup_root,
        run_id=run_id,
    )
    return AtomicWriteResult("changed", target_path, backup)
