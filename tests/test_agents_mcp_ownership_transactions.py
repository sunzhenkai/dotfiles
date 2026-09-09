"""MCP entry ownership, transaction rollback, and safe template generation tests."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "src"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "agents"))

from common import Catalog  # noqa: E402
from dotf_core.config_deploy import (  # noqa: E402
    _load_registry_module,
    apply_config_plan,
    compile_config_plan,
    deploy_config,
)
from dotf_core.config_producers import producer_for  # noqa: E402
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


def _deploy_opencode(home: Path, state: Path, profile: str = "company") -> None:
    module = _load_registry_module(ROOT, "opencode")
    producer = producer_for("opencode", repo_root=ROOT, home=home)
    prior = os.environ.get("DOTF_OPENCODE_PROFILE")
    os.environ["DOTF_OPENCODE_PROFILE"] = profile
    try:
        deploy_config(
            module,
            repo_root=ROOT,
            home=home,
            state_home=state,
            producer=producer,
            run_id="test-opencode-config",
        )
    finally:
        if prior is None:
            os.environ.pop("DOTF_OPENCODE_PROFILE", None)
        else:
            os.environ["DOTF_OPENCODE_PROFILE"] = prior


def _catalog_with_changed_reader(tmp_path: Path) -> Catalog:
    repo = tmp_path / "catalog-repo"
    (repo / "agents").mkdir(parents=True)
    shutil.copytree(ROOT / "agents" / "env", repo / "agents" / "env")
    shutil.copy2(
        ROOT / "agents" / "skills-defaults.lock.yaml",
        repo / "agents" / "skills-defaults.lock.yaml",
    )
    servers_path = repo / "agents" / "env" / "mcp" / "servers.yaml"
    servers = yaml.safe_load(servers_path.read_text(encoding="utf-8"))
    servers["servers"]["web-reader"]["url"] = "https://example.com/changed/mcp"
    servers_path.write_text(yaml.safe_dump(servers, sort_keys=False), encoding="utf-8")
    return Catalog(repo, include_overlays=False)


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


def test_mcp_adopts_equivalent_entries_without_replacing_target(tmp_home: Path) -> None:
    cat = Catalog(ROOT)
    state = tmp_home / ".state"
    _apply(cat, tmp_home, "research", ["cursor"])
    manifest = state / "dotf" / MCP_MANIFEST_NAME
    manifest.unlink()
    target = tmp_home / ".cursor" / "mcp.json"
    value = json.loads(target.read_text(encoding="utf-8"))
    value["mcpServers"]["private-local"] = {"command": "mine"}
    target.write_text(json.dumps(value), encoding="utf-8")
    before = (target.read_bytes(), target.stat().st_ino, target.stat().st_mtime_ns)

    plan = compile_sync_plan(cat, "research", ["cursor"], home=tmp_home, state_home=state)
    item = plan.items[0]
    assert (item.state, item.action) == ("update", "adopt")
    owned = [entry for entry in item.entries if entry.ownership == "owned"]
    assert owned and all((entry.state, entry.action) == ("update", "adopt") for entry in owned)
    local = next(entry for entry in item.entries if entry.server_id == "private-local")
    assert (local.ownership, local.state, local.action) == ("unowned", "unchanged", "none")

    results, _secrets = apply_sync_plan(
        plan, cat, approved=True, home=tmp_home, state_home=state
    )
    assert results[0].status == "changed"
    assert (target.read_bytes(), target.stat().st_ino, target.stat().st_mtime_ns) == before
    adopted = json.loads(manifest.read_text(encoding="utf-8"))
    assert {entry["server_id"] for entry in adopted["items"]} == {
        "web-reader", "web-search-prime", "zai-vision", "zread"
    }

    repeated = compile_sync_plan(cat, "research", ["cursor"], home=tmp_home, state_home=state)
    assert (repeated.items[0].state, repeated.items[0].action) == ("unchanged", "none")
    assert next(
        entry for entry in repeated.items[0].entries if entry.server_id == "private-local"
    ).ownership == "unowned"


def test_mcp_unowned_expected_entry_conflicts_when_not_equivalent(tmp_home: Path) -> None:
    cat = Catalog(ROOT)
    state = tmp_home / ".state"
    _apply(cat, tmp_home, "research", ["cursor"])
    (state / "dotf" / MCP_MANIFEST_NAME).unlink()
    target = tmp_home / ".cursor" / "mcp.json"
    value = json.loads(target.read_text(encoding="utf-8"))
    value["mcpServers"]["web-reader"]["url"] = "https://example.invalid/local-edit"
    target.write_text(json.dumps(value), encoding="utf-8")
    before = target.read_bytes()

    plan = compile_sync_plan(cat, "research", ["cursor"], home=tmp_home, state_home=state)
    entry = next(item for item in plan.items[0].entries if item.server_id == "web-reader")
    assert (entry.state, entry.action) == ("conflict", "block")
    with pytest.raises(SyncPlanError, match="without ownership"):
        apply_sync_plan(plan, cat, approved=True, home=tmp_home, state_home=state)
    assert target.read_bytes() == before
    assert not (state / "dotf" / MCP_MANIFEST_NAME).exists()


def test_sync_releases_legacy_registry_ownership_for_pure_mcp_target(tmp_home: Path) -> None:
    state = tmp_home / ".state"
    module = {
        "name": "cursor",
        "config": {
            "source": "agents/vendors/cursor/mcp.json",
            "target": "~/.cursor/mcp.json",
            "strategy": "render",
            "writable": True,
            "sensitive": True,
            "target_mode": "0600",
            "preserve": [],
            "exclude": [],
        },
    }
    producer = producer_for("cursor", repo_root=ROOT, home=tmp_home)
    deploy_config(
        module,
        repo_root=ROOT,
        home=tmp_home,
        state_home=state,
        producer=producer,
        run_id="legacy-cursor",
    )
    target = tmp_home / ".cursor" / "mcp.json"
    before = (target.read_bytes(), target.stat().st_ino, target.stat().st_mtime_ns)

    _apply(Catalog(ROOT, include_overlays=False), tmp_home, "research", ["cursor"])
    config_manifest = json.loads(
        (state / "dotf" / "config-manifest.json").read_text(encoding="utf-8")
    )
    assert not [
        item for item in config_manifest["items"] if item["target"] == str(target)
    ]
    assert (target.read_bytes(), target.stat().st_ino, target.stat().st_mtime_ns) == before


def test_opencode_sync_coordinates_config_manifest_and_preserves_local_agent(
    tmp_path: Path, tmp_home: Path,
) -> None:
    state = tmp_home / ".state"
    _deploy_opencode(tmp_home, state)
    target = tmp_home / ".config" / "opencode" / "opencode.json"
    value = json.loads(target.read_text(encoding="utf-8"))
    value["agent"]["local-only"] = {"prompt": "keep me"}
    target.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    module = _load_registry_module(ROOT, "opencode")
    producer = producer_for("opencode", repo_root=ROOT, home=tmp_home)
    repair = compile_config_plan(
        module, repo_root=ROOT, home=tmp_home, state_home=state, producer=producer
    )
    apply_config_plan(repair, repo_root=ROOT, home=tmp_home, state_home=state, run_id="local-agent")

    cat = Catalog(ROOT, include_overlays=False)
    _apply(cat, tmp_home, "research", ["opencode"])
    changed = _catalog_with_changed_reader(tmp_path)
    _apply(changed, tmp_home, "research", ["opencode"])

    plan = compile_config_plan(
        module, repo_root=ROOT, home=tmp_home, state_home=state, producer=producer
    )
    assert plan.status == "unchanged"
    installed = json.loads(target.read_text(encoding="utf-8"))
    assert installed["agent"]["local-only"] == {"prompt": "keep me"}
    assert installed["model"] == "company/vanchin/deepseek-v4-pro-0813"
    assert installed["mcp"]["web-reader"]["url"] == "https://example.com/changed/mcp"

    installed["model"] = "minimax/MiniMax-M3"
    target.write_text(json.dumps(installed, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    drift = compile_config_plan(
        module, repo_root=ROOT, home=tmp_home, state_home=state, producer=producer
    )
    assert drift.status == "changed"
    write = next(op for op in drift.operations if op.item.target == str(target))
    assert (write.item.state, write.item.action) == ("update", "update")


def test_opencode_coordinated_manifest_failure_rolls_back_every_output(
    tmp_path: Path, tmp_home: Path,
) -> None:
    state = tmp_home / ".state"
    _deploy_opencode(tmp_home, state)
    _apply(Catalog(ROOT, include_overlays=False), tmp_home, "research", ["opencode"])
    changed = _catalog_with_changed_reader(tmp_path)
    target = tmp_home / ".config" / "opencode" / "opencode.json"
    agent_manifest = state / "dotf" / MCP_MANIFEST_NAME
    config_manifest = state / "dotf" / "config-manifest.json"
    before = {
        target: target.read_bytes(),
        agent_manifest: agent_manifest.read_bytes(),
        config_manifest: config_manifest.read_bytes(),
    }
    plan = compile_sync_plan(changed, "research", ["opencode"], home=tmp_home, state_home=state)

    def fail(phase: str, index: int, _label: str) -> None:
        if phase == "commit" and index == 2:
            raise RuntimeError("config-manifest-commit-fault")

    with pytest.raises(RuntimeError, match="config-manifest-commit-fault"):
        apply_sync_plan(
            plan, changed, approved=True, home=tmp_home, state_home=state, fault=fail
        )
    assert {path: path.read_bytes() for path in before} == before


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
    shutil.copy2(
        ROOT / "agents" / "skills-defaults.lock.yaml",
        repo / "agents" / "skills-defaults.lock.yaml",
    )
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
        [sys.executable, str(ROOT / "src" / "agents" / "generate_templates.py"), "--check", "--root", str(ROOT)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "/private/browser/profile" not in "".join(path.read_text(encoding="utf-8") for path in (ROOT / "agents" / "vendors").rglob("*.json"))
    runtime = (ROOT / "src" / "agents" / "env_sync.py").read_text(encoding="utf-8")
    assert "repo-templates" not in runtime

    isolated = tmp_path / "template-repo"
    (isolated / "agents").mkdir(parents=True)
    shutil.copytree(ROOT / "agents" / "env", isolated / "agents" / "env")
    shutil.copy2(
        ROOT / "agents" / "skills-defaults.lock.yaml",
        isolated / "agents" / "skills-defaults.lock.yaml",
    )
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
        [sys.executable, str(ROOT / "src" / "agents" / "generate_templates.py"), "--root", str(isolated)],
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
