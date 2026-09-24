"""role-chat：frontmatter、角色注册表与 references 一致性。"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[2]
ROLES_DIR = ROOT / "references" / "roles"

ROLE_RE = re.compile(r"references/roles/([a-z0-9-]+)\.md")
EXPECTED_ROLES = {
    "finance",
    "dev-engineer",
    "architect",
    "product-manager",
    "english-tutor",
}


def _skill() -> str:
    return (ROOT / "SKILL.md").read_text(encoding="utf-8")


def _frontmatter(skill_md: str) -> str:
    parts = skill_md.split("---", 2)
    if len(parts) < 3:
        return ""
    return parts[1]


class ContractTest(unittest.TestCase):
    def test_frontmatter_name_matches_directory(self) -> None:
        self.assertEqual(ROOT.name, "role-chat")
        text = _skill()
        self.assertIn("name: role-chat", text)
        self.assertIn("id: role-chat", text)

    def test_description_declares_manual_trigger_only(self) -> None:
        fm = _frontmatter(_skill())
        self.assertIn("仅在用户点名", fm)
        self.assertIn("不要自动加载", fm)
        # 占位符只在正文渲染，写进 frontmatter 会让 sync 的残留校验失败。
        self.assertNotIn("{{slash:", fm)

    def test_gate_sections_present(self) -> None:
        text = _skill()
        self.assertIn("仅手动触发", text)
        self.assertIn("门 2", text)
        self.assertIn("超过 **2 个**", text)
        self.assertIn("默认互斥", text)

    def test_registry_roles_have_reference_files(self) -> None:
        refs = set(ROLE_RE.findall(_skill()))
        self.assertEqual(refs, EXPECTED_ROLES)
        for role_id in refs:
            self.assertTrue((ROLES_DIR / f"{role_id}.md").is_file(), role_id)

    def test_no_orphan_role_files(self) -> None:
        on_disk = {path.stem for path in ROLES_DIR.glob("*.md")}
        self.assertEqual(on_disk, set(ROLE_RE.findall(_skill())))

    def test_role_files_share_entry_and_exit_sections(self) -> None:
        for path in sorted(ROLES_DIR.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            self.assertIn("## 身份与视角", text, path.name)
            self.assertIn("## 切换信号", text, path.name)

    def test_slash_placeholder_used(self) -> None:
        text = _skill()
        self.assertIn("{{slash:role-chat}}", text)
        self.assertNotIn("/role-chat", text)

    def test_english_tutor_preserves_legacy_rules(self) -> None:
        tutor = (ROLES_DIR / "english-tutor.md").read_text(encoding="utf-8")
        for needle in (
            "CET-4",
            "CET-6",
            "IELTS 5.5",
            "IELTS 6.5",
            "自由",
            "默认 **CET-4**",
            "**Coach:**",
            "✏️",
            "换话题",
            "更难",
            "更简单",
            "结束",
            "最多指出 **2 个问题**",
            "全程用英语对话",
        ):
            self.assertIn(needle, tutor)

    def test_only_installable_and_dev_dirs_present(self) -> None:
        entries = {path.name for path in ROOT.iterdir()}
        self.assertEqual(entries, {"SKILL.md", "references", "tests"})

    def test_runtime_allowlist_compatibility(self) -> None:
        import yaml

        policy = yaml.safe_load(
            (REPO_ROOT / "agents" / "runtime.yaml").read_text(encoding="utf-8")
        )["skills"]
        self.assertIn("SKILL.md", policy["files"])
        self.assertIn("references", policy["sidecars"])
        self.assertNotIn("tests", policy["files"] + policy["sidecars"])

    def test_shared_skill_has_no_private_content(self) -> None:
        blobs = [_skill()]
        blobs += [path.read_text(encoding="utf-8") for path in ROLES_DIR.glob("*.md")]
        for text in blobs:
            for needle in ("/home/", "~/.agents", "dotf ", "sunzhenkai"):
                self.assertNotIn(needle, text)


if __name__ == "__main__":
    unittest.main()
