#!/usr/bin/env python3
"""Golden fixture: marine-life source rendered through pretty-view-html paths.

Run: python3 tests/test_marine_life_outputs.py
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


TESTS = Path(__file__).resolve().parent
MANIFEST = TESTS / "fixtures" / "marine-life" / "manifest.json"


def _count_h1(html: str) -> int:
    return len(re.findall(r"<h1\b", html, flags=re.I))


class MarineLifeFixtureTest(unittest.TestCase):
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
                if spec.get("bundle"):
                    continue
                text = self.outputs[name]
                self.assertGreater(len(text), 400)
                for phrase in phrases:
                    self.assertIn(phrase, text, f"{name} missing {phrase}")

    def test_html_page_contract(self) -> None:
        html = self.outputs["html-page"]
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn('lang="zh-CN"', html)
        self.assertIn("viewport", html)
        self.assertEqual(_count_h1(html), 1)
        self.assertIn("<nav", html)
        self.assertIn('aria-label="本页目录"', html)
        self.assertIn("<details", html)
        self.assertIn("<summary", html)
        self.assertIn(".shell:has(.site-nav details:not([open]))", html)
        self.assertIn('href="#zones-intertidal"', html)
        self.assertIn('href="#why"', html)
        self.assertIn("跳到正文", html)
        self.assertNotIn('aria-label="阅读宽度"', html)
        self.assertNotIn("data-measure", html)
        self.assertNotIn("pretty-view-width", html)
        self.assertIn("68ch", html)
        self.assertIn("min(100%, 110ch)", html)
        self.assertIn("article > .wide", html)
        self.assertNotIn("max-width: none", html)
        self.assertIn("timeline", html)
        self.assertIn("<table", html)
        self.assertIn("<ul", html)
        self.assertIn("<ol", html)
        self.assertIn("--abyss", html)
        self.assertNotIn("#667eea", html)
        self.assertNotIn("font-family: Inter", html)
        self.assertNotIn("file:///", html)

HREF_RE = re.compile(r"""<a\b[^>]*href=["']([^"']+)["']""", re.I)
H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.I | re.S)
SITE_DIR = TESTS / "golden" / "marine-life" / "html-page-site"


def _h1(html: str) -> str:
    match = H1_RE.search(html)
    assert match, "missing h1"
    return re.sub(r"<[^>]+>", "", match.group(1)).strip()


def _site_entries(data: dict) -> list[tuple[str, str]]:
    entries = [(data["home"], data["title"])]
    def walk(nodes: list[dict]) -> None:
        for node in nodes:
            entries.append((node["path"], node["title"]))
            walk(node.get("children") or [])

    walk(data["pages"])
    return entries


def _site_titles(data: dict) -> list[str]:
    titles: list[str] = []

    def walk(nodes: list[dict]) -> None:
        for node in nodes:
            titles.append(node["title"])
            walk(node.get("children") or [])

    walk(data["pages"])
    return titles


class MarineLifeSiteNavTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.site = SITE_DIR
        cls.meta = json.loads((cls.site / "_site.json").read_text(encoding="utf-8"))
        cls.entries = _site_entries(cls.meta)
        cls.html = {
            path: (cls.site / path).read_text(encoding="utf-8") for path, _title in cls.entries
        }

    def test_site_json_paths_are_safe_and_complete(self) -> None:
        self.assertEqual(self.meta["home"], "index.html")
        listed = {path for path, _title in self.entries}
        disk = {p.relative_to(self.site).as_posix() for p in self.site.rglob("*.html")}
        self.assertEqual(listed, disk)
        for path, title in self.entries:
            with self.subTest(path=path):
                self.assertFalse(path.startswith("/"))
                self.assertNotIn("..", path)
                self.assertEqual(_h1(self.html[path]), title)
                self.assertEqual(_count_h1(self.html[path]), 1)

    def test_shared_css_and_no_absolute_file_urls(self) -> None:
        css = self.site / "assets" / "site.css"
        js = self.site / "assets" / "site.js"
        self.assertTrue(css.is_file())
        self.assertFalse(js.exists())
        css_text = css.read_text(encoding="utf-8")
        self.assertIn("68ch", css_text)
        self.assertIn("min(100%, 110ch)", css_text)
        self.assertIn(".page > .wide", css_text)
        self.assertNotIn("max-width: none", css_text)
        self.assertNotIn("pretty-view-width", css_text)
        self.assertNotIn(".measure", css_text)
        for path, html in self.html.items():
            with self.subTest(path=path):
                self.assertIn('rel="stylesheet"', html)
                self.assertNotIn("file:///", html)
                self.assertNotIn("<style>", html)
                self.assertNotIn("site.js", html)
                self.assertNotIn('aria-label="阅读宽度"', html)
                self.assertNotIn("data-measure", html)
                depth = path.count("/")
                expected_css = "../" * depth + "assets/site.css"
                self.assertIn(expected_css, html)
                self.assertIn('aria-label="站点导航"', html)
                self.assertIn('aria-current="page"', html)

    def test_navigation_matches_manifest_order(self) -> None:
        expected_titles = _site_titles(self.meta)
        for path, html in self.html.items():
            with self.subTest(path=path):
                match = re.search(
                    r'<nav class="site-nav".*?</nav>',
                    html,
                    flags=re.I | re.S,
                )
                self.assertIsNotNone(match, f"{path} missing site nav")
                nav = re.sub(r"<[^>]+>", " ", match.group(0))
                positions = [nav.find(title) for title in expected_titles]
                self.assertTrue(all(pos >= 0 for pos in positions), f"{path} nav missing title")
                self.assertEqual(positions, sorted(positions), f"{path} nav order drift")

    def test_every_page_can_reach_home(self) -> None:
        home = (self.site / "index.html").resolve()
        for path, html in self.html.items():
            page = self.site / path
            targets = []
            for href in HREF_RE.findall(html):
                if href.startswith(("#", "http://", "https://", "mailto:")):
                    continue
                target = (page.parent / href).resolve()
                self.assertTrue(target.exists(), f"{path} dead link {href}")
                self.assertTrue(str(target).startswith(str(self.site.resolve())))
                targets.append(target)
            with self.subTest(path=path):
                self.assertIn(home, targets)

    def test_group_index_explains_and_links_children(self) -> None:
        zones = next(node for node in self.meta["pages"] if node["path"] == "zones/index.html")
        html = self.html["zones/index.html"]
        self.assertIn("领域", html)
        page = self.site / "zones/index.html"
        child_files = {(page.parent / child["path"].split("/", 1)[-1]).resolve() for child in zones["children"]}
        linked = {
            (page.parent / href).resolve()
            for href in HREF_RE.findall(html)
            if not href.startswith("#")
        }
        self.assertTrue(child_files <= linked)

    def test_nested_pages_have_breadcrumb_and_sibling_pager(self) -> None:
        html = self.html["zones/intertidal.html"]
        self.assertIn('aria-label="面包屑"', html)
        self.assertIn('href="../index.html"', html)
        self.assertIn('href="index.html"', html)
        self.assertIn('rel="prev"', html)
        self.assertIn('rel="next"', html)
        self.assertIn("浅海陆架", html)
        self.assertIn("海洋分区", html)
        self.assertIn('aria-current="page"', html)
        self.assertRegex(html, re.compile(r'aria-current="page"[^>]*>潮间带'))

    def test_bundle_keeps_source_phrases(self) -> None:
        phrases = json.loads(MANIFEST.read_text(encoding="utf-8"))["phrases"]
        blob = "\n".join(self.html.values())
        for phrase in phrases:
            self.assertIn(phrase, blob)


if __name__ == "__main__":
    unittest.main()
