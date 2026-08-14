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

    def test_reading_pages_have_one_runtime_reference_and_theme(self) -> None:
        self.assertIn("所有未命中 PPT、reveal.js、显式 md→html 的 HTML 请求", self.skill)
        self.assertIn("**reference**：`html-page`", self.skill)
        self.assertIn("**主题**：`stone-ink`", self.skill)
        self.assertIn("只 Read `references/html-page.md`", self.skill)

        for retired in ("spec-to-readable-html", "html-artifact", "html-doc"):
            self.assertNotIn(retired, self.skill)

    def test_unified_reference_keeps_content_modes_in_one_visual_system(self) -> None:
        for mode in ("`spec`", "`visual`", "`doc`", "`article`", "`review`"):
            self.assertIn(mode, self.reading_page)
        for token in ("--canvas", "--paper", "--ink", "--accent", "--line"):
            self.assertIn(token, self.reading_page)
        self.assertIn("同壳、同 token、按内容换组件", self.reading_page)

    def test_page_split_gate_defaults_to_single_page_and_auto_infers_packages(self) -> None:
        for text in (
            "**默认生成单页。**",
            "信号不确定时保持单页",
            "强信号",
            "自动生成多文件包",
            "无需用户确认拆页决策",
            "index.html` 是总览与唯一对外入口",
            "每页都必须用相对链接返回 `index.html`",
        ):
            with self.subTest(text=text):
                self.assertIn(text, self.skill)

        self.assertIn("默认生成**一个 HTML 页面**", self.reading_page)
        self.assertIn("判断不确定时保持单页，不向用户追问", self.reading_page)
        self.assertIn("所有本地 `href` / `src` 都使用相对路径", self.reading_page)
        self.assertIn("附属页不得单独登记", self.reading_page)

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
