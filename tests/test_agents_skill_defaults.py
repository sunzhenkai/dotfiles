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

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "agents"))
def _load(name: str):
    return importlib.import_module(name)


def test_repository_catalog_matches_strict_lock() -> None:
    defaults = _load("defaults")
    catalog_mod = _load("skills_catalog")
    lock = defaults.load_catalog(ROOT)
    catalog = catalog_mod.load_skills_catalog(ROOT)
    ids = [item.id for item in lock.skills]
    third_party = set(catalog.third_party_ids())
    first_party = set(catalog.first_party_ids())
    assert lock.kind == "third-party-skills-lock"
    assert lock.schema_version == 1
    # every catalogued third-party id is lock-covered...
    assert third_party <= set(ids)
    # ...and no first-party id leaks into the lock (no source confusion).
    assert first_party.isdisjoint(ids)
    assert "ui-template-apply" in ids
    assert "ui-template-author" in ids
    assert "ui-template-design" in ids
    assert "setup-matt-pocock-skills" in ids
    assert "wait-what" in ids
    assert "writing-for-agents" in ids
    assert "wizard" in ids
    assert "to-questionnaire" in ids
    # taste-skill 仍在审计锁中，但已从编目注释掉 -> 不自动装，也不能经 overlay 引用。
    assert "taste-skill" in ids
    assert "taste-skill" not in set(catalog.ids())
    # lark-cli / en-chat 是 optional 编目条目：可经 overlay 启用，但不进默认 Desired Set。
    by_id = catalog.by_id()
    assert by_id["lark-cli"].optional is True
    assert by_id["en-chat"].optional is True
    assert by_id["wizard"].optional is True
    assert by_id["to-questionnaire"].optional is True
    assert by_id["frontend-slides"].optional is True
    assert by_id["frontend-slides"].aliases == ("ppt",)
    assert catalog.canonical_id("ppt") == "frontend-slides"
    assert "frontend-slides" in ids
    assert "frontend-slides" not in catalog.default_ids()
    assert "lark-cli" not in catalog.default_ids()
    assert "wizard" not in catalog.default_ids()
    assert "to-questionnaire" not in catalog.default_ids()
    assert "commit-push" in catalog.default_ids()
    assert "agent-roster-flow" in catalog.default_ids()
    assert "wait-what" in catalog.default_ids()
    assert "writing-for-agents" in catalog.default_ids()
    assert "ask-matt" not in ids
    assert all(item.audit.status == "approved" for item in lock.skills)


_OPTIONAL_CATALOG = """
version: 3
lock: skills.lock.yaml
groups:
  dotfiles:
    type: first-party
    skills:
      - commit-push
      - id: lark-cli
        optional: true
        aliases:
          - lark
"""


def test_catalog_optional_member_form() -> None:
    catalog_mod = _load("skills_catalog")
    catalog = catalog_mod.parse_catalog(yaml.safe_load(_OPTIONAL_CATALOG))
    by_id = catalog.by_id()
    assert by_id["commit-push"].optional is False
    assert by_id["lark-cli"].optional is True
    assert by_id["lark-cli"].aliases == ("lark",)
    assert catalog.canonical_id("lark") == "lark-cli"
    assert catalog.canonical_id("commit-push") == "commit-push"
    assert catalog.canonical_id("missing") is None
    assert catalog.default_ids() == ["commit-push"]
    assert catalog.ids() == ["commit-push", "lark-cli"]


def test_catalog_optional_member_form_rejects_bad_shapes() -> None:
    catalog_mod = _load("skills_catalog")
    with pytest.raises(catalog_mod.SkillsCatalogError, match="optional must be a boolean"):
        catalog_mod.parse_catalog(
            yaml.safe_load(_OPTIONAL_CATALOG.replace("optional: true", "optional: 1"))
        )
    with pytest.raises(catalog_mod.SkillsCatalogError, match="unknown keys"):
        catalog_mod.parse_catalog(
            yaml.safe_load(_OPTIONAL_CATALOG.replace("optional: true", "optional: true\n        extra: 1"))
        )
    with pytest.raises(catalog_mod.SkillsCatalogError, match="non-empty skill id"):
        catalog_mod.parse_catalog(
            yaml.safe_load(_OPTIONAL_CATALOG.replace("- id: lark-cli", "- id: ''"))
        )


def test_catalog_alias_collides_with_skill_id() -> None:
    catalog_mod = _load("skills_catalog")
    with pytest.raises(catalog_mod.SkillsCatalogError, match="collides with skill id"):
        catalog_mod.parse_catalog(
            yaml.safe_load(_OPTIONAL_CATALOG.replace("- lark", "- commit-push"))
        )


