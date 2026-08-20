#!/usr/bin/env python3
"""Contract tests for pretty-view routing and bundled references."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"
REFERENCES = ROOT / "references"


class PrettyViewContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = SKILL.read_text(encoding="utf-8")
        cls.reading_page = (REFERENCES / "html-page.md").read_text(encoding="utf-8")

    def test_reading_pages_pair_structure_and_design_references(self) -> None:
        self.assertIn("所有未命中 PPT、reveal.js、显式 md→html 的 HTML 请求", self.skill)
        self.assertIn("**reference**：`html-page`", self.skill)
        self.assertIn("**设计参考**：`frontend-design`", self.skill)
        self.assertIn(
            "Read `references/html-page.md` 与 `references/frontend-design/SKILL.md`",
            self.skill,
        )

        for retired in ("spec-to-readable-html", "html-artifact", "html-doc"):
            self.assertNotIn(retired, self.skill)

    def test_reading_reference_keeps_content_modes_and_requires_a_brief(self) -> None:
        for mode in ("`spec`", "`visual`", "`doc`", "`article`", "`review`"):
            self.assertIn(mode, self.reading_page)
        for item in ("**Subject**", "**Audience**", "**Page job**", "**Signature**"):
            self.assertIn(item, self.reading_page)
        self.assertIn("不使用固定皮肤", self.reading_page)

    def test_page_architecture_covers_single_flat_and_hierarchical(self) -> None:
        for text in (
            "**单页**（默认）",
            "**扁平多页**",
            "**层级多页**",
            "`_site.json` 是页面树、标题、顺序和父子关系的**唯一维护源**",
            "默认最多两级内容页",
            "新增、删除、移动或改名页面时",
        ):
            with self.subTest(text=text):
                self.assertIn(text, self.skill)

        for text in (
            "## 单页合同",
            "## 扁平多页合同",
            "## 层级多页合同",
            "## `_site.json`：多页唯一维护源",
            "页面文件不得游离于 `_site.json`",
        ):
            with self.subTest(text=text):
                self.assertIn(text, self.reading_page)

    def test_special_routes_remain_available(self) -> None:
        expected = {
            "html-ppt": REFERENCES / "html-ppt" / "SKILL.md",
            "html-slides": REFERENCES / "html-slides" / "SKILL.md",
            "baoyu-markdown-to-html": REFERENCES / "baoyu-markdown-to-html" / "SKILL.md",
        }
        for route, path in expected.items():
            with self.subTest(route=route):
                self.assertIn(route, self.skill)
                self.assertTrue(path.is_file(), path)

    def test_frontend_design_is_required_for_html(self) -> None:
        for text in (
            "**门 4 · HTML 必做视觉设计**",
            "进入任何 HTML 输出路径后 Read `references/frontend-design/SKILL.md`",
            "不是输出路径",
        ):
            with self.subTest(text=text):
                self.assertIn(text, self.skill)

        self.assertIn("frontend-design", self.skill)
        self.assertIn("## 视觉验收（MUST）", self.reading_page)
        self.assertIn("frontend-design", (ROOT / "README.md").read_text(encoding="utf-8"))

    def test_retired_reading_page_references_are_not_distributed(self) -> None:
        for relpath in (
            "html-doc.md",
            "html-artifact",
            "spec-to-readable-html",
        ):
            with self.subTest(relpath=relpath):
                self.assertFalse((REFERENCES / relpath).exists(), relpath)


if __name__ == "__main__":
    unittest.main()
