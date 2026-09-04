"""Status read-only behavior and strict latest-summary retry entry points."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _dotf(tmp_home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["XDG_STATE_HOME"] = str(tmp_home / ".local" / "state")
    return subprocess.run(
        ["bash", str(ROOT / "bin" / "dotf"), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )


def test_retry_no_report(tmp_home: Path) -> None:
    result = _dotf(tmp_home, "retry")
    assert result.returncode != 0
    assert "无最近执行报告" in (result.stdout + result.stderr)


def test_retry_damaged_or_incompatible_report(tmp_home: Path, tmp_state_dir: Path) -> None:
    report = tmp_state_dir / "last-run.json"
    report.write_text("{damaged", encoding="utf-8")
    report.chmod(0o600)
    damaged = _dotf(tmp_home, "retry")
    assert damaged.returncode != 0
    assert "损坏" in (damaged.stdout + damaged.stderr)

    report.write_text(json.dumps({"version": 99, "kind": "run-summary"}), encoding="utf-8")
    report.chmod(0o600)
    incompatible = _dotf(tmp_home, "retry")
    assert incompatible.returncode != 0
    assert "版本不兼容" in (incompatible.stdout + incompatible.stderr)


def test_status_help(tmp_home: Path) -> None:
    result = _dotf(tmp_home, "status", "--help")
    assert result.returncode == 0
    assert "只读" in result.stdout


def test_status_profile_minimal_remains_read_only(tmp_home: Path) -> None:
    result = _dotf(tmp_home, "status", "--profile", "minimal")
    assert "环境状态" in result.stdout
    assert "profile=minimal" in result.stdout
    state = tmp_home / ".local" / "state" / "dotf"
    assert not (state / "last-run.json").exists()
    assert not (state / "runs").exists()
