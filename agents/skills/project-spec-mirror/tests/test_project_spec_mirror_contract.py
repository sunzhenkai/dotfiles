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
    "diff",
    "route",
    "finalize",
}

RETIRED = {
    "git-info",
    "inventory",
    "symbols",
    "coverage",
    "set-sync",
    "validate",
}


class ContractTest(unittest.TestCase):
    def test_commands_match_skill_table(self) -> None:
        self.assertEqual(set(specctl.COMMANDS), EXPECTED)
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for name in EXPECTED:
            self.assertRegex(text, rf"`{re.escape(name)}`")
        for name in RETIRED:
            self.assertNotRegex(text, rf"`{re.escape(name)}`")

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
            "references/routing.md",
            "references/diagrams.md",
            "references/appendix.md",
            "references/modes.md",
            "references/knowledge.md",
            "references/facets.md",
            "references/projections.md",
            "examples/minimal-checkout.md",
        ):
            self.assertTrue((SKILL_ROOT / rel).is_file(), rel)

    def test_dual_audience_contract(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        layout = (SKILL_ROOT / "references" / "layout.md").read_text(encoding="utf-8")
        modes = (SKILL_ROOT / "references" / "modes.md").read_text(encoding="utf-8")
        self.assertIn("briefing/", skill)
        self.assertIn("agent/specs/", skill)
        self.assertIn("evidence/", skill)
        self.assertIn("reconstructable", skill)
        self.assertIn("briefing", modes)
        self.assertIn("reconstructable", modes)
        self.assertIn("briefing/", layout)
        self.assertIn("agent/specs/", layout)
        self.assertIn("合法值只有 `briefing` | `reconstructable`", modes)
        self.assertNotIn("detail_level", skill)
        self.assertNotIn("`scope`", skill)

    def test_briefing_forbids_implementation_leak(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        layout = (SKILL_ROOT / "references" / "layout.md").read_text(encoding="utf-8")
        modes = (SKILL_ROOT / "references" / "modes.md").read_text(encoding="utf-8")
        self.assertIn("禁写", skill)
        self.assertIn("禁止源文件表", skill)
        self.assertIn("方法逐步走读", skill)
        self.assertIn("完整逻辑", skill)
        self.assertIn("待 build", layout)
        self.assertIn("禁写", modes)

    def test_secret_literals_must_redact(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        modes = (SKILL_ROOT / "references" / "modes.md").read_text(encoding="utf-8")
        self.assertIn("<REDACTED>", skill)
        self.assertIn("AppKey", skill)
        self.assertIn("SecretKey", skill)
        self.assertIn("<REDACTED>", modes)

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
        self.assertIn("禁止覆盖", skill)
        self.assertIn("外来仓", skill)

    def test_facets_are_opt_in(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        facets = (SKILL_ROOT / "references" / "facets.md").read_text(encoding="utf-8")
        appendix = (SKILL_ROOT / "references" / "appendix.md").read_text(encoding="utf-8")
        self.assertIn("默认不生成", skill)
        self.assertIn("默认不生成", facets)
        self.assertIn("evidence/realization", skill)
        self.assertIn("facets", appendix)

    def test_capability_status_and_finalize_only(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        layout = (SKILL_ROOT / "references" / "layout.md").read_text(encoding="utf-8")
        self.assertIn("`draft` | `ready`", skill)
        self.assertIn("唯一能把状态写成 `built`", layout)
        self.assertIn("layout=legacy", skill)
        self.assertIn("rebuild", skill)
        appendix = (SKILL_ROOT / "references" / "appendix.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("旧金字塔", appendix)

    def test_shared_skill_has_no_private_project_names(self) -> None:
        forbidden = (
            "algogear",
            "ali_express",
            "feature-extraction-lib",
            "dotf agents",
            "dotfiles 仓",
        )
        roots = [
            SKILL_ROOT / "SKILL.md",
            SKILL_ROOT / "experience",
            SKILL_ROOT / "evals",
            SKILL_ROOT / "references",
            SKILL_ROOT / "examples",
            SKILL_ROOT / "evolutions" / "README.md",
            SKILL_ROOT / "evolutions" / "20260829-complete-mode-notes-mandatory" / "proposal.yaml",
            SKILL_ROOT / "evolutions" / "20260829-complete-mode-notes-mandatory" / "decision.md",
            SKILL_ROOT / "evolutions" / "20260829-complete-mode-notes-mandatory" / "eval.md",
        ]
        blob = []
        for path in roots:
            if path.is_file():
                blob.append(path.read_text(encoding="utf-8"))
            else:
                for child in path.rglob("*"):
                    if child.is_file() and child.suffix in {".md", ".yaml", ".yml"}:
                        blob.append(child.read_text(encoding="utf-8"))
        text = "\n".join(blob).lower()
        for needle in forbidden:
            self.assertNotIn(needle.lower(), text, needle)

    def test_checklist_is_the_installable_selfcheck(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        checklist = (SKILL_ROOT / "references" / "checklist.md").read_text(encoding="utf-8")
        self.assertIn("references/checklist.md", skill)
        self.assertNotIn("-s agents/skills/project-spec-mirror/tests", skill)
        self.assertNotIn("set-sync --built", checklist)
        for marker in ("<REDACTED>", "finalize", "archify", "复现抽检"):
            self.assertIn(marker, checklist)
