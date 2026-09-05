"""OpenSpec CLI skills install to the shared ~/.agents/skills tree."""

from __future__ import annotations

import importlib
import shutil
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent

import sys

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "agents"))


def _load(name: str):
    return importlib.import_module(name)


SKILL_BODY = """---
name: openspec-propose
description: Propose a new change.
allowed-tools: Bash(openspec:*)
license: MIT
metadata:
  author: openspec
  generatedBy: "1.8.0"
---

Propose a change.
"""


def _fake_generate(destination: Path, *, openspec: Path) -> Path:
    del openspec
    skills = destination / "skills"
    skill = skills / "openspec-propose"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(SKILL_BODY, encoding="utf-8")
    return skills


def _repo_with_runtime(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "agents" / "skills").mkdir(parents=True)
    shutil.copy2(ROOT / "agents" / "runtime.yaml", repo / "agents" / "runtime.yaml")
    return repo


def test_missing_openspec_cli_skips_without_writes(
    tmp_path: Path, tmp_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    openspec_skills = _load("openspec_skills")
    repo = _repo_with_runtime(tmp_path)
    monkeypatch.setattr(openspec_skills, "openspec_command", lambda: None)
    destination = tmp_home / ".agents" / "skills"
    assert openspec_skills.install_openspec_skills(repo, dest_root=destination) == 0
    assert not destination.exists()


def test_first_party_openspec_overlap_fails_closed(tmp_path: Path, tmp_home: Path) -> None:
    openspec_skills = _load("openspec_skills")
    repo = _repo_with_runtime(tmp_path)
    overlap = repo / "agents" / "skills" / "openspec-propose"
    overlap.mkdir()
    (overlap / "SKILL.md").write_text("---\nname: openspec-propose\ndescription: d\n---\n", encoding="utf-8")
    destination = tmp_home / ".agents" / "skills"
    assert (
        openspec_skills.install_openspec_skills(
            repo,
            dest_root=destination,
            generate=_fake_generate,
            openspec=Path("/usr/bin/true"),
        )
        == 1
    )
    assert not destination.exists()


def test_installs_shared_and_kiro_through_managed_ownership(
    tmp_path: Path, tmp_home: Path
) -> None:
    openspec_skills = _load("openspec_skills")
    repo = _repo_with_runtime(tmp_path)
    shared = tmp_home / ".agents" / "skills"
    kiro = tmp_home / ".kiro" / "skills"
    assert (
        openspec_skills.install_openspec_skills(
            repo,
            dest_roots=(shared, kiro),
            generate=_fake_generate,
            openspec=Path("/usr/bin/true"),
        )
        == 0
    )
    shared_target = shared / "openspec-propose" / "SKILL.md"
    kiro_target = kiro / "openspec-propose" / "SKILL.md"
    assert shared_target.read_text(encoding="utf-8") == SKILL_BODY
    assert "allowed-tools: Bash(openspec:*)" in shared_target.read_text(encoding="utf-8")
    assert kiro_target.read_text(encoding="utf-8").rstrip().endswith("$ARGUMENTS")
    manifest = yaml.safe_load((tmp_home / ".local" / "state" / "dotf" / "agents-manifest.json").read_text())
    assert {item["owner"] for item in manifest["items"] if "openspec" in item["owner"]} == {
        "agents:openspec:openspec-propose",
        "agents:kiro-openspec:openspec-propose",
    }
    shared_before = shared_target.stat().st_mtime_ns
    assert (
        openspec_skills.install_openspec_skills(
            repo,
            dest_roots=(shared, kiro),
            generate=_fake_generate,
            openspec=Path("/usr/bin/true"),
        )
        == 0
    )
    assert shared_target.stat().st_mtime_ns == shared_before


def test_adopts_equivalent_unowned_file(tmp_path: Path, tmp_home: Path) -> None:
    openspec_skills = _load("openspec_skills")
    repo = _repo_with_runtime(tmp_path)
    shared = tmp_home / ".agents" / "skills"
    target = shared / "openspec-propose" / "SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text(SKILL_BODY, encoding="utf-8")
    assert (
        openspec_skills.install_openspec_skills(
            repo,
            dest_root=shared,
            generate=_fake_generate,
            openspec=Path("/usr/bin/true"),
        )
        == 0
    )
    assert target.read_text(encoding="utf-8") == SKILL_BODY
    manifest = yaml.safe_load((tmp_home / ".local" / "state" / "dotf" / "agents-manifest.json").read_text())
    assert any(item["owner"] == "agents:openspec:openspec-propose" for item in manifest["items"])


def test_conflicts_on_divergent_unowned_file(tmp_path: Path, tmp_home: Path) -> None:
    openspec_skills = _load("openspec_skills")
    repo = _repo_with_runtime(tmp_path)
    shared = tmp_home / ".agents" / "skills"
    target = shared / "openspec-propose" / "SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text(SKILL_BODY + "local edit\n", encoding="utf-8")
    assert (
        openspec_skills.install_openspec_skills(
            repo,
            dest_root=shared,
            generate=_fake_generate,
            openspec=Path("/usr/bin/true"),
        )
        == 1
    )
    assert target.read_text(encoding="utf-8").endswith("local edit\n")


def test_sync_sh_invokes_openspec_skills() -> None:
    script = (ROOT / "scripts" / "agents" / "sync.sh").read_text(encoding="utf-8")
    assert 'python3 "$SCRIPT_DIR/openspec_skills.py"' in script
    assert "--- openspec skills ---" in script


@pytest.mark.skipif(shutil.which("openspec") is None, reason="openspec CLI required")
def test_generate_uses_shared_agents_tool(tmp_path: Path) -> None:
    openspec_skills = _load("openspec_skills")
    skills = openspec_skills.generate_openspec_skills(
        tmp_path, openspec=Path(shutil.which("openspec"))
    )
    assert (skills / "openspec-propose" / "SKILL.md").is_file()
    assert not (skills / ".openspec-target").exists()
    names = {path.name for path in skills.iterdir() if path.is_dir()}
    assert names
    assert all(name.startswith("openspec-") for name in names)


def test_passthrough_keeps_allowed_tools(tmp_path: Path) -> None:
    openspec_skills = _load("openspec_skills")
    path = tmp_path / "openspec-propose"
    path.mkdir()
    (path / "SKILL.md").write_text(SKILL_BODY, encoding="utf-8")
    rendered = openspec_skills.render_openspec_skill_bytes(path, "openspec-propose")
    assert b"allowed-tools: Bash(openspec:*)" in rendered
    kiro = openspec_skills.render_openspec_kiro_skill_bytes(path, "openspec-propose")
    assert kiro.decode("utf-8").rstrip().endswith("$ARGUMENTS")
