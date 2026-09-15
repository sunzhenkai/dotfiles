"""task-explore：阶段门禁、落点与按需加载的文本契约。"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.explore = (ROOT / "references" / "phase-explore.md").read_text(
            encoding="utf-8"
        )
        cls.design = (ROOT / "references" / "phase-design.md").read_text(
            encoding="utf-8"
        )
        cls.decide = (ROOT / "references" / "phase-decide.md").read_text(
            encoding="utf-8"
        )
        cls.handoff = (ROOT / "references" / "phase-handoff.md").read_text(
            encoding="utf-8"
        )

    def test_frontmatter_name_matches_directory(self) -> None:
        self.assertIn("name: task-explore", self.skill)
        self.assertEqual(ROOT.name, "task-explore")

    def test_reference_files_exist(self) -> None:
        for rel in (
            "references/phase-explore.md",
            "references/phase-design.md",
            "references/phase-decide.md",
            "references/phase-handoff.md",
            "references/design-template.md",
            "references/task-template.md",
            "references/index-template.md",
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_missing_tasks_dir_requires_confirm(self) -> None:
        self.assertIn("必须先获得确认再创建", self.skill)
        self.assertIn("询问是否在当前位置创建 `tasks/`", self.skill)
        self.assertIn("未确认则停止", self.skill)

    def test_unbound_requires_new_or_resume(self) -> None:
        self.assertIn("应提示创建或者恢复", self.skill)
        self.assertIn("在确认后进行 new/resume 阶段", self.skill)
        self.assertIn("用户确认前不进入", self.skill)

    def test_archive_checks_dest_before_mutating_task_md(self) -> None:
        archive = self.skill.split("## `archive`", 1)[1].split("## ", 1)[0]
        dest = archive.find("目标已存在则停止")
        status = archive.find("`status` 改为 `archived`")
        move = archive.find("**移动**过去")
        self.assertGreater(dest, -1)
        self.assertGreater(status, dest)
        self.assertGreater(move, status)

    def test_index_sync_on_mutating_phases(self) -> None:
        self.assertIn(
            "`new` / `save` / `decide` / `handoff` / `archive` / `reopen` 必须同步对应行",
            self.skill,
        )

    def test_phase_loaded_on_demand(self) -> None:
        self.assertIn("只读该阶段详情", self.skill)
        self.assertIn("不要预加载其它 phase", self.skill)
        self.assertIn("references/phase-explore.md", self.skill)
        self.assertIn("references/phase-design.md", self.skill)
        self.assertIn("references/phase-decide.md", self.skill)
        self.assertIn("references/phase-handoff.md", self.skill)
        self.assertNotIn("| 方案 | 成本 |", self.skill)

    def test_explore_does_not_write_repo_glossary(self) -> None:
        self.assertIn("只委托 `grilling`", self.explore)
        self.assertIn("禁止调用 `grill-with-docs` 或 `domain-modeling`", self.explore)
        self.assertIn("禁止写仓库根 `CONTEXT.md`、`docs/adr/`", self.explore)
        self.assertNotIn("使用 `grill-with-docs` 进行", self.explore)
        explore_sec = self.skill.split("## `explore`", 1)[1].split("## ", 1)[0]
        self.assertIn("禁止调用 `grill-with-docs`", explore_sec)
        self.assertNotIn("委托 `grill-with-docs`", explore_sec)

    def test_resume_task_docs_readonly_index_repair_allowed(self) -> None:
        self.assertIn("任务文档只读", self.skill)
        self.assertIn("INDEX 漂移可重建", self.skill)
        resume = self.skill.split("## `resume`", 1)[1].split("## ", 1)[0]
        self.assertIn("任务文档只读", resume)
        self.assertIn("INDEX", resume)
        self.assertIn("reopen", resume)

    def test_two_task_kinds_are_named(self) -> None:
        self.assertIn("探索任务", self.skill)
        self.assertIn("taskflow 任务", self.skill)
        self.assertIn("`{task-name}-driver`", self.skill)

    def test_decide_is_required_before_handoff(self) -> None:
        self.assertIn("决策** 小节已写明采纳方案", self.handoff)
        self.assertIn("没有则打断，先 `decide`", self.handoff)
        handoff_sec = self.skill.split("## `handoff`", 1)[1].split("## ", 1)[0]
        self.assertIn("无决策则先 `decide`", handoff_sec)

    def test_handoff_delegates_taskflow_same_slug(self) -> None:
        self.assertIn("taskflow-new", self.handoff)
        self.assertIn("必须等于探索任务 slug", self.handoff)
        self.assertIn("不发明", self.handoff)
        self.assertIn("不要写 `tasks.md`", self.handoff)
        self.assertIn("保持探索任务在 `ongoing/`", self.handoff)
        self.assertIn("仅当 driver 已存在", self.handoff)

    def test_reopen_checks_dest_before_move(self) -> None:
        reopen = self.skill.split("## `reopen`", 1)[1].split("---", 1)[0]
        dest = reopen.find("目标已存在则停止")
        status = reopen.find("`status` 改回 `ongoing`")
        move = reopen.find("移动目录到 `ongoing/`")
        self.assertGreater(dest, -1)
        self.assertGreater(status, dest)
        self.assertGreater(move, status)


if __name__ == "__main__":
    unittest.main()
