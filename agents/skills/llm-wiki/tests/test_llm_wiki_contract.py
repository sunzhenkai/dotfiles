"""llm-wiki：本地文档 wiki 的契约与边界。"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.layout = (ROOT / "references" / "layout.md").read_text(encoding="utf-8")
        cls.types = (ROOT / "references" / "page-types.md").read_text(encoding="utf-8")
        cls.ingest = (ROOT / "references" / "ingest.md").read_text(encoding="utf-8")
        cls.lint = (ROOT / "references" / "lint.md").read_text(encoding="utf-8")
        cls.organize = (ROOT / "references" / "organize.md").read_text(encoding="utf-8")

    def test_frontmatter_name_matches_directory(self) -> None:
        self.assertIn("name: llm-wiki", self.skill)
        self.assertEqual(ROOT.name, "llm-wiki")

    def test_reference_and_script_exist(self) -> None:
        for rel in (
            "references/layout.md",
            "references/page-types.md",
            "references/ingest.md",
            "references/lint.md",
            "references/organize.md",
            "scripts/lint_wiki.py",
            "agents/openai.yaml",
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_no_runtime_service_dependency(self) -> None:
        self.assertIn("不依赖 llmwiki 服务、MCP 或 SQLite", self.skill)
        self.assertIn("不启动 llmwiki 应用", self.skill)
        self.assertNotIn("Call the MCP", self.skill)
        self.assertNotIn(".llmwiki/index.db", self.skill)
        self.assertIn("不要创建 `.llmwiki/`", self.skill)

    def test_raw_is_readonly(self) -> None:
        self.assertIn("`raw/` 只读", self.skill)
        self.assertIn("不编辑 `raw/`", self.skill)

    def test_init_requires_confirm(self) -> None:
        init = self.skill.split("## `init`", 1)[1].split("## ", 1)[0]
        self.assertIn("必须先获得确认", init)
        self.assertIn("未确认则停止", init)
        self.assertIn("必须先获得确认", self.layout)
        self.assertIn("未确认则停止", self.layout)

    def test_phases_are_named(self) -> None:
        for phase in ("guide", "init", "ingest", "query", "organize", "lint"):
            self.assertIn(f"`{phase}`", self.skill)

    def test_handoff_boundaries(self) -> None:
        self.assertIn("project-spec-mirror", self.skill)
        self.assertIn("dotf-code-explore", self.skill)

    def test_privacy_gate(self) -> None:
        self.assertIn("摄入前做隐私自查", self.skill)
        self.assertIn("<REDACTED>", self.skill)
        self.assertIn("<REDACTED>", self.ingest)

    def test_log_contract(self) -> None:
        self.assertIn("## [YYYY-MM-DD] action | description", self.skill)
        self.assertIn("仅追加", self.skill)

    def test_typed_plural_directories(self) -> None:
        self.assertIn("wiki/entities/", self.layout)
        self.assertIn("应用复数目录名", self.layout)
        self.assertIn("不是 `entity/`", self.layout)

    def test_entity_concept_split(self) -> None:
        self.assertIn("概念标题保持中性", self.types)
        self.assertIn("渐进披露", self.types)

    def test_phase_loaded_on_demand(self) -> None:
        self.assertIn("只读该阶段详情", self.skill)
        self.assertIn("不要预加载其它 reference", self.skill)
        self.assertIn("references/layout.md", self.skill)
        self.assertIn("references/organize.md", self.skill)

    def test_guide_and_init_live_in_layout(self) -> None:
        self.assertIn("## `guide`", self.layout)
        self.assertIn("真实 `ls`", self.layout)
        self.assertIn("不要创建 `.llmwiki/`", self.layout)
        guide = self.skill.split("## `guide`", 1)[1].split("## ", 1)[0]
        self.assertNotIn("缺哪个就说哪个", guide)

    def test_organize_procedure_lives_in_reference(self) -> None:
        organize = self.skill.split("## `organize`", 1)[1].split("## ", 1)[0]
        self.assertNotIn("不要编造 `wiki/entity/`", organize)
        self.assertIn("不要编造 `wiki/entity/`", self.organize)
        self.assertIn("确认前不改", self.organize)


if __name__ == "__main__":
    unittest.main()
