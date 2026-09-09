"""确保 PyYAML 可 import；缺失时用 pip 自动安装（跨平台，不依赖发行版包名）。"""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
from types import ModuleType


def _try_import() -> ModuleType | None:
    try:
        return importlib.import_module("yaml")
    except ImportError:
        return None


def _install_commands() -> list[list[str]]:
    """按通用性优先：pip --user → break-system-packages → uv。"""
    py = sys.executable
    cmds: list[list[str]] = [
        [py, "-m", "pip", "install", "--user", "PyYAML"],
        [py, "-m", "pip", "install", "--user", "--break-system-packages", "PyYAML"],
        [py, "-m", "pip", "install", "--break-system-packages", "PyYAML"],
    ]
    uv = shutil.which("uv")
    if uv:
        cmds.append([uv, "pip", "install", "--python", py, "PyYAML"])
        cmds.append([uv, "pip", "install", "--system", "PyYAML"])
    return cmds


def ensure_yaml(*, quiet: bool = True) -> ModuleType:
    """返回 yaml 模块；若缺失则尝试自动安装后再 import。"""
    mod = _try_import()
    if mod is not None:
        return mod

    if not quiet:
        print("正在安装 PyYAML …", file=sys.stderr)

    for cmd in _install_commands():
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError):
            continue
        importlib.invalidate_caches()
        mod = _try_import()
        if mod is not None:
            return mod

    print(
        "错误: 需要 PyYAML，自动安装失败。"
        "请手动执行: python3 -m pip install --user PyYAML",
        file=sys.stderr,
    )
    sys.exit(1)
