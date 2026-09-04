"""Focused safety-foundation contracts for dotf_core (OpenSpec 1.1-1.5)."""

from __future__ import annotations

import json
import os
import stat
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import dotf_core.atomic as atomic_module
import dotf_core.backup as backup_module
from dotf_core.atomic import atomic_replace, atomic_write, stage_bytes, validate_content
from dotf_core.backup import backup_target, generate_run_id
from dotf_core.paths import PathBoundaryError, assert_no_symlinks, open_nofollow
from dotf_core.sanitize import REDACTED, sanitize_for_json, sanitize_for_persistence, sanitize_for_terminal
from dotf_core.schemas import (
    JournalAction,
    ManagedManifest,
    PlanItem,
    McpTransactionJournal,
    SchemaError,
    validate_managed_manifest,
    validate_plan_item,
    validate_mcp_transaction_journal,
)

HASH = "a" * 64


def plan_data() -> dict[str, object]:
    return {
        "schema_version": 1,
        "kind": "plan-item",
        "owner": "agents:mcp",
        "source_identity": "catalog/server",
        "expected_hash": HASH,
        "target": "/home/test/.config/tool/config.json",
        "strategy": "render",
        "risk": "sensitive",
        "state": "update",
        "action": "update",
        "conflict_reason": None,
        "required_secrets": ["SERVICE_TOKEN"],
        "target_mode": 0o600,
        "sensitive": True,
    }


def managed_data(target: str = "/home/test/.config/tool/config.json") -> dict[str, object]:
    return {
        "owner": "agents:mcp",
        "target": target,
        "source_identity": "catalog/server",
        "expected_hash": HASH,
        "installed_hash": HASH,
        "strategy": "render",
        "mode": 0o600,
        "run_id": "run-1",
        "sensitive": True,
    }


def action_data() -> dict[str, object]:
    return {
        "module": "agents",
        "action": "config",
        "status": "completed",
        "started_at": "2026-09-03T00:00:00Z",
        "ended_at": "2026-09-03T00:00:01Z",
        "duration_ms": 1000,
        "reason_code": "updated",
        "reason": "managed output updated",
        "before_hash": None,
        "after_hash": HASH,
    }


def test_strict_versioned_immutable_schemas_round_trip() -> None:
    plan = validate_plan_item(plan_data())
    assert isinstance(plan, PlanItem)
    assert plan.required_secrets == ("SERVICE_TOKEN",)
    with pytest.raises(FrozenInstanceError):
        plan.owner = "other"  # type: ignore[misc]

    manifest = validate_managed_manifest(
        {
            "schema_version": 1,
            "kind": "managed-manifest",
            "generated_at": "2026-09-03T00:00:00Z",
            "items": [managed_data()],
        }
    )
    assert isinstance(manifest, ManagedManifest)
    assert isinstance(manifest.items, tuple)

    journal = validate_mcp_transaction_journal(
        {
            "schema_version": 1,
            "kind": "mcp-transaction-journal",
            "run_id": "run-1",
            "status": "completed",
            "started_at": "2026-09-03T00:00:00Z",
            "updated_at": "2026-09-03T00:00:01Z",
            "plan_version": 1,
            "actions": [action_data()],
        }
    )
    assert isinstance(journal, McpTransactionJournal)
    assert isinstance(journal.actions[0], JournalAction)
    assert journal.to_dict()["schema_version"] == 1


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: data.update(schema_version=2),
        lambda data: data.update(kind="other"),
        lambda data: data.update(extra=True),
        lambda data: data.pop("owner"),
        lambda data: data.update(target_mode="0600"),
        lambda data: data.update(target_mode=0o644),
    ],
)
def test_plan_schema_rejects_versions_unknown_missing_and_invalid_types(mutate) -> None:
    data = plan_data()
    mutate(data)
    with pytest.raises(SchemaError):
        validate_plan_item(data)


def test_manifest_rejects_duplicate_targets_and_journal_unknown_keys() -> None:
    with pytest.raises(SchemaError, match="duplicate"):
        validate_managed_manifest(
            {
                "schema_version": 1,
                "kind": "managed-manifest",
                "generated_at": "now",
                "items": [managed_data(), managed_data()],
            }
        )
    action = action_data()
    action["output"] = "must never be persisted"
    with pytest.raises(SchemaError):
        validate_mcp_transaction_journal(
            {
                "schema_version": 1,
                "kind": "mcp-transaction-journal",
                "run_id": "r",
                "status": "failed",
                "started_at": "now",
                "updated_at": "now",
                "plan_version": 1,
                "actions": [action],
            }
        )


