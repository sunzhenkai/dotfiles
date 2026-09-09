"""Restricted, run-scoped, descriptor-relative backups."""

from __future__ import annotations

import errno
import hashlib
import os
import secrets
import stat
import time
from pathlib import Path

from .paths import (
    PathBoundaryError,
    assert_path_confined,
    normalize_target_root,
    open_directory_nofollow,
    open_parent_nofollow,
)

_DIR_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_DIRECTORY", 0)
)
_FILE_FLAGS = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)


def generate_run_id() -> str:
    """Return a process- and collision-resistant, filesystem-safe run id."""
    return f"{time.time_ns():020d}-{os.getpid()}-{secrets.token_hex(8)}"


def _validate_run_id(run_id: str) -> str:
    if not run_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for c in run_id):
        raise ValueError("run_id contains unsafe characters")
    if run_id in (".", ".."):
        raise ValueError("invalid run_id")
    return run_id


def target_relative_path(target_root: os.PathLike[str] | str, target: os.PathLike[str] | str) -> Path:
    root = normalize_target_root(target_root)
    confined = assert_path_confined(root, target)
    relative = confined.relative_to(root)
    if str(relative) == ".":
        raise ValueError("cannot back up the target root itself")
    return relative


def _identity(item: os.stat_result) -> tuple[int, int, int]:
    return item.st_dev, item.st_ino, stat.S_IFMT(item.st_mode)


def _require_identity(current: os.stat_result, expected: os.stat_result, message: str) -> None:
    if _identity(current) != _identity(expected):
        raise RuntimeError(message)


def _lstat_at(parent_fd: int, name: str) -> os.stat_result:
    return os.stat(name, dir_fd=parent_fd, follow_symlinks=False)


def _open_checked(parent_fd: int, name: str, expected: os.stat_result, *, directory: bool) -> int:
    try:
        fd = os.open(name, _DIR_FLAGS if directory else _FILE_FLAGS, dir_fd=parent_fd)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise PathBoundaryError(errno.ELOOP, "source entry changed to an unsafe link", name) from exc
        raise
    try:
        _require_identity(os.fstat(fd), expected, "source entry changed while opening")
    except BaseException:
        os.close(fd)
        raise
    return fd


def _readlink_checked(parent_fd: int, name: str, expected: os.stat_result) -> str:
    value = os.readlink(name, dir_fd=parent_fd)
    _require_identity(_lstat_at(parent_fd, name), expected, "source symlink changed while reading")
    return value


def _hash_regular_fd(fd: int, digest: "hashlib._Hash") -> None:
    os.lseek(fd, 0, os.SEEK_SET)
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            break
        digest.update(chunk)
    os.lseek(fd, 0, os.SEEK_SET)


def _hash_directory_fd(fd: int, digest: "hashlib._Hash") -> None:
    for name in sorted(os.listdir(fd)):
        item = _lstat_at(fd, name)
        digest.update(os.fsencode(name) + b"\0" + str(stat.S_IFMT(item.st_mode)).encode("ascii") + b"\0")
        if stat.S_ISREG(item.st_mode):
            child_fd = _open_checked(fd, name, item, directory=False)
            try:
                _hash_regular_fd(child_fd, digest)
                _require_identity(_lstat_at(fd, name), item, "source file changed while hashing")
            finally:
                os.close(child_fd)
        elif stat.S_ISDIR(item.st_mode):
            child_fd = _open_checked(fd, name, item, directory=True)
            try:
                _hash_directory_fd(child_fd, digest)
                _require_identity(_lstat_at(fd, name), item, "source directory changed while hashing")
            finally:
                os.close(child_fd)
        elif stat.S_ISLNK(item.st_mode):
            digest.update(os.fsencode(_readlink_checked(fd, name, item)))
        else:
            raise ValueError("unsupported backup target type")


def _open_source(parent_fd: int, name: str, item: os.stat_result) -> tuple[int | None, str | None]:
    if stat.S_ISREG(item.st_mode):
        return _open_checked(parent_fd, name, item, directory=False), None
    if stat.S_ISDIR(item.st_mode):
        return _open_checked(parent_fd, name, item, directory=True), None
    if stat.S_ISLNK(item.st_mode):
        return None, _readlink_checked(parent_fd, name, item)
    raise ValueError("unsupported backup target type")


