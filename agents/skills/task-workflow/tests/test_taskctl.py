#!/usr/bin/env python3
"""Unit tests for taskctl (stdlib unittest)."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "taskctl.py"


def load_taskctl():
    spec = importlib.util.spec_from_file_location("taskctl", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["taskctl"] = mod
    spec.loader.exec_module(mod)
    return mod


tc = load_taskctl()


class TaskctlTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="taskctl-"))
        (self.tmp / "tasks").mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *argv: str) -> tuple[int, dict]:
        from io import StringIO
        from contextlib import redirect_stdout, redirect_stderr

        out = StringIO()
        err = StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = tc.main(["--root", str(self.tmp), *argv])
        payload = json.loads(out.getvalue())
        return code, payload

    def _seed_task(
        self,
        task_id: str,
        slug: str,
        *,
        day: str = "2026-08-01",
        status: str = "draft",
        numbered_dir: bool = True,
        openspec: bool = False,
        scope_block: str = "",
    ) -> Path:
        dirname = f"{task_id}-{slug}" if numbered_dir else slug
        root = self.tmp / "tasks" / day / dirname
        root.mkdir(parents=True)
        openspec_block = ""
        if openspec:
            openspec_block = """
### 关联 OpenSpec

| change | 路径 | 说明 |
|--------|------|------|
| `demo-change` | `openspec/changes/demo-change/` | demo |
"""
        (root / "README.md").write_text(
            f"""# {slug}

**id：** {task_id}
**status：** {status}
**slug：** {slug}
**创建时间：** {day}

## 概述

hello
{scope_block}{openspec_block}
## 验收标准

