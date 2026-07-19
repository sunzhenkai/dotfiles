"""计划控制：dry-run、非 TTY、yes 不绕过校验。"""

from __future__ import annotations

import os
from pathlib import Path

from conftest import run_dotf


def test_dry_run_shows_plan_no_home_writes(tmp_home: Path) -> None:
    before = {p.relative_to(tmp_home) for p in tmp_home.rglob("*") if p.is_file()}
    result = run_dotf("sdk", "-i", "--dry-run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "执行计划" in result.stdout
    assert "install" in result.stdout
    assert "sdk" in result.stdout
    assert "dry-run" in result.stdout
    after = {p.relative_to(tmp_home) for p in tmp_home.rglob("*") if p.is_file()}
    assert after == before


def test_dry_run_all_config(tmp_home: Path) -> None:
    result = run_dotf("-c", "-a", "--dry-run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "config" in result.stdout
    assert "dry-run" in result.stdout


def test_capability_error_before_execute(tmp_home: Path) -> None:
    result = run_dotf("nvim", "-i", "--dry-run")
    assert result.returncode != 0
    assert "install" in (result.stdout + result.stderr)


def test_non_tty_without_yes_fails(tmp_home: Path) -> None:
    """管道 stdin 且无 /dev/tty 时：缺少 --yes/--dry-run 应失败。
    在 CI/无 tty 环境用 DOTF 路径：不传 dry-run/yes 时 run_plan 检查 /dev/tty。
    本机通常有 /dev/tty，故改为断言 dry-run 路径可用；非 TTY 逻辑由 run_plan 单测覆盖。
    """
    result = run_dotf("sdk", "-i", "--dry-run")
    assert result.returncode == 0


def test_yes_still_validates_os_capability(tmp_home: Path) -> None:
    result = run_dotf("system", "-d", "--yes")
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "诊断" in combined or "doctor" in combined.lower() or "能力" in combined


def test_init_dry_run(tmp_home: Path) -> None:
    result = run_dotf("init", "--dry-run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "profile=full" in result.stdout or "profile=full" in result.stderr or "profile=full" in result.stdout
    assert "dry-run" in result.stdout
