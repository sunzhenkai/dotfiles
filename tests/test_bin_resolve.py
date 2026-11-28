"""Tests for scripts/lib/bin_resolve.sh and mise shim handling."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _make_exec(path: Path, content: str = "#!/bin/sh\nexit 0\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)
    return path


def _setup_mise_env(tmp_home: Path, *, active_real: Path | None, with_mise: bool = True) -> dict[str, str]:
    mise_data = tmp_home / ".local" / "share" / "mise"
    shims_dir = mise_data / "shims"
    tools_dir = tmp_home / "tools"
    shims_dir.mkdir(parents=True, exist_ok=True)
    tools_dir.mkdir(parents=True, exist_ok=True)

    _make_exec(shims_dir / "pi")

    if with_mise:
        if active_real is not None:
            mise_script = (
                "#!/bin/sh\n"
                'if [ "$1" = "which" ] && [ "$2" = "pi" ]; then\n'
                f'  printf "%s\\n" "{active_real}"\n'
                "  exit 0\n"
                "fi\n"
                "exit 1\n"
            )
        else:
            mise_script = "#!/bin/sh\nexit 1\n"
        _make_exec(tools_dir / "mise", mise_script)

    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["MISE_DATA_DIR"] = str(mise_data)
    env["PATH"] = f"{shims_dir}:{tools_dir}:/usr/bin:/bin"
    return env


def _run_bash(script: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )


def test_dotf_resolve_bin_regular_exec(tmp_home: Path) -> None:
    bin_dir = tmp_home / "bin"
    real_bin = _make_exec(bin_dir / "mytool")
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["PATH"] = f"{bin_dir}:/usr/bin:/bin"

    r = _run_bash(f'source "{ROOT}/scripts/lib/bin_resolve.sh"; dotf_resolve_bin mytool', env)
    assert r.returncode == 0
    assert r.stdout.strip() == str(real_bin)


def test_dotf_resolve_bin_dangling_symlink(tmp_home: Path) -> None:
    bin_dir = tmp_home / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    (bin_dir / "broken").symlink_to(tmp_home / "does-not-exist")
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["PATH"] = f"{bin_dir}:/usr/bin:/bin"

    r = _run_bash(f'source "{ROOT}/scripts/lib/bin_resolve.sh"; dotf_resolve_bin broken', env)
    assert r.returncode != 0
    assert r.stdout.strip() == ""


def test_dotf_resolve_bin_stale_mise_shim(tmp_home: Path) -> None:
    env = _setup_mise_env(tmp_home, active_real=None, with_mise=True)
    r = _run_bash(f'source "{ROOT}/scripts/lib/bin_resolve.sh"; dotf_resolve_bin pi', env)
    assert r.returncode != 0
    assert r.stdout.strip() == ""


def test_dotf_resolve_bin_active_mise_shim(tmp_home: Path) -> None:
    real_pi = _make_exec(tmp_home / ".local" / "share" / "mise" / "installs" / "node" / "24.22.1" / "bin" / "pi")
    env = _setup_mise_env(tmp_home, active_real=real_pi, with_mise=True)

    r = _run_bash(f'source "{ROOT}/scripts/lib/bin_resolve.sh"; dotf_resolve_bin pi', env)
    assert r.returncode == 0
    assert r.stdout.strip() == str(real_pi)


def test_dotf_resolve_bin_mise_shim_without_mise_cmd(tmp_home: Path) -> None:
    env = _setup_mise_env(tmp_home, active_real=None, with_mise=False)
    r = _run_bash(f'source "{ROOT}/scripts/lib/bin_resolve.sh"; dotf_resolve_bin pi', env)
    assert r.returncode != 0


def test_dotf_skip_if_bin_mise_shim(tmp_home: Path) -> None:
    stale_env = _setup_mise_env(tmp_home, active_real=None, with_mise=True)
    r_stale = _run_bash(
        f'source "{ROOT}/scripts/lib/result.sh"; '
        f'source "{ROOT}/scripts/lib/handler_common.sh"; '
        "dotf_skip_if_bin pi",
        stale_env,
    )
    assert r_stale.returncode != 0

    real_pi = _make_exec(tmp_home / ".local" / "share" / "mise" / "installs" / "node" / "24.22.1" / "bin" / "pi")
    active_env = _setup_mise_env(tmp_home, active_real=real_pi, with_mise=True)
    r_active = _run_bash(
        f'source "{ROOT}/scripts/lib/result.sh"; '
        f'source "{ROOT}/scripts/lib/handler_common.sh"; '
        "dotf_skip_if_bin pi",
        active_env,
    )
    assert r_active.returncode == 0
    assert "RESULT\tunchanged" in r_active.stdout


def test_doctor_l0_pi_stale_and_active_mise_shim(tmp_home: Path) -> None:
    stale_env = _setup_mise_env(tmp_home, active_real=None, with_mise=True)
    r_stale = subprocess.run(
        ["bash", str(ROOT / "scripts" / "lib" / "dispatch_doctor.sh"), "pi"],
        capture_output=True,
        text=True,
        env=stale_env,
        cwd=str(ROOT),
        check=False,
    )
    assert r_stale.returncode != 0
    assert "fail  install: 'pi' 命中失效 mise shim" in r_stale.stdout
    assert "RESULT\tfailed" in r_stale.stdout

    real_pi = _make_exec(tmp_home / ".local" / "share" / "mise" / "installs" / "node" / "24.22.1" / "bin" / "pi")
    active_env = _setup_mise_env(tmp_home, active_real=real_pi, with_mise=True)
    r_active = subprocess.run(
        ["bash", str(ROOT / "scripts" / "lib" / "dispatch_doctor.sh"), "pi"],
        capture_output=True,
        text=True,
        env=active_env,
        cwd=str(ROOT),
        check=False,
    )
    assert f"pass  install: PATH 中找到 'pi' ({real_pi})" in r_active.stdout


def test_install_pi_does_not_skip_on_stale_mise_shim(tmp_home: Path) -> None:
    env = _setup_mise_env(tmp_home, active_real=None, with_mise=True)
    tools_dir = tmp_home / "tools"
    npm_prefix = tmp_home / "npm-global"
    npm_prefix.mkdir(parents=True, exist_ok=True)
    npm_marker = tmp_home / "npm_install_called"
    _make_exec(
        tools_dir / "npm",
        (
            "#!/bin/sh\n"
            'if [ "$1" = "prefix" ] && [ "$2" = "-g" ]; then printf "%s\\n" "'
            f'{npm_prefix}"; exit 0; fi\n'
            'if [ "$1" = "install" ] && [ "$2" = "-g" ] && [ "$3" = "@earendil-works/pi-coding-agent@latest" ]; then\n'
            f'  touch "{npm_marker}"\n'
            "  exit 1\n"
            "fi\n"
            "exit 1\n"
        ),
    )

    r = _run_bash(
        f'export SCRIPT_DIR="{ROOT}"; '
        f'source "{ROOT}/scripts/modules/pi/lib.sh"; '
        "install_pi",
        env,
    )
    assert "Pi 已安装:" not in r.stdout
    assert npm_marker.exists()
