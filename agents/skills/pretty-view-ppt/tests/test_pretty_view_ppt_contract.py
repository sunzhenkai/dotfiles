#!/usr/bin/env python3
"""Contract tests for pretty-view-ppt routing and bundled references."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"
REFERENCES = ROOT / "references"


class PrettyViewPptContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = SKILL.read_text(encoding="utf-8")

    def test_special_routes_remain_available(self) -> None:
        expected = {
            "html-ppt": REFERENCES / "html-ppt" / "SKILL.md",
            "html-slides": REFERENCES / "html-slides" / "SKILL.md",
        }
        for route, path in expected.items():
            with self.subTest(route=route):
                self.assertIn(route, self.skill)
                self.assertTrue(path.is_file(), path)

    def test_each_deck_route_has_one_design_authority(self) -> None:
        for text in (
            "每次只服从所选路径的主题、模板和运行时约束",
            "禁止跨路径拼接设计规则",
        ):
            with self.subTest(text=text):
                self.assertIn(text, self.skill)

    def test_only_presentation_references_are_bundled(self) -> None:
        self.assertFalse((REFERENCES / "html-page.md").exists())
        self.assertFalse((REFERENCES / "frontend-design").exists())
        for unrelated in (
            "pretty-view-html",
            "html-page.md",
            "frontend-design",
            "Markdown",
            "阅读页",
        ):
            with self.subTest(unrelated=unrelated):
                self.assertNotIn(unrelated, self.skill)

    def test_language_and_delivery_are_content_driven(self) -> None:
        self.assertNotIn("最后一段固定写", self.skill)
        self.assertNotIn(".pretty-view.md", self.skill)
        self.assertIn("docs/pretty-view-ppt/slides/", self.skill)
        self.assertNotIn("docs/pretty-view/slides/", self.skill)

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
