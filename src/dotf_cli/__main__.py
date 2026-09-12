"""dotf 入口：主体优先语法分发（旧 bin/dotf main() 的 Python 平移）。

语法：dotf <module...> -i|-c|-d|-ic|-id|-cd|-icd [--uninstall|--deconfig]
      dotf <独立命令> [参数...]   # pull/init/path/status/tui/agents/skills/retry
"""

from __future__ import annotations

import sys

from .commands import (
    cmd_agents_artifact,
    cmd_init,
    cmd_path,
    cmd_pull,
    cmd_retry,
    cmd_skills,
    cmd_status,
    cmd_tui,
)
from .errors import DotfError, exit_code, render
from .help_text import HELP_TEXT
from .output import emit_error
from .runner import Ctx, plan_and_run
from .select import interactive_select

_LEGACY_SYNTAX_MSG = """错误: 旧语法已移除（动作优先不再支持）

新用法（主体优先）:
  dotf <module...> -i|-c|-d|-ic|-id|-cd|-icd
  dotf -i|-c|-d|...           # 交互选择
  dotf -i -a | -c -a | -d -a | -a

示例:
  dotf sdk -i
  dotf nvim -c
  dotf nvim -d
  dotf agents -ic
  dotf agents -cd"""

_DOCTOR_BYPASS_MSG = """错误: --doctor 已不再作为 config/sync 旁路旗标

请改用:
  dotf agents -d              # 仅诊断
  dotf agents -cd             # 先配置再诊断"""

_ACTION_COMBOS = {
    "-ic": ("i", "c"),
    "-id": ("i", "d"),
    "-di": ("i", "d"),
    "-cd": ("c", "d"),
    "-dc": ("c", "d"),
    "-icd": ("i", "c", "d"),
    "-idc": ("i", "c", "d"),
    "-cid": ("i", "c", "d"),
    "-cdi": ("i", "c", "d"),
    "-dic": ("i", "c", "d"),
    "-dci": ("i", "c", "d"),
}


def _reject_legacy() -> None:
    raise DotfError("usage", _LEGACY_SYNTAX_MSG)


def _reject_doctor_bypass() -> None:
    raise DotfError("usage", _DOCTOR_BYPASS_MSG)


class _Abort(Exception):
    """已输出错误文案，直接以 usage 退出的快捷路径。"""


def _guard_independent(name: str, modules: list[str], acting: bool, msg: str | None = None) -> None:
    if modules or acting:
        raise DotfError("usage", msg or f"错误: {name} 为独立命令")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    command_name = args[0] if args else "dotf"
    ctx = Ctx()
    try:
        return _dispatch(ctx, args)
    except _Abort:
        return 1
    except DotfError as err:
        if ctx.json:
            emit_error(command_name, err, json_mode=True, verbose=ctx.verbose)
        else:
            print(render(err, verbose=ctx.verbose), file=sys.stderr)
        return err.rc if err.rc is not None else exit_code(err.code)
    except KeyboardInterrupt:
        return 130


