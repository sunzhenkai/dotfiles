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

    def test_foreign_source_from_workspace_git_root(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw) / "workspace"
            workspace.mkdir()
            git(workspace, "init", "-q")
            git(workspace, "config", "user.email", "dev@example.com")
            git(workspace, "config", "user.name", "example")
            git(workspace, "config", "commit.gpgsign", "false")
            (workspace / "Makefile").write_text("all:\n\ttrue\n", encoding="utf-8")
            git(workspace, "add", ".")
            git(workspace, "commit", "-q", "-m", "workspace")
            git(workspace, "branch", "-M", "main")
            other = make_repo(Path(raw) / "other-lib")
            code, payload = run(
                "detect",
                "--cwd",
                str(workspace),
                "--project",
                "other-lib",
                "--source",
                str(other),
            )
            self.assertEqual(code, 0, payload)
            self.assertEqual(payload["placement"], "external")
            self.assertEqual(payload["spec_root"], str(workspace / "spec" / "other-lib"))
            self.assertEqual(payload["source"], str(other.resolve()))

    def test_foreign_project_flag_without_source(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw) / "workspace"
            workspace.mkdir()
            git(workspace, "init", "-q")
            git(workspace, "config", "user.email", "dev@example.com")
            git(workspace, "config", "user.name", "example")
            git(workspace, "config", "commit.gpgsign", "false")
            (workspace / "Makefile").write_text("all:\n\ttrue\n", encoding="utf-8")
            git(workspace, "add", ".")
            git(workspace, "commit", "-q", "-m", "workspace")
            git(workspace, "branch", "-M", "main")
            code, payload = run(
                "detect", "--cwd", str(workspace), "--project", "other-lib"
            )
            self.assertEqual(code, 0, payload)
            self.assertEqual(payload["placement"], "external")
            self.assertEqual(payload["spec_root"], str(workspace / "spec" / "other-lib"))
            self.assertIsNone(payload["source"])

    def test_matching_project_name_stays_in_project(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            code, payload = run(
                "detect", "--cwd", str(root), "--project", "example-api"
            )
            self.assertEqual(code, 0, payload)
            self.assertEqual(payload["placement"], "in-project")
            self.assertEqual(payload["spec_root"], str(root / "spec"))

    def test_init_foreign_source_creates_named_spec(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw) / "workspace"
            workspace.mkdir()
            git(workspace, "init", "-q")
            git(workspace, "config", "user.email", "dev@example.com")
            git(workspace, "config", "user.name", "example")
            git(workspace, "config", "commit.gpgsign", "false")
            (workspace / "Makefile").write_text("all:\n\ttrue\n", encoding="utf-8")
            git(workspace, "add", ".")
            git(workspace, "commit", "-q", "-m", "workspace")
            git(workspace, "branch", "-M", "main")
            other = make_repo(Path(raw) / "other-lib")
            code, payload = run(
                "init",
                "--cwd",
                str(workspace),
                "--project",
                "other-lib",
                "--source",
                str(other),
                "--confirm",
            )
            self.assertEqual(code, 0, payload)
            spec = workspace / "spec" / "other-lib"
            self.assertTrue((spec / ".mirror.json").is_file())
            self.assertFalse((workspace / "spec" / ".mirror.json").exists())
            state = json.loads((spec / ".mirror.json").read_text(encoding="utf-8"))
            self.assertEqual(state["placement"], "external")
            self.assertEqual(state["project"], "other-lib")


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
            self.assertTrue((spec / "context" / "INDEX.md").is_file())
            self.assertTrue((spec / "data" / "INDEX.md").is_file())
            self.assertTrue((spec / "surface" / "INDEX.md").is_file())
            self.assertTrue((spec / "surface" / "config.md").is_file())
            self.assertTrue((spec / "runtime" / "INDEX.md").is_file())
            self.assertTrue((spec / "build" / "INDEX.md").is_file())
            self.assertTrue((spec / "facets" / "INDEX.md").is_file())
            self.assertTrue((spec / "diagrams" / "INDEX.md").is_file())
            state = json.loads((spec / ".mirror.json").read_text(encoding="utf-8"))
            self.assertEqual(state["placement"], "in-project")
            self.assertEqual(state["source"], "..")
            self.assertEqual(state["mode"], "concise")
            self.assertEqual(state["detail_level"], "important")
            self.assertEqual(state.get("hotspots"), [])
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
            (root / "node_modules" / "pkg" / "index.js").parent.mkdir(parents=True)
            (root / "node_modules" / "pkg" / "index.js").write_text("module.exports = 1\n", encoding="utf-8")
            git(root, "add", "-f", ".env", "vendor/lib.go", "node_modules/pkg/index.js")
            git(root, "commit", "-q", "-m", "noise")
            run("init", "--cwd", str(root), "--confirm")
            code, payload = run("inventory", "--cwd", str(root))
            self.assertEqual(code, 0)
            names = payload["files"]
            self.assertNotIn(".env", names)
            self.assertTrue(all(not item.startswith("vendor/") for item in names))
            self.assertTrue(all(not item.startswith("node_modules/") for item in names))
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
        self.assertTrue(specctl.should_skip_file("vendor/github.com/foo/lib.go"))
        self.assertTrue(specctl.should_skip_file("node_modules/pkg/index.js"))
        self.assertFalse(specctl.should_skip_file("internal/order.go"))
        self.assertFalse(specctl.should_skip_file("src/App.php"))

    def test_diff_skips_vendor_changes(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            run("init", "--cwd", str(root), "--confirm")
            sha = git(root, "rev-parse", "HEAD").stdout.strip()
            run("set-sync", "--cwd", str(root), "--commit", sha)
            (root / "vendor" / "lib.go").parent.mkdir()
            (root / "vendor" / "lib.go").write_text("package vendor\n", encoding="utf-8")
            (root / "internal" / "order.go").write_text(
                "package order\n\nfunc Place() {}\n\nfunc Cancel() {}\n\nfunc Get() {}\n",
                encoding="utf-8",
            )
            git(root, "add", "-f", "vendor/lib.go", "internal/order.go")
            git(root, "commit", "-q", "-m", "vendor and code")
            code, payload = run("diff", "--cwd", str(root))
            self.assertEqual(code, 0, payload)
            paths = {item["path"] for item in payload["files"]}
            self.assertIn("internal/order.go", paths)
            self.assertTrue(all(not item.startswith("vendor/") for item in paths))

    def test_inventory_skips_nested_git_on_nongit_source(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "app"
            root.mkdir()
            (root / "composer.json").write_text("{\n}\n", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "App.php").write_text("<?php\n", encoding="utf-8")
            nested = make_repo(Path(raw) / "app" / "libs" / "other")
            self.assertTrue((nested / "internal" / "order.go").is_file())
            run("init", "--cwd", str(root), "--confirm")
            code, payload = run("inventory", "--cwd", str(root))
            self.assertEqual(code, 0, payload)
            names = payload["files"]
            self.assertIn("src/App.php", names)
            self.assertTrue(all(not item.startswith("libs/other") for item in names))

    def test_inventory_skips_gitlink(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            nested = make_repo(Path(raw) / "other-lib")
            sha = git(nested, "rev-parse", "HEAD").stdout.strip()
            root = make_repo(Path(raw) / "example-api")
            git(
                root,
                "update-index",
                "--add",
                "--cacheinfo",
                f"160000,{sha},libs/other-lib",
            )
            git(root, "commit", "-q", "-m", "gitlink")
            run("init", "--cwd", str(root), "--confirm")
            code, payload = run("inventory", "--cwd", str(root))
            self.assertEqual(code, 0, payload)
            names = payload["files"]
            self.assertIn("internal/order.go", names)
            self.assertNotIn("libs/other-lib", names)
            self.assertTrue(all(not item.startswith("libs/other-lib") for item in names))

    def test_symbols_skips_vendor(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            (root / "vendor" / "lib.go").parent.mkdir()
            (root / "vendor" / "lib.go").write_text(
                "package vendor\n\nfunc Ignore() {}\n", encoding="utf-8"
            )
            git(root, "add", "-f", "vendor/lib.go")
            git(root, "commit", "-q", "-m", "vendor")
            run("init", "--cwd", str(root), "--confirm")
            code, payload = run(
                "symbols", "--cwd", str(root), "--file", "vendor/lib.go"
            )
            self.assertEqual(code, 0, payload)
            item = payload["files"][0]
            self.assertTrue(item.get("skipped"))
            self.assertEqual(item.get("reason"), "third_party")
            self.assertEqual(item["symbols"], [])


ORDER_README = """# order

## 根

| 路径前缀 | 角色 |
|----------|------|
| `internal` | 领域包 |

## 文件

| 文件 | 职责 | 核心 |
|------|------|------|
| `internal/order.go` | 下单与取消 | `Place`, `Cancel` |
"""


def write_order_module(spec: Path) -> None:
    readme = spec / "modules" / "order" / "README.md"
    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_text(ORDER_README, encoding="utf-8")


class RouteParseTest(unittest.TestCase):
    def test_parse_root_and_files_tables(self) -> None:
        roots, files = specctl.parse_module_readme(ORDER_README)
        self.assertEqual(roots, ["internal"])
        self.assertEqual(files, ["internal/order.go"])

    def test_parse_english_headings(self) -> None:
        text = """# billing

## Roots

| prefix | role |
|--------|------|
| `internal/bill` | domain |

## Files

| file | duty |
|------|------|
| [`internal/bill/calc.go`](unused) | calc |
"""
        roots, files = specctl.parse_module_readme(text)
        self.assertEqual(roots, ["internal/bill"])
        self.assertEqual(files, ["internal/bill/calc.go"])


class RouteTest(unittest.TestCase):
    def test_not_built_lists_unmapped(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            code, payload = run("route", "--cwd", str(root))
            self.assertEqual(code, 0, payload)
            self.assertTrue(payload["not_built"])
            self.assertEqual(payload["note"], "not_built")
            self.assertEqual(payload["modules"], [])
            self.assertIn("internal/order.go", payload["unmapped"])

    def test_file_table_and_root_prefix_and_unmapped(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            write_order_module(root / "spec")
            sha = git(root, "rev-parse", "HEAD").stdout.strip()
            self.assertEqual(
                run("set-sync", "--cwd", str(root), "--commit", sha)[0], 0
            )
            (root / "internal" / "order.go").write_text(
                "package order\n\nfunc Place() {}\n\nfunc Cancel() {}\n\nfunc Get() {}\n",
                encoding="utf-8",
            )
            (root / "internal" / "extra.go").write_text(
                "package order\n\nfunc Extra() {}\n", encoding="utf-8"
            )
            (root / "scripts").mkdir()
            (root / "scripts" / "one-off.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-q", "-m", "more files")
            code, payload = run("route", "--cwd", str(root))
            self.assertEqual(code, 0, payload)
            self.assertFalse(payload["not_built"])
            by_path = {item["path"]: item for item in payload["changes"]}
            self.assertEqual(by_path["internal/order.go"]["via"], "file-table")
            self.assertEqual(by_path["internal/order.go"]["modules"], ["order"])
            self.assertEqual(by_path["internal/extra.go"]["via"], "root-prefix")
            self.assertEqual(by_path["internal/extra.go"]["modules"], ["order"])
            self.assertEqual(by_path["scripts/one-off.sh"]["via"], "unmapped")
            self.assertIn("scripts/one-off.sh", payload["unmapped"])
            self.assertEqual(payload["modules"], ["order"])
            self.assertEqual(payload["pages"], ["modules/order/README.md"])

    def test_rename_uses_from_file_table(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            write_order_module(root / "spec")
            sha = git(root, "rev-parse", "HEAD").stdout.strip()
            self.assertEqual(
                run("set-sync", "--cwd", str(root), "--commit", sha)[0], 0
            )
            git(root, "mv", "internal/order.go", "internal/placed.go")
            git(root, "commit", "-q", "-m", "rename order")
            code, payload = run("route", "--cwd", str(root))
            self.assertEqual(code, 0, payload)
            self.assertEqual(payload["renames"][0]["from"], "internal/order.go")
            self.assertEqual(payload["renames"][0]["to"], "internal/placed.go")
            self.assertEqual(payload["renames"][0]["module"], "order")
            rec = payload["changes"][0]
            self.assertEqual(rec["via"], "file-table")
            self.assertEqual(rec["from"], "internal/order.go")

    def test_set_sync_hotspot_replaces_list(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            code, payload = run(
                "set-sync",
                "--cwd",
                str(root),
                "--hotspot",
                "internal/order.go",
                "--hotspot",
                "cmd/orderd/main.go",
            )
            self.assertEqual(code, 0, payload)
            self.assertEqual(
                payload["state"]["hotspots"],
                ["internal/order.go", "cmd/orderd/main.go"],
            )
            code, payload = run(
                "set-sync", "--cwd", str(root), "--hotspot", "internal/extra.go"
            )
            self.assertEqual(code, 0, payload)
            self.assertEqual(payload["state"]["hotspots"], ["internal/extra.go"])
            code, payload = run("validate", "--cwd", str(root))
            self.assertEqual(code, 0, payload)
            self.assertEqual(payload["issues"], [])


if __name__ == "__main__":
    unittest.main()