def _source_digest(item: os.stat_result, source_fd: int | None, link_value: str | None) -> str:
    digest = hashlib.sha256()
    if stat.S_ISREG(item.st_mode):
        assert source_fd is not None
        digest.update(b"regular\0")
        _hash_regular_fd(source_fd, digest)
    elif stat.S_ISDIR(item.st_mode):
        assert source_fd is not None
        digest.update(b"directory\0")
        _hash_directory_fd(source_fd, digest)
    elif stat.S_ISLNK(item.st_mode):
        assert link_value is not None
        digest.update(b"symlink\0" + os.fsencode(link_value))
    else:  # protected by _open_source
        raise ValueError("unsupported backup target type")
    return digest.hexdigest()


def _stable_source_digest(
    parent_fd: int,
    name: str,
    item: os.stat_result,
    source_fd: int | None,
    link_value: str | None,
    message: str,
) -> str:
    """Hash twice around identity checks so in-place changes cannot pass as stable."""
    _require_identity(_lstat_at(parent_fd, name), item, message)
    if source_fd is not None:
        _require_identity(os.fstat(source_fd), item, message)
    first = _source_digest(item, source_fd, link_value)
    _require_identity(_lstat_at(parent_fd, name), item, message)
    second = _source_digest(item, source_fd, link_value)
    _require_identity(_lstat_at(parent_fd, name), item, message)
    if source_fd is not None:
        _require_identity(os.fstat(source_fd), item, message)
    if first != second:
        raise RuntimeError(message)
    return first


def _inspect_source(
    source: os.PathLike[str] | str,
    target_root: os.PathLike[str] | str,
) -> tuple[Path, int, str, os.stat_result, int | None, str | None, str]:
    root = normalize_target_root(target_root)
    source_path = assert_path_confined(root, Path(source).expanduser().absolute())
    if source_path == root:
        raise ValueError("cannot back up the target root itself")
    parent_fd, name = open_parent_nofollow(root, source_path)
    try:
        item = _lstat_at(parent_fd, name)
        source_fd, link_value = _open_source(parent_fd, name, item)
        try:
            digest = _stable_source_digest(
                parent_fd,
                name,
                item,
                source_fd,
                link_value,
                "source changed while hashing",
            )
        except BaseException:
            if source_fd is not None:
                os.close(source_fd)
            raise
        return source_path, parent_fd, name, item, source_fd, link_value, digest
    except BaseException:
        os.close(parent_fd)
        raise


def backup_destination(
    source: os.PathLike[str] | str,
    backup_root: os.PathLike[str] | str,
    run_id: str,
    target_root: os.PathLike[str] | str,
) -> Path:
    """Build (but do not reserve) <run-id>/<relative-target>.<hash>."""
    run_id = _validate_run_id(run_id)
    source_path, parent_fd, _name, _item, source_fd, _link, digest = _inspect_source(source, target_root)
    try:
        relative = target_relative_path(target_root, source_path)
        base = Path(backup_root).expanduser().absolute() / run_id / relative.parent / f"{relative.name}.{digest[:16]}"
        for number in range(10000):
            candidate = _unique_candidate(base, number)
            if not os.path.lexists(candidate):
                return candidate
        raise FileExistsError("unable to find unique backup destination")
    finally:
        if source_fd is not None:
            os.close(source_fd)
        os.close(parent_fd)


def _unique_candidate(base: Path, number: int) -> Path:
    return base if number == 0 else base.with_name(f"{base.name}.{number}")