def test_unified_sanitizer_redacts_all_required_secret_shapes() -> None:
    env = {
        "SERVICE_TOKEN": "actual-env-secret-123",
        "NORMAL_VALUE": "public-value",
    }
    raw = (
        "credential=cred-value Authorization: Bearer auth-value\n"
        "Cookie: sid=cookie-value\n"
        "https://alice:uri-password@example.test/path "
        "actual-env-secret-123 public-value"
    )
    nested = {
        "reason": raw,
        "authorization": "Bearer nested-auth",
        "cookie": "nested-cookie",
        "safe": "public-value",
    }
    surfaces = (
        sanitize_for_terminal(nested, environ=env),
        json.dumps(sanitize_for_json(nested, environ=env)),
        json.dumps(sanitize_for_persistence(nested, environ=env)),
    )
    for rendered in surfaces:
        for secret in (
            "cred-value",
            "auth-value",
            "cookie-value",
            "alice",
            "uri-password",
            "actual-env-secret-123",
            "nested-auth",
            "nested-cookie",
        ):
            assert secret not in rendered
        assert REDACTED in rendered
        assert "public-value" in rendered


def test_authorization_assignment_redacts_bearer_continuation_on_every_surface() -> None:
    raw = {"reason": "request failed: authorization=Bearer audit-token-123 safe=visible"}
    surfaces = (
        sanitize_for_terminal(raw, environ={}),
        json.dumps(sanitize_for_json(raw, environ={})),
        json.dumps(sanitize_for_persistence(raw, environ={})),
    )
    for rendered in surfaces:
        assert "audit-token-123" not in rendered
        assert "authorization=[REDACTED]" in rendered
        assert "safe=visible" in rendered


def test_parent_symlink_attack_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "parent").symlink_to(outside, target_is_directory=True)
    target = root / "parent" / "secret"
    with pytest.raises(PathBoundaryError):
        assert_no_symlinks(root, target)
    with pytest.raises(PathBoundaryError):
        open_nofollow(root, target, os.O_WRONLY | os.O_CREAT)
    assert not (outside / "secret").exists()


def test_trusted_root_is_canonicalized_without_following_descendants(tmp_path: Path) -> None:
    real_root = tmp_path / "real-home"
    real_root.mkdir()
    root_alias = tmp_path / "home-alias"
    root_alias.symlink_to(real_root, target_is_directory=True)
    target = root_alias / "app" / "config"
    checked = assert_no_symlinks(root_alias, target)
    assert checked == real_root / "app" / "config"


def test_leaf_symlink_and_lexical_escape_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    victim = outside / "victim"
    victim.write_text("unchanged", encoding="utf-8")
    (root / "leaf").symlink_to(victim)
    with pytest.raises(PathBoundaryError):
        assert_no_symlinks(root, root / "leaf")
    with pytest.raises(PathBoundaryError):
        assert_no_symlinks(root, root / ".." / "outside" / "victim")
    assert victim.read_text(encoding="utf-8") == "unchanged"


def test_backup_layout_permissions_and_same_names(tmp_path: Path) -> None:
    root = tmp_path / "home"
    backup_root = root / ".config" / "backups"
    first = root / "a" / "settings.json"
    second = root / "b" / "settings.json"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")
    run_id = generate_run_id()

    d1 = backup_target(first, backup_root, run_id, root, sensitive=True)
    d2 = backup_target(second, backup_root, run_id, root, sensitive=True)
    assert d1 != d2
    assert d1.relative_to(backup_root).parts[:2] == (run_id, "a")
    assert d2.relative_to(backup_root).parts[:2] == (run_id, "b")
    assert stat.S_IMODE(backup_root.stat().st_mode) == 0o700
    assert stat.S_IMODE((backup_root / run_id).stat().st_mode) == 0o700
    assert stat.S_IMODE(d1.stat().st_mode) == 0o600


def test_concurrent_backup_collision_never_overwrites(tmp_path: Path) -> None:
    root = tmp_path / "home"
    root.mkdir()
    source = root / "credential.json"
    source.write_text("secret", encoding="utf-8")
    backup_root = root / "backups"
    run_id = generate_run_id()
    with ThreadPoolExecutor(max_workers=8) as pool:
        paths = list(pool.map(lambda _: backup_target(source, backup_root, run_id, root, sensitive=True), range(16)))
    assert len(set(paths)) == 16
    assert all(path.read_text(encoding="utf-8") == "secret" for path in paths)


def test_backup_preserves_symlink_and_rejects_backup_root_symlink(tmp_path: Path) -> None:
    root = tmp_path / "home"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    victim = outside / "victim"
    victim.write_text("do not copy", encoding="utf-8")
    link = root / "link"
    link.symlink_to(victim)
    backup = backup_target(link, root / "backups", generate_run_id(), root, remove_source=True)
    assert backup.is_symlink()
    assert os.readlink(backup) == str(victim)
    assert not link.exists()
    assert victim.read_text(encoding="utf-8") == "do not copy"

    evil = root / "evil-backups"
    evil.symlink_to(outside, target_is_directory=True)
    source = root / "source"
    source.write_text("x", encoding="utf-8")
    with pytest.raises(PathBoundaryError):
        backup_target(source, evil, generate_run_id(), root)


