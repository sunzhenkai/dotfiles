"""P2 doctor 分层：L0 / L1 / 结果映射。"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_l0_only_deep_skips_missing_l1(tmp_home: Path) -> None:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    # starship 无 L1 doctor.sh
    r = subprocess.run(
        ["bash", str(ROOT / "scripts" / "doctor.sh"), "starship", "--deep"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    # L0 可能 fail（未配置），但 L1 应为 intentional skip
    assert "skip  L1:" in r.stdout
    assert "RESULT\t" in r.stdout


def test_doctor_map_fail_to_failed(tmp_home: Path, tmp_path: Path) -> None:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    # nvim 未配置 → L0 fail → failed
    r = subprocess.run(
        ["bash", str(ROOT / "scripts" / "doctor.sh"), "nvim"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode != 0
    assert "RESULT\tfailed" in r.stdout


def test_doctor_pass_maps_unchanged(tmp_home: Path) -> None:
    # zed：仅 config、无 bin，构造正确 symlink 后 L0 应全 pass → unchanged
    zed_src = ROOT / "config" / "editors" / "zed"
    zed_tgt = Path(os.environ["XDG_CONFIG_HOME"]) / "zed"
    if zed_tgt.exists() or zed_tgt.is_symlink():
        if zed_tgt.is_dir() and not zed_tgt.is_symlink():
            import shutil

            shutil.rmtree(zed_tgt)
        else:
            zed_tgt.unlink()
    zed_tgt.symlink_to(zed_src)

    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    r = subprocess.run(
        ["bash", str(ROOT / "scripts" / "doctor.sh"), "zed"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "RESULT\tunchanged" in r.stdout or "RESULT\tskipped" in r.stdout


def test_agents_l1_only_with_deep(tmp_home: Path) -> None:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    shallow = subprocess.run(
        ["bash", str(ROOT / "scripts" / "doctor.sh"), "agents"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert "doctor (agents) — L0" in shallow.stdout
    assert "doctor (agents) — L1" not in shallow.stdout

    deep = subprocess.run(
        ["bash", str(ROOT / "scripts" / "doctor.sh"), "agents", "--deep", "--json"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert "doctor (agents) — L1" in deep.stdout or "L1" in deep.stdout
