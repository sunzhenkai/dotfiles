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
    "status",
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
        safety = (SKILL_ROOT / "references/safety.md").read_text(encoding="utf-8")
        command_text = (COMMAND_ROOT / "task-apply.md").read_text(encoding="utf-8")
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for text in (apply_text, command_text, skill_text):
            self.assertNotIn("kiro", text.lower())
            self.assertNotIn("goal(complete)", text.lower())
        # 规则正文只在 safety.md；apply.md 只保留 outcome 契约与模板。
        self.assertIn("只有 `done` 可宣称完成", safety)
        self.assertIn("并行挂起", safety)
        self.assertIn("停本轮调度", apply_text)
        self.assertIn("仓级测试不是 final verification", apply_text)
        self.assertIn("只有 `done` 才允许套完成模板", apply_text)
        # 完成措辞不再靠禁令重复，而是靠模板结构与 CLI 的 forbidden 标识。
        for follower in (command_text, skill_text):
            self.assertIn("next_action.forbidden", follower)
            self.assertNotIn("不宣称完成", follower)
        self.assertIn("claim_complete", apply_text)
        self.assertNotIn("停止并执行对应阶段动作", command_text)

    def test_apply_reporting_templates_are_fixed(self) -> None:
        apply_text = (SKILL_ROOT / "references/apply.md").read_text(encoding="utf-8")
        self.assertIn("## 汇报模板", apply_text)
        self.assertIn("### 暂停", apply_text)
        self.assertIn("### 完成", apply_text)
        self.assertIn("本轮以 `<result>` 结束（未完成）", apply_text)
        self.assertIn("`advance --phase done` 返回 `done`", apply_text)

    def test_next_action_contract_is_pinned_in_references(self) -> None:
        apply_text = (SKILL_ROOT / "references/apply.md").read_text(encoding="utf-8")
        source = TASKCTL_PATH.read_text(encoding="utf-8")
        for token in (
            "claim_complete",
            "schedule_candidate",
            "assume_not_started",
            "budget",
            "should_report",
        ):
            self.assertIn(token, apply_text, token)
            self.assertIn(token, source, token)
        self.assertIn("以 `result` 为准", apply_text)

    def test_apply_outcome_contract_has_one_complete_source(self) -> None:
        outcomes = (
            "blocked",
            "next",
            "deferred_only",
            "validation_required",
            "validation_recorded",
            "done",
        )
        apply_text = (SKILL_ROOT / "references/apply.md").read_text(encoding="utf-8")
        rows = [
            line
            for line in apply_text.splitlines()
            if line.startswith("| `") and line.count("|") >= 4
        ]
        for outcome in outcomes:
            self.assertTrue(
                any(f"`{outcome}`" in row for row in rows),
                f"apply.md must define outcome {outcome} in the contract table",
            )
        followers = {
            "SKILL.md": (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8"),
            "task-apply.md": (COMMAND_ROOT / "task-apply.md").read_text(encoding="utf-8"),
            "openai.yaml": (SKILL_ROOT / "agents/openai.yaml").read_text(encoding="utf-8"),
        }
        contract_only = ("deferred_only", "validation_required", "validation_recorded")
        for name, text in followers.items():
            for outcome in contract_only:
                self.assertNotIn(
                    outcome,
                    text,
                    f"{name} must point at references/apply.md instead of re-listing outcomes",
                )

    def test_state_ownership_lives_only_in_safety(self) -> None:
        safety = (SKILL_ROOT / "references/safety.md").read_text(encoding="utf-8")
        self.assertIn("## 仓库角色", safety)
        self.assertIn("## 状态所有权", safety)
        for token in ("task_store", ".task-apply-state.json", "reference | 建议/排除仓"):
            self.assertIn(token, safety)
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("safety.md", skill_text)
        for token in ("task_store", ".task-apply-state.json"):
            self.assertNotIn(token, skill_text)

    def test_openspec_delegation_contract_is_pinned_in_references(self) -> None:
        safety = (SKILL_ROOT / "references/safety.md").read_text(encoding="utf-8")
        self.assertIn("PROXY-1", safety)
        self.assertIn("PROXY-2", safety)
        self.assertIn("unsupported_openspec_schema", safety)
        self.assertIn("unsupported_openspec_store", safety)
        for name in ("planning.md", "archive.md"):
            text = (SKILL_ROOT / f"references/{name}").read_text(encoding="utf-8")
            self.assertIn("planning_root", text, name)
            self.assertIn("openspec validate --strict --change", text, name)
        planning = (SKILL_ROOT / "references/planning.md").read_text(encoding="utf-8")
        self.assertIn("canonical planning root", planning)

    def test_schema_assertion_is_implemented_in_taskctl(self) -> None:
        source = TASKCTL_PATH.read_text(encoding="utf-8")
        self.assertIn("unsupported_openspec_schema", source)
        self.assertIn("spec-driven", source)
        self.assertIn("config.yaml", source)

    def test_root_option_is_global_and_documented(self) -> None:
        parser = load_taskctl().build_parser()
        self.assertTrue(
            any(
                "--root" in (action.option_strings or [])
                for action in parser._actions
            )
        )
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("`--root` 在子命令前后均可写", skill_text)
        self.assertIn("值不同即报错", skill_text)

    def test_script_entry_point_is_resolved_once(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("每阶段解析一次", skill_text)
        self.assertIn("command -v taskctl", skill_text)
        self.assertIn("~/.local/bin/", skill_text)
        self.assertEqual(skill_text.count("<this-skill>"), 2)

    def test_delegation_budget_rules_are_pinned(self) -> None:
        safety = (SKILL_ROOT / "references/safety.md").read_text(encoding="utf-8")
        apply_text = (SKILL_ROOT / "references/apply.md").read_text(encoding="utf-8")
        self.assertIn("DELEG-1", safety)
        self.assertIn("DELEG-1", apply_text)
        # 硬规则表只保留可验证部分；不可计量的墙钟/失败次数是 apply.md 的建议。
        self.assertIn("不得因委托失败判 blocked", safety)
        for token in ("墙钟上限", "连续失败上限", "降级", "15 分钟"):
            self.assertNotIn(token, safety, token)
            self.assertIn(token, apply_text, token)
        self.assertIn("必经路径", apply_text)

    def test_apply_rhythm_rules_are_pinned(self) -> None:
        safety = (SKILL_ROOT / "references/safety.md").read_text(encoding="utf-8")
        apply_text = (SKILL_ROOT / "references/apply.md").read_text(encoding="utf-8")
        self.assertIn("APPLY-7", safety)
        self.assertIn("APPLY-1/2/3/4/5/6/7", apply_text)
        self.assertIn("budget.should_report", safety)
        self.assertNotIn("60 分钟", safety)
        for token in ("首轮", "targeted 验证", "不重复审阅"):
            self.assertIn(token, safety, token)
        for token in ("targeted 验证", "5 个 candidate", "60 分钟"):
            self.assertIn(token, apply_text, token)
        self.assertIn("openspec-apply-change", apply_text)

    def test_instruction_footprint_is_below_previous_baseline(self) -> None:
        # Baseline raised from 30_000 once APPLY-7 and DELEG-1 landed; these rules
        # bound scheduling and delegation, so they are worth their instruction cost.
        paths = [SKILL_ROOT / "SKILL.md", *(SKILL_ROOT / "references").glob("*.md")]
        paths.extend(COMMAND_ROOT.glob("task-*.md"))
        total = sum(path.stat().st_size for path in paths)
        self.assertLess(total, 32_000)


if __name__ == "__main__":
    unittest.main()
