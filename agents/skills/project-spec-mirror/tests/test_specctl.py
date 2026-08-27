"""specctl 回归测试。

覆盖放置判定、init 确认门、git 同步指针、清单忽略与符号提取。
不测 JSON 排版与 stderr 措辞。
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "specctl.py"
sys.path.insert(0, str(SCRIPT.parent))

import specctl  # noqa: E402


def run(*args: str, cwd: Path | None = None) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    return proc.returncode, payload


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )


def make_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q")
    git(path, "config", "user.email", "dev@example.com")
    git(path, "config", "user.name", "example")
    git(path, "config", "commit.gpgsign", "false")
    (path / "go.mod").write_text("module example.com/example-api\n", encoding="utf-8")
    (path / "internal").mkdir()
    (path / "internal" / "order.go").write_text(
        "package order\n\nfunc Place() {}\n\nfunc Cancel() {}\n",
        encoding="utf-8",
    )
    (path / "README.md").write_text("# example-api\n", encoding="utf-8")
    git(path, "add", ".")
    git(path, "commit", "-q", "-m", "init")
    git(path, "branch", "-M", "main")
    return path


class DetectTest(unittest.TestCase):
    def test_project_root_places_spec_here(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            code, payload = run("detect", "--cwd", str(root))
            self.assertEqual(code, 0)
            self.assertTrue(payload["is_project_root"])
            self.assertEqual(payload["placement"], "in-project")
            self.assertEqual(payload["spec_root"], str(root / "spec"))
            self.assertEqual(payload["project"], "example-api")

    def test_non_project_requires_project_or_source(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            notes = Path(raw) / "notes"
            notes.mkdir()
            code, payload = run("detect", "--cwd", str(notes))
            self.assertEqual(code, 1)
            self.assertEqual(payload["reason"], "project_required")

    def test_external_placement_uses_project_slug(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            notes = Path(raw) / "notes"
            notes.mkdir()
            src = make_repo(Path(raw) / "example-api")
            code, payload = run(
                "detect",
                "--cwd",
                str(notes),
                "--source",
                str(src),
                "--project",
                "example-api",
            )
            self.assertEqual(code, 0)
            self.assertEqual(payload["placement"], "external")
            self.assertEqual(payload["spec_root"], str(notes / "spec" / "example-api"))


class InitTest(unittest.TestCase):
    def test_init_without_confirm_exits_2(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            code, payload = run("init", "--cwd", str(root))
            self.assertEqual(code, 2)
            self.assertEqual(payload["reason"], "create_spec_dir")
            self.assertFalse((root / "spec").exists())
            self.assertIn("--confirm", payload["confirm_args"])

    def test_init_confirm_creates_skeleton(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            code, payload = run("init", "--cwd", str(root), "--confirm")
            self.assertEqual(code, 0, payload)
            spec = root / "spec"
            self.assertTrue((spec / ".mirror.json").is_file())
            self.assertTrue((spec / "README.md").is_file())
            self.assertTrue((spec / "concepts" / "INDEX.md").is_file())
            state = json.loads((spec / ".mirror.json").read_text(encoding="utf-8"))
            self.assertEqual(state["placement"], "in-project")
            self.assertEqual(state["source"], "..")
            self.assertEqual(state["mode"], "concise")
            self.assertIsNone(state["synced_commit"])

    def test_occupied_spec_dir_exits_2(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            spec = root / "spec"
            spec.mkdir()
            (spec / "other.md").write_text("not a mirror\n", encoding="utf-8")
            code, payload = run("init", "--cwd", str(root), "--confirm")
            self.assertEqual(code, 2)
            self.assertEqual(payload["reason"], "spec_dir_occupied")

    def test_in_project_from_subdir(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            sub = root / "internal"
            code, payload = run(
                "init", "--cwd", str(sub), "--in-project", "--confirm"
            )
            self.assertEqual(code, 0, payload)
            self.assertTrue((root / "spec" / ".mirror.json").is_file())
            self.assertEqual(payload["placement"], "in-project")


class GitAndSyncTest(unittest.TestCase):
    def test_diff_then_set_sync(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            code, _ = run("init", "--cwd", str(root), "--confirm")
            self.assertEqual(code, 0)
            sha = git(root, "rev-parse", "HEAD").stdout.strip()
            code, payload = run("diff", "--cwd", str(root))
            self.assertEqual(code, 0)
            self.assertTrue(payload["full"])
            self.assertEqual(payload["to"], sha)

            (root / "internal" / "order.go").write_text(
                "package order\n\nfunc Place() {}\n\nfunc Cancel() {}\n\nfunc Get() {}\n",
                encoding="utf-8",
            )
            git(root, "add", ".")
            git(root, "commit", "-q", "-m", "add Get")
            new_sha = git(root, "rev-parse", "HEAD").stdout.strip()

            code, payload = run("set-sync", "--cwd", str(root), "--commit", sha)
            self.assertEqual(code, 0, payload)
            code, payload = run("diff", "--cwd", str(root))
            self.assertEqual(code, 0, payload)
            self.assertFalse(payload["full"])
            paths = {item["path"] for item in payload["files"]}
            self.assertIn("internal/order.go", paths)

            code, payload = run("status", "--cwd", str(root))
            self.assertEqual(code, 0)
            self.assertFalse(payload["freshness"]["in_sync"])
            self.assertTrue(payload["freshness"]["is_ancestor"])

            code, payload = run("set-sync", "--cwd", str(root), "--commit", new_sha)
            self.assertEqual(code, 0)
            code, payload = run("status", "--cwd", str(root))
            self.assertTrue(payload["freshness"]["in_sync"])

    def test_inventory_skips_secrets_and_vendor(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            (root / ".env").write_text("SECRET=1\n", encoding="utf-8")
            (root / "vendor" / "lib.go").parent.mkdir()
            (root / "vendor" / "lib.go").write_text("package vendor\n", encoding="utf-8")
            git(root, "add", "-f", ".env", "vendor/lib.go")
            git(root, "commit", "-q", "-m", "noise")
            run("init", "--cwd", str(root), "--confirm")
            code, payload = run("inventory", "--cwd", str(root))
            self.assertEqual(code, 0)
            names = payload["files"]
            self.assertNotIn(".env", names)
            self.assertTrue(all(not item.startswith("vendor/") for item in names))
            self.assertIn("internal/order.go", names)


class SymbolsTest(unittest.TestCase):
    def test_python_ast_and_go_regex(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "demo"
            root.mkdir()
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            (root / "app.py").write_text(
                "VALUE = 1\n_hidden = 2\n\nclass Order:\n    def place(self):\n        return 1\n\ndef cancel():\n    return 0\n",
                encoding="utf-8",
            )
            (root / "order.go").write_text(
                "package order\n\nfunc Place() {}\n",
                encoding="utf-8",
            )
            code, payload = run("init", "--cwd", str(root), "--confirm")
            self.assertEqual(code, 0, payload)
            code, payload = run(
                "symbols", "--cwd", str(root), "--file", "app.py", "--file", "order.go"
            )
            self.assertEqual(code, 0, payload)
            by_path = {item["path"]: item["symbols"] for item in payload["files"]}
            py_names = {item["name"] for item in by_path["app.py"]}
            self.assertIn("VALUE", py_names)
            self.assertIn("Order", py_names)
            self.assertIn("Order.place", py_names)
            self.assertIn("cancel", py_names)
            self.assertNotIn("_hidden", py_names)
            go_names = {item["name"] for item in by_path["order.go"]}
            self.assertIn("Place", go_names)


class ValidateTest(unittest.TestCase):
    def test_validate_ok_after_init(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            run("init", "--cwd", str(root), "--confirm")
            code, payload = run("validate", "--cwd", str(root))
            self.assertEqual(code, 0, payload)
            self.assertEqual(payload["issues"], [])

    def test_direct_helpers_secret_skip(self) -> None:
        self.assertTrue(specctl.should_skip_file(".env.local"))
        self.assertTrue(specctl.should_skip_file("certs/server.pem"))
        self.assertFalse(specctl.should_skip_file("internal/order.go"))


if __name__ == "__main__":
    unittest.main()
