"""临时 git 仓库测试：pull / init（spec: cli-surface，slow）。

建 local bare remote + clone 真跑 git 操作；通过 DOTF_REPO_ROOT 把
dotf_cli 指向临时仓库，避免触碰开发仓库本身。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )


def _make_remote_repo(tmp_path: Path) -> tuple[Path, Path]:
    """bare remote + 一份已配置 user 的 clone。"""
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", str(remote))
    seed = tmp_path / "seed"
    seed.mkdir()
    _git(seed, "init", "-q")
    _git(seed, "config", "user.email", "dotf@test")
    _git(seed, "config", "user.name", "dotf")
    (seed / "README.md").write_text("v1\n", encoding="utf-8")
    _git(seed, "add", ".")
    _git(seed, "commit", "-qm", "init")
    _git(seed, "branch", "-M", "main")
    _git(seed, "remote", "add", "origin", str(remote))
    _git(seed, "push", "-q", "origin", "main")

    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", str(remote), str(clone))
    _git(clone, "config", "user.email", "dotf@test")
    _git(clone, "config", "user.name", "dotf")
    return remote, clone


def _run_cli(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    env["DOTF_REPO_ROOT"] = str(repo)
    return subprocess.run(
        [sys.executable, "-m", "dotf_cli", *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.slow
def test_pull_fast_forward(tmp_path: Path) -> None:
    remote, clone = _make_remote_repo(tmp_path)
    # remote 再推进一个提交
    other = tmp_path / "other"
    _git(tmp_path, "clone", "-q", str(remote), str(other))
    (other / "new.txt").write_text("new\n", encoding="utf-8")
    _git(other, "add", ".")
    _git(other, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "add")
    _git(other, "push", "-q", "origin", "HEAD:main")

    result = _run_cli(clone, "pull")
    assert result.returncode == 0, result.stderr
    assert "拉取最新代码" in result.stdout
    assert "✓ dotfiles 已更新" in result.stdout
    assert (clone / "new.txt").read_text(encoding="utf-8") == "new\n"


@pytest.mark.slow
def test_pull_stashes_dirty_tree(tmp_path: Path) -> None:
    remote, clone = _make_remote_repo(tmp_path)
    other = tmp_path / "other"
    _git(tmp_path, "clone", "-q", str(remote), str(other))
    (other / "new.txt").write_text("new\n", encoding="utf-8")
    _git(other, "add", ".")
    _git(other, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "add")
    _git(other, "push", "-q", "origin", "HEAD:main")

    # 本地未提交改动 → 触发 stash → pull → pop 恢复
    readme = clone / "README.md"
    readme.write_text("local edit\n", encoding="utf-8")

    result = _run_cli(clone, "pull")
    assert result.returncode == 0, result.stderr
    assert "检测到未提交的改动，执行 stash" in result.stdout
    assert "恢复暂存的改动" in result.stdout
    assert "✓ dotfiles 已更新" in result.stdout
    assert readme.read_text(encoding="utf-8") == "local edit\n"
    assert (clone / "new.txt").exists()


@pytest.mark.slow
def test_pull_conflict_reports_conflict_code(tmp_path: Path) -> None:
    remote, clone = _make_remote_repo(tmp_path)
    other = tmp_path / "other"
    _git(tmp_path, "clone", "-q", str(remote), str(other))
    (other / "README.md").write_text("remote v2\n", encoding="utf-8")
    _git(other, "add", ".")
    _git(other, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "update")
    _git(other, "push", "-q", "origin", "HEAD:main")

    (clone / "README.md").write_text("local conflicting edit\n", encoding="utf-8")

    result = _run_cli(clone, "pull")
    assert result.returncode == 5  # conflict
    assert "stash pop 发生冲突" in result.stdout
    # 冲突状态保留给人工解决
    assert _git(clone, "stash", "list").stdout.strip() != ""


@pytest.mark.slow
def test_init_list_profiles(tmp_path: Path) -> None:
    _, clone = _make_remote_repo(tmp_path)
    result = _run_cli(clone, "init", "--list")
    assert result.returncode == 0, result.stderr
    assert "darwin" in result.stdout
    assert "ubuntu" in result.stdout


@pytest.mark.slow
def test_init_dry_run_plan(tmp_path: Path) -> None:
    _, clone = _make_remote_repo(tmp_path)
    result = _run_cli(clone, "init", "--os", "arch", "--profile", "minimal", "--dry-run")
    assert result.returncode == 0, result.stderr + result.stdout
    assert "使用强制 OS: arch" in result.stdout
    assert "Dotfiles 初始化 (os=arch profile=minimal)" in result.stdout