@pytest.mark.parametrize(
    ("format", "valid", "invalid"),
    [
        ("json", '{"ok": true}', '{"broken":'),
        ("yaml", "ok: true\n", "ok: [unterminated\n"),
        ("toml", 'ok = true\n', 'ok = "unterminated\n'),
    ],
)
def test_format_validation(format: str, valid: str, invalid: str) -> None:
    validate_content(valid, format)  # type: ignore[arg-type]
    with pytest.raises(Exception):
        validate_content(invalid, format)  # type: ignore[arg-type]


def test_staging_same_filesystem_unchanged_and_permissions(tmp_path: Path) -> None:
    root = tmp_path / "home"
    root.mkdir()
    target = root / "app" / "config.json"
    target.parent.mkdir()
    target.write_text('{"same":true}', encoding="utf-8")
    before = target.stat().st_mtime_ns
    backup_root = root / "backups"
    result = atomic_write(
        target,
        b'{"same":true}',
        root=root,
        format="json",
        backup_root=backup_root,
        run_id=generate_run_id(),
    )
    assert result.status == "unchanged"
    assert target.stat().st_mtime_ns == before
    assert not backup_root.exists()

    staged = stage_bytes(target, b'{"new":true}', root=root, format="json", mode=0o600)
    assert staged.stat().st_dev == target.parent.stat().st_dev
    assert stat.S_IMODE(staged.stat().st_mode) == 0o600
    staged.cleanup()


def test_sensitive_unchanged_target_is_secured_without_replacement_or_backup(tmp_path: Path) -> None:
    root = tmp_path / "home"
    root.mkdir()
    target = root / "secret.json"
    target.write_text('{"same":true}', encoding="utf-8")
    os.chmod(target, 0o644)
    before = target.stat()
    backup_root = root / "backups"

    result = atomic_write(
        target,
        b'{"same":true}',
        root=root,
        format="json",
        mode=0o600,
        sensitive=True,
        backup_root=backup_root,
        run_id=generate_run_id(),
    )

    after = target.stat()
    assert result.status == "unchanged"
    assert result.backup is None
    assert (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino)
    assert after.st_mtime_ns == before.st_mtime_ns
    assert stat.S_IMODE(after.st_mode) == 0o600
    assert target.read_bytes() == b'{"same":true}'
    assert not backup_root.exists()
    assert not list(root.glob(".*.dotf-stage-*"))


def test_sensitive_unchanged_mode_failure_restores_exact_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "home"
    root.mkdir()
    target = root / "secret.json"
    target.write_text('{"same":true}', encoding="utf-8")
    os.chmod(target, 0o644)
    before = target.stat()
    backup_root = root / "backups"
    real_fchmod = atomic_module.os.fchmod
    injected = False

    def chmod_then_fail_once(fd: int, mode: int) -> None:
        nonlocal injected
        if not injected and os.fstat(fd).st_ino == before.st_ino and mode == 0o600:
            injected = True
            real_fchmod(fd, mode)
            raise OSError("injected sensitive chmod failure")
        real_fchmod(fd, mode)

    monkeypatch.setattr(atomic_module.os, "fchmod", chmod_then_fail_once)
    with pytest.raises(OSError, match="injected sensitive chmod failure"):
        atomic_write(
            target,
            b'{"same":true}',
            root=root,
            format="json",
            mode=0o600,
            sensitive=True,
            backup_root=backup_root,
            run_id=generate_run_id(),
        )

    after = target.stat()
    assert injected
    assert (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino)
    assert after.st_mtime_ns == before.st_mtime_ns
    assert stat.S_IMODE(after.st_mode) == 0o644
    assert target.read_bytes() == b'{"same":true}'
    assert not backup_root.exists()
    assert not list(root.glob(".*.dotf-stage-*"))
    assert not list(root.glob(".*.dotf-quarantine-*"))


def test_unchanged_fails_closed_on_same_inode_final_decision_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "home"
    root.mkdir()
    target = root / "config.json"
    target.write_text('{"same":true}', encoding="utf-8")
    original_inode = target.stat().st_ino
    real_visible_check = atomic_module._require_visible_target

    def mutate_same_inode_at_final_decision(*args, **kwargs):
        real_visible_check(*args, **kwargs)
        target.write_text('{"evil":true}', encoding="utf-8")
        assert target.stat().st_ino == original_inode

    monkeypatch.setattr(atomic_module, "_require_visible_target", mutate_same_inode_at_final_decision)
    with pytest.raises(RuntimeError, match="content changed before unchanged decision"):
        atomic_write(target, '{"same":true}', root=root, format="json")

    assert target.stat().st_ino == original_inode
    assert target.read_text(encoding="utf-8") == '{"evil":true}'
    assert not list(root.glob(".*.dotf-stage-*"))