def _open_private_dirs(root_fd: int, parts: tuple[str, ...]) -> int:
    current = os.dup(root_fd)
    try:
        for part in parts:
            try:
                os.mkdir(part, mode=0o700, dir_fd=current)
            except FileExistsError:
                pass
            child = os.open(part, _DIR_FLAGS, dir_fd=current)
            os.fchmod(child, 0o700)
            os.fsync(current)
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def _copy_regular_fd(source_fd: int, destination_parent_fd: int, name: str, mode: int) -> None:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    destination_fd = os.open(name, flags, mode, dir_fd=destination_parent_fd)
    created = os.fstat(destination_fd)
    try:
        os.fchmod(destination_fd, mode)
        os.lseek(source_fd, 0, os.SEEK_SET)
        while True:
            chunk = os.read(source_fd, 1024 * 1024)
            if not chunk:
                break
            view = memoryview(chunk)
            while view:
                written = os.write(destination_fd, view)
                view = view[written:]
        os.fsync(destination_fd)
        os.lseek(source_fd, 0, os.SEEK_SET)
    except BaseException:
        os.close(destination_fd)
        try:
            _require_identity(_lstat_at(destination_parent_fd, name), created, "backup destination changed during cleanup")
            os.unlink(name, dir_fd=destination_parent_fd)
        except FileNotFoundError:
            pass
        raise
    else:
        os.close(destination_fd)


def _copy_directory_fd(source_fd: int, destination_fd: int, file_mode: int) -> None:
    for name in sorted(os.listdir(source_fd)):
        item = _lstat_at(source_fd, name)
        if stat.S_ISREG(item.st_mode):
            child_source = _open_checked(source_fd, name, item, directory=False)
            try:
                _copy_regular_fd(child_source, destination_fd, name, file_mode)
                _require_identity(_lstat_at(source_fd, name), item, "source file changed while copying")
            finally:
                os.close(child_source)
        elif stat.S_ISDIR(item.st_mode):
            child_source = _open_checked(source_fd, name, item, directory=True)
            try:
                os.mkdir(name, mode=0o700, dir_fd=destination_fd)
                child_destination = os.open(name, _DIR_FLAGS, dir_fd=destination_fd)
                try:
                    os.fchmod(child_destination, 0o700)
                    _copy_directory_fd(child_source, child_destination, file_mode)
                    os.fsync(child_destination)
                finally:
                    os.close(child_destination)
                _require_identity(_lstat_at(source_fd, name), item, "source directory changed while copying")
            finally:
                os.close(child_source)
        elif stat.S_ISLNK(item.st_mode):
            os.symlink(_readlink_checked(source_fd, name, item), name, dir_fd=destination_fd)
        else:
            raise ValueError("unsupported backup target type")
    os.fsync(destination_fd)


def _remove_directory_contents_fd(directory_fd: int) -> None:
    """Remove a pinned tree by quarantining each child before recursive cleanup."""
    for name in os.listdir(directory_fd):
        item = _lstat_at(directory_fd, name)
        quarantine_name = _unique_quarantine_name(directory_fd, name)
        _quarantine_source(directory_fd, name, quarantine_name, item)
        try:
            if stat.S_ISDIR(item.st_mode):
                child_fd = _open_checked(directory_fd, quarantine_name, item, directory=True)
                try:
                    _remove_directory_contents_fd(child_fd)
                finally:
                    os.close(child_fd)
                _require_identity(
                    _lstat_at(directory_fd, quarantine_name),
                    item,
                    "quarantined directory entry changed before removal",
                )
                os.rmdir(quarantine_name, dir_fd=directory_fd)
            else:
                _require_identity(
                    _lstat_at(directory_fd, quarantine_name),
                    item,
                    "quarantined source entry changed before removal",
                )
                os.unlink(quarantine_name, dir_fd=directory_fd)
        except BaseException:
            _restore_quarantine(directory_fd, name, quarantine_name, item)
            raise


def _cleanup_created_directory(parent_fd: int, name: str, directory_fd: int, created: os.stat_result) -> None:
    try:
        _remove_directory_contents_fd(directory_fd)
        _require_identity(_lstat_at(parent_fd, name), created, "backup destination changed during cleanup")
        os.rmdir(name, dir_fd=parent_fd)
    except FileNotFoundError:
        pass


