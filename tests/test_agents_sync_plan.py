"""Strict Agent catalogs, pure adapters, side-effect-free plans, and safe apply."""

from __future__ import annotations

import json
import os
import shutil
import socket
import stat
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "agents"))

from adapters import adapter_for  # noqa: E402
from catalog import CatalogError, load_catalog_documents, load_vendor_matrix, render_vendor_docs  # noqa: E402
from common import Catalog, TOOLS  # noqa: E402
from sync_plan import SyncPlanError, apply_sync_plan, compile_sync_plan, plan_json  # noqa: E402

GOLDEN = ROOT / "tests" / "golden" / "agents"
FAKE_SECRET = "sync-plan-test-secret-value"


def _copy_catalog(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "agents").mkdir(parents=True)
    shutil.copytree(ROOT / "agents" / "env", repo / "agents" / "env")
    return repo


def _yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, value: dict) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


@pytest.mark.parametrize("mutation, match", [
    ("unknown", "unknown keys"),
    ("version", "version must be 1"),
    ("type", "must be boolean"),
    ("cross-ref", "unknown ids"),
    ("docs", "out of sync"),
])
def test_catalog_rejects_unknown_version_type_cross_ref_and_doc_drift(
    tmp_path: Path, mutation: str, match: str
) -> None:
    repo = _copy_catalog(tmp_path)
    if mutation == "unknown":
        path = repo / "agents" / "env" / "manifest.yaml"
        value = _yaml(path)
        value["surprise"] = True
        _write_yaml(path, value)
    elif mutation == "version":
        path = repo / "agents" / "env" / "vendors.yaml"
        value = _yaml(path)
        value["version"] = 2
        _write_yaml(path, value)
    elif mutation == "type":
        path = repo / "agents" / "env" / "vendors.yaml"
        value = _yaml(path)
        value["vendors"]["zcode"]["sensitive"] = "yes"
        _write_yaml(path, value)
    elif mutation == "cross-ref":
        path = repo / "agents" / "env" / "mcp" / "servers.yaml"
        value = _yaml(path)
        value["servers"]["zread"]["tools"].append("missing-vendor")
        _write_yaml(path, value)
    else:
        path = repo / "agents" / "env" / "README.md"
        path.write_text(path.read_text(encoding="utf-8").replace("literal-at-apply", "drifted"), encoding="utf-8")
    with pytest.raises(CatalogError, match=match):
        load_catalog_documents(repo)


@pytest.mark.parametrize("mutation, match", [
    ("header-secret", "unknown ids"),
    ("browser-key", "unknown ids"),
    ("browser-runtime", "omits declared runtime version"),
    ("manifest-mcp", "must equal vendors.yaml MCP tools"),
    ("provider-tools", "must equal server playwright.tools"),
])
def test_catalog_rejects_placeholder_browser_and_matrix_drift(
    tmp_path: Path, mutation: str, match: str
) -> None:
    repo = _copy_catalog(tmp_path)
    if mutation == "header-secret":
        path = repo / "agents" / "env" / "mcp" / "servers.yaml"
        value = _yaml(path)
        value["servers"]["web-reader"]["headers"] = {"X-Token": "${GHOST_SECRET}"}
    elif mutation == "browser-key":
        path = repo / "agents" / "env" / "browser.yaml"
        value = _yaml(path)
        value["providers"]["chrome-devtools"]["checks"][0]["keys"].append("GHOST_ENV_OR_LOCAL_KEY")
    elif mutation == "browser-runtime":
        path = repo / "agents" / "env" / "browser.yaml"
        value = _yaml(path)
        value["providers"]["playwright"]["launch"]["args"][1] = "@playwright/mcp@latest"
    elif mutation == "manifest-mcp":
        path = repo / "agents" / "env" / "manifest.yaml"
        value = _yaml(path)
        value["modules"]["mcp"]["tools"].remove("zcode")
        value["modules"]["mcp"]["exclude"].append("zcode")
    else:
        path = repo / "agents" / "env" / "browser.yaml"
        value = _yaml(path)
        value["providers"]["playwright"]["tools"].remove("cursor")
    _write_yaml(path, value)
    with pytest.raises(CatalogError, match=match):
        load_catalog_documents(repo)


def test_vendor_matrix_drives_cli_adapters_and_docs() -> None:
    docs = load_catalog_documents(ROOT)
    assert TOOLS == docs.vendors.cli_tools
    assert docs.vendors.adapter_tools == ("cursor", "kiro", "opencode", "kimi-code", "zcode")
    assert render_vendor_docs(docs.vendors) in (ROOT / "agents" / "env" / "README.md").read_text(encoding="utf-8")
    assert docs.vendors.capability("zcode").secret_mode == "literal-at-apply"
    assert docs.vendors.capability("zcode").sensitive is True


