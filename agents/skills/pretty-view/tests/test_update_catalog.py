#!/usr/bin/env python3
"""Tests for update-catalog.py. Run: python3 tests/test_update_catalog.py"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "update_catalog",
    Path(__file__).resolve().parent.parent / "scripts" / "update-catalog.py",
)
assert _SPEC is not None and _SPEC.loader is not None
uc = importlib.util.module_from_spec(_SPEC)
sys.modules["update_catalog"] = uc
_SPEC.loader.exec_module(uc)


INDEX = """# pretty-view

| 日期 | 标题 | 类型 | 介质 | 路径 |
|------|------|------|------|------|
| 2026-08-13 | 鉴权方案 | proposals | HTML | [proposals/2026-08-13-auth.html](proposals/2026-08-13-auth.html) |
| 2026-08-12 | 笔记 | knowledge | Markdown | [knowledge/2026-08-12-notes.md](knowledge/2026-08-12-notes.md) |
"""


class CatalogTest(unittest.TestCase):
    def test_parse_index(self) -> None:
        entries = uc.parse_index_md(INDEX)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].relpath, "proposals/2026-08-13-auth.html")
        self.assertTrue(uc.is_html_medium(entries[0].medium, entries[0].relpath))
        self.assertFalse(uc.is_html_medium(entries[1].medium, entries[1].relpath))

    def test_generates_index_html_and_nav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            article = root / "proposals" / "2026-08-13-auth.html"
            article.parent.mkdir(parents=True)
            article.write_text("<!DOCTYPE html><html><body><p>hi</p></body></html>\n", encoding="utf-8")
            (root / "knowledge").mkdir()
            (root / "knowledge" / "2026-08-12-notes.md").write_text("# notes\n", encoding="utf-8")
            (root / "INDEX.md").write_text(INDEX, encoding="utf-8")

            code = uc.run(root, check=False, no_nav=False)
            self.assertEqual(code, 0)
            catalog = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="proposals/2026-08-13-auth.html"', catalog)
            self.assertNotIn("notes.md", catalog)
            self.assertIn("浏览器入口", (root / "INDEX.md").read_text(encoding="utf-8"))
            page = article.read_text(encoding="utf-8")
            self.assertIn("data-pretty-view-nav", page)
            self.assertIn('href="../index.html"', page)

            code = uc.run(root, check=True, no_nav=False)
            self.assertEqual(code, 0)

    def test_orphan_listed_missing_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "INDEX.md").write_text(INDEX, encoding="utf-8")
            orphan = root / "articles" / "2026-08-01-orphan.html"
            orphan.parent.mkdir(parents=True)
            orphan.write_text("<html><body>x</body></html>\n", encoding="utf-8")
            code = uc.run(root, check=False, no_nav=True)
            self.assertEqual(code, 1)  # INDEX dead link to auth.html
            catalog = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn("orphan.html", catalog)
            self.assertNotIn("auth.html", catalog)

    def test_markdown_only_no_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            md_only = """# pretty-view

浏览器入口：[index.html](index.html)。

| 日期 | 标题 | 类型 | 介质 | 路径 |
|------|------|------|------|------|
| 2026-08-12 | 笔记 | knowledge | Markdown | [knowledge/a.md](knowledge/a.md) |
"""
            (root / "INDEX.md").write_text(md_only, encoding="utf-8")
            (root / "index.html").write_text("stale\n", encoding="utf-8")
            code = uc.run(root, check=False, no_nav=True)
            self.assertEqual(code, 0)
            self.assertFalse((root / "index.html").exists())
            self.assertNotIn("浏览器入口", (root / "INDEX.md").read_text(encoding="utf-8"))

    def test_skip_slide_nav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deck = root / "slides" / "talk" / "index.html"
            deck.parent.mkdir(parents=True)
            deck.write_text("<html><body><div class=slide>x</div></body></html>\n", encoding="utf-8")
            (root / "INDEX.md").write_text(
                """# pretty-view

| 日期 | 标题 | 类型 | 介质 | 路径 |
|------|------|------|------|------|
| 2026-08-13 | 分享 | slides | HTML | [slides/talk/index.html](slides/talk/index.html) |
""",
                encoding="utf-8",
            )
            self.assertEqual(uc.run(root, check=False, no_nav=False), 0)
            self.assertNotIn("data-pretty-view-nav", deck.read_text(encoding="utf-8"))
            self.assertIn('href="slides/talk/index.html"', (root / "index.html").read_text(encoding="utf-8"))

    def test_bundle_indexes_only_main(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "proposals" / "2026-08-13-auth-series"
            bundle.mkdir(parents=True)
            (bundle / "index.html").write_text(
                "<html><body><p>toc</p><a href='api.html'>api</a></body></html>\n",
                encoding="utf-8",
            )
            (bundle / "api.html").write_text("<html><body><p>api</p></body></html>\n", encoding="utf-8")
            (bundle / "faq.html").write_text("<html><body><p>faq</p></body></html>\n", encoding="utf-8")
            (root / "INDEX.md").write_text(
                """# pretty-view

| 日期 | 标题 | 类型 | 介质 | 路径 |
|------|------|------|------|------|
| 2026-08-13 | 鉴权系列 | proposals | HTML | [proposals/2026-08-13-auth-series/index.html](proposals/2026-08-13-auth-series/index.html) |
| 2026-08-13 | API | proposals | HTML | [proposals/2026-08-13-auth-series/api.html](proposals/2026-08-13-auth-series/api.html) |
""",
                encoding="utf-8",
            )
            self.assertEqual(uc.run(root, check=False, no_nav=False), 0)
            catalog = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="proposals/2026-08-13-auth-series/index.html"', catalog)
            self.assertNotIn("api.html", catalog)
            self.assertNotIn("faq.html", catalog)
            main = (bundle / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="../../index.html"', main)
            self.assertNotIn("data-pretty-view-nav", (bundle / "api.html").read_text(encoding="utf-8"))

    def test_bundle_without_index_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "articles" / "2026-08-13-notes"
            bundle.mkdir(parents=True)
            (bundle / "a.html").write_text("<html><body>a</body></html>\n", encoding="utf-8")
            (root / "INDEX.md").write_text(
                """# pretty-view

| 日期 | 标题 | 类型 | 介质 | 路径 |
|------|------|------|------|------|
| 2026-08-12 | 笔记 | knowledge | Markdown | [knowledge/x.md](knowledge/x.md) |
""",
                encoding="utf-8",
            )
            self.assertEqual(uc.run(root, check=False, no_nav=True), 0)
            self.assertFalse((root / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