def _dispatch(ctx: Ctx, args: list[str]) -> int:
    if not args:
        print(HELP_TEXT)
        return 0

    modules: list[str] = []
    config_extra: list[str] = []
    doctor_extra: list[str] = []
    do_i = do_c = do_d = do_uninstall = do_deconfig = 0
    want_all = False
    saw_action_flag = False
    positional_before_action = False

    def acting() -> bool:
        return bool(do_i or do_c or do_d or do_uninstall or do_deconfig)

    def flag_error(msg: str) -> None:
        """与旧 bash 一致：文案到 stdout、退出 1。help 类输出由调用点先打印。"""
        print(msg)
        raise _Abort()

    i = 0
    while i < len(args):
        a = args[i]

        # --- 独立命令 ---
        if a == "pull":
            _guard_independent("pull", modules, acting())
            return cmd_pull()
        if a == "init":
            _guard_independent("init", modules, acting())
            return cmd_init(ctx, args[i + 1 :])
        if a == "tui":
            _guard_independent("tui", modules, acting(), "错误: tui 为独立命令，不能与模块或动作旗标混用")
            return cmd_tui(ctx, args[i + 1 :])
        if a == "agents" and (args[i + 1] if i + 1 < len(args) else "") in ("skill", "mcp"):
            _guard_independent("agents skill|mcp", modules, acting(), "错误: agents skill|mcp 为独立命令")
            return cmd_agents_artifact(ctx, args[i + 1 :])
        if a == "skills":
            _guard_independent("skills", modules, acting())
            return cmd_skills(ctx, args[i + 1 :])
        if a == "status":
            _guard_independent("status", modules, acting())
            return cmd_status(ctx, args[i + 1 :])
        if a == "retry":
            _guard_independent("retry", modules, acting())
            return cmd_retry(ctx)
        if a == "__path":
            return cmd_path()

        # --- 动作旗标 ---
        if a in ("-i", "--install"):
            saw_action_flag = True
            if do_c and modules and not positional_before_action:
                _reject_legacy()
            do_i = 1
        elif a in ("-c", "--config"):
            saw_action_flag = True
            if do_i and modules and not positional_before_action:
                _reject_legacy()
            do_c = 1
        elif a == "-d":
            saw_action_flag = True
            do_d = 1
        elif a == "--doctor":
            if do_c and not do_d:
                _reject_doctor_bypass()
            saw_action_flag = True
            do_d = 1
        elif a in _ACTION_COMBOS:
            saw_action_flag = True
            if "i" in _ACTION_COMBOS[a]:
                do_i = 1
            if "c" in _ACTION_COMBOS[a]:
                do_c = 1
            if "d" in _ACTION_COMBOS[a]:
                do_d = 1
        elif a in ("-a", "--all"):
            want_all = True
        elif a in ("-h", "--help"):
            print(HELP_TEXT)
            return 0
        elif a in ("--skills-only", "--env-only", "--strict"):
            config_extra.append(a)
        elif a in ("--uninstall", "--deconfig"):
            if do_i or do_c or do_d:
                flag_error(f"错误: {a} 不能与 -i/-c/-d 组合成新字母串")
            saw_action_flag = True
            if a == "--uninstall":
                do_uninstall = 1
            else:
                do_deconfig = 1
        elif a == "--dry-run":
            ctx.dry_run = True
        elif a == "--continue-on-error":
            ctx.continue_on_error = True
        elif a in ("--yes", "-y"):
            ctx.yes = True
        elif a == "--json":
            ctx.json = True
            doctor_extra.append("--json")
        elif a == "--deep":
            ctx.deep = True
            doctor_extra.append("--deep")
        elif a == "--verbose":
            ctx.verbose = True
            doctor_extra.append("--verbose")
        elif a == "--fail-on":
            i += 1
            if i >= len(args):
                raise DotfError("usage", "错误: --fail-on 需要参数")
            doctor_extra += ["--fail-on", args[i]]
        elif a == "--tool":
            i += 1
            if i >= len(args):
                raise DotfError("usage", "错误: --tool 需要参数")
            config_extra.append(args[i])
            doctor_extra += ["--tool", args[i]]
        elif a == "--profile":
            i += 1
            if i >= len(args):
                raise DotfError("usage", "错误: --profile 需要参数")
            ctx.usage_profile = args[i]
            config_extra += ["--profile", args[i]]
            doctor_extra += ["--profile", args[i]]
        elif a.startswith("-"):
            print(f"错误: 未知选项 '{a}'")
            print()
            print(HELP_TEXT)
            raise _Abort()
        else:
            # 位置参数 = 模块名
            if not saw_action_flag:
                positional_before_action = True
            else:
                _reject_legacy()
            modules.append(a)
        i += 1

    if (do_uninstall or do_deconfig) and (do_i or do_c or do_d):
        flag_error("错误: --uninstall/--deconfig 不能与 -i/-c/-d 组合成新字母串")

    actions: list[str] = []
    if do_i:
        actions.append("install")
    if do_c:
        actions.append("config")
    if do_d:
        actions.append("doctor")
    if do_uninstall:
        actions.append("uninstall")
    if do_deconfig:
        actions.append("deconfig")
    actions_csv = ",".join(actions)

    # --- 全量模式 ---
    if want_all:
        if modules:
            flag_error("错误: -a/--all 不能与模块名同时使用")
        if not actions:
            actions_csv = "install,config"
        plan_and_run(
            ctx,
            actions_csv,
            select_all=True,
            profile=ctx.usage_profile,
            config_extra=tuple(config_extra),
            doctor_extra=tuple(doctor_extra),
        )
        return 0

    # --- 必须有动作 ---
    if not actions:
        print(HELP_TEXT)
        flag_error("错误: 请指定动作 -i / -c / -d / -ic / -id / -cd / -icd 或 --uninstall / --deconfig")

    # --- 无模块 → 交互选择 ---
    selected = list(modules)
    if not selected:
        if do_i and not do_c and not do_d:
            cap = "install"
        elif do_c and not do_i and not do_d:
            cap = "config"
        elif do_d and not do_i and not do_c:
            cap = "doctor"
        else:
            cap = ""  # 展示全部，执行时校验
        selected = interactive_select(cap or "all")

    # --- 深层 agents 选项仅支持 agents（--json/--verbose 已是全局契约，不在此列） ---
    if config_extra or doctor_extra:
        only_agents = all(m == "agents" for m in selected)
        if not only_agents:
            agents_only = any(
                x in (
                    "--skills-only", "--env-only", "--strict",
                    "--deep", "--fail-on", "--tool",
                )
                for x in config_extra + doctor_extra
            )
            if agents_only:
                flag_error("错误: 诊断/agents 选项仅支持与 agents 一起使用（如: dotf agents -d --json）")

    modules_csv = ",".join(selected)
    plan_and_run(
        ctx,
        actions_csv,
        modules_csv=modules_csv,
        config_extra=tuple(config_extra),
        doctor_extra=tuple(doctor_extra),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