def _cleanup_candidate(parent_fd: int, name: str, item: os.stat_result) -> None:
    try:
        _require_identity(_lstat_at(parent_fd, name), item, "backup destination changed during cleanup")
        if stat.S_ISDIR(item.st_mode):
            directory_fd = _open_checked(parent_fd, name, item, directory=True)
            try:
                _cleanup_created_directory(parent_fd, name, directory_fd, item)
            finally:
                os.close(directory_fd)
        else:
            os.unlink(name, dir_fd=parent_fd)
    except FileNotFoundError:
        pass


def _copy_to_candidate(
    item: os.stat_result,
    source_fd: int | None,
    link_value: str | None,
    destination_parent_fd: int,
    name: str,
    file_mode: int,
) -> None:
    if stat.S_ISREG(item.st_mode):
        assert source_fd is not None
        _copy_regular_fd(source_fd, destination_parent_fd, name, file_mode)
    elif stat.S_ISLNK(item.st_mode):
        assert link_value is not None
        os.symlink(link_value, name, dir_fd=destination_parent_fd)
    elif stat.S_ISDIR(item.st_mode):
        assert source_fd is not None
        os.mkdir(name, mode=0o700, dir_fd=destination_parent_fd)
        destination_fd = os.open(name, _DIR_FLAGS, dir_fd=destination_parent_fd)
        created = os.fstat(destination_fd)
        try:
            os.fchmod(destination_fd, 0o700)
            try:
                _copy_directory_fd(source_fd, destination_fd, file_mode)
            except BaseException:
                _cleanup_created_directory(destination_parent_fd, name, destination_fd, created)
                raise
        finally:
            os.close(destination_fd)
    else:
        raise ValueError("unsupported backup target type")
    os.fsync(destination_parent_fd)


def _candidate_digest(
    destination_parent_fd: int,
    name: str,
    expected_type: os.stat_result,
) -> tuple[os.stat_result, str]:
    item = _lstat_at(destination_parent_fd, name)
    if stat.S_IFMT(item.st_mode) != stat.S_IFMT(expected_type.st_mode):
        raise RuntimeError("backup destination type differs from source")
    destination_fd, link_value = _open_source(destination_parent_fd, name, item)
    try:
        digest = _stable_source_digest(
            destination_parent_fd,
            name,
            item,
            destination_fd,
            link_value,
            "backup destination changed while verifying",
        )
        return item, digest
    finally:
        if destination_fd is not None:
            os.close(destination_fd)


def _unique_quarantine_name(parent_fd: int, source_name: str) -> str:
    for _ in range(256):
        candidate = f".{source_name}.dotf-quarantine-{secrets.token_hex(12)}"
        try:
            _lstat_at(parent_fd, candidate)
        except FileNotFoundError:
            return candidate
    raise FileExistsError("unable to reserve source quarantine name")


def _quarantine_source(
    source_parent_fd: int,
    source_name: str,
    quarantine_name: str,
    original: os.stat_result,
) -> None:
    """Atomically detach the exact pinned leaf from its live name."""
    _require_identity(_lstat_at(source_parent_fd, source_name), original, "source changed before quarantine")
    os.replace(
        source_name,
        quarantine_name,
        src_dir_fd=source_parent_fd,
        dst_dir_fd=source_parent_fd,
    )
    _require_identity(
        _lstat_at(source_parent_fd, quarantine_name),
        original,
        "source changed while entering quarantine",
    )
    try:
        _lstat_at(source_parent_fd, source_name)
    except FileNotFoundError:
        pass
    else:
        raise RuntimeError("source live name reappeared during quarantine")
    os.fsync(source_parent_fd)


