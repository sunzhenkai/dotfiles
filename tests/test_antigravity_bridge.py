"""Antigravity 桥接阶段：dotf agents -c 覆盖 ~/.gemini/config/skills.json。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "agents"))

import antigravity_bridge
import doctor


def _run(args: list[str], home: Path, *, dry_run: bool = False) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["XDG_STATE_HOME"] = str(home / ".local" / "state")
    env["PYTHONPATH"] = str(ROOT / "src")
    cmd = [sys.executable, str(ROOT / "src" / "agents" / "antigravity_bridge.py"), "--root", str(ROOT)]
    cmd += ["--home", str(home)]
    if dry_run:
        cmd.append("--dry-run")
    return subprocess.run(cmd, capture_output=True, text=True, env=env, check=False, cwd=str(ROOT))


def _antigravity_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    (home / ".gemini" / "antigravity").mkdir(parents=True)
    return home


def test_stage_skips_when_antigravity_is_absent(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    result = _run([], home)
    assert result.returncode == 0, result.stderr
    assert "未检测到 Antigravity" in result.stdout
    assert not (home / ".gemini").exists()


def test_stage_deploys_bridge_and_is_idempotent(tmp_path: Path) -> None:
    home = _antigravity_home(tmp_path)
    first = _run([], home)
    assert first.returncode == 0, first.stderr
    bridge = home / ".gemini" / "config" / "skills.json"
    assert bridge.is_file() and not bridge.is_symlink()
    assert json.loads(bridge.read_text(encoding="utf-8")) == {
        "entries": [{"path": str(home / ".agents" / "skills")}]
    }
    assert bridge.stat().st_mode & 0o777 == 0o644

    second = _run([], home)
    assert second.returncode == 0, second.stderr
    assert "changed=0" in second.stdout


def test_stage_never_emits_a_tilde_path(tmp_path: Path) -> None:
    """hub server 2.34.0 拒绝 `~/`：桥接里只能是展开后的绝对路径。"""
    home = _antigravity_home(tmp_path)
    assert _run([], home).returncode == 0
    text = (home / ".gemini" / "config" / "skills.json").read_text(encoding="utf-8")
    assert "~/" not in text
    assert str(home / ".agents" / "skills") in text


def test_stage_dry_run_writes_nothing(tmp_path: Path) -> None:
    home = _antigravity_home(tmp_path)
    result = _run([], home, dry_run=True)
    assert result.returncode == 0, result.stderr
    assert "changed=1" in result.stdout
    assert not (home / ".gemini" / "config" / "skills.json").exists()


def test_stage_takes_over_existing_bridge_file(tmp_path: Path) -> None:
    home = _antigravity_home(tmp_path)
    bridge = home / ".gemini" / "config" / "skills.json"
    bridge.parent.mkdir(parents=True)
    bridge.write_text('{"entries": []}\n', encoding="utf-8")

    result = _run([], home)
    assert result.returncode == 0, result.stderr
    assert json.loads(bridge.read_text(encoding="utf-8")) == {
        "entries": [{"path": str(home / ".agents" / "skills")}]
    }


def test_detected_follows_install_dir_and_existing_bridge(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    assert not antigravity_bridge.detected(home)
    (home / ".gemini" / "config").mkdir(parents=True)
    (home / ".gemini" / "config" / "skills.json").write_text("{}", encoding="utf-8")
    assert antigravity_bridge.detected(home)


def test_doctor_points_at_the_aggregate_sync(tmp_path: Path) -> None:
    home = _antigravity_home(tmp_path)
    report = doctor.DoctorReport("research", None, "low")
    doctor.check_antigravity_skills_bridge(report, home=home)
    item = next(i for i in report.items if i.id == "antigravity-bridge")
    assert item.status == doctor.STATUS_WARN
    assert "dotf agents -c" in item.hint
