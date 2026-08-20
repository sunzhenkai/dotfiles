#!/usr/bin/env python3
"""Golden fixture: beacon-ttl postmortem + fix review through pretty-view-html.

Run: python3 tests/test_beacon_ttl_outputs.py
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


TESTS = Path(__file__).resolve().parent
MANIFEST = TESTS / "fixtures" / "beacon-ttl" / "manifest.json"


def _count_h1(html: str) -> int:
    return len(re.findall(r"<h1\b", html, flags=re.I))


class BeaconTtlFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.sources: dict[str, str] = {}
        cls.outputs: dict[str, str] = {}
        for name, spec in cls.manifest["outputs"].items():
            cls.sources[name] = (TESTS / spec["source"]).read_text(encoding="utf-8")
            cls.outputs[name] = (TESTS / spec["path"]).read_text(encoding="utf-8")

    def test_postmortem_source_is_article_report(self) -> None:
        src = self.sources["postmortem"]
        self.assertRegex(src, re.compile(r"^# ", re.M))
        self.assertRegex(src, re.compile(r"^## 结论", re.M))
        self.assertIn("## 2. 时间线", src)
        self.assertIn("|------|", src)
        self.assertGreaterEqual(src.count("|------|"), 2)
        self.assertIn("```go", src)
        self.assertIn("动作项", src)
        self.assertIn("未决项", src)
        self.assertIn("SEV-1", src)
        self.assertIn("ttl_ms", src)

    def test_review_source_is_severity_grouped(self) -> None:
        src = self.sources["fix-review"]
        self.assertRegex(src, re.compile(r"^# ", re.M))
        self.assertRegex(src, re.compile(r"^## 结论", re.M))
        self.assertIn("## 2. 阻断", src)
        self.assertIn("## 3. 主要", src)
        self.assertIn("## 4. 次要", src)
        self.assertIn("残留风险", src)
        self.assertIn("```go", src)
        self.assertIn("internal/auth/session.go", src)
        self.assertIn("|------|", src)

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

    def test_shared_html_contract(self) -> None:
        for name, html in self.outputs.items():
            with self.subTest(output=name):
                self.assertIn("<!DOCTYPE html>", html)
                self.assertIn('lang="zh-CN"', html)
                self.assertIn("viewport", html)
                self.assertEqual(_count_h1(html), 1)
                self.assertIn("<nav", html)
                self.assertIn('aria-label="本页目录"', html)
                self.assertIn("<details", html)
                self.assertIn("<summary", html)
                self.assertIn(".shell:has(.toc details:not([open]))", html)
                self.assertIn("跳到正文", html)
                self.assertNotIn('aria-label="阅读宽度"', html)
                self.assertNotIn("data-measure", html)
                self.assertNotIn("pretty-view-width", html)
                self.assertIn("68ch", html)
                self.assertIn("min(100%, 110ch)", html)
                self.assertIn("article > .wide", html)
                self.assertNotIn("max-width: none", html)
                self.assertNotIn("#667eea", html)
                self.assertNotIn("font-family: Inter", html)
                self.assertNotIn("file:///", html)

    def test_postmortem_article_contract(self) -> None:
        html = self.outputs["postmortem"]
        spec = self.manifest["outputs"]["postmortem"]
        self.assertEqual(spec["mode"], "article")
        self.assertEqual(spec["architecture"], "single-page")
        self.assertIn("tldr", html)
        self.assertIn("结论", html)
        self.assertIn("timeline", html)
        self.assertIn("<table", html)
        self.assertIn("callout", html)
        self.assertIn('href="#timeline"', html)
        self.assertIn('href="#root-cause"', html)
        self.assertIn("<pre", html)
        self.assertNotIn("_site.json", html)

    def test_fix_review_contract(self) -> None:
        html = self.outputs["fix-review"]
        spec = self.manifest["outputs"]["fix-review"]
        self.assertEqual(spec["mode"], "review")
        self.assertEqual(spec["architecture"], "single-page")
        self.assertIn("阻断", html)
        self.assertIn("主要", html)
        self.assertIn("次要", html)
        self.assertIn("残留风险", html)
        self.assertIn("<pre", html)
        self.assertIn("<code", html)
        self.assertIn("internal/auth/session.go:142", html)
        self.assertIn("<table", html)
        self.assertIn('href="#blocker"', html)
        self.assertIn('href="#residual"', html)
        self.assertIn("finding", html)
        self.assertNotIn("_site.json", html)


if __name__ == "__main__":
    unittest.main()
