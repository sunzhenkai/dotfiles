"""SKILL.md / references 与 CLI 的一致性契约。

目的是防止文档和实现漂移，以及防止复杂度悄悄长回来（指令面、命令数、并行进度源）。
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SKILL_ROOT = ROOT / "agents/skills/task-workflow"
TASKCTL_PATH = SKILL_ROOT / "scripts/taskctl.py"

EXPECTED_COMMANDS = {
    "new",
    "list",
    "resolve",
    "status",
    "validate-round-end",
    "set-status",
    "prepare-branches",
    "archive",
    "restore",
    "notes",
    "sync-index",
}

# 被移除的调度器接口；重新出现说明第二套 apply 流程或并行状态源回来了。
REMOVED_COMMANDS = {
    "advance",
    "execution-context",
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


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class SkillContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.skill = read(SKILL_ROOT / "SKILL.md")
        self.refs = {
            path.name: read(path) for path in (SKILL_ROOT / "references").glob("*.md")
        }

    # ---- 指令面 ---------------------------------------------------------- #

    def test_reference_set_is_bounded(self) -> None:
        self.assertEqual(
            set(self.refs), {"planning.md", "apply.md", "archive.md", "safety.md"}
        )

    def test_instruction_surface_stays_small(self) -> None:
        """SKILL.md 加四份 reference 的总行数设上限，避免规则再度膨胀。"""
        total = len(self.skill.splitlines()) + sum(
            len(body.splitlines()) for body in self.refs.values()
        )
        self.assertLess(total, 320, f"instruction surface grew to {total} lines")

    # ---- CLI 与文档一致 -------------------------------------------------- #

    def test_public_taskctl_commands_are_converged(self) -> None:
        parser = load_taskctl().build_parser()
        subparsers = next(
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        )
        self.assertEqual(set(subparsers.choices), EXPECTED_COMMANDS)
        self.assertTrue(REMOVED_COMMANDS.isdisjoint(subparsers.choices))

    def test_round_end_confirmation_flag_is_pinned(self) -> None:
        parser = load_taskctl().build_parser()
        subparsers = next(
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        )
        validate = subparsers.choices["validate-round-end"]
        options = {option for action in validate._actions for option in action.option_strings}
        self.assertIn("--confirm-blockers", options)

    def test_skill_documents_exactly_the_real_commands(self) -> None:
        taskctl_section = self.skill.split("## taskctl", 1)[1].split("\n## ", 1)[0]
        documented = set(re.findall(r"^\| `([a-z-]+)` \|", taskctl_section, re.MULTILINE))
        self.assertEqual(documented, EXPECTED_COMMANDS)

    def test_removed_scheduler_is_absent_from_instructions(self) -> None:
        haystack = self.skill + "".join(self.refs.values())
        for token in ("execution-context", "advance --phase", "deferred_only", "validation_recorded"):
            self.assertNotIn(token, haystack, f"{token} should be gone")

    def test_exit_codes_are_documented_once(self) -> None:
        self.assertIn("退出码", self.skill)
        # 门禁语义只在 safety.md 定义，不在别处复制规则表。
        self.assertIn("| ID |", self.refs["safety.md"])
        for name, body in self.refs.items():
            if name != "safety.md":
                self.assertNotIn("| ID |", body, f"{name} duplicates the safety table")

    # ---- 单一进度真相 ---------------------------------------------------- #

    def test_checkbox_is_declared_the_only_progress_truth(self) -> None:
        self.assertIn("checkbox", self.skill)
        self.assertIn("PROG-1", self.refs["safety.md"])
        for token in ("progress.md", ".task-apply-state.json"):
            self.assertNotIn(
                token, self.skill + "".join(self.refs.values()), f"{token} is retired"
            )

    def test_apply_reference_owns_the_reporting_templates(self) -> None:
        apply_md = self.refs["apply.md"]
        # 汇报点与本轮终止必须是两套模板，否则汇报会被当成收尾。
        self.assertIn("### 进行中", apply_md)
        self.assertIn("### 本轮结束", apply_md)
        self.assertIn("### 完成", apply_md)
        self.assertNotIn("汇报模板", self.refs["planning.md"])

    # ---- apply 调度不得提前停摆 ------------------------------------------ #

    def test_apply_round_end_conditions_are_pinned(self) -> None:
        apply_md = self.refs["apply.md"]
        self.assertIn("APPLY-1", self.refs["safety.md"])
        self.assertIn("## 本轮结束条件", apply_md)
        for token in ("需要用户决策", "全局故障", "都不是结束理由"):
            self.assertIn(token, apply_md, f"missing round-end condition: {token}")
        # 汇报点是继续点，不是交回控制权的地方。
        self.assertIn("立即继续", apply_md)
        # 做不完必须有诚实出口，否则只能被迫谎报暂缓。
        for body in (apply_md, self.refs["safety.md"]):
            self.assertIn("本轮预算耗尽", body)
        self.assertIn("续跑锚点", apply_md)

    def test_deferral_does_not_cascade_across_changes(self) -> None:
        self.assertIn("APPLY-2", self.refs["safety.md"])
        self.assertIn("后续 change 中不依赖它的项", self.refs["safety.md"])
        apply_md = self.refs["apply.md"]
        self.assertIn("不是串行门", apply_md)
        self.assertIn("继续下一项", apply_md)

    def test_deferral_must_be_itemized(self) -> None:
        self.assertIn("APPLY-3", self.refs["safety.md"])
        apply_md = self.refs["apply.md"]
        # 暂缓与未判定是两种身份，报告必须分开。
        self.assertIn("未判定剩余", apply_md)
        self.assertIn("checkbox 原文", apply_md)
        for token in ("行数必须等于", "不要编原因"):
            self.assertIn(token, apply_md, f"apply.md 缺少逐项化约束: {token}")
        # 按 change 汇总数量冒充暂缓，是本规则要拦的形态。
        self.assertIn("冒充暂缓", apply_md)

    def test_round_end_validation_is_mandatory(self) -> None:
        apply_md = self.refs["apply.md"]
        safety = self.refs["safety.md"]
        for token in ("validate-round-end", "all-deferred", "budget-exhausted"):
            self.assertIn(token, apply_md)
        self.assertIn("APPLY-4", safety)
        for token in (
            "<kind>:<stable-id>",
            "transitive_deferral",
            "confirm_args",
            "blocker_confirmation_stale",
            "global_block_confirmed",
        ):
            self.assertIn(token, apply_md, f"apply.md missing round-end contract: {token}")
        for token in ("退出码 2", "task-level success", "set-status <id> in_progress"):
            self.assertIn(token, apply_md)
        for token in ("<kind>:<stable-id>", "confirm_args", "global_block_confirmed"):
            self.assertIn(token, safety)
        for removed in ("task_internal_responsibility", "cascade_suspected", "identity_split_suspected"):
            self.assertNotIn(removed, apply_md + safety)
        self.assertIn("全局阻塞", apply_md)
        self.assertNotIn("或余下每一项都已逐项", apply_md)

    # ---- 安全规则可追溯 -------------------------------------------------- #

    def test_safety_rules_reference_existing_tests(self) -> None:
        safety = self.refs["safety.md"]
        rule_ids = set(re.findall(r"^\| (\w+-\d+) \|", safety, re.MULTILINE))
        self.assertTrue(rule_ids, "safety table has no rule ids")

        suite = read(Path(__file__).parent / "test_taskctl.py") + read(
            Path(__file__)
        )
        for name in re.findall(r"`(test_\w+)`", safety):
            self.assertIn(f"def {name}", suite, f"{name} referenced but not defined")

    def test_openspec_delegation_contract_is_pinned(self) -> None:
        for name in ("planning.md", "archive.md"):
            body = self.refs[name]
            self.assertIn("planning_root", body)
            self.assertIn("change name", body)
        self.assertIn("openspec validate --strict", self.refs["planning.md"])

    def test_openspec_cli_flags_match_installed_cli(self) -> None:
        # openspec 1.6.0 起 validate 用 `--type change <name>`；`--change` 已被拒绝。
        for name, body in self.refs.items():
            self.assertNotIn(
                "--strict --change",
                body,
                f"{name} 仍在用已废弃的 `openspec validate --strict --change`",
            )
        for body in (self.refs["planning.md"], self.refs["safety.md"], self.refs["archive.md"]):
            self.assertIn("--strict --type change", body)

    def test_archive_has_cli_path_and_failure_recovery(self) -> None:
        archive = self.refs["archive.md"]
        # 外部归档不得依赖目标仓未必生成的 openspec-* skill。
        self.assertIn("openspec archive --yes", archive)
        self.assertIn("--skip-specs", archive)
        for token in ("已预同步", "逐字相同", "失败与续跑", "Aborted. No files were changed."):
            self.assertIn(token, archive, f"archive.md 缺少失败恢复要素: {token}")
        # skill 不可用时必须停下报告，而不是自行发明命令。
        self.assertIn("不要自行发明等价命令", self.refs["planning.md"])

    def test_archive_gate_asks_instead_of_exiting(self) -> None:
        archive = self.refs["archive.md"]
        # 退出码 2 是待确认；当成失败会让没做完的 task 永远归不了档。
        self.assertIn("待确认，不是失败", archive)
        self.assertIn("继续归档还是先补完", archive)
        self.assertIn("待确认", self.refs["safety.md"])

    def test_archive_gate_release_is_a_single_confirmation(self) -> None:
        archive = self.refs["archive.md"]
        # 按 gate 拆 flag 会让调用方一轮一轮地往上堆参数，最后变成无脑放行。
        for flag in ("--allow-remaining", "--allow-unchecked-acceptance", "--allow-dirty"):
            self.assertNotIn(flag, archive)
            self.assertNotIn(flag, read(TASKCTL_PATH))
        self.assertIn("--confirmed", archive)
        self.assertIn("--confirmed", self.refs["safety.md"])
        # 一次放行全部 gate，所以事后对账只剩 changes.md 一处。
        self.assertIn("门禁覆盖", archive)

    def test_archive_delta_diagnosis_is_section_aware(self) -> None:
        archive = self.refs["archive.md"]
        self.assertIn("ARCH-2", self.refs["safety.md"])
        # MODIFIED 的正常待归档状态就是主 spec 里正文不同；
        # 按「正文相同才算已同步」一刀切会把最健康的 change 判成冲突。
        self.assertIn("不同才正常", archive)
        self.assertNotIn("标题相同但正文不同", archive)
        for section in ("ADDED", "MODIFIED", "REMOVED", "RENAMED"):
            self.assertIn(f"| {section} |", archive)
        # 判定权归 openspec：先跑归档，报错才手工比对。
        self.assertIn("先跑、报错再分诊", archive)

    def test_scope_roles_are_the_only_three(self) -> None:
        taskctl = load_taskctl()
        self.assertEqual(set(taskctl.ROLE_TO_KEY), {"必须", "建议", "排除"})
        self.assertIn("必须", self.refs["safety.md"])


if __name__ == "__main__":
    unittest.main()
