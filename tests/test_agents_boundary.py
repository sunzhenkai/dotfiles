"""P2 agents 边界：聚合 install 展开、单工具不隐式 sync。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "agents"))
from common import TOOLS  # noqa: E402


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
    document = json.loads(r.stdout)
    assert document["header"] == "DOTF_EXECUTION_PLAN"
    planned = {(action["action"], action["module"]) for action in document["actions"]}
    for tool in ("cursor", "kiro", "opencode", "codex", "kimi-code", "pi", "zcode"):
        assert ("install", tool) in planned
    # 已移除的 vendor 不进安装计划
    assert ("install", "claude") not in planned
    assert ("install", "qoder") not in planned
    assert ("install", "codebuddy-code") not in planned


def test_removed_vendors_not_in_tools_or_bundle() -> None:
    for removed in ("claude", "qoder", "codebuddy-code"):
        assert removed not in TOOLS
    assert "zcode" in TOOLS
    assert "kiro" in TOOLS
    bundle = (ROOT / "scripts" / "planner.py").read_text(encoding="utf-8")
    assert (
        'AGENTS_INSTALL_BUNDLE = ("cursor", "kiro", "opencode", "codex", "kimi-code", "pi", "zcode")'
        in bundle
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
    planned = {(action["action"], action["module"]) for action in json.loads(r.stdout)["actions"]}
    assert ("config", "agents") in planned
    assert ("config", "claude") not in planned
    assert ("config", "cursor") not in planned


def test_cursor_install_plan_is_solo() -> None:
    r = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "planner.py"),
            "plan",
            "--actions",
            "install",
            "--modules",
            "cursor",
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
    planned = {(action["action"], action["module"]) for action in json.loads(r.stdout)["actions"]}
    assert ("install", "cursor") in planned
    assert ("install", "kiro") not in planned
    assert ("install", "agents") not in planned


def test_single_tool_config_source_has_no_sync_call() -> None:
    text = (ROOT / "scripts" / "config.sh").read_text(encoding="utf-8")
    # install_cursor 等函数体内不应再调用 sync
    assert "sync_agents cursor" not in text
    assert "sync_agents kiro" not in text
    assert "sync_agents codex" not in text
    assert "sync_agents opencode" not in text
    assert "sync_agents kimi-code" not in text
    assert "sync_agents pi" not in text
    assert "sync_agents zcode" not in text
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


def test_sync_removed_tools_rejected(tmp_home: Path) -> None:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    for tool in ("claude", "qoder", "codebuddy-code"):
        r = subprocess.run(
            [
                "bash",
                str(ROOT / "scripts" / "agents" / "sync.sh"),
                tool,
                "--skills-only",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(ROOT),
        )
        assert r.returncode != 0
        assert "未知参数" in r.stderr


def test_skills_sync_targets_shared_agents_dir(tmp_home: Path) -> None:
    """skills 同步与 tool 无关：写共享目录、Kiro 例外镜像与 shims。"""
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    r = subprocess.run(
        [
            "bash",
            str(ROOT / "scripts" / "agents" / "sync.sh"),
            "cursor",
            "--skills-only",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
    )
    assert r.returncode == 0, r.stderr + r.stdout
    written = [line[4:] for line in r.stdout.splitlines() if line.startswith("  + ")]
    assert written, r.stdout
    for dest in written:
        assert dest.startswith(str(tmp_home / ".agents" / "skills")) or dest.startswith(
            str(tmp_home / ".local" / "bin")
        ) or dest.startswith(
            str(tmp_home / ".kiro" / "skills")
        ), dest


def test_dotf_agents_config_executes_kiro_skills_sync(tmp_home: Path) -> None:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["XDG_STATE_HOME"] = str(tmp_home / ".local" / "state")
    r = subprocess.run(
        [
            "bash",
            str(ROOT / "bin" / "dotf"),
            "agents",
            "-c",
            "--skills-only",
            "--yes",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert f"==> sync kiro skills → {tmp_home / '.kiro' / 'skills'}" in r.stdout
    assert (tmp_home / ".kiro" / "skills" / "task-design" / "SKILL.md").is_file()
