"""No-follow target-root confinement helpers."""

from __future__ import annotations

import errno
import os
import stat
from pathlib import Path
from typing import Iterator


class PathBoundaryError(OSError):
    """A path escaped its root or traversed an unexpected symbolic link."""


def normalize_target_root(root: os.PathLike[str] | str) -> Path:
    """Resolve the trusted boundary once; managed descendants are never resolved."""
    expanded = os.path.abspath(os.path.expanduser(os.fspath(root)))
    try:
        canonical = Path(os.path.realpath(expanded, strict=True))
    except TypeError:  # Python < 3.10 compatibility
        canonical = Path(os.path.realpath(expanded))
        if not canonical.exists():
            raise FileNotFoundError(expanded)
    st = os.stat(canonical)
    if not stat.S_ISDIR(st.st_mode):
        raise NotADirectoryError(str(canonical))
    return canonical


def assert_path_confined(root: os.PathLike[str] | str, target: os.PathLike[str] | str) -> Path:
    lexical_root = Path(os.path.abspath(os.path.expanduser(os.fspath(root))))
    base = normalize_target_root(lexical_root)
    raw = os.path.expanduser(os.fspath(target))
    if not os.path.isabs(raw):
        candidate = Path(os.path.abspath(os.path.join(base, raw)))
    else:
        absolute = Path(os.path.abspath(raw))
        # A trusted root may itself be a symlink (for example /tmp on macOS).
        # Translate only its lexical prefix; never resolve managed descendants.
        try:
            relative = absolute.relative_to(lexical_root)
        except ValueError:
            candidate = absolute
        else:
            candidate = base / relative
    try:
        common = os.path.commonpath((str(base), str(candidate)))
    except ValueError as exc:
        raise PathBoundaryError(errno.EXDEV, "target is outside managed root", str(candidate)) from exc
    if common != str(base):
        raise PathBoundaryError(errno.EXDEV, "target is outside managed root", str(candidate))
    return candidate


def _relative_parts(root: Path, target: Path) -> tuple[str, ...]:
    rel = target.relative_to(root)
    return () if str(rel) == "." else rel.parts


def lstat_components(
    root: os.PathLike[str] | str,
    target: os.PathLike[str] | str,
    *,
    missing_ok: bool = True,
) -> tuple[tuple[Path, os.stat_result | None], ...]:
    """lstat each managed component from root to leaf, never following a leaf."""
    base = normalize_target_root(root)
    candidate = assert_path_confined(root, target)
    result: list[tuple[Path, os.stat_result | None]] = []
    current = base
    for part in _relative_parts(base, candidate):
        current = current / part
        try:
            item = os.lstat(current)
        except FileNotFoundError:
            if not missing_ok:
                raise
            result.append((current, None))
            # Later components cannot exist without this parent.
            for rest in _relative_parts(current, candidate):
                current = current / rest
                result.append((current, None))
            break
        result.append((current, item))
    return tuple(result)


def assert_no_symlinks(
    root: os.PathLike[str] | str,
    target: os.PathLike[str] | str,
    *,
    allow_leaf_symlink: bool = False,
    missing_ok: bool = True,
) -> Path:
    candidate = assert_path_confined(root, target)
    components = lstat_components(root, candidate, missing_ok=missing_ok)
    for index, (path, item) in enumerate(components):
        if item is not None and stat.S_ISLNK(item.st_mode):
            is_leaf = index == len(components) - 1
            if not (is_leaf and allow_leaf_symlink):
                raise PathBoundaryError(errno.ELOOP, "symbolic link crosses managed path boundary", str(path))
    return candidate


def _open_flags(*, directory: bool = False) -> int:
    flags = os.O_RDONLY
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    if directory:
        flags |= getattr(os, "O_DIRECTORY", 0)
    return flags


def _walk_parent_fd(root: Path, target: Path, *, create: bool, mode: int) -> tuple[int, str]:
    parts = _relative_parts(root, target)
    if not parts:
        raise PathBoundaryError(errno.EINVAL, "operation requires a path below root", str(target))
    fd = os.open(root, _open_flags(directory=True))
    try:
        for part in parts[:-1]:
            try:
                child = os.open(part, _open_flags(directory=True), dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, mode=mode, dir_fd=fd)
                child = os.open(part, _open_flags(directory=True), dir_fd=fd)
                os.fchmod(child, mode)
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise PathBoundaryError(errno.ELOOP, "unsafe managed parent", str(target)) from exc
                raise
            os.close(fd)
            fd = child
        return fd, parts[-1]
    except BaseException:
        os.close(fd)
        raise


def ensure_directory(
    root: os.PathLike[str] | str,
    directory: os.PathLike[str] | str,
    *,
    mode: int = 0o700,
) -> Path:
    base = normalize_target_root(root)
    target = assert_path_confined(root, directory)
    if target == base:
        return target
    parent_fd, leaf = _walk_parent_fd(base, target, create=True, mode=mode)
    created = False
    try:
        try:
            os.mkdir(leaf, mode=mode, dir_fd=parent_fd)
            created = True
        except FileExistsError:
            fd = os.open(leaf, _open_flags(directory=True), dir_fd=parent_fd)
            os.close(fd)
        if created:
            os.chmod(leaf, mode, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise PathBoundaryError(errno.ELOOP, "unsafe managed directory", str(target)) from exc
        raise
    finally:
        os.close(parent_fd)
    return target


def open_nofollow(
    root: os.PathLike[str] | str,
    target: os.PathLike[str] | str,
    flags: int = os.O_RDONLY,
    mode: int = 0o600,
    *,
    create_parents: bool = False,
) -> int:
    """Open a confined leaf relative to securely opened parent descriptors."""
    base = normalize_target_root(root)
    candidate = assert_path_confined(root, target)
    parent_fd, leaf = _walk_parent_fd(base, candidate, create=create_parents, mode=0o700)
    try:
        safe_flags = flags | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        return os.open(leaf, safe_flags, mode, dir_fd=parent_fd)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise PathBoundaryError(errno.ELOOP, "unsafe managed leaf", str(candidate)) from exc
        raise
    finally:
        os.close(parent_fd)


def open_parent_nofollow(
    root: os.PathLike[str] | str,
    target: os.PathLike[str] | str,
    *,
    create: bool = False,
    mode: int = 0o700,
) -> tuple[int, str]:
    """Return an owned fd for target's parent plus its leaf name.

    Every component is opened relative to the previously retained directory fd
    with ``O_NOFOLLOW``.  The caller must close the returned fd.
    """
    base = normalize_target_root(root)
    candidate = assert_path_confined(root, target)
    return _walk_parent_fd(base, candidate, create=create, mode=mode)


def open_directory_nofollow(
    root: os.PathLike[str] | str,
    directory: os.PathLike[str] | str,
    *,
    create: bool = False,
    mode: int = 0o700,
) -> int:
    """Open and retain a confined directory without following managed links."""
    base = normalize_target_root(root)
    candidate = assert_path_confined(root, directory)
    if candidate == base:
        return os.open(base, _open_flags(directory=True))
    parent_fd, leaf = _walk_parent_fd(base, candidate, create=create, mode=mode)
    try:
        if create:
            try:
                os.mkdir(leaf, mode=mode, dir_fd=parent_fd)
            except FileExistsError:
                pass
        return os.open(leaf, _open_flags(directory=True), dir_fd=parent_fd)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise PathBoundaryError(errno.ELOOP, "unsafe managed directory", str(candidate)) from exc
        raise
    finally:
        os.close(parent_fd)
