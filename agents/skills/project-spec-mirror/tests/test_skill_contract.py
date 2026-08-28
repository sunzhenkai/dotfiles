"""SKILL.md 与 specctl 命令表一致性。"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "specctl.py"
sys.path.insert(0, str(SCRIPT.parent))

import specctl  # noqa: E402

EXPECTED = {
    "detect",
    "init",
    "status",
    "git-info",
    "inventory",
    "symbols",
    "diff",
    "route",
    "set-sync",
    "validate",
}


class ContractTest(unittest.TestCase):
    def test_commands_match_skill_table(self) -> None:
        self.assertEqual(set(specctl.COMMANDS), EXPECTED)
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for name in EXPECTED:
            self.assertRegex(text, rf"`{re.escape(name)}`")

    def test_frontmatter_name(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: project-spec-mirror", text)
        self.assertIn("id: project-spec-mirror", text)

    def test_reference_files_exist(self) -> None:
        for rel in (
            "references/layout.md",
            "references/modes.md",
            "references/knowledge.md",
            "references/facets.md",
            "references/diagrams.md",
            "references/routing.md",
            "references/projections.md",
        ):
            self.assertTrue((SKILL_ROOT / rel).is_file(), rel)
