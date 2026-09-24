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
        cls.archive = (ROOT / "references" / "phase-archive.md").read_text(
            encoding="utf-8"
        )
        cls.reopen = (ROOT / "references" / "phase-reopen.md").read_text(
            encoding="utf-8"
        )
        cls.ledger = (
            ROOT / "references" / "ledger-write-discipline.md"
        ).read_text(encoding="utf-8")

    @staticmethod
    def _section(text: str, head: str) -> str:
        return text.split(head, 1)[1].split("## ", 1)[0]

    def test_frontmatter_name_matches_directory(self) -> None:
        self.assertIn("name: task-explore", self.skill)
        self.assertEqual(ROOT.name, "task-explore")

    def test_reference_files_exist(self) -> None:
        for rel in (
            "references/phase-explore.md",
            "references/phase-design.md",
            "references/phase-decide.md",
            "references/phase-handoff.md",
            "references/phase-archive.md",
            "references/phase-reopen.md",
            "references/design-template.md",
            "references/task-template.md",
            "references/index-template.md",
            "references/ledger-write-discipline.md",
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
        dest = self.archive.find("目标已存在则停止")
        save = self.archive.find("目标路径确认无冲突后")
        status = self.archive.find("`status` 改为 `archived`")
        move = self.archive.find("**移动**过去")
        self.assertGreater(dest, -1)
        self.assertGreater(save, dest)
        self.assertGreater(status, save)
        self.assertGreater(move, status)

    def test_archive_gate_keeps_zero_side_effects_on_conflict(self) -> None:
        section = self._section(self.skill, "## `archive`")
        self.assertIn("目标已存在则停止并询问，禁止覆盖", section)
        self.assertIn("不得改 `TASK.md`、不得移动目录、不得改 INDEX", section)
        self.assertIn("未结子任务", section)

    def test_archive_requires_closing_reason(self) -> None:
        self.assertIn("留下本次结论与关闭原因", self.skill)
        self.assertIn("关闭原因", self.archive)
        self.assertIn("本次结论", self.archive)
        self.assertIn("取自用户回答", self.archive)
        tpl = (ROOT / "references" / "task-template.md").read_text(encoding="utf-8")
        self.assertIn("**归档** 小节", tpl)
        self.assertIn("本次结论", tpl)
        self.assertIn("SUMMARY.md", tpl)

    def test_archive_counts_open_items_without_forcing_clearance(self) -> None:
        section = self._section(self.skill, "## `archive`")
        self.assertIn("未决问题", section)
        self.assertIn("不要求清零", self.archive)
        self.assertIn("随归档关闭", self.archive)

    def test_archive_reads_driver_progress_without_writeback(self) -> None:
        self.assertIn("已完成 X/Y", self.archive)
        self.assertIn("进度未知", self.archive)
        self.assertIn("**不回写**", self.archive)

    def test_archive_checks_inbound_links(self) -> None:
        self.assertIn("旧路径的链接", self.archive)
        self.assertIn("保留断链", self.archive)

    def test_archive_updates_index_wording(self) -> None:
        self.assertIn("保留 `→ {task-name}-driver` 结尾", self.archive)
        self.assertIn("不留「设计中」这类进行时", self.archive)

    def test_archive_writes_human_summary(self) -> None:
        self.assertIn("## 任务总结（`{taskRoot}/SUMMARY.md`）", self.archive)
        self.assertIn("主干是时间线", self.archive)
        self.assertIn("不超过约 40 行", self.archive)
        self.assertIn("交付进度未记录", self.archive)
        self.assertIn("给用户过一眼", self.archive)
        self.assertIn("`{taskRoot}/SUMMARY.md`（给人读的时间线总结）", self.skill)
        self.assertIn("│   ├── SUMMARY.md", self.skill)

    def test_archive_summary_written_after_dest_check(self) -> None:
        dest = self.archive.find("目标已存在则停止")
        summary = self.archive.find("给用户过眼后继续")
        move = self.archive.find("**移动**过去")
        self.assertGreater(summary, dest)
        self.assertGreater(move, summary)

    def test_archive_requires_save_before_move(self) -> None:
        self.assertIn("必须按 `save` 写回", self.archive)
        self.assertIn("不接受按现状归档", self.archive)
        self.assertIn("必须先按 `save` 落盘", self._section(self.skill, "## `archive`"))

    def test_batch_archive_reuses_full_gates(self) -> None:
        self.assertIn("逐个跑完整门禁", self.archive)
        self.assertIn("合并成一次确认", self.archive)
        self.assertIn("已搬的不回滚", self.archive)
        self.assertNotIn("不在本阶段范围", self.archive)

    def test_archive_single_confirmation_for_multiple_gates(self) -> None:
        self.assertIn("合并成一次确认", self.archive)
        self.assertIn("「确认关闭」的明确答复才搬", self.archive)
        skill_sec = self._section(self.skill, "## `archive`")
        self.assertIn("合并成一次确认", skill_sec)
        self.assertIn("未确认不搬", skill_sec)

    def test_archive_verifies_move_afterwards(self) -> None:
        self.assertIn("旧路径已不存在", self.archive)
        self.assertIn("`TASK.md` 与 `SUMMARY.md` 可读", self.archive)
        self.assertIn("INDEX 每条归档路径都实际存在", self.archive)

    def test_archive_date_is_consistent(self) -> None:
        self.assertIn("三处日期必须同一个 `{yyyy-mm-dd}`", self.archive)
        self.assertIn("三处", self._section(self.skill, "## `archive`"))

    def test_index_sync_on_mutating_phases(self) -> None:
        self.assertIn(
            "`new` / `split` / `save` / `decide` / `handoff` / `archive` / `reopen` 必须同步对应行",
            self.skill,
        )

    def test_phase_loaded_on_demand(self) -> None:
        self.assertIn("只读该阶段详情", self.skill)
        self.assertIn("不要预加载其它 phase", self.skill)
        self.assertIn("references/phase-explore.md", self.skill)
        self.assertIn("references/phase-design.md", self.skill)
        self.assertIn("references/phase-decide.md", self.skill)
        self.assertIn("references/phase-handoff.md", self.skill)
        self.assertIn("references/phase-archive.md", self.skill)
        self.assertIn("references/phase-reopen.md", self.skill)
        self.assertNotIn("| 方案 | 成本 |", self.skill)

    def test_explore_does_not_write_repo_glossary(self) -> None:
        self.assertIn("只委托 `grilling`", self.explore)
        self.assertIn("禁止调用 `grill-with-docs` 或 `domain-modeling`", self.explore)
        self.assertIn("禁止写仓库根 `CONTEXT.md`、`docs/adr/`", self.explore)
        self.assertNotIn("使用 `grill-with-docs` 进行", self.explore)
        explore_sec = self._section(self.skill, "## `explore`")
        self.assertIn("禁止调用 `grill-with-docs`", explore_sec)
        self.assertNotIn("委托 `grill-with-docs`", explore_sec)

    def test_resume_task_docs_readonly_index_repair_allowed(self) -> None:
        self.assertIn("任务文档只读", self.skill)
        self.assertIn("INDEX 漂移可重建", self.skill)
        resume = self._section(self.skill, "## `resume`")
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
        handoff_sec = self._section(self.skill, "## `handoff`")
        self.assertIn("已 `decide` 未交接", handoff_sec)

    def test_handoff_delegates_taskflow_same_slug(self) -> None:
        self.assertIn("taskflow-new", self.handoff)
        self.assertIn("driver change 名 = 任务 slug + `-driver`", self.handoff)
        self.assertIn("不发明", self.handoff)
        self.assertIn("不要写 `tasks.md`", self.handoff)
        self.assertIn("保持探索任务在 `ongoing/`", self.handoff)
        self.assertIn("已存在则不要新建", self.handoff)

    def test_handoff_does_not_archive(self) -> None:
        handoff_sec = self._section(self.skill, "## `handoff`")
        self.assertIn("不归档、不搬目录、不清绑定", handoff_sec)
        self.assertIn("不归档、不搬目录、不清绑定", self.handoff)

    def test_reopen_checks_dest_before_move(self) -> None:
        dest = self.reopen.find("目标已存在则停止")
        status = self.reopen.find("`status` 改回 `ongoing`")
        move = self.reopen.find("**移动**回 `tasks/ongoing/{task-name}`")
        self.assertGreater(dest, -1)
        self.assertGreater(status, dest)
        self.assertGreater(move, status)

    def test_reopen_gate_zero_side_effects_on_conflict(self) -> None:
        section = self._section(self.skill, "## `reopen`")
        self.assertIn("禁止覆盖", section)
        self.assertIn("不得改 `TASK.md`、不得移动目录、不得改 INDEX", section)
        self.assertIn("「确认 reopen」的明确答复", section)

    def test_reopen_preserves_history_and_driver(self) -> None:
        self.assertIn("保留 `archived: YYYY-MM-DD` 作为历史", self.reopen)
        self.assertIn("加 `reopened: YYYY-MM-DD`", self.reopen)
        self.assertIn("一律不删不改写", self.reopen)
        self.assertIn("driver 及其 change 不删", self.reopen)

    def test_reopen_clears_handoff_tailnote_in_index(self) -> None:
        self.assertIn("去掉 `→ {task-name}-driver` 尾注", self.reopen)
        self.assertIn("去掉 `→ {task-name}-driver` 尾注", self._section(self.skill, "## `reopen`"))  # noqa: E501

    def test_reopen_checks_subtask_name_collision(self) -> None:
        self.assertIn("**子任务名撞车**", self.reopen)
        self.assertIn("`{sub}-driver` 会撞", self.reopen)

    def test_reopen_reports_driver_side_without_assuming(self) -> None:
        self.assertIn("以 `TASK.md` 的 `status` 为准", self.reopen)
        self.assertIn("进度未知", self.reopen)

    def test_reopen_keeps_summary_as_history(self) -> None:
        self.assertIn("`SUMMARY.md` 随树搬回", self.reopen)
        self.assertIn("不改写", self.reopen)
        tpl = (ROOT / "references" / "task-template.md").read_text(encoding="utf-8")
        self.assertIn("reopened: YYYY-MM-DD", tpl)

    def test_split_phase_is_routed_and_gated(self) -> None:
        self.assertIn("## `split`", self.skill)
        split = self._section(self.skill, "## `split`")
        self.assertIn("必须已绑定", split)
        self.assertIn("全局唯一", split)
        self.assertIn("只一层", split)
        self.assertIn("`parent:`", split)

    def test_subtask_terms_are_named(self) -> None:
        self.assertIn("**子任务**", self.skill)
        self.assertIn("**父任务**", self.skill)
        self.assertIn("**handed-off**", self.skill)
        self.assertIn("子 change", self.skill)

    def test_parent_forbidden_handoff(self) -> None:
        handoff_sec = self._section(self.skill, "## `handoff`")
        self.assertIn("父是纯伞不可交接", handoff_sec)
        self.assertIn("不建 `{parent}-driver`", handoff_sec)
        self.assertIn("不得建 `{parent}-driver`", self.handoff)

    def test_parent_archive_closes_whole_tree(self) -> None:
        self.assertIn("未结子任务", self._section(self.skill, "## `archive`"))
        self.assertIn("含子任务树", self.archive)
        self.assertIn("父任务归档即关闭整棵子任务树", self.archive)
        reopen = self._section(self.skill, "## `reopen`")
        self.assertIn("不自动复活", reopen)

    def test_nested_layout_and_index_rows(self) -> None:
        self.assertIn("`{parent}/{sub}`", self.skill)
        tpl = (ROOT / "references" / "task-template.md").read_text(encoding="utf-8")
        self.assertIn("parent:", tpl)
        index = (ROOT / "references" / "index-template.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("{parent}/{sub}", index)

    def test_explore_hints_split_once(self) -> None:
        self.assertIn("提示一次", self.explore)
        self.assertIn("`split`", self.explore)

    def test_ledger_write_discipline_is_gated(self) -> None:
        self.assertIn("references/ledger-write-discipline.md", self.skill)
        self.assertIn("写台账", self.skill)
        for phrase in (
            "锚点串",
            "恰为 1",
            "整行替换",
            "列数与表头一致",
            "精确整行等值",
            "最大编号",
            "不静默改写",
        ):
            self.assertIn(phrase, self.ledger)

    def test_ledger_discipline_carves_out_batch_path_update(self) -> None:
        self.assertIn("父路径前缀", self.ledger)
        self.assertIn("phase-archive.md", self.ledger)
        self.assertIn("phase-reopen.md", self.ledger)

    def test_goal_confirmations_go_to_review(self) -> None:
        section = self._section(self.skill, "## Goal 里的确认")
        self.assertIn("走 task-wizard 的「审阅」", section)
        self.assertIn("不列选项", section)
        self.assertIn("不在 goal 里时，下面的确认规则不变", section)
        self.assertIn("不交给审阅放行", section)
        self.assertIn("处在 goal 里时不逐条问用户", self.skill)
        self.assertIn("## Goal 里", self.decide)
        self.assertIn("全部按默认冻结", self.decide)
        self.assertIn("不在 goal 里时执行本节", self.decide)
        self.assertIn("逐条请用户确认", self.decide)
        self.assertIn("处在 goal 里时，不询问是否交接", self.handoff)


if __name__ == "__main__":
    unittest.main()
