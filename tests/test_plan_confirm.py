"""分层确认：TTY I/O、计划路径无冗余 confirm、副作用白名单与 --yes。"""

from __future__ import annotations

import os
import re
import select
import stat
import subprocess
import textwrap
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN_PLAN = ROOT / "scripts" / "run_plan.sh"
COMMON = ROOT / "scripts" / "tools" / "common.sh"
SYSTEM = ROOT / "scripts" / "tools" / "system.sh"
TOOLS = ROOT / "scripts" / "tools"


def _pty_run(
    script: str,
    *,
    feed: bytes,
    feed_when: str,
    env: dict[str, str] | None = None,
    timeout: float = 8.0,
) -> str:
    """在伪终端中运行 bash 脚本；当输出出现 feed_when 时向 /dev/tty 写入 feed。"""
    import pty

    master, slave = pty.openpty()
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    pid = os.fork()
    if pid == 0:
        os.close(master)
        os.setsid()
        try:
            import fcntl
            import termios

            fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
        except OSError:
            pass
        os.dup2(slave, 0)
        os.dup2(slave, 1)
        os.dup2(slave, 2)
        if slave > 2:
            os.close(slave)
        os.chdir(str(ROOT))
        os.execve("/bin/bash", ["bash", "-c", script], run_env)
    os.close(slave)

    def _finish(status: int) -> str:
        # 排空剩余输出
        while True:
            ready, _, _ = select.select([master], [], [], 0.05)
            if not ready:
                break
            try:
                chunk = os.read(master, 4096)
            except OSError:
                break
            if not chunk:
                break
            buf.extend(chunk)
        os.close(master)
        text = buf.decode(errors="replace")
        if os.WIFEXITED(status) and os.WEXITSTATUS(status) != 0:
            raise AssertionError(f"pty bash exit {os.WEXITSTATUS(status)}:\n{text}")
        return text

    buf = bytearray()
    fed = False
    deadline = time.time() + timeout
    while time.time() < deadline:
        ready, _, _ = select.select([master], [], [], 0.2)
        if ready:
            try:
                chunk = os.read(master, 4096)
            except OSError:
                # slave 关闭：回收子进程
                _, status = os.waitpid(pid, 0)
                return _finish(status)
            if not chunk:
                _, status = os.waitpid(pid, 0)
                return _finish(status)
            buf.extend(chunk)
            if not fed and feed and feed_when in buf.decode(errors="replace"):
                os.write(master, feed)
                fed = True

        waited_pid, status = os.waitpid(pid, os.WNOHANG)
        if waited_pid == pid:
            return _finish(status)

    try:
        os.kill(pid, 9)
        os.waitpid(pid, 0)
    except OSError:
        pass
    try:
        os.close(master)
    except OSError:
        pass
    raise TimeoutError(buf.decode(errors="replace"))


def test_confirm_uses_dev_tty_io() -> None:
    text = COMMON.read_text(encoding="utf-8")
    assert ">/dev/tty" in text
    assert "read -r reply </dev/tty" in text
    assert "DOTF_YES" in text and "ASSUME_YES" in text


