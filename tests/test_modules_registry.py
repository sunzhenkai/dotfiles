"""注册表：能力查询、OS 过滤、校验 — 不修改真实 HOME。"""

from __future__ import annotations

import subprocess
from pathlib import Path

import modules
import pytest


def test_validate_registry_passes(repo_root: Path) -> None:
    result = subprocess.run(
        ["python3", str(repo_root / "scripts" / "modules.py"), "validate"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "校验通过" in result.stdout


def test_tool_modules_declare_doctor() -> None:
    for mod in modules.load_registry():
        if modules.is_tool_module(mod):
            assert modules.has_doctor(mod), f"{mod.get('name')} 缺少 doctor"


def test_non_tool_modules_may_omit_doctor() -> None:
    for name in modules.NON_TOOL_MODULES:
        mod = modules.find_module(modules.load_registry(), name)
        assert mod is not None, name
        # 允许省略；若声明则也不强制失败
        assert not modules.is_tool_module(mod)


def test_capability_queries() -> None:
    mods = modules.load_registry()
    nvim = modules.find_module(mods, "nvim")
    sdk = modules.find_module(mods, "sdk")
    agents = modules.find_module(mods, "agents")
    system = modules.find_module(mods, "system")

    assert nvim and modules.has_config(nvim) and not modules.has_install(nvim)
    assert sdk and modules.has_install(sdk) and not modules.has_config(sdk)
    assert agents and modules.has_install(agents) and modules.has_config(agents)
    assert agents and modules.has_doctor(agents)
    assert system and modules.has_install(system) and not modules.has_doctor(system)


def test_os_filter_config_modules() -> None:
    mods = modules.load_registry()
    linux_cfg = {m["name"] for m in modules.filter_modules(mods, capability="config", os_id="linux")}
    darwin_cfg = {
        m["name"] for m in modules.filter_modules(mods, capability="config", os_id="darwin")
    }

    assert "hypr" in linux_cfg
    assert "fcitx5" in linux_cfg
    assert "iterm2" not in linux_cfg

    assert "iterm2" in darwin_cfg
    assert "hypr" not in darwin_cfg
    assert "fcitx5" not in darwin_cfg

    # 全平台模块两侧都应存在
    assert "nvim" in linux_cfg and "nvim" in darwin_cfg


def test_matches_os_family() -> None:
    assert modules.matches_os(["linux"], "ubuntu")
    assert modules.matches_os(["linux"], "arch")
    assert not modules.matches_os(["linux"], "darwin")
    assert modules.matches_os(["darwin"], "darwin")
    assert modules.matches_os(None, "anything")
    assert modules.matches_os([], "anything")


def test_cli_has_and_exists(repo_root: Path) -> None:
    py = repo_root / "scripts" / "modules.py"

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(py), *args],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )

    assert run("exists", "nvim").returncode == 0
    assert run("exists", "no-such-module").returncode == 1
    assert run("has", "nvim", "config").returncode == 0
    assert run("has", "nvim", "install").returncode == 1
    assert run("has", "sdk", "doctor").returncode == 0
    assert run("has", "system", "doctor").returncode == 1


def test_doctor_capability_list_excludes_system(repo_root: Path) -> None:
    result = subprocess.run(
        ["python3", str(repo_root / "scripts" / "modules.py"), "list", "--capability", "doctor"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    names = set(result.stdout.split())
    assert "nvim" in names
    assert "agents" in names
    assert "system" not in names
    assert "homebrew" not in names