def test_invalid_or_failed_atomic_write_preserves_original(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "home"
    root.mkdir()
    target = root / "config.json"
    target.write_text('{"original":true}', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        atomic_write(target, '{"invalid":', root=root, format="json")
    assert target.read_text(encoding="utf-8") == '{"original":true}'
    assert not list(root.glob(".*.dotf-stage-*"))

    def fail_replace(source, destination, *args, **kwargs):
        raise OSError("injected replace failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected"):
        atomic_write(target, '{"replacement":true}', root=root, format="json")
    assert target.read_text(encoding="utf-8") == '{"original":true}'
    assert not list(root.glob(".*.dotf-stage-*"))


def test_atomic_write_rejects_leaf_symlink(tmp_path: Path) -> None:
    root = tmp_path / "home"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    victim = outside / "config.json"
    victim.write_text('{"victim":true}', encoding="utf-8")
    target = root / "config.json"
    target.symlink_to(victim)
    with pytest.raises(PathBoundaryError):
        atomic_write(target, '{"attack":true}', root=root, format="json")
    assert victim.read_text(encoding="utf-8") == '{"victim":true}'


def test_sensitive_keys_redact_entire_recursive_value_for_every_json_type() -> None:
    raw = {
        "credential": {"nested": ["must", "all", "disappear"]},
        "authorization": ["Bearer visible-before-redaction", {"safe": "also hidden"}],
        "cookie": 12345,
        "api_key": False,
        "client_secret": None,
        "safe": [{"token": {"deep": [1, False, None]}}],
    }
    expected = {
        "credential": REDACTED,
        "authorization": REDACTED,
        "cookie": REDACTED,
        "api_key": REDACTED,
        "client_secret": REDACTED,
        "safe": [{"token": REDACTED}],
    }
    assert sanitize_for_json(raw, environ={}) == expected
    assert sanitize_for_persistence(raw, environ={}) == expected
    rendered = sanitize_for_terminal(raw, environ={})
    assert "must" not in rendered
    assert "12345" not in rendered
    assert rendered.count(REDACTED) == 6


def test_sensitive_modes_reject_every_bit_outside_0600(tmp_path: Path) -> None:
    plan = plan_data()
    plan["target_mode"] = 0o700
    with pytest.raises(SchemaError, match="outside 0600"):
        validate_plan_item(plan)

    managed = managed_data()
    managed["mode"] = 0o700
    with pytest.raises(SchemaError, match="outside 0600"):
        validate_managed_manifest(
            {
                "schema_version": 1,
                "kind": "managed-manifest",
                "generated_at": "now",
                "items": [managed],
            }
        )

    root = tmp_path / "home"
    root.mkdir()
    target = root / "secret"
    with pytest.raises(ValueError, match="outside 0600"):
        stage_bytes(target, b"secret", root=root, mode=0o700, sensitive=True)
    with pytest.raises(ValueError, match="outside 0600"):
        atomic_write(target, b"secret", root=root, mode=0o700, sensitive=True)

    staged = stage_bytes(target, b"secret", root=root, mode=0o700)
    try:
        with pytest.raises(ValueError, match="outside 0600"):
            atomic_replace(staged, target, root=root, mode=0o700, sensitive=True)
    finally:
        staged.cleanup()
    assert not target.exists()


def test_atomic_parent_swap_cannot_redirect_replace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "home"
    parent = root / "app"
    parent.mkdir(parents=True)
    target = parent / "config.json"
    target.write_text('{"original":true}', encoding="utf-8")
    pinned_parent = root / "app-pinned"
    real_replace = os.replace
    swapped = False

    def swap_parent_then_replace(source, destination, *args, **kwargs):
        nonlocal swapped
        if not swapped:
            swapped = True
            parent.rename(pinned_parent)
            parent.mkdir()
            (parent / "config.json").write_text('{"redirected":false}', encoding="utf-8")
        return real_replace(source, destination, *args, **kwargs)

    monkeypatch.setattr(atomic_module.os, "replace", swap_parent_then_replace)
    with pytest.raises(RuntimeError, match="visible target parent changed"):
        atomic_write(target, '{"replacement":true}', root=root, format="json")

    assert (pinned_parent / "config.json").read_text(encoding="utf-8") == '{"original":true}'
    assert (parent / "config.json").read_text(encoding="utf-8") == '{"redirected":false}'
    assert not list(parent.glob(".*.dotf-stage-*"))
    assert not list(pinned_parent.glob(".*.dotf-stage-*"))


def test_directory_backup_preserves_nested_symlinks_without_traversal(tmp_path: Path) -> None:
    root = tmp_path / "home"
    source = root / "tree"
    outside = tmp_path / "outside"
    source.mkdir(parents=True)
    outside.mkdir()
    victim = outside / "victim"
    victim.write_text("outside", encoding="utf-8")
    (source / "link").symlink_to(victim)
    (source / "regular").write_text("inside", encoding="utf-8")

    destination = backup_target(source, root / "backups", generate_run_id(), root)

    assert (destination / "link").is_symlink()
    assert os.readlink(destination / "link") == str(victim)
    assert (destination / "regular").read_text(encoding="utf-8") == "inside"
    assert victim.read_text(encoding="utf-8") == "outside"


def test_remove_source_directory_mutation_restores_exact_quarantined_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "home"
    nested = root / "tree" / "nested"
    nested.mkdir(parents=True)
    owned = nested / "owned"
    owned.write_text("original", encoding="utf-8")
    original_inode = owned.stat().st_ino
    backup_root = root / "backups"
    real_apply_modes = backup_module._apply_backup_modes

    def apply_modes_then_mutate_candidate(parent_fd, name, expected, file_mode):
        result = real_apply_modes(parent_fd, name, expected, file_mode)
        if stat.S_ISDIR(expected.st_mode) and name.startswith("tree."):
            moved_owned = next(backup_root.rglob("owned"))
            moved_owned.write_text("mutated!", encoding="utf-8")
            assert moved_owned.stat().st_ino == original_inode
        return result

    monkeypatch.setattr(backup_module, "_apply_backup_modes", apply_modes_then_mutate_candidate)
    with pytest.raises(RuntimeError, match="source content changed while finalizing backup"):
        backup_target(root / "tree", backup_root, generate_run_id(), root, remove_source=True)

    restored = root / "tree" / "nested" / "owned"
    assert restored.read_text(encoding="utf-8") == "mutated!"
    assert restored.stat().st_ino == original_inode
    assert not list(root.glob(".tree.dotf-quarantine-*"))
    assert not [path for path in backup_root.rglob("*") if path.is_file() or path.is_symlink()]


def test_remove_source_directory_renames_exact_tree_without_child_unlinks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "home"
    source = root / "tree"
    nested = source / "nested"
    nested.mkdir(parents=True, mode=0o755)
    first = nested / "first"
    second = nested / "second"
    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")
    os.chmod(first, 0o644)
    os.chmod(second, 0o644)
    outside = tmp_path / "outside"
    outside.mkdir()
    victim = outside / "victim"
    victim.write_text("outside", encoding="utf-8")
    os.chmod(victim, 0o644)
    link = nested / "link"
    link.symlink_to(victim)

    original_tree = source.stat()
    original_first = first.stat()
    original_second = second.stat()
    original_link = link.lstat()
    real_unlink = backup_module.os.unlink
    child_unlinks: list[str] = []

    def fail_second_child_unlink(path, *args, **kwargs):
        name = os.fspath(path)
        if ".dotf-quarantine-" in name and ("first" in name or "second" in name):
            child_unlinks.append(name)
            if len(child_unlinks) == 2:
                raise OSError("injected second-child unlink failure")
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(backup_module.os, "unlink", fail_second_child_unlink)
    backup_root = root / "backups"
    destination = backup_target(source, backup_root, generate_run_id(), root, remove_source=True)

    assert child_unlinks == []
    assert not os.path.lexists(source)
    assert (destination.stat().st_dev, destination.stat().st_ino) == (
        original_tree.st_dev,
        original_tree.st_ino,
    )
    assert (destination / "nested" / "first").stat().st_ino == original_first.st_ino
    assert (destination / "nested" / "second").stat().st_ino == original_second.st_ino
    assert (destination / "nested" / "link").lstat().st_ino == original_link.st_ino
    assert os.readlink(destination / "nested" / "link") == str(victim)
    assert victim.read_text(encoding="utf-8") == "outside"
    assert stat.S_IMODE(victim.stat().st_mode) == 0o644
    assert stat.S_IMODE(destination.stat().st_mode) == 0o700
    assert stat.S_IMODE((destination / "nested").stat().st_mode) == 0o700
    assert stat.S_IMODE((destination / "nested" / "first").stat().st_mode) == 0o600
    assert stat.S_IMODE((destination / "nested" / "second").stat().st_mode) == 0o600
    assert list(destination.parent.iterdir()) == [destination]
    assert not [path for path in root.rglob("*") if ".dotf-quarantine-" in path.name]


@pytest.mark.parametrize("failure_entry", ["second", "root"])
def test_remove_source_mode_failure_restores_all_original_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_entry: str
) -> None:
    root = tmp_path / "home"
    source = root / "tree"
    nested = source / "nested"
    nested.mkdir(parents=True)
    first = nested / "first"
    second = nested / "second"
    first.write_bytes(b"one")
    second.write_bytes(b"two")
    os.chmod(source, 0o755)
    os.chmod(nested, 0o751)
    os.chmod(first, 0o644)
    os.chmod(second, 0o640)

    paths = (source, nested, first, second)
    before = {
        path.relative_to(root): (
            path.stat().st_dev,
            path.stat().st_ino,
            stat.S_IMODE(path.stat().st_mode),
            path.read_bytes() if path.is_file() else None,
        )
        for path in paths
    }
    failure_inode = (second if failure_entry == "second" else source).stat().st_ino
    failure_mode = 0o600 if failure_entry == "second" else 0o700
    real_fchmod = backup_module.os.fchmod
    injected = False

    def fail_selected_mode_once(fd: int, mode: int) -> None:
        nonlocal injected
        if not injected and os.fstat(fd).st_ino == failure_inode and mode == failure_mode:
            injected = True
            raise OSError(f"injected {failure_entry} chmod failure")
        real_fchmod(fd, mode)

    monkeypatch.setattr(backup_module.os, "fchmod", fail_selected_mode_once)
    backup_root = root / "backups"
    with pytest.raises(OSError, match=f"injected {failure_entry} chmod failure"):
        backup_target(source, backup_root, generate_run_id(), root, remove_source=True)

    assert injected
    for relative, expected in before.items():
        restored = root / relative
        restored_stat = restored.stat()
        actual = (
            restored_stat.st_dev,
            restored_stat.st_ino,
            stat.S_IMODE(restored_stat.st_mode),
            restored.read_bytes() if restored.is_file() else None,
        )
        assert actual == expected
    assert not [path for path in backup_root.rglob("tree.*")]
    assert not [path for path in root.rglob("*") if ".dotf-quarantine-" in path.name]


def test_directory_root_symlink_swap_is_detected_before_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "home"
    source = root / "tree"
    source.mkdir(parents=True)
    (source / "owned").write_text("original", encoding="utf-8")
    moved = root / "tree-original"
    outside = tmp_path / "outside"
    outside.mkdir()
    victim = outside / "victim"
    victim.write_text("outside", encoding="utf-8")
    real_apply_modes = backup_module._apply_backup_modes
    swapped = False

    def apply_modes_after_live_name_swap(parent_fd, name, expected, file_mode):
        nonlocal swapped
        if not swapped:
            swapped = True
            source.symlink_to(outside, target_is_directory=True)
        return real_apply_modes(parent_fd, name, expected, file_mode)

    monkeypatch.setattr(backup_module, "_apply_backup_modes", apply_modes_after_live_name_swap)
    with pytest.raises(RuntimeError, match="live name reappeared"):
        backup_target(source, root / "backups", generate_run_id(), root, remove_source=True)

    assert source.is_dir() and not source.is_symlink()
    assert source.joinpath("owned").read_text(encoding="utf-8") == "original"
    displaced_links = list(root.glob(".tree-conflict.dotf-quarantine-*"))
    assert len(displaced_links) == 1 and displaced_links[0].is_symlink()
    assert victim.read_text(encoding="utf-8") == "outside"


def test_nested_directory_symlink_swap_is_rejected_without_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "home"
    source = root / "tree"
    nested = source / "nested"
    nested.mkdir(parents=True)
    (nested / "owned").write_text("inside", encoding="utf-8")
    moved = source / "nested-original"
    outside = tmp_path / "outside"
    outside.mkdir()
    victim = outside / "victim"
    victim.write_text("outside", encoding="utf-8")
    real_open = backup_module._open_checked
    nested_open_count = 0

    def swap_before_second_nested_open(parent_fd, name, expected, *, directory):
        nonlocal nested_open_count
        if name == "nested" and directory:
            nested_open_count += 1
            if nested_open_count == 2:
                nested.rename(moved)
                nested.symlink_to(outside, target_is_directory=True)
        return real_open(parent_fd, name, expected, directory=directory)

    monkeypatch.setattr(backup_module, "_open_checked", swap_before_second_nested_open)
    with pytest.raises((PathBoundaryError, RuntimeError)):
        backup_target(source, root / "backups", generate_run_id(), root)

    assert nested.is_symlink()
    assert moved.joinpath("owned").read_text(encoding="utf-8") == "inside"
    assert victim.read_text(encoding="utf-8") == "outside"


def test_same_type_source_replacement_is_not_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "home"
    root.mkdir()
    source = root / "config"
    source.write_text("original", encoding="utf-8")
    moved = root / "config-original"
    real_apply_modes = backup_module._apply_backup_modes
    replaced = False

    def apply_modes_after_live_name_replace(parent_fd, name, expected, file_mode):
        nonlocal replaced
        if not replaced:
            replaced = True
            source.write_text("replacement", encoding="utf-8")
        return real_apply_modes(parent_fd, name, expected, file_mode)

    monkeypatch.setattr(backup_module, "_apply_backup_modes", apply_modes_after_live_name_replace)
    with pytest.raises(RuntimeError, match="live name reappeared"):
        backup_target(source, root / "backups", generate_run_id(), root, remove_source=True)

    assert source.read_text(encoding="utf-8") == "original"
    displaced = list(root.glob(".config-conflict.dotf-quarantine-*"))
    assert len(displaced) == 1
    assert displaced[0].read_text(encoding="utf-8") == "replacement"


def test_staged_same_name_same_type_replacement_is_rejected_before_commit(tmp_path: Path) -> None:
    root = tmp_path / "home"
    root.mkdir()
    target = root / "config.json"
    target.write_text('{"original":true}', encoding="utf-8")
    staged = stage_bytes(target, b'{"validated":true}', root=root, format="json")
    displaced = root / "displaced-stage"
    staged.path.rename(displaced)
    staged.path.write_text('{"attacker":true}', encoding="utf-8")

    with pytest.raises(RuntimeError, match="staging entry changed"):
        atomic_replace(staged, target, root=root, mode=0o600)

    assert target.read_text(encoding="utf-8") == '{"original":true}'
    assert staged.path.read_text(encoding="utf-8") == '{"attacker":true}'
    assert displaced.read_text(encoding="utf-8") == '{"validated":true}'


def test_staged_in_place_mutation_cannot_commit_unvalidated_bytes(tmp_path: Path) -> None:
    root = tmp_path / "home"
    root.mkdir()
    target = root / "config.json"
    target.write_text('{"original":true}', encoding="utf-8")
    staged = stage_bytes(target, b'{"validated":true}', root=root, format="json")
    staged.path.write_text('{"mutated":true}', encoding="utf-8")

    with pytest.raises(RuntimeError, match="staging content changed after validation"):
        atomic_replace(staged, target, root=root, mode=0o600)

    assert target.read_text(encoding="utf-8") == '{"original":true}'
    assert not staged.path.exists()


def test_atomic_backup_captures_late_same_inode_bytes_from_quarantine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "home"
    root.mkdir()
    target = root / "config.json"
    target.write_text('{"original":true}', encoding="utf-8")
    original_inode = target.stat().st_ino
    backup_root = root / "backups"
    real_replace = atomic_module.os.replace
    injected = False

    def mutate_old_at_quarantine_replace(source, destination, *args, **kwargs):
        nonlocal injected
        if not injected and source == "config.json" and ".dotf-quarantine-" in destination:
            injected = True
            target.write_text('{"late-old":true}', encoding="utf-8")
            assert target.stat().st_ino == original_inode
        return real_replace(source, destination, *args, **kwargs)

    monkeypatch.setattr(atomic_module.os, "replace", mutate_old_at_quarantine_replace)
    result = atomic_write(
        target,
        '{"replacement":true}',
        root=root,
        format="json",
        backup_root=backup_root,
        run_id=generate_run_id(),
    )

    assert result.status == "changed"
    assert result.backup is not None
    assert result.backup.read_text(encoding="utf-8") == '{"late-old":true}'
    assert target.read_text(encoding="utf-8") == '{"replacement":true}'
    assert not list(root.glob(".config.json.dotf-quarantine-*"))


def test_atomic_late_quarantine_mutation_rolls_back_and_discards_stale_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "home"
    root.mkdir()
    target = root / "config.json"
    target.write_text('{"original":true}', encoding="utf-8")
    original_inode = target.stat().st_ino
    backup_root = root / "backups"
    real_visible_check = atomic_module._require_visible_target
    visible_checks = 0

    def mutate_quarantine_after_backup(*args, **kwargs):
        nonlocal visible_checks
        visible_checks += 1
        real_visible_check(*args, **kwargs)
        if visible_checks == 2:
            quarantine = next(root.glob(".config.json.dotf-quarantine-*"))
            quarantine.write_text('{"late-old":true}', encoding="utf-8")
            assert quarantine.stat().st_ino == original_inode

    monkeypatch.setattr(atomic_module, "_require_visible_target", mutate_quarantine_after_backup)
    with pytest.raises(RuntimeError, match="old target changed before quarantine cleanup"):
        atomic_write(
            target,
            '{"replacement":true}',
            root=root,
            format="json",
            backup_root=backup_root,
            run_id=generate_run_id(),
        )

    assert target.stat().st_ino == original_inode
    assert target.read_text(encoding="utf-8") == '{"late-old":true}'
    assert not list(root.glob(".config.json.dotf-quarantine-*"))
    assert not [path for path in backup_root.rglob("*") if path.is_file() or path.is_symlink()]


def test_stage_mutation_at_replace_boundary_rolls_back_exact_old_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "home"
    root.mkdir()
    target = root / "config.json"
    target.write_text('{"original":true}', encoding="utf-8")
    original_inode = target.stat().st_ino
    backup_root = root / "backups"
    real_replace = atomic_module.os.replace
    injected = False

    def mutate_stage_then_replace(source, destination, *args, **kwargs):
        nonlocal injected
        if not injected and ".dotf-stage-" in source and destination == "config.json":
            injected = True
            stage = next(root.glob(".config.json.dotf-stage-*"))
            stage.write_text('{"attacker":true}', encoding="utf-8")
        return real_replace(source, destination, *args, **kwargs)

    monkeypatch.setattr(atomic_module.os, "replace", mutate_stage_then_replace)
    with pytest.raises(RuntimeError, match="committed target content differs"):
        atomic_write(
            target,
            '{"validated":true}',
            root=root,
            format="json",
            backup_root=backup_root,
            run_id=generate_run_id(),
        )

    assert target.stat().st_ino == original_inode
    assert target.read_text(encoding="utf-8") == '{"original":true}'
    assert not list(root.glob(".config.json.dotf-stage-*"))
    assert not list(root.glob(".config.json.dotf-quarantine-*"))
    assert not list(root.glob(".config.json.dotf-failed-*"))
    assert not backup_root.exists()


def test_atomic_write_backup_uses_pinned_parent_and_aborts_visible_parent_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "home"
    parent = root / "app"
    parent.mkdir(parents=True)
    target = parent / "config.json"
    target.write_text('{"original":true}', encoding="utf-8")
    pinned_parent = root / "app-original"
    backup_root = root / "backups"
    real_copy = backup_module._copy_to_candidate
    swapped = False

    def swap_visible_parent_before_copy(*args, **kwargs):
        nonlocal swapped
        if not swapped:
            swapped = True
            parent.rename(pinned_parent)
            parent.mkdir()
            target.write_text('{"replacement":true}', encoding="utf-8")
        return real_copy(*args, **kwargs)

    monkeypatch.setattr(backup_module, "_copy_to_candidate", swap_visible_parent_before_copy)
    with pytest.raises(RuntimeError, match="visible target parent changed"):
        atomic_write(
            target,
            '{"new":true}',
            root=root,
            format="json",
            backup_root=backup_root,
            run_id=generate_run_id(),
        )

    assert (pinned_parent / "config.json").read_text(encoding="utf-8") == '{"original":true}'
    assert target.read_text(encoding="utf-8") == '{"replacement":true}'
    backups = [path for path in backup_root.rglob("config.json.*") if path.is_file()]
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == '{"original":true}'
    assert not list(pinned_parent.glob(".*.dotf-stage-*"))


def test_backup_detects_same_inode_in_place_source_mutation_and_keeps_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "home"
    root.mkdir()
    source = root / "config"
    source.write_text("original", encoding="utf-8")
    original_inode = source.stat().st_ino
    backup_root = root / "backups"
    real_apply_modes = backup_module._apply_backup_modes
    mutated = False

    def apply_modes_then_mutate(parent_fd, name, expected, file_mode):
        nonlocal mutated
        result = real_apply_modes(parent_fd, name, expected, file_mode)
        if not mutated:
            mutated = True
            moved_fd = os.open(name, os.O_WRONLY, dir_fd=parent_fd)
            try:
                os.ftruncate(moved_fd, 0)
                os.write(moved_fd, b"mutated!")
                os.fsync(moved_fd)
                assert os.fstat(moved_fd).st_ino == original_inode
            finally:
                os.close(moved_fd)
        return result

    monkeypatch.setattr(backup_module, "_apply_backup_modes", apply_modes_then_mutate)
    with pytest.raises(RuntimeError, match="source content changed while finalizing backup"):
        backup_target(source, backup_root, generate_run_id(), root, remove_source=True)

    assert source.read_text(encoding="utf-8") == "mutated!"
    assert source.stat().st_ino == original_inode
    assert not [path for path in backup_root.rglob("*") if path.is_file() or path.is_symlink()]


def test_backup_rejects_destination_digest_mismatch_and_keeps_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "home"
    root.mkdir()
    source = root / "config"
    source.write_text("original", encoding="utf-8")
    backup_root = root / "backups"
    real_candidate_digest = backup_module._candidate_digest
    injected = False

    def report_mismatched_destination_digest(destination_parent_fd, name, expected_type):
        nonlocal injected
        item, actual_digest = real_candidate_digest(destination_parent_fd, name, expected_type)
        if not injected:
            injected = True
            return item, "0" * len(actual_digest)
        return item, actual_digest

    monkeypatch.setattr(backup_module, "_candidate_digest", report_mismatched_destination_digest)
    with pytest.raises(RuntimeError, match="backup destination digest differs"):
        backup_target(source, backup_root, generate_run_id(), root, remove_source=True)

    assert source.read_text(encoding="utf-8") == "original"
    assert not [path for path in backup_root.rglob("*") if path.is_file() or path.is_symlink()]