def _restore_quarantine(
    source_parent_fd: int,
    source_name: str,
    quarantine_name: str,
    original: os.stat_result,
) -> None:
    """Restore quarantine without overwriting a concurrently-created live leaf."""
    _require_identity(
        _lstat_at(source_parent_fd, quarantine_name),
        original,
        "quarantined source changed before restore",
    )
    displaced_name: str | None = None
    try:
        _lstat_at(source_parent_fd, source_name)
    except FileNotFoundError:
        pass
    else:
        displaced_name = _unique_quarantine_name(source_parent_fd, f"{source_name}-conflict")
        os.replace(
            source_name,
            displaced_name,
            src_dir_fd=source_parent_fd,
            dst_dir_fd=source_parent_fd,
        )
    try:
        os.replace(
            quarantine_name,
            source_name,
            src_dir_fd=source_parent_fd,
            dst_dir_fd=source_parent_fd,
        )
    except BaseException:
        if displaced_name is not None:
            os.replace(
                displaced_name,
                source_name,
                src_dir_fd=source_parent_fd,
                dst_dir_fd=source_parent_fd,
            )
        raise
    _require_identity(_lstat_at(source_parent_fd, source_name), original, "source restore failed")
    os.fsync(source_parent_fd)


def _require_live_name_absent(source_parent_fd: int, source_name: str) -> None:
    try:
        _lstat_at(source_parent_fd, source_name)
    except FileNotFoundError:
        return
    raise RuntimeError("source live name reappeared during quarantine")


def _reserve_backup_candidate(
    destination_parent_fd: int,
    name: str,
    source: os.stat_result,
) -> os.stat_result:
    """Reserve a destination without exposing an overwrite race to peer backups."""
    if stat.S_ISDIR(source.st_mode):
        os.mkdir(name, mode=0o700, dir_fd=destination_parent_fd)
    else:
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        fd = os.open(name, flags, 0o600, dir_fd=destination_parent_fd)
        try:
            os.fchmod(fd, 0o600)
            os.fsync(fd)
        finally:
            os.close(fd)
    reserved = _lstat_at(destination_parent_fd, name)
    os.fsync(destination_parent_fd)
    return reserved


class _ModeRollback:
    """Retain exact regular-file/directory inodes until final validation succeeds."""

    __slots__ = ("_entries", "_attempted", "_active")

    def __init__(self, entries: list[tuple[int, int, int]]) -> None:
        self._entries = entries
        self._attempted: list[tuple[int, int, int]] = []
        self._active = True

    def mark_attempted(self, entry: tuple[int, int, int]) -> None:
        self._attempted.append(entry)

    def close(self) -> None:
        if not self._active:
            return
        for fd, _original_mode, _final_mode in self._entries:
            os.close(fd)
        self._active = False

    def rollback(self) -> None:
        """Restore every mode that may have changed, then release retained fds."""
        if not self._active:
            return
        failures: list[BaseException] = []
        try:
            for fd, original_mode, _final_mode in reversed(self._attempted):
                try:
                    if stat.S_IMODE(os.fstat(fd).st_mode) != original_mode:
                        os.fchmod(fd, original_mode)
                        os.fsync(fd)
                    if stat.S_IMODE(os.fstat(fd).st_mode) != original_mode:
                        raise RuntimeError("backup mode rollback did not restore original mode")
                except BaseException as error:
                    failures.append(error)
        finally:
            self.close()
        if failures:
            for extra in failures[1:]:
                failures[0].add_note(f"additional backup mode rollback failure: {extra!r}")
            raise failures[0]


def _collect_backup_mode_entries(
    parent_fd: int,
    name: str,
    expected: os.stat_result,
    file_mode: int,
    entries: list[tuple[int, int, int]],
) -> None:
    """Pin every chmod-capable inode without traversing symbolic links."""
    _require_identity(_lstat_at(parent_fd, name), expected, "backup entry changed before applying modes")
    if stat.S_ISREG(expected.st_mode):
        fd = _open_checked(parent_fd, name, expected, directory=False)
        entries.append((fd, stat.S_IMODE(os.fstat(fd).st_mode), file_mode))
    elif stat.S_ISDIR(expected.st_mode):
        directory_fd = _open_checked(parent_fd, name, expected, directory=True)
        retained = False
        try:
            for child_name in sorted(os.listdir(directory_fd)):
                child = _lstat_at(directory_fd, child_name)
                _collect_backup_mode_entries(directory_fd, child_name, child, file_mode, entries)
            entries.append((directory_fd, stat.S_IMODE(os.fstat(directory_fd).st_mode), 0o700))
            retained = True
        finally:
            if not retained:
                os.close(directory_fd)
    elif stat.S_ISLNK(expected.st_mode):
        _readlink_checked(parent_fd, name, expected)
    else:
        raise ValueError("unsupported backup target type")
    _require_identity(_lstat_at(parent_fd, name), expected, "backup entry changed while pinning modes")


