"""P3 status / 执行报告 / retry。"""

from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_report_save_privacy_and_perms(tmp_home: Path, tmp_state_dir: Path) -> None:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    script = f"""
set -euo pipefail
source "{ROOT}/scripts/lib/report.sh"
export HOME="{tmp_home}"
export XDG_STATE_HOME="{tmp_home}/.local/state"
dotf_report_save linux minimal \\
  $'RESULT\\tfailed\\tdemo\\tinstall\\t10\\t1\\tAPI_KEY=supersecret and more' \\
  $'RESULT\\tchanged\\tok\\tconfig\\t5\\t0\\tok'
"""
    r = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0, r.stderr
    path = Path(r.stdout.strip().splitlines()[-1])
    assert path.is_file()
    mode = path.stat().st_mode & 0o777
    assert mode == 0o600
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["version"] == 1
    reasons = [a["reason"] for a in doc["actions"]]
    assert "supersecret" not in json.dumps(doc)
    assert any(r == "redacted" for r in reasons)


def test_retry_no_report(tmp_home: Path) -> None:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["XDG_STATE_HOME"] = str(tmp_home / ".local" / "state")
    r = subprocess.run(
        ["bash", str(ROOT / "bin" / "dotf"), "retry"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode != 0
    assert "无最近执行报告" in (r.stdout + r.stderr)


def test_retry_no_failed(tmp_home: Path, tmp_state_dir: Path) -> None:
    report = tmp_state_dir / "last-run.json"
    report.write_text(
        json.dumps(
            {
                "version": 1,
                "os": "linux",
                "profile": None,
                "actions": [
                    {
                        "status": "changed",
                        "module": "zed",
                        "action": "config",
                        "duration_ms": 1,
                        "exit_code": 0,
                        "reason": "ok",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    r = subprocess.run(
        ["bash", str(ROOT / "bin" / "dotf"), "retry"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode != 0
    assert "没有 failed" in (r.stdout + r.stderr)


def test_retry_version_incompatible(tmp_home: Path, tmp_state_dir: Path) -> None:
    report = tmp_state_dir / "last-run.json"
    report.write_text(json.dumps({"version": 99, "actions": []}), encoding="utf-8")
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    r = subprocess.run(
        ["bash", str(ROOT / "bin" / "dotf"), "retry"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode != 0
    assert "版本不兼容" in (r.stdout + r.stderr)


def test_retry_plan_dep_failure(tmp_path: Path) -> None:
    report = tmp_path / "r.json"
    report.write_text(
        json.dumps(
            {
                "version": 1,
                "os": "ubuntu",
                "actions": [
                    {
                        "status": "failed",
                        "module": "grepom",
                        "action": "install",
                        "duration_ms": 1,
                        "exit_code": 1,
                        "reason": "x",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    # 伪造未知依赖：改用未知模块
    report.write_text(
        json.dumps(
            {
                "version": 1,
                "os": "ubuntu",
                "actions": [
                    {
                        "status": "failed",
                        "module": "no-such-module-xyz",
                        "action": "install",
                        "duration_ms": 1,
                        "exit_code": 1,
                        "reason": "x",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "plan.txt"
    r = subprocess.run(
        ["python3", str(ROOT / "scripts" / "retry_plan.py"), str(report), str(out)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode != 0
    assert "未知模块" in r.stderr


def test_status_help(tmp_home: Path) -> None:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    r = subprocess.run(
        ["bash", str(ROOT / "bin" / "dotf"), "status", "--help"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0
    assert "只读" in r.stdout


def test_status_profile_minimal_dryish(tmp_home: Path) -> None:
    """status 使用 minimal + doctor；不写报告（STATUS_MODE）。"""
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["XDG_STATE_HOME"] = str(tmp_home / ".local" / "state")
    r = subprocess.run(
        ["bash", str(ROOT / "bin" / "dotf"), "status", "--profile", "minimal"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    # 多数 L0 会 fail，但命令应跑完并保持只读语义
    assert "环境状态" in r.stdout
    assert "profile=minimal" in r.stdout
    report = Path(env["XDG_STATE_HOME"]) / "dotf" / "last-run.json"
    assert not report.exists()
