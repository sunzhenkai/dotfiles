"""Antigravity 模块：skills.json 桥接配置部署、权限与 doctor 诊断。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from dotf_core import registry as modules

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "agents"))


def test_antigravity_registry_metadata_is_readonly_single_file() -> None:
    mod = modules.find_module(modules.load_registry(), "antigravity")
    assert mod is not None
    assert mod["bin"] == "agy"
    assert mod["install"] is True
    assert mod["doctor"] is True
    cfg = mod["config"]
    assert cfg["source"] == "agents/vendors/antigravity/skills.json"
    assert cfg["target"] == "~/.gemini/config/skills.json"
    assert cfg["strategy"] == "render"
    assert cfg["writable"] is False
    assert cfg["sensitive"] is False
    assert cfg["target_mode"] == "0644"


def test_antigravity_config_deploys_skills_bridge_without_touching_runtime_dirs(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    cfg_dir = home / ".gemini" / "config"
    (cfg_dir / "plugins").mkdir(parents=True)
    (cfg_dir / "plugins" / "installed.json").write_text("{}", encoding="utf-8")

    env = os.environ.copy()
    env["HOME"] = str(home)
    env["XDG_STATE_HOME"] = str(home / ".local" / "state")
    env["PYTHONPATH"] = str(ROOT / "src")

    res = subprocess.run(
        [
            sys.executable,
            "-m",
            "dotf_core.config_handler",
            "antigravity",
            "--repo-root",
            str(ROOT),
            "--home",
            str(home),
            "--state-home",
            str(home / ".local" / "state"),
            "--run-id",
            "test-antigravity-01",
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
        check=False,
    )
    assert res.returncode == 0, res.stderr + res.stdout
    target = cfg_dir / "skills.json"
    assert target.is_file() and not target.is_symlink()
    payload = json.loads(target.read_text(encoding="utf-8"))
    # hub server 2.34.0 不展开 `~/`，桥接必须是绝对路径
    assert payload == {"entries": [{"path": str(home / ".agents" / "skills")}]}
    assert target.stat().st_mode & 0o777 == 0o644
    # 运行时兄弟目录原样保留
    assert (cfg_dir / "plugins" / "installed.json").read_text(encoding="utf-8") == "{}"


def test_doctor_checks_antigravity_skills_bridge(tmp_path: Path) -> None:
    import doctor

    home = tmp_path / "home"
    (home / ".gemini" / "antigravity").mkdir(parents=True)

    # 1. 检测到 .gemini/antigravity 但缺 skills.json → warn
    report1 = doctor.DoctorReport("research", None, "low")
    doctor.check_antigravity_skills_bridge(report1, home=home)
    item1 = next(i for i in report1.items if i.id == "antigravity-bridge")
    assert item1.status == doctor.STATUS_WARN
    assert "dotf agents -c" in item1.hint

    # 2. 写入正确 skills.json（已按 HOME 展开）→ pass
    cfg_dir = home / ".gemini" / "config"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "skills.json").write_text(
        json.dumps({"entries": [{"path": str(home / ".agents" / "skills")}]}),
        encoding="utf-8",
    )
    report2 = doctor.DoctorReport("research", None, "low")
    doctor.check_antigravity_skills_bridge(report2, home=home)
    item2 = next(i for i in report2.items if i.id == "antigravity-bridge")
    assert item2.status == doctor.STATUS_PASS

    # 2b. 残留未展开的占位符 → warn（hub server 不认）
    (cfg_dir / "skills.json").write_text(
        (ROOT / "agents" / "vendors" / "antigravity" / "skills.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    report2b = doctor.DoctorReport("research", None, "low")
    doctor.check_antigravity_skills_bridge(report2b, home=home)
    item2b = next(i for i in report2b.items if i.id == "antigravity-bridge")
    assert item2b.status == doctor.STATUS_WARN

    # 3. 损坏 JSON → fail
    (cfg_dir / "skills.json").write_text("{bad json", encoding="utf-8")
    report3 = doctor.DoctorReport("research", None, "low")
    doctor.check_antigravity_skills_bridge(report3, home=home)
    item3 = next(i for i in report3.items if i.id == "antigravity-bridge")
    assert item3.status == doctor.STATUS_FAIL
