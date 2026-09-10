"""claude-code 模块：安装策略顺序与兜底（curl/npm 桩，全程离线）。

回归背景：官方一键脚本 https://claude.ai/install.sh 在部分网络被 Cloudflare 挑战，
curl 直接 403。模块必须先试官方脚本（下载确认后再执行，不 curl | bash），失败才走
官方分发仓库直装 + manifest sha256，最后才是 npm。
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "scripts" / "modules" / "claude-code" / "lib.sh"

OFFICIAL_URL = "https://claude.ai/install.sh"
OFFICIAL_HTML = b"<!DOCTYPE html><html><body>App unavailable in region</body></html>\n"
DIST_BASE = "https://downloads.claude.ai/claude-code-releases"
VERSION = "9.9.9"
BINARY = b'#!/bin/sh\necho "9.9.9 (Claude Code)"\n'

OFFICIAL_STUB = """#!/bin/bash
set -e
mkdir -p "$HOME/.local/bin" "$HOME/.local/share/claude/versions"
printf '#!/bin/sh\\necho "__VERSION__ (Claude Code)"\\n' >"$HOME/.local/share/claude/versions/__VERSION__"
chmod +x "$HOME/.local/share/claude/versions/__VERSION__"
ln -sfn "$HOME/.local/share/claude/versions/__VERSION__" "$HOME/.local/bin/claude"
"""

NPM_FAIL_STUB = """#!/usr/bin/env bash
echo "npm stub: 测试中不应触达真实 npm" >&2
exit 1
"""

CURL_STUB = """#!/usr/bin/env bash
set -u
url=""; out=""
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    --max-time|--retry|--retry-delay|--connect-timeout|--speed-limit|--speed-time) shift 2 ;;
    -*) shift ;;
    *) url="$1"; shift ;;
  esac
done
printf '%s\\n' "$url" >>"__LOG__"
src="__URL_ROOT__/${url#*://}"
if [ ! -f "$src" ]; then
  printf 'curl: (22) The requested URL returned error: 403\\n' >&2
  exit 22
fi
if [ -n "$out" ]; then cp "$src" "$out"; else cat "$src"; fi
"""

NPM_STUB = """#!/usr/bin/env bash
set -u
case "${1:-}" in
  prefix) printf '%s\\n' "__PREFIX__" ;;
  install)
    mkdir -p "__PREFIX__/bin"
    printf '#!/bin/sh\\necho "9.9.9 (Claude Code)"\\n' >"__PREFIX__/bin/claude"
    chmod +x "__PREFIX__/bin/claude"
    ;;
