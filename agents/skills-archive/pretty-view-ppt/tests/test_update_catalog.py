#!/usr/bin/env python3
"""Tests for the presentation-only catalog."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "update_ppt_catalog",
    Path(__file__).resolve().parent.parent / "scripts" / "update-catalog.py",
)
assert _SPEC is not None and _SPEC.loader is not None
catalog = importlib.util.module_from_spec(_SPEC)
sys.modules["update_ppt_catalog"] = catalog
_SPEC.loader.exec_module(catalog)

INDEX = """# pretty-view-ppt

| 日期 | 标题 | 类型 | 介质 | 路径 |
|------|------|------|------|------|
| 2026-08-20 | 海洋图鉴 | slides | HTML | [slides/marine-life/index.html](slides/marine-life/index.html) |
"""


class CatalogTest(unittest.TestCase):
    def test_generates_catalog_without_modifying_deck(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deck = root / "slides" / "marine-life" / "index.html"
            deck.parent.mkdir(parents=True)
            original = "<!DOCTYPE html><html><body>deck</body></html>\n"
            deck.write_text(original, encoding="utf-8")
            (root / "INDEX.md").write_text(INDEX, encoding="utf-8")

            self.assertEqual(catalog.run(root, check=False), 0)
            output = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="slides/marine-life/index.html"', output)
            self.assertEqual(deck.read_text(encoding="utf-8"), original)
            self.assertIn("浏览器入口", (root / "INDEX.md").read_text(encoding="utf-8"))
            self.assertEqual(catalog.run(root, check=True), 0)

    def test_missing_listed_deck_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.mkdir(exist_ok=True)
            (root / "INDEX.md").write_text(INDEX, encoding="utf-8")
            self.assertEqual(catalog.run(root, check=False), 1)


if __name__ == "__main__":
    unittest.main()