@pytest.mark.parametrize("tool", ["cursor", "kiro", "opencode", "kimi-code", "zcode"])
def test_adapter_render_matches_golden(tool: str, tmp_home: Path) -> None:
    cat = Catalog(ROOT)
    adapter = adapter_for(cat.vendor_matrix, tool)
    selected = cat.selected_servers(tool, "research")
    rendered = adapter.render(selected)
    actual = {"required_secrets": list(rendered.required_secrets), "servers": rendered.servers}
    expected = json.loads((GOLDEN / f"{tool}-research.json").read_text(encoding="utf-8"))
    assert actual == expected
    assert adapter.read_actual(tmp_home).state == "missing"


def _document_for(adapter, block: dict) -> dict:
    value: dict = {}
    current = value
    for component in adapter.capability.block_path[:-1]:
        current[component] = {}
        current = current[component]
    current[adapter.capability.block_path[-1]] = block
    return value


@pytest.mark.parametrize("tool", ["cursor", "kiro", "opencode", "kimi-code", "zcode"])
def test_adapter_distinguishes_malformed_unowned_and_preserves_unowned(tool: str, tmp_home: Path) -> None:
    cat = Catalog(ROOT)
    adapter = adapter_for(cat.vendor_matrix, tool)
    target = adapter.target(tmp_home)
    target.parent.mkdir(parents=True)
    target.write_text("{broken", encoding="utf-8")
    assert adapter.read_actual(tmp_home).state == "malformed"

    target.write_text(json.dumps(_document_for(adapter, {"my-local": {"command": "mine"}})), encoding="utf-8")
    actual = adapter.read_actual(tmp_home)
    assert actual.state == "present"
    assert adapter.unowned_ids(actual, {"managed"}) == ("my-local",)
    merged = json.loads(adapter.merge(actual, {"managed": {"command": "safe"}}))
    current = merged
    for component in adapter.capability.block_path:
        current = current[component]
    assert current["my-local"] == {"command": "mine"}
    assert current["managed"] == {"command": "safe"}


def test_adapter_marks_symlink_target_unsafe(tmp_home: Path) -> None:
    cat = Catalog(ROOT)
    adapter = adapter_for(cat.vendor_matrix, "cursor")
    target = adapter.target(tmp_home)
    target.parent.mkdir(parents=True)
    outside = tmp_home / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    target.symlink_to(outside)
    assert adapter.read_actual(tmp_home).state == "unsafe"


def _plan_snapshot(plan, home: Path) -> dict:
    return {
        "schema_version": plan.schema_version,
        "kind": plan.kind,
        "profile": plan.profile,
        "tools": list(plan.tools),
        "items": {
            item.adapter: {
                "expected_hash": item.expected_hash,
                "risk": item.risk,
                "target": str(Path(item.target).relative_to(home)),
            }
            for item in plan.items
        },
    }


def test_sync_plan_matches_snapshot_is_immutable_and_contains_no_secret_value(tmp_home: Path) -> None:
    cat = Catalog(ROOT)
    plan = compile_sync_plan(cat, "research", cat.vendor_matrix.cli_tools, home=tmp_home)
    expected = json.loads((GOLDEN / "plan-research.json").read_text(encoding="utf-8"))
    assert _plan_snapshot(plan, tmp_home) == expected
    payload = plan_json(plan)
    from dotf_core.schemas import validate_sync_plan
    assert validate_sync_plan(json.loads(payload)) == plan
    assert FAKE_SECRET not in payload
    assert "ZHIPU_API_KEY" in payload
    with pytest.raises(FrozenInstanceError):
        plan.profile = "browser"  # type: ignore[misc]


def _tree(path: Path) -> dict[str, tuple[int, bytes]]:
    if not path.exists():
        return {}
    return {
        str(item.relative_to(path)): (stat.S_IMODE(item.lstat().st_mode), item.read_bytes())
        for item in path.rglob("*")
        if item.is_file() and not item.is_symlink()
    }


