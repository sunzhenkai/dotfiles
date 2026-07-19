"""公共测试夹具：临时 HOME、状态目录、命令桩；禁止触碰真实 HOME。"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
DOTF = ROOT / "bin" / "dotf"

# 会话开始时锁定真实 HOME，供断言对照
_LAUNCH_HOME = Path(os.environ.get("HOME", str(Path.home()))).resolve()

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def dotf_bin() -> Path:
    return DOTF


@pytest.fixture(scope="session")
def launch_home() -> Path:
    return _LAUNCH_HOME


@pytest.fixture
def tmp_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, launch_home: Path) -> Path:
    """隔离的临时 HOME，并重定向常见 XDG 路径。"""
    home = tmp_path / "home"
    home.mkdir()
    state = home / ".local" / "state"
    config = home / ".config"
    cache = home / ".cache"
    for d in (state, config, cache):
        d.mkdir(parents=True)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config))
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    monkeypatch.delenv("DOTFILES_HOME", raising=False)

    assert home.resolve() != launch_home
    return home


@pytest.fixture
def tmp_state_dir(tmp_home: Path) -> Path:
    """dotf 执行报告等状态目录（XDG state）。"""
    state = Path(os.environ["XDG_STATE_HOME"]) / "dotf"
    state.mkdir(parents=True, exist_ok=True)
    return state


@pytest.fixture
def stub_bin_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """临时 PATH 前缀，用于放置命令桩。"""
    bindir = tmp_path / "stub-bin"
    bindir.mkdir()
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}")
    return bindir


def make_stub(
    bindir: Path,
    name: str,
    *,
    exit_code: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> Path:
    """在 bindir 创建可执行命令桩。"""
    path = bindir / name
    # 用 printf 避免复杂转义；stdout/stderr 仅用于简单桩
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"cat <<'STDOUT_EOF'\n{stdout}\nSTDOUT_EOF\n"
        f"cat <<'STDERR_EOF' >&2\n{stderr}\nSTDERR_EOF\n"
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


@pytest.fixture
def make_command_stub(stub_bin_dir: Path):
    def _factory(
        name: str,
        *,
        exit_code: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> Path:
        return make_stub(
            stub_bin_dir,
            name,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
        )

    return _factory


def run_dotf(
    *args: str,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    """在当前进程环境中运行 bin/dotf（调用方应已设置临时 HOME）。"""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        [str(DOTF), *args],
        cwd=str(ROOT),
        env=full_env,
        input=input_text,
        text=True,
        capture_output=True,
        check=check,
    )
