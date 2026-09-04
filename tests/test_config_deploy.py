"""Focused contracts for registry-driven config plan/apply (OpenSpec 2.3-2.5)."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

import pytest

from dotf_core.config_deploy import (
    CONFIG_MANIFEST_NAME,
    ConfigConflictError,
    ConfigDeployError,
    MalformedConfigManifest,
    ProducedContent,
    ProducedFile,
    UnsafeConfigHandlerError,
    apply_config_plan,
    compile_config_plan,
)
from dotf_core.paths import PathBoundaryError
from dotf_core.schemas import validate_managed_manifest


def _module(source: Path, target: Path, **updates: Any) -> dict[str, Any]:
    config: dict[str, Any] = {
        "source": str(source),
        "target": str(target),
        "strategy": "copy",
        "writable": True,
        "sensitive": False,
        "target_mode": "0755" if source.is_dir() else "0644",
        "preserve": [],
        "exclude": [],
    }
    config.update(updates)
    return {"name": "fixture", "config": config}


def _roots(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    state = home / ".state"
    repo.mkdir()
    home.mkdir()
    return repo, home, state


def _manifest(state: Path) -> dict[str, Any]:
    return json.loads((state / "dotf" / CONFIG_MANIFEST_NAME).read_text(encoding="utf-8"))


def _tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for entry in sorted(path.rglob("*")):
        relative = str(entry.relative_to(path))
        item = entry.lstat()
        digest.update(relative.encode() + b"\0" + str(stat.S_IFMT(item.st_mode)).encode() + b"\0")
        if entry.is_symlink():
            digest.update(os.fsencode(os.readlink(entry)))
        elif entry.is_file():
            digest.update(entry.read_bytes())
    return digest.hexdigest()


def test_copy_plan_is_side_effect_free_and_apply_is_file_hash_idempotent(tmp_path: Path) -> None:
    repo, home, state = _roots(tmp_path)
    source = repo / "config"
    source.mkdir()
    (source / "one.toml").write_text("value = 1\n", encoding="utf-8")
    nested = source / "nested"
    nested.mkdir()
    (nested / "two.txt").write_text("two\n", encoding="utf-8")
    target = home / ".config" / "fixture"
    module = _module(source, target)

    plan = compile_config_plan(module, repo_root=repo, home=home, state_home=state)
    assert plan.status == "changed"
    assert [op.operation for op in plan.operations] == ["create-root", "write", "write"]
    assert not target.exists()
    assert not state.exists()

    first = apply_config_plan(plan, repo_root=repo, home=home, state_home=state, run_id="run-1")
    assert first.status == "changed"
    assert first.backups == ()
    one = target / "one.toml"
    two = target / "nested" / "two.txt"
    before = {path: (path.stat().st_ino, path.stat().st_mtime_ns) for path in (one, two)}
    manifest_before = (state / "dotf" / CONFIG_MANIFEST_NAME).read_bytes()
    parsed = validate_managed_manifest(_manifest(state))
    assert {item.target for item in parsed.items} == {str(one), str(two)}
    assert all(item.expected_hash == item.installed_hash for item in parsed.items)

    second_plan = compile_config_plan(module, repo_root=repo, home=home, state_home=state)
    assert second_plan.status == "unchanged"
    second = apply_config_plan(
        second_plan, repo_root=repo, home=home, state_home=state, run_id="run-2"
    )
    assert second.status == "unchanged"
    assert second.backups == ()
    assert before == {path: (path.stat().st_ino, path.stat().st_mtime_ns) for path in (one, two)}
    assert (state / "dotf" / CONFIG_MANIFEST_NAME).read_bytes() == manifest_before
    assert not (home / ".local" / "state" / "dotf" / "backups").exists()


def test_copy_update_uses_managed_hash_and_stale_reconcile_is_conservative(tmp_path: Path) -> None:
    repo, home, state = _roots(tmp_path)
    source = repo / "config"
    source.mkdir()
    source_file = source / "managed.txt"
    source_file.write_text("one", encoding="utf-8")
    target = home / ".config" / "fixture"
    module = _module(source, target)
    apply_config_plan(
        compile_config_plan(module, repo_root=repo, home=home, state_home=state),
        repo_root=repo,
        home=home,
        state_home=state,
        run_id="run-1",
    )

    source_file.write_text("two", encoding="utf-8")
    update = compile_config_plan(module, repo_root=repo, home=home, state_home=state)
    write = next(op for op in update.operations if op.operation == "write")
    assert (write.item.state, write.item.action) == ("update", "update")
    result = apply_config_plan(update, repo_root=repo, home=home, state_home=state, run_id="run-2")
    assert (target / "managed.txt").read_text(encoding="utf-8") == "two"
    assert len(result.backups) == 1
    assert result.backups[0].read_text(encoding="utf-8") == "one"

    source_file.unlink()
    stale = compile_config_plan(module, repo_root=repo, home=home, state_home=state)
    prune = next(op for op in stale.operations if op.operation == "prune")
    assert (prune.item.state, prune.item.action) == ("prune", "prune")
    apply_config_plan(stale, repo_root=repo, home=home, state_home=state, run_id="run-3")
    assert not (target / "managed.txt").exists()
    assert _manifest(state)["items"] == []


def test_unowned_modified_and_stale_modified_targets_are_conflicts(tmp_path: Path) -> None:
    repo, home, state = _roots(tmp_path)
    source = repo / "config"
    source.mkdir()
    (source / "managed.txt").write_text("expected", encoding="utf-8")
    target = home / ".config" / "fixture"
    target.mkdir(parents=True)
    actual = target / "managed.txt"
    actual.write_text("foreign", encoding="utf-8")
    module = _module(source, target)

    unowned = compile_config_plan(module, repo_root=repo, home=home, state_home=state)
    assert unowned.status == "conflict"
    assert unowned.conflicts[0].conflict_reason == "unowned-real-target"
    with pytest.raises(ConfigConflictError):
        apply_config_plan(unowned, repo_root=repo, home=home, state_home=state)
    assert actual.read_text(encoding="utf-8") == "foreign"

    actual.unlink()
    initial = compile_config_plan(module, repo_root=repo, home=home, state_home=state)
    apply_config_plan(initial, repo_root=repo, home=home, state_home=state, run_id="run-1")
    (source / "managed.txt").unlink()
    actual.write_text("user edit", encoding="utf-8")
    stale = compile_config_plan(module, repo_root=repo, home=home, state_home=state)
    assert stale.status == "conflict"
    assert stale.conflicts[0].conflict_reason == "stale-target-modified-or-unsafe"
    with pytest.raises(ConfigConflictError):
        apply_config_plan(stale, repo_root=repo, home=home, state_home=state)
    assert actual.read_text(encoding="utf-8") == "user edit"


def test_malformed_or_symlinked_manifest_fails_closed_without_target_write(tmp_path: Path) -> None:
    repo, home, state = _roots(tmp_path)
    source = repo / "config.txt"
    source.write_text("expected", encoding="utf-8")
    target = home / ".config" / "config.txt"
    module = _module(source, target)
    manifest_dir = state / "dotf"
    manifest_dir.mkdir(parents=True)
    manifest = manifest_dir / CONFIG_MANIFEST_NAME
    manifest.write_text('{"schema_version": 99}', encoding="utf-8")

    with pytest.raises(MalformedConfigManifest):
        compile_config_plan(module, repo_root=repo, home=home, state_home=state)
    assert not target.exists()

    manifest.unlink()
    outside = tmp_path / "outside-manifest"
    outside.write_text("{}", encoding="utf-8")
    manifest.symlink_to(outside)
    with pytest.raises(PathBoundaryError):
        compile_config_plan(module, repo_root=repo, home=home, state_home=state)
    assert outside.read_text(encoding="utf-8") == "{}"


def test_render_producer_returns_data_but_cannot_control_safety_path_or_mode(tmp_path: Path) -> None:
    repo, home, state = _roots(tmp_path)
    source = repo / "template.json"
    source.write_text('{"public": true}\n', encoding="utf-8")
    target = home / ".config" / "tool" / "config.json"
    module = _module(
        source,
        target,
        strategy="render",
        sensitive=True,
        target_mode="0600",
    )

    def render(context):
        assert context.source_files["."] == b'{"public": true}\n'
        assert dict(context.actual_files) == {}
        return ProducedContent({"rendered": True}, format="json", mode=0o600)

    plan = compile_config_plan(
        module, repo_root=repo, home=home, state_home=state, producer=render
    )
    result = apply_config_plan(plan, repo_root=repo, home=home, state_home=state, run_id="render-1")
    assert result.status == "changed"
    assert json.loads(target.read_text(encoding="utf-8")) == {"rendered": True}
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    item = validate_managed_manifest(_manifest(state)).items[0]
    assert item.strategy == "render" and item.sensitive is True

    directory_source = repo / "templates"
    directory_source.mkdir()
    (directory_source / "input.txt").write_text("input", encoding="utf-8")
    directory_module = _module(
        directory_source,
        home / ".config" / "other",
        strategy="render",
        sensitive=True,
        target_mode="0700",
    )
    with pytest.raises(ConfigDeployError, match="unsafe producer path"):
        compile_config_plan(
            directory_module,
            repo_root=repo,
            home=home,
            state_home=state,
            producer=lambda _context: [ProducedFile("../escape", b"bad")],
        )
    with pytest.raises(ConfigDeployError, match="broadens"):
        compile_config_plan(
            directory_module,
            repo_root=repo,
            home=home,
            state_home=state,
            producer=lambda _context: [ProducedFile("output", b"bad", mode=0o644)],
        )
    assert not (home / ".config" / "escape").exists()


def test_producer_audit_skips_preserved_runtime_subtrees(tmp_path: Path) -> None:
    repo, home, state = _roots(tmp_path)
    source = repo / "template"
    source.mkdir()
    (source / "config.json").write_text("{}\n", encoding="utf-8")
    target = home / ".config" / "tool"
    runtime = target / "sessions" / "large-runtime-state"
    runtime.parent.mkdir(parents=True)
    runtime.write_text("keep", encoding="utf-8")
    module = _module(
        source,
        target,
        strategy="merge",
        target_mode="0700",
        preserve=["sessions"],
    )

    def producer(context):
        # A runtime writer is outside this producer's managed input/output
        # boundary, so it must not turn a config plan into a false conflict.
        runtime.write_text("updated-by-runtime", encoding="utf-8")
        return [ProducedFile("config.json", context.source_files["config.json"], format="json")]

    plan = compile_config_plan(
        module, repo_root=repo, home=home, state_home=state, producer=producer
    )
    assert plan.status == "changed"
    assert runtime.read_text(encoding="utf-8") == "updated-by-runtime"

def test_unsafe_specialized_direct_write_is_detected_and_not_manifested(tmp_path: Path) -> None:
    repo, home, state = _roots(tmp_path)
    source = repo / "template.json"
    source.write_text("{}\n", encoding="utf-8")
    target = home / ".config" / "tool" / "config.json"
    module = _module(source, target, strategy="merge", target_mode="0644")

    def unsafe(_context):
        target.parent.mkdir(parents=True)
        target.write_text('{"bypassed": true}\n', encoding="utf-8")
        return b"{}\n"

    with pytest.raises(UnsafeConfigHandlerError, match="direct"):
        compile_config_plan(
            module, repo_root=repo, home=home, state_home=state, producer=unsafe
        )
    assert json.loads(target.read_text(encoding="utf-8")) == {"bypassed": True}
    assert not state.exists()


def test_legacy_exact_directory_link_is_explicitly_migrated_without_repo_mutation(tmp_path: Path) -> None:
    repo, home, state = _roots(tmp_path)
    source = repo / "config"
    source.mkdir()
    (source / "managed.txt").write_text("repository bytes", encoding="utf-8")
    source_before = _tree_digest(source)
    target = home / ".config" / "fixture"
    target.parent.mkdir(parents=True)
    target.symlink_to(source, target_is_directory=True)
    module = _module(source, target)

    plan = compile_config_plan(module, repo_root=repo, home=home, state_home=state)
    migration = plan.operations[0]
    assert migration.operation == "migrate-link"
    assert (migration.item.state, migration.item.action) == ("update", "update")
    assert target.is_symlink()
    result = apply_config_plan(plan, repo_root=repo, home=home, state_home=state, run_id="migrate-1")

    assert result.status == "changed"
    assert target.is_dir() and not target.is_symlink()
    assert (target / "managed.txt").read_text(encoding="utf-8") == "repository bytes"
    assert source.is_dir() and (source / "managed.txt").read_text(encoding="utf-8") == "repository bytes"
    assert _tree_digest(source) == source_before


def test_legacy_foreign_link_and_unowned_real_root_default_to_conflict(tmp_path: Path) -> None:
    repo, home, state = _roots(tmp_path)
    source = repo / "config"
    source.mkdir()
    (source / "managed.txt").write_text("repo", encoding="utf-8")
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    victim = foreign / "victim"
    victim.write_text("keep", encoding="utf-8")
    target = home / ".config" / "fixture"
    target.parent.mkdir(parents=True)
    target.symlink_to(foreign, target_is_directory=True)
    module = _module(source, target)

    link_plan = compile_config_plan(module, repo_root=repo, home=home, state_home=state)
    assert link_plan.status == "conflict"
    assert link_plan.conflicts[0].conflict_reason == "foreign-directory-symlink"
    with pytest.raises(ConfigConflictError):
        apply_config_plan(link_plan, repo_root=repo, home=home, state_home=state)
    assert target.is_symlink()
    assert victim.read_text(encoding="utf-8") == "keep"

    target.unlink()
    target.write_text("foreign real leaf", encoding="utf-8")
    real_plan = compile_config_plan(module, repo_root=repo, home=home, state_home=state)
    assert real_plan.status == "conflict"
    assert real_plan.conflicts[0].conflict_reason == "unowned-real-target"
    with pytest.raises(ConfigConflictError):
        apply_config_plan(real_plan, repo_root=repo, home=home, state_home=state)
    assert target.read_text(encoding="utf-8") == "foreign real leaf"
    assert (source / "managed.txt").read_text(encoding="utf-8") == "repo"


def test_single_file_producer_receives_owned_existing_actual_bytes(tmp_path: Path) -> None:
    repo, home, state = _roots(tmp_path)
    source = repo / "template.json"
    source.write_text('{"managed": true}\n', encoding="utf-8")
    target = home / ".config" / "tool" / "config.json"
    module = _module(source, target, strategy="merge", target_mode="0644")
    expected = b'{"local": "preserved", "managed": true}\n'
    seen: list[dict[str, bytes]] = []

    def merge(context):
        actual = dict(context.actual_files)
        seen.append(actual)
        if not actual:
            return expected
        assert actual["."] == expected
        return actual["."]

    initial = compile_config_plan(
        module, repo_root=repo, home=home, state_home=state, producer=merge
    )
    assert seen == [{}]
    apply_config_plan(
        initial,
        repo_root=repo,
        home=home,
        state_home=state,
        run_id="merge-owned-1",
    )

    repeated = compile_config_plan(
        module, repo_root=repo, home=home, state_home=state, producer=merge
    )
    assert seen[-1] == {".": expected}
    assert repeated.status == "unchanged"


def test_single_file_producer_receives_unowned_existing_actual_bytes_before_conflict(
    tmp_path: Path,
) -> None:
    repo, home, state = _roots(tmp_path)
    source = repo / "template.toml"
    source.write_text("managed = true\n", encoding="utf-8")
    target = home / ".config" / "tool" / "config.toml"
    target.parent.mkdir(parents=True)
    existing = b'local = "keep"\n'
    target.write_bytes(existing)
    module = _module(source, target, strategy="merge", target_mode="0644")

    def merge(context):
        assert context.actual_files["."] == existing
        return context.actual_files["."] + context.source_files["."]

    plan = compile_config_plan(
        module, repo_root=repo, home=home, state_home=state, producer=merge
    )
    assert plan.status == "conflict"
    assert plan.conflicts[0].conflict_reason == "unowned-real-target"
    assert target.read_bytes() == existing


def test_single_file_producer_rejects_target_symlink_without_callback(
    tmp_path: Path,
) -> None:
    repo, home, state = _roots(tmp_path)
    source = repo / "template.json"
    source.write_text("{}\n", encoding="utf-8")
    target = home / ".config" / "tool" / "config.json"
    target.parent.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    outside.write_text('{"secret": true}\n', encoding="utf-8")
    target.symlink_to(outside)
    module = _module(source, target, strategy="render", target_mode="0644")
    called = False

    def render(_context):
        nonlocal called
        called = True
        return b"{}\n"

    with pytest.raises(PathBoundaryError, match="must not be a symbolic link"):
        compile_config_plan(
            module, repo_root=repo, home=home, state_home=state, producer=render
        )
    assert called is False
    assert target.is_symlink()
    assert outside.read_text(encoding="utf-8") == '{"secret": true}\n'


def test_logseq_producer_preserves_private_json_fields_after_managed_install(
    repo_root: Path, tmp_path: Path
) -> None:
    import modules
    from dotf_core.config_producers import producer_for

    repo, home, state = repo_root, tmp_path / "home", tmp_path / "state"
    home.mkdir()
    module = next(item for item in modules.load_registry() if item["name"] == "logseq")
    producer = producer_for("logseq", repo_root=repo, home=home)
    initial = compile_config_plan(
        module, repo_root=repo, home=home, state_home=state, producer=producer
    )
    apply_config_plan(initial, repo_root=repo, home=home, state_home=state, run_id="logseq-1")

    setting = home / ".logseq" / "settings" / "logseq-todoist-plugin.json"
    payload = json.loads(setting.read_text(encoding="utf-8"))
    assert payload["apiToken"] == ""
    payload["apiToken"] = "local-only-secret"
    payload["workspace"] = "/private/workspace"
    setting.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    merged = compile_config_plan(
        module, repo_root=repo, home=home, state_home=state, producer=producer
    )
    write = next(op for op in merged.operations if op.item.target == str(setting))
    assert write.content is not None
    expected = json.loads(write.content)
    assert expected["apiToken"] == "local-only-secret"
    assert expected["workspace"] == "/private/workspace"
    source_setting = repo / "config" / "tools" / "logseq" / "settings" / "logseq-todoist-plugin.json"
    source_payload = json.loads(source_setting.read_text(encoding="utf-8"))
    assert source_payload["apiToken"] == ""
    assert "local-only-secret" not in source_setting.read_text(encoding="utf-8")


def test_merge_requires_explicit_field_reconciliation_for_modified_owned_target(
    tmp_path: Path,
) -> None:
    repo, home, state = _roots(tmp_path)
    source = repo / "template.json"
    source.write_text('{"managed": true}\n', encoding="utf-8")
    target = home / ".config" / "tool" / "config.json"
    module = _module(source, target, strategy="merge", target_mode="0644")

    def merge(context):
        return ProducedContent(context.source_files["."], format="json")

    initial = compile_config_plan(
        module, repo_root=repo, home=home, state_home=state, producer=merge
    )
    apply_config_plan(
        initial, repo_root=repo, home=home, state_home=state, run_id="merge-safe-1"
    )
    target.write_text('{"managed": false, "local": true}\n', encoding="utf-8")

    conflict = compile_config_plan(
        module, repo_root=repo, home=home, state_home=state, producer=merge
    )
    assert conflict.status == "conflict"
    assert conflict.conflicts[0].conflict_reason == "managed-target-modified"
