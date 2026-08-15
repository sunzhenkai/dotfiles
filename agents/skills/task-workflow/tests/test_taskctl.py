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
from contextlib import redirect_stderr
from io import StringIO
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

    def _write_fresh_progress(self, task: Path) -> None:
        readme = (task / "README.md").read_text(encoding="utf-8")
        snapshots = []
        for binding in tc.parse_work_context(readme):
            checkout = tc.resolve_checkout_path(self.tmp, str(binding["checkout"]))
            if checkout.is_dir() and tc.current_branch(checkout) == binding["branch"]:
                snapshots.append(
                    f"- repo=`{binding['repo']}` checkout=`{tc.display_checkout_path(self.tmp, checkout)}` "
                    f"branch=`{binding['branch']}` head=`{tc.git_head(checkout)}`"
                )
        text = (
            "# progress\n\n## 验证证据\n\n- tests passed\n\n"
            "## 最终验证快照\n\n- 状态：`fresh`\n"
            "- 说明：test fixture\n"
            + ("\n".join(snapshots) + "\n" if snapshots else "")
        )
        (task / "progress.md").write_text(text, encoding="utf-8")

    def _mark_archive_ready(self, task: Path) -> None:
        readme = (task / "README.md").read_text(encoding="utf-8")
        (task / "README.md").write_text(
            readme.replace("- [ ] done", "- [x] done"), encoding="utf-8"
        )
        (task / "changes.md").write_text("# changes\n", encoding="utf-8")
        self._write_fresh_progress(task)

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

    def test_resolve_reports_archived_match_and_restore(self) -> None:
        task = self._seed_task("T0001", "archived-alpha")
        self._mark_archive_ready(task)
        self._write_index(next_id=2)
        code, archived = self._run("archive", "T0001", "--date", "2026-08-20")
        self.assertEqual(code, 0)

        code, payload = self._run("resolve", "T0001", "--command", "task-apply")
        self.assertEqual(code, 2)
        self.assertEqual(payload["result"], "archived_match")
        self.assertEqual(payload["reason"], "task_archived")
        self.assertEqual(payload["archived_match"]["task_id"], "T0001")
        self.assertEqual(payload["restore_command"], "taskctl restore T0001")
        self.assertIn("任务已归档", payload["exit_markdown"])

        code, restored = self._run("restore", "T0001")
        self.assertEqual(code, 0)
        self.assertEqual(restored["result"], "restored")
        self.assertEqual(restored["status"], "in_progress")
        active = self.tmp / "tasks/2026-08-01/T0001-archived-alpha"
        self.assertTrue(active.is_dir())
        self.assertIn(
            "**status：** in_progress",
            (active / "README.md").read_text(encoding="utf-8"),
        )
        code, resolved = self._run("resolve", "T0001", "--command", "task-apply")
        self.assertEqual(code, 0)
        self.assertEqual(resolved["task"]["status"], "in_progress")

    def test_restore_rolls_back_move_and_status_when_index_write_fails(self) -> None:
        task = self._seed_task("T0001", "restore-rollback")
        self._mark_archive_ready(task)
        self._write_index(next_id=2)
        code, archived = self._run("archive", "T0001")
        self.assertEqual(code, 0)
        archive_dir = self.tmp / archived["to"].rstrip("/")
        original_index = (self.tmp / "tasks/INDEX.md").read_text(encoding="utf-8")

        with mock.patch.object(tc, "write_index", side_effect=OSError("disk full")):
            code, payload = self._run("restore", "T0001")
        self.assertEqual(code, 1)
        self.assertTrue(archive_dir.is_dir())
        self.assertFalse(
            (self.tmp / "tasks/2026-08-01/T0001-restore-rollback").exists()
        )
        self.assertIn(
            "**status：** archived",
            (archive_dir / "README.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            (self.tmp / "tasks/INDEX.md").read_text(encoding="utf-8"),
            original_index,
        )

    def test_restore_without_index_uses_archive_scan(self) -> None:
        task = self._seed_task("T0001", "scan-only")
        archive_dir = self.tmp / "tasks/archive/2026-08-01-T0001-scan-only"
        archive_dir.parent.mkdir(parents=True)
        readme = (task / "README.md").read_text(encoding="utf-8")
        (task / "README.md").write_text(
            tc.set_readme_status(readme, "archived"), encoding="utf-8"
        )
        shutil.move(str(task), str(archive_dir))

        code, payload = self._run("restore", "T0001")
        self.assertEqual(code, 0)
        self.assertEqual(payload["result"], "restored")
        active = self.tmp / "tasks/2026-08-01/T0001-scan-only"
        self.assertTrue(active.is_dir())
        index = (self.tmp / "tasks/INDEX.md").read_text()
        self.assertIn("T0001", index)
        self.assertIn("next_id: 2", index)
        code, created = self._run("new", "--slug", "next-task")
        self.assertEqual(code, 0)
        self.assertEqual(created["task"]["task_id"], "T0002")

    def test_restore_without_index_preserves_other_archived_rows(self) -> None:
        for task_id, slug in (("T0001", "restore-me"), ("T0009", "keep-me")):
            task = self._seed_task(task_id, slug)
            archive_dir = self.tmp / f"tasks/archive/2026-08-01-{task_id}-{slug}"
            archive_dir.parent.mkdir(parents=True, exist_ok=True)
            readme = (task / "README.md").read_text(encoding="utf-8")
            (task / "README.md").write_text(
                tc.set_readme_status(readme, "archived"), encoding="utf-8"
            )
            shutil.move(str(task), str(archive_dir))

        code, restored = self._run("restore", "T0001")
        self.assertEqual(code, 0)
        self.assertEqual(restored["result"], "restored")
        code, archived = self._run("list", "--archived")
        self.assertEqual(code, 0)
        self.assertEqual([row["task_id"] for row in archived["tasks"]], ["T0009"])
        code, created = self._run("new", "--slug", "next-task")
        self.assertEqual(code, 0)
        self.assertEqual(created["task"]["task_id"], "T0010")

    def test_restore_rejects_active_slug_conflict(self) -> None:
        archived_task = self._seed_task("T0001", "same-slug")
        archive_dir = self.tmp / "tasks/archive/2026-08-01-T0001-same-slug"
        archive_dir.parent.mkdir(parents=True)
        readme = (archived_task / "README.md").read_text(encoding="utf-8")
        (archived_task / "README.md").write_text(
            tc.set_readme_status(readme, "archived"), encoding="utf-8"
        )
        shutil.move(str(archived_task), str(archive_dir))
        self._seed_task("T0002", "same-slug", day="2026-08-02")
        self._write_index(next_id=3)

        code, payload = self._run("restore", "T0001")
        self.assertEqual(code, 1)
        self.assertIn("active task slug already exists", payload["error"])
        self.assertTrue(archive_dir.is_dir())

    def test_restore_reports_rollback_failure(self) -> None:
        task = self._seed_task("T0001", "rollback-visible")
        self._mark_archive_ready(task)
        self._write_index(next_id=2)
        code, archived = self._run("archive", "T0001")
        self.assertEqual(code, 0)
        real_move = shutil.move
        calls = 0

        def fail_move_back(src, dest):
            nonlocal calls
            calls += 1
            if calls == 1:
                return real_move(src, dest)
            raise OSError("cannot move back")

        with mock.patch.object(tc, "write_index", side_effect=OSError("disk full")), mock.patch.object(
            tc.shutil, "move", side_effect=fail_move_back
        ):
            code, payload = self._run("restore", "T0001")
        self.assertEqual(code, 1)
        self.assertIn("rollback_failed", payload["error"])
        self.assertIn("cannot move back", payload["error"])

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
        self.assertIn("apply 前尚未准备", readme)
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

    def test_new_cjk_title_asks_for_explicit_slug(self) -> None:
        code, payload = self._run("new", "--title", "在本地起一套完整的测试服务")
        self.assertEqual(code, 1)
        self.assertIn("--slug", payload["error"])

    def test_archive(self) -> None:
        root = self._seed_task("T0001", "alpha")
        (root / "changes.md").write_text("# changes\n", encoding="utf-8")
        self._write_index(next_id=2)
        code, payload = self._run(
            "archive",
            "T0001",
            "--date",
            "2026-08-20",
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

    def test_archive_requires_changes_but_dry_run_can_build_summary_first(self) -> None:
        task = self._seed_task("T0001", "alpha")
        self._mark_archive_ready(task)
        (task / "changes.md").unlink()
        self._write_index(next_id=2)
        code, payload = self._run("archive", "T0001")
        self.assertEqual(code, 1)
        self.assertEqual(payload["reason"], "missing_changes_summary")
        code, payload = self._run("archive", "T0001", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn(payload["result"], {"initial_preflight", "final_preflight"})

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
            "# progress\n\n## 验证证据\n\n- tests passed\n\n## 最终验证快照\n\n- 状态：`fresh`\n- 说明：test fixture\n", encoding="utf-8"
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
            "# progress\n\n## 验证证据\n\n- tests passed\n\n## 最终验证快照\n\n- 状态：`fresh`\n- 说明：test fixture\n", encoding="utf-8"
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
        self.assertIn(payload["result"], {"initial_preflight", "final_preflight"})
        self.assertEqual(changes.read_text(encoding="utf-8"), "# changes\n")

    def test_openspec_parse(self) -> None:
        self._seed_task("T0002", "beta", openspec=True)
        self._write_index()
        code, payload = self._run("resolve", "T0002")
        self.assertEqual(code, 0)
        self.assertEqual(payload["task"]["openspec"][0]["name"], "demo-change")

    def test_advance_persists_state_progress_and_returns_next(self) -> None:
        self._seed_task("T0002", "beta", openspec=True)
        change = self.tmp / "openspec/changes/demo-change"
        change.mkdir(parents=True)
        (change / "tasks.md").write_text(
            "- [x] first\n- [ ] second\n", encoding="utf-8"
        )
        self._write_index()
        code, payload = self._run(
            "advance", "T0002", "--phase", "implementing", "--change", "demo-change",
            "--current-task", "second", "--completed", "first", "--next", "continue second",
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["result"], "next")
        self.assertEqual(payload["next"]["text"], "second")
        self.assertEqual(payload["checkpoint"]["status"], "in_progress")
        progress = (self.tmp / "tasks/2026-08-01/T0002-beta/progress.md").read_text(encoding="utf-8")
        self.assertIn("| `demo-change` | 1 | 2 | 1 |", progress)
        self.assertIn("当前任务：second", progress)
        readme = (self.tmp / "tasks/2026-08-01/T0002-beta/README.md").read_text(encoding="utf-8")
        self.assertIn("**status：** in_progress", readme)
        code, context = self._run("execution-context", "T0002")
        self.assertEqual(code, 0)
        self.assertEqual(context["targets"][0]["progress"]["remaining"], 1)
        self.assertTrue(context["progress_exists"])

    def test_advance_defers_resumes_and_keeps_candidate_work(self) -> None:
        self._seed_task("T0002", "deferred", openspec=True)
        change = self.tmp / "openspec/changes/demo-change"
        change.mkdir(parents=True)
        tasks = change / "tasks.md"
        tasks.write_text("- [x] first\n- [ ] manual verification\n- [ ] implement next\n", encoding="utf-8")
        self._write_index()
        code, advanced = self._run(
            "advance", "T0002", "--phase", "implementing", "--change", "demo-change",
            "--current-task", "manual verification", "--defer-current", "requires operator validation",
        )
        self.assertEqual(code, 0)
        self.assertEqual(advanced["result"], "next")
        self.assertEqual(advanced["apply_schedule"]["deferred"][0]["task"], "manual verification")
        self.assertEqual(advanced["next"]["text"], "implement next")

        tasks.write_text("- [x] first\n- [ ] manual verification\n- [x] implement next\n", encoding="utf-8")
        code, deferred_only = self._run(
            "advance", "T0002", "--phase", "implementing", "--change", "demo-change",
            "--current-task", "implement next",
        )
        self.assertEqual(code, 0)
        self.assertEqual(deferred_only["result"], "deferred_only")
        self.assertIsNone(deferred_only["next"])

        code, resumed = self._run(
            "advance", "T0002", "--phase", "implementing", "--change", "demo-change",
            "--current-task", "manual verification", "--resume-current",
        )
        self.assertEqual(code, 0)
        self.assertEqual(resumed["result"], "next")
        self.assertEqual(resumed["next"]["text"], "manual verification")

        tasks.write_text("- [x] first\n- [x] manual verification\n- [x] implement next\n", encoding="utf-8")
        code, exhausted = self._run("advance", "T0002", "--phase", "implementing", "--change", "demo-change")
        self.assertEqual(code, 0)
        self.assertEqual(exhausted["result"], "validation_required")
        code, testing = self._run(
            "advance", "T0002", "--phase", "testing", "--change", "demo-change",
            "--verification", "unit tests passed",
        )
        self.assertEqual(code, 0)
        self.assertEqual(testing["result"], "validation_recorded")
        code, done = self._run("advance", "T0002", "--phase", "done", "--change", "demo-change")
        self.assertEqual(code, 0)
        self.assertEqual(done["result"], "done")
        self.assertIsNone(done["next"])
        progress = (self.tmp / "tasks/2026-08-01/T0002-deferred/progress.md").read_text(encoding="utf-8")
        self.assertIn("## 暂缓项", progress)
        self.assertIn("## 候选项", progress)

    def test_advance_rejects_defer_that_is_not_an_exact_remaining_item(self) -> None:
        self._seed_task("T0002", "bad-defer", openspec=True)
        change = self.tmp / "openspec/changes/demo-change"
        change.mkdir(parents=True)
        (change / "tasks.md").write_text("- [ ] real item\n", encoding="utf-8")
        self._write_index()
        code, payload = self._run(
            "advance", "T0002", "--phase", "implementing", "--change", "demo-change",
            "--current-task", "not real", "--defer-current", "manual",
        )
        self.assertEqual(code, 1)
        self.assertIn("not an exact remaining", payload["error"])

    def test_advance_rejects_blank_defer_reason_without_writing_state(self) -> None:
        task = self._seed_task("T0002", "blank-defer", openspec=True)
        change = self.tmp / "openspec/changes/demo-change"
        change.mkdir(parents=True)
        (change / "tasks.md").write_text("- [ ] real item\n", encoding="utf-8")
        self._write_index()
        code, payload = self._run(
            "advance", "T0002", "--phase", "implementing", "--change", "demo-change",
            "--current-task", "real item", "--defer-current", "   ",
        )
        self.assertEqual(code, 1)
        self.assertIn("must not be blank", payload["error"])
        self.assertFalse((task / tc.APPLY_STATE_FILENAME).exists())
        self.assertFalse((task / "progress.md").exists())

    def test_advance_rejects_duplicate_remaining_checkbox_text(self) -> None:
        self._seed_task("T0002", "duplicate", openspec=True)
        change = self.tmp / "openspec/changes/demo-change"
        change.mkdir(parents=True)
        (change / "tasks.md").write_text("- [ ] same\n- [ ] same\n", encoding="utf-8")
        self._write_index()
        code, payload = self._run("advance", "T0002", "--phase", "implementing")
        self.assertEqual(code, 1)
        self.assertIn("duplicate remaining OpenSpec checkbox", payload["error"])

    def test_advance_defer_resume_are_exclusive_and_require_implementing(self) -> None:
        self._seed_task("T0002", "flags", openspec=True)
        change = self.tmp / "openspec/changes/demo-change"
        change.mkdir(parents=True)
        (change / "tasks.md").write_text("- [ ] item\n", encoding="utf-8")
        self._write_index()
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            tc.main([
                "--root", str(self.tmp), "advance", "T0002", "--phase", "implementing",
                "--change", "demo-change", "--current-task", "item",
                "--defer-current", "manual", "--resume-current",
            ])
        code, payload = self._run(
            "advance", "T0002", "--phase", "done", "--change", "demo-change",
            "--current-task", "item", "--defer-current", "manual",
        )
        self.assertEqual(code, 1)
        self.assertIn("require --phase implementing", payload["error"])
        code, payload = self._run(
            "advance", "T0002", "--phase", "implementing", "--change", "demo-change",
            "--current-task", "item", "--resume-current",
        )
        self.assertEqual(code, 1)
        self.assertIn("is not deferred", payload["error"])

    def test_advance_rolls_back_when_status_index_write_fails(self) -> None:
        task = self._seed_task("T0001", "advance-rollback")
        self._write_index(next_id=2)
        original_index = (self.tmp / "tasks/INDEX.md").read_text(encoding="utf-8")
        with mock.patch.object(tc, "write_index", side_effect=OSError("disk full")):
            code, payload = self._run("advance", "T0001", "--phase", "implementing")
        self.assertEqual(code, 1)
        self.assertFalse((task / "progress.md").exists())
        self.assertFalse((task / tc.APPLY_STATE_FILENAME).exists())
        self.assertIn("**status：** draft", (task / "README.md").read_text(encoding="utf-8"))
        self.assertEqual((self.tmp / "tasks/INDEX.md").read_text(encoding="utf-8"), original_index)

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
            "advance", "T0001", "--phase", "implementing"
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
            "# progress\n\n## 验证证据\n\n- tests passed\n\n## 最终验证快照\n\n- 状态：`fresh`\n- 说明：test fixture\n", encoding="utf-8"
        )
        self._write_index(next_id=2)
        code, payload = self._run("archive", "T0001")
        self.assertEqual(code, 2)
        self.assertEqual(payload["reason"], "openspec_remaining")
        self.assertIn("pending", payload["exit_markdown"])

    def test_checkbox_parsing_reports_facts_without_classifying(self) -> None:
        items = tc.parse_openspec_checkboxes(
            "- [x] 实现 API\n- [ ] 实现 /healthz healthcheck 接口\n"
        )
        self.assertEqual(
            items,
            [
                {"text": "实现 API", "done": True},
                {"text": "实现 /healthz healthcheck 接口", "done": False},
            ],
        )
        self.assertEqual(tc.remaining_state_of(items), "remaining")
        self.assertEqual(
            tc.remaining_state_of([{"text": "实现 API", "done": True}]),
            "none",
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
        self._write_fresh_progress(task)
        self._write_index(next_id=2)
        return task

    def test_execution_context_reports_remaining_items_verbatim(self) -> None:
        self._seed_archive_ready(
            "verify-ctx",
            "- [x] 实现 API\n"
            "- [ ] 5.1 Docker multi-stage build 验证\n"
            "- [ ] 6.1 完整 Compose smoke\n",
        )
        code, payload = self._run("execution-context", "T0001")
        self.assertEqual(code, 0)
        self.assertEqual(payload["openspec_remaining"]["state"], "remaining")
        self.assertEqual(payload["openspec_remaining"]["complete"], 1)
        self.assertEqual(payload["openspec_remaining"]["total"], 3)
        self.assertEqual(payload["targets"][0]["remaining_state"], "remaining")
        texts = [item["text"] for item in payload["openspec_remaining"]["items"]]
        self.assertIn("5.1 Docker multi-stage build 验证", texts)

    def test_archive_confirms_any_remaining_with_verbatim_items(self) -> None:
        self._seed_archive_ready(
            "verify-only",
            "- [x] 实现 API\n- [ ] 最终 runtime/Compose/smoke 验证\n",
        )
        code, payload = self._run("archive", "T0001")
        self.assertEqual(code, 2)
        self.assertEqual(payload["result"], "needs_confirm")
        self.assertEqual(payload["reason"], "openspec_remaining")
        self.assertIn("最终 runtime/Compose/smoke 验证", payload["exit_markdown"])
        self.assertIn("--force-merge", payload["exit_markdown"])
        self.assertNotIn("全部判定", payload["exit_markdown"])
        self.assertTrue(
            (self.tmp / "tasks/2026-08-01/T0001-verify-only").is_dir()
        )

    def test_archive_does_not_downgrade_gate_for_implementation_wording(self) -> None:
        """A leftover that merely mentions healthcheck is still user's call."""
        self._seed_archive_ready(
            "impl-wording",
            "- [x] done\n- [ ] 实现 /healthz healthcheck 接口\n",
        )
        code, payload = self._run("archive", "T0001")
        self.assertEqual(code, 2)
        self.assertEqual(payload["reason"], "openspec_remaining")
        self.assertIn("实现 /healthz healthcheck 接口", payload["exit_markdown"])

    def test_archive_force_merge_allows_remaining(self) -> None:
        task = self._seed_archive_ready(
            "force-verify",
            "- [x] 实现 API\n- [ ] 6.1 完整 Compose smoke\n",
            archived=True,
        )
        code, payload = self._run("archive", "T0001", "--force-merge")
        self.assertEqual(code, 0)
        self.assertEqual(payload["result"], "archived")
        dest = self.tmp / "tasks/archive/2026-08-01-T0001-force-verify"
        self.assertTrue((dest / "README.md").is_file())
        self.assertFalse(task.exists())
        audit = (dest / "changes.md").read_text(encoding="utf-8")
        self.assertIn("## Gate Overrides", audit)
        self.assertIn("authorization=`--force-merge`", audit)

    def test_archive_force_merge_allows_implementation_remaining(self) -> None:
        self._seed_archive_ready(
            "force-impl",
            "- [x] done\n- [ ] 实现 billing 模块\n",
            archived=True,
        )
        code, payload = self._run("archive", "T0001")
        self.assertEqual(code, 2)
        self.assertEqual(payload["reason"], "openspec_remaining")
        self.assertIn("实现 billing 模块", payload["exit_markdown"])
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
            "# progress\n\n## 验证证据\n\n- tests passed\n\n## 最终验证快照\n\n- 状态：`fresh`\n- 说明：test fixture\n", encoding="utf-8"
        )
        self._write_index(next_id=2)
        code, payload = self._run("archive", "T0001")
        self.assertEqual(code, 1)
        self.assertIn("missing/invalid task checkout", payload["error"])
        code, payload = self._run(
            "archive", "T0001", "--allow-dirty-checkout", "svc"
        )
        self.assertEqual(code, 1)
        self.assertEqual(
            payload["reason"], "checkout_missing"
        )

    def test_archive_allows_dirty_planning_and_task_store(self) -> None:
        self._init_git_repo("service-a")
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| service-a | `service-a` | 必须 |

## 工作上下文

| 仓库 | 仓库路径 | checkout 路径 | worktree | 分支 | 基线 |
|------|----------|---------------|----------|------|------|
| service-a | `service-a` | `service-a` | 否 | `feat-example` | `main` |
"""
        task = self._seed_task(
            "T0001", "workspace-change", openspec=True, scope_block=scope_block
        )
        self._git(self.tmp / "service-a", "checkout", "-b", "feat-example")
        archived_change = (
            self.tmp / "openspec/changes/archive/2026-08-01-demo-change"
        )
        archived_change.mkdir(parents=True)
        (archived_change / "tasks.md").write_text("- [x] done\n", encoding="utf-8")
        self._mark_archive_ready(task)
        self._write_index(next_id=2)
        self._init_git_repo(".")
        (self.tmp / "other-task-note.md").write_text("in progress\n", encoding="utf-8")

        code, payload = self._run("archive", "T0001", "--dry-run")

        self.assertEqual(code, 0)
        self.assertIn(payload["result"], {"initial_preflight", "final_preflight"})
        uses = {
            row["repo"]: row for row in payload["archive_gate"]["repository_uses"]
        }
        self.assertEqual(uses["service-a"]["roles"], ["delivery"])
        self.assertEqual(uses["."]["roles"], ["planning", "task_store"])
        self.assertEqual(payload["archive_gate"]["blocking"], [])
        self.assertEqual(
            payload["archive_gate"]["non_blocking_dirty"][0]["repo"], "."
        )

        original_run_git = tc.run_git

        def run_git_with_unavailable_workspace(
            repo: Path, *git_args: str, check: bool = False
        ):
            if (
                repo.resolve() == self.tmp.resolve()
                and git_args == ("status", "--porcelain")
            ):
                raise OSError("simulated status failure")
            return original_run_git(repo, *git_args, check=check)

        with mock.patch.object(
            tc,
            "run_git",
            side_effect=run_git_with_unavailable_workspace,
        ):
            code, payload = self._run("archive", "T0001", "--dry-run")
        self.assertEqual(code, 0)
        diagnostic = payload["archive_gate"]["non_blocking_diagnostics"][0]
        self.assertEqual(diagnostic["repo"], ".")
        self.assertEqual(diagnostic["reason"], "non_delivery_status_unavailable")

    def test_archive_blocks_dirty_delivery_and_supports_exact_override(self) -> None:
        repo = self._init_git_repo("service-a")
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| service-a | `service-a` | 必须 |

## 工作上下文

| 仓库 | 仓库路径 | checkout 路径 | worktree | 分支 | 基线 |
|------|----------|---------------|----------|------|------|
| service-a | `service-a` | `service-a` | 否 | `feat-example` | `main` |
"""
        task = self._seed_task("T0001", "delivery-change", scope_block=scope_block)
        self._git(repo, "checkout", "-b", "feat-example")
        self._mark_archive_ready(task)
        self._write_index(next_id=2)
        (repo / "local-change.txt").write_text("dirty\n", encoding="utf-8")

        code, payload = self._run("archive", "T0001")
        self.assertEqual(code, 2)
        self.assertEqual(payload["reason"], "dirty_delivery_checkout")
        self.assertEqual(
            payload["archive_gate"]["blocking"][0]["repo"], "service-a"
        )
        self.assertEqual(
            payload["exact_action"],
            "taskctl archive T0001 --allow-dirty-checkout service-a",
        )

        code, payload = self._run(
            "archive",
            "T0001",
            "--allow-dirty-checkout",
            "service-a",
            "--allow-missing-verification",
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["result"], "archived")
        self.assertEqual(
            payload["archive_gate"]["overridden"][0]["repo"], "service-a"
        )
        audit = self.tmp / "tasks/archive/2026-08-01-T0001-delivery-change/changes.md"
        self.assertIn(
            "authorization=`--allow-dirty-checkout service-a`",
            audit.read_text(encoding="utf-8"),
        )

    def test_archive_rolls_back_new_override_audit_file(self) -> None:
        repo = self._init_git_repo("service-a")
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| service-a | `service-a` | 必须 |

## 工作上下文

| 仓库 | 仓库路径 | checkout 路径 | worktree | 分支 | 基线 |
|------|----------|---------------|----------|------|------|
| service-a | `service-a` | `service-a` | 否 | `main` | `main` |
"""
        task = self._seed_task("T0001", "audit-rollback", scope_block=scope_block)
        self._mark_archive_ready(task)
        self._write_index(next_id=2)
        (repo / "local-change.txt").write_text("dirty\n", encoding="utf-8")

        with mock.patch.object(tc, "write_index", side_effect=OSError("disk full")):
            code, payload = self._run(
                "archive",
                "T0001",
                "--allow-dirty-checkout",
                "service-a",
                "--allow-missing-verification",
            )

        self.assertEqual(code, 1)
        self.assertIn("disk full", payload["error"])
        self.assertTrue(task.is_dir())
        self.assertEqual((task / "changes.md").read_text(encoding="utf-8"), "# changes\n")
        self.assertIn(
            "**status：** draft", (task / "README.md").read_text(encoding="utf-8")
        )
        self.assertFalse(
            (self.tmp / "tasks/archive/2026-08-01-T0001-audit-rollback").exists()
        )

    def test_archive_fails_closed_when_delivery_status_is_unavailable(self) -> None:
        self._init_git_repo("service-a")
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| service-a | `service-a` | 必须 |

## 工作上下文

| 仓库 | 仓库路径 | checkout 路径 | worktree | 分支 | 基线 |
|------|----------|---------------|----------|------|------|
| service-a | `service-a` | `service-a` | 否 | `main` | `main` |
"""
        task = self._seed_task("T0001", "status-failure", scope_block=scope_block)
        self._mark_archive_ready(task)
        self._write_index(next_id=2)

        original_run_git = tc.run_git

        def run_git_with_status_failure(
            repo: Path, *git_args: str, check: bool = False
        ):
            if git_args == ("status", "--porcelain"):
                raise OSError("simulated status failure")
            return original_run_git(repo, *git_args, check=check)

        with mock.patch.object(
            tc,
            "run_git",
            side_effect=run_git_with_status_failure,
        ):
            code, payload = self._run("archive", "T0001", "--dry-run")

        self.assertEqual(code, 1)
        self.assertEqual(payload["reason"], "delivery_status_unavailable")
        blocking = payload["archive_gate"]["blocking"][0]
        self.assertEqual(blocking["repo"], "service-a")
        self.assertEqual(blocking["reason"], "delivery_status_unavailable")

    def test_archive_reports_reference_without_inspecting_git(self) -> None:
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| docs-only | `missing-reference` | 建议 |
| excluded-only | `another-missing-reference` | 排除 |
"""
        task = self._seed_task("T0001", "reference-only", scope_block=scope_block)
        self._mark_archive_ready(task)
        self._write_index(next_id=2)

        with mock.patch.object(tc, "run_git") as run_git_mock:
            code, payload = self._run("archive", "T0001", "--dry-run")

        self.assertEqual(code, 0)
        run_git_mock.assert_not_called()
        uses = {
            row["repo"]: row for row in payload["archive_gate"]["repository_uses"]
        }
        self.assertEqual(uses["missing-reference"]["roles"], ["reference"])
        self.assertEqual(
            uses["another-missing-reference"]["roles"], ["reference"]
        )

    def test_archive_delivery_role_takes_priority_over_reference(self) -> None:
        repo = self._init_git_repo("service-a")
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| service-a | `service-a` | 必须 |
| service-a-docs | `service-a` | 建议 |
"""
        task = self._seed_task("T0001", "mixed-reference", scope_block=scope_block)
        self._mark_archive_ready(task)
        self._write_index(next_id=2)
        (repo / "local-change.txt").write_text("dirty\n", encoding="utf-8")

        code, payload = self._run("archive", "T0001")

        self.assertEqual(code, 1)
        blocking = payload["archive_gate"]["blocking"][0]
        self.assertEqual(blocking["repo"], "service-a")
        self.assertEqual(blocking["reason"], "checkout_not_prepared")
        self.assertEqual(blocking["roles"], ["delivery", "reference"])

    def test_archive_does_not_special_case_workspace_delivery_repo(self) -> None:
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| workspace | `.` | 必须 |

## 工作上下文

| 仓库 | 仓库路径 | checkout 路径 | worktree | 分支 | 基线 |
|------|----------|---------------|----------|------|------|
| workspace | `.` | `.` | 否 | `feat-example` | `main` |
"""
        task = self._seed_task("T0001", "workspace-delivery", scope_block=scope_block)
        self._write_index(next_id=2)
        workspace = self._init_git_repo(".")
        self._git(workspace, "checkout", "-b", "feat-example")
        self._mark_archive_ready(task)
        (self.tmp / "delivery-change.txt").write_text("dirty\n", encoding="utf-8")

        code, payload = self._run("archive", "T0001")

        self.assertEqual(code, 2)
        self.assertEqual(payload["reason"], "dirty_delivery_checkout")
        blocking = payload["archive_gate"]["blocking"][0]
        self.assertEqual(blocking["repo"], ".")
        self.assertEqual(blocking["roles"], ["delivery", "task_store"])

    def test_archive_blocks_dirty_repo_with_delivery_and_planning_roles(self) -> None:
        repo = self._init_git_repo("service-a")
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| service-a | `service-a` | 必须 |

### 关联 OpenSpec

| change | 路径 | 仓库 | store | 说明 |
|--------|------|------|-------|------|
| demo-change | `openspec/changes/demo-change/` | `service-a` | | demo |

## 工作上下文

| 仓库 | 仓库路径 | checkout 路径 | worktree | 分支 | 基线 |
|------|----------|---------------|----------|------|------|
| service-a | `service-a` | `service-a` | 否 | `feat-example` | `main` |
"""
        task = self._seed_task("T0001", "combined-role", scope_block=scope_block)
        self._git(repo, "checkout", "-b", "feat-example")
        archived_change = repo / "openspec/changes/archive/2026-08-01-demo-change"
        archived_change.mkdir(parents=True)
        (archived_change / "tasks.md").write_text("- [x] done\n", encoding="utf-8")
        self._mark_archive_ready(task)
        self._write_index(next_id=2)

        code, payload = self._run("archive", "T0001")

        self.assertEqual(code, 2)
        self.assertEqual(payload["reason"], "dirty_delivery_checkout")
        blocking = payload["archive_gate"]["blocking"][0]
        self.assertEqual(blocking["repo"], "service-a")
        self.assertEqual(blocking["roles"], ["delivery", "planning"])

    def test_worktree_apply_advance_archive_lifecycle(self) -> None:
        repo = self._init_git_repo("svc")
        code, created = self._run("new", "--slug", "lifecycle", "--title", "Lifecycle", "--date", "2026-08-14")
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
            "prepare-branches", "--slug", "lifecycle", "--from-task", "T0001",
            "--worktree", "svc=svc-life-wt",
        )
        self.assertEqual(code, 0)
        self.assertEqual(prepared["repos"][0]["action"], "created_worktree")
        change = wt / "openspec/changes/life-change"
        change.mkdir(parents=True)
        (change / "tasks.md").write_text("- [ ] implement\n", encoding="utf-8")
        code, advanced = self._run(
            "advance", "T0001", "--phase", "implementing", "--change", "life-change", "--current-task", "implement",
        )
        self.assertEqual(code, 0)
        self.assertEqual(advanced["result"], "next")
        self.assertEqual(advanced["targets"][0]["checkout"], "svc-life-wt")
        (change / "tasks.md").write_text("- [x] implement\n", encoding="utf-8")
        code, exhausted = self._run(
            "advance", "T0001", "--phase", "implementing", "--change", "life-change",
        )
        self.assertEqual(code, 0)
        self.assertEqual(exhausted["result"], "validation_required")
        code, provisional = self._run(
            "advance", "T0001", "--phase", "testing", "--change", "life-change",
            "--verification", "unit tests passed on dirty checkout",
        )
        self.assertEqual(code, 0)
        self.assertEqual(provisional["result"], "validation_required")
        self.assertEqual(provisional["verification"]["status"], "provisional")

        self._git(wt, "add", ".")
        self._git(wt, "commit", "-m", "implement lifecycle")
        code, testing = self._run(
            "advance", "T0001", "--phase", "testing", "--change", "life-change",
            "--verification", "unit tests passed after commit",
        )
        self.assertEqual(code, 0)
        self.assertEqual(testing["result"], "validation_recorded")
        code, resumed = self._run(
            "advance", "T0001", "--phase", "implementing", "--change", "life-change",
        )
        self.assertEqual(code, 0)
        self.assertEqual(resumed["result"], "validation_required")
        code, stale_done = self._run("advance", "T0001", "--phase", "done", "--change", "life-change")
        self.assertEqual(code, 1)
        self.assertEqual(stale_done["reason"], "stale_verification")
        code, testing = self._run(
            "advance", "T0001", "--phase", "testing", "--change", "life-change",
            "--verification", "unit tests rerun after implementation resume",
        )
        self.assertEqual(code, 0)
        self.assertEqual(testing["result"], "validation_recorded")
        code, done = self._run("advance", "T0001", "--phase", "done", "--change", "life-change")
        self.assertEqual(code, 0)
        self.assertEqual(done["result"], "done")

        archived_change = wt / "openspec/changes/archive/2026-08-14-life-change"
        archived_change.parent.mkdir(parents=True)
        shutil.move(str(change), str(archived_change))
        self._git(wt, "add", ".")
        self._git(wt, "commit", "-m", "archive lifecycle spec")
        (task / "changes.md").write_text("# Changes\n", encoding="utf-8")
        code, stale_archive = self._run("archive", "T0001", "--dry-run", "--date", "2026-08-14")
        self.assertEqual(code, 2)
        self.assertEqual(stale_archive["reason"], "stale_verification")
        self.assertEqual(
            stale_archive["exact_action"],
            "taskctl archive T0001 --allow-missing-verification",
        )
        code, retested = self._run(
            "advance", "T0001", "--phase", "testing", "--change", "life-change",
            "--verification", "unit tests rerun at archived-spec HEAD",
        )
        self.assertEqual(code, 0)
        self.assertEqual(retested["result"], "validation_recorded")
        code, done = self._run("advance", "T0001", "--phase", "done", "--change", "life-change")
        self.assertEqual(code, 0)
        code, dry_run = self._run("archive", "T0001", "--dry-run", "--date", "2026-08-14")
        self.assertEqual(code, 0)
        self.assertEqual(dry_run["archive_gate"]["delivery_summaries"][0]["checkout"], "svc-life-wt")
        code, archived = self._run("archive", "T0001", "--date", "2026-08-14")
        self.assertEqual(code, 0)
        self.assertEqual(archived["result"], "archived")
        self.assertTrue((self.tmp / "tasks/archive/2026-08-14-T0001-lifecycle").is_dir())


    def test_archive_initial_preflight_lists_active_complete_without_mutation(self) -> None:
        task = self._seed_archive_ready("initial", "- [x] done\n")
        active = self.tmp / "openspec/changes/demo-change"
        before = (active / "tasks.md").read_text(encoding="utf-8")

        code, payload = self._run("archive", "T0001", "--dry-run")

        self.assertEqual(code, 0)
        self.assertEqual(payload["result"], "initial_preflight")
        self.assertEqual(payload["target_states"][0]["state"], "active")
        self.assertEqual(payload["external_actions"][0]["state"], "pending")
        self.assertTrue(task.is_dir())
        self.assertEqual((active / "tasks.md").read_text(encoding="utf-8"), before)
        self.assertFalse((self.tmp / "openspec/changes/archive").exists())

    def test_archive_multi_target_partial_retry_recognizes_completed_target(self) -> None:
        task = self._seed_task("T0001", "partial", openspec=True)
        readme = (task / "README.md").read_text(encoding="utf-8")
        readme = readme.replace(
            "| `demo-change` | `openspec/changes/demo-change/` | demo |",
            "| `demo-change` | `openspec/changes/demo-change/` | demo |\n"
            "| `second-change` | `openspec/changes/second-change/` | second |",
        ).replace("- [ ] done", "- [x] done")
        (task / "README.md").write_text(readme, encoding="utf-8")
        for name in ("demo-change", "second-change"):
            root = self.tmp / f"openspec/changes/{name}"
            root.mkdir(parents=True)
            (root / "tasks.md").write_text("- [x] done\n", encoding="utf-8")
        first_archive = self.tmp / "openspec/changes/archive/2026-08-14-demo-change"
        first_archive.parent.mkdir(parents=True)
        shutil.move(str(self.tmp / "openspec/changes/demo-change"), str(first_archive))
        (task / "changes.md").write_text("# Changes\n", encoding="utf-8")
        self._write_fresh_progress(task)
        self._write_index(next_id=2)

        code, partial = self._run("archive", "T0001", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(partial["result"], "initial_preflight")
        self.assertEqual(
            {row["name"]: row["state"] for row in partial["target_states"]},
            {"demo-change": "uniquely_archived", "second-change": "active"},
        )
        self.assertEqual(
            {row["change"]: row["state"] for row in partial["external_actions"] if row["action"] == "archive_openspec"},
            {"demo-change": "completed", "second-change": "pending"},
        )

        second_archive = self.tmp / "openspec/changes/archive/2026-08-14-second-change"
        shutil.move(str(self.tmp / "openspec/changes/second-change"), str(second_archive))
        code, final = self._run("archive", "T0001", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(final["result"], "final_preflight")
        self.assertTrue(all(row["state"] == "uniquely_archived" for row in final["target_states"]))
        self.assertTrue(task.is_dir())

    def test_archive_final_preflight_reports_new_dirty_and_keeps_task_active(self) -> None:
        repo = self._init_git_repo("svc")
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| svc | `svc` | 必须 |

## 工作上下文

| 仓库 | 仓库路径 | checkout 路径 | worktree | 分支 | 基线 |
|------|----------|---------------|----------|------|------|
| svc | `svc` | `svc` | 否 | `main` | `main` |
"""
        task = self._seed_task("T0001", "final-dirty", openspec=True, scope_block=scope_block)
        change = self.tmp / "openspec/changes/demo-change"
        change.mkdir(parents=True)
        (change / "tasks.md").write_text("- [x] done\n", encoding="utf-8")
        self._mark_archive_ready(task)
        self._write_index(next_id=2)
        code, initial = self._run("archive", "T0001", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(initial["result"], "initial_preflight")

        archived = self.tmp / "openspec/changes/archive/2026-08-14-demo-change"
        archived.parent.mkdir(parents=True)
        shutil.move(str(change), str(archived))
        (repo / "external-write.txt").write_text("dirty\n", encoding="utf-8")
        code, final = self._run("archive", "T0001", "--dry-run")
        self.assertEqual(code, 2)
        self.assertEqual(final["reason"], "dirty_delivery_checkout")
        self.assertEqual(final["target_states"][0]["state"], "uniquely_archived")
        self.assertTrue(task.is_dir())

    def test_archive_confirmations_are_code_2_and_gate_overrides_are_audited(self) -> None:
        repo = self._init_git_repo("svc")
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| svc | `svc` | 必须 |

## 工作上下文

| 仓库 | 仓库路径 | checkout 路径 | worktree | 分支 | 基线 |
|------|----------|---------------|----------|------|------|
| svc | `svc` | `svc` | 否 | `main` | `main` |
"""
        task = self._seed_task("T0001", "confirmations", scope_block=scope_block)
        (task / "changes.md").write_text("# Changes\n", encoding="utf-8")
        self._write_index(next_id=2)

        code, acceptance = self._run("archive", "T0001")
        self.assertEqual(code, 2)
        self.assertEqual(acceptance["reason"], "unchecked_acceptance")
        self.assertEqual(acceptance["affected"], ["done"])
        self.assertEqual(
            acceptance["exact_action"],
            "taskctl archive T0001 --allow-unchecked-acceptance",
        )

        code, verification = self._run(
            "archive", "T0001", "--allow-unchecked-acceptance"
        )
        self.assertEqual(code, 2)
        self.assertEqual(verification["reason"], "stale_verification")
        self.assertEqual(
            verification["exact_action"],
            "taskctl archive T0001 --allow-missing-verification",
        )

        (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        code, dirty = self._run(
            "archive",
            "T0001",
            "--allow-unchecked-acceptance",
            "--allow-missing-verification",
        )
        self.assertEqual(code, 2)
        self.assertEqual(dirty["reason"], "dirty_delivery_checkout")

        code, archived = self._run(
            "archive",
            "T0001",
            "--allow-unchecked-acceptance",
            "--allow-missing-verification",
            "--allow-dirty-checkout",
            "svc",
        )
        self.assertEqual(code, 0)
        audit_path = self.tmp / "tasks/archive/2026-08-01-T0001-confirmations/changes.md"
        audit = audit_path.read_text(encoding="utf-8")
        self.assertIn("## Gate Overrides", audit)
        self.assertIn("authorization=`--allow-unchecked-acceptance`", audit)
        self.assertIn("authorization=`--allow-missing-verification`", audit)
        self.assertIn("authorization=`--allow-dirty-checkout svc`", audit)
        self.assertEqual(len(archived["gate_overrides"]), 3)

    def test_archive_structural_failures_are_not_overrideable(self) -> None:
        task = self._seed_task("T0001", "missing-structural", openspec=True)
        self._mark_archive_ready(task)
        self._write_index(next_id=2)
        code, missing = self._run(
            "archive",
            "T0001",
            "--dry-run",
            "--force-merge",
            "--allow-unchecked-acceptance",
            "--allow-missing-verification",
        )
        self.assertEqual(code, 1)
        self.assertEqual(missing["reason"], "openspec_target_missing")

        active = self.tmp / "openspec/changes/demo-change"
        active.mkdir(parents=True)
        (active / "tasks.md").write_text("- [x] done\n", encoding="utf-8")
        archived = self.tmp / "openspec/changes/archive/2026-08-14-demo-change"
        archived.mkdir(parents=True)
        (archived / "tasks.md").write_text("- [x] done\n", encoding="utf-8")
        code, ambiguous = self._run(
            "archive", "T0001", "--dry-run", "--force-merge"
        )
        self.assertEqual(code, 1)
        self.assertEqual(ambiguous["reason"], "openspec_target_ambiguous")

    def test_archive_parser_has_no_unsafe_flags(self) -> None:
        parser = tc.build_parser()
        removed_flags = [
            "--allow-" + "active-openspec",
            "--allow-" + "missing-changes",
        ]
        for flag in removed_flags:
            with self.assertRaises(SystemExit):
                parser.parse_args(["archive", "T0001", flag])

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

    def test_archive_dry_run_includes_delivery_summaries(self) -> None:
        repo = self._init_git_repo("svc")
        self._git(repo, "checkout", "-b", "feat-sum")
        (repo / "a.txt").write_text("a\n", encoding="utf-8")
        self._git(repo, "add", ".")
        self._git(repo, "commit", "-m", "add a")
        (repo / "wip.txt").write_text("wip\n", encoding="utf-8")
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| svc | `svc` | 必须 |

## 工作上下文

| 仓库 | 仓库路径 | checkout 路径 | worktree | 分支 | 基线 |
|------|----------|---------------|----------|------|------|
| svc | `svc` | `svc` | 否 | `feat-sum` | `main` |
"""
        task = self._seed_task("T0001", "summary", scope_block=scope_block)
        self._mark_archive_ready(task)
        self._write_index(next_id=2)
        code, payload = self._run(
            "archive", "T0001", "--dry-run", "--allow-dirty-checkout", "svc",
            "--allow-missing-verification",
        )
        self.assertEqual(code, 0)
        summary = payload["archive_gate"]["delivery_summaries"][0]
        self.assertTrue(summary["commits"])
        self.assertTrue(any(f["path"] == "a.txt" for f in summary["files"]))
        self.assertTrue(any(f["path"] == "wip.txt" and f["source"] == "untracked" for f in summary["files"]))

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

    def test_execution_context_requires_binding_for_must_checkout(self) -> None:
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| svc | `svc` | 必须 |
| notes | `other` | 建议 |
| vendor | `vendor` | 排除 |
"""
        self._seed_task("T0001", "demo-feature", scope_block=scope_block)
        self._write_index(next_id=2)
        code, payload = self._run("execution-context", "T0001")
        self.assertEqual(code, 1)
        self.assertEqual(payload["reason"], "checkout_not_prepared")
        self.assertEqual(payload["checkout_gate"]["blocking"][0]["repo"], "svc")

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

    def test_restored_task_with_archived_incomplete_change_is_not_done(self) -> None:
        task = self._seed_task("T0001", "archived-change", openspec=True)
        change = self.tmp / "openspec/changes/demo-change"
        change.mkdir(parents=True)
        (change / "tasks.md").write_text("- [ ] unfinished archived item\n", encoding="utf-8")
        self._mark_archive_ready(task)
        self._write_index(next_id=2)
        code, preflight = self._run("archive", "T0001", "--dry-run", "--force-merge")
        self.assertEqual(code, 0)
        self.assertEqual(preflight["result"], "initial_preflight")
        archived_change = self.tmp / "openspec/changes/archive/2026-08-01-demo-change"
        archived_change.parent.mkdir(parents=True)
        shutil.move(str(change), str(archived_change))
        code, _ = self._run("archive", "T0001", "--force-merge")
        self.assertEqual(code, 0)
        code, _ = self._run("restore", "T0001")
        self.assertEqual(code, 0)
        code, context = self._run("execution-context", "T0001")
        self.assertEqual(code, 0)
        self.assertEqual(context["openspec_remaining"]["remaining"], 1)
        self.assertEqual(context["apply_schedule"]["state"], "deferred_only")
        code, advanced = self._run("advance", "T0001", "--phase", "implementing")
        self.assertEqual(code, 0)
        self.assertEqual(advanced["result"], "deferred_only")
        self.assertIn("restore or create a follow-up", advanced["apply_schedule"]["deferred"][0]["reason"])


    def test_execution_context_rejects_wrong_repository_and_detached_head(self) -> None:
        svc = self._init_git_repo("svc")
        other = self._init_git_repo("other")
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| svc | `svc` | 必须 |

## 工作上下文

| 仓库 | 仓库路径 | checkout 路径 | worktree | 分支 | 基线 |
|------|----------|---------------|----------|------|------|
| svc | `svc` | `other` | 否 | `main` | `main` |
"""
        task = self._seed_task("T0001", "wrong-repo", scope_block=scope_block)
        self._write_index(next_id=2)
        code, payload = self._run("execution-context", "T0001")
        self.assertEqual(code, 1)
        self.assertEqual(payload["reason"], "wrong_repository")

        readme = (task / "README.md").read_text(encoding="utf-8")
        (task / "README.md").write_text(
            readme.replace("`other` | 否 | `main`", "`svc` | 否 | `main`"),
            encoding="utf-8",
        )
        self._git(svc, "checkout", "--detach")
        code, payload = self._run("execution-context", "T0001")
        self.assertEqual(code, 1)
        self.assertEqual(payload["reason"], "detached_head")
        self.assertIsNone(payload["checkout_gate"]["blocking"][0]["actual_branch"])

    def test_archive_rejects_clean_wrong_branch_with_expected_actual(self) -> None:
        repo = self._init_git_repo("svc")
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| svc | `svc` | 必须 |

## 工作上下文

| 仓库 | 仓库路径 | checkout 路径 | worktree | 分支 | 基线 |
|------|----------|---------------|----------|------|------|
| svc | `svc` | `svc` | 否 | `feat-expected` | `main` |
"""
        task = self._seed_task("T0001", "wrong-branch", scope_block=scope_block)
        self._mark_archive_ready(task)
        self._write_index(next_id=2)
        self.assertFalse(tc.is_dirty(repo))
        code, payload = self._run("archive", "T0001", "--dry-run")
        self.assertEqual(code, 1)
        self.assertEqual(payload["reason"], "branch_mismatch")
        blocking = payload["archive_gate"]["blocking"][0]
        self.assertEqual(blocking["expected_branch"], "feat-expected")
        self.assertEqual(blocking["actual_branch"], "main")

    def test_prepare_branches_multi_repo_persists_only_success_and_returns_blocking(self) -> None:
        good = self._init_git_repo("good")
        bad = self._init_git_repo("bad")
        (bad / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| good | `good` | 必须 |
| bad | `bad` | 必须 |
"""
        task = self._seed_task("T0001", "partial", scope_block=scope_block)
        self._write_index(next_id=2)
        code, payload = self._run(
            "prepare-branches", "--slug", "partial", "--from-task", "T0001"
        )
        self.assertEqual(code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["errors"][0]["action"], "blocked_dirty")
        self.assertEqual(tc.current_branch(good), "feat-partial")
        readme = (task / "README.md").read_text(encoding="utf-8")
        bindings = tc.parse_work_context(readme)
        self.assertEqual([row["repo"] for row in bindings], ["good"])
        self.assertNotIn("skipped_" + "dirty", json.dumps(payload))

    def test_prepare_branches_parser_has_no_skip_dirty(self) -> None:
        parser = tc.build_parser()
        removed_flag = "--skip-" + "dirty"
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["prepare-branches", "--slug", "x", "--repo", "svc", removed_flag])

    def test_advance_blocked_precedes_candidates_and_testing_rejects_remaining(self) -> None:
        self._seed_task("T0001", "blocked", openspec=True)
        change = self.tmp / "openspec/changes/demo-change"
        change.mkdir(parents=True)
        (change / "tasks.md").write_text("- [ ] still candidate\n", encoding="utf-8")
        self._write_index(next_id=2)
        code, payload = self._run(
            "advance", "T0001", "--phase", "blocked", "--blocker", "global outage"
        )
        self.assertEqual(code, 0)
        self.assertEqual(payload["result"], "blocked")
        self.assertIsNone(payload["next"])
        self.assertEqual(payload["apply_schedule"]["candidates"][0]["text"], "still candidate")
        self.assertNotIn("run" + "nable", payload["apply_schedule"])
        code, payload = self._run(
            "advance", "T0001", "--phase", "testing", "--verification", "not ready"
        )
        self.assertEqual(code, 1)
        self.assertEqual(payload["reason"], "checkboxes_remaining")

    def test_deferred_dependency_chain_keeps_independent_candidate(self) -> None:
        self._seed_task("T0001", "deps", openspec=True)
        change = self.tmp / "openspec/changes/demo-change"
        change.mkdir(parents=True)
        (change / "tasks.md").write_text(
            "- [ ] A manual environment\n- [ ] B depends on A\n- [ ] C independent\n",
            encoding="utf-8",
        )
        self._write_index(next_id=2)
        code, first = self._run(
            "advance", "T0001", "--phase", "implementing", "--change", "demo-change",
            "--current-task", "A manual environment", "--defer-current", "environment unavailable",
        )
        self.assertEqual(code, 0)
        self.assertEqual(first["next"]["text"], "B depends on A")
        code, second = self._run(
            "advance", "T0001", "--phase", "implementing", "--change", "demo-change",
            "--current-task", "B depends on A", "--defer-current", "blocked by demo-change:A manual environment",
        )
        self.assertEqual(code, 0)
        self.assertEqual(second["next"]["text"], "C independent")
        reasons = {row["task"]: row["reason"] for row in second["apply_schedule"]["deferred"]}
        self.assertIn("A manual environment", reasons["B depends on A"])

    def test_catalog_omitted_row_is_repaired_and_id_not_reused(self) -> None:
        self._seed_task("T0009", "unindexed")
        (self.tmp / "tasks/INDEX.md").write_text(
            tc.render_index(2, [], []), encoding="utf-8"
        )
        code, listed = self._run("list")
        self.assertEqual(code, 0)
        self.assertTrue(listed["catalog"]["repair_needed"])
        self.assertEqual(listed["catalog"]["max_id"], 9)
        code, created = self._run("new", "--slug", "after-gap")
        self.assertEqual(code, 0)
        self.assertEqual(created["task"]["task_id"], "T0010")
        index = (self.tmp / "tasks/INDEX.md").read_text(encoding="utf-8")
        self.assertIn("T0009", index)

    def test_catalog_duplicate_and_active_archive_conflicts_block_mutation(self) -> None:
        self._seed_task("T0001", "one")
        self._seed_task("T0001", "two", day="2026-08-02")
        self._write_index(next_id=2)
        code, payload = self._run("new", "--slug", "blocked-by-duplicate")
        self.assertEqual(code, 1)
        self.assertEqual(payload["reason"], "task_catalog_conflict")
        self.assertEqual(payload["catalog"]["diagnostics"][0]["reason"], "duplicate_task_id")

        shutil.rmtree(self.tmp / "tasks/2026-08-02")
        task = self.tmp / "tasks/2026-08-01/T0001-one"
        archived = self.tmp / "tasks/archive/2026-08-01-T0001-copy"
        archived.parent.mkdir(parents=True)
        shutil.copytree(task, archived)
        archived_readme = (archived / "README.md").read_text(encoding="utf-8")
        (archived / "README.md").write_text(
            tc.set_readme_status(archived_readme, "archived"), encoding="utf-8"
        )
        code, payload = self._run("set-status", "T0001", "exploring")
        self.assertEqual(code, 1)
        reasons = [row["reason"] for row in payload["catalog"]["diagnostics"]]
        self.assertIn("active_archive_id_conflict", reasons)

    def test_catalog_reports_dir_identity_and_missing_index_path(self) -> None:
        task = self._seed_task("T0001", "identity")
        wrong = task.parent / "T0002-identity"
        task.rename(wrong)
        self._write_index(next_id=3)
        code, payload = self._run("new", "--slug", "blocked")
        self.assertEqual(code, 1)
        diagnostics = payload["catalog"]["diagnostics"]
        self.assertTrue(any(row["reason"] == "readme_dir_id_mismatch" for row in diagnostics))

        shutil.rmtree(wrong)
        missing = tc.TaskRow(
            task_id="T0003", name="missing", path="tasks/2026-08-01/T0003-missing/"
        )
        tc.write_index(self.tmp, 4, [missing], [])
        code, payload = self._run("new", "--slug", "still-blocked")
        self.assertEqual(code, 1)
        self.assertTrue(
            any(row["reason"] == "missing_indexed_path" for row in payload["catalog"]["diagnostics"])
        )

    def test_unknown_scope_role_and_malformed_tables_fail_before_git(self) -> None:
        scope_block = """
### 涉及面

| 逻辑库 | 路径 | 角色 |
|--------|------|------|
| svc | `svc` | maybe |
"""
        self._seed_task("T0001", "bad-scope", scope_block=scope_block)
        self._write_index(next_id=2)
        with mock.patch.object(tc, "run_git") as run_git_mock:
            code, payload = self._run("execution-context", "T0001")
        self.assertEqual(code, 1)
        self.assertEqual(payload["reason"], "task_catalog_conflict")
        diagnostic = payload["catalog"]["diagnostics"][0]["diagnostic"]
        self.assertEqual(diagnostic["section"], "涉及面")
        self.assertGreater(diagnostic["line"], 0)
        run_git_mock.assert_not_called()

    def test_malformed_work_context_and_openspec_tables_report_lines(self) -> None:
        task = self._seed_task("T0001", "bad-tables")
        readme = (task / "README.md").read_text(encoding="utf-8")
        readme = readme.replace(
            "## 验收标准",
            """## 工作上下文

| 仓库 | 仓库路径 | checkout 路径 | worktree | 分支 | 基线 |
|------|----------|---------------|----------|------|------|
| svc | `svc` |

## 验收标准""",
        )
        (task / "README.md").write_text(readme, encoding="utf-8")
        self._write_index(next_id=2)
        code, payload = self._run("set-status", "T0001", "exploring")
        self.assertEqual(code, 1)
        self.assertEqual(payload["catalog"]["diagnostics"][0]["diagnostic"]["section"], "工作上下文")

        shutil.rmtree(task)
        task = self._seed_task("T0002", "bad-openspec")
        readme = (task / "README.md").read_text(encoding="utf-8").replace(
            "## 验收标准",
            """### 关联 OpenSpec

| change | 路径 |
|--------|------|
| only-one-cell |

## 验收标准""",
        )
        (task / "README.md").write_text(readme, encoding="utf-8")
        self._write_index(next_id=3)
        code, payload = self._run("set-status", "T0002", "exploring")
        self.assertEqual(code, 1)
        self.assertEqual(payload["catalog"]["diagnostics"][0]["diagnostic"]["section"], "关联 OpenSpec")

    def test_archive_requires_acceptance_structure(self) -> None:
        task = self._seed_task("T0001", "no-acceptance")
        readme = (task / "README.md").read_text(encoding="utf-8")
        readme = readme.split("## 验收标准", 1)[0] + "## Notes\n\nnone\n"
        (task / "README.md").write_text(readme, encoding="utf-8")
        (task / "changes.md").write_text("# Changes\n", encoding="utf-8")
        self._write_fresh_progress(task)
        self._write_index(next_id=2)
        code, payload = self._run("archive", "T0001", "--dry-run")
        self.assertEqual(code, 1)
        self.assertEqual(payload["reason"], "invalid_acceptance_structure")

    def test_execution_context_rejects_nonempty_openspec_store(self) -> None:
        task = self._seed_task("T0001", "store")
        readme = (task / "README.md").read_text(encoding="utf-8").replace(
            "## 验收标准",
            """### 关联 OpenSpec

| change | 路径 | 仓库 | store | 说明 |
|--------|------|------|-------|------|
| demo | `openspec/changes/demo` | | `external-store` | unsupported |

## 验收标准""",
        )
        (task / "README.md").write_text(readme, encoding="utf-8")
        self._write_index(next_id=2)
        code, payload = self._run("execution-context", "T0001")
        self.assertEqual(code, 1)
        self.assertEqual(payload["reason"], "unsupported_openspec_store")
        self.assertEqual(payload["store"], "external-store")

    def test_new_reports_structured_rollback_failure(self) -> None:
        with mock.patch.object(tc, "write_index", side_effect=OSError("primary index failure")), mock.patch.object(
            tc.shutil, "rmtree", side_effect=OSError("cleanup failed")
        ):
            code, payload = self._run("new", "--slug", "rollback-fails")
        self.assertEqual(code, 1)
        self.assertEqual(payload["reason"], "rollback_failed")
        self.assertIn("primary index failure", payload["primary_error"])
        self.assertTrue(any("cleanup failed" in error for error in payload["rollback_errors"]))
        self.assertTrue(payload["affected_paths"])
        self.assertIn("inspect", payload["recovery_hint"])

    def test_advance_reports_structured_rollback_failure(self) -> None:
        task = self._seed_task("T0001", "advance-rollback-fails")
        progress = task / "progress.md"
        progress.write_text("old progress\n", encoding="utf-8")
        self._write_index(next_id=2)
        real_atomic = tc.atomic_write_text

        def fail_progress_restore(path: Path, text: str) -> None:
            if Path(path) == progress and text == "old progress\n":
                raise OSError("progress restore failed")
            real_atomic(path, text)

        with mock.patch.object(tc, "write_index", side_effect=OSError("primary index failure")), mock.patch.object(
            tc, "atomic_write_text", side_effect=fail_progress_restore
        ):
            code, payload = self._run("advance", "T0001", "--phase", "implementing")
        self.assertEqual(code, 1)
        self.assertEqual(payload["reason"], "rollback_failed")
        self.assertIn("primary index failure", payload["primary_error"])
        self.assertTrue(any("progress restore failed" in error for error in payload["rollback_errors"]))

    def test_archive_reports_structured_rollback_failure(self) -> None:
        task = self._seed_task("T0001", "archive-rollback-fails")
        self._mark_archive_ready(task)
        self._write_index(next_id=2)
        real_move = shutil.move
        calls = 0

        def fail_move_back(src, dest):
            nonlocal calls
            calls += 1
            if calls == 1:
                return real_move(src, dest)
            raise OSError("archive move-back failed")

        with mock.patch.object(tc, "write_index", side_effect=OSError("primary index failure")), mock.patch.object(
            tc.shutil, "move", side_effect=fail_move_back
        ):
            code, payload = self._run("archive", "T0001")
        self.assertEqual(code, 1)
        self.assertEqual(payload["reason"], "rollback_failed")
        self.assertIn("primary index failure", payload["primary_error"])
        self.assertTrue(any("archive move-back failed" in error for error in payload["rollback_errors"]))
        self.assertTrue(any("archive" in path for path in payload["affected_paths"]))

    def test_restore_rollback_failure_is_structured(self) -> None:
        task = self._seed_task("T0001", "restore-structured")
        self._mark_archive_ready(task)
        self._write_index(next_id=2)
        code, _ = self._run("archive", "T0001")
        self.assertEqual(code, 0)
        real_move = shutil.move
        calls = 0

        def fail_move_back(src, dest):
            nonlocal calls
            calls += 1
            if calls == 1:
                return real_move(src, dest)
            raise OSError("restore move-back failed")

        with mock.patch.object(tc, "write_index", side_effect=OSError("primary index failure")), mock.patch.object(
            tc.shutil, "move", side_effect=fail_move_back
        ):
            code, payload = self._run("restore", "T0001")
        self.assertEqual(code, 1)
        self.assertEqual(payload["reason"], "rollback_failed")
        self.assertTrue(any("restore move-back failed" in error for error in payload["rollback_errors"]))

if __name__ == "__main__":
    unittest.main()
