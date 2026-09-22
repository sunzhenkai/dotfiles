"""Config Takeover: backup 接管无主目标，/dev/tty 汇总确认，其余冲突保持 fail closed。

见 docs/adr/0024-config-unowned-takeover.md。
"""

from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

from dotf_core import config_handler
from dotf_core.config_deploy import (
    ConfigConflictError,
    ConfigDeployError,
    apply_config_plan,
    compile_config_plan,
    deploy_config,
    takeover_targets,
)


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


def _divergent_copy_module(tmp_path: Path) -> tuple[dict[str, Any], Path, Path, Path]:
    """copy 模块 + 目标处已存在内容不等价的无主文件（pi settings.json 的最小复现）。"""
    repo, home, state = _roots(tmp_path)
    source = repo / "config"
    source.mkdir()
    (source / "one.toml").write_text("value = 1\n", encoding="utf-8")
    target = home / ".config" / "fixture"
    target.mkdir(parents=True)
    (target / "one.toml").write_text("value = 999\n", encoding="utf-8")
    return _module(source, target), home, state, target


def test_default_still_fail_closed_for_divergent_unowned(tmp_path: Path) -> None:
    module, home, state, target = _divergent_copy_module(tmp_path)
    repo = Path(module["config"]["source"]).parent

    plan = compile_config_plan(module, repo_root=repo, home=home, state_home=state)
    assert plan.conflicts
    assert plan.conflicts[0].conflict_reason == "unowned-real-target"
    with pytest.raises(ConfigConflictError, match="不受本模块管理"):
        apply_config_plan(plan, repo_root=repo, home=home, state_home=state)
    assert (target / "one.toml").read_text(encoding="utf-8") == "value = 999\n"
    assert not (state / "dotf" / "config-manifest.json").exists()


def test_takeover_backup_writes_and_registers_ownership(tmp_path: Path) -> None:
    module, home, state, target = _divergent_copy_module(tmp_path)
    repo = Path(module["config"]["source"]).parent

    plan = compile_config_plan(
        module, repo_root=repo, home=home, state_home=state, on_takeover="backup"
    )
    assert not plan.conflicts
    assert takeover_targets(plan) == (str(target / "one.toml"),)

    result = apply_config_plan(
        plan, repo_root=repo, home=home, state_home=state, run_id="tk-1"
    )
    assert result.status == "changed"
    # 原文件被备份
    assert len(result.backups) == 1
    assert result.backups[0].read_text(encoding="utf-8") == "value = 999\n"
    assert "tk-1" in str(result.backups[0])
    # 目标写入受管内容
    assert (target / "one.toml").read_text(encoding="utf-8") == "value = 1\n"
    # 首次登记 ownership
    manifest = json.loads((state / "dotf" / "config-manifest.json").read_text(encoding="utf-8"))
    owners = {item["owner"] for item in manifest["items"]}
    assert owners == {"config:fixture"}

    # 接管后默认策略（skip）幂等通过
    second = compile_config_plan(module, repo_root=repo, home=home, state_home=state)
    assert not second.conflicts
    assert second.status == "unchanged"


def test_takeover_only_after_confirmation_change_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """规划后、应用前文件再被改 → takeover 也要拒绝（pin 住规划时字节）。"""
    module, home, state, target = _divergent_copy_module(tmp_path)
    repo = Path(module["config"]["source"]).parent
    plan = compile_config_plan(
        module, repo_root=repo, home=home, state_home=state, on_takeover="backup"
    )
    (target / "one.toml").write_text("changed again\n", encoding="utf-8")
    with pytest.raises(ConfigConflictError, match="changed after planning"):
        apply_config_plan(plan, repo_root=repo, home=home, state_home=state)


def test_symlink_conflict_is_never_takeable(tmp_path: Path) -> None:
    repo, home, state = _roots(tmp_path)
    source = repo / "config"
    source.mkdir()
    (source / "one.toml").write_text("value = 1\n", encoding="utf-8")
    target = home / ".config" / "fixture"
    target.mkdir(parents=True)
    victim = tmp_path / "foreign"
    victim.mkdir()
    (victim / "keep.txt").write_text("keep", encoding="utf-8")
    (target / "one.toml").symlink_to(victim / "keep.txt")
    module = _module(source, target)

    plan = compile_config_plan(
        module, repo_root=repo, home=home, state_home=state, on_takeover="backup"
    )
    assert plan.conflicts
    assert not takeover_targets(plan)
    with pytest.raises(ConfigConflictError):
        apply_config_plan(plan, repo_root=repo, home=home, state_home=state)
    assert (target / "one.toml").is_symlink()


