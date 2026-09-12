"""公共测试夹具：临时 HOME、状态目录、命令桩；禁止触碰真实 HOME。"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "src"
DOTF = ROOT / "bin" / "dotf"

# 会话开始时锁定真实 HOME，供断言对照
_LAUNCH_HOME = Path(os.environ.get("HOME", str(Path.home()))).resolve()

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "slow: 端到端慢测（pty 交互、临时 git 仓库），与快测分离运行",
    )


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
    monkeypatch.delenv("KIRO_HOME", raising=False)

    assert home.resolve() != launch_home
    return home


def write_skills_catalog(repo: Path, *, default: bool = True) -> None:
    """Write a v3 agenda catalog covering every first-party skill dir in *repo*.

    Test mini-repos only ship first-party skills; this keeps them consistent
    with the unified catalog's coverage invariant.
    """
    skills_root = repo / "agents" / "skills"
    ids = sorted(
        path.name
        for path in skills_root.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    ) if skills_root.is_dir() else []
    lines = ["version: 3", "lock: skills.lock.yaml", "groups:"]
    lines += ["  dotfiles:", "    type: first-party"]
    if ids:
        lines.append("    skills:")
        lines += [f"      - {skill_id}" for skill_id in ids]
    else:
        lines.append("    skills: []")
    (repo / "agents" / "skills.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def isolate_agents_sync_for_test(home: Path) -> None:
    """Disable network-backed third-party defaults and secret-bearing MCP in tests."""
    import yaml

    overlay_dir = home / ".config" / "dotf" / "overlays"
    overlay_dir.mkdir(parents=True)
    catalog = yaml.safe_load((ROOT / "agents" / "skills.yaml").read_text(encoding="utf-8"))
    servers = yaml.safe_load((ROOT / "agents" / "env" / "mcp" / "servers.yaml").read_text(encoding="utf-8"))
    # Only third-party skills are network-backed; first-party skills come from
    # the repo and stay enabled so tests can exercise the sync path.
    catalog_ids = [
        skill_id
        for group in (catalog.get("groups") or {}).values()
        if isinstance(group, dict) and group.get("type") == "third-party"
        for skill_id in (group.get("skills") or [])
    ]
    overlay = {
        "schema_version": 1,
        "kind": "dotf-overlay",
        "agents": {
            "profile": "research",
            "disabled_servers": sorted((servers.get("servers") or {}).keys()),
            "disabled_skills": catalog_ids,
        },
    }
    (overlay_dir / "00-test.yaml").write_text(
        yaml.safe_dump(overlay, sort_keys=False), encoding="utf-8"
    )


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
