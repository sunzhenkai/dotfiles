"""Skill 加载器递归扫描 SKILL.md：Skill 根目录以外的 SKILL.md 会被重复注册。

进化快照用 SKILL.md.candidate，内置子参考用 REFERENCE.md。
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_TREES = (".agents/skills", "agents/skills", "agents/skills-archive")


def test_only_skill_root_has_skill_md() -> None:
    nested = []
    for tree in SKILL_TREES:
        base = ROOT / tree
        if not base.is_dir():
            continue
        nested += [
            str(p.relative_to(ROOT))
            for p in base.glob("*/**/SKILL.md")
            if p.parent.parent != base
        ]
    assert nested == [], f"Skill 根目录以外不得有 SKILL.md：{sorted(nested)}"
