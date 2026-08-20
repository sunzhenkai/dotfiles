#!/usr/bin/env python3
"""Contract tests for pretty-view-html routing and bundled references."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"
REFERENCES = ROOT / "references"


class PrettyViewHtmlContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = SKILL.read_text(encoding="utf-8")
        cls.reading_page = (REFERENCES / "html-page.md").read_text(encoding="utf-8")

    def test_reading_pages_pair_structure_and_design_references(self) -> None:
        self.assertIn(
            "只 Read `references/html-page.md` 与 `references/frontend-design/SKILL.md`",
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
        self.assertIn("装饰性侧栏、刻度尺或图例不能代替导航", self.reading_page)
        self.assertIn("## 阅读宽度", self.reading_page)
        self.assertIn("max-width: 68ch", self.reading_page)
        self.assertIn("max-width: min(100%, 110ch)", self.reading_page)
        self.assertIn("宽内容区", self.reading_page)
        self.assertIn("时间演进用时间线或步骤", self.reading_page)
        self.assertIn("不依赖颜色单独传达信息", self.reading_page)
        self.assertIn("禁止用 `max-width: none`", self.reading_page)
        self.assertIn("不预设冷暖色系", self.reading_page)
        self.assertIn("不预设冷暖色系", self.skill)
        self.assertNotIn("暖色优先", self.reading_page)
        self.assertNotIn("配色优先考虑暖色系", self.skill)
        self.assertNotIn("pretty-view-width", self.reading_page)
        self.assertNotIn("data-measure", self.reading_page)
        self.assertIn("连续正文保持可读行宽", self.skill)
        self.assertNotIn("pretty-view-width", self.skill)

    def test_core_rules_and_collapsible_toc_are_explicit(self) -> None:
        self.assertIn("## 七条核心规则", self.reading_page)
        for rule in (
            "**结构真实**",
            "**内容决定形式**",
            "**机制最少**",
            "**清单统一**",
            "**阅读优先**",
            "**本地优先、渐进增强**",
            "**可访问、可验证**",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, self.reading_page)

        self.assertIn("## 页内目录合同", self.reading_page)
        for text in (
            '<nav aria-label="本页目录">',
            "默认收录 H2",
            "必须支持视觉隐藏",
            "不得继续占据原栏宽",
            "<details>",
            "<summary>",
            ":has()",
            "aria-expanded",
            'aria-current="location"',
            "视觉层级低于标题和正文",
            "打印时展开目录内容",
        ):
            with self.subTest(text=text):
                self.assertIn(text, self.reading_page)
        self.assertIn("目录栏支持键盘可操作的视觉隐藏", self.skill)
        self.assertIn("隐藏后释放侧栏空间", self.skill)

    def test_text_diagrams_default_to_images_and_keep_source_toggle(self) -> None:
        self.assertIn("## 文本定义图", self.reading_page)
        for text in (
            "Mermaid、PlantUML、Graphviz/DOT、D2",
            "同时交付渲染图片和原始代码",
            "默认显示图片",
            "代码视图完整保留可复制源码",
            "JS 失败时至少保留默认图片和可访问源码",
            "打印默认输出图片",
        ):
            with self.subTest(text=text):
                self.assertIn(text, self.reading_page)
        self.assertIn("查看时支持图片/代码切换，默认显示图片", self.skill)

    def test_page_architecture_covers_single_flat_and_hierarchical(self) -> None:
        self.assertIn("## 页面架构", self.skill)
        self.assertIn("单页、扁平多页或层级多页", self.skill)
        self.assertIn("规范依据", self.skill)
        self.assertNotIn("唯一维护源", self.skill)

        for text in (
            "### 单页",
            "### 扁平多页",
            "### 层级多页",
            "## `_site.json`：多页规范清单",
            "页面文件不得游离于 `_site.json`",
            "不宣称能自动生成页面",
        ):
            with self.subTest(text=text):
                self.assertIn(text, self.reading_page)

    def test_only_reading_page_references_are_bundled(self) -> None:
        self.assertFalse((REFERENCES / "html-ppt").exists())
        self.assertFalse((REFERENCES / "html-slides").exists())
        self.assertTrue((REFERENCES / "frontend-design" / "SKILL.md").is_file())
        self.assertTrue((REFERENCES / "html-page.md").is_file())

    def test_skill_is_html_only_and_has_one_design_authority(self) -> None:
        self.assertIn("frontend-design", self.skill)
        self.assertIn("## 工程与交付验收（MUST）", self.reading_page)
        self.assertIn("frontend-design", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("直接生成 `.html`", self.skill)
        for unrelated in (
            "pretty-view-ppt",
            "html-ppt",
            "html-slides",
            "reveal.js",
            "Markdown 准则",
            "Markdown 或 HTML",
        ):
            with self.subTest(unrelated=unrelated):
                self.assertNotIn(unrelated, self.skill)
        self.assertNotIn("pretty-view-ppt", self.reading_page)

    def test_language_and_delivery_are_content_driven(self) -> None:
        self.assertIn("准确 `lang`", self.skill)
        self.assertIn("与正文语言一致的 `lang`", self.reading_page)
        self.assertNotIn("最后一段固定写", self.skill)
        self.assertNotIn(".pretty-view.md", self.skill)
        self.assertIn("docs/pretty-view-html/", self.skill)
        self.assertNotIn("docs/pretty-view/", self.skill)

    def test_retired_reading_page_references_are_not_distributed(self) -> None:
        for relpath in (
            "html-doc.md",
            "html-artifact",
            "spec-to-readable-html",
            "baoyu-markdown-to-html",
        ):
            with self.subTest(relpath=relpath):
                self.assertFalse((REFERENCES / relpath).exists(), relpath)
        self.assertNotIn("baoyu", self.skill)


if __name__ == "__main__":
    unittest.main()