def test_directory_where_file_expected_is_never_takeable(tmp_path: Path) -> None:
    repo, home, state = _roots(tmp_path)
    source = repo / "config"
    source.mkdir()
    (source / "one.toml").write_text("value = 1\n", encoding="utf-8")
    target = home / ".config" / "fixture"
    (target / "one.toml").mkdir(parents=True)  # 该是文件的位置放了个目录
    module = _module(source, target)

    plan = compile_config_plan(
        module, repo_root=repo, home=home, state_home=state, on_takeover="backup"
    )
    assert plan.conflicts
    assert not takeover_targets(plan)


def test_invalid_takeover_policy_rejected(tmp_path: Path) -> None:
    module, home, state, _target = _divergent_copy_module(tmp_path)
    repo = Path(module["config"]["source"]).parent
    with pytest.raises(ConfigDeployError, match="unknown on-takeover policy"):
        compile_config_plan(
            module, repo_root=repo, home=home, state_home=state, on_takeover="yes"  # type: ignore[arg-type]
        )


def test_deploy_config_passes_takeover_through(tmp_path: Path) -> None:
    module, home, state, target = _divergent_copy_module(tmp_path)
    repo = Path(module["config"]["source"]).parent
    result = deploy_config(
        module,
        repo_root=repo,
        home=home,
        state_home=state,
        run_id="tk-deploy",
        on_takeover="backup",
    )
    assert result.status == "changed"
    assert (target / "one.toml").read_text(encoding="utf-8") == "value = 1\n"


# ---- handler：env flag / /dev/tty 确认 ----


class _TtyOut(io.StringIO):
    frozen = ""

    def close(self) -> None:
        type(self).frozen = self.getvalue()
        super().close()


def _conflict_plan() -> Any:
    return type("P", (), {"conflicts": [("x",)]})()


def _clean_plan() -> Any:
    return type("P", (), {"conflicts": []})()


def _backup_probe(targets: list[str]) -> Any:
    ops = [
        type(
            "O",
            (),
            {"takeover": True, "item": type("I", (), {"target": target})()},
        )()
        for target in targets
    ]
    return type("P", (), {"operations": ops})()


def test_decide_non_tty_is_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config_handler.ON_TAKEOVER_ENV, raising=False)
    monkeypatch.setattr(config_handler, "_interactive_tty", lambda: None)
    assert config_handler.decide_takeover(
        _conflict_plan(), compile_backup=lambda: (_ for _ in ()).throw(AssertionError())
    ) == "skip"


def test_decide_env_backup_never_prompts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config_handler.ON_TAKEOVER_ENV, "backup")
    monkeypatch.setattr(
        config_handler,
        "_interactive_tty",
        lambda: (_ for _ in ()).throw(AssertionError("explicit flag must not prompt")),
    )
    assert config_handler.decide_takeover(
        _conflict_plan(), compile_backup=lambda: (_ for _ in ()).throw(AssertionError())
    ) == "backup"


def test_decide_env_skip_never_prompts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config_handler.ON_TAKEOVER_ENV, "skip")
    monkeypatch.setattr(
        config_handler,
        "_interactive_tty",
        lambda: (_ for _ in ()).throw(AssertionError("explicit flag must not prompt")),
    )
    assert (
        config_handler.decide_takeover(
            _conflict_plan(), compile_backup=lambda: (_ for _ in ()).throw(AssertionError())
        )
        == "skip"
    )


def test_decide_clean_plan_does_not_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config_handler.ON_TAKEOVER_ENV, raising=False)
    monkeypatch.setattr(
        config_handler,
        "_interactive_tty",
        lambda: (_ for _ in ()).throw(AssertionError("clean plan must not prompt")),
    )
    assert (
        config_handler.decide_takeover(
            _clean_plan(), compile_backup=lambda: (_ for _ in ()).throw(AssertionError())
        )
        == "skip"
    )


def test_decide_tty_yes_returns_backup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config_handler.ON_TAKEOVER_ENV, raising=False)
    monkeypatch.setattr(
        config_handler, "_interactive_tty", lambda: (io.StringIO("y\n"), _TtyOut())
    )
    assert (
        config_handler.decide_takeover(
            _conflict_plan(),
            compile_backup=lambda: _backup_probe(["/home/x/.pi/agent/settings.json"]),
        )
        == "backup"
    )
    assert "/home/x/.pi/agent/settings.json" in _TtyOut.frozen
    assert "Takeover with backup?" in _TtyOut.frozen
    assert "backups/" in _TtyOut.frozen