def test_confirm_dotf_yes_short_circuits_under_capture() -> None:
    """stdout/stderr 被捕获时，DOTF_YES 仍应短路成功（不读 tty）。"""
    r = subprocess.run(
        [
            "bash",
            "-c",
            textwrap.dedent(
                f"""\
                set -euo pipefail
                SCRIPT_DIR="{ROOT}"
                source "{COMMON}"
                export DOTF_YES=1
                out=$(mktemp)
                confirm "不应出现" "N" >"$out" 2>&1
                rc=$?
                cat "$out"
                exit $rc
                """
            ),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "不应出现" not in r.stdout
    assert "不应出现" not in r.stderr


def test_confirm_prompt_on_tty_while_stdout_captured() -> None:
    """模拟 runner 捕获 stdout/stderr：提示仍经 /dev/tty。"""
    script = textwrap.dedent(
        f"""\
        set -euo pipefail
        SCRIPT_DIR="{ROOT}"
        source "{COMMON}"
        out=$(mktemp)
        if confirm "副作用测试?" "N" >"$out" 2>&1; then
          echo CONFIRM_YES
        else
          echo CONFIRM_NO
        fi
        if grep -q "副作用测试" "$out" 2>/dev/null; then
          echo CAPTURED_PROMPT
        else
          echo CAPTURE_CLEAN
        fi
        """
    )
    out = _pty_run(script, feed=b"n\n", feed_when="副作用测试")
    assert "副作用测试" in out
    assert "CAPTURE_CLEAN" in out
    assert "CAPTURED_PROMPT" not in out
    assert "CONFIRM_NO" in out


def test_run_plan_exports_dotf_yes_only_with_yes_flag() -> None:
    text = RUN_PLAN.read_text(encoding="utf-8")
    assert "export DOTF_YES=1" in text
    plan_confirm = text.split("按计划执行?")[0]
    assert "export DOTF_YES" not in plan_confirm
    assert re.search(
        r'if \[ "\$ASSUME_YES" -eq 1 \]; then\s*\n\s*export DOTF_YES=1',
        text,
    )


def test_system_keeps_side_effect_confirms_only() -> None:
    text = SYSTEM.read_text(encoding="utf-8")
    assert "是否安装系统软件包?" not in text
    assert "是否配置 zsh" not in text
    assert "是否配置 Docker" in text
    assert "是否安装并配置 Docker Engine?" in text
    assert "是否将默认 Shell 更改为 zsh?" in text


def test_regular_modules_have_no_install_confirm() -> None:
    """白名单外模块不应再有「是否安装/配置」confirm。"""
    side_effect_files = {"system.sh", "common.sh"}
    pattern = re.compile(r'confirm\s+"是否')
    offenders: list[str] = []
    for path in TOOLS.glob("*.sh"):
        if path.name in side_effect_files:
            continue
        text = path.read_text(encoding="utf-8")
        if pattern.search(text):
            offenders.append(path.name)
    assert offenders == [], f"仍含安装/配置 confirm: {offenders}"


def test_plan_y_does_not_set_dotf_yes_for_handlers(tmp_home: Path, tmp_path: Path) -> None:
    """计划确认通过（非 --yes）时，处理器环境不应带 DOTF_YES=1。"""
    handlers = tmp_path / "handlers"
    mod = handlers / "probe"
    mod.mkdir(parents=True)
    install = mod / "install.sh"
    install.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            echo "DOTF_YES=${DOTF_YES:-}"
            echo "ASSUME_YES=${ASSUME_YES:-}"
            dotf_result_changed "probed"
            """
        ),
        encoding="utf-8",
    )
    install.chmod(install.stat().st_mode | stat.S_IXUSR)

    plan = tmp_path / "plan.txt"
    plan.write_text(
        "PLAN_OK\nOS\tlinux\nPROFILE\t\nACTION\t1\tinstall\tprobe\texplicit\n",
        encoding="utf-8",
    )

    env = {
        "HOME": str(tmp_home),
        "DOTF_HANDLERS_DIR": str(handlers),
        "DOTFILES_ROOT": str(ROOT),
    }
    # 清掉可能继承的授权
    full_env = os.environ.copy()
    full_env.update(env)
    full_env.pop("DOTF_YES", None)
    full_env.pop("ASSUME_YES", None)

    script = f'bash "{RUN_PLAN}" --plan-file "{plan}"'
    out = _pty_run(
        script, feed=b"y\n", feed_when="按计划执行", env=full_env, timeout=15.0
    )
    assert "DOTF_YES=" in out
    assert "DOTF_YES=1" not in out
    assert "RESULT\tchanged\tprobe\tinstall" in out


def test_run_plan_yes_sets_dotf_yes(tmp_home: Path, tmp_path: Path) -> None:
    handlers = tmp_path / "handlers"
    mod = handlers / "probe"
    mod.mkdir(parents=True)
    install = mod / "install.sh"
    install.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            echo "DOTF_YES=${DOTF_YES:-}"
            dotf_result_changed "probed"
            """
        ),
        encoding="utf-8",
    )
    install.chmod(install.stat().st_mode | stat.S_IXUSR)
    plan = tmp_path / "plan.txt"
    plan.write_text(
        "PLAN_OK\nOS\tlinux\nPROFILE\t\nACTION\t1\tinstall\tprobe\texplicit\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["DOTF_HANDLERS_DIR"] = str(handlers)
    r = subprocess.run(
        ["bash", str(RUN_PLAN), "--yes", "--plan-file", str(plan)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "DOTF_YES=1" in r.stdout


def test_help_mentions_layered_confirm(tmp_home: Path) -> None:
    from conftest import run_dotf

    r = run_dotf("-h")
    assert r.returncode == 0
    out = r.stdout
    assert "计划确认" in out
    assert "副作用确认" in out
