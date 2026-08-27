"""taskflow 的边界契约：零脚本、不新增 shim、旧工作流资产仍在。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "agents"
TASKFLOW = AGENTS / "skills" / "taskflow"


def _load_sync_module():
    path = ROOT / "scripts" / "agents" / "sync.py"
    spec = importlib.util.spec_from_file_location("agents_sync", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_taskflow_skill_ships_no_scripts() -> None:
    assert (TASKFLOW / "SKILL.md").is_file()
    assert not (TASKFLOW / "scripts").exists(), "taskflow 必须零脚本"


def test_sync_shims_unchanged_by_taskflow() -> None:
    assert set(_load_sync_module().SHIMS) == {"taskctl"}


def test_taskflow_skill_frontmatter() -> None:
    skill = (TASKFLOW / "SKILL.md").read_text(encoding="utf-8")
    for field in ("id: taskflow", "name: taskflow", "description:"):
        assert field in skill, f"SKILL.md frontmatter 缺字段: {field}"


def test_legacy_task_workflow_assets_survive() -> None:
    assert (AGENTS / "skills" / "task-workflow" / "SKILL.md").is_file()
