from __future__ import annotations

import argparse
import importlib.util
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SKILL_ROOT = ROOT / "agents/skills/task-workflow"
COMMAND_ROOT = ROOT / "agents/commands"
TASKCTL_PATH = SKILL_ROOT / "scripts/taskctl.py"
EXPECTED_COMMANDS = {
    "list",
    "resolve",
    "set-status",
    "new",
    "archive",
    "restore",
    "prepare-branches",
    "execution-context",
    "advance",
    "notes",
}
REMOVED_COMMANDS = {
    "checkpoint",
    "apply-next",
    "repo-roots",
    "scope-repos",
    "git-summary",
}


def load_taskctl():
    spec = importlib.util.spec_from_file_location("taskctl_contract", TASKCTL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SkillContractTest(unittest.TestCase):
    def test_reference_set_is_bounded(self) -> None:
        refs = {path.name for path in (SKILL_ROOT / "references").glob("*.md")}
        self.assertEqual(refs, {"planning.md", "apply.md", "archive.md", "safety.md"})

    def test_public_taskctl_commands_are_converged(self) -> None:
        parser = load_taskctl().build_parser()
        subparsers = next(
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        )
        self.assertEqual(set(subparsers.choices), EXPECTED_COMMANDS)
        self.assertTrue(REMOVED_COMMANDS.isdisjoint(subparsers.choices))

    def test_root_skill_routes_instead_of_copying_phase_steps(self) -> None:
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("### task-new", text)
        self.assertNotIn("### task-apply", text)
        self.assertNotIn("### task-archive", text)
        for removed in REMOVED_COMMANDS:
            self.assertNotIn(f"`{removed}", text)

    def test_commands_are_thin_and_task_new_keeps_boundary(self) -> None:
        files = [COMMAND_ROOT / f"task-{name}.md" for name in (
            "new", "explore", "design", "propose", "apply", "archive"
        )]
        for path in files:
            text = path.read_text(encoding="utf-8")
            non_empty = [line for line in text.splitlines() if line.strip()]
            self.assertLessEqual(len(non_empty), 15, path.name)
            for removed in REMOVED_COMMANDS:
                self.assertNotIn(f"`{removed}", text, path.name)
        new_text = (COMMAND_ROOT / "task-new.md").read_text(encoding="utf-8")
        self.assertEqual(new_text.count("[TASK_NEW_INPUT_START]"), 1)

    def test_planning_commands_are_thin_and_git_free(self) -> None:
        for name in ("new", "explore", "design", "propose"):
            text = (COMMAND_ROOT / f"task-{name}.md").read_text(encoding="utf-8")
            for forbidden in ("prepare-branches", "git status", "git checkout", "worktree add"):
                self.assertNotIn(forbidden, text, name)

    def test_safety_references_existing_test_methods(self) -> None:
        safety = (SKILL_ROOT / "references/safety.md").read_text(encoding="utf-8")
        referenced = set(re.findall(r"`(test_[A-Za-z0-9_]+)`", safety))
        existing: set[str] = set()
        for path in (SKILL_ROOT / "tests").glob("test_*.py"):
            existing.update(
                re.findall(
                    r"^\s*def\s+(test_[A-Za-z0-9_]+)\s*\(",
                    path.read_text(encoding="utf-8"),
                    re.MULTILINE,
                )
            )
        self.assertTrue(referenced, "safety.md must reference regression tests")
        self.assertEqual(referenced - existing, set())

    def test_apply_pause_outcomes_are_not_completion(self) -> None:
        apply_text = (SKILL_ROOT / "references/apply.md").read_text(encoding="utf-8")
        command_text = (COMMAND_ROOT / "task-apply.md").read_text(encoding="utf-8")
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for text in (apply_text, command_text, skill_text):
            self.assertIn("不宣称完成", text)
            self.assertIn("只有 `done`", text)
            self.assertNotIn("kiro", text.lower())
            self.assertNotIn("goal(complete)", text.lower())
        self.assertIn("停本轮调度", apply_text)
        self.assertIn("不自动 defer", apply_text)
        self.assertIn("后续 change", apply_text)
        self.assertIn("停本轮调度", command_text)
        self.assertNotIn("停止并执行对应阶段动作", command_text)

    def test_instruction_footprint_is_below_previous_baseline(self) -> None:
        paths = [SKILL_ROOT / "SKILL.md", *(SKILL_ROOT / "references").glob("*.md")]
        paths.extend(COMMAND_ROOT.glob("task-*.md"))
        total = sum(path.stat().st_size for path in paths)
        self.assertLess(total, 30_000)


if __name__ == "__main__":
    unittest.main()
