from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reviewctl.py"


def load_reviewctl():
    spec = importlib.util.spec_from_file_location("reviewctl", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["reviewctl"] = mod
    spec.loader.exec_module(mod)
    return mod


rc = load_reviewctl()


class ReviewctlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "repos").mkdir()

    def _git(self, repo: Path, *args: str) -> None:
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

    def _init_repo(self, rel: str, name: str | None = None) -> Path:
        repo = self.tmp / "repos" / rel
        repo.mkdir(parents=True)
        self._git(repo, "init")
        self._git(repo, "config", "user.email", "test@example.invalid")
        self._git(repo, "config", "user.name", "tester")
        (repo / "README").write_text("init\n", encoding="utf-8")
        self._git(repo, "add", ".")
        self._git(repo, "commit", "-m", "init")
        self._git(repo, "branch", "-M", "main")
        if name:
            pass
        return repo

    def test_resolve_by_basename_and_ambiguous(self) -> None:
        self._init_repo("group/service")
        hit = rc.resolve_repo(self.tmp, "service")
        self.assertEqual(hit["basename"], "service")
        self.assertTrue(hit["git_root"].endswith("service"))

        self._init_repo("other/service")
        amb = rc.resolve_repo(self.tmp, "service")
        self.assertTrue(amb.get("ambiguous"))
        self.assertEqual(len(amb["candidates"]), 2)

    def test_inspect_recommends_uncommitted_vs_default_branch(self) -> None:
        repo = self._init_repo("svc")
        (repo / "dirty.txt").write_text("x\n", encoding="utf-8")
        payload = rc.inspect_repo(self.tmp, "svc")
        self.assertEqual(payload["recommendation"], "uncommitted")
        self.assertTrue(payload["needs_confirm"])

        self._git(repo, "add", "dirty.txt")
        self._git(repo, "commit", "-m", "dirty")
        self._git(repo, "checkout", "-b", "feat-x")
        (repo / "feat.txt").write_text("y\n", encoding="utf-8")
        self._git(repo, "add", "feat.txt")
        self._git(repo, "commit", "-m", "feat")
        payload = rc.inspect_repo(self.tmp, "svc")
        self.assertEqual(payload["recommendation"], "default-branch")
        self.assertEqual(payload["ahead_of_default"], 1)

        (repo / "wip.txt").write_text("z\n", encoding="utf-8")
        payload = rc.inspect_repo(self.tmp, "svc")
        self.assertEqual(payload["recommendation"], "ask")

    def test_parse_mr_urls(self) -> None:
        gl = rc.parse_mr_url("https://gitlab.example.invalid/group/service/-/merge_requests/88")
        self.assertEqual(gl["kind"], "gitlab")
        self.assertEqual(gl["project"], "group/service")
        self.assertEqual(gl["iid"], 88)
        self.assertEqual(gl["repo_hint"], "service")

        gh = rc.parse_mr_url("https://github.example.invalid/example-org/example-repo/pull/12")
        self.assertEqual(gh["kind"], "github")
        self.assertEqual(gh["project"], "example-org/example-repo")
        self.assertEqual(gh["iid"], 12)

    def test_change_name_and_priority(self) -> None:
        self.assertEqual(
            rc.change_name(repo_basename="service", mode="mr", mr_iid=88, title="Fix timeout"),
            "service-mr-88-fix-timeout",
        )
        self.assertEqual(rc.classify_priority("SQL injection in query builder"), "P0")
        self.assertEqual(rc.classify_priority("nil deref on empty payload"), "P1")
        self.assertEqual(rc.classify_priority("missing test for retry path"), "P2")
        self.assertEqual(rc.classify_priority("rename helper for clarity"), "P3")

    def test_write_review_sorted_summary(self) -> None:
        ocr = {
            "status": "success",
            "session_id": "abc",
            "summary": {"files_reviewed": 2, "comments": 2, "elapsed": "1s"},
            "comments": [
                {"path": "b.go", "content": "rename helper for clarity", "start_line": 3, "end_line": 3},
                {
                    "path": "a.go",
                    "content": "SQL injection in query builder",
                    "start_line": 10,
                    "end_line": 12,
                    "existing_code": "db.Exec(q)",
                    "suggestion_code": "db.Exec(q, args)",
                    "thinking": "user input concatenated",
                },
            ],
        }
        meta = {
            "repo": "group/service",
            "mode": "default-branch",
            "date": "2026-08-13",
            "change_name": "service-feat-x",
            "branch": "feat-x",
            "from": "origin/main",
            "to": "HEAD",
        }
        result = rc.write_review(self.tmp, ocr, meta)
        review = (self.tmp / result["review"]).read_text(encoding="utf-8")
        self.assertIn("### P0", review)
        self.assertIn("### P3", review)
        self.assertLess(review.index("### P0"), review.index("### P3"))
        summary = result["summary"]
        self.assertIn("P0=1", summary)
        self.assertIn("[P0] SQL injection", summary)
        self.assertTrue(summary.index("### P0") < summary.index("### P3"))
        self.assertTrue((self.tmp / "docs/reviews/INDEX.md").exists())
        printed = rc.render_summary(meta, [], result["review"])
        self.assertIn("No findings.", printed)


if __name__ == "__main__":
    unittest.main()
