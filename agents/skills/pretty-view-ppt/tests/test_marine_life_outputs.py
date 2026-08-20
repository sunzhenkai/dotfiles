#!/usr/bin/env python3
"""Golden fixture: marine-life source rendered through pretty-view-ppt paths.

Run: python3 tests/test_marine_life_outputs.py
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


TESTS = Path(__file__).resolve().parent
MANIFEST = TESTS / "fixtures" / "marine-life" / "manifest.json"
ASSET_RE = re.compile(r"""(?:href|src)=["']([^"'#]+)["']""", re.I)


class MarineLifeDeckFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.source = (TESTS / cls.manifest["source"]).read_text(encoding="utf-8")
        cls.outputs: dict[str, str] = {}
        for name, spec in cls.manifest["outputs"].items():
            path = TESTS / spec["path"]
            cls.outputs[name] = path.read_text(encoding="utf-8")

    def test_source_has_hierarchy_and_content_types(self) -> None:
        src = self.source
        self.assertRegex(src, re.compile(r"^# ", re.M))
        self.assertRegex(src, re.compile(r"^## ", re.M))
        self.assertRegex(src, re.compile(r"^### ", re.M))
        self.assertRegex(src, re.compile(r"^#### ", re.M))
        self.assertIn("|------|", src)
        self.assertGreaterEqual(src.count("|------|"), 2)
        self.assertIn("时间线", src)
        self.assertIn("## 目录", src)
        self.assertRegex(src, re.compile(r"^[-*] ", re.M))
        self.assertRegex(src, re.compile(r"^1\. ", re.M))
        self.assertIn("潮间带", src)
        self.assertIn("灯笼鱼", src)
        self.assertIn("马里亚纳", src)

    def test_all_outputs_exist_and_keep_source_phrases(self) -> None:
        phrases = self.manifest["phrases"]
        for name, spec in self.manifest["outputs"].items():
            path = TESTS / spec["path"]
            with self.subTest(output=name):
                self.assertTrue(path.is_file(), path)
                text = self.outputs[name]
                self.assertGreater(len(text), 400)
                for phrase in phrases:
                    self.assertIn(phrase, text, f"{name} missing {phrase}")

    def test_html_ppt_contract(self) -> None:
        html = self.outputs["html-ppt"]
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn('lang="zh-CN"', html)
        self.assertIn("academic-paper", html)
        self.assertGreaterEqual(html.count('class="slide"'), 8)
        self.assertIn('src="assets/runtime.js"', html)
        self.assertIn('href="assets/deck.css"', html)
        self.assertIn('class="tl"', html)
        self.assertIn("<table", html)
        self.assertIn('class="notes"', html)
        ppt_dir = TESTS / "golden" / "marine-life" / "html-ppt"
        self.assertNotIn("references/", html)
        local_assets = [
            rel
            for rel in ASSET_RE.findall(html)
            if not rel.startswith(("http://", "https://", "mailto:"))
        ]
        self.assertEqual(local_assets, ["assets/deck.css", "assets/runtime.js"])
        for rel in local_assets:
            target = (ppt_dir / rel).resolve()
            self.assertTrue(str(target).startswith(str(ppt_dir.resolve())))
            self.assertTrue(target.is_file(), rel)

    def test_html_slides_contract(self) -> None:
        html = self.outputs["html-slides"]
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("reveal.js", html)
        self.assertIn("theme/white.css", html)
        self.assertIn("<table", html)
        self.assertIn("<ul", html)
        self.assertIn("<h2>海洋分区</h2>", html)
        self.assertIn("<h3>潮间带</h3>", html)
        self.assertRegex(html, re.compile(r"<section>\s*<section>", re.S))
        self.assertGreaterEqual(len(re.findall(r"<section\b", html)), 8)


if __name__ == "__main__":
    unittest.main()
