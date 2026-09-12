"""子进程委托：planner / run_plan / modules 查询 / skills_map。

与旧 bash 版逐一对应：同一批解释器与脚本、同样的参数顺序，
保证行为契约不因调用方换语言而改变。
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .errors import DotfError

SRC_DIR = Path(__file__).resolve().parent.parent  # 代码位置，不随 DOTF_REPO_ROOT 变
SCRIPTS_DIR = SRC_DIR.parent / "scripts"
REPO_ROOT = Path(os.environ.get("DOTF_REPO_ROOT", str(SRC_DIR.parent)))


class Ctx:
    """命令级全局开关（对应旧 bash 的 DOTF_* 变量）。"""

    def __init__(self) -> None:
        self.yes = False
        self.dry_run = False
        self.json = False
        self.deep = False
        self.continue_on_error = False
        self.usage_profile = ""
        self.verbose = os.environ.get("DOTF_VERBOSE", "") == "1"

    def export(self) -> None:
        """把开关写入环境，供 run_plan.sh 与 handler 子进程读取。"""
        if self.deep:
            os.environ["DOTF_DEEP"] = "1"


def _python(*args: str, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(["python3", *map(str, args)], **kwargs)


def modules_py(*args: str, capture: bool = False) -> subprocess.CompletedProcess:
    return _python(SRC_DIR / "modules.py", *args, capture_output=capture, text=True)


def skills_map_py(*args: str, capture: bool = False) -> subprocess.CompletedProcess:
    return _python(
        SRC_DIR / "agents" / "skills_map.py", *args, capture_output=capture, text=True
    )


def detect_os() -> str:
    return modules_py("detect-os", capture=True).stdout.strip()


def default_usage_profile() -> str:
    proc = modules_py("profiles", "default", capture=True)
    out = proc.stdout.strip() if proc.returncode == 0 else ""
    return out or "full"


def plan_and_run(
    ctx: Ctx,
    actions_csv: str,
    *,
    select_all: bool = False,
    modules_csv: str = "",
    os_id: str = "",
    profile: str = "",
    config_extra: tuple[str, ...] = (),
    doctor_extra: tuple[str, ...] = (),
) -> None:
    """生成计划并交给 run_plan.sh 执行（唯一编排入口）。

    成功返回；失败抛 DotfError（planner → plan，执行 → handler）。
    """
    ctx.export()
    sys.stdout.flush()  # 子进程直写 fd，先冲刷 Python 缓冲保证输出顺序
    plan_args = [
        "python3",
        str(SRC_DIR / "planner.py"),
        "plan",
        "--actions",
        actions_csv,
        "--format",
        "machine",
    ]
    if os_id:
        plan_args += ["--os", os_id]
    if profile:
        plan_args += ["--profile", profile]
    if select_all:
        plan_args.append("--all")
    if modules_csv:
        plan_args += ["--modules", modules_csv]

    plan_file = tempfile.NamedTemporaryFile(mode="w", suffix=".plan", delete=False)
    try:
        with plan_file:
            proc = subprocess.run(plan_args, stdout=plan_file)
        if proc.returncode != 0:
            # 契约：planner 失败退出码逐字透传（见其测试），不归类为 3。
            raise DotfError(
                "plan",
                "计划生成失败（详见上方 planner 输出）",
                chain=["planner.py plan " + " ".join(plan_args[2:])],
                rc=proc.returncode,
            )

        run_args = ["bash", str(SCRIPTS_DIR / "run_plan.sh"), "--plan-file", plan_file.name]
        if ctx.yes:
            run_args.append("--yes")
        if ctx.dry_run:
            run_args.append("--dry-run")
        if ctx.continue_on_error:
            run_args.append("--continue-on-error")
        if ctx.json:
            run_args.append("--json")
        for x in config_extra:
            run_args += ["--config-extra", x]
        for x in doctor_extra:
            run_args += ["--doctor-extra", x]

        rc = subprocess.run(run_args).returncode
        if rc != 0:
            raise DotfError(
                "handler",
                f"执行失败（退出码 {rc}）",
                chain=["run_plan.sh --plan-file <plan>"],
            )
    finally:
        os.unlink(plan_file.name)