- [ ] done
""",
            encoding="utf-8",
        )
        return root

    def _write_index(self, next_id: int = 3) -> None:
        active = []
        for readme in sorted((self.tmp / "tasks").glob("*/*/README.md")):
            if "archive" in readme.parts:
                continue
            rel = readme.parent.relative_to(self.tmp).as_posix() + "/"
            text = readme.read_text(encoding="utf-8")
            tid = tc.parse_id_from_readme(text) or "T0000"
            status = tc.parse_status_from_readme(text)
            slug = tc.slug_from_dirname(readme.parent.name)
            link = f"[{rel}](./{rel.removeprefix('tasks/')})"
            active.append(f"| {tid} | {slug} | {link} | {status} | 2026-08-01 |")
        body = "\n".join(
            [
                "---",
                f"next_id: {next_id}",
                "---",
                "",
                "# Tasks Index",
                "",
                "## 活跃",
                "",
                "| ID | 名称 | 路径 | status | 更新 |",
                "|----|------|------|--------|------|",
                *active,
                "",
                "## 已归档",
                "",
                "| ID | 名称 | 路径 | 归档日 |",
                "|----|------|------|--------|",
                "| — | （尚无） | | |",
                "",
            ]
        )
        (self.tmp / "tasks" / "INDEX.md").write_text(body, encoding="utf-8")

    def test_resolve_by_id(self) -> None:
        self._seed_task("T0001", "alpha")
        self._seed_task("T0002", "beta", day="2026-08-02")
        self._write_index()
        code, payload = self._run("resolve", "T0002")
        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["task"]["task_id"], "T0002")
        self.assertEqual(payload["task"]["slug"], "beta")

    def test_resolve_legacy_slug_dir(self) -> None:
        self._seed_task("T0001", "legacy-slug", numbered_dir=False)
        self._write_index(next_id=2)
        code, payload = self._run("resolve", "T0001")
        self.assertEqual(code, 0)
        self.assertEqual(payload["task"]["slug"], "legacy-slug")

    def test_resolve_zero_and_multi(self) -> None:
        self._seed_task("T0001", "alpha")
        self._write_index(next_id=2)
        code, payload = self._run("resolve", "T9999")
        self.assertEqual(code, 2)
        self.assertEqual(payload["result"], "zero")
        self.assertIn("无法确定当前任务", payload["exit_markdown"])

        self._seed_task("T0002", "alpha", day="2026-08-03")  # same slug different id
        self._write_index(next_id=3)
        code, payload = self._run("resolve", "alpha")
        self.assertEqual(code, 2)
        self.assertEqual(payload["result"], "multi")

    def test_set_status(self) -> None:
        self._seed_task("T0001", "alpha")
        self._write_index(next_id=2)
        code, payload = self._run("set-status", "T0001", "exploring")
        self.assertEqual(code, 0)
        self.assertEqual(payload["task"]["status"], "exploring")
        text = (self.tmp / "tasks/2026-08-01/T0001-alpha/README.md").read_text()
        self.assertIn("**status：** exploring", text)
        index = (self.tmp / "tasks/INDEX.md").read_text()
        self.assertIn("| T0001 | alpha |", index)
        self.assertIn("| exploring |", index)

    def test_set_status_designed(self) -> None:
        self._seed_task("T0001", "alpha")
        self._write_index(next_id=2)
        code, payload = self._run("set-status", "T0001", "designed")
        self.assertEqual(code, 0)
        self.assertEqual(payload["task"]["status"], "designed")
        text = (self.tmp / "tasks/2026-08-01/T0001-alpha/README.md").read_text()
        self.assertIn("**status：** designed", text)

    def test_set_status_rejects_unknown(self) -> None:
        self._seed_task("T0001", "alpha")
        self._write_index(next_id=2)
        code, payload = self._run("set-status", "T0001", "designing")
        self.assertEqual(code, 1)
        self.assertIn("invalid status", payload["error"])

    def test_subprocess_io_error_keeps_json_contract(self) -> None:
        (self.tmp / "tasks/INDEX.md").write_bytes(b"\xff\xfe")
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(self.tmp),
                "list",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error_type"], "io_or_process_error")

    def test_new_and_list(self) -> None:
        code, payload = self._run("new", "--slug", "fresh-feature", "--title", "新功能", "--date", "2026-08-12")
        self.assertEqual(code, 0)
        self.assertEqual(payload["task"]["task_id"], "T0001")
        root = self.tmp / "tasks/2026-08-12/T0001-fresh-feature"
        readme = (root / "README.md").read_text(encoding="utf-8")
        self.assertTrue((root / "README.md").is_file())
        self.assertIn("## 现状缺口", readme)
        self.assertIn("建议补齐", readme)
        self.assertIn("### 设计文档", readme)
        self.assertIn("## 工作上下文", readme)
        self.assertIn("worktree", readme)
        index = (self.tmp / "tasks/INDEX.md").read_text()
        self.assertIn("next_id: 2", index)
        code, payload = self._run("list")
        self.assertEqual(code, 0)
        self.assertEqual(len(payload["tasks"]), 1)

    def test_new_rejects_bad_slug(self) -> None:
        code, payload = self._run("new", "--slug", "Bad_Slug")
        self.assertEqual(code, 1)
        self.assertIn("invalid slug", payload["error"])

    def test_slugify_from_text(self) -> None:
        self.assertEqual(
            tc.slugify_from_text(
                "优化 Providers：从 model.dev 拉取 provider/models 信息，Adapter kind"
            ),
            "providers-model-dev-provider-models-adapter",
        )
        self.assertEqual(
            tc.slugify_from_text("Optimize providers from model.dev"),
            "optimize-providers-model-dev",
        )
        with self.assertRaises(tc.TaskError):
            tc.slugify_from_text("增加一键启动脚本")

    def test_new_infers_slug_from_title(self) -> None:
        code, payload = self._run(
            "new",
            "--title",
            "优化 Providers：从 model.dev 拉取 provider/models",
            "--date",
            "2026-08-14",
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["task"]["slug"], "providers-model-dev-provider-models")
        self.assertTrue(
            (self.tmp / "tasks/2026-08-14/T0001-providers-model-dev-provider-models").is_dir()
        )

    def test_new_requires_slug_or_title(self) -> None:
        code, payload = self._run("new")
        self.assertEqual(code, 1)
        self.assertIn("requires --slug or --title", payload["error"])

    def test_archive(self) -> None:
        root = self._seed_task("T0001", "alpha", openspec=True)
        (root / "changes.md").write_text("# changes\n", encoding="utf-8")
        self._write_index(next_id=2)
        code, payload = self._run(
            "archive",
            "T0001",
            "--date",
            "2026-08-20",
            "--allow-active-openspec",
            "--allow-unchecked-acceptance",
            "--allow-missing-verification",
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["result"], "archived")
        dest = self.tmp / "tasks/archive/2026-08-01-T0001-alpha"
        self.assertTrue((dest / "README.md").is_file())
        self.assertFalse(root.exists())
        text = (dest / "README.md").read_text()
        self.assertIn("**status：** archived", text)
        index = (self.tmp / "tasks/INDEX.md").read_text()
        self.assertIn("## 已归档", index)
        self.assertIn("T0001", index)
        self.assertIn("2026-08-20", index)
        # active empty placeholder
        self.assertIn("（尚无）", index)

    def test_archive_requires_changes(self) -> None:
        self._seed_task("T0001", "alpha")
        self._write_index(next_id=2)
        code, payload = self._run("archive", "T0001")
        self.assertEqual(code, 1)
        self.assertIn("changes.md", payload["error"])

    def test_new_rolls_back_scaffold_when_index_write_fails(self) -> None:
        with mock.patch.object(tc, "write_index", side_effect=OSError("disk full")):
            code, payload = self._run("new", "--slug", "rollback-me")
        self.assertEqual(code, 1)
        self.assertEqual(payload["error_type"], "io_or_process_error")
        self.assertFalse(
            (self.tmp / "tasks" / tc.today_str() / "T0001-rollback-me").exists()
        )

    def test_new_rolls_back_directory_when_readme_write_fails(self) -> None:
        with mock.patch.object(
            tc, "atomic_write_text", side_effect=OSError("read-only")
        ):
            code, payload = self._run("new", "--slug", "readme-fail")
        self.assertEqual(code, 1)
        self.assertFalse(
            (self.tmp / "tasks" / tc.today_str() / "T0001-readme-fail").exists()
        )

    def test_archive_rolls_back_move_when_index_write_fails(self) -> None:
        task = self._seed_task("T0001", "rollback")
        (task / "changes.md").write_text("# changes\n", encoding="utf-8")
        (task / "progress.md").write_text(
            "# progress\n\n## 验证证据\n\n- tests passed\n", encoding="utf-8"
        )
        readme = (task / "README.md").read_text(encoding="utf-8")
        (task / "README.md").write_text(
            readme.replace("- [ ] done", "- [x] done"), encoding="utf-8"
        )
        self._write_index(next_id=2)
        with mock.patch.object(tc, "write_index", side_effect=OSError("disk full")):
            code, payload = self._run("archive", "T0001")
        self.assertEqual(code, 1)
        self.assertTrue(task.is_dir())
        self.assertIn(
            "**status：** draft",
            (task / "README.md").read_text(encoding="utf-8"),
        )

    def test_archive_rolls_back_status_when_move_fails(self) -> None:
        task = self._seed_task("T0001", "move-fail")
        (task / "changes.md").write_text("# changes\n", encoding="utf-8")
        (task / "progress.md").write_text(
            "# progress\n\n## 验证证据\n\n- tests passed\n", encoding="utf-8"
        )
        readme = (task / "README.md").read_text(encoding="utf-8")
        (task / "README.md").write_text(
            readme.replace("- [ ] done", "- [x] done"), encoding="utf-8"
        )
        self._write_index(next_id=2)
        with mock.patch.object(tc.shutil, "move", side_effect=OSError("move failed")):
            code, payload = self._run("archive", "T0001")
        self.assertEqual(code, 1)
        self.assertTrue(task.is_dir())
        self.assertIn(
            "**status：** draft",
            (task / "README.md").read_text(encoding="utf-8"),
        )

    def test_archive_dry_run_does_not_append_override_notes(self) -> None:
        task = self._seed_task("T0001", "dry-archive")
        changes = task / "changes.md"
        changes.write_text("# changes\n", encoding="utf-8")
        self._write_index(next_id=2)
        code, payload = self._run(
            "archive",
            "T0001",
            "--dry-run",
            "--allow-unchecked-acceptance",
            "--allow-missing-verification",
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["result"], "dry_run")
        self.assertEqual(changes.read_text(encoding="utf-8"), "# changes\n")

    def test_openspec_parse(self) -> None:
        self._seed_task("T0002", "beta", openspec=True)
        self._write_index()
        code, payload = self._run("resolve", "T0002")
        self.assertEqual(code, 0)
        self.assertEqual(payload["task"]["openspec"][0]["name"], "demo-change")

    def test_checkpoint_persists_apply_state_and_openspec_progress(self) -> None:
        self._seed_task("T0002", "beta", openspec=True)
        change = self.tmp / "openspec/changes/demo-change"
        change.mkdir(parents=True)
        (change / "tasks.md").write_text(
            "- [x] first\n- [ ] second\n", encoding="utf-8"
        )
        self._write_index()
        code, payload = self._run(
            "checkpoint",
            "T0002",
            "--phase",
            "implementing",
            "--change",
            "demo-change",
            "--current-task",
            "second",
            "--completed",
            "first",
            "--next",
            "continue second",
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "in_progress")
        progress = (
            self.tmp / "tasks/2026-08-01/T0002-beta/progress.md"
        ).read_text(encoding="utf-8")
        self.assertIn("| `demo-change` | 1 | 2 | 1 |", progress)
        self.assertIn("当前任务：second", progress)
        readme = (
            self.tmp / "tasks/2026-08-01/T0002-beta/README.md"
        ).read_text(encoding="utf-8")
        self.assertIn("**status：** in_progress", readme)

        code, context = self._run("execution-context", "T0002")
        self.assertEqual(code, 0)
        self.assertEqual(context["targets"][0]["progress"]["remaining"], 1)
        self.assertTrue(context["progress_exists"])

    def test_checkpoint_rolls_back_when_status_index_write_fails(self) -> None:
        task = self._seed_task("T0001", "checkpoint-rollback")
        self._write_index(next_id=2)
        original_index = (self.tmp / "tasks/INDEX.md").read_text(encoding="utf-8")
        with mock.patch.object(tc, "write_index", side_effect=OSError("disk full")):
            code, payload = self._run(
                "checkpoint", "T0001", "--phase", "implementing"
            )
        self.assertEqual(code, 1)
        self.assertFalse((task / "progress.md").exists())
        self.assertIn(
            "**status：** draft",
            (task / "README.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            (self.tmp / "tasks/INDEX.md").read_text(encoding="utf-8"),
            original_index,
        )

    def test_execution_context_rejects_repo_escape(self) -> None:
        task = self._seed_task("T0001", "escape")
        readme = (task / "README.md").read_text(encoding="utf-8")
        readme = readme.replace(
            "## 验收标准",
            """### 关联 OpenSpec

