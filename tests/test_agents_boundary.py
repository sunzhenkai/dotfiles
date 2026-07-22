"""P2 agents 边界：聚合 install 展开、单工具不隐式 sync。"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_agents_install_plan_expands_tools() -> None:
    r = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "planner.py"),
            "plan",
            "--actions",
            "install",
            "--modules",
            "agents",
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
    assert r.returncode == 0, r.stderr + r.stdout
    assert "PLAN_OK" in r.stdout
    for tool in ("claude", "cursor", "opencode", "codex", "kimi-code", "pi"):
        assert f"install\t{tool}" in r.stdout.replace(" ", "\t") or (
            f"\tinstall\t{tool}\t" in r.stdout
        )


def test_agents_config_plan_does_not_pull_tool_configs() -> None:
    r = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "planner.py"),
            "plan",
            "--actions",
            "config",
            "--modules",
            "agents",
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
    assert r.returncode == 0, r.stdout
    assert "\tconfig\tagents\t" in r.stdout
    assert "\tconfig\tclaude\t" not in r.stdout
    assert "\tconfig\tcursor\t" not in r.stdout


def test_claude_install_plan_is_solo() -> None:
    r = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "planner.py"),
            "plan",
            "--actions",
            "install",
            "--modules",
            "claude",
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
    assert r.returncode == 0, r.stdout
    assert "\tinstall\tclaude\t" in r.stdout
    assert "\tinstall\tcursor\t" not in r.stdout
    assert "\tinstall\tagents\t" not in r.stdout


def test_single_tool_config_source_has_no_sync_call() -> None:
    text = (ROOT / "scripts" / "config.sh").read_text(encoding="utf-8")
    # install_claude / install_cursor 等函数体内不应再调用 sync
    assert "sync_agents cursor" not in text
    assert "sync_agents codex" not in text
    assert "sync_agents opencode" not in text
    assert "sync_agents kimi-code" not in text
    assert "sync_agents pi" not in text
    assert 'sync.sh" claude' not in text
    # 聚合入口仍保留
    assert "sync_agents all" in text or "sync_agents()" in text


def test_sync_tool_filter_dry_run_idempotent(tmp_home: Path) -> None:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    cmd = [
        "bash",
        str(ROOT / "scripts" / "agents" / "sync.sh"),
        "cursor",
        "--skills-only",
        "--dry-run",
    ]
    r1 = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(ROOT))
    r2 = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(ROOT))
    assert r1.returncode == 0, r1.stderr
    assert r2.returncode == 0, r2.stderr
    assert "tool=cursor" in r1.stdout
    assert r1.stdout == r2.stdout
