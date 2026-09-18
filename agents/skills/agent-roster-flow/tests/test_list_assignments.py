"""list_assignments.py：从名册与 models.yaml 列出 Assignment 菜单。"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "list_assignments.py"


def run_script(*args: str, data_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--data-root", str(data_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )


class ListAssignmentsTest(unittest.TestCase):
    def _write_roster(self, tmp: Path) -> Path:
        data = tmp / "data"
        host = data / "agents" / "testhost"
        host.mkdir(parents=True)
        (host / "cursor.md").write_text(
            "# testhost/cursor\n\n- **模型**: grok-4.6\n",
            encoding="utf-8",
        )
        (host / "codex.md").write_text(
            "# testhost/codex\n\n- **模型**: <探测不到,留空>\n",
            encoding="utf-8",
        )
        (data / "agents" / "models.yaml").write_text(
            "cursor:\n  - grok-4.6\n  - claude-opus-4\ncodex:\n  - gpt-5.2\n",
            encoding="utf-8",
        )
        (data / "agents" / "README.md").write_text("ignore\n", encoding="utf-8")
        (data / "agents" / "traces").mkdir()
        (data / "agents" / "traces" / "note.md").write_text("not an endpoint\n", encoding="utf-8")
        return data

    def test_lists_endpoints_and_merges_models(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            data = self._write_roster(Path(raw))
            done = run_script(data_root=data)
            self.assertEqual(done.returncode, 0, done.stderr)
            payload = json.loads(done.stdout)
            endpoints = {row["endpoint"]: row for row in payload["endpoints"]}
            self.assertIn("testhost/cursor", endpoints)
            self.assertIn("testhost/codex", endpoints)
            self.assertNotIn("testhost/README", endpoints)
            self.assertEqual(
                endpoints["testhost/cursor"]["models"],
                ["grok-4.6", "claude-opus-4"],
            )
            self.assertEqual(endpoints["testhost/cursor"]["default_model"], "grok-4.6")
            self.assertIsNone(endpoints["testhost/codex"]["default_model"])
            self.assertEqual(endpoints["testhost/codex"]["models"], ["gpt-5.2"])
            self.assertFalse(payload["human_allowed"])

    def test_human_only_on_plan_review_and_wrap_up(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            data = self._write_roster(Path(raw))
            review = json.loads(run_script("--stage", "plan-review", data_root=data).stdout)
            wrap = json.loads(run_script("--stage", "wrap-up", data_root=data).stdout)
            code = json.loads(run_script("--stage", "code-review", data_root=data).stdout)
            self.assertTrue(review["human_allowed"])
            self.assertTrue(wrap["human_allowed"])
            self.assertFalse(code["human_allowed"])

    def test_missing_config_fails(self) -> None:
        done = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--config",
                "/no/such/agent-roster-config.yaml",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(done.returncode, 2)
        self.assertIn("missing agent-roster config", done.stderr)

    def test_render_includes_human_row(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            data = self._write_roster(Path(raw))
            done = run_script("--stage", "plan-review", "--render", data_root=data)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn("`human`", done.stdout)
            self.assertIn("`testhost/cursor`", done.stdout)


if __name__ == "__main__":
    unittest.main()
