"""Ownership-aware Agent runtime planning and apply."""

from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
import stat
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable, Literal, Mapping

_AGENTS = Path(__file__).resolve().parent
_SCRIPTS = _AGENTS.parent
for _path in (_SCRIPTS, _AGENTS):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from dotf_core.atomic import atomic_write  # noqa: E402
from dotf_core.backup import backup_target, generate_run_id  # noqa: E402
from dotf_core.paths import (  # noqa: E402
    PathBoundaryError,
    assert_no_symlinks,
    assert_path_confined,
    ensure_directory,
    lstat_components,
    open_nofollow,
)
from dotf_core.schemas import (  # noqa: E402
    MANIFEST_SCHEMA_VERSION,
    ManagedItem,
    ManagedManifest,
    SchemaError,
    validate_managed_manifest,
)
from ensure_pyyaml import ensure_yaml  # noqa: E402
from layouts import layout_for_target  # noqa: E402

yaml = ensure_yaml()

AGENTS_MANIFEST_NAME = "agents-manifest.json"
AGENTS_LOCK_NAME = "agents-manifest.lock"
RUNTIME_SCHEMA_VERSION = 1
OWNER_PREFIX = "agents:skill:"
_REQUIRED_EXCLUSIONS = frozenset({"patches", "evals", "experience", "evolutions", "authoring"})
RenderSkill = Callable[[Path, str], bytes]

OnConflict = Literal["block", "backup"]
OnTakeover = Literal["skip", "backup"]
ON_CONFLICT_ENV = "DOTF_ON_CONFLICT"
ON_TAKEOVER_ENV = "DOTF_TAKEOVER"

CONTENT_DRIFT = "owned target was modified locally"
MODE_DRIFT = "owned target mode was modified locally"
IDENTITY_MISMATCH = "manifest ownership identity differs"
SYMLINK_CONFLICT = "target path contains a symlink"
ADOPT_REASON = "target exists without agents ownership"

_REMEDIABLE_CONFLICTS = frozenset({CONTENT_DRIFT, MODE_DRIFT, IDENTITY_MISMATCH})


def parse_on_conflict(value: str | None) -> OnConflict:
    policy = (value or "backup").strip().lower()
    if policy not in ("block", "backup"):
        raise AgentRuntimeError(f"unknown on-conflict policy: {value!r} (expected block or backup)")
    return policy  # type: ignore[return-value]


def on_conflict_from_env(env: Mapping[str, str] | None = None) -> OnConflict:
    return parse_on_conflict((env if env is not None else os.environ).get(ON_CONFLICT_ENV))


def parse_on_takeover(value: str | None) -> OnTakeover:
    policy = (value or "backup").strip().lower()
    if policy not in ("skip", "backup"):
        raise AgentRuntimeError(f"unknown on-takeover policy: {value!r} (expected skip or backup)")
    return policy  # type: ignore[return-value]


def on_takeover_from_env(env: Mapping[str, str] | None = None) -> OnTakeover:
    return parse_on_takeover((env if env is not None else os.environ).get(ON_TAKEOVER_ENV))


def skill_id_from_target(target: str, target_root: str | Path) -> str | None:
    """First path component under the skills root is the Skill id."""
    try:
        relative = Path(target).relative_to(Path(target_root))
    except ValueError:
        return None
    return relative.parts[0] if relative.parts else None


class AgentRuntimeError(RuntimeError):
    """The Agent runtime plan cannot be safely applied."""


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
    actual_state: Literal["missing", "present", "symlink", "unsafe"]
    remediated: bool = False


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
    include_unlisted: bool
    manifest_status: Literal["missing", "ok", "malformed"]
    manifest_digest: str | None
    prior_manifest: ManagedManifest
    operations: tuple[RuntimeOperation, ...]
    only_ids: frozenset[str] | None = None
    on_conflict: OnConflict = "block"
    on_takeover: OnTakeover = "skip"
    isolate_by_skill: bool = False

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
    skipped_skills: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _ManifestSnapshot:
    status: Literal["missing", "ok", "malformed"]
    manifest: ManagedManifest
    digest: str | None
    mode: int | None


@dataclass(frozen=True, slots=True)
class _Actual:
    state: Literal["missing", "present", "symlink", "unsafe"]
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


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


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


def _state_home(home: Path, state_home: Path | None) -> Path:
    if state_home is not None:
        return state_home.expanduser().absolute()
    configured = os.environ.get("XDG_STATE_HOME")
    return Path(configured).expanduser().absolute() if configured else home / ".local" / "state"


