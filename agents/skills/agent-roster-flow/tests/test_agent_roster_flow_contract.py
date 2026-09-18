"""agent-roster-flow：脊柱、Decision Surface 与按需加载的文本契约。"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.tracks = (ROOT / "references" / "tracks.md").read_text(encoding="utf-8")
        cls.stages = (ROOT / "references" / "stages.md").read_text(encoding="utf-8")
        cls.spine = (ROOT / "references" / "spine.md").read_text(encoding="utf-8")

    def test_frontmatter_name_matches_directory(self) -> None:
        self.assertIn("name: agent-roster-flow", self.skill)
        self.assertEqual(ROOT.name, "agent-roster-flow")

    def test_reference_files_exist(self) -> None:
        for rel in (
            "CONTEXT.md",
            "references/tracks.md",
            "references/stages.md",
            "references/spine.md",
            "references/models-yaml.md",
            "scripts/list_assignments.py",
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_loads_references_on_demand(self) -> None:
        self.assertIn("不要预加载其它 Stage", self.skill)
        self.assertIn("确认 Track 之后读", self.skill)
        self.assertNotIn("| Simple | Medium | Complex |", self.skill)

    def test_decisions_stay_on_surface(self) -> None:
        self.assertIn("Decision Surface", self.skill)
        self.assertIn("受派 prompt 只含 Frozen Input", self.skill)
        self.assertIn("不再提问", self.skill)

    def test_does_not_call_acpx_directly(self) -> None:
        self.assertIn("不直接调用 `acpx`", self.skill)
        self.assertIn("委托 `$agent-roster`", self.skill)
        self.assertIn("契约没有 `model` 字段就停下报告", self.skill)

    def test_assignment_comes_from_script(self) -> None:
        self.assertIn("list_assignments.py", self.skill)
        self.assertIn("未收到选择不得发出 Delegation", self.skill)

    def test_code_review_is_optional_and_bound(self) -> None:
        self.assertIn("问是否做代码评审", self.skill)
        self.assertIn("Simple 默认跳过", self.skill)
        self.assertIn("$dotf-code-review", self.stages)
        self.assertIn("不允许 `human`", self.stages)

    def test_complex_explore_does_not_call_grill_with_docs(self) -> None:
        self.assertIn("不调用 `grill-with-docs`", self.tracks)
        self.assertIn("`$task-explore`", self.tracks)

    def test_human_only_on_plan_review_and_wrap_up(self) -> None:
        self.assertIn("方案评审与收尾", self.skill)
        self.assertIn("默认推荐 `human`", self.tracks)
        implement = self.stages.split("## 实现", 1)[1].split("## ", 1)[0]
        self.assertIn("不允许 `human`", implement)

    def test_code_review_allows_dirty_tree(self) -> None:
        self.assertIn("允许脏工作树", self.skill)
        self.assertIn("Stage 级例外", self.skill)

    def test_spine_stays_in_cache(self) -> None:
        self.assertIn("~/.cache/agent-roster/flows/", self.skill)
        self.assertIn("不进 git", self.spine)
        self.assertIn("orchestrator/<kind>", self.spine)
