#!/usr/bin/env python3
"""Contract: four capability skills are internal refs; frontend-design is not vendored."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"
CATALOG = ROOT / "references" / "catalog.md"
INTERNAL = (
    "shadcn",
    "tailwind-css-patterns",
    "tailwind-design-system",
    "webapp-testing",
)


class DotfUiDesignContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = SKILL.read_text(encoding="utf-8")
        cls.catalog = CATALOG.read_text(encoding="utf-8")

    def test_frontmatter_name_matches_directory(self) -> None:
        self.assertIn("name: dotf-ui-design", self.skill)
        self.assertEqual(ROOT.name, "dotf-ui-design")

    def test_internal_refs_are_vendored(self) -> None:
        refs = ROOT / "references"
        for name in INTERNAL:
            with self.subTest(name=name):
                self.assertTrue((refs / name / "SKILL.md").is_file(), refs / name)

    def test_frontend_design_is_not_vendored(self) -> None:
        self.assertFalse((ROOT / "references" / "frontend-design").exists())

    def test_catalog_binds_sources_and_load_paths(self) -> None:
        expected = {
            "frontend-design": "~/.agents/skills/frontend-design/SKILL.md",
            "shadcn": "references/shadcn/SKILL.md",
            "tailwind-css-patterns": "references/tailwind-css-patterns/SKILL.md",
            "tailwind-design-system": "references/tailwind-design-system/SKILL.md",
            "webapp-testing": "references/webapp-testing/SKILL.md",
        }
        sources = {
            "frontend-design": "anthropics/skills",
            "shadcn": "shadcn/ui",
            "tailwind-css-patterns": "giuseppe-trisciuoglio/developer-kit",
            "tailwind-design-system": "wshobson/agents",
            "webapp-testing": "anthropics/skills",
        }
        for name, path in expected.items():
            with self.subTest(name=name):
                self.assertIn(f"`{name}`", self.catalog)
                self.assertIn(f"`{path}`", self.catalog)
                self.assertIn(f"`{sources[name]}`", self.catalog)

    def test_router_keeps_frontend_design_global(self) -> None:
        for text in (
            "skills-defaults.yaml",
            "dotf agents -c",
            "一次只加载一个能力 skill",
            "内部引用",
        ):
            with self.subTest(text=text):
                self.assertIn(text, self.skill)

    def test_excludes_lookalike_sources(self) -> None:
        for text in (
            "heygen-com/hyperframes@tailwind",
            "browser-use",
            "不要用这些同名/近名来源",
        ):
            with self.subTest(text=text):
                self.assertIn(text, self.catalog)


if __name__ == "__main__":
    unittest.main()