def _apply_backup_modes(
    parent_fd: int,
    name: str,
    expected: os.stat_result,
    file_mode: int,
) -> _ModeRollback:
    """Apply private modes and retain an exact metadata rollback transaction."""
    entries: list[tuple[int, int, int]] = []
    try:
        _collect_backup_mode_entries(parent_fd, name, expected, file_mode, entries)
    except BaseException:
        for fd, _original_mode, _final_mode in entries:
            os.close(fd)
        raise

    rollback = _ModeRollback(entries)
    try:
        for entry in entries:
            fd, _original_mode, final_mode = entry
            if stat.S_IMODE(os.fstat(fd).st_mode) == final_mode:
                continue
            rollback.mark_attempted(entry)
            os.fchmod(fd, final_mode)
            os.fsync(fd)
            if stat.S_IMODE(os.fstat(fd).st_mode) != final_mode:
                raise RuntimeError("backup mode application did not set final mode")
        _require_identity(
            _lstat_at(parent_fd, name),
            expected,
            "backup entry changed while applying modes",
        )
    except BaseException as error:
        try:
            rollback.rollback()
        except BaseException as rollback_error:
            rollback_error.add_note(f"original backup mode failure: {error!r}")
            raise rollback_error from error
        raise
    return rollback


def _restore_moved_candidate(
    destination_parent_fd: int,
    candidate_name: str,
    source_parent_fd: int,
    quarantine_name: str,
    original: os.stat_result,
) -> None:
    """Atomically return the exact moved entry to its original quarantine name."""
    _require_identity(
        _lstat_at(destination_parent_fd, candidate_name),
        original,
        "moved backup entry changed before rollback",
    )
    try:
        _lstat_at(source_parent_fd, quarantine_name)
    except FileNotFoundError:
        pass
    else:
        raise RuntimeError("source quarantine name reappeared before rollback")
    os.replace(
        candidate_name,
        quarantine_name,
        src_dir_fd=destination_parent_fd,
        dst_dir_fd=source_parent_fd,
    )
    _require_identity(
        _lstat_at(source_parent_fd, quarantine_name),
        original,
        "moved backup entry changed during rollback",
    )
    os.fsync(destination_parent_fd)
    os.fsync(source_parent_fd)


