"""独立子命令：path / status / tui / retry / skills / agents / init / pull。

每个函数对应旧 bin/dotf 的一个 cmd_*，文案与分支逐一对齐。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from .errors import DotfError
from .help_text import HELP_TEXT
from .runner import (
    Ctx,
    REPO_ROOT,
    SCRIPTS_DIR,
    SRC_DIR,
    default_usage_profile,
    detect_os,
    modules_py,
    plan_and_run,
    python_env,
    skills_map_py,
)

HELP = "-h", "--help"


def cmd_path() -> int:
    print(REPO_ROOT)
    return 0


def cmd_status(ctx: Ctx, argv: list[str]) -> int:
    usage_profile = ""
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--profile":
            i += 1
            usage_profile = argv[i] if i < len(argv) else ""
        elif arg == "--json":
            ctx.json = True
        elif arg in HELP:
            print("用法: dotf status [--profile <name>] [--json]")
            print("  只读 L0 检查；不安装、不改配置、不跑 L1")
            return 0
        else:
            raise DotfError("usage", f"错误: 未知选项 {arg}")
        i += 1

    if not usage_profile:
        usage_profile = default_usage_profile()

    os.environ["DOTF_STATUS_MODE"] = "1"
    os.environ["DOTF_YES"] = "1"
    ctx.yes = True

    header = f"环境状态  profile={usage_profile} (只读 L0)"
    print(header, file=sys.stderr if ctx.json else sys.stdout)
    plan_and_run(ctx, "doctor", profile=usage_profile)
    return 0


def cmd_tui(ctx: Ctx, argv: list[str]) -> int:
    for arg in argv:
        if arg in HELP:
            print("用法: dotf tui")
            print("  需要 TTY；缺 Textual 时失败并提示用户级安装")
            print("  提交后走与 CLI 相同的计划确认（/dev/tty）")
            return 0
        if arg in (
            "-i", "-c", "-d", "--install", "--config", "--doctor",
            "--uninstall", "--deconfig", "-ic", "-id", "-cd", "-icd", "-a", "--all",
        ):
            raise DotfError(
                "usage",
                "错误: tui 为独立命令，不能与动作旗标混用\n"
                "请改用 CLI，例如: dotf nvim --deconfig 或 dotf agents skill apply <id>",
            )
        raise DotfError(
            "usage",
            f"错误: tui 不接受参数 '{arg}'\n请改用 CLI 动词",
        )

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print(
            "错误: dotf tui 需要 TTY。请改用 CLI，例如: dotf nvim --deconfig 或 dotf agents skill apply <id>",
            file=sys.stderr,
        )
        return 2
    os.execvp(
        "python3",
        ["python3", "-m", "dotf_tui"],
    )
    return 0  # pragma: no cover - execvp 不返回


def cmd_retry(ctx: Ctx) -> int:
    report = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; dotf_report_load',
            "_",
            str(SCRIPTS_DIR / "lib" / "report.sh"),
        ],
        capture_output=True,
        text=True,
    )
    if report.returncode != 0:
        sys.stderr.write(report.stderr)
        raise DotfError("env", "无法加载最近执行报告")

    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(report.stdout)
        report_file = f.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".plan", delete=False) as f:
        plan_file = f.name
    try:
        proc = subprocess.run(
            ["python3", "-m", "dotf_core.retry_plan", report_file, plan_file],
            env=python_env(),
        )
        if proc.returncode != 0:
            raise DotfError("plan", "无法从报告中重建失败计划")
        os.environ["DOTF_YES"] = "1"
        rc = subprocess.run(
            ["bash", str(SCRIPTS_DIR / "run_plan.sh"), "--yes", "--plan-file", plan_file]
        ).returncode
        if rc != 0:
            raise DotfError("handler", f"重试执行失败（退出码 {rc}）")
    finally:
        os.unlink(report_file)
        os.unlink(plan_file)
    return 0


# ============================================================
# skills
# ============================================================

_SKILLS_HELP = """用法: dotf skills -i <package> [选项...]
      dotf skills -r|--uninstall [skill-name] [选项...]
  -i 通过 npx skills 安装；<package> 一般直接写 skill 名称
  -r 移除已安装 skill；省略名称时进入 npx skills 交互式移除
  <name> 解析顺序：先匹配 agents/skills.yaml 的 group，再匹配 skill id，
  最后按字面透传给 npx skills 搜索；一手 skill 请用 dotf agents skill apply
  也可写 owner/repo 或 URL 来指定来源仓库
  默认交互式：npx skills 会询问安装位置与目标 agents
  -g 全局；--project 当前项目；-y 跳过询问；-a 指定 agents
