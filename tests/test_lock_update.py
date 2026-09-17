"""Promote third-party lock entries to each source HEAD."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

import sys

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "agents"))

import lock_update  # noqa: E402
import third_party  # noqa: E402

SOURCE = "https://github.com/example/demo"


def _git(path: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(path), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout or f"git failed: {args}")
    return proc.stdout.strip()


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True)
    subprocess.run(
        ["git", "init", "--quiet", "-b", "main", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    _git(path, "config", "user.email", "dev@example.com")
    _git(path, "config", "user.name", "dev")
    _git(path, "config", "commit.gpgsign", "false")


def _commit(path: Path, message: str) -> str:
    _git(path, "add", "-A")
    _git(path, "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", message)
    return _git(path, "rev-parse", "HEAD")


def _write_skill(repo: Path, subdirectory: str, body: str) -> None:
    skill = repo / subdirectory
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(body, encoding="utf-8")


def _lock_body(items: list[third_party.LockedSkill]) -> str:
    return lock_update.dump_lock(items)


def _locked(
    skill_id: str,
    checkout: Path,
    subdirectory: str,
    revision: str,
    *,
    source: str = SOURCE,
) -> third_party.LockedSkill:
    skill = checkout / subdirectory
    license_file = checkout / "LICENSE"
    return third_party.LockedSkill(
        skill_id,
        source,
        revision,
        subdirectory,
        third_party.tree_hash(skill),
        third_party.LicenseLock(
            "MIT",
            "LICENSE",
            hashlib.sha256(license_file.read_bytes()).hexdigest(),
        ),
        third_party.AuditLock(
            "approved",
            "2026-09-01",
            lock_update.AUDIT_TOOL,
            f"{source}/commit/{revision}",
        ),
    )


def _write_repo(dotfiles: Path, lock: str) -> None:
    agents = dotfiles / "agents"
    agents.mkdir(parents=True)
    (agents / "skills.yaml").write_text(
        "version: 3\nlock: skills.lock.yaml\ngroups:\n"
        "  demo:\n    type: third-party\n    source: github\n"
        f"    package: {SOURCE}\n    skills:\n      - demo\n",
        encoding="utf-8",
    )
    (agents / "skills.lock.yaml").write_text(lock, encoding="utf-8")
    script = agents / "skills" / "skills-store" / "scripts"
    script.mkdir(parents=True)
    (script / "audit-skill.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")


def test_dump_lock_round_trips_through_loader() -> None:
    item = third_party.LockedSkill(
        "demo",
        SOURCE,
        "a" * 40,
        "skills/demo",
        "b" * 64,
        third_party.LicenseLock("MIT", "LICENSE", "c" * 64),
        third_party.AuditLock(
            "approved",
            "2026-09-17",
            lock_update.AUDIT_TOOL,
            f"{SOURCE}/commit/{'a' * 40}",
        ),
    )
    loaded = lock_update.load_lock_bytes(lock_update.dump_lock([item]))
    assert loaded.skills[0] == item


def test_update_lock_promotes_source_to_head(tmp_path: Path) -> None:
    upstream = tmp_path / "upstream"
    _init_repo(upstream)
    (upstream / "LICENSE").write_text("MIT\n", encoding="utf-8")
    _write_skill(upstream, "skills/demo", "---\nname: demo\ndescription: old\n---\nold\n")
    old = _commit(upstream, "old")
    _write_skill(upstream, "skills/demo", "---\nname: demo\ndescription: new\n---\nnew\n")
    new = _commit(upstream, "new")
    assert old != new

    _git(upstream, "checkout", "--quiet", old)
    item = _locked("demo", upstream, "skills/demo", old)
    _git(upstream, "checkout", "--quiet", "main")

    dotfiles = tmp_path / "dotfiles"
    _write_repo(dotfiles, _lock_body([item]))
    audits: list[Path] = []

    result = lock_update.update_lock(
        dotfiles,
        aliases={SOURCE: str(upstream)},
        audit=lambda path: (audits.append(path) or (0, "")),
        today="2026-09-17",
    )
    assert result.wrote is True
    assert result.updated[0].revision == new
    assert result.updated[0].skill_ids == ("demo",)
    loaded = third_party.load_lock(dotfiles / "agents" / "skills.lock.yaml")
    assert loaded.skills[0].revision == new
    assert loaded.skills[0].content_hash == third_party.tree_hash(upstream / "skills" / "demo")
    assert loaded.skills[0].audit.date == "2026-09-17"
    assert loaded.skills[0].audit.evidence == f"{SOURCE}/commit/{new}"
    assert len(audits) == 1
    assert audits[0].name == "demo"


def test_update_lock_unifies_mixed_revisions_on_one_source(tmp_path: Path) -> None:
    upstream = tmp_path / "upstream"
    _init_repo(upstream)
    (upstream / "LICENSE").write_text("MIT\n", encoding="utf-8")
    _write_skill(upstream, "skills/one", "---\nname: one\ndescription: a\n---\na\n")
    _write_skill(upstream, "skills/two", "---\nname: two\ndescription: a\n---\na\n")
    first = _commit(upstream, "first")
    _write_skill(upstream, "skills/two", "---\nname: two\ndescription: b\n---\nb\n")
    second = _commit(upstream, "second")

    _git(upstream, "checkout", "--quiet", first)
    one = _locked("one", upstream, "skills/one", first)
    _git(upstream, "checkout", "--quiet", second)
    two = _locked("two", upstream, "skills/two", second)

    dotfiles = tmp_path / "dotfiles"
    _write_repo(dotfiles, _lock_body([one, two]))
    result = lock_update.update_lock(
        dotfiles,
        aliases={SOURCE: str(upstream)},
        audit=lambda path: (0, ""),
        today="2026-09-17",
    )
    assert result.wrote is True
    loaded = third_party.load_lock(dotfiles / "agents" / "skills.lock.yaml")
    assert {item.revision for item in loaded.skills} == {second}


def test_update_lock_skips_write_when_already_current(tmp_path: Path) -> None:
    upstream = tmp_path / "upstream"
    _init_repo(upstream)
    (upstream / "LICENSE").write_text("MIT\n", encoding="utf-8")
    _write_skill(upstream, "skills/demo", "---\nname: demo\ndescription: x\n---\nx\n")
    revision = _commit(upstream, "only")
    item = _locked("demo", upstream, "skills/demo", revision)
    dotfiles = tmp_path / "dotfiles"
    payload = _lock_body([item])
    _write_repo(dotfiles, payload)
    result = lock_update.update_lock(
        dotfiles,
        aliases={SOURCE: str(upstream)},
        audit=lambda path: (0, ""),
        today="2026-09-17",
    )
    assert result.wrote is False
    assert result.current == (SOURCE,)
    assert (dotfiles / "agents" / "skills.lock.yaml").read_text(encoding="utf-8") == payload


def test_update_lock_dry_run_and_audit_warn_do_not_write(tmp_path: Path) -> None:
    upstream = tmp_path / "upstream"
    _init_repo(upstream)
    (upstream / "LICENSE").write_text("MIT\n", encoding="utf-8")
    _write_skill(upstream, "skills/demo", "---\nname: demo\ndescription: old\n---\nold\n")
    old = _commit(upstream, "old")
    _write_skill(upstream, "skills/demo", "---\nname: demo\ndescription: new\n---\nnew\n")
    _commit(upstream, "new")
    _git(upstream, "checkout", "--quiet", old)
    item = _locked("demo", upstream, "skills/demo", old)
    _git(upstream, "checkout", "--quiet", "main")

    dotfiles = tmp_path / "dotfiles"
    payload = _lock_body([item])
    _write_repo(dotfiles, payload)

    planned = lock_update.update_lock(
        dotfiles,
        dry_run=True,
        aliases={SOURCE: str(upstream)},
        audit=lambda path: (0, ""),
        today="2026-09-17",
    )
    assert planned.wrote is False
    assert planned.updated
    assert (dotfiles / "agents" / "skills.lock.yaml").read_text(encoding="utf-8") == payload

    with pytest.raises(lock_update.LockUpdateError, match="warnings"):
        lock_update.update_lock(
            dotfiles,
            aliases={SOURCE: str(upstream)},
            audit=lambda path: (1, "warn"),
            today="2026-09-17",
        )
    assert (dotfiles / "agents" / "skills.lock.yaml").read_text(encoding="utf-8") == payload

    accepted = lock_update.update_lock(
        dotfiles,
        accept_warn=True,
        aliases={SOURCE: str(upstream)},
        audit=lambda path: (1, "warn"),
        today="2026-09-17",
    )
    assert accepted.wrote is True


def test_update_lock_keeps_critically_blocked_skill(tmp_path: Path) -> None:
    upstream = tmp_path / "upstream"
    _init_repo(upstream)
    (upstream / "LICENSE").write_text("MIT\n", encoding="utf-8")
    _write_skill(upstream, "skills/ok", "---\nname: ok\ndescription: a\n---\na\n")
    _write_skill(upstream, "skills/bad", "---\nname: bad\ndescription: a\n---\na\n")
    old = _commit(upstream, "old")
    _write_skill(upstream, "skills/ok", "---\nname: ok\ndescription: b\n---\nb\n")
    _write_skill(upstream, "skills/bad", "---\nname: bad\ndescription: b\n---\nb\n")
    new = _commit(upstream, "new")

    _git(upstream, "checkout", "--quiet", old)
    ok = _locked("ok", upstream, "skills/ok", old)
    bad = _locked("bad", upstream, "skills/bad", old)
    _git(upstream, "checkout", "--quiet", "main")

    dotfiles = tmp_path / "dotfiles"
    _write_repo(dotfiles, _lock_body([ok, bad]))

    def audit(path: Path) -> tuple[int, str]:
        return (2, "block") if path.name == "bad" else (0, "")

    result = lock_update.update_lock(
        dotfiles,
        aliases={SOURCE: str(upstream)},
        audit=audit,
        today="2026-09-17",
    )
    assert result.wrote is True
    assert result.blocked == ("bad",)
    assert result.updated[0].skill_ids == ("ok",)
    loaded = {item.id: item for item in third_party.load_lock(dotfiles / "agents" / "skills.lock.yaml").skills}
    assert loaded["ok"].revision == new
    assert loaded["bad"].revision == old


def test_update_lock_refuses_missing_subdirectory(tmp_path: Path) -> None:
    upstream = tmp_path / "upstream"
    _init_repo(upstream)
    (upstream / "LICENSE").write_text("MIT\n", encoding="utf-8")
    _write_skill(upstream, "skills/demo", "---\nname: demo\ndescription: old\n---\nold\n")
    old = _commit(upstream, "old")
    (upstream / "skills" / "demo" / "SKILL.md").unlink()
    (upstream / "skills" / "demo").rmdir()
    _commit(upstream, "removed")
    _git(upstream, "checkout", "--quiet", old)
    item = _locked("demo", upstream, "skills/demo", old)
    _git(upstream, "checkout", "--quiet", "main")

    dotfiles = tmp_path / "dotfiles"
    payload = _lock_body([item])
    _write_repo(dotfiles, payload)
    with pytest.raises(lock_update.LockUpdateError, match="subdirectory missing"):
        lock_update.update_lock(
            dotfiles,
            aliases={SOURCE: str(upstream)},
            audit=lambda path: (0, ""),
            today="2026-09-17",
        )
    assert (dotfiles / "agents" / "skills.lock.yaml").read_text(encoding="utf-8") == payload