def test_catalog_duplicate_alias_is_rejected() -> None:
    catalog_mod = _load("skills_catalog")
    body = _OPTIONAL_CATALOG + (
        "      - id: extra\n        optional: true\n        aliases:\n          - lark\n"
    )
    with pytest.raises(catalog_mod.SkillsCatalogError, match="duplicate alias"):
        catalog_mod.parse_catalog(yaml.safe_load(body))


def _write_min_repo(repo: Path, lock_body: str, *, ids: list[str]) -> None:
    """Write a v3 catalog (one third-party group) + lock."""
    (repo / "agents").mkdir(parents=True, exist_ok=True)
    lines = [
        "version: 3",
        "lock: skills.lock.yaml",
        "groups:",
        "  test:",
        "    type: third-party",
        "    source: github",
        "    package: https://github.com/example/demo",
    ]
    if ids:
        lines.append("    skills:")
        lines += [f"      - {skill_id}" for skill_id in ids]
    else:
        lines.append("    skills: []")
    (repo / "agents" / "skills.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (repo / "agents" / "skills.lock.yaml").write_text(lock_body, encoding="utf-8")


def test_unlocked_or_floating_catalog_fails_closed(tmp_path: Path) -> None:
    defaults = _load("defaults")
    repo = tmp_path / "repo"
    (repo / "agents" / "skills").mkdir(parents=True)

    # third-party id not covered by the lock -> fail closed
    _write_min_repo(repo, "schema_version: 1\nkind: third-party-skills-lock\nskills: []\n", ids=["unlocked"])
    with pytest.raises(defaults.ThirdPartyLockError, match="covered by the strict lock"):
        defaults.load_catalog(repo)

    # floating revision + non-approved audit -> fail closed in the lock loader
    _write_min_repo(
        repo,
        "schema_version: 1\nkind: third-party-skills-lock\nskills:\n"
        "  - id: demo\n    source: https://github.com/example/demo\n"
        "    revision: main\n    subdirectory: skill\n    content_hash: '" + "a" * 64 + "'\n"
        "    license: {spdx: MIT, file: LICENSE, hash: '" + "b" * 64 + "'}\n"
        "    audit: {status: pending, date: '2026-09-04', tool: review, evidence: https://example.com/audit}\n",
        ids=["demo"],
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


def test_verified_locked_skill_installs_shared_and_kiro_through_managed_ownership(
    tmp_path: Path, tmp_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    _write_min_repo(
        repo,
        "schema_version: 1\nkind: third-party-skills-lock\nskills:\n"
        "  - id: demo\n    source: https://github.com/example/demo\n"
        f"    revision: '{revision}'\n    subdirectory: skill\n    content_hash: {content_hash}\n"
        f"    license: {{spdx: MIT, file: LICENSE, hash: {license_hash}}}\n"
        "    audit: {status: approved, date: '2026-09-04', tool: test-review-v1, evidence: https://example.com/audit/demo}\n",
        ids=["demo"],
    )

    def acquire(lock, destination):
        verified = third_party.verify_checkout(lock.skills[0], checkout, revision)
        destination.mkdir(mode=0o700)
        output = destination / "skills"
        output.mkdir(mode=0o700)
        shutil.copytree(verified, output / "demo")
        return output

    monkeypatch.setattr(defaults, "acquire_all", acquire)
    shared_destination = tmp_home / ".agents" / "skills"
    kiro_destination = tmp_home / ".kiro" / "skills"
    claude_destination = tmp_home / ".claude" / "skills"
    assert defaults.install_defaults(
        repo, dest_roots=(shared_destination, kiro_destination, claude_destination)
    ) == 0
    shared_target = shared_destination / "demo" / "SKILL.md"
    kiro_target = kiro_destination / "demo" / "SKILL.md"
    claude_target = claude_destination / "demo" / "SKILL.md"
    assert shared_target.is_file()
    assert kiro_target.is_file()
    assert claude_target.is_file()
    # Claude Code consumes $ARGUMENTS itself; only Kiro needs the explicit marker.
    assert kiro_target.read_text().rstrip().endswith("$ARGUMENTS")
    assert claude_target.read_text().rstrip().endswith("$ARGUMENTS") is False
    assert claude_target.read_bytes() == shared_target.read_bytes()
    manifest = yaml.safe_load((tmp_home / ".local" / "state" / "dotf" / "agents-manifest.json").read_text())
    assert {item["owner"] for item in manifest["items"]} == {
        "agents:third-party:demo",
        "agents:kiro-third-party:demo",
        "agents:claude-third-party:demo",
    }
    shared_before = shared_target.stat().st_mtime_ns
    kiro_before = kiro_target.stat().st_mtime_ns
    assert defaults.install_defaults(
        repo, dest_roots=(shared_destination, kiro_destination, claude_destination)
    ) == 0
    assert shared_target.stat().st_mtime_ns == shared_before
    assert kiro_target.stat().st_mtime_ns == kiro_before


def test_third_party_install_copies_unlisted_runtime_files(
    tmp_path: Path, tmp_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    defaults = _load("defaults")
    third_party = _load("third_party")
    repo = tmp_path / "repo"
    (repo / "agents" / "skills").mkdir(parents=True)
    shutil.copy2(ROOT / "agents" / "runtime.yaml", repo / "agents" / "runtime.yaml")
    checkout = tmp_path / "checkout"
    skill = checkout / "skill"
    (skill / "catalog").mkdir(parents=True)
    (skill / "runtime").mkdir()
    (skill / "patches").mkdir()
    (skill / "SKILL.md").write_text("---\nname: demo\ndescription: demo\n---\nbody\n", encoding="utf-8")
    (skill / "catalog" / "index.md").write_text("catalog\n", encoding="utf-8")
    (skill / "runtime" / "validate.py").write_text("print(1)\n", encoding="utf-8")
    (skill / "template.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (skill / "patches" / "private.txt").write_text("authoring\n", encoding="utf-8")
    (checkout / "LICENSE").write_text("MIT\n", encoding="utf-8")
    revision = "1" * 40
    content_hash = third_party.tree_hash(skill)
    license_hash = hashlib.sha256((checkout / "LICENSE").read_bytes()).hexdigest()
    _write_min_repo(
        repo,
        "schema_version: 1\nkind: third-party-skills-lock\nskills:\n"
        "  - id: demo\n    source: https://github.com/example/demo\n"
        f"    revision: '{revision}'\n    subdirectory: skill\n    content_hash: {content_hash}\n"
        f"    license: {{spdx: MIT, file: LICENSE, hash: {license_hash}}}\n"
        "    audit: {status: approved, date: '2026-09-04', tool: test-review-v1, evidence: https://example.com/audit/demo}\n",
        ids=["demo"],
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
    installed = destination / "demo"
    assert (installed / "SKILL.md").is_file()
    assert (installed / "catalog" / "index.md").read_text() == "catalog\n"
    assert (installed / "runtime" / "validate.py").read_text() == "print(1)\n"
    assert (installed / "template.sh").is_file()
    assert not (installed / "patches").exists()


def test_install_conflict_reports_file_and_reason(
    tmp_path: Path,
    tmp_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    defaults = _load("defaults")
    third_party = _load("third_party")
    repo = tmp_path / "repo"
    (repo / "agents" / "skills").mkdir(parents=True)
    shutil.copy2(ROOT / "agents" / "runtime.yaml", repo / "agents" / "runtime.yaml")
    checkout = tmp_path / "checkout"
    skill = checkout / "skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: demo\ndescription: demo\n---\nbody\n", encoding="utf-8"
    )
    (checkout / "LICENSE").write_text("MIT\n", encoding="utf-8")
    revision = "1" * 40
    content_hash = third_party.tree_hash(skill)
    license_hash = hashlib.sha256((checkout / "LICENSE").read_bytes()).hexdigest()
    _write_min_repo(
        repo,
        "schema_version: 1\nkind: third-party-skills-lock\nskills:\n"
        "  - id: demo\n    source: https://github.com/example/demo\n"
        f"    revision: '{revision}'\n    subdirectory: skill\n    content_hash: {content_hash}\n"
        f"    license: {{spdx: MIT, file: LICENSE, hash: {license_hash}}}\n"
        "    audit: {status: approved, date: '2026-09-04', tool: test-review-v1, evidence: https://example.com/audit/demo}\n",
        ids=["demo"],
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
    target.write_text("local edit\n", encoding="utf-8")
    capsys.readouterr()

    assert defaults.install_defaults(repo, dest_root=destination) == 1

    captured = capsys.readouterr()
    assert str(target) in captured.err
    assert "owned target was modified locally" in captured.err


def _lock_body_for(
    content_hash: str, license_hash: str, revision: str, *, extra_entry: bool
) -> str:
    body = (
        "schema_version: 1\nkind: third-party-skills-lock\nskills:\n"
        "  - id: demo\n    source: https://github.com/example/demo\n"
        f"    revision: '{revision}'\n    subdirectory: skill\n    content_hash: {content_hash}\n"
        f"    license: {{spdx: MIT, file: LICENSE, hash: {license_hash}}}\n"
        "    audit: {status: approved, date: '2026-09-04', tool: test-review-v1, evidence: https://example.com/audit/demo}\n"
    )
    if extra_entry:
        body += (
            "  - id: other\n    source: https://github.com/example/other\n"
            f"    revision: '{revision}'\n    subdirectory: other\n    content_hash: {content_hash}\n"
            f"    license: {{spdx: MIT, file: LICENSE, hash: {license_hash}}}\n"
            "    audit: {status: approved, date: '2026-09-04', tool: test-review-v1, evidence: https://example.com/audit/other}\n"
        )
    return body


def test_lock_digest_change_reowns_equivalent_third_party_bytes(
    tmp_path: Path, tmp_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Adding a lock entry must not block re-attesting unchanged skill bytes.

    The third-party identity embeds the whole-lock digest, so any lock edit
    rewrites every third-party identity. A target still owned by us whose bytes
    equal the newly locked content is re-recorded, not reported as a conflict.
    """
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
    _write_min_repo(
        repo, _lock_body_for(content_hash, license_hash, revision, extra_entry=False), ids=["demo"]
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
    installed = target.read_bytes()
    manifest_file = tmp_home / ".local" / "state" / "dotf" / "agents-manifest.json"

    def recorded_identity() -> str:
        items = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))["items"]
        return next(item["source_identity"] for item in items if item["target"] == str(target))

    identity_before = recorded_identity()

    # Same locked skill, but the lock file itself changed digest (new entry).
    _write_min_repo(
        repo, _lock_body_for(content_hash, license_hash, revision, extra_entry=True), ids=["demo"]
    )

    assert defaults.install_defaults(repo, dest_root=destination) == 0
    assert target.read_bytes() == installed
    identity_after = recorded_identity()
    assert identity_after != identity_before
    assert identity_after.endswith("demo/SKILL.md")


def test_relocked_third_party_content_updates_pristine_target(
    tmp_path: Path, tmp_home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Re-locking a skill to new upstream bytes must update an untouched target.

    The lock digest and the skill content move together on every `skills-lock-update`,
    so the identity mismatch and the new content arrive in the same run. A target
    still byte-identical to what we installed has no local edit to review, so it
    gets the new bytes instead of being reported as a conflict.
    """
    defaults = _load("defaults")
    third_party = _load("third_party")
    repo = tmp_path / "repo"
    (repo / "agents" / "skills").mkdir(parents=True)
    shutil.copy2(ROOT / "agents" / "runtime.yaml", repo / "agents" / "runtime.yaml")
    checkout = tmp_path / "checkout"
    skill = checkout / "skill"
    skill.mkdir(parents=True)
    (checkout / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (skill / "SKILL.md").write_text("---\nname: demo\ndescription: demo\n---\nbody\n", encoding="utf-8")
    license_hash = hashlib.sha256((checkout / "LICENSE").read_bytes()).hexdigest()
    revision = "1" * 40

    def relock(rev: str) -> None:
        _write_min_repo(
            repo,
            _lock_body_for(third_party.tree_hash(skill), license_hash, rev, extra_entry=False),
            ids=["demo"],
        )

    def acquire(lock, destination):
        verified = third_party.verify_checkout(lock.skills[0], checkout, lock.skills[0].revision)
        destination.mkdir(mode=0o700)
        output = destination / "skills"
        output.mkdir(mode=0o700)
        shutil.copytree(verified, output / "demo")
        return output

    monkeypatch.setattr(defaults, "acquire_all", acquire)
    destination = tmp_home / ".agents" / "skills"
    relock(revision)
    assert defaults.install_defaults(repo, dest_root=destination) == 0
    target = destination / "demo" / "SKILL.md"
    installed = target.read_bytes()

    # Upstream published a new body; re-locking rewrites content hash and digest.
    (skill / "SKILL.md").write_text(
        "---\nname: demo\ndescription: demo\n---\nnew upstream body\n", encoding="utf-8"
    )
    relock("2" * 40)
    capsys.readouterr()

    assert defaults.install_defaults(repo, dest_root=destination) == 0
    captured = capsys.readouterr()
    assert "identity differs" not in captured.err
    assert target.read_bytes() != installed
    assert b"new upstream body" in target.read_bytes()
