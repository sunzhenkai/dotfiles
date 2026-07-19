"""P1 profile：minimal/remote/desktop/full 与展示区分。"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_profiles_validate() -> None:
    r = subprocess.run(
        ["python3", str(ROOT / "scripts" / "modules.py"), "validate"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0, r.stderr


def test_minimal_profile_plan() -> None:
    r = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "planner.py"),
            "plan",
            "--actions",
            "install,config",
            "--profile",
            "minimal",
            "--os",
            "ubuntu",
            "--format",
            "machine",
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0, r.stderr
    assert "PLAN_OK" in r.stdout
    assert "zsh" in r.stdout
    assert "hypr" not in r.stdout


def test_full_profile_larger_than_minimal() -> None:
    def count_actions(profile: str) -> int:
        r = subprocess.run(
            [
                "python3",
                str(ROOT / "scripts" / "planner.py"),
                "plan",
                "--actions",
                "install,config",
                "--profile",
                profile,
                "--os",
                "ubuntu",
                "--format",
                "machine",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            check=True,
        )
        return sum(1 for line in r.stdout.splitlines() if line.startswith("ACTION\t"))

    assert count_actions("full") > count_actions("minimal")
    assert count_actions("remote") > count_actions("minimal")


def test_desktop_filters_darwin_only_on_linux() -> None:
    r = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "planner.py"),
            "plan",
            "--actions",
            "config",
            "--profile",
            "desktop",
            "--os",
            "ubuntu",
            "--format",
            "machine",
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0, r.stderr
    assert "iterm2" not in r.stdout
    assert "kitty" in r.stdout or "nvim" in r.stdout


def test_init_list_separates_os_and_usage(tmp_home: Path) -> None:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    r = subprocess.run(
        ["bash", str(ROOT / "bin" / "dotf"), "init", "--list"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0, r.stderr
    assert "可用 OS profile" in r.stdout
    assert "可用使用场景 profile" in r.stdout
    assert "minimal" in r.stdout
    assert "ubuntu" in r.stdout or "darwin" in r.stdout


def test_run_plan_json_summary(tmp_home: Path, tmp_path: Path) -> None:
    handlers = tmp_path / "handlers"
    (handlers / "demo").mkdir(parents=True)
    (handlers / "demo" / "install.sh").write_text(
        "#!/usr/bin/env bash\ndotf_result_changed 'ok'\n",
        encoding="utf-8",
    )
    plan = tmp_path / "plan.txt"
    plan.write_text(
        "PLAN_OK\nOS\tlinux\nPROFILE\tminimal\nACTION\t1\tinstall\tdemo\texplicit\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["DOTF_HANDLERS_DIR"] = str(handlers)
    r = subprocess.run(
        [
            "bash",
            str(ROOT / "scripts" / "run_plan.sh"),
            "--yes",
            "--json",
            "--plan-file",
            str(plan),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert '"changed": 1' in r.stdout
    assert '"module": "demo"' in r.stdout
    # 脱敏：不应出现 HOME 路径下的私密内容标记
    assert "API_KEY" not in r.stdout
