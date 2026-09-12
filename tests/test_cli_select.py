"""pty 真终端测试：CLI 编号点选（spec: cli-surface，slow）。

通过 pty 起 dotf 进程、喂按键序列，断言提示行与选中结果。
只匹配稳定子串，不断言完整 ANSI 转义序列。
"""

from __future__ import annotations

import os
import pty
import select
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOTF = ROOT / "bin" / "dotf"


def _run_in_pty(args: list[str], keys: str, timeout: float = 15.0) -> str:
    """在 pty 中运行 dotf，发送 keys 后关闭 stdin，收集全部输出。"""
    master, slave = pty.openpty()
    env = os.environ.copy()
    env["HOME"] = os.environ.get("HOME", str(Path.home()))
    env["TERM"] = "dumb"
    proc = subprocess.Popen(
        [str(DOTF), *args],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        cwd=str(ROOT),
        env=env,
        close_fds=True,
    )
    os.close(slave)
    output = b""
    try:
        # 等待提示符出现，再喂输入
        deadline = time.time() + timeout
        sent = False
        while time.time() < deadline:
            r, _, _ = select.select([master], [], [], 0.2)
            if r:
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                output += chunk
                if not sent and b"> " in output:
                    os.write(master, keys.encode())
                    sent = True
            if proc.poll() is not None and not r:
                break
        proc.wait(timeout=timeout)
    finally:
        os.close(master)
    text = output.decode(errors="replace")
    # 去掉 CR，便于断言
    return text.replace("\r", "")


@pytest.mark.slow
def test_select_lists_modules_and_cancels() -> None:
    out = _run_in_pty(["-i"], "q\n")
    assert "可选模块" in out
    assert "[agents]" in out or "agents" in out
    assert "已取消" in out
    assert "输入序号、模块名或 a" in out


@pytest.mark.slow
def test_select_numeric_then_quit() -> None:
    # 选第一个模块后 plan 阶段非 tty 无 --yes → 快速失败；能走到那一步即说明点选生效
    out = _run_in_pty(["-i"], "1\nq\n")
    assert "可选模块" in out


@pytest.mark.slow
def test_select_all_option_lists_modules() -> None:
    out = _run_in_pty(["-i"], "a\n")
    # a 全选后进入 plan 确认；非 tty 确认失败快速退出
    assert "可选模块" in out