esac
exit 0
"""


def _exec_script(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _lib_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["SCRIPT_DIR"] = str(ROOT)
    env["DOTFILES_ROOT"] = str(ROOT)
    # 双保险：即使某条路径漏过 stub，真实 npm 也只会连接失败，不会产生副作用
    env["npm_config_registry"] = "http://127.0.0.1:1/"
    if extra:
        env.update(extra)
    return env


def _platform_key() -> str:
    proc = subprocess.run(
        ["bash", "-c", f'source "{LIB}"; _claude_code_platform_key'],
        capture_output=True,
        text=True,
        env=_lib_env(),
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        pytest.skip(f"测试主机平台不被模块支持: {proc.stdout}{proc.stderr}")
    return proc.stdout.strip()


def _dist_fixtures(platform: str, checksum: str) -> dict[str, bytes]:
    return {
        f"{DIST_BASE}/latest": f"{VERSION}\n".encode(),
        f"{DIST_BASE}/{VERSION}/manifest.json": json.dumps(
            {"version": VERSION, "platforms": {platform: {"binary": "claude", "checksum": checksum}}}
        ).encode(),
        f"{DIST_BASE}/{VERSION}/{platform}/claude": BINARY,
    }


def _prepare(tmp_path: Path, fixtures: dict[str, bytes]) -> tuple[Path, Path]:
    stubs = tmp_path / "stub-bin"
    stubs.mkdir()
    url_root = tmp_path / "urls"
    for url, payload in fixtures.items():
        target = url_root / url.split("://", 1)[1]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    log = tmp_path / "curl.log"
    _exec_script(
        stubs / "curl",
        CURL_STUB.replace("__LOG__", str(log)).replace("__URL_ROOT__", str(url_root)),
    )
    # 默认 npm 一定失败：任何用例都不允许跑到真实 npm
    _exec_script(stubs / "npm", NPM_FAIL_STUB)
    return stubs, log


def _path_without_claude(stubs: Path) -> str:
    parts = [str(stubs)]
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if entry and not (Path(entry) / "claude").exists():
            parts.append(entry)
    return os.pathsep.join(parts)


def _run_install(home: Path, stubs: Path, extra_env: dict[str, str] | None = None):
    env = _lib_env({"HOME": str(home), "PATH": _path_without_claude(stubs)})
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", "-c", f'source "{LIB}"; install_claude_code'],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _installed(home: Path) -> Path:
    return home / ".local" / "share" / "claude" / "versions" / VERSION


def test_official_installer_is_tried_first(tmp_home: Path, tmp_path: Path) -> None:
    stubs, log = _prepare(
        tmp_path, {OFFICIAL_URL: OFFICIAL_STUB.replace("__VERSION__", VERSION).encode()}
    )

    proc = _run_install(tmp_home, stubs)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (tmp_home / ".local" / "bin" / "claude").is_symlink()
    assert "官方脚本" in proc.stdout
    # 官方脚本成功就不再碰分发仓库
    assert log.read_text(encoding="utf-8").splitlines() == [OFFICIAL_URL]


def test_official_html_is_not_executed_and_falls_back_to_repo(tmp_home: Path, tmp_path: Path) -> None:
    platform = _platform_key()
    checksum = hashlib.sha256(BINARY).hexdigest()
    fixtures = {OFFICIAL_URL: OFFICIAL_HTML, **_dist_fixtures(platform, checksum)}
    stubs, log = _prepare(tmp_path, fixtures)

    proc = _run_install(tmp_home, stubs)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "不是 shell 脚本" in proc.stdout
    assert "sha256 校验通过" in proc.stdout
    assert _installed(tmp_home).read_bytes() == BINARY
    assert (tmp_home / ".local" / "bin" / "claude").is_symlink()
    urls = log.read_text(encoding="utf-8").splitlines()
    assert urls[0] == OFFICIAL_URL
    assert f"{DIST_BASE}/latest" in urls


def test_native_install_layout_and_checksum(tmp_home: Path, tmp_path: Path) -> None:
    platform = _platform_key()
    checksum = hashlib.sha256(BINARY).hexdigest()
    stubs, log = _prepare(tmp_path, _dist_fixtures(platform, checksum))

    proc = _run_install(tmp_home, stubs)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    target = _installed(tmp_home)
    link = tmp_home / ".local" / "bin" / "claude"
    assert target.read_bytes() == BINARY
    assert target.stat().st_mode & stat.S_IXUSR
    assert link.is_symlink() and os.readlink(link) == str(target)

    urls = log.read_text(encoding="utf-8").splitlines()
    assert f"{DIST_BASE}/{VERSION}/{platform}/claude" in urls
    assert all("install.ps1" not in url for url in urls)


def test_checksum_mismatch_fails_closed_without_fallback(tmp_home: Path, tmp_path: Path) -> None:
    platform = _platform_key()
    stubs, _ = _prepare(tmp_path, _dist_fixtures(platform, "0" * 64))

    proc = _run_install(tmp_home, stubs)

    assert proc.returncode != 0
    assert "校验失败" in proc.stdout
    assert "@anthropic-ai/claude-code@latest" not in proc.stdout
    assert not (tmp_home / ".local" / "bin" / "claude").exists()
    assert not _installed(tmp_home).exists()


def test_npm_fallback_when_every_source_fails(tmp_home: Path, tmp_path: Path) -> None:
    stubs, _ = _prepare(tmp_path, {})
    prefix = tmp_path / "npm-prefix"
    _exec_script(stubs / "npm", NPM_STUB.replace("__PREFIX__", str(prefix)))

    proc = _run_install(tmp_home, stubs)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "npm" in proc.stdout
    assert (prefix / "bin" / "claude").exists()


def test_module_downloads_script_instead_of_piping_to_bash() -> None:
    text = LIB.read_text(encoding="utf-8")
    # 注释里保留了背景说明，只看真正会执行的代码行
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    assert OFFICIAL_URL in code
    assert "| bash" not in code
    assert "^#!" in code  # 执行前确认真的是 shell 脚本
    assert "downloads.claude.ai/claude-code-releases" in code
    assert "manifest.json" in code and "sha256" in code
    assert ".local/share/claude/versions" in text
