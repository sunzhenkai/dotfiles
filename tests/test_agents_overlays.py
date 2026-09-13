"""External Agent/Codex overlays, safe defaults, and manifest status."""

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
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "agents"))

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
    profiles=frozenset({"coding", "research", "full"}),
    tools=frozenset({"cursor", "opencode"}),
    skills=frozenset({"grill-with-docs"}),
)


def _doc(**values):
    return {"schema_version": OVERLAY_SCHEMA_VERSION, "kind": OVERLAY_KIND, **values}


def _write_overlay(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _fake_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    env = repo / "agents" / "env"
    profiles = env / "profiles"
    profiles.mkdir(parents=True)
    (repo / "agents" / "vendors" / "codex").mkdir(parents=True)
    (env / "manifest.yaml").write_text(
        "version: 1\ntools: [cursor, opencode]\ndefault_profile: research\n",
        encoding="utf-8",
    )
    for name in ("coding", "research", "full"):
        (profiles / f"{name}.yaml").write_text(f"version: 1\nid: {name}\n", encoding="utf-8")
    return repo


def test_overlay_files_merge_in_utf8_name_order(tmp_home: Path) -> None:
    directory = overlay_directory(tmp_home)
    _write_overlay(
        directory / "20-last.yaml",
        _doc(agents={"profile": "research"}),
    )
    _write_overlay(
        directory / "10-first.yaml",
        _doc(agents={"profile": "coding", "enabled_skills": ["grill-with-docs"]}),
    )
    loaded = load_overlays(repo_root=ROOT, catalog=CATALOG, home=tmp_home, include_legacy=False)
    assert [path.name for path in loaded.files] == ["10-first.yaml", "20-last.yaml"]
    assert loaded.agents == {"profile": "research", "enabled_skills": ["grill-with-docs"]}


@pytest.mark.parametrize(
    "payload, message",
    [
        (_doc(unknown=True), "unknown keys"),
        (_doc(agents={"profile": 3}), "non-empty string"),
        (_doc(agents={"enabled_skills": ["missing-skill"]}), "unknown or unlocked skills"),
        (_doc(agents={"disabled_skills": ["openspec-propose"]}), "rejects OpenSpec skills"),
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
    legacy.write_text("profile: coding\nenabled_skills: []\n", encoding="utf-8")
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


def test_safe_default_profile_is_research_and_low_risk(tmp_home: Path) -> None:
    cat = Catalog(ROOT)
    assert cat.default_profile() == "research"
    assert cat.resolve_profile()["risk"] == "low"
    assert sorted(cat.resolve_profile()["modules"]) == ["agents", "env", "security", "tools"]


def test_no_latest_pins_in_agent_sources() -> None:
    normal_paths = [ROOT / "agents" / "env", ROOT / "agents" / "vendors"]
    offenders = []
    for base in normal_paths:
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in {".yaml", ".yml", ".json", ".toml", ".md"}:
                text = path.read_text(encoding="utf-8", errors="ignore")
                if "@latest" in text:
                    offenders.append(path.relative_to(ROOT))
    assert offenders == []


def test_registry_has_no_dotfiles_agents_source_link_target() -> None:
    text = (ROOT / "modules.yaml").read_text(encoding="utf-8")
    assert "dotfiles-agents" not in text
    assert "source: agents\n" not in text


def test_agents_status_uses_managed_manifest_hash(tmp_home: Path) -> None:
    target = tmp_home / ".config" / "dotf" / "managed" / "agents-skills.yaml"
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
                        "source_identity": "agents/skills.yaml",
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
source "$DOTFILES_ROOT/scripts/lib/registry.sh"
source "$DOTFILES_ROOT/scripts/lib/dispatch_config.sh"
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
