"""First-party Agent runtime ownership, safety, reconcile, and allowlist tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "agents"))

from managed_runtime import AGENTS_MANIFEST_NAME  # noqa: E402


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    skill = repo / "agents" / "skills" / "demo"
    (skill / "references").mkdir(parents=True)
    (skill / "scripts").mkdir()
    (skill / "patches").mkdir()
    (skill / "evals").mkdir()
    (skill / "experience").mkdir()
    (skill / "evolutions").mkdir()
    (skill / "authoring").mkdir()
    (repo / "agents" / "runtime.yaml").write_text(
        "version: 1\nskills:\n  files: [SKILL.md]\n"
        "  sidecars: [references, scripts]\n"
        "  excluded: [patches, evals, experience, evolutions, authoring]\n",
        encoding="utf-8",
    )
    (skill / "SKILL.md").write_text(
        "---\nname: demo\ndescription: demo skill\n---\nbody\n", encoding="utf-8"
    )
    (skill / "references" / "guide.md").write_text("guide\n", encoding="utf-8")
    (skill / "scripts" / "run.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    for name in ("patches", "evals", "experience", "evolutions", "authoring"):
        (skill / name / "private.txt").write_text(name, encoding="utf-8")
    return repo


def _run(repo: Path, home: Path, *, dry_run: bool = False) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["XDG_STATE_HOME"] = str(home / ".state")
    cmd = [sys.executable, str(ROOT / "scripts" / "agents" / "sync.py"), "--root", str(repo)]
    if dry_run:
        cmd.append("--dry-run")
    return subprocess.run(cmd, text=True, capture_output=True, env=env, cwd=ROOT, check=False)


def _manifest(home: Path) -> Path:
    return home / ".state" / "dotf" / AGENTS_MANIFEST_NAME


def test_manifest_permissions_records_and_idempotence(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    first = _run(repo, home)
    assert first.returncode == 0, first.stderr + first.stdout
    manifest = _manifest(home)
    before = manifest.stat().st_mtime_ns
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest.stat().st_mode & 0o777 == 0o600
    assert manifest.parent.stat().st_mode & 0o777 == 0o700
    assert data["schema_version"] == 1
    assert {item["owner"] for item in data["items"]} == {
        "agents:skill:demo",
        "agents:kiro-skill:demo",
    }
    assert all(item["expected_hash"] == item["installed_hash"] for item in data["items"])
    target = home / ".agents" / "skills" / "demo" / "SKILL.md"
    target_before = target.stat().st_mtime_ns
    second = _run(repo, home)
    assert second.returncode == 0, second.stderr + second.stdout
    assert "done skills: changed=0" in second.stdout
    assert "done kiro skills: changed=0" in second.stdout
    assert manifest.stat().st_mtime_ns == before
    assert target.stat().st_mtime_ns == target_before


def test_dry_run_is_side_effect_free(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    result = _run(repo, home, dry_run=True)
    assert result.returncode == 0, result.stderr + result.stdout
    assert not (home / ".agents").exists()
    assert not (home / ".state").exists()


def test_malformed_manifest_degrades_without_prune_or_overwrite(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    assert _run(repo, home).returncode == 0
    target = home / ".agents" / "skills" / "demo" / "SKILL.md"
    target.write_text("local\n", encoding="utf-8")
    manifest = _manifest(home)
    manifest.write_text('{"schema_version": 99}\n', encoding="utf-8")
    before = manifest.read_bytes()
    result = _run(repo, home)
    assert result.returncode != 0
    assert "malformed" in result.stderr
    assert target.read_text(encoding="utf-8") == "local\n"
    assert manifest.read_bytes() == before


def test_parent_and_leaf_symlink_attacks_are_preserved(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    for leaf in (False, True):
        home = tmp_path / ("leaf-home" if leaf else "parent-home")
        home.mkdir()
        outside = tmp_path / ("leaf-outside" if leaf else "parent-outside")
        outside.mkdir()
        if leaf:
            target_dir = home / ".agents" / "skills" / "demo"
            target_dir.mkdir(parents=True)
            outside_file = outside / "victim"
            outside_file.write_text("outside\n", encoding="utf-8")
            (target_dir / "SKILL.md").symlink_to(outside_file)
        else:
            (home / ".agents").mkdir()
            (home / ".agents" / "skills").symlink_to(outside, target_is_directory=True)
            outside_file = outside / "sentinel"
            outside_file.write_text("outside\n", encoding="utf-8")
        result = _run(repo, home)
        assert result.returncode != 0
        assert outside_file.read_text(encoding="utf-8") == "outside\n"
        assert not _manifest(home).exists()


def test_stale_sidecar_and_whole_skill_prune_only_when_unmodified(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    assert _run(repo, home).returncode == 0
    source = repo / "agents" / "skills" / "demo" / "references" / "guide.md"
    target = home / ".agents" / "skills" / "demo" / "references" / "guide.md"
    source.unlink()
    result = _run(repo, home)
    assert result.returncode == 0, result.stderr + result.stdout
    assert not target.exists()
    skill_source = repo / "agents" / "skills" / "demo"
    for path in sorted(skill_source.rglob("*"), key=lambda value: len(value.parts), reverse=True):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            path.rmdir()
    skill_source.rmdir()
    result = _run(repo, home)
    assert result.returncode == 0, result.stderr + result.stdout
    assert not (home / ".agents" / "skills" / "demo").exists()


def test_local_and_unowned_conflicts_are_preserved(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    unowned = home / ".agents" / "skills" / "demo" / "SKILL.md"
    unowned.parent.mkdir(parents=True)
    unowned.write_text("unowned\n", encoding="utf-8")
    result = _run(repo, home)
    assert result.returncode != 0
    assert unowned.read_text(encoding="utf-8") == "unowned\n"
    unowned.unlink()
    unowned.parent.rmdir()
    assert _run(repo, home).returncode == 0
    unowned.write_text("local\n", encoding="utf-8")
    result = _run(repo, home)
    assert result.returncode != 0
    assert unowned.read_text(encoding="utf-8") == "local\n"


def test_locally_modified_to_new_expected_bytes_still_conflicts(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    assert _run(repo, home).returncode == 0
    skill = repo / "agents" / "skills" / "demo"
    (skill / "SKILL.md").write_text(
        "---\nname: demo\ndescription: demo skill\n---\nnew body\n", encoding="utf-8"
    )
    from sync import render_skill_bytes

    target = home / ".agents" / "skills" / "demo" / "SKILL.md"
    expected = render_skill_bytes(skill, "demo")
    target.write_bytes(expected)
    result = _run(repo, home)
    assert result.returncode != 0
    assert "modified locally" in result.stderr
    assert target.read_bytes() == expected


def test_runtime_allowlist_excludes_authoring_trees(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    result = _run(repo, home)
    assert result.returncode == 0, result.stderr + result.stdout
    installed = home / ".agents" / "skills" / "demo"
    assert (installed / "SKILL.md").is_file()
    assert (installed / "references" / "guide.md").is_file()
    assert (installed / "scripts" / "run.sh").is_file()
    for name in ("patches", "evals", "experience", "evolutions", "authoring"):
        assert not (installed / name).exists()


def test_concurrent_syncs_serialize_without_manifest_loss(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["XDG_STATE_HOME"] = str(home / ".state")
    cmd = [sys.executable, str(ROOT / "scripts" / "agents" / "sync.py"), "--root", str(repo)]
    one = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, cwd=ROOT)
    two = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, cwd=ROOT)
    out1, err1 = one.communicate(timeout=30)
    out2, err2 = two.communicate(timeout=30)
    assert one.returncode == 0, err1 + out1
    assert two.returncode == 0, err2 + out2
    data = json.loads(_manifest(home).read_text(encoding="utf-8"))
    assert len(data["items"]) == 6
    assert len({item["target"] for item in data["items"]}) == 6


def test_symlinked_lock_is_rejected(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    home = tmp_path / "home"
    lock_dir = home / ".state" / "dotf"
    lock_dir.mkdir(parents=True)
    outside = tmp_path / "outside-lock"
    outside.write_text("outside\n", encoding="utf-8")
    (lock_dir / "agents-manifest.lock").symlink_to(outside)
    result = _run(repo, home)
    assert result.returncode != 0
    assert outside.read_text(encoding="utf-8") == "outside\n"


def test_duplicate_json_member_is_malformed_and_preserved(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    assert _run(repo, home).returncode == 0
    manifest = _manifest(home)
    duplicate = manifest.read_text(encoding="utf-8").replace(
        "{\n", '{\n  "schema_version": 1,\n', 1
    )
    assert duplicate.count('"schema_version"') == 2
    manifest.write_text(duplicate, encoding="utf-8")
    before = manifest.read_bytes()

    result = _run(repo, home)

    assert result.returncode != 0
    assert "malformed" in result.stderr
    assert manifest.read_bytes() == before


def test_manifest_mode_drift_is_repaired_without_rewrite(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    assert _run(repo, home).returncode == 0
    manifest = _manifest(home)
    manifest.chmod(0o644)
    before = (manifest.stat().st_ino, manifest.stat().st_mtime_ns, manifest.read_bytes())

    result = _run(repo, home)

    assert result.returncode == 0, result.stderr + result.stdout
    assert manifest.stat().st_mode & 0o777 == 0o600
    assert (manifest.stat().st_ino, manifest.stat().st_mtime_ns, manifest.read_bytes()) == before


def test_owned_target_mode_drift_conflicts_and_is_preserved(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    source = repo / "agents" / "skills" / "demo" / "scripts" / "run.sh"
    source.chmod(0o755)
    home = tmp_path / "home"
    home.mkdir()
    assert _run(repo, home).returncode == 0
    target = home / ".agents" / "skills" / "demo" / "scripts" / "run.sh"
    target.chmod(0o777)
    before = (target.stat().st_ino, target.stat().st_mtime_ns, target.read_bytes())

    result = _run(repo, home)

    assert result.returncode != 0
    assert "mode was modified locally" in result.stderr
    assert target.stat().st_mode & 0o777 == 0o777
    assert (target.stat().st_ino, target.stat().st_mtime_ns, target.read_bytes()) == before


def test_declared_source_mode_change_chmods_without_content_rewrite(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    source = repo / "agents" / "skills" / "demo" / "scripts" / "run.sh"
    source.chmod(0o644)
    home = tmp_path / "home"
    home.mkdir()
    assert _run(repo, home).returncode == 0
    target = home / ".agents" / "skills" / "demo" / "scripts" / "run.sh"
    before = (target.stat().st_ino, target.stat().st_mtime_ns, target.read_bytes())
    source.chmod(0o755)

    changed = _run(repo, home)

    assert changed.returncode == 0, changed.stderr + changed.stdout
    assert "done skills: changed=1" in changed.stdout
    assert target.stat().st_mode & 0o777 == 0o755
    assert (target.stat().st_ino, target.stat().st_mtime_ns, target.read_bytes()) == before
    manifest_item = next(
        item
        for item in json.loads(_manifest(home).read_text(encoding="utf-8"))["items"]
        if item["target"] == str(target)
    )
    assert manifest_item["mode"] == 0o755

    unchanged = _run(repo, home)
    assert unchanged.returncode == 0, unchanged.stderr + unchanged.stdout
    assert "done skills: changed=0" in unchanged.stdout
