"""External Agent/Codex overlays, safe defaults, runtime pins, and manifest status."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "agents"))

from dotf_core.overlays import (  # noqa: E402
    OVERLAY_KIND,
    OVERLAY_SCHEMA_VERSION,
    OverlayCatalog,
    OverlayError,
    init_overlay,
    load_overlays,
    migrate_legacy,
    overlay_directory,
)
from common import Catalog  # noqa: E402
from managed_status import inspect_agents_manifest  # noqa: E402

CATALOG = OverlayCatalog(
    profiles=frozenset({"coding", "research", "browser", "full"}),
    servers=frozenset({"web-reader", "zai-vision", "playwright"}),
    tools=frozenset({"cursor", "opencode"}),
)


def _doc(**values):
    return {"schema_version": OVERLAY_SCHEMA_VERSION, "kind": OVERLAY_KIND, **values}


def _write_overlay(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _fake_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    env = repo / "agents" / "env"
    profiles = env / "mcp" / "profiles"
    profiles.mkdir(parents=True)
    (repo / "agents" / "vendors" / "codex").mkdir(parents=True)
    (env / "manifest.yaml").write_text(
        "version: 1\ntools: [cursor, opencode]\ndefault_profile: research\n",
        encoding="utf-8",
    )
    (env / "mcp" / "servers.yaml").write_text(
        "version: 1\nservers:\n  web-reader: {}\n  playwright: {}\n",
        encoding="utf-8",
    )
    for name in ("coding", "research", "browser", "full"):
        (profiles / f"{name}.yaml").write_text(f"id: {name}\nmcp_servers: []\n", encoding="utf-8")
    return repo


def test_overlay_files_merge_in_utf8_name_order(tmp_home: Path) -> None:
    directory = overlay_directory(tmp_home)
    _write_overlay(
        directory / "20-last.yaml",
        _doc(agents={"profile": "research", "disabled_servers": ["zai-vision"]}),
    )
    _write_overlay(
        directory / "10-first.yaml",
        _doc(agents={"profile": "coding", "disabled_servers": ["web-reader"]}),
    )
    loaded = load_overlays(repo_root=ROOT, catalog=CATALOG, home=tmp_home, include_legacy=False)
    assert [path.name for path in loaded.files] == ["10-first.yaml", "20-last.yaml"]
    assert loaded.agents == {"profile": "research", "disabled_servers": ["zai-vision"]}


@pytest.mark.parametrize(
    "payload, message",
    [
        (_doc(unknown=True), "unknown keys"),
        (_doc(agents={"profile": 3}), "non-empty string"),
        (_doc(agents={"enabled_servers": ["missing-server"]}), "unknown servers"),
        (_doc(agents={"exclude": {"missing-tool": {"servers": []}}}), "unknown tools"),
        ({"schema_version": 99, "kind": OVERLAY_KIND}, "schema_version"),
    ],
)
def test_overlay_schema_rejects_unknown_type_version_and_cross_refs(
    tmp_home: Path, payload: dict, message: str
) -> None:
    _write_overlay(overlay_directory(tmp_home) / "bad.yaml", payload)
    with pytest.raises(OverlayError, match=message):
        load_overlays(repo_root=ROOT, catalog=CATALOG, home=tmp_home, include_legacy=False)


def test_overlay_loader_rejects_repository_location(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(ROOT / ".private-test"))
    with pytest.raises(OverlayError, match="outside the repository"):
        load_overlays(repo_root=ROOT, catalog=CATALOG, include_legacy=False)
    assert not (ROOT / ".private-test").exists()


def test_initializer_writes_only_xdg_with_private_mode(tmp_home: Path) -> None:
    destination = init_overlay(ROOT, home=tmp_home)
    assert destination == tmp_home / ".config" / "dotf" / "overlays" / "00-local.yaml"
    assert destination.is_file()
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    value = yaml.safe_load(destination.read_text(encoding="utf-8"))
    assert value["agents"]["profile"] == "research"
    assert str(destination).startswith(str(tmp_home))


def test_legacy_inputs_warn_and_migrate_only_to_xdg(
    tmp_path: Path, tmp_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _fake_repo(tmp_path)
    legacy = repo / "agents" / "env" / "local.yaml"
    legacy.write_text("profile: coding\ndisabled_servers: [web-reader]\n", encoding="utf-8")
    codex = repo / "agents" / "vendors" / "codex" / "config.local.toml"
    codex.write_text('[projects."/private/work"]\ntrust_level = "trusted"\n', encoding="utf-8")

    loaded = load_overlays(repo_root=repo, catalog=CATALOG, home=tmp_home)
    warning = capsys.readouterr().err
    assert "deprecated repository-local config" in warning
    assert str(overlay_directory(tmp_home) / "90-migrated.yaml") in warning
    assert loaded.agents["profile"] == "coding"
    assert "/private/work" in (loaded.codex_local_toml or "")
    assert legacy.read_text(encoding="utf-8").startswith("profile: coding")

    destination = migrate_legacy(repo, home=tmp_home)
    assert destination == overlay_directory(tmp_home) / "90-migrated.yaml"
    assert destination.is_file()
    assert not any(path.name == "90-migrated.yaml" for path in repo.rglob("*"))
    migrated = yaml.safe_load(destination.read_text(encoding="utf-8"))
    assert migrated["codex"]["local_toml"].startswith('[projects."/private/work"]')


def test_safe_default_profile_excludes_browser_and_requires_no_browser_consent(tmp_home: Path) -> None:
    cat = Catalog(ROOT)
    assert cat.default_profile() == "research"
    assert cat.resolve_profile()["risk"] == "low"
    assert "playwright" not in cat.selected_servers("cursor")
    assert "browser" not in cat.resolve_profile()["modules"]


def test_runtime_packages_are_exact_and_no_normal_path_uses_latest(tmp_home: Path) -> None:
    cat = Catalog(ROOT)
    assert cat.servers["playwright"]["version"] == "0.0.80"
    assert cat.servers["zai-vision"]["version"] == "0.1.5"
    normal_paths = [ROOT / "agents" / "env", ROOT / "agents" / "vendors"]
    offenders = []
    for base in normal_paths:
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in {".yaml", ".yml", ".json", ".toml", ".md"}:
                text = path.read_text(encoding="utf-8", errors="ignore")
                if "@playwright/mcp@latest" in text or "@z_ai/mcp-server@latest" in text:
                    offenders.append(path.relative_to(ROOT))
    assert offenders == []


def test_plan_and_doctor_show_declared_runtime_version(tmp_home: Path) -> None:
    env = os.environ.copy()
    sync = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "agents" / "env_sync.py"),
            "cursor",
            "--profile",
            "research",
            "--dry-run",
            "--root",
            str(ROOT),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert sync.returncode == 0, sync.stdout + sync.stderr
    assert "declared_runtime_versions=" in sync.stdout
    assert "@z_ai/mcp-server@0.1.5" in sync.stdout
    assert "@playwright/mcp@0.0.80" not in sync.stdout

    doctor = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "agents" / "doctor.py"),
            "--profile",
            "research",
            "--tool",
            "cursor",
            "--verbose",
            "--root",
            str(ROOT),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert "declared runtime @z_ai/mcp-server@0.1.5" in doctor.stdout


def test_plan_shows_overlay_enabled_runtime_version(tmp_home: Path) -> None:
    _write_overlay(
        overlay_directory(tmp_home) / "10-browser-consent.yaml",
        _doc(agents={"profile": "research", "enabled_servers": ["playwright"]}),
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "agents" / "env_sync.py"),
            "cursor",
            "--profile",
            "research",
            "--dry-run",
            "--root",
            str(ROOT),
        ],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        cwd=str(ROOT),
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    header = next(
        line for line in result.stdout.splitlines() if line.startswith("declared_runtime_versions=")
    )
    assert "playwright:@playwright/mcp@0.0.80" in header
    assert "zai-vision:@z_ai/mcp-server@0.1.5" in header


def test_registry_has_no_dotfiles_agents_source_link_target() -> None:
    text = (ROOT / "modules.yaml").read_text(encoding="utf-8")
    assert "dotfiles-agents" not in text
    assert "source: agents\n" not in text


def test_agents_status_uses_managed_manifest_hash(tmp_home: Path) -> None:
    target = tmp_home / ".config" / "dotf" / "managed" / "agents-skills-defaults.yaml"
    target.parent.mkdir(parents=True)
    target.write_text("skills: []\n", encoding="utf-8")
    target.chmod(0o600)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    state = tmp_home / ".local" / "state"
    manifest = state / "dotf" / "config-manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "managed-manifest",
                "generated_at": "2026-09-04T00:00:00Z",
                "items": [
                    {
                        "owner": "config:agents",
                        "target": str(target),
                        "source_identity": "agents/skills-defaults.yaml",
                        "expected_hash": digest,
                        "installed_hash": digest,
                        "strategy": "render",
                        "mode": 0o600,
                        "run_id": "test-run",
                        "sensitive": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    status = inspect_agents_manifest(home=tmp_home, state_home=state)
    assert status.status == "unchanged"
    assert status.managed_count == 1

    target.write_text("skills: [changed]\n", encoding="utf-8")
    changed = inspect_agents_manifest(home=tmp_home, state_home=state)
    assert changed.status == "changed"


def test_codex_config_reads_external_overlay_only(tmp_home: Path) -> None:
    _write_overlay(
        overlay_directory(tmp_home) / "10-codex.yaml",
        _doc(codex={"local_toml": '[projects."/external/work"]\ntrust_level = "trusted"\n'}),
    )
    env = os.environ.copy()
    env["DOTFILES_ROOT"] = str(ROOT)
    script = r'''
set -euo pipefail
source "$DOTFILES_ROOT/scripts/lib/config_safe.sh"
source "$DOTFILES_ROOT/scripts/modules.sh"
source "$DOTFILES_ROOT/scripts/config.sh"
install_codex
'''
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    output = tmp_home / ".codex" / "config.toml"
    assert '/external/work' in output.read_text(encoding="utf-8")
    assert not (ROOT / "agents" / "vendors" / "codex" / "config.local.toml").exists()


def test_default_doctor_skips_browser_capability(tmp_home: Path) -> None:
    env = os.environ.copy()
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "agents" / "doctor.py"),
            "--json",
            "--root",
            str(ROOT),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    payload = json.loads(result.stdout)
    assert payload["profile"] == "research"
    browser = [item for item in payload["checks"] if item["group"] == "browser"]
    assert browser == [
        {
            "group": "browser",
            "id": "profile",
            "status": "skip",
            "message": "profile=research 未启用 browser 模块",
            "hint": "",
        }
    ]
    assert "playwright" not in json.dumps(payload)


def test_runtime_sync_never_writes_repository_templates(tmp_home: Path) -> None:
    templates = [
        ROOT / "agents" / "vendors" / "cursor" / "mcp.json",
        ROOT / "agents" / "vendors" / "kiro" / "mcp.json",
        ROOT / "agents" / "vendors" / "opencode" / "opencode.json",
        ROOT / "agents" / "vendors" / "kimi-code" / "mcp.json",
        ROOT / "agents" / "vendors" / "zcode" / "mcp.json",
    ]
    before = {path: path.read_bytes() for path in templates}
    env = os.environ.copy()
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "agents" / "env_sync.py"),
            "cursor",
            "--profile",
            "research",
            "--root",
            str(ROOT),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_home / ".cursor" / "mcp.json").is_file()
    assert {path: path.read_bytes() for path in templates} == before

    rejected = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "agents" / "env_sync.py"),
            "cursor",
            "--dry-run",
            "--also-repo-templates",
            "--root",
            str(ROOT),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert rejected.returncode != 0
    assert "unrecognized arguments" in rejected.stderr
