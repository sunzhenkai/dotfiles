"""Shared, dependency-light safety primitives for dotf state changes."""

from .atomic import AtomicWriteResult, StagedFile, atomic_replace, atomic_write, stage_bytes, validate_content
from .backup import backup_destination, backup_target, generate_run_id, target_relative_path
from .paths import (
    PathBoundaryError,
    assert_no_symlinks,
    assert_path_confined,
    ensure_directory,
    lstat_components,
    normalize_target_root,
    open_directory_nofollow,
    open_nofollow,
    open_parent_nofollow,
)
from .sanitize import (
    REDACTED,
    sanitize,
    sanitize_for_json,
    sanitize_for_persistence,
    sanitize_for_terminal,
    sanitize_json,
    sanitize_text,
)
from .schemas import (
    MANIFEST_SCHEMA_VERSION,
    PLAN_SCHEMA_VERSION,
    ManagedItem,
    ManagedManifest,
    PlanItem,
    SchemaError,
    validate_managed_manifest,
    validate_plan_item,
)

__all__ = [name for name in globals() if not name.startswith("_")]