def test_planning_forbids_secret_lookup_subprocess_and_all_writes(
    tmp_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_before = _tree(ROOT / "agents" / "env")
    home_before = _tree(tmp_home)
    home_paths_before = {str(item.relative_to(tmp_home)) for item in tmp_home.rglob("*")}

    def forbidden(*args, **kwargs):
        raise AssertionError("forbidden planning call")

    monkeypatch.setattr("sync_plan.lookup_env_value", forbidden)
    monkeypatch.setattr("common._senv_get", forbidden)
    monkeypatch.setattr("mcp_runtime.atomic_write", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    cat = Catalog(ROOT)
    plan = compile_sync_plan(cat, "research", ["zcode"], home=tmp_home)
    assert plan.items[0].required_secrets == ("ZHIPU_API_KEY",)
    assert _tree(ROOT / "agents" / "env") == repo_before
    assert _tree(tmp_home) == home_before == {}
    assert {str(item.relative_to(tmp_home)) for item in tmp_home.rglob("*")} == home_paths_before


def test_plan_distinguishes_missing_malformed_and_unowned(tmp_home: Path) -> None:
    cat = Catalog(ROOT)
    missing = compile_sync_plan(cat, "research", ["cursor"], home=tmp_home).items[0]
    assert (missing.actual_state, missing.state, missing.action) == ("missing", "create", "create")

    target = tmp_home / ".cursor" / "mcp.json"
    target.parent.mkdir(parents=True)
    target.write_text("not-json", encoding="utf-8")
    malformed = compile_sync_plan(cat, "research", ["cursor"], home=tmp_home).items[0]
    assert malformed.actual_state == "malformed"
    assert malformed.state == "conflict"
    assert malformed.action == "skip"

    target.write_text(json.dumps({"mcpServers": {"private": {"command": "mine"}}}), encoding="utf-8")
    unowned = compile_sync_plan(cat, "research", ["cursor"], home=tmp_home).items[0]
    assert unowned.actual_state == "unowned"
    assert unowned.state == "update"


def test_apply_requires_approval_before_secret_lookup_or_write(
    tmp_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cat = Catalog(ROOT)
    plan = compile_sync_plan(cat, "research", ["zcode"], home=tmp_home)
    monkeypatch.setattr("sync_plan.lookup_env_value", lambda name: (_ for _ in ()).throw(AssertionError("secret lookup")))
    with pytest.raises(SyncPlanError, match="approval"):
        apply_sync_plan(plan, cat, approved=False, home=tmp_home)
    assert _tree(tmp_home) == {}


def test_zcode_apply_resolves_after_approval_and_enforces_private_modes(
    tmp_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cat = Catalog(ROOT)
    ancestor = tmp_home / ".zcode"
    parent = ancestor / "cli"
    parent.mkdir(parents=True, mode=0o755)
    ancestor.chmod(0o755)
    parent.chmod(0o755)
    plan = compile_sync_plan(cat, "research", ["zcode"], home=tmp_home)
    calls: list[str] = []

    def resolve(name: str) -> str:
        calls.append(name)
        return FAKE_SECRET

    monkeypatch.setattr("sync_plan.lookup_env_value", resolve)
    results, secret_values = apply_sync_plan(plan, cat, approved=True, home=tmp_home)
    target = tmp_home / ".zcode" / "cli" / "config.json"
    assert results[0].status == "changed"
    assert calls == ["ZHIPU_API_KEY"]
    assert secret_values == (FAKE_SECRET,)
    assert FAKE_SECRET in target.read_text(encoding="utf-8")
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(target.parent.parent.stat().st_mode) == 0o700


def test_zcode_no_secret_machine_dry_run_has_no_writes(tmp_home: Path) -> None:
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_home),
        "XDG_CONFIG_HOME": str(tmp_home / ".config"),
        "XDG_STATE_HOME": str(tmp_home / ".state"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "agents" / "env_sync.py"), "zcode", "--dry-run", "--json", "--root", str(ROOT)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["items"][0]["required_secrets"] == ["ZHIPU_API_KEY"]
    assert _tree(tmp_home) == {}


def test_apply_cli_never_logs_literal_secret(tmp_home: Path) -> None:
    env = os.environ.copy()
    env.update({
        "HOME": str(tmp_home),
        "XDG_CONFIG_HOME": str(tmp_home / ".config"),
        "XDG_STATE_HOME": str(tmp_home / ".state"),
        "ZHIPU_API_KEY": FAKE_SECRET,
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "agents" / "env_sync.py"), "zcode", "--root", str(ROOT)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert FAKE_SECRET not in result.stdout + result.stderr
    target = tmp_home / ".zcode" / "cli" / "config.json"
    assert FAKE_SECRET in target.read_text(encoding="utf-8")


def test_zcode_update_persists_no_plaintext_secret_in_state_or_backups(
    tmp_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cat = Catalog(ROOT)
    monkeypatch.setattr("sync_plan.lookup_env_value", lambda name: FAKE_SECRET)
    state_home = tmp_home / ".state"
    first = compile_sync_plan(cat, "research", ["zcode"], home=tmp_home)
    apply_sync_plan(first, cat, approved=True, home=tmp_home, state_home=state_home)
    target = tmp_home / ".zcode" / "cli" / "config.json"
    target.parent.chmod(0o755)
    target.parent.parent.chmod(0o755)

    update = compile_sync_plan(cat, "browser", ["zcode"], home=tmp_home, state_home=state_home)
    assert update.items[0].action == "update"
    results, _ = apply_sync_plan(update, cat, approved=True, home=tmp_home, state_home=state_home)
    assert results[0].backup is None
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(target.parent.parent.stat().st_mode) == 0o700
    marker = FAKE_SECRET.encode("utf-8")
    assert all(marker not in content for _, content in _tree(state_home).values())


def test_env_sync_error_surface_sanitizes_secret(
    tmp_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import env_sync

    monkeypatch.setenv("HOME", str(tmp_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_home / ".config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_home / ".state"))
    monkeypatch.setenv("ZHIPU_API_KEY", FAKE_SECRET)

    def fail(*args, **kwargs):
        raise ValueError(f"Authorization: Bearer {FAKE_SECRET}")

    monkeypatch.setattr(env_sync, "apply_sync_plan", fail)
    with pytest.raises(SystemExit) as caught:
        env_sync.main(["zcode", "--root", str(ROOT)])
    message = str(caught.value)
    assert FAKE_SECRET not in message
    assert "[REDACTED]" in message


def test_apply_rejects_repository_targets_and_state_before_secret_lookup(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    cat = Catalog(ROOT)
    plan = compile_sync_plan(cat, "research", ["zcode"], home=ROOT)

    def forbidden(name: str) -> str:
        raise AssertionError("secret lookup must not happen")

    monkeypatch.setattr("sync_plan.lookup_env_value", forbidden)
    with pytest.raises(SyncPlanError, match="outside the repository"):
        apply_sync_plan(plan, cat, approved=True, home=ROOT, state_home=ROOT / ".state")
    assert not (ROOT / ".zcode").exists()
    assert not (ROOT / ".state").exists()


def test_public_sync_wrapper_delegates_vendor_and_capability_validation_to_matrix(
    tmp_path: Path,
) -> None:
    repo = _copy_catalog(tmp_path)
    vendor_id = "matrix-extra"
    old_table = render_vendor_docs(load_vendor_matrix(repo))

    vendors_path = repo / "agents" / "env" / "vendors.yaml"
    vendors = _yaml(vendors_path)
    vendors["vendors"][vendor_id] = {
        "cli": True,
        "mcp": False,
        "adapter": "none",
        "target": None,
        "block_path": [],
        "transports": [],
        "secret_mode": "unsupported",
        "runtime_versions": False,
        "sensitive": False,
        "docs": "Mutation vendor supports shared skills but not MCP sync",
    }
    _write_yaml(vendors_path, vendors)

    manifest_path = repo / "agents" / "env" / "manifest.yaml"
    manifest = _yaml(manifest_path)
    manifest["tools"].append(vendor_id)
    manifest["unsupported"][vendor_id] = {
        "mcp": "skip",
        "reason": "MCP sync is unsupported by the mutation vendor",
    }
    _write_yaml(manifest_path, manifest)

    readme_path = repo / "agents" / "env" / "README.md"
    readme_path.write_text(
        readme_path.read_text(encoding="utf-8").replace(
            old_table, render_vendor_docs(load_vendor_matrix(repo))
        ),
        encoding="utf-8",
    )
    (repo / "agents" / "skills").mkdir()
    shutil.copy2(ROOT / "agents" / "runtime.yaml", repo / "agents" / "runtime.yaml")
    shutil.copy2(ROOT / "agents" / "skills-defaults.yaml", repo / "agents" / "skills-defaults.yaml")
    shutil.copy2(ROOT / "agents" / "skills-defaults.lock.yaml", repo / "agents" / "skills-defaults.lock.yaml")

    home = tmp_path / "home"
    home.mkdir()
    env = os.environ.copy()
    env.update({
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_STATE_HOME": str(home / ".state"),
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    wrapper = ROOT / "scripts" / "agents" / "sync.sh"
    accepted = subprocess.run(
        ["bash", str(wrapper), vendor_id, "--skills-only", "--dry-run", "--root", str(repo)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
        check=False,
    )
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    assert f"tool={vendor_id}" in accepted.stdout

    unsupported = subprocess.run(
        ["bash", str(wrapper), vendor_id, "--env-only", "--dry-run", "--root", str(repo)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
        check=False,
    )
    assert unsupported.returncode != 0
    assert vendor_id in unsupported.stderr
    assert "vendors.yaml" in unsupported.stderr
    wrapper_text = wrapper.read_text(encoding="utf-8")
    assert "cursor | kiro | opencode" not in wrapper_text


def test_sensitive_equivalent_content_plans_and_applies_mode_only_remediation(
    tmp_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cat = Catalog(ROOT)
    monkeypatch.setattr("sync_plan.lookup_env_value", lambda name: FAKE_SECRET)
    created = compile_sync_plan(cat, "research", ["zcode"], home=tmp_home)
    first_results, _ = apply_sync_plan(created, cat, approved=True, home=tmp_home)
    assert first_results[0].status == "changed"

    target = tmp_home / ".zcode" / "cli" / "config.json"
    ancestors = (target.parent.parent, target.parent)
    retained_inodes = tuple((path.stat().st_dev, path.stat().st_ino) for path in (*ancestors, target))
    for ancestor in ancestors:
        ancestor.chmod(0o755)
    target.chmod(0o644)

    calls: list[str] = []

    def forbidden_lookup(name: str) -> str:
        calls.append(name)
        raise AssertionError("mode-only remediation must not resolve secrets")

    monkeypatch.setattr("sync_plan.lookup_env_value", forbidden_lookup)
    repair = compile_sync_plan(cat, "research", ["zcode"], home=tmp_home)
    item = repair.items[0]
    assert (item.actual_state, item.state, item.action) == ("present", "permission", "chmod")
    assert FAKE_SECRET not in plan_json(repair)

    results, secret_values = apply_sync_plan(repair, cat, approved=True, home=tmp_home)
    assert results[0].status == "changed"
    assert results[0].backup is None
    assert calls == []
    assert secret_values == ()
    assert tuple((path.stat().st_dev, path.stat().st_ino) for path in (*ancestors, target)) == retained_inodes
    assert [stat.S_IMODE(path.stat().st_mode) for path in ancestors] == [0o700, 0o700]
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert FAKE_SECRET in target.read_text(encoding="utf-8")

    unchanged = compile_sync_plan(cat, "research", ["zcode"], home=tmp_home).items[0]
    assert (unchanged.state, unchanged.action) == ("unchanged", "none")


def test_sensitive_mode_repair_chmods_retained_inode_and_rejects_leaf_swap(
    tmp_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cat = Catalog(ROOT)
    monkeypatch.setattr("sync_plan.lookup_env_value", lambda name: FAKE_SECRET)
    created = compile_sync_plan(cat, "research", ["zcode"], home=tmp_home)
    apply_sync_plan(created, cat, approved=True, home=tmp_home)

    target = tmp_home / ".zcode" / "cli" / "config.json"
    target.parent.parent.chmod(0o755)
    target.parent.chmod(0o755)
    target.chmod(0o644)
    repair = compile_sync_plan(cat, "research", ["zcode"], home=tmp_home)
    assert repair.items[0].action == "chmod"
    monkeypatch.setattr(
        "sync_plan.lookup_env_value",
        lambda name: (_ for _ in ()).throw(AssertionError("secret lookup")),
    )

    displaced = target.with_name("retained-config.json")
    original_bytes = target.read_bytes()
    real_fchmod = os.fchmod
    swapped = False

    def swap_leaf_before_chmod(fd: int, mode: int) -> None:
        nonlocal swapped
        if not swapped and stat.S_ISREG(os.fstat(fd).st_mode):
            target.rename(displaced)
            target.write_bytes(original_bytes)
            target.chmod(0o644)
            swapped = True
        real_fchmod(fd, mode)

    monkeypatch.setattr("sync_plan.os.fchmod", swap_leaf_before_chmod)
    with pytest.raises(SyncPlanError, match="path changed during permission remediation"):
        apply_sync_plan(repair, cat, approved=True, home=tmp_home)

    assert swapped
    assert stat.S_IMODE(target.stat().st_mode) == 0o644
    assert stat.S_IMODE(displaced.stat().st_mode) == 0o600
    assert target.read_bytes() == displaced.read_bytes() == original_bytes
