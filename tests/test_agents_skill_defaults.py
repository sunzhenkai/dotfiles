"""第三方默认 skill 清单：与一手 skill 不重名；已存在则跳过 npx。"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent


def _load_defaults():
    path = ROOT / "scripts" / "agents" / "defaults.py"
    spec = importlib.util.spec_from_file_location("agents_defaults", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_catalog_has_archify_browser_use_frontend_design() -> None:
    defaults = _load_defaults()
    items = defaults.load_catalog(ROOT)
    by_skill = {it["skill"]: it["source"] for it in items}
    assert by_skill["archify"] == "tt-a1i/archify"
    assert by_skill["browser-use"] == "browser-use/browser-use"
    assert by_skill["frontend-design"] == "anthropics/skills"
    assert "shadcn" not in by_skill
    assert "tailwind-css-patterns" not in by_skill
    assert "tailwind-design-system" not in by_skill
    assert "webapp-testing" not in by_skill


def test_catalog_does_not_overlap_first_party() -> None:
    defaults = _load_defaults()
    items = defaults.load_catalog(ROOT)
    first = set(defaults.first_party_skill_ids(ROOT))
    overlap = first.intersection(it["skill"] for it in items)
    assert not overlap, f"默认 skill 与一手 skill 同名: {sorted(overlap)}"
    assert "browser-use" not in first
    assert "frontend-design" not in first


def test_add_command_is_global_copy_without_agent_flag() -> None:
    defaults = _load_defaults()
    cmd = defaults.add_command("tt-a1i/archify", "archify")
    assert cmd[:5] == ["npx", "--yes", "skills", "add", "tt-a1i/archify"]
    assert "--skill" in cmd and "archify" in cmd
    assert "--global" in cmd
    assert "--yes" in cmd
    assert "--copy" in cmd
    assert "--agent" not in cmd and "-a" not in cmd
    assert "--all" not in cmd


def test_install_skips_existing_and_is_idempotent(tmp_path: Path) -> None:
    defaults = _load_defaults()
    dest = tmp_path / ".agents" / "skills"
    existing = {"archify", "browser-use"}
    for name in existing:
        skill_dir = dest / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"# {name}\n")
    expected_missing = [
        it["skill"] for it in defaults.load_catalog(ROOT) if it["skill"] not in existing
    ]
    calls: list[list[str]] = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0)

    rc = defaults.install_defaults(
        ROOT,
        dest_root=dest,
        run=run,
        which=lambda _name: "/usr/bin/npx",
    )
    assert rc == 0
    assert calls, "缺失的默认 skill 应调用 npx"
    assert [c[c.index("--skill") + 1] for c in calls] == expected_missing

    rc2 = defaults.install_defaults(
        ROOT,
        dest_root=dest,
        run=run,
        which=lambda _name: "/usr/bin/npx",
    )
    assert rc2 == 0
    # mock 不落盘，第二次仍会重试同一批缺失项
    assert [c[c.index("--skill") + 1] for c in calls[len(expected_missing) :]] == expected_missing


def test_dry_run_does_not_invoke_npx(tmp_path: Path) -> None:
    defaults = _load_defaults()
    dest = tmp_path / ".agents" / "skills"
    calls: list[list[str]] = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        raise AssertionError("dry-run 不应调用 npx")

    rc = defaults.install_defaults(
        ROOT,
        dry_run=True,
        dest_root=dest,
        run=run,
        which=lambda _name: "/usr/bin/npx",
    )
    assert rc == 0
    assert calls == []


def test_missing_npx_skips_without_failing(tmp_path: Path) -> None:
    defaults = _load_defaults()
    dest = tmp_path / ".agents" / "skills"
    calls: list[list[str]] = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    rc = defaults.install_defaults(
        ROOT,
        dest_root=dest,
        run=run,
        which=lambda _name: None,
    )
    assert rc == 0
    assert calls == []