示例:
  dotf skills -i frontend-design
  dotf skills -i frontend-design --project
  dotf skills -r design-taste-frontend"""


def cmd_skills(ctx: Ctx, argv: list[str]) -> int:
    if not argv:
        print("错误: 需要 -i/--install 或 -r/--remove 动作")
        print("用法: dotf skills -i <package> [选项...]")
        return 1
    verb = argv[0]
    mode = "add"
    if verb in ("-i", "--install"):
        pass
    elif verb in ("-r", "--remove", "--uninstall"):
        mode = "remove"
    elif verb in HELP:
        print(_SKILLS_HELP)
        return 0
    else:
        print("错误: skills 仅支持 -i/--install 与 -r/--remove/--uninstall")
        print("用法: dotf skills -i <package> [选项...]")
        return 1

    package = ""
    want_global = False
    want_project = False
    extra: list[str] = []
    i = 0
    rest = argv[1:]
    while i < len(rest):
        arg = rest[i]
        if arg == "--project":
            want_project = True
        elif arg in ("-g", "--global"):
            want_global = True
            extra.append("-g")
        elif arg == "--dry-run":
            ctx.dry_run = True
        elif arg in ("-a", "--agent", "-s", "--skill", "--subagent", "--metadata"):
            if i + 1 >= len(rest):
                raise DotfError("usage", f"错误: {arg} 需要参数")
            extra += [arg, rest[i + 1]]
            i += 1
        elif arg.startswith("-"):
            extra.append(arg)
        else:
            if package:
                raise DotfError("usage", f"错误: 多余参数 '{arg}'；一次只安装一个 package")
            package = arg
        i += 1

    if not package and mode == "add":
        print("错误: 需要 skills package")
        print("用法: dotf skills -i <package> [选项...]")
        return 1
    if want_global and want_project:
        print("错误: -g/--global 与 --project 只能二选一")
        return 1

    package_args: list[str] = []
    if package:
        resolver_args = ["--remove", package] if mode == "remove" else [package]
        proc = skills_map_py(*resolver_args, capture=True)
        sys.stderr.write(proc.stderr)
        if proc.returncode != 0:
            return 1
        package_args = [line for line in proc.stdout.splitlines() if line.strip()]

    skills_args = [mode, *package_args, *extra]
    print(f"==> npx skills {' '.join(skills_args)}", flush=True)
    if ctx.dry_run:
        return 0
    if shutil.which("npx") is None:
        raise DotfError("env", "错误: 未找到 npx；请先安装 Node.js/npm")
    rc = subprocess.run(["npx", "--yes", "skills", *skills_args]).returncode
    if rc != 0:
        raise DotfError("handler", f"npx skills 失败（退出码 {rc}）")
    return 0


# ============================================================
# agents skill|mcp artifact
# ============================================================

def cmd_agents_artifact(ctx: Ctx, argv: list[str]) -> int:
    kind = argv[0] if argv else ""
    verb = argv[1] if len(argv) > 1 else ""
    if kind not in ("skill", "mcp"):
        raise DotfError("usage", f"错误: 未知 agents 制品 '{kind}'")
    if verb not in ("apply", "remove"):
        print(f"用法: dotf agents {kind} apply|remove <id>")
        return 1

    rest = argv[2:]
    skill_id = ""
    tool = ""
    all_tools = False
    i = 0
    while i < len(rest):
        arg = rest[i]
        if arg == "--tool":
            i += 1
            if i >= len(rest):
                raise DotfError("usage", "错误: --tool 需要参数")
            tool = rest[i]
        elif arg == "--all-tools":
            all_tools = True
        elif arg in ("--yes", "-y"):
            ctx.yes = True
        elif arg == "--dry-run":
            ctx.dry_run = True
        elif arg == "--continue-on-error":
            ctx.continue_on_error = True
        elif arg == "--json":
            ctx.json = True
        elif arg.startswith("-"):
            raise DotfError("usage", f"错误: 未知选项 '{arg}'")
        else:
            if skill_id:
                raise DotfError("usage", f"错误: 多余参数 '{arg}'")
            skill_id = arg
        i += 1

    if not skill_id:
        print(f"错误: 需要 {kind} id")
        return 1

    action = f"{kind}.{verb}"
    if kind == "skill":
        if tool or all_tools:
            print("错误: skill apply/remove 以本机为粒度，不接受 --tool/--all-tools")
            return 1
        proc = skills_map_py("--expand-group", skill_id, capture=True)
        sys.stderr.write(proc.stderr)
        if proc.returncode != 0:
            return 1
        group_ids = [line for line in proc.stdout.splitlines() if line.strip()]
        if group_ids:
            plan_and_run(ctx, action, modules_csv=",".join(f"skill:{g}" for g in group_ids))
            return 0
        plan_and_run(ctx, action, modules_csv=f"skill:{skill_id}")
        return 0

    if all_tools and tool:
        print("错误: --tool 与 --all-tools 不能同时使用")
        return 1
    if not all_tools and not tool:
        print("错误: mcp 需要 --tool <tool> 或显式 --all-tools")
        return 1
    selector = f"mcp:*/{skill_id}" if all_tools else f"mcp:{tool}/{skill_id}"
    plan_and_run(ctx, action, modules_csv=selector)
    return 0


# ============================================================
# init
# ============================================================

_INIT_HELP = """用法: dotf init [--os <id>] [--profile <name>] [--yes] [--dry-run] [--continue-on-error] [--list]

  OS 决定平台适用性；--profile 选择使用场景（默认 full）
  --os <id>        强制 OS（darwin、ubuntu、arch…）
  --profile <name> 使用场景 profile（minimal/remote/desktop/full）
  --list           列出 OS 与使用场景 profile
  --dry-run        只展示计划（允许跨 OS 预览）
  --continue-on-error 失败后仅继续依赖无关动作（最终仍非零）
  --yes            跳过计划确认与副作用确认"""


def cmd_init(ctx: Ctx, argv: list[str]) -> int:
    force_os = ""
    list_only = False
    usage_profile = ""
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--list":
            list_only = True
        elif arg == "--os":
            i += 1
            if i >= len(argv):
                raise DotfError("usage", "错误: --os 需要参数")
            force_os = argv[i]
        elif arg == "--profile":
            i += 1
            if i >= len(argv):
                raise DotfError("usage", "错误: --profile 需要参数")
            usage_profile = argv[i]
        elif arg in ("--yes", "-y"):
            ctx.yes = True
        elif arg == "--dry-run":
            ctx.dry_run = True
        elif arg == "--continue-on-error":
            ctx.continue_on_error = True
        elif arg in HELP:
            print(_INIT_HELP)
            return 0
        else:
            print(f"错误: 未知 init 选项 '{arg}'")
            print("用法: dotf init [--os <id>] [--profile <name>] [--list]")
            return 1
        i += 1

    if list_only:
        print("可用 OS profile:")
        proc = modules_py("profiles", "os", capture=True)
        for line in proc.stdout.splitlines():
            print(f"  {line}")
        print()
        print("可用使用场景 profile:")
        proc = modules_py("profiles", "usage", capture=True)
        for line in proc.stdout.splitlines():
            print(f"  {line}")
        return 0

    if not usage_profile:
        usage_profile = default_usage_profile()

    if force_os:
        os_id = force_os
        print(f"使用强制 OS: {os_id}")
    else:
        os_id = detect_os()
        print(f"检测到 OS: {os_id}")

    print("============================================")
    print(f"  Dotfiles 初始化 (os={os_id} profile={usage_profile})")
    print("============================================")
    print()

    plan_and_run(ctx, "install,config", os_id=os_id, profile=usage_profile)
    return 0


# ============================================================
# pull
# ============================================================

def _git(*args: str) -> subprocess.CompletedProcess:
    sys.stdout.flush()  # 子进程直写 fd，先冲刷 Python 缓冲保证输出顺序
    return subprocess.run(["git", *args], cwd=REPO_ROOT)


def cmd_pull() -> int:
    def dirty() -> bool:
        return (
            _git("diff", "--quiet").returncode != 0
            or _git("diff", "--cached", "--quiet").returncode != 0
            or bool(
                subprocess.run(
                    ["git", "ls-files", "--others", "--exclude-standard"],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
            )
        )

    stashed = False
    if dirty():
        print("检测到未提交的改动，执行 stash...")
        if _git("stash").returncode != 0:
            raise DotfError("env", "错误: git stash 失败")
        stashed = True

    print("拉取最新代码...")
    if _git("pull").returncode != 0:
        print("错误: git pull 失败")
        if stashed:
            print("改动已 stash，请手动恢复: git stash pop")
        raise DotfError("env", "错误: git pull 失败")

    if stashed:
        print("恢复暂存的改动...")
        if _git("stash", "pop").returncode != 0:
            print()
            print("⚠️  stash pop 发生冲突，请手动解决：")
            print("   1. 查看冲突文件: git status")
            print("   2. 解决冲突后: git stash drop")
            raise DotfError("conflict", "stash pop 冲突，请手动解决")
    print("✓ dotfiles 已更新")
    return 0
