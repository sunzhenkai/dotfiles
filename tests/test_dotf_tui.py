"""TUI 入口与计划构造：非 TTY、无参数帮助、与 CLI 计划一致。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from conftest import ROOT, run_dotf

SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from dotf_tui.catalog import Selectable, list_agent_selectables, list_module_selectables  # noqa: E402
from dotf_tui.plan_request import planner_argv  # noqa: E402


def test_tui_catalog_hides_uninstall_and_openspec(tmp_home: Path) -> None:
    modules = list_module_selectables("linux")
    nvim_actions = {item.action for item in modules if item.selector == "nvim"}
    grepom_actions = {item.action for item in modules if item.selector == "grepom"}
    assert "uninstall" not in nvim_actions
    assert "deconfig" in nvim_actions
    assert "uninstall" in grepom_actions
    assert "update" not in {item.action for item in modules}
    agents = list_agent_selectables(ROOT, home=tmp_home)
    assert all(not item.selector.endswith("openspec-apply-change") for item in agents)
    assert any(item.selector == "skill:grill-with-docs" for item in agents)
    assert any(item.selector.startswith("mcp:cursor/") for item in agents)


def test_dotf_without_args_is_help(tmp_home: Path) -> None:
    result = run_dotf()
    assert result.returncode == 0
    assert "用法" in result.stdout
    assert "tui" in result.stdout
    assert "Textual" not in result.stdout.lower() or "tui" in result.stdout


def test_tui_without_tty_fails(tmp_home: Path) -> None:
    result = run_dotf("tui")
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "TTY" in combined
    assert "CLI" in combined


def test_tui_mixed_with_install_fails(tmp_home: Path) -> None:
    result = run_dotf("tui", "-i")
    assert result.returncode != 0
    assert "独立命令" in result.stdout + result.stderr


def test_tui_and_cli_deconfig_plans_match(tmp_home: Path) -> None:
    items = [Selectable("nvim / deconfig", "deconfig", "nvim", "modules")]
    argv = planner_argv(items)
    tui_plan = subprocess.run(
        ["python3", str(SCRIPTS / "planner.py"), *argv],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    cli_plan = subprocess.run(
        [
            "python3",
            str(SCRIPTS / "planner.py"),
            "plan",
            "--actions",
            "deconfig",
            "--modules",
            "nvim",
            "--format",
            "machine",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    left = json.loads(tui_plan.stdout)
    right = json.loads(cli_plan.stdout)
    assert [(item["module"], item["action"]) for item in left["actions"]] == [
        (item["module"], item["action"]) for item in right["actions"]
    ]
    assert left["plan_digest"] == right["plan_digest"]


def test_mcp_remove_requires_tool_or_all_tools(tmp_home: Path) -> None:
    result = run_dotf("agents", "mcp", "remove", "web-reader", "--yes")
    assert result.returncode != 0
    assert "--tool" in result.stdout + result.stderr


def test_skill_apply_dry_run_builds_plan(tmp_home: Path) -> None:
    result = run_dotf("agents", "skill", "apply", "grill-with-docs", "--dry-run")
    assert result.returncode == 0, result.stderr
    assert "skill.apply" in result.stdout
    leftover = list((tmp_home / ".config").rglob("*.yaml"))
    assert leftover == []


def test_help_lists_reverse_actions_and_tui(tmp_home: Path) -> None:
    result = run_dotf("-h")
    assert result.returncode == 0
    out = result.stdout
    assert "--uninstall" in out
    assert "--deconfig" in out
    assert "dotf tui" in out
    assert "skill apply" in out
