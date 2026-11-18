"""Config owned 漂移：默认先备份再覆盖，`--on-conflict=block` 恢复拒绝；glob exclude。

见 docs/adr/0034-config-owned-drift-backup.md。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from dotf_core import config_handler
from dotf_core.config_deploy import (
    ConfigConflictError,
    ConfigDeployError,
    apply_config_plan,
    compile_config_plan,
    drift_backup_targets,
)


def _module(source: Path, target: Path, **updates: Any) -> dict[str, Any]:
    config: dict[str, Any] = {
        "source": str(source),
        "target": str(target),
        "strategy": "copy",
        "writable": True,
        "sensitive": False,
        "target_mode": "0755",
        "preserve": [],
        "exclude": [],
    }
    config.update(updates)
    return {"name": "fixture", "config": config}


def _deployed_then_edited(tmp_path: Path) -> tuple[dict[str, Any], Path, Path, Path, Path]:
    """copy 模块部署一次后，本机改了受管文件（那台机器 aliases.zsh 的最小复现）。"""
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    state = home / ".state"
    source = repo / "config"
    source.mkdir(parents=True)
    home.mkdir()
    (source / "aliases.zsh").write_text("alias a=1\n", encoding="utf-8")
    target = home / ".config" / "fixture"
    module = _module(source, target)
    apply_config_plan(
        compile_config_plan(module, repo_root=repo, home=home, state_home=state),
        repo_root=repo,
        home=home,
        state_home=state,
        run_id="first",
    )
    (source / "aliases.zsh").write_text("alias a=2\n", encoding="utf-8")
    edited = target / "aliases.zsh"
    edited.write_text("alias a=1\nalias local=1\n", encoding="utf-8")
    return module, repo, home, state, edited


def test_default_policy_still_blocks_owned_drift_with_hint(tmp_path: Path) -> None:
    module, repo, home, state, edited = _deployed_then_edited(tmp_path)
    plan = compile_config_plan(module, repo_root=repo, home=home, state_home=state)
    assert plan.conflicts[0].conflict_reason == "managed-target-modified"
    with pytest.raises(ConfigConflictError, match="--on-conflict=backup"):
        apply_config_plan(plan, repo_root=repo, home=home, state_home=state)
    assert edited.read_text(encoding="utf-8") == "alias a=1\nalias local=1\n"


def test_backup_policy_backs_up_local_edits_then_overwrites(tmp_path: Path) -> None:
    module, repo, home, state, edited = _deployed_then_edited(tmp_path)
    plan = compile_config_plan(
        module, repo_root=repo, home=home, state_home=state, on_conflict="backup"
    )
    assert not plan.conflicts
    assert drift_backup_targets(plan) == (str(edited),)

    result = apply_config_plan(plan, repo_root=repo, home=home, state_home=state, run_id="drift-1")
    assert result.status == "changed"
    assert edited.read_text(encoding="utf-8") == "alias a=2\n"
    [(target, backup)] = result.drift_backups
    assert target == str(edited)
    assert "drift-1" in str(backup)
    assert backup.read_text(encoding="utf-8") == "alias a=1\nalias local=1\n"

    again = compile_config_plan(module, repo_root=repo, home=home, state_home=state)
    assert again.status == "unchanged"


def test_backup_policy_rejects_edit_after_planning(tmp_path: Path) -> None:
    module, repo, home, state, edited = _deployed_then_edited(tmp_path)
    plan = compile_config_plan(
        module, repo_root=repo, home=home, state_home=state, on_conflict="backup"
    )
    edited.write_text("edited again\n", encoding="utf-8")
    with pytest.raises(ConfigConflictError, match="changed after planning"):
        apply_config_plan(plan, repo_root=repo, home=home, state_home=state)
    assert edited.read_text(encoding="utf-8") == "edited again\n"


def test_backup_policy_does_not_take_over_unowned_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    source = repo / "config"
    source.mkdir(parents=True)
    (source / "one.toml").write_text("value = 1\n", encoding="utf-8")
    target = home / ".config" / "fixture"
    target.mkdir(parents=True)
    (target / "one.toml").write_text("value = 999\n", encoding="utf-8")
    module = _module(source, target)

    plan = compile_config_plan(
        module, repo_root=repo, home=home, state_home=home / ".state", on_conflict="backup"
    )
    assert plan.conflicts[0].conflict_reason == "unowned-real-target"
    with pytest.raises(ConfigConflictError, match="--takeover=backup"):
        apply_config_plan(plan, repo_root=repo, home=home, state_home=home / ".state")


def test_untakeable_conflict_hint_asks_for_manual_handling(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    source = repo / "config"
    source.mkdir(parents=True)
    (source / "one.toml").write_text("value = 1\n", encoding="utf-8")
    target = home / ".config" / "fixture"
    (target / "one.toml").mkdir(parents=True)
    module = _module(source, target)

    plan = compile_config_plan(module, repo_root=repo, home=home, state_home=home / ".state")
    with pytest.raises(ConfigConflictError) as excinfo:
        apply_config_plan(plan, repo_root=repo, home=home, state_home=home / ".state")
    assert "手动移走" in str(excinfo.value)
    assert "--takeover=backup" not in str(excinfo.value)


def test_invalid_on_conflict_policy_rejected(tmp_path: Path) -> None:
    module, repo, home, state, _edited = _deployed_then_edited(tmp_path)
    with pytest.raises(ConfigDeployError, match="unknown on-conflict policy"):
        compile_config_plan(
            module, repo_root=repo, home=home, state_home=state, on_conflict="yes"  # type: ignore[arg-type]
        )


# ---- glob exclude ----


def test_glob_exclude_skips_nested_compiled_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    source = repo / "config"
    (source / "modules").mkdir(parents=True)
    home.mkdir()
    (source / "aliases.zsh").write_text("alias a=1\n", encoding="utf-8")
    (source / "aliases.zsh.zwc").write_bytes(b"stale bytecode")
    (source / "modules" / "misc.zsh.zwc").write_bytes(b"stale bytecode")
    target = home / ".config" / "fixture"
    module = _module(source, target, exclude=["*.zwc"])

    plan = compile_config_plan(module, repo_root=repo, home=home, state_home=home / ".state")
    writes = {op.relative_path for op in plan.operations if op.operation == "write"}
    assert writes == {"aliases.zsh"}


def test_newly_excluded_owned_file_is_released_without_conflict(tmp_path: Path) -> None:
    """源目录残留的 .zwc 曾被托管、目标又被重新编译：加 exclude 后不再冲突，也不删文件。"""
    repo = tmp_path / "repo"
    home = tmp_path / "home"
    state = home / ".state"
    source = repo / "config"
    source.mkdir(parents=True)
    home.mkdir()
    (source / "aliases.zsh").write_text("alias a=1\n", encoding="utf-8")
    (source / "aliases.zsh.zwc").write_bytes(b"stale bytecode")
    target = home / ".config" / "fixture"
    apply_config_plan(
        compile_config_plan(_module(source, target), repo_root=repo, home=home, state_home=state),
        repo_root=repo,
        home=home,
        state_home=state,
        run_id="first",
    )
    compiled = target / "aliases.zsh.zwc"
    compiled.write_bytes(b"fresh bytecode")

    module = _module(source, target, exclude=["*.zwc"])
    plan = compile_config_plan(module, repo_root=repo, home=home, state_home=state)
    assert not plan.conflicts
    apply_config_plan(plan, repo_root=repo, home=home, state_home=state, run_id="second")
    assert compiled.read_bytes() == b"fresh bytecode"
    manifest = json.loads((state / "dotf" / "config-manifest.json").read_text(encoding="utf-8"))
    assert str(compiled) not in {item["target"] for item in manifest["items"]}


# ---- handler：DOTF_ON_CONFLICT ----


def test_handler_policy_defaults_to_backup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config_handler.ON_CONFLICT_ENV, raising=False)
    assert config_handler._on_conflict_from_env() == "backup"


def test_handler_policy_rejects_unknown_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config_handler.ON_CONFLICT_ENV, "bogus")
    with pytest.raises(ValueError, match="unknown on-conflict policy"):
        config_handler._on_conflict_from_env()


def _registry_zsh_deployed_then_edited(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """取注册表里真实的 zsh 模块部署到临时 HOME，再在本机改它的 aliases.zsh。"""
    repo = Path(__file__).resolve().parent.parent
    home = tmp_path / "home"
    state = home / ".state"
    home.mkdir()
    argv = ["zsh", "--repo-root", str(repo), "--home", str(home), "--state-home", str(state)]
    assert config_handler.main(argv + ["--run-id", "first"]) == 0
    aliases = home / ".config" / "zsh" / "aliases.zsh"
    aliases.write_text(aliases.read_text(encoding="utf-8") + "alias local-only=1\n", encoding="utf-8")
    return repo, home, state, aliases


def test_main_backs_up_owned_drift_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv(config_handler.ON_CONFLICT_ENV, raising=False)
    monkeypatch.delenv(config_handler.ON_TAKEOVER_ENV, raising=False)
    monkeypatch.setattr(config_handler, "_interactive_tty", lambda: None)
    repo, home, state, aliases = _registry_zsh_deployed_then_edited(tmp_path)
    capsys.readouterr()

    argv = ["zsh", "--repo-root", str(repo), "--home", str(home), "--state-home", str(state)]
    assert config_handler.main(argv + ["--run-id", "drift-e2e"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "changed"
    warnings = [line for line in captured.err.splitlines() if line.startswith("warning: ")]
    assert len(warnings) == 1
    assert "~/.config/zsh/aliases.zsh →" in warnings[0]
    source = repo / "config" / "shell" / "zsh" / "aliases.zsh"
    assert aliases.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    backups = list((home / ".local" / "state" / "dotf" / "backups" / "drift-e2e").rglob("aliases.zsh.*"))
    assert len(backups) == 1
    assert "alias local-only=1" in backups[0].read_text(encoding="utf-8")


def test_main_block_policy_keeps_local_edits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv(config_handler.ON_CONFLICT_ENV, raising=False)
    monkeypatch.delenv(config_handler.ON_TAKEOVER_ENV, raising=False)
    monkeypatch.setattr(config_handler, "_interactive_tty", lambda: None)
    repo, home, state, aliases = _registry_zsh_deployed_then_edited(tmp_path)
    edited = aliases.read_text(encoding="utf-8")
    capsys.readouterr()

    monkeypatch.setenv(config_handler.ON_CONFLICT_ENV, "block")
    argv = ["zsh", "--repo-root", str(repo), "--home", str(home), "--state-home", str(state)]
    assert config_handler.main(argv) == 1
    err = capsys.readouterr().err
    assert "受管文件内容已与上次写入不一致" in err
    assert "可选处理：--on-conflict=backup" in err
    assert aliases.read_text(encoding="utf-8") == edited
