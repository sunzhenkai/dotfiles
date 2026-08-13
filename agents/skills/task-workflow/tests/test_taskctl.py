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
{openspec_block}
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
        index = (self.tmp / "tasks/INDEX.md").read_text()
        self.assertIn("next_id: 2", index)
        code, payload = self._run("list")
        self.assertEqual(code, 0)
        self.assertEqual(len(payload["tasks"]), 1)

    def test_new_rejects_bad_slug(self) -> None:
        code, payload = self._run("new", "--slug", "Bad_Slug")
        self.assertEqual(code, 1)
        self.assertIn("invalid slug", payload["error"])

    def test_archive(self) -> None:
        root = self._seed_task("T0001", "alpha", openspec=True)
        (root / "changes.md").write_text("# changes\n", encoding="utf-8")
        self._write_index(next_id=2)
        code, payload = self._run("archive", "T0001", "--date", "2026-08-20")
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

    def test_openspec_parse(self) -> None:
        self._seed_task("T0002", "beta", openspec=True)
        self._write_index()
        code, payload = self._run("resolve", "T0002")
        self.assertEqual(code, 0)
        self.assertEqual(payload["task"]["openspec"][0]["name"], "demo-change")

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
        code, payload = self._run("repo-roots", "no-such")
        self.assertEqual(code, 1)
        self.assertIn("does not exist", payload["errors"][0]["error"])
        self._init_git_repo(".")
        code, payload = self._run("repo-roots", ".")
        self.assertEqual(code, 0)
        self.assertEqual(payload["repos"][0]["git_root"], "./")

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

    def test_git_summary(self) -> None:
        repo = self._init_git_repo("svc")
        self._git(repo, "checkout", "-b", "feat-sum")
        (repo / "a.txt").write_text("a\n", encoding="utf-8")
        self._git(repo, "add", ".")
        self._git(repo, "commit", "-m", "add a")
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


if __name__ == "__main__":
    unittest.main()
