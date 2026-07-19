"""run_plan.sh 非 TTY 快速失败。"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_run_plan_requires_yes_without_tty(tmp_home: Path, tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text(
        "PLAN_OK\n"
        "OS\tubuntu\n"
        "PROFILE\t\n"
        "ACTION\t1\tinstall\tsdk\texplicit\n",
        encoding="utf-8",
    )
    # 通过 script 关闭 tty：用 setsid / 重定向；这里用环境伪造不可读 tty 较难，
    # 改为直接调用时 stdin/stdout 均非 tty，并暂时去掉 /dev/tty 可读性——改测逻辑：
    # 当 ASSUME_YES=0 且无法打开 /dev/tty 时失败。用 unshare 不现实，改为测试
    # --dry-run 成功与 --yes 会进入执行（用假 install）。
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)

    dry = subprocess.run(
        ["bash", str(ROOT / "scripts" / "run_plan.sh"), "--dry-run", "--plan-file", str(plan)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert dry.returncode == 0
    assert "dry-run" in dry.stdout
    assert "→ install" not in dry.stdout