| change | 路径 | 仓库 | store | 说明 |
|--------|------|------|-------|------|
| bad | `openspec/changes/bad` | `../outside` | | bad |

## 验收标准""",
        )
        (task / "README.md").write_text(readme, encoding="utf-8")
        self._write_index(next_id=2)
        code, payload = self._run("execution-context", "T0001")
        self.assertEqual(code, 1)
        self.assertIn("outside workspace", payload["error"])
        code, payload = self._run(
            "checkpoint", "T0001", "--phase", "implementing"
        )
        self.assertEqual(code, 1)
        self.assertIn(
            "**status：** draft",
            (task / "README.md").read_text(encoding="utf-8"),
        )

    def test_archive_rejects_incomplete_archived_openspec(self) -> None:
        task = self._seed_task("T0001", "incomplete-archive", openspec=True)
        archived_change = (
            self.tmp / "openspec/changes/archive/2026-08-14-demo-change"
        )
        archived_change.mkdir(parents=True)
        (archived_change / "tasks.md").write_text(
            "- [x] done\n- [ ] pending\n", encoding="utf-8"
        )
        readme = (task / "README.md").read_text(encoding="utf-8")
        (task / "README.md").write_text(
            readme.replace("- [ ] done", "- [x] done"), encoding="utf-8"
        )
        (task / "changes.md").write_text("# changes\n", encoding="utf-8")
        (task / "progress.md").write_text(
            "# progress\n\n## 验证证据\n\n- tests passed\n", encoding="utf-8"
        )
        self._write_index(next_id=2)
        code, payload = self._run("archive", "T0001")
        self.assertEqual(code, 1)
        self.assertIn("remaining=1", payload["error"])
        self.assertIn("--force-merge", payload["error"])

    def test_classify_checkbox_item(self) -> None:
        self.assertEqual(
            tc.classify_checkbox_item("5.1 Docker multi-stage build 验证"),
            "verification",
        )
        self.assertEqual(
            tc.classify_checkbox_item("6.1 完整 Compose smoke"),
            "verification",
        )
        self.assertEqual(
            tc.classify_checkbox_item("5.3 六服务 healthcheck 与 Compose healthy 验证"),
            "verification",
        )
        self.assertEqual(tc.classify_checkbox_item("运行单元测试"), "verification")
        self.assertEqual(tc.classify_checkbox_item("实现 Fastify API"), "implementation")
        self.assertEqual(
            tc.remaining_kind_of(
                [
                    {"done": True, "kind": "implementation"},
                    {"done": False, "kind": "verification"},
                    {"done": False, "kind": "verification"},
                ]
            ),
            "verification_only",
        )
        self.assertEqual(
            tc.remaining_kind_of(
                [
                    {"done": False, "kind": "implementation"},
                    {"done": False, "kind": "verification"},
                ]
            ),
            "implementation",
        )

    def _seed_archive_ready(self, slug: str, tasks_md: str, *, archived: bool = False) -> Path:
        task = self._seed_task("T0001", slug, openspec=True)
        change = self.tmp / "openspec/changes/demo-change"
        change.mkdir(parents=True)
        (change / "tasks.md").write_text(tasks_md, encoding="utf-8")
        if archived:
            dest = self.tmp / "openspec/changes/archive/2026-08-14-demo-change"
            dest.parent.mkdir(parents=True)
            shutil.move(str(change), str(dest))
        readme = (task / "README.md").read_text(encoding="utf-8")
        (task / "README.md").write_text(
            readme.replace("- [ ] done", "- [x] done"), encoding="utf-8"
        )
        (task / "changes.md").write_text("# changes\n", encoding="utf-8")
        (task / "progress.md").write_text(
            "# progress\n\n## 验证证据\n\n- tests passed\n", encoding="utf-8"
        )
        self._write_index(next_id=2)
        return task

    def test_execution_context_reports_verification_only(self) -> None:
        self._seed_archive_ready(
            "verify-ctx",
            "- [x] 实现 API\n"
            "- [ ] 5.1 Docker multi-stage build 验证\n"
            "- [ ] 6.1 完整 Compose smoke\n",
        )
        code, payload = self._run("execution-context", "T0001")
        self.assertEqual(code, 0)
        self.assertEqual(payload["openspec_remaining"]["kind"], "verification_only")
        self.assertEqual(payload["openspec_remaining"]["complete"], 1)
        self.assertEqual(payload["openspec_remaining"]["total"], 3)
        self.assertEqual(payload["targets"][0]["remaining_kind"], "verification_only")
        texts = [item["text"] for item in payload["openspec_remaining"]["items"]]
        self.assertIn("5.1 Docker multi-stage build 验证", texts)

    def test_archive_confirms_verification_only_remaining(self) -> None:
        self._seed_archive_ready(
            "verify-only",
            "- [x] 实现 API\n- [ ] 最终 runtime/Compose/smoke 验证\n",
        )
        code, payload = self._run("archive", "T0001")
        self.assertEqual(code, 2)
        self.assertEqual(payload["result"], "needs_confirm")
        self.assertEqual(payload["reason"], "verification_only_remaining")
        self.assertIn("只剩测试/验证", payload["exit_markdown"])
        self.assertIn("--force-merge", payload["exit_markdown"])
        self.assertTrue(
            (self.tmp / "tasks/2026-08-01/T0001-verify-only").is_dir()
        )

    def test_archive_force_merge_allows_verification_remaining(self) -> None:
        task = self._seed_archive_ready(
            "force-verify",
            "- [x] 实现 API\n- [ ] 6.1 完整 Compose smoke\n",
        )
        code, payload = self._run("archive", "T0001", "--force-merge")
        self.assertEqual(code, 0)
        self.assertEqual(payload["result"], "archived")
        dest = self.tmp / "tasks/archive/2026-08-01-T0001-force-verify"
        self.assertTrue((dest / "README.md").is_file())
        self.assertFalse(task.exists())
        self.assertIn("强行合并", (dest / "changes.md").read_text(encoding="utf-8"))

    def test_archive_force_merge_allows_implementation_remaining(self) -> None:
        self._seed_archive_ready(
            "force-impl",
            "- [x] done\n- [ ] 实现 billing 模块\n",
            archived=True,
        )
        code, payload = self._run("archive", "T0001")
        self.assertEqual(code, 1)
        self.assertIn("remaining=1", payload["error"])
        code, payload = self._run("archive", "T0001", "--force-merge")
        self.assertEqual(code, 0)
        self.assertEqual(payload["result"], "archived")

    def test_archive_fails_closed_when_recorded_checkout_is_missing(self) -> None:
        self._init_git_repo("svc")
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| svc | `svc` | 必须 |

