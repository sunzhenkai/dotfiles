"""claude-plugins 模块：desired set 幂等同步与诊断。

回归背景：插件状态存在 claude CLI 的本地 store（~/.claude/plugins），仓库只声明
desired set（marketplace 源 + 插件）。同步必须幂等（已在位 → unchanged 且不再调用
add/install），claude 缺失时必须给出 claude-code 的前置提示而不是静默通过。
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "scripts" / "modules" / "claude-plugins" / "lib.sh"
DOCTOR = ROOT / "scripts" / "modules" / "claude-plugins" / "doctor.sh"

MARKETPLACE = "openai/codex-plugin-cc"
PLUGIN = "codex@openai-codex"

CLAUDE_STUB = """#!/usr/bin/env bash
set -u
state="__STATE__"
mkdir -p "$state"
printf '%s\n' "$*" >>"$state/calls.log"
touch "$state/marketplaces.txt" "$state/plugins.txt"
case "${1:-} ${2:-}" in
  "plugin marketplace")
    case "${3:-}" in
      list)
        echo "Configured marketplaces:"
        while IFS= read -r repo; do
          [ -n "$repo" ] || continue
          echo "  ❯ mp-openai-codex"
          echo "    Source: GitHub ($repo)"
        done <"$state/marketplaces.txt"
        ;;
      add)
        printf '%s\n' "${4:-}" >>"$state/marketplaces.txt"
        ;;
      *) exit 1 ;;
    esac
    ;;
  "plugin list")
    echo "Installed plugins:"
    while IFS= read -r spec; do
      [ -n "$spec" ] || continue
      echo "  ❯ $spec"
      echo "    Version: 1.0.0"
      echo "    Status: ✔ enabled"
    done <"$state/plugins.txt"
    ;;
  "plugin install")
    printf '%s\n' "${3:-}" >>"$state/plugins.txt"
    ;;
  *)
    exit 1
    ;;
esac
exit 0
"""


def _exec_script(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _env(home: Path, stubs: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["DOTFILES_ROOT"] = str(ROOT)
    # 仅保留桩目录 + 系统目录：确保真实 claude（mise shim 等）不会混进 PATH
    env["PATH"] = os.pathsep.join([str(stubs), "/usr/bin", "/bin"])
    return env


def _prepare(tmp_path: Path, with_cli: bool = True) -> tuple[Path, Path]:
    stubs = tmp_path / "stub-bin"
    stubs.mkdir()
    state = tmp_path / "state"
    state.mkdir()
    if with_cli:
        _exec_script(stubs / "claude", CLAUDE_STUB.replace("__STATE__", str(state)))
    return stubs, state


def _seed(state: Path, marketplaces: str = "", plugins: str = "") -> None:
    (state / "marketplaces.txt").write_text(marketplaces, encoding="utf-8")
    (state / "plugins.txt").write_text(plugins, encoding="utf-8")


def _run_sync(home: Path, stubs: Path):
    script = (
        f'source "{LIB}"; claude_plugins_sync; rc=$?; '
        'echo "CHANGED=$CLAUDE_PLUGINS_SYNC_CHANGED"; exit "$rc"'
    )
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=_env(home, stubs),
        check=False,
    )


def _run_doctor(home: Path, stubs: Path):
    return subprocess.run(
        ["bash", str(DOCTOR)],
        capture_output=True,
        text=True,
        env=_env(home, stubs),
        check=False,
    )


def test_sync_installs_missing_marketplace_and_plugin(tmp_home: Path, tmp_path: Path) -> None:
    stubs, state = _prepare(tmp_path)
    _seed(state)

    proc = _run_sync(tmp_home, stubs)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "CHANGED=1" in proc.stdout
    assert (state / "marketplaces.txt").read_text(encoding="utf-8").split() == [MARKETPLACE]
    assert (state / "plugins.txt").read_text(encoding="utf-8").split() == [PLUGIN]
    calls = (state / "calls.log").read_text(encoding="utf-8")
    assert f"plugin marketplace add {MARKETPLACE}" in calls
    assert f"plugin install {PLUGIN}" in calls


def test_sync_is_idempotent_when_desired_state_present(tmp_home: Path, tmp_path: Path) -> None:
    stubs, state = _prepare(tmp_path)
    _seed(state, marketplaces=f"{MARKETPLACE}\n", plugins=f"{PLUGIN}\n")

    proc = _run_sync(tmp_home, stubs)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "CHANGED=0" in proc.stdout
    calls = (state / "calls.log").read_text(encoding="utf-8")
    assert "marketplace add" not in calls
    assert "plugin install" not in calls


def test_sync_fails_without_claude_cli(tmp_home: Path, tmp_path: Path) -> None:
    stubs, _ = _prepare(tmp_path, with_cli=False)

    proc = _run_sync(tmp_home, stubs)

    assert proc.returncode != 0
    assert "CHANGED=0" in proc.stdout
    assert "dotf claude-code -i" in proc.stdout + proc.stderr


def test_sync_falls_back_to_local_bin_layout(tmp_home: Path, tmp_path: Path) -> None:
    stubs, state = _prepare(tmp_path, with_cli=False)
    link = tmp_home / ".local" / "bin" / "claude"
    link.parent.mkdir(parents=True)
    _exec_script(link, CLAUDE_STUB.replace("__STATE__", str(state)))

    proc = _run_sync(tmp_home, stubs)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "CHANGED=1" in proc.stdout


def test_doctor_passes_when_desired_state_present(tmp_home: Path, tmp_path: Path) -> None:
    stubs, state = _prepare(tmp_path)
    _seed(state, marketplaces=f"{MARKETPLACE}\n", plugins=f"{PLUGIN}\n")

    proc = _run_doctor(tmp_home, stubs)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"pass  marketplace: {MARKETPLACE}" in proc.stdout
    assert f"pass  plugin: {PLUGIN}" in proc.stdout
    assert "fail " not in proc.stdout


def test_doctor_reports_missing_desired_state(tmp_home: Path, tmp_path: Path) -> None:
    stubs, state = _prepare(tmp_path)
    _seed(state)

    proc = _run_doctor(tmp_home, stubs)

    assert proc.returncode != 0
    assert f"fail  marketplace: 未配置 {MARKETPLACE}" in proc.stdout
    assert f"fail  plugin: 未安装 {PLUGIN}" in proc.stdout
    assert "dotf claude-plugins -i" in proc.stdout
