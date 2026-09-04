"""MCP entry ownership, transaction rollback, and safe template generation tests."""

from __future__ import annotations

import json
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "agents"))

from common import Catalog  # noqa: E402
from mcp_runtime import MCP_JOURNAL_DIR, MCP_MANIFEST_NAME  # noqa: E402
from sync_plan import SyncPlanError, apply_sync_plan, compile_sync_plan  # noqa: E402


def _block(target: Path, *path: str) -> dict:
    value = json.loads(target.read_text(encoding="utf-8"))
    current = value
    for component in path:
        current = current[component]
    return current


def _journal(home: Path) -> dict:
    files = sorted((home / ".state" / "dotf" / MCP_JOURNAL_DIR).glob("*.json"))
    assert files
    return json.loads(files[-1].read_text(encoding="utf-8"))


def _apply(cat: Catalog, home: Path, profile: str, tools: list[str], **kwargs):
    state = home / ".state"
    plan = compile_sync_plan(cat, profile, tools, home=home, state_home=state)
    return plan, apply_sync_plan(plan, cat, approved=True, home=home, state_home=state, **kwargs)


def test_mcp_manifest_owns_each_server_and_preserves_reports_unowned(tmp_home: Path) -> None:
    cat = Catalog(ROOT)
    _apply(cat, tmp_home, "research", ["cursor"])
    manifest = json.loads((tmp_home / ".state" / "dotf" / MCP_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert {(item["tool"], item["server_id"]) for item in manifest["items"]} == {
        ("cursor", "web-search-prime"),
        ("cursor", "web-reader"),
        ("cursor", "zread"),
        ("cursor", "zai-vision"),
    }
    target = tmp_home / ".cursor" / "mcp.json"
    value = json.loads(target.read_text(encoding="utf-8"))
    value["mcpServers"]["private-local"] = {"command": "mine"}
    target.write_text(json.dumps(value), encoding="utf-8")

    plan = compile_sync_plan(cat, "research", ["cursor"], home=tmp_home, state_home=tmp_home / ".state")
    item = plan.items[0]
    assert item.actual_state == "unowned"
    assert item.action == "none"
    assert [(entry.server_id, entry.ownership) for entry in item.entries if entry.ownership == "unowned"] == [
        ("private-local", "unowned")
    ]
    apply_sync_plan(plan, cat, approved=True, home=tmp_home, state_home=tmp_home / ".state")
    assert _block(target, "mcpServers")["private-local"] == {"command": "mine"}


def test_mcp_prunes_only_unchanged_stale_and_conflicts_on_local_edit(tmp_home: Path) -> None:
    cat = Catalog(ROOT)
    _apply(cat, tmp_home, "browser", ["cursor"])
    target = tmp_home / ".cursor" / "mcp.json"
    assert "playwright" in _block(target, "mcpServers")

    stale = compile_sync_plan(cat, "research", ["cursor"], home=tmp_home, state_home=tmp_home / ".state")
    playwright = next(entry for entry in stale.items[0].entries if entry.server_id == "playwright")
    assert (playwright.state, playwright.action) == ("prune", "prune")
    apply_sync_plan(stale, cat, approved=True, home=tmp_home, state_home=tmp_home / ".state")
    assert "playwright" not in _block(target, "mcpServers")

    value = json.loads(target.read_text(encoding="utf-8"))
    value["mcpServers"]["web-reader"]["url"] = "https://local.invalid/edit"
    target.write_text(json.dumps(value), encoding="utf-8")
    conflict = compile_sync_plan(cat, "research", ["cursor"], home=tmp_home, state_home=tmp_home / ".state")
    edited = next(entry for entry in conflict.items[0].entries if entry.server_id == "web-reader")
    assert (edited.state, edited.action) == ("conflict", "block")
    before = target.read_bytes()
    with pytest.raises(SyncPlanError, match="modified locally"):
        apply_sync_plan(conflict, cat, approved=True, home=tmp_home, state_home=tmp_home / ".state")
    assert target.read_bytes() == before


def test_mcp_source_change_updates_only_changed_owned_entry(tmp_path: Path, tmp_home: Path) -> None:
    _apply(Catalog(ROOT), tmp_home, "research", ["cursor"])
    repo = tmp_path / "repo"
    (repo / "agents").mkdir(parents=True)
    shutil.copytree(ROOT / "agents" / "env", repo / "agents" / "env")
    servers_path = repo / "agents" / "env" / "mcp" / "servers.yaml"
    servers = yaml.safe_load(servers_path.read_text(encoding="utf-8"))
    servers["servers"]["web-reader"]["url"] = "https://example.com/changed/mcp"
    servers_path.write_text(yaml.safe_dump(servers, sort_keys=False), encoding="utf-8")
    changed = compile_sync_plan(
        Catalog(repo), "research", ["cursor"], home=tmp_home, state_home=tmp_home / ".state"
    )
    actions = {entry.server_id: entry.action for entry in changed.items[0].entries if entry.ownership == "owned"}
    assert actions == {
        "web-reader": "update",
        "web-search-prime": "none",
        "zai-vision": "none",
        "zread": "none",
    }


def test_multi_target_later_failure_rolls_back_and_journals_failed(tmp_home: Path) -> None:
    cat = Catalog(ROOT)
    state = tmp_home / ".state"
    plan = compile_sync_plan(cat, "research", ["cursor", "kiro"], home=tmp_home, state_home=state)

    def fail(phase: str, index: int, _label: str) -> None:
        if phase == "commit" and index == 1:
            raise RuntimeError("injected later-target failure")

    with pytest.raises(RuntimeError, match="later-target"):
        apply_sync_plan(plan, cat, approved=True, home=tmp_home, state_home=state, fault=fail)
    assert not (tmp_home / ".cursor" / "mcp.json").exists()
    assert not (tmp_home / ".kiro" / "settings" / "mcp.json").exists()
    assert not (state / "dotf" / MCP_MANIFEST_NAME).exists()
    journal = _journal(tmp_home)
    assert journal["status"] == "failed"
    assert all("ZHIPU" not in json.dumps(action) for action in journal["actions"])


def test_transaction_records_failed_rollback_and_interruption(tmp_home: Path) -> None:
    cat = Catalog(ROOT)
    state = tmp_home / ".state"
    plan = compile_sync_plan(cat, "research", ["cursor", "kiro"], home=tmp_home, state_home=state)

    def rollback_failure(phase: str, index: int, _label: str) -> None:
        if phase == "commit" and index == 1:
            raise RuntimeError("commit-fault")
        if phase == "rollback" and index == 0:
            raise RuntimeError("rollback-fault")

    with pytest.raises(RuntimeError, match="rollback-fault"):
        apply_sync_plan(plan, cat, approved=True, home=tmp_home, state_home=state, fault=rollback_failure)
    assert _journal(tmp_home)["status"] == "failed-rollback"

    other = tmp_home.parent / "interrupted-home"
    other.mkdir()
    other_state = other / ".state"
    interrupted_plan = compile_sync_plan(cat, "research", ["cursor", "kiro"], home=other, state_home=other_state)

    def interrupt(phase: str, index: int, _label: str) -> None:
        if phase == "commit" and index == 1:
            raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        apply_sync_plan(interrupted_plan, cat, approved=True, home=other, state_home=other_state, fault=interrupt)
    assert _journal(other)["status"] == "interrupted"
    assert not (other / ".cursor" / "mcp.json").exists()


def test_manifest_stage_failure_changes_no_target_and_persists_failed_journal(tmp_home: Path) -> None:
    cat = Catalog(ROOT)
    state = tmp_home / ".state"
    plan = compile_sync_plan(cat, "research", ["cursor", "kiro"], home=tmp_home, state_home=state)

    def fail(phase: str, index: int, _label: str) -> None:
        if phase == "stage" and index == 2:
            raise RuntimeError("manifest-stage-fault")

    with pytest.raises(RuntimeError, match="manifest-stage-fault"):
        apply_sync_plan(plan, cat, approved=True, home=tmp_home, state_home=state, fault=fail)
    assert not (tmp_home / ".cursor" / "mcp.json").exists()
    assert not (tmp_home / ".kiro" / "settings" / "mcp.json").exists()
    assert not (state / "dotf" / MCP_MANIFEST_NAME).exists()
    assert _journal(tmp_home)["status"] == "failed"


def test_explicit_template_generator_is_overlay_independent_and_regenerates_cleanly(tmp_path: Path, tmp_home: Path) -> None:
    overlay = tmp_home / ".config" / "dotf" / "overlays" / "10-private.yaml"
    overlay.parent.mkdir(parents=True)
    overlay.write_text(
        "schema_version: 1\nkind: dotf-overlay\nagents:\n  enabled_servers: [playwright]\n"
        "  browser:\n    user_data_dir: /private/browser/profile\n",
        encoding="utf-8",
    )
    env = dict(__import__("os").environ)
    env.update({"HOME": str(tmp_home), "XDG_CONFIG_HOME": str(tmp_home / ".config")})
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "agents" / "generate_templates.py"), "--check", "--root", str(ROOT)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "/private/browser/profile" not in "".join(path.read_text(encoding="utf-8") for path in (ROOT / "agents" / "vendors").rglob("*.json"))
    runtime = (ROOT / "scripts" / "agents" / "env_sync.py").read_text(encoding="utf-8")
    assert "repo-templates" not in runtime

    isolated = tmp_path / "template-repo"
    (isolated / "agents").mkdir(parents=True)
    shutil.copytree(ROOT / "agents" / "env", isolated / "agents" / "env")
    for tool in ("cursor", "kiro", "opencode", "kimi-code", "zcode"):
        shutil.copytree(ROOT / "agents" / "vendors" / tool, isolated / "agents" / "vendors" / tool)
    for command in (
        ["git", "init", "--quiet"],
        ["git", "config", "user.email", "tests@example.invalid"],
        ["git", "config", "user.name", "tests"],
        ["git", "add", "agents"],
        ["git", "commit", "--quiet", "-m", "baseline"],
    ):
        subprocess.run(command, cwd=isolated, check=True, capture_output=True)
    generated = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "agents" / "generate_templates.py"), "--root", str(isolated)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert generated.returncode == 0, generated.stdout + generated.stderr
    no_diff = subprocess.run(
        ["git", "diff", "--exit-code", "--", "agents/vendors"],
        cwd=isolated,
        text=True,
        capture_output=True,
        check=False,
    )
    assert no_diff.returncode == 0, no_diff.stdout + no_diff.stderr