## 工作上下文

| 仓库 | 仓库路径 | checkout 路径 | worktree | 分支 | 基线 |
|------|----------|---------------|----------|------|------|
| svc | `svc` | `missing-wt` | 是 | `feat-missing` | `main` |
"""
        task = self._seed_task("T0001", "missing", scope_block=scope_block)
        readme = (task / "README.md").read_text(encoding="utf-8")
        (task / "README.md").write_text(
            readme.replace("- [ ] done", "- [x] done"), encoding="utf-8"
        )
        (task / "changes.md").write_text("# changes\n", encoding="utf-8")
        (task / "progress.md").write_text(
            "# progress\n\n## 验证证据\n\n- tests passed\n", encoding="utf-8"
        )
        self._write_index(next_id=2)
        code, payload = self._run("archive", "T0001")
        self.assertEqual(code, 1)
        self.assertIn("missing/invalid task checkout", payload["error"])

    def test_worktree_apply_checkpoint_archive_lifecycle(self) -> None:
        repo = self._init_git_repo("svc")
        code, created = self._run(
            "new", "--slug", "lifecycle", "--title", "Lifecycle", "--date", "2026-08-14"
        )
        self.assertEqual(code, 0)
        task = self.tmp / created["task"]["task_root"]
        readme = (task / "README.md").read_text(encoding="utf-8")
        readme = readme.replace(
            "| （待补） | `path/to/repo`（仅工作区自身是目标时才写 `.`） | 必须 / 建议 / 排除 |",
            "| svc | `svc` | 必须 |",
        ).replace(
            "| — | | | | （尚无） |",
            "| `life-change` | `openspec/changes/life-change` | `svc` | | lifecycle |",
        ).replace("- [ ] （待补）", "- [x] lifecycle works")
        (task / "README.md").write_text(readme, encoding="utf-8")

        wt = self.tmp / "svc-life-wt"
        code, prepared = self._run(
            "prepare-branches",
            "--slug",
            "lifecycle",
            "--from-task",
            "T0001",
            "--worktree",
            "svc=svc-life-wt",
        )
        self.assertEqual(code, 0)
        self.assertEqual(prepared["repos"][0]["action"], "created_worktree")

        change = wt / "openspec/changes/life-change"
        change.mkdir(parents=True)
        (change / "tasks.md").write_text("- [ ] implement\n", encoding="utf-8")
        code, checkpoint = self._run(
            "checkpoint",
            "T0001",
            "--phase",
            "implementing",
            "--change",
            "life-change",
            "--current-task",
            "implement",
        )
        self.assertEqual(code, 0)
        self.assertEqual(checkpoint["targets"][0]["checkout"], "svc-life-wt")
        (change / "tasks.md").write_text("- [x] implement\n", encoding="utf-8")
        code, _ = self._run(
            "checkpoint",
            "T0001",
            "--phase",
            "testing",
            "--change",
            "life-change",
            "--verification",
            "unit tests passed",
        )
        self.assertEqual(code, 0)
        code, _ = self._run(
            "checkpoint",
            "T0001",
            "--phase",
            "done",
            "--change",
            "life-change",
        )
        self.assertEqual(code, 0)
        self.assertIn(
            "unit tests passed",
            (task / "progress.md").read_text(encoding="utf-8"),
        )
        archived_change = wt / "openspec/changes/archive/2026-08-14-life-change"
        archived_change.parent.mkdir(parents=True)
        shutil.move(str(change), str(archived_change))
        self._git(wt, "add", ".")
        self._git(wt, "commit", "-m", "implement lifecycle")
        (task / "changes.md").write_text("# Changes\n", encoding="utf-8")

        code, archived = self._run("archive", "T0001", "--date", "2026-08-14")
        self.assertEqual(code, 0)
        self.assertEqual(archived["result"], "archived")
        self.assertTrue(
            (self.tmp / "tasks/archive/2026-08-14-T0001-lifecycle").is_dir()
        )

    def _git(self, cwd: Path, *args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def _init_git_repo(self, rel: str = "svc") -> Path:
        repo = self.tmp if rel in (".", "") else self.tmp / rel
        repo.mkdir(parents=True, exist_ok=True)
        self._git(repo, "init")
        self._git(repo, "config", "user.email", "t@example.com")
        self._git(repo, "config", "user.name", "tester")
        (repo / "README").write_text("init\n", encoding="utf-8")
        self._git(repo, "add", ".")
        self._git(repo, "commit", "-m", "init")
        self._git(repo, "branch", "-M", "main")
        return repo

    def test_repo_roots_nested_and_workspace(self) -> None:
        self._init_git_repo("svc")
        code, payload = self._run("repo-roots", "svc")
        self.assertEqual(code, 0)
        self.assertTrue(payload["repos"][0]["git_root"].startswith("svc"))
        self.assertFalse(payload["repos"][0]["is_worktree"])
        self.assertIsNone(payload["repos"][0]["main_worktree"])
        code, payload = self._run("repo-roots", "no-such")
        self.assertEqual(code, 1)
        self.assertIn("does not exist", payload["errors"][0]["error"])
        self._init_git_repo(".")
        code, payload = self._run("repo-roots", ".")
        self.assertEqual(code, 0)
        self.assertEqual(payload["repos"][0]["git_root"], "./")

    def test_repo_roots_detects_linked_worktree(self) -> None:
        repo = self._init_git_repo("svc")
        wt = self.tmp / "svc-wt"
        self._git(repo, "worktree", "add", str(wt), "-b", "feat-x")
        code, payload = self._run("repo-roots", "svc-wt")
        self.assertEqual(code, 0)
        info = payload["repos"][0]
        self.assertTrue(info["is_worktree"])
        self.assertEqual(info["main_worktree"], "svc")
        code, payload = self._run("repo-roots", "svc")
        self.assertEqual(code, 0)
        self.assertFalse(payload["repos"][0]["is_worktree"])

    def test_prepare_branches_creates_branch_inside_selected_worktree(self) -> None:
        repo = self._init_git_repo("svc")
        wt = self.tmp / "svc-wt"
        self._git(repo, "worktree", "add", str(wt), "-b", "feat-old")
        code, payload = self._run(
            "prepare-branches",
            "--slug",
            "new-task",
            "--repo",
            "svc",
            "--worktree",
            "svc=svc-wt",
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["repos"][0]["checkout"], "svc-wt")
        self.assertTrue(payload["repos"][0]["is_worktree"])
        self.assertEqual(
            subprocess.run(
                ["git", "-C", str(wt), "branch", "--show-current"],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout.strip(),
            "feat-new-task",
        )
        self.assertEqual(
            subprocess.run(
                ["git", "-C", str(repo), "branch", "--show-current"],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout.strip(),
            "main",
        )

    def test_prepare_branches_reuses_recorded_worktree_and_persists(self) -> None:
        repo = self._init_git_repo("svc")
        wt = self.tmp / "svc-wt"
        self._git(repo, "worktree", "add", str(wt), "-b", "feat-demo")
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| svc | `svc` | 必须 |

## 工作上下文

| 仓库 | 仓库路径 | checkout 路径 | worktree | 分支 | 基线 |
|------|----------|---------------|----------|------|------|
| svc | `svc` | `svc-wt` | 是 | `feat-demo` | `main` |
"""
        task = self._seed_task("T0001", "demo", scope_block=scope_block)
        self._write_index(next_id=2)
        code, payload = self._run(
            "prepare-branches", "--slug", "demo", "--from-task", "T0001"
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["repos"][0]["action"], "already_on_branch")
        self.assertEqual(payload["repos"][0]["checkout"], "svc-wt")
        readme = (task / "README.md").read_text(encoding="utf-8")
        self.assertIn("`svc-wt`", readme)

    def test_prepare_branches_dry_run_does_not_persist_context(self) -> None:
        self._init_git_repo("svc")
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| svc | `svc` | 必须 |
"""
        task = self._seed_task("T0001", "dry-demo", scope_block=scope_block)
        self._write_index(next_id=2)
        before = (task / "README.md").read_text(encoding="utf-8")
        code, payload = self._run(
            "prepare-branches",
            "--slug",
            "dry-demo",
            "--from-task",
            "T0001",
            "--dry-run",
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["repos"][0]["action"], "would_create")
        self.assertEqual((task / "README.md").read_text(encoding="utf-8"), before)

    def test_prepare_branches_blocks_configured_origin_fetch_failure(self) -> None:
        repo = self._init_git_repo("svc")
        self._git(repo, "remote", "add", "origin", str(self.tmp / "missing-origin"))
        code, payload = self._run(
            "prepare-branches", "--slug", "x", "--repo", "svc"
        )
        self.assertEqual(code, 1)
        self.assertEqual(payload["errors"][0]["action"], "blocked_fetch")

    def test_prepare_branches_create_and_idempotent(self) -> None:
        repo = self._init_git_repo("svc")
        code, payload = self._run(
            "prepare-branches",
            "--slug",
            "demo-feature",
            "--repo",
            "svc",
            "--dry-run",
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["repos"][0]["action"], "would_create")
        self.assertEqual(payload["branch"], "feat-demo-feature")

        code, payload = self._run(
            "prepare-branches",
            "--slug",
            "demo-feature",
            "--repo",
            "svc",
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["repos"][0]["action"], "created")
        cur = subprocess.run(
            ["git", "-C", str(repo), "branch", "--show-current"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
        self.assertEqual(cur, "feat-demo-feature")

        code, payload = self._run(
            "prepare-branches",
            "--slug",
            "demo-feature",
            "--repo",
            "svc",
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["repos"][0]["action"], "already_on_branch")

    def test_prepare_branches_blocks_dirty(self) -> None:
        repo = self._init_git_repo("svc")
        (repo / "dirty.txt").write_text("x\n", encoding="utf-8")
        code, payload = self._run(
            "prepare-branches",
            "--slug",
            "x",
            "--repo",
            "svc",
        )
        self.assertEqual(code, 1)
        self.assertEqual(payload["errors"][0]["action"], "blocked_dirty")

        code, payload = self._run(
            "prepare-branches",
            "--slug",
            "x",
            "--repo",
            "svc",
            "--skip-dirty",
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["repos"][0]["action"], "skipped_dirty")

    def test_prepare_branches_already_on_branch_allows_dirty(self) -> None:
        repo = self._init_git_repo("svc")
        self._git(repo, "checkout", "-b", "feat-x")
        (repo / "dirty.txt").write_text("x\n", encoding="utf-8")
        code, payload = self._run(
            "prepare-branches",
            "--slug",
            "x",
            "--repo",
            "svc",
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["repos"][0]["action"], "already_on_branch")
        self.assertTrue(payload["repos"][0].get("dirty"))

    def test_git_summary(self) -> None:
        repo = self._init_git_repo("svc")
        self._git(repo, "checkout", "-b", "feat-sum")
        (repo / "a.txt").write_text("a\n", encoding="utf-8")
        self._git(repo, "add", ".")
        self._git(repo, "commit", "-m", "add a")
        (repo / "wip.txt").write_text("wip\n", encoding="utf-8")
        code, payload = self._run(
            "git-summary",
            "--repo",
            "svc",
            "--branch",
            "feat-sum",
            "--base",
            "main",
        )
        self.assertEqual(code, 0)
        self.assertTrue(payload["repos"][0]["commits"])
        self.assertTrue(any(f["path"] == "a.txt" for f in payload["repos"][0]["files"]))
        self.assertTrue(
            any(
                f["path"] == "wip.txt" and f["source"] == "untracked"
                for f in payload["repos"][0]["files"]
            )
        )
        self.assertIn("svc/a.txt", payload["markdown"])

    def test_infer_sole_active(self) -> None:
        self._seed_task("T0001", "only-one")
        self._write_index(next_id=2)
        code, payload = self._run("resolve", "--command", "task-apply", "--infer")
        self.assertEqual(code, 0)
        self.assertEqual(payload["reason"], "sole_active")
        self.assertEqual(payload["task"]["task_id"], "T0001")

    def test_infer_hint_id(self) -> None:
        self._seed_task("T0001", "alpha")
        self._seed_task("T0002", "beta", day="2026-08-02", status="in_progress")
        self._write_index()
        code, payload = self._run(
            "resolve",
            "--command",
            "task-apply",
            "--hint",
            "继续做 T0002 的实施",
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["reason"], "hint_id")
        self.assertEqual(payload["task"]["task_id"], "T0002")

    def test_infer_cwd(self) -> None:
        root = self._seed_task("T0001", "alpha")
        self._seed_task("T0002", "beta", day="2026-08-02")
        self._write_index()
        code, payload = self._run(
            "resolve",
            "--command",
            "task-explore",
            "--cwd",
            str(root),
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["reason"], "cwd_task")
        self.assertEqual(payload["task"]["task_id"], "T0001")

    def test_infer_git_branch(self) -> None:
        self._seed_task("T0001", "alpha")
        self._seed_task("T0002", "beta-thing", day="2026-08-02")
        self._write_index()
        code, payload = self._run(
            "resolve",
            "--command",
            "task-apply",
            "--git-branch",
            "feat-beta-thing",
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["reason"], "git_branch")
        self.assertEqual(payload["task"]["task_id"], "T0002")

    def test_infer_heuristic_needs_confirm(self) -> None:
        self._seed_task("T0001", "alpha", status="draft")
        self._seed_task("T0002", "beta", day="2026-08-02", status="in_progress")
        self._write_index()
        code, payload = self._run("resolve", "--command", "task-apply")
        self.assertEqual(code, 2)
        self.assertEqual(payload["result"], "needs_confirm")
        self.assertEqual(payload["confidence"], "heuristic")
        self.assertEqual(payload["candidates"][0]["task"]["task_id"], "T0002")
        self.assertIn("请确认", payload["exit_markdown"])

    def test_parse_scope_must_only_and_skips_placeholder(self) -> None:
        text = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| （待补） | `.` 或 `path/to/repo` | 必须 / 建议 / 排除 |
| svc | `svc` | 必须 |
| notes | `notes` | 建议 |
| vendor | `vendor` | 排除 |
"""
        scope = tc.parse_scope(text)
        self.assertEqual(scope["checkout"], ["svc"])
        self.assertEqual([r["path"] for r in scope["must"]], ["svc"])
        self.assertEqual([r["path"] for r in scope["suggested"]], ["notes"])
        self.assertEqual([r["path"] for r in scope["excluded"]], ["vendor"])

    def test_prepare_branches_requires_explicit_repo(self) -> None:
        code, payload = self._run("prepare-branches", "--slug", "x")
        self.assertEqual(code, 1)
        self.assertFalse(payload["ok"])
        self.assertIn("do not default to cwd", payload["error"])

    def test_prepare_branches_from_task_skips_unrelated_and_cwd(self) -> None:
        target = self._init_git_repo("svc")
        other = self._init_git_repo("other")
        workspace = self._init_git_repo(".")
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| svc | `svc` | 必须 |
| notes | `other` | 建议 |
"""
        self._seed_task("T0001", "demo-feature", scope_block=scope_block)
        self._write_index(next_id=2)
        code, payload = self._run(
            "prepare-branches",
            "--slug",
            "demo-feature",
            "--from-task",
            "T0001",
            "--cwd",
            str(workspace),
        )
        self.assertEqual(code, 0)
        self.assertEqual(len(payload["repos"]), 1)
        self.assertEqual(payload["repos"][0]["git_root"].rstrip("/"), "svc")
        self.assertEqual(payload["repos"][0]["action"], "created")
        self.assertTrue(payload["cwd_untouched"])
        self.assertFalse(payload["cwd_in_targets"])
        self.assertEqual(
            subprocess.run(
                ["git", "-C", str(target), "branch", "--show-current"],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout.strip(),
            "feat-demo-feature",
        )
        self.assertEqual(
            subprocess.run(
                ["git", "-C", str(other), "branch", "--show-current"],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout.strip(),
            "main",
        )
        self.assertEqual(
            subprocess.run(
                ["git", "-C", str(workspace), "branch", "--show-current"],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout.strip(),
            "main",
        )

    def test_prepare_branches_from_task_empty_skips(self) -> None:
        workspace = self._init_git_repo(".")
        self._seed_task("T0001", "no-target")
        self._write_index(next_id=2)
        code, payload = self._run(
            "prepare-branches",
            "--slug",
            "no-target",
            "--from-task",
            "T0001",
            "--cwd",
            str(workspace),
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["skipped"], "no_target_repos")
        self.assertEqual(payload["repos"], [])
        self.assertTrue(payload["cwd_untouched"])
        self.assertEqual(
            subprocess.run(
                ["git", "-C", str(workspace), "branch", "--show-current"],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout.strip(),
            "main",
        )

    def test_scope_repos_checkout_must_only(self) -> None:
        self._init_git_repo("svc")
        self._init_git_repo("other")
        workspace = self._init_git_repo(".")
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| svc | `svc` | 必须 |
| notes | `other` | 建议 |
"""
        self._seed_task("T0001", "demo-feature", scope_block=scope_block)
        self._write_index(next_id=2)
        code, payload = self._run(
            "scope-repos",
            "T0001",
            "--cwd",
            str(workspace),
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["checkout"], ["svc"])
        self.assertTrue(payload["cwd_untouched"])

    def test_prepare_branches_dirty_asks_confirm(self) -> None:
        repo = self._init_git_repo("svc")
        (repo / "dirty.txt").write_text("x\n", encoding="utf-8")
        code, payload = self._run(
            "prepare-branches",
            "--slug",
            "x",
            "--repo",
            "svc",
        )
        self.assertEqual(code, 1)
        self.assertTrue(payload["needs_user_confirm"])
        self.assertTrue(payload["errors"][0]["user_actions"])
        self.assertIn("确认", payload["exit_markdown"])

    def test_notes_missing_then_init(self) -> None:
        code, payload = self._run("notes")
        self.assertEqual(code, 0)
        self.assertFalse(payload["exists"])
        self.assertEqual(payload["result"], "missing")
        self.assertEqual(payload["path"], ".task-workflow.md")

        code, payload = self._run("notes", "--init")
        self.assertEqual(code, 0)
        self.assertEqual(payload["result"], "created")
        self.assertTrue(payload["exists"])
        path = self.tmp / ".task-workflow.md"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("## 特殊要求", text)
        self.assertIn("## 规格说明", text)
        self.assertIn("## 默认涉及面", text)

        code, payload = self._run("notes", "--init")
        self.assertEqual(code, 0)
        self.assertEqual(payload["result"], "exists")
        self.assertEqual(path.read_text(encoding="utf-8"), text)

    def test_notes_set_section_and_from_file(self) -> None:
        code, payload = self._run(
            "notes",
            "--set-section",
            "特殊要求",
            "--body",
            "- 验收必须带回归清单",
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["result"], "created")
        self.assertTrue(payload["exists"])
        text = (self.tmp / ".task-workflow.md").read_text(encoding="utf-8")
        self.assertIn("- 验收必须带回归清单", text)
        self.assertIn("## 规格说明", text)

        code, payload = self._run(
            "notes",
            "--set-section",
            "特殊要求",
            "--body",
            "- 禁止提交密钥",
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["result"], "updated")
        text = (self.tmp / ".task-workflow.md").read_text(encoding="utf-8")
        self.assertIn("- 禁止提交密钥", text)
        self.assertNotIn("回归清单", text)
        self.assertIn("## 规格说明", text)

        src = self.tmp / "notes-in.md"
        src.write_text("# 自定义\n\n## 规格说明\n\n- OpenSpec 落在目标仓\n", encoding="utf-8")
        code, payload = self._run("notes", "--from-file", str(src))
        self.assertEqual(code, 0)
        self.assertEqual(payload["result"], "updated")
        self.assertIn("OpenSpec 落在目标仓", payload["markdown"])
        headings = [s["heading"] for s in payload["sections"]]
        self.assertIn("规格说明", headings)

    def test_notes_parse_default_scope_and_new_prefill(self) -> None:
        (self.tmp / ".task-workflow.md").write_text(
            """# 任务工作流

## 默认涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| svc | `svc` | 必须 |
| notes | `other` | 建议 |
""",
            encoding="utf-8",
        )
        code, payload = self._run("notes")
        self.assertEqual(code, 0)
        self.assertEqual(payload["scope"]["checkout"], ["svc"])
        self.assertEqual(payload["scope"]["suggested"][0]["path"], "other")

        code, payload = self._run("new", "--slug", "from-notes", "--date", "2026-08-14")
        self.assertEqual(code, 0)
        self.assertTrue(payload["workflow_notes"]["exists"])
        readme = (self.tmp / "tasks/2026-08-14/T0001-from-notes/README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("| svc | `svc` | 必须 |", readme)
        self.assertIn("| notes | `other` | 建议 |", readme)
        self.assertNotIn("（待补）", readme.split("### 涉及面", 1)[1].split("### 关联", 1)[0])

    def test_resolve_includes_workflow_notes(self) -> None:
        self._seed_task("T0001", "alpha")
        self._write_index(next_id=2)
        (self.tmp / ".task-workflow.md").write_text(
            "## 特殊要求\n\n- 分支前缀用 feat\n",
            encoding="utf-8",
        )
        code, payload = self._run("resolve", "T0001")
        self.assertEqual(code, 0)
        self.assertTrue(payload["workflow_notes"]["exists"])
        self.assertIn("分支前缀用 feat", payload["workflow_notes"]["markdown"])


if __name__ == "__main__":
    unittest.main()
