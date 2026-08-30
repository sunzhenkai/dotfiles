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
    "coverage",
    "route",
    "set-sync",
    "finalize",
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

    def test_metadata_and_maintenance_boundary(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        experience = (SKILL_ROOT / "experience" / "README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("compatibility:", skill)
        self.assertIn("Git 源按 commit 更新", skill)
        self.assertNotIn("## Self-evolution", skill)
        self.assertNotIn("skill-upgrader", skill)
        self.assertIn("普通 project spec 镜像任务不得自动写入", experience)

    def test_reference_files_exist(self) -> None:
        for rel in (
            "references/layout.md",
            "references/checklist.md",
            "references/modes.md",
            "references/knowledge.md",
            "references/facets.md",
            "references/diagrams.md",
            "references/routing.md",
            "references/projections.md",
        ):
            self.assertTrue((SKILL_ROOT / rel).is_file(), rel)

    def test_important_briefs_not_omits(self) -> None:
        modes = (SKILL_ROOT / "references" / "modes.md").read_text(encoding="utf-8")
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("简述", modes)
        self.assertIn("不得整份省略", modes)
        self.assertNotIn("只能忽略没有业务含义的文件", modes)
        self.assertIn("简述", skill)
        self.assertNotIn("只能忽略无业务含义文件", skill)

    def test_important_behavior_is_deep_but_not_fake_complete(self) -> None:
        modes = (SKILL_ROOT / "references" / "modes.md").read_text(encoding="utf-8")
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("完整逻辑", modes)
        self.assertIn("important_paths", modes)
        self.assertIn("不是语言级完备索引", modes)
        self.assertRegex(modes, r"测试方法\s*\|\s*只简述")
        self.assertIn("深入行为承载符号", skill)
        self.assertIn("测试只写覆盖意图", skill)
        self.assertIn("不作为完备证明", skill)
        self.assertNotIn("用返回名单核对方法不得漏列", skill)

    def test_secret_literals_must_redact(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        modes = (SKILL_ROOT / "references" / "modes.md").read_text(encoding="utf-8")
        self.assertIn("<REDACTED>", skill)
        self.assertIn("AppKey", skill)
        self.assertIn("SecretKey", skill)
        self.assertIn("<REDACTED>", modes)
        self.assertIn("AppKey", modes)
        self.assertIn("SecretKey", modes)

    def test_reader_pages_use_project_voice(self) -> None:
        layout = (SKILL_ROOT / "references" / "layout.md").read_text(encoding="utf-8")
        specctl_src = (SKILL_ROOT / "scripts" / "specctl.py").read_text(encoding="utf-8")
        evals = (SKILL_ROOT / "evals" / "cases.yaml").read_text(encoding="utf-8")
        self.assertIn("读者口吻", layout)
        self.assertIn("# <project>", layout)
        self.assertNotIn("# Spec 镜像 — <project>", layout)
        self.assertNotIn("给人读的孪生规格", layout)
        self.assertNotIn("给人读的孪生规格", specctl_src)
        self.assertNotIn("# Spec 镜像 — {project}", specctl_src)
        self.assertIn("孪生规格", evals)

    def test_diagrams_cover_complex_logic_without_fake_delivery(self) -> None:
        diagrams = (SKILL_ROOT / "references" / "diagrams.md").read_text(encoding="utf-8")
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        knowledge = (SKILL_ROOT / "references" / "knowledge.md").read_text(encoding="utf-8")
        evals = (SKILL_ROOT / "evals" / "cases.yaml").read_text(encoding="utf-8")
        self.assertIn("复杂业务逻辑", diagrams)
        self.assertIn("本轮必须交付", diagrams)
        self.assertIn("不能只留 JSON", diagrams)
        self.assertIn("没有图不算失败", diagrams)
        self.assertIn("复杂业务逻辑", skill)
        self.assertIn("线性三步", skill)
        self.assertIn("复杂业务逻辑", knowledge)
        self.assertIn("复杂业务逻辑", evals)
        self.assertNotIn("不把“没有图”当作 build 失败", diagrams)
        self.assertNotIn("不因候选未画自动阻塞 build", skill)

    def test_hard_safety_boundaries_remain(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("不自动 commit / push", skill)
        self.assertIn("<REDACTED>", skill)
        self.assertIn("不得覆盖", skill)
        self.assertIn("外来仓", skill)

    def test_checklist_is_the_installable_selfcheck(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        checklist = (SKILL_ROOT / "references" / "checklist.md").read_text(encoding="utf-8")
        self.assertIn("references/checklist.md", skill)
        self.assertNotIn("-s agents/skills/project-spec-mirror/tests", skill)
        for marker in ("<REDACTED>", "set-sync --built", "coverage", "archify"):
            self.assertIn(marker, checklist)