def resolve_state_home(home: Path, state_home: Path | None = None) -> Path:
    return _state_home(home.expanduser().absolute(), state_home)


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
    skill_dirs: Mapping[str, Path] | None = None,
    owner_prefix: str = OWNER_PREFIX,
    identity_prefix: str = "agents/skills",
    include_unlisted: bool = False,
    only_ids: frozenset[str] | None = None,
) -> tuple[RuntimeFile, ...]:
    policy = load_runtime_policy(root)
    if skill_dirs is None:
        source_root = source_root or root / "agents" / "skills"
        if not source_root.is_dir():
            raise AgentRuntimeError(f"missing first-party skills source: {source_root}")
        candidates = sorted(
            (p.name, p) for p in source_root.iterdir() if p.is_dir() and not p.is_symlink()
        )
    else:
        candidates = sorted(
            (skill_id, path)
            for skill_id, path in skill_dirs.items()
            if path.is_dir() and not path.is_symlink()
        )
    target_base = assert_path_confined(home, target_root)
    reserved = layout_for_target(target_base)
    reserved_ids = reserved.reserved_ids if reserved is not None else frozenset()
    result: list[RuntimeFile] = []
    targets: set[str] = set()
    declared = set(policy.files) | set(policy.sidecars) | set(policy.excluded)

    def add_file(owner: str, source: Path, relative: PurePosixPath, content: bytes) -> None:
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

    def add_directory(owner: str, source_dir: Path, prefix: PurePosixPath) -> None:
        if source_dir.is_symlink() or not source_dir.is_dir():
            raise AgentRuntimeError(f"runtime sidecar is not a real directory: {source_dir}")
        for source in _source_files(source_dir):
            nested = source.relative_to(source_dir)
            add_file(owner, source, prefix / PurePosixPath(nested.as_posix()), source.read_bytes())

    for skill_id, skill_dir in candidates:
        if only_ids is not None and skill_id not in only_ids:
            continue
        if skill_id in reserved_ids:
            raise AgentRuntimeError(
                f"skill id {skill_id!r} is reserved in target {target_base}: {reserved.label}"
            )
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
            add_file(owner, source, PurePosixPath(skill_id) / filename, content)
        for sidecar in policy.sidecars:
            source_dir = skill_dir / sidecar
            if source_dir.exists():
                add_directory(owner, source_dir, PurePosixPath(skill_id) / sidecar)
        if include_unlisted:
            for child in sorted(skill_dir.iterdir(), key=lambda path: path.name):
                if child.name in declared or child.name.startswith("."):
                    continue
                if child.is_symlink():
                    raise AgentRuntimeError(f"runtime source contains symlink: {child}")
                if child.is_file():
                    add_file(owner, child, PurePosixPath(skill_id) / child.name, child.read_bytes())
                elif child.is_dir():
                    add_directory(owner, child, PurePosixPath(skill_id) / child.name)
                else:
                    raise AgentRuntimeError(f"runtime source contains unsupported entry: {child}")
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
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read()
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