def _backup_inspected(
    source_path: Path,
    backup_root: os.PathLike[str] | str,
    run_id: str,
    source_root: Path,
    source_parent_fd: int,
    source_name: str,
    item: os.stat_result,
    source_fd: int | None,
    link_value: str | None,
    digest: str,
    *,
    remove_source: bool,
) -> Path:
    backup_fd: int | None = None
    destination_parent_fd: int | None = None
    quarantine_name: str | None = None
    physical_name = source_name
    try:
        if remove_source:
            quarantine_name = _unique_quarantine_name(source_parent_fd, source_name)
            _quarantine_source(source_parent_fd, source_name, quarantine_name, item)
            physical_name = quarantine_name

        current_digest = _stable_source_digest(
            source_parent_fd,
            physical_name,
            item,
            source_fd,
            link_value,
            "source changed before backup",
        )
        if current_digest != digest:
            raise RuntimeError("source content changed before backup")

        backup_base = assert_path_confined(source_root, Path(backup_root).expanduser().absolute())
        backup_fd = open_directory_nofollow(source_root, backup_base, create=True, mode=0o700)
        os.fchmod(backup_fd, 0o700)

        relative = target_relative_path(source_root, source_path)
        parent_parts = (run_id, *relative.parent.parts) if str(relative.parent) != "." else (run_id,)
        destination_parent_fd = _open_private_dirs(backup_fd, parent_parts)
        desired_name = f"{relative.name}.{digest[:16]}"
        destination: Path | None = None

        if remove_source:
            assert quarantine_name is not None
            for number in range(10000):
                candidate_name = desired_name if number == 0 else f"{desired_name}.{number}"
                try:
                    reserved = _reserve_backup_candidate(destination_parent_fd, candidate_name, item)
                except FileExistsError:
                    continue

                destination_holds_source = False
                mode_rollback: _ModeRollback | None = None
                try:
                    if os.fstat(source_parent_fd).st_dev != os.fstat(destination_parent_fd).st_dev:
                        raise OSError(errno.EXDEV, "backup destination is on a different filesystem")
                    _require_identity(
                        _lstat_at(source_parent_fd, quarantine_name),
                        item,
                        "quarantined source changed before backup move",
                    )
                    _require_identity(
                        _lstat_at(destination_parent_fd, candidate_name),
                        reserved,
                        "backup destination reservation changed",
                    )
                    source_before_move = _stable_source_digest(
                        source_parent_fd,
                        quarantine_name,
                        item,
                        source_fd,
                        link_value,
                        "source changed before backup move",
                    )
                    if source_before_move != digest:
                        raise RuntimeError("source content changed before backup move")
                    _require_live_name_absent(source_parent_fd, source_name)

                    os.replace(
                        quarantine_name,
                        candidate_name,
                        src_dir_fd=source_parent_fd,
                        dst_dir_fd=destination_parent_fd,
                    )
                    destination_holds_source = True
                    os.fsync(source_parent_fd)
                    os.fsync(destination_parent_fd)

                    _require_identity(
                        _lstat_at(destination_parent_fd, candidate_name),
                        item,
                        "quarantined source changed during backup move",
                    )
                    try:
                        _lstat_at(source_parent_fd, quarantine_name)
                    except FileNotFoundError:
                        pass
                    else:
                        raise RuntimeError("source quarantine name reappeared after backup move")
                    _require_live_name_absent(source_parent_fd, source_name)

                    _verified_item, destination_digest = _candidate_digest(
                        destination_parent_fd,
                        candidate_name,
                        item,
                    )
                    if destination_digest != digest:
                        raise RuntimeError("backup destination digest differs from source digest")
                    mode_rollback = _apply_backup_modes(
                        destination_parent_fd,
                        candidate_name,
                        item,
                        0o600,
                    )
                    _verified_item, final_digest = _candidate_digest(
                        destination_parent_fd,
                        candidate_name,
                        item,
                    )
                    if final_digest != digest:
                        raise RuntimeError("source content changed while finalizing backup")
                    _require_live_name_absent(source_parent_fd, source_name)
                    os.fsync(destination_parent_fd)
                except BaseException as error:
                    mode_rollback_error: BaseException | None = None
                    if mode_rollback is not None:
                        try:
                            mode_rollback.rollback()
                        except BaseException as rollback_error:
                            mode_rollback_error = rollback_error
                    if destination_holds_source:
                        try:
                            _restore_moved_candidate(
                                destination_parent_fd,
                                candidate_name,
                                source_parent_fd,
                                quarantine_name,
                                item,
                            )
                        except BaseException as move_restore_error:
                            move_restore_error.add_note(f"original backup failure: {error!r}")
                            if mode_rollback_error is not None:
                                move_restore_error.add_note(
                                    f"backup mode rollback failure: {mode_rollback_error!r}"
                                )
                            raise move_restore_error from error
                    else:
                        _cleanup_candidate(destination_parent_fd, candidate_name, reserved)
                        os.fsync(destination_parent_fd)
                    if mode_rollback_error is not None:
                        mode_rollback_error.add_note(f"original backup failure: {error!r}")
                        raise mode_rollback_error from error
                    raise
                else:
                    if mode_rollback is not None:
                        mode_rollback.close()

                destination = backup_base.joinpath(*parent_parts, candidate_name)
                quarantine_name = None
                break
        else:
            for number in range(10000):
                candidate_name = desired_name if number == 0 else f"{desired_name}.{number}"
                try:
                    _copy_to_candidate(item, source_fd, link_value, destination_parent_fd, candidate_name, 0o600)
                except FileExistsError:
                    continue

                candidate_item = _lstat_at(destination_parent_fd, candidate_name)
                try:
                    source_after = _stable_source_digest(
                        source_parent_fd,
                        source_name,
                        item,
                        source_fd,
                        link_value,
                        "source changed while backing up",
                    )
                    _verified_item, destination_digest = _candidate_digest(
                        destination_parent_fd,
                        candidate_name,
                        item,
                    )
                    if source_after != digest:
                        raise RuntimeError("source content changed while backing up")
                    if destination_digest != digest:
                        raise RuntimeError("backup destination digest differs from source digest")
                except BaseException:
                    _cleanup_candidate(destination_parent_fd, candidate_name, candidate_item)
                    raise

                destination = backup_base.joinpath(*parent_parts, candidate_name)
                break

        if destination is None:
            raise FileExistsError("unable to reserve unique backup destination")
        return destination
    except BaseException as error:
        if quarantine_name is not None:
            try:
                _restore_quarantine(source_parent_fd, source_name, quarantine_name, item)
            except BaseException as restore_error:
                restore_error.add_note(f"original backup failure: {error!r}")
                raise restore_error from error
        raise
    finally:
        if destination_parent_fd is not None:
            os.close(destination_parent_fd)
        if backup_fd is not None:
            os.close(backup_fd)