def test_decide_tty_default_is_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config_handler.ON_TAKEOVER_ENV, raising=False)
    monkeypatch.setattr(
        config_handler, "_interactive_tty", lambda: (io.StringIO("\n"), _TtyOut())
    )
    assert (
        config_handler.decide_takeover(
            _conflict_plan(), compile_backup=lambda: _backup_probe(["/x/y"])
        )
        == "skip"
    )


def test_decide_tty_without_candidates_stays_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    """冲突全是 symlink 等不可接管项时，不问直接失败。"""
    monkeypatch.delenv(config_handler.ON_TAKEOVER_ENV, raising=False)
    out = _TtyOut()
    monkeypatch.setattr(
        config_handler, "_interactive_tty", lambda: (io.StringIO("y\n"), out)
    )
    assert (
        config_handler.decide_takeover(
            _conflict_plan(), compile_backup=lambda: _backup_probe([])
        )
        == "skip"
    )
    assert out.frozen == ""


def test_decide_tty_eof_is_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config_handler.ON_TAKEOVER_ENV, raising=False)
    monkeypatch.setattr(
        config_handler, "_interactive_tty", lambda: (io.StringIO(""), _TtyOut())
    )
    assert (
        config_handler.decide_takeover(
            _conflict_plan(), compile_backup=lambda: _backup_probe(["/x/y"])
        )
        == "skip"
    )


def test_invalid_env_policy_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config_handler.ON_TAKEOVER_ENV, "bogus")
    with pytest.raises(ValueError, match="unknown on-takeover policy"):
        config_handler._on_takeover_from_env()


def _registry_copy_module_with_divergent_target(
    tmp_path: Path,
) -> tuple[dict[str, Any], Path, Path, Path, Path]:
    """取注册表里真实的 copy 模块（tmux），在目标处放一个内容不等价的同名文件。"""
    from dotf_core import registry as modules

    repo = Path(__file__).resolve().parent.parent
    module = next(
        m for m in modules.load_registry()
        if m["name"] == "tmux" and modules.has_config(m)
    )
    home = tmp_path / "home"
    state = home / ".state"
    home.mkdir()
    source = repo / module["config"]["source"]
    rel = sorted(p for p in source.rglob("*") if p.is_file())[0]
    target_file = home / module["config"]["target"][2:] / rel.relative_to(source)
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("# foreign local file\n", encoding="utf-8")
    return module, repo, home, state, target_file


def test_main_fail_closed_without_tty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """端到端：无 TTY、无 flag → 维持原失败（不受本模块管理），不写不备份。"""
    module, repo, home, state, target_file = _registry_copy_module_with_divergent_target(
        tmp_path
    )
    monkeypatch.delenv(config_handler.ON_TAKEOVER_ENV, raising=False)
    monkeypatch.setattr(config_handler, "_interactive_tty", lambda: None)

    rc = config_handler.main(
        [
            module["name"],
            "--repo-root",
            str(repo),
            "--home",
            str(home),
            "--state-home",
            str(state),
        ]
    )
    assert rc == 1
    captured = capsys.readouterr()
    assert "不受本模块管理" in captured.err
    assert target_file.read_text(encoding="utf-8") == "# foreign local file\n"
    assert not (state / "dotf" / "config-manifest.json").exists()


def test_main_env_takeover_backup_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """端到端：DOTF_TAKEOVER=backup 不询问，直接备份+接管+登记 ownership。"""
    module, repo, home, state, target_file = _registry_copy_module_with_divergent_target(
        tmp_path
    )
    source_file = (
        repo / module["config"]["source"]
    ) / target_file.relative_to(
        home / module["config"]["target"][2:]
    )
    monkeypatch.setenv(config_handler.ON_TAKEOVER_ENV, "backup")
    monkeypatch.setattr(
        config_handler,
        "_interactive_tty",
        lambda: (_ for _ in ()).throw(AssertionError("explicit flag must not prompt")),
    )

    rc = config_handler.main(
        [
            module["name"],
            "--repo-root",
            str(repo),
            "--home",
            str(home),
            "--state-home",
            str(state),
            "--run-id", "e2e-1",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "changed"
    assert target_file.read_text(encoding="utf-8") == source_file.read_text(encoding="utf-8")
    backups = list((home / ".local" / "state" / "dotf" / "backups" / "e2e-1").rglob("*"))
    assert any(b.is_file() and "foreign local file" in b.read_text(encoding="utf-8") for b in backups)
    manifest = json.loads((state / "dotf" / "config-manifest.json").read_text(encoding="utf-8"))
    assert {i["owner"] for i in manifest["items"]} == {f"config:{module['name']}"}