def _inspect_target(home: Path, target_root: Path, target: Path) -> _Actual:
    """Inspect target without following symlinks; distinguish root boundary vs inside links."""
    try:
        confined_root = assert_path_confined(home, target_root)
        confined = assert_path_confined(home, target)
        rel = confined.relative_to(confined_root)
        for comp, st in lstat_components(home, confined_root, missing_ok=True):
            if st is not None and stat.S_ISLNK(st.st_mode):
                return _Actual("unsafe", None, f"target root contains a symlink: {comp}")
    except (OSError, PathBoundaryError, ValueError) as exc:
        return _Actual("unsafe", None, str(exc))

    if str(rel) == ".":
        return _Actual("unsafe", None, "target equals root")

    current = confined_root
    parts = rel.parts
    for index, part in enumerate(parts):
        current = current / part
        try:
            st = os.lstat(current)
        except FileNotFoundError:
            return _Actual("missing", None)
        except OSError as exc:
            return _Actual("unsafe", None, str(exc))
        if stat.S_ISLNK(st.st_mode):
            return _Actual("symlink", None, f"symlink: {current}")
        is_leaf = index == len(parts) - 1
        if not is_leaf:
            if not stat.S_ISDIR(st.st_mode):
                return _Actual("unsafe", None, f"target parent is not a directory: {current}")
        elif not stat.S_ISREG(st.st_mode):
            return _Actual("unsafe", None, "target is not a regular file")

    try:
        fd = os.open(confined, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        return _Actual("missing", None)
    except OSError as exc:
        return _Actual("unsafe", None, str(exc))
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return _Actual("unsafe", None, "target is not a regular file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            content = stream.read()
        return _Actual("present", _sha256(content), mode=stat.S_IMODE(st.st_mode))
    finally:
        os.close(fd)


def _unlink_symlink_only(target_root: Path, target: Path) -> None:
    """Unlink the first symlink component strictly beneath target_root without following it."""
    rel = target.relative_to(target_root)
    current = target_root
    for part in rel.parts:
        current = current / part
        if os.path.islink(current):
            os.unlink(current)
            return


def adoptable_equivalent(plan: SkillsPlan) -> tuple[RuntimeOperation, ...]:
    """Unowned regular targets whose bytes already match what we would write."""
    return tuple(
        op
        for op in plan.conflicts
        if op.conflict == ADOPT_REASON
        and op.expected is not None
        and op.actual_state == "present"
        and op.current_hash == op.expected_hash
    )


def _conflict(
    target: str,
    source_identity: str,
    expected_hash: str | None,
    actual: _Actual,
    installed_hash: str | None,
    reason: str,
    expected: RuntimeFile | None,
    prior: ManagedItem | None,
    *,
    on_conflict: OnConflict = "block",
    on_takeover: OnTakeover = "skip",
) -> RuntimeOperation:
    if (
        actual.state == "symlink"
        and expected is not None
        and ((prior is None and on_takeover == "backup") or (prior is not None and on_conflict == "backup"))
    ):
        return RuntimeOperation(
            "update", "update", target, source_identity, expected_hash,
            actual.digest, installed_hash, reason, expected, prior, actual.state, True,
        )
    if (
        on_conflict == "backup"
        and reason in _REMEDIABLE_CONFLICTS
        and expected is not None
        and prior is not None
        and actual.state == "present"
    ):
        return RuntimeOperation(
            "update", "update", target, source_identity, expected_hash,
            actual.digest, installed_hash, reason, expected, prior, actual.state, True,
        )
    if (
        on_takeover == "backup"
        and reason == ADOPT_REASON
        and expected is not None
        and actual.state == "present"
    ):
        return RuntimeOperation(
            "update", "update", target, source_identity, expected_hash,
            actual.digest, installed_hash, reason, expected, prior, actual.state, True,
        )
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
    skill_dirs: Mapping[str, Path] | None = None,
    owner_prefix: str = OWNER_PREFIX,
    identity_prefix: str = "agents/skills",
    include_unlisted: bool = False,
    only_ids: frozenset[str] | None = None,
    on_conflict: OnConflict = "block",
    on_takeover: OnTakeover = "skip",
) -> SkillsPlan:
    """Compile expected Agent runtime and ownership decisions without writes."""
    repo = root.expanduser().absolute()
    base_home = (home or Path.home()).expanduser().absolute()
    state = _state_home(base_home, state_home)
    base_target = assert_path_confined(
        base_home, (target_root or base_home / ".agents" / "skills").expanduser().absolute()
    )
    resolved_source_root = (source_root or repo / "agents" / "skills").expanduser().absolute()
    expected = collect_runtime_files(
        repo, base_home, base_target, render_skill,
        source_root=resolved_source_root,
        skill_dirs=skill_dirs,
        owner_prefix=owner_prefix,
        identity_prefix=identity_prefix,
        include_unlisted=include_unlisted,
        only_ids=only_ids,
    )
    return compile_owned_plan(
        repo,
        expected,
        home=base_home,
        state=state,
        target_root=base_target,
        source_root=resolved_source_root,
        owner_prefix=owner_prefix,
        identity_prefix=identity_prefix,
        include_unlisted=include_unlisted,
        only_ids=only_ids,
        on_conflict=on_conflict,
        on_takeover=on_takeover,
        outside_root_message="stale manifest target is outside the skills root",
        isolate_by_skill=True,
    )


def compile_owned_plan(
    repo: Path,
    expected: tuple[RuntimeFile, ...],
    *,
    home: Path,
    state: Path,
    target_root: Path,
    source_root: Path,
    owner_prefix: str,
    identity_prefix: str,
    include_unlisted: bool = False,
    only_ids: frozenset[str] | None = None,
    on_conflict: OnConflict = "block",
    on_takeover: OnTakeover = "skip",
    outside_root_message: str = "stale manifest target is outside the owned root",
    isolate_by_skill: bool = False,
) -> SkillsPlan:
    """Compile ownership decisions for an explicit set of HOME files."""
    snapshot = _read_manifest(home, state)
    prior_by_target = {
        item.target: item
        for item in snapshot.manifest.items
        if item.owner.startswith(owner_prefix)
    }
    operations: list[RuntimeOperation] = []
    expected_targets = {item.target for item in expected}
    kw = {"on_conflict": on_conflict, "on_takeover": on_takeover}

    if snapshot.status == "malformed":
        for item in expected:
            actual = _inspect_target(home, target_root, Path(item.target))
            operations.append(_conflict(
                item.target, item.source_identity, item.expected_hash, actual, None,
                "agents manifest is malformed or incompatible", item, None, **kw,
            ))
    else:
        for item in expected:
            actual = _inspect_target(home, target_root, Path(item.target))
            prior = prior_by_target.get(item.target)
            if prior is None:
                if actual.state == "missing":
                    operations.append(RuntimeOperation(
                        "create", "create", item.target, item.source_identity,
                        item.expected_hash, None, None, None, item, None, "missing",
                    ))
                elif actual.state == "symlink":
                    operations.append(_conflict(
                        item.target, item.source_identity, item.expected_hash, actual, None,
                        SYMLINK_CONFLICT, item, None, **kw,
                    ))
                elif actual.state == "unsafe":
                    operations.append(_conflict(
                        item.target, item.source_identity, item.expected_hash, actual, None,
                        actual.detail or "target path contains an unsafe type", item, None, **kw,
                    ))
                else:
                    operations.append(_conflict(
                        item.target, item.source_identity, item.expected_hash, actual, None,
                        ADOPT_REASON, item, None, **kw,
                    ))
                continue

            if actual.state == "missing":
                operations.append(RuntimeOperation(
                    "create", "create", item.target, item.source_identity,
                    item.expected_hash, None, prior.installed_hash, None, item, prior, "missing",
                ))
            elif prior.owner != item.owner:
                operations.append(_conflict(
                    item.target, item.source_identity, item.expected_hash, actual,
                    prior.installed_hash, IDENTITY_MISMATCH, item, prior, **kw,
                ))
            elif actual.state == "unsafe":
                operations.append(_conflict(
                    item.target, item.source_identity, item.expected_hash, actual,
                    prior.installed_hash, actual.detail or "target path contains an unsafe type",
                    item, prior, **kw,
                ))
            elif actual.state == "symlink":
                operations.append(_conflict(
                    item.target, item.source_identity, item.expected_hash, actual,
                    prior.installed_hash, SYMLINK_CONFLICT, item, prior, **kw,
                ))
            elif actual.digest != prior.installed_hash:
                operations.append(_conflict(
                    item.target, item.source_identity, item.expected_hash, actual,
                    prior.installed_hash, CONTENT_DRIFT, item, prior, **kw,
                ))
            elif actual.mode != prior.mode:
                operations.append(_conflict(
                    item.target, item.source_identity, item.expected_hash, actual,
                    prior.installed_hash, MODE_DRIFT, item, prior, **kw,
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
                normalized = assert_path_confined(home, target)
                normalized.relative_to(target_root)
            except (OSError, PathBoundaryError, ValueError):
                operations.append(_conflict(
                    prior.target, prior.source_identity, None, _Actual("unsafe", None),
                    prior.installed_hash, outside_root_message, None, prior, **kw,
                ))
                continue
            actual = _inspect_target(home, target_root, normalized)
            if actual.state == "unsafe":
                operations.append(_conflict(
                    prior.target, prior.source_identity, None, actual, prior.installed_hash,
                    actual.detail or "stale target path contains an unsafe type", None, prior, **kw,
                ))
            elif actual.state == "symlink":
                if on_conflict == "backup":
                    operations.append(RuntimeOperation(
                        "prune", "prune", prior.target, prior.source_identity, None,
                        None, prior.installed_hash, SYMLINK_CONFLICT, None, prior, "symlink", True,
                    ))
                else:
                    operations.append(_conflict(
                        prior.target, prior.source_identity, None, actual, prior.installed_hash,
                        SYMLINK_CONFLICT, None, prior, **kw,
                    ))
            elif actual.state == "present" and actual.digest != prior.installed_hash:
                if on_conflict == "backup":
                    operations.append(RuntimeOperation(
                        "prune", "prune", prior.target, prior.source_identity, None,
                        actual.digest, prior.installed_hash,
                        "stale owned target was modified locally", None, prior, "present", True,
                    ))
                else:
                    operations.append(_conflict(
                        prior.target, prior.source_identity, None, actual, prior.installed_hash,
                        "stale owned target was modified locally", None, prior, **kw,
                    ))
            else:
                operations.append(RuntimeOperation(
                    "prune", "prune", prior.target, prior.source_identity, None,
                    actual.digest, prior.installed_hash, None, None, prior, actual.state,
                ))

    return SkillsPlan(
        MANIFEST_SCHEMA_VERSION,
        str(repo),
        str(home),
        str(state),
        str(target_root),
        str(source_root),
        owner_prefix,
        identity_prefix,
        include_unlisted,
        snapshot.status,
        snapshot.digest,
        snapshot.manifest,
        tuple(sorted(operations, key=lambda item: (item.target, item.action))),
        only_ids,
        on_conflict,
        on_takeover,
        isolate_by_skill,
    )


def _ensure_state(home: Path, state_home: Path) -> Path:
    directory = manifest_path(home, state_home).parent
    boundary = _boundary(home, directory)
    ensure_directory(boundary, state_home, mode=0o700)
    ensure_directory(boundary, directory, mode=0o700)
    os.chmod(directory, 0o700)
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
        self.fd = open_nofollow(_boundary(self.home, path), path, os.O_RDWR | os.O_CREAT, 0o600)
        if stat.S_IMODE(os.fstat(self.fd).st_mode) != 0o600:
            os.fchmod(self.fd, 0o600)
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.fd is not None:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
            self.fd = None


def _remove_empty_parents(target_root: Path, start: Path) -> None:
    current = start
    while current != target_root:
        try:
            os.rmdir(current)
        except OSError:
            return
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
    """Apply a skills plan under the Agent manifest lock."""

    def compile_current() -> SkillsPlan:
        return compile_skills_plan(
            Path(plan.repo_root),
            render_skill,
            home=Path(plan.home),
            state_home=Path(plan.state_home),
            target_root=Path(plan.target_root),
            source_root=Path(plan.source_root),
            owner_prefix=plan.owner_prefix,
            identity_prefix=plan.identity_prefix,
            include_unlisted=plan.include_unlisted,
            only_ids=plan.only_ids,
            on_conflict=plan.on_conflict,
            on_takeover=plan.on_takeover,
        )

    return apply_owned_plan(plan, compile_current, run_id=run_id)


def _quarantined_skills(plan: SkillsPlan, blocking: list[RuntimeOperation]) -> set[str]:
    skipped: set[str] = set()
    for operation in blocking:
        skill_id = skill_id_from_target(operation.target, plan.target_root) if plan.isolate_by_skill else None
        if skill_id is None:
            raise AgentRuntimeConflict(f"{operation.target}: {operation.conflict or 'conflict outside skills root'}")
        skipped.add(skill_id)
    return skipped


def _plan_excluding_skills(plan: SkillsPlan, skip: frozenset[str]) -> SkillsPlan:
    if not skip:
        return plan
    kept = tuple(
        op for op in plan.operations
        if skill_id_from_target(op.target, plan.target_root) not in skip
    )
    return replace(plan, operations=kept)


def apply_owned_plan(
    plan: SkillsPlan,
    compile_current: Callable[[], SkillsPlan],
    *,
    run_id: str | None = None,
) -> SkillsApplyResult:
    """Apply an owned-file plan under the Agent manifest lock."""
    if not isinstance(plan, SkillsPlan) or plan.schema_version != MANIFEST_SCHEMA_VERSION:
        raise AgentRuntimeError("unsupported skills plan")
    home = Path(plan.home)
    state_home = Path(plan.state_home)
    target_root = Path(plan.target_root)
    run = run_id or generate_run_id()
    changed = 0
    manifest_file = manifest_path(home, state_home)

    with AgentManifestLock(home, state_home):
        snapshot = _read_manifest(home, state_home)
        if snapshot.status == "malformed":
            raise AgentRuntimeConflict("agents manifest is malformed or incompatible")
        if snapshot.status == plan.manifest_status and snapshot.digest == plan.manifest_digest:
            current = plan
        else:
            current = compile_current()
            if current.manifest_status == "malformed":
                raise AgentRuntimeConflict("agents manifest is malformed or incompatible")

        if snapshot.status == "ok" and snapshot.mode != 0o600:
            os.chmod(manifest_file, 0o600)
            changed += 1

        adoptable_targets = {item.target for item in adoptable_equivalent(current)}
        blocking = [op for op in current.conflicts if op.target not in adoptable_targets]
        skipped = frozenset(_quarantined_skills(current, blocking))
        skipped_priors = tuple(
            op.prior for op in current.operations
            if skill_id_from_target(op.target, current.target_root) in skipped and op.prior is not None
        )
        effective = _plan_excluding_skills(current, skipped)

        result = _apply_operations(
            effective,
            home,
            state_home,
            target_root,
            snapshot,
            run,
            changed=changed,
            manifest_file=manifest_file,
            adoptable_targets=adoptable_targets,
            retain_priors=skipped_priors,
        )
        return replace(result, skipped_skills=tuple(sorted(skipped)))


def _apply_operations(
    current: SkillsPlan,
    home: Path,
    state_home: Path,
    target_root: Path,
    snapshot: _ManifestSnapshot,
    run: str,
    *,
    changed: int,
    manifest_file: Path,
    adoptable_targets: set[str],
    retain_priors: tuple[ManagedItem, ...] = (),
) -> SkillsApplyResult:
    unresolved = [op for op in current.conflicts if op.target not in adoptable_targets]
    if unresolved:
        raise AgentRuntimeConflict("; ".join(f"{op.target}: {op.conflict}" for op in unresolved))

    retained = [item for item in snapshot.manifest.items if not item.owner.startswith(current.owner_prefix)]
    expected_items: list[ManagedItem] = list(retain_priors)
    seen_targets = {item.target for item in expected_items}
    backup_root = state_home / "dotf" / "backups"
    pruned_parents: list[Path] = []
    unchanged = 0
    pruned = 0

    def record(item: ManagedItem) -> None:
        if item.target not in seen_targets:
            expected_items.append(item)
            seen_targets.add(item.target)
        else:
            for idx, existing in enumerate(expected_items):
                if existing.target == item.target:
                    expected_items[idx] = item
                    break

    for op in current.operations:
        if op.action == "none":
            assert op.prior is not None
            record(op.prior)
            unchanged += 1
            continue

        if op.target in adoptable_targets:
            assert op.expected is not None
            if os.stat(op.target, follow_symlinks=False).st_mode & 0o777 != op.expected.mode:
                os.chmod(op.target, op.expected.mode)
            record(_managed_item(op.expected, run))
            changed += 1
            continue

        if op.action in {"create", "update"}:
            assert op.expected is not None
            is_symlink = op.actual_state == "symlink"
            if is_symlink:
                _unlink_symlink_only(target_root, Path(op.target))
            use_backup = op.action == "update" and not is_symlink
            atomic_write(
                op.target,
                op.expected.content,
                root=home,
                format="text" if op.target.endswith((".md", ".mdc", ".py", ".sh")) else "binary",
                mode=op.expected.mode,
                backup_root=backup_root if use_backup else None,
                run_id=run if use_backup else None,
                sensitive=False,
            )
            record(_managed_item(op.expected, run))
            changed += 1
            continue

        if op.action == "chmod":
            assert op.expected is not None and op.prior is not None
            os.chmod(op.target, op.expected.mode)
            entry = (
                op.prior
                if (op.prior.expected_hash == op.expected.expected_hash and op.prior.mode == op.expected.mode)
                else _managed_item(op.expected, run)
            )
            record(entry)
            changed += 1
            continue

        if op.action == "prune":
            assert op.prior is not None
            if op.actual_state == "symlink":
                _unlink_symlink_only(target_root, Path(op.target))
                pruned_parents.append(Path(op.target).parent)
            elif op.actual_state == "present":
                if op.remediated:
                    backup_target(op.target, backup_root, run, home, remove_source=True)
                else:
                    try:
                        os.unlink(op.target)
                    except FileNotFoundError:
                        pass
                pruned_parents.append(Path(op.target).parent)
            pruned += 1
            changed += 1

    for parent in sorted(set(pruned_parents), key=lambda value: len(value.parts), reverse=True):
        _remove_empty_parents(target_root, parent)

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