def discard_backup_candidate(
    backup: os.PathLike[str] | str,
    target_root: os.PathLike[str] | str,
) -> None:
    """Remove one known backup candidate without following any path component."""
    source_root = normalize_target_root(target_root)
    backup_path = assert_path_confined(source_root, Path(backup).expanduser().absolute())
    if backup_path == source_root:
        raise ValueError("cannot discard the target root")
    parent_fd, name = open_parent_nofollow(source_root, backup_path)
    try:
        item = _lstat_at(parent_fd, name)
        _cleanup_candidate(parent_fd, name, item)
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def backup_target_at(
    source: os.PathLike[str] | str,
    backup_root: os.PathLike[str] | str,
    run_id: str,
    target_root: os.PathLike[str] | str,
    *,
    source_parent_fd: int,
    source_name: str,
    source_stat: os.stat_result,
    source_fd: int,
    source_digest: str,
    sensitive: bool = False,
) -> Path:
    """Back up a regular leaf using caller-retained parent and source fds only."""
    del sensitive  # all backup regular files are private, including non-sensitive ones
    run_id = _validate_run_id(run_id)
    source_root = normalize_target_root(target_root)
    source_path = assert_path_confined(source_root, Path(source).expanduser().absolute())
    if source_path == source_root:
        raise ValueError("pinned backup source cannot be the target root")
    if not source_name or "/" in source_name or source_name in (".", ".."):
        raise ValueError("invalid pinned backup source leaf")
    if not stat.S_ISREG(source_stat.st_mode):
        raise ValueError("pinned atomic backup source is not a regular file")
    _require_identity(os.fstat(source_fd), source_stat, "pinned backup source changed")
    return _backup_inspected(
        source_path,
        backup_root,
        run_id,
        source_root,
        source_parent_fd,
        source_name,
        source_stat,
        source_fd,
        None,
        source_digest,
        remove_source=False,
    )


def backup_target(
    source: os.PathLike[str] | str,
    backup_root: os.PathLike[str] | str,
    run_id: str,
    target_root: os.PathLike[str] | str,
    *,
    sensitive: bool = False,
    remove_source: bool = False,
) -> Path:
    """Create a no-follow backup, then optionally remove the pinned source."""
    del sensitive  # all backup regular files are private, including non-sensitive ones
    run_id = _validate_run_id(run_id)
    source_root = normalize_target_root(target_root)
    source_path, source_parent_fd, source_name, item, source_fd, link_value, digest = _inspect_source(
        source, source_root
    )
    try:
        return _backup_inspected(
            source_path,
            backup_root,
            run_id,
            source_root,
            source_parent_fd,
            source_name,
            item,
            source_fd,
            link_value,
            digest,
            remove_source=remove_source,
        )
    finally:
        if source_fd is not None:
            os.close(source_fd)
        os.close(source_parent_fd)
