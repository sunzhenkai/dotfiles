"""Strict audited third-party skill lock and ownership installation tests."""

from __future__ import annotations

import hashlib
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


def test_repository_defaults_use_empty_strict_lock_without_invented_approvals() -> None:
    defaults = _load("defaults")
    lock = defaults.load_catalog(ROOT)
    assert lock.kind == "third-party-skills-lock"
    assert lock.schema_version == 1
    assert lock.skills == ()
    assert yaml.safe_load((ROOT / "agents" / "skills-defaults.yaml").read_text())["skills"] == []


def test_unlocked_or_floating_catalog_fails_closed(tmp_path: Path) -> None:
    defaults = _load("defaults")
    repo = tmp_path / "repo"
    (repo / "agents" / "skills").mkdir(parents=True)
    shutil.copy2(ROOT / "agents" / "skills-defaults.lock.yaml", repo / "agents")
    (repo / "agents" / "skills-defaults.yaml").write_text(
        "version: 2\nlock: skills-defaults.lock.yaml\nskills: [unlocked]\n", encoding="utf-8"
    )
    with pytest.raises(defaults.ThirdPartyLockError, match="strict lock"):
        defaults.load_catalog(repo)

    (repo / "agents" / "skills-defaults.yaml").write_text(
        "version: 2\nlock: skills-defaults.lock.yaml\nskills: [demo]\n", encoding="utf-8"
    )
    (repo / "agents" / "skills-defaults.lock.yaml").write_text(
        "schema_version: 1\nkind: third-party-skills-lock\nskills:\n"
        "  - id: demo\n    source: https://github.com/example/demo\n"
        "    revision: main\n    subdirectory: skill\n    content_hash: '" + "a" * 64 + "'\n"
        "    license: {spdx: MIT, file: LICENSE, hash: '" + "b" * 64 + "'}\n"
        "    audit: {status: pending, date: '2026-09-04', tool: review, evidence: https://example.com/audit}\n",
        encoding="utf-8",
    )
    with pytest.raises(defaults.ThirdPartyLockError, match="revision|audit"):
        defaults.load_catalog(repo)


def test_checkout_verification_checks_revision_content_license_and_symlinks(tmp_path: Path) -> None:
    third_party = _load("third_party")
    checkout = tmp_path / "checkout"
    skill = checkout / "skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: demo\ndescription: demo\n---\nbody\n", encoding="utf-8")
    license_file = checkout / "LICENSE"
    license_file.write_text("MIT\n", encoding="utf-8")
    revision = "1" * 40
    item = third_party.LockedSkill(
        "demo",
        "https://github.com/example/demo",
        revision,
        "skill",
        third_party.tree_hash(skill),
        third_party.LicenseLock("MIT", "LICENSE", hashlib.sha256(license_file.read_bytes()).hexdigest()),
        third_party.AuditLock("approved", "2026-09-04", "manual-review-v1", "https://example.com/audit/demo"),
    )
    assert third_party.verify_checkout(item, checkout, revision) == skill
    with pytest.raises(third_party.ThirdPartyLockError, match="revision"):
        third_party.verify_checkout(item, checkout, "2" * 40)
    license_file.write_text("changed\n", encoding="utf-8")
    with pytest.raises(third_party.ThirdPartyLockError, match="license hash"):
        third_party.verify_checkout(item, checkout, revision)
    license_file.write_text("MIT\n", encoding="utf-8")
    (skill / "unsafe").symlink_to("SKILL.md")
    with pytest.raises(third_party.ThirdPartyLockError, match="symlink"):
        third_party.verify_checkout(item, checkout, revision)


def test_empty_lock_dry_run_and_apply_never_invoke_network(tmp_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    defaults = _load("defaults")
    calls: list[object] = []
    monkeypatch.setattr(defaults, "acquire_all", lambda lock, destination: (destination / "skills"))
    assert defaults.install_defaults(ROOT, dry_run=True, dest_root=tmp_home / ".agents" / "skills") == 0
    assert calls == []

    def empty_acquire(lock, destination):
        destination.mkdir(mode=0o700)
        skills = destination / "skills"
        skills.mkdir(mode=0o700)
        return skills

    monkeypatch.setattr(defaults, "acquire_all", empty_acquire)
    assert defaults.install_defaults(ROOT, dest_root=tmp_home / ".agents" / "skills") == 0
    assert not (tmp_home / ".agents" / "skills").exists()


def test_verified_locked_skill_installs_through_managed_ownership(tmp_path: Path, tmp_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    defaults = _load("defaults")
    third_party = _load("third_party")
    repo = tmp_path / "repo"
    (repo / "agents" / "skills").mkdir(parents=True)
    shutil.copy2(ROOT / "agents" / "runtime.yaml", repo / "agents" / "runtime.yaml")
    checkout = tmp_path / "checkout"
    skill = checkout / "skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: demo\ndescription: demo\n---\nbody\n", encoding="utf-8")
    (checkout / "LICENSE").write_text("MIT\n", encoding="utf-8")
    revision = "1" * 40
    content_hash = third_party.tree_hash(skill)
    license_hash = hashlib.sha256((checkout / "LICENSE").read_bytes()).hexdigest()
    (repo / "agents" / "skills-defaults.yaml").write_text(
        "version: 2\nlock: skills-defaults.lock.yaml\nskills: [demo]\n", encoding="utf-8"
    )
    (repo / "agents" / "skills-defaults.lock.yaml").write_text(
        "schema_version: 1\nkind: third-party-skills-lock\nskills:\n"
        "  - id: demo\n    source: https://github.com/example/demo\n"
        f"    revision: '{revision}'\n    subdirectory: skill\n    content_hash: {content_hash}\n"
        f"    license: {{spdx: MIT, file: LICENSE, hash: {license_hash}}}\n"
        "    audit: {status: approved, date: '2026-09-04', tool: test-review-v1, evidence: https://example.com/audit/demo}\n",
        encoding="utf-8",
    )

    def acquire(lock, destination):
        verified = third_party.verify_checkout(lock.skills[0], checkout, revision)
        destination.mkdir(mode=0o700)
        output = destination / "skills"
        output.mkdir(mode=0o700)
        shutil.copytree(verified, output / "demo")
        return output

    monkeypatch.setattr(defaults, "acquire_all", acquire)
    destination = tmp_home / ".agents" / "skills"
    assert defaults.install_defaults(repo, dest_root=destination) == 0
    target = destination / "demo" / "SKILL.md"
    assert target.is_file()
    manifest = yaml.safe_load((tmp_home / ".local" / "state" / "dotf" / "agents-manifest.json").read_text())
    assert {item["owner"] for item in manifest["items"]} == {"agents:third-party:demo"}
    before = target.stat().st_mtime_ns
    assert defaults.install_defaults(repo, dest_root=destination) == 0
    assert target.stat().st_mtime_ns == before
