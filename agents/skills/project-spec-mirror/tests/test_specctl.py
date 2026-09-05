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
from unittest.mock import patch

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
            with patch.object(specctl, "nearest_project_root", return_value=None):
                with self.assertRaises(specctl.SpecError) as raised:
                    specctl.detect_layout(notes)
            self.assertEqual(raised.exception.reason, "project_required")

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
            self.assertTrue((spec / "briefing" / "overview.md").is_file())
            self.assertTrue((spec / "briefing" / "architecture.md").is_file())
            self.assertTrue((spec / "briefing" / "concepts" / "INDEX.md").is_file())
            self.assertTrue((spec / "briefing" / "flows" / "INDEX.md").is_file())
            self.assertTrue((spec / "briefing" / "diagrams" / "INDEX.md").is_file())
            self.assertTrue((spec / "agent" / "INDEX.md").is_file())
            self.assertTrue((spec / "agent" / "model" / "INDEX.md").is_file())
            self.assertTrue((spec / "agent" / "surface" / "INDEX.md").is_file())
            self.assertTrue((spec / "agent" / "data" / "INDEX.md").is_file())
            self.assertTrue((spec / "evidence" / "source-map.md").is_file())
            self.assertFalse((spec / "facets" / "INDEX.md").exists())
            self.assertFalse((spec / "runtime" / "INDEX.md").exists())
            state = json.loads((spec / ".mirror.json").read_text(encoding="utf-8"))
            self.assertEqual(state["placement"], "in-project")
            self.assertEqual(state["source"], "..")
            self.assertEqual(state["mode"], "briefing")
            self.assertNotIn("detail_level", state)
            self.assertNotIn("scope", state)
            self.assertEqual(state["build_status"], "skeleton")
            self.assertIsNone(state["built_at"])
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

    def test_reconstructable_init_mode(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            code, payload = run(
                "init", "--cwd", str(root), "--mode", "reconstructable", "--confirm"
            )
            self.assertEqual(code, 0, payload)
            self.assertEqual(payload["mode"], "reconstructable")
            state = json.loads(
                (root / "spec" / ".mirror.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["mode"], "reconstructable")


class GitAndSyncTest(unittest.TestCase):
    def test_diff_then_finalize(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            code, _ = run("init", "--cwd", str(root), "--confirm")
            self.assertEqual(code, 0)
            write_minimum_content(root / "spec")
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

            code, payload = run("finalize", "--cwd", str(root), "--commit", sha)
            self.assertEqual(code, 0, payload)
            code, payload = run("diff", "--cwd", str(root))
            self.assertEqual(code, 0, payload)
            self.assertFalse(payload["full"])
            paths = {item["path"] for item in payload["files"]}
            self.assertIn("internal/order.go", paths)

            code, payload = run("status", "--cwd", str(root))
            self.assertEqual(code, 0)
            self.assertEqual(payload["layout"], "current")
            self.assertFalse(payload["freshness"]["in_sync"])
            self.assertTrue(payload["freshness"]["is_ancestor"])

            code, payload = run("finalize", "--cwd", str(root), "--commit", new_sha)
            self.assertEqual(code, 0, payload)
            code, payload = run("status", "--cwd", str(root))
            self.assertTrue(payload["freshness"]["in_sync"])
            self.assertEqual(payload["build_status"], "built")
            self.assertEqual(payload["phase"], "update")
            readme = (root / "spec" / "README.md").read_text(encoding="utf-8")
            self.assertIn(f"| 同步 commit | `{new_sha[:12]}` |", readme)
            self.assertIn("| 粒度 | briefing |", readme)
            self.assertNotIn("文件粒度", readme)

    def test_non_git_build_has_status_without_fake_commit(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "demo"
            root.mkdir()
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            write_minimum_content(root / "spec")
            code, payload = run("finalize", "--cwd", str(root))
            self.assertEqual(code, 0, payload)
            self.assertEqual(payload["state"]["build_status"], "built")
            self.assertIsNone(payload["state"]["synced_commit"])
            code, status = run("status", "--cwd", str(root))
            self.assertEqual(code, 0, status)
            self.assertEqual(status["phase"], "update")
            self.assertEqual(status["freshness"]["kind"], "non-git")

            code, payload = run("finalize", "--cwd", str(root), "--commit", "fake")
            self.assertEqual(code, 1, payload)
            self.assertEqual(payload["reason"], "commit_not_supported")

    def test_finalize_does_not_advance_invalid_skeleton(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            sha = git(root, "rev-parse", "HEAD").stdout.strip()
            (root / "spec" / "briefing" / "overview.md").unlink()
            code, payload = run("finalize", "--cwd", str(root), "--commit", sha)
            self.assertEqual(code, 1, payload)
            self.assertIn(payload["reason"], {"coverage_missing", "legacy_layout"})
            state = json.loads(
                (root / "spec" / ".mirror.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["build_status"], "skeleton")
            self.assertIsNone(state["synced_commit"])

    def test_empty_reconstructable_cannot_mark_built(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(
                run(
                    "init",
                    "--cwd",
                    str(root),
                    "--mode",
                    "reconstructable",
                    "--confirm",
                )[0],
                0,
            )
            sha = git(root, "rev-parse", "HEAD").stdout.strip()
            code, payload = run("finalize", "--cwd", str(root), "--commit", sha)
            self.assertEqual(code, 1, payload)
            self.assertEqual(payload["reason"], "coverage_missing")

    def test_retired_commands_are_not_public(self) -> None:
        code, payload = run("set-sync")
        self.assertEqual(code, 1, payload)
        self.assertEqual(payload["reason"], "usage")
        for name in ("validate", "coverage", "inventory", "symbols", "git-info"):
            code, payload = run(name)
            self.assertEqual(code, 1, payload)
            self.assertEqual(payload["reason"], "usage")

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
            names = specctl.inventory_files(root)
            self.assertNotIn(".env", names)
            self.assertTrue(all(not item.startswith("vendor/") for item in names))
            self.assertTrue(all(not item.startswith("node_modules/") for item in names))
            self.assertIn("internal/order.go", names)

    def test_inventory_skips_tracked_ignored_and_non_text_files(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            (root / "ignored.log").write_text("ignored\n", encoding="utf-8")
            (root / "opaque.data").write_bytes(b"plain\0binary")
            git(root, "add", "ignored.log", "opaque.data")
            git(root, "commit", "-q", "-m", "add generated artifacts")
            (root / ".gitignore").write_text(
                "ignored.log\n",
                encoding="utf-8",
            )
            git(root, "add", ".gitignore")
            git(root, "commit", "-q", "-m", "ignore generated log")
            names = specctl.inventory_files(root)
            self.assertNotIn("ignored.log", names)
            self.assertNotIn("opaque.data", names)
            self.assertIn(".gitignore", names)
            ignored = specctl.inspect_symbols(root, "ignored.log")
            self.assertEqual(ignored["reason"], "ignored")
            opaque = specctl.inspect_symbols(root, "opaque.data")
            self.assertEqual(opaque["reason"], "non_text")


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
            files = [
                specctl.inspect_symbols(root, "app.py"),
                specctl.inspect_symbols(root, "order.go"),
            ]
            by_path = {item["path"]: item["symbols"] for item in files}
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
            spec = root / "spec"
            issues = specctl.validation_issues(spec, specctl.load_state(spec))
            self.assertEqual(issues, [])

    def test_validate_rejects_explicit_invalid_build_status(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            run("init", "--cwd", str(root), "--confirm")
            state_path = root / "spec" / ".mirror.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["build_status"] = "unknown"
            state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            issues = specctl.validation_issues(root / "spec", specctl.load_state(root / "spec"))
            self.assertIn("invalid build_status 'unknown'", issues)

    def test_validate_rejects_legacy_mode(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            run("init", "--cwd", str(root), "--confirm")
            state_path = root / "spec" / ".mirror.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["mode"] = "detailed"
            state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            issues = specctl.validation_issues(root / "spec", specctl.load_state(root / "spec"))
            self.assertTrue(any("invalid mode" in item for item in issues), issues)

    def test_direct_helpers_secret_skip(self) -> None:
        self.assertTrue(specctl.should_skip_file(".env.local"))
        self.assertTrue(specctl.should_skip_file("certs/server.pem"))
        self.assertTrue(specctl.should_skip_file("vendor/github.com/foo/lib.go"))
        self.assertTrue(specctl.should_skip_file("node_modules/pkg/index.js"))
        self.assertFalse(specctl.should_skip_file("internal/order.go"))
        self.assertFalse(specctl.should_skip_file("src/App.php"))

    def test_non_git_inventory_respects_gitignore_and_text_content(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "app"
            root.mkdir()
            (root / "pyproject.toml").write_text("[project]\nname='app'\n", encoding="utf-8")
            (root / ".gitignore").write_text("cache/\n", encoding="utf-8")
            (root / "cache").mkdir()
            (root / "cache" / "generated.txt").write_text(
                "generated\n",
                encoding="utf-8",
            )
            (root / "app.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "blob").write_bytes(b"\x00\x01\x02")
            run("init", "--cwd", str(root), "--confirm")
            names = specctl.inventory_files(root)
            self.assertIn("app.py", names)
            self.assertIn(".gitignore", names)
            self.assertNotIn("cache/generated.txt", names)
            self.assertNotIn("blob", names)

    def test_diff_skips_vendor_changes(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            run("init", "--cwd", str(root), "--confirm")
            write_minimum_content(root / "spec")
            sha = git(root, "rev-parse", "HEAD").stdout.strip()
            self.assertEqual(run("finalize", "--cwd", str(root), "--commit", sha)[0], 0)
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
            names = specctl.inventory_files(root)
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
            names = specctl.inventory_files(root)
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
            item = specctl.inspect_symbols(root, "vendor/lib.go")
            self.assertTrue(item.get("skipped"))
            self.assertEqual(item.get("reason"), "third_party")
            self.assertEqual(item["symbols"], [])


CHECKOUT_SPEC = """# checkout

## Purpose
下单。

## Requirements

### Requirement: 可以下单
系统 SHALL 接受有效订单。

#### Scenario: 成功
- **WHEN** 库存充足
- **THEN** 订单创建
"""


def write_checkout_capability(spec: Path, source_path: str = "internal") -> None:
    (spec / "agent").mkdir(parents=True, exist_ok=True)
    (spec / "evidence").mkdir(parents=True, exist_ok=True)
    (spec / "agent" / "INDEX.md").write_text(
        """# 能力

| 概念 | 一句话 |
|------|--------|
| 订单 | 不要当能力 |

| 能力 | 一句话 | 状态 | 页 |
|------|--------|------|-----|
| checkout | 下单 | ready | [checkout](specs/checkout/spec.md) |

## 未指定

| 路径 | 原因 |
|------|------|
""",
        encoding="utf-8",
    )
    spec_page = spec / "agent" / "specs" / "checkout" / "spec.md"
    spec_page.parent.mkdir(parents=True, exist_ok=True)
    spec_page.write_text(CHECKOUT_SPEC, encoding="utf-8")
    (spec / "evidence" / "source-map.md").write_text(
        f"""# 源映射

| 能力 | 源路径 | spec |
|------|--------|------|
| checkout | `{source_path}` | [checkout](../agent/specs/checkout/spec.md) |
""",
        encoding="utf-8",
    )


def write_minimum_content(spec: Path, *, source_path: str = "internal") -> None:
    (spec / "briefing").mkdir(parents=True, exist_ok=True)
    (spec / "briefing" / "overview.md").write_text(
        "# example-api\n\n给店铺用的下单 API。\n",
        encoding="utf-8",
    )
    flows = spec / "briefing" / "flows"
    flows.mkdir(parents=True, exist_ok=True)
    (flows / "INDEX.md").write_text(
        """# 业务处理线

| 名称 | 一句话 | 页 |
|------|--------|-----|
| checkout | 下单 | [checkout](checkout.md) |
""",
        encoding="utf-8",
    )
    (flows / "checkout.md").write_text("# 下单\n\n买家提交订单。\n", encoding="utf-8")
    write_checkout_capability(spec, source_path)


class RouteParseTest(unittest.TestCase):
    def test_parse_source_map_rows(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            spec = Path(raw) / "spec"
            spec.mkdir()
            write_checkout_capability(spec, "internal")
            rows = specctl.load_source_map(spec)
            self.assertEqual(rows[0]["name"], "checkout")
            self.assertEqual(rows[0]["path"], "internal")

    def test_parse_capability_index(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            spec = Path(raw) / "spec"
            spec.mkdir()
            write_checkout_capability(spec)
            caps = specctl.load_capabilities(spec)
            self.assertEqual([item["name"] for item in caps], ["checkout"])


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
            self.assertEqual(payload["capabilities"], [])
            self.assertIn("internal/order.go", payload["unmapped"])

    def test_source_map_exact_prefix_and_unmapped(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            write_minimum_content(root / "spec", source_path="internal/order.go")
            sha = git(root, "rev-parse", "HEAD").stdout.strip()
            self.assertEqual(
                run("finalize", "--cwd", str(root), "--commit", sha)[0],
                0,
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
            # prefix row so extra.go also maps
            write_checkout_capability(root / "spec", "internal")
            code, payload = run("route", "--cwd", str(root))
            self.assertEqual(code, 0, payload)
            self.assertFalse(payload["not_built"])
            by_path = {item["path"]: item for item in payload["changes"]}
            self.assertEqual(by_path["internal/order.go"]["via"], "source-prefix")
            self.assertEqual(by_path["internal/order.go"]["capabilities"], ["checkout"])
            self.assertEqual(by_path["internal/extra.go"]["via"], "source-prefix")
            self.assertEqual(by_path["internal/extra.go"]["capabilities"], ["checkout"])
            self.assertEqual(by_path["scripts/one-off.sh"]["via"], "unmapped")
            self.assertIn("scripts/one-off.sh", payload["unmapped"])
            self.assertEqual(payload["capabilities"], ["checkout"])
            self.assertEqual(payload["pages"], ["agent/specs/checkout/spec.md"])

    def test_rename_uses_from_source_map(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            write_minimum_content(root / "spec", source_path="internal/order.go")
            sha = git(root, "rev-parse", "HEAD").stdout.strip()
            self.assertEqual(
                run("finalize", "--cwd", str(root), "--commit", sha)[0],
                0,
            )
            git(root, "mv", "internal/order.go", "internal/placed.go")
            git(root, "commit", "-q", "-m", "rename order")
            code, payload = run("route", "--cwd", str(root))
            self.assertEqual(code, 0, payload)
            self.assertEqual(payload["renames"][0]["from"], "internal/order.go")
            self.assertEqual(payload["renames"][0]["to"], "internal/placed.go")
            self.assertEqual(payload["renames"][0]["capability"], "checkout")
            self.assertGreaterEqual(payload["renames_applied"], 1)
            rec = payload["changes"][0]
            self.assertEqual(rec["via"], "source-map")
            self.assertEqual(rec["from"], "internal/order.go")
            mapped = specctl.load_source_map(root / "spec")
            self.assertEqual(mapped[0]["path"], "internal/placed.go")

    def test_finalize_drops_legacy_hotspot_fields(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            write_minimum_content(root / "spec")
            state_path = root / "spec" / ".mirror.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["hotspots"] = ["internal/order.go"]
            state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            sha = git(root, "rev-parse", "HEAD").stdout.strip()
            code, payload = run("finalize", "--cwd", str(root), "--commit", sha)
            self.assertEqual(code, 0, payload)
            self.assertNotIn("hotspots", payload["state"])
            issues = specctl.validation_issues(root / "spec", payload["state"])
            self.assertEqual(issues, [])


class CoverageTest(unittest.TestCase):
    def test_empty_skeleton_fails_content_gates(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            spec = root / "spec"
            payload = specctl.collect_coverage(
                spec, root, specctl.load_state(spec)
            )
            self.assertFalse(payload["ok"])
            self.assertFalse(payload["enforce"])
            self.assertIn("overview:stub", payload["missing"])
            self.assertIn("flows:none", payload["missing"])
            self.assertIn("<no capabilities identified>", payload["missing"])
            self.assertIn("source-map:empty", payload["missing"])

    def test_reconstructable_fails_until_capability_is_mapped(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(
                run(
                    "init",
                    "--cwd",
                    str(root),
                    "--mode",
                    "reconstructable",
                    "--confirm",
                )[0],
                0,
            )
            spec = root / "spec"
            payload = specctl.collect_coverage(
                spec, root, specctl.load_state(spec)
            )
            self.assertFalse(payload["ok"])
            self.assertTrue(payload["enforce"])
            self.assertIn("<no capabilities identified>", payload["missing"])
            write_minimum_content(spec)
            payload = specctl.collect_coverage(
                spec, root, specctl.load_state(spec)
            )
            self.assertTrue(payload["ok"], payload)
            self.assertEqual(payload["missing"], [])
            self.assertEqual(payload["covered_count"], payload["required_count"])

    def test_unspecified_covers_reconstructable_unmapped(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            (root / "cmd" / "legacy.go").parent.mkdir()
            (root / "cmd" / "legacy.go").write_text("package main\n", encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-q", "-m", "legacy cmd")
            self.assertEqual(
                run(
                    "init",
                    "--cwd",
                    str(root),
                    "--mode",
                    "reconstructable",
                    "--confirm",
                )[0],
                0,
            )
            spec = root / "spec"
            write_minimum_content(spec)
            payload = specctl.collect_coverage(
                spec, root, specctl.load_state(spec)
            )
            self.assertFalse(payload["ok"], payload)
            self.assertIn("unmapped:cmd/legacy.go", payload["missing"])
            index = (spec / "agent" / "INDEX.md").read_text(encoding="utf-8")
            (spec / "agent" / "INDEX.md").write_text(
                index.replace(
                    "| 路径 | 原因 |\n|------|------|\n",
                    "| 路径 | 原因 |\n|------|------|\n| `cmd/legacy.go` | 一次性脚本 |\n",
                ),
                encoding="utf-8",
            )
            payload = specctl.collect_coverage(
                spec, root, specctl.load_state(spec)
            )
            self.assertTrue(payload["ok"], payload)

    def test_briefing_extra_source_map_does_not_fail(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            write_minimum_content(root / "spec")
            (root / "spec" / "evidence" / "source-map.md").write_text(
                """# 源映射

| 能力 | 源路径 | spec |
|------|--------|------|
| checkout | `internal` | [checkout](../agent/specs/checkout/spec.md) |
| ghost | `internal/gone.go` | [ghost](../agent/specs/ghost/spec.md) |
""",
                encoding="utf-8",
            )
            payload = specctl.collect_coverage(
                root / "spec", root, specctl.load_state(root / "spec")
            )
            self.assertTrue(payload["ok"], payload)
            self.assertIn("ghost", payload["extra"])

    def test_reconstructable_ghost_map_fails(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(
                run(
                    "init",
                    "--cwd",
                    str(root),
                    "--mode",
                    "reconstructable",
                    "--confirm",
                )[0],
                0,
            )
            write_minimum_content(root / "spec")
            (root / "spec" / "evidence" / "source-map.md").write_text(
                """# 源映射

| 能力 | 源路径 | spec |
|------|--------|------|
| checkout | `internal` | [checkout](../agent/specs/checkout/spec.md) |
| ghost | `internal/gone.go` | [ghost](../agent/specs/ghost/spec.md) |
""",
                encoding="utf-8",
            )
            payload = specctl.collect_coverage(
                root / "spec", root, specctl.load_state(root / "spec")
            )
            self.assertFalse(payload["ok"])
            self.assertIn("ghost:ghost", payload["missing"])


class FinalizeTest(unittest.TestCase):
    def test_finalize_blocks_on_missing_coverage(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            head = git(root, "rev-parse", "HEAD").stdout.strip()
            code, payload = run(
                "finalize",
                "--cwd",
                str(root),
                "--mode",
                "reconstructable",
                "--commit",
                head,
            )
            self.assertEqual(code, 1, payload)
            self.assertEqual(payload["stage"], "coverage")
            self.assertEqual(payload["reason"], "coverage_missing")
            self.assertIn(
                "<no capabilities identified>", payload["coverage"]["missing"]
            )
            state = json.loads(
                (root / "spec" / ".mirror.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["build_status"], "skeleton")
            self.assertIsNone(state["synced_commit"])

    def test_finalize_records_commit_after_coverage_passes(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            write_minimum_content(root / "spec")
            head = git(root, "rev-parse", "HEAD").stdout.strip()
            code, payload = run(
                "finalize",
                "--cwd",
                str(root),
                "--mode",
                "reconstructable",
                "--commit",
                head,
            )
            self.assertEqual(code, 0, payload)
            self.assertEqual(payload["stage"], "done")
            self.assertEqual(payload["issues"], [])
            self.assertEqual(
                payload["coverage"]["required_count"],
                payload["coverage"]["covered_count"],
            )
            self.assertEqual(payload["state"]["build_status"], "built")
            self.assertEqual(payload["state"]["synced_commit"], head)

    def test_finalize_non_git_keeps_commit_null(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "plain-project"
            (root / "internal").mkdir(parents=True)
            (root / "go.mod").write_text("module example.com/plain\n", encoding="utf-8")
            (root / "internal" / "order.go").write_text(
                "package order\n\nfunc Place() {}\n", encoding="utf-8"
            )
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            write_minimum_content(root / "spec")
            code, payload = run("finalize", "--cwd", str(root), "--mode", "briefing")
            self.assertEqual(code, 0, payload)
            self.assertEqual(payload["state"]["build_status"], "built")
            self.assertIsNone(payload["state"]["synced_commit"])

    def test_empty_skeleton_finalize_fails(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            head = git(root, "rev-parse", "HEAD").stdout.strip()
            code, payload = run("finalize", "--cwd", str(root), "--commit", head)
            self.assertEqual(code, 1, payload)
            self.assertEqual(payload["reason"], "coverage_missing")
            self.assertIn("overview:stub", payload["coverage"]["missing"])
            state = json.loads(
                (root / "spec" / ".mirror.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["build_status"], "skeleton")

    def test_legacy_layout_is_rebuild(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            spec = root / "spec"
            (spec / "briefing" / "overview.md").unlink()
            (spec / "modules").mkdir()
            (spec / "modules" / "INDEX.md").write_text("# 旧表\n", encoding="utf-8")
            code, payload = run("detect", "--cwd", str(root))
            self.assertEqual(code, 0, payload)
            self.assertEqual(payload["layout"], "legacy")
            code, status = run("status", "--cwd", str(root))
            self.assertEqual(code, 0, status)
            self.assertEqual(status["layout"], "legacy")
            self.assertEqual(status["phase"], "rebuild")
            head = git(root, "rev-parse", "HEAD").stdout.strip()
            code, payload = run("finalize", "--cwd", str(root), "--commit", head)
            self.assertEqual(code, 1, payload)
            self.assertEqual(payload["reason"], "legacy_layout")

    def test_briefing_leak_blocks_built(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            write_minimum_content(root / "spec")
            (root / "spec" / "briefing" / "overview.md").write_text(
                "# example-api\n\n完整逻辑如下。\n",
                encoding="utf-8",
            )
            head = git(root, "rev-parse", "HEAD").stdout.strip()
            code, payload = run("finalize", "--cwd", str(root), "--commit", head)
            self.assertEqual(code, 1, payload)
            self.assertEqual(payload["reason"], "briefing_leak")
            self.assertTrue(any("完整逻辑" in item for item in payload["leaks"]))

    def test_english_stub_and_leak_patterns(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            spec = Path(raw) / "spec"
            (spec / "briefing").mkdir(parents=True)
            (spec / "briefing" / "overview.md").write_text(
                "# demo\n\n(to be built: say what this is.)\n",
                encoding="utf-8",
            )
            self.assertTrue(specctl.overview_is_stub(spec))
            (spec / "briefing" / "overview.md").write_text(
                "# demo\n\nA shop checkout API.\n",
                encoding="utf-8",
            )
            self.assertFalse(specctl.overview_is_stub(spec))
            (spec / "briefing" / "flow.md").write_text(
                "# flow\n\n## Files\n\n- a.py\nSee Cargo.toml 1.2.3 and full logic.\n",
                encoding="utf-8",
            )
            leaks = specctl.briefing_leaks(spec)
            self.assertTrue(any("文件表" in item for item in leaks), leaks)
            self.assertTrue(any("工具链版本" in item for item in leaks), leaks)
            self.assertTrue(any("完整逻辑" in item for item in leaks), leaks)

    def test_capability_header_accepts_english(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            spec = Path(raw) / "spec"
            (spec / "agent").mkdir(parents=True)
            (spec / "agent" / "INDEX.md").write_text(
                """# Capabilities

| Capability | Summary | Status | Page |
|------------|---------|--------|------|
| checkout | place order | ready | x |
""",
                encoding="utf-8",
            )
            caps = specctl.load_capabilities(spec)
            self.assertEqual([item["name"] for item in caps], ["checkout"])

    def test_finalize_rejects_undigested_unmapped(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = make_repo(Path(raw) / "example-api")
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            write_minimum_content(root / "spec", source_path="internal/order.go")
            sha = git(root, "rev-parse", "HEAD").stdout.strip()
            self.assertEqual(run("finalize", "--cwd", str(root), "--commit", sha)[0], 0)
            (root / "scripts").mkdir()
            (root / "scripts" / "one-off.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-q", "-m", "script")
            new_sha = git(root, "rev-parse", "HEAD").stdout.strip()
            code, payload = run("finalize", "--cwd", str(root), "--commit", new_sha)
            self.assertEqual(code, 1, payload)
            self.assertEqual(payload["reason"], "unmapped_pending")
            self.assertIn("scripts/one-off.sh", payload["unmapped"])

    def test_status_nongit_reports_new_and_gone_entries(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "plain-project"
            (root / "internal").mkdir(parents=True)
            (root / "go.mod").write_text("module example.com/plain\n", encoding="utf-8")
            (root / "internal" / "order.go").write_text(
                "package order\n\nfunc Place() {}\n", encoding="utf-8"
            )
            self.assertEqual(run("init", "--cwd", str(root), "--confirm")[0], 0)
            write_minimum_content(root / "spec", source_path="internal")
            self.assertEqual(run("finalize", "--cwd", str(root))[0], 0)
            (root / "internal" / "extra.go").write_text(
                "package order\n\nfunc Extra() {}\n", encoding="utf-8"
            )
            (root / "spec" / "evidence" / "source-map.md").write_text(
                """# 源映射

| 能力 | 源路径 | spec |
|------|--------|------|
| checkout | `missing/path` | [checkout](../agent/specs/checkout/spec.md) |
""",
                encoding="utf-8",
            )
            code, payload = run("status", "--cwd", str(root))
            self.assertEqual(code, 0, payload)
            self.assertIn("internal/order.go", payload["freshness"]["unmapped"])
            self.assertIn("internal/extra.go", payload["freshness"]["unmapped"])
            self.assertIn("missing/path", payload["freshness"]["gone"])


if __name__ == "__main__":
    unittest.main()
