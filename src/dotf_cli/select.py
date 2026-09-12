"""编号点选（interactive_select 的 Python 平移）。

行为对齐旧 bash 版：分组列表、数字/名字 token 选择、a 全选、q 取消、
空输入重刷、保序去重。新增：非 tty 直接以 env 错误码拒绝（不挂起）。
"""

from __future__ import annotations

import subprocess
import sys

from .errors import DotfError
from .runner import REPO_ROOT, SRC_DIR, modules_py

_CAPABILITIES = ("install", "config", "doctor", "both")


def _modules_for_capability(capability: str) -> list[str]:
    args = ["list"]
    if capability in _CAPABILITIES:
        args += ["--capability", capability]
    args += ["--filter-os", "--registry-order"]
    proc = modules_py(*args, capture=True)
    if proc.returncode != 0:
        raise DotfError("env", "无法读取模块列表", chain=["modules.py " + " ".join(args)])
    return [line for line in proc.stdout.splitlines() if line.strip()]


def _field(name: str, key: str) -> str:
    proc = modules_py("field", name, key, capture=True)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def interactive_select(capability: str) -> list[str]:
    """返回选中的模块名；取消/无可用模块抛 DotfError。"""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise DotfError(
            "env", "需要 TTY 交互；请直接指定模块名，或用 --yes / --dry-run"
        )

    modules = _modules_for_capability(capability)
    if not modules:
        raise DotfError("env", "当前 OS 下无可用模块")

    while True:
        print()
        print("可选模块（按 group 展示；序号为选择用，执行顺序仍由 planner 决定）:")
        cur_group = ""
        for i, name in enumerate(modules):
            group = _field(name, "group") or "other"
            if group != cur_group:
                cur_group = group
                print()
                print(f"  [{cur_group}]")
            print(f"  {i + 1:2d}) {name:<14} {_field(name, 'desc')}")
        print()
        print("输入序号、模块名或 a（全部），空格分隔；q 取消")

        try:
            raw = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            print("已取消")
            raise DotfError("usage", "已取消")

        if raw in ("q", "Q"):
            print("已取消")
            raise DotfError("usage", "已取消")
        if raw in ("a", "A"):
            return list(modules)

        picked: list[str] = []
        valid = True
        for token in raw.split():
            if token.isdigit():
                idx = int(token) - 1
                if idx < 0 or idx >= len(modules):
                    print(f"无效序号: {token}")
                    valid = False
                    break
                picked.append(modules[idx])
            elif token in modules:
                picked.append(token)
            else:
                print(f"无效输入: {token}")
                valid = False
                break

        if not valid:
            continue
        if not picked:
            print("未选择任何模块")
            continue

        selected: list[str] = []
        for name in picked:
            if name not in selected:
                selected.append(name)
        return selected
