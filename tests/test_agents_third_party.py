"""`third_party`: locked revision acquisition, sparse materialization, and caching."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "agents"))

import third_party  # noqa: E402

EVIDENCE = "https://github.com/example/demo/commit/0"


def _git(path: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(path), *args], text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout or f"git failed: {args}")
    return proc.stdout.strip()


def _upstream(tmp_path: Path) -> Path:
    """A local stand-in remote: two lockable skills, a license, and unrelated bulk."""
    checkout = tmp_path / "checkout"
    for skill_id in ("alpha", "beta"):
        skill = checkout / "skills" / skill_id
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"# {skill_id}\n", encoding="utf-8")
    (checkout / "LICENSE").write_text("MIT\n", encoding="utf-8")
    bulk = checkout / "unrelated"
    bulk.mkdir()
    (bulk / "big.bin").write_bytes(b"x" * 4096)
    subprocess.run(
        ["git", "init", "--quiet", "-b", "main", str(checkout)],
        check=True, capture_output=True, text=True,
    )
    _git(checkout, "config", "user.email", "dev@example.com")
    _git(checkout, "config", "user.name", "dev")
    _git(checkout, "add", "-A")
    _git(checkout, "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "init")
    return checkout


def _locked(checkout: Path, revision: str, skill_id: str) -> third_party.LockedSkill:
    return third_party.LockedSkill(
        skill_id,
        str(checkout),
        revision,
        f"skills/{skill_id}",
        third_party.tree_hash(checkout / "skills" / skill_id),
        third_party.LicenseLock(
            "MIT", "LICENSE",
            hashlib.sha256((checkout / "LICENSE").read_bytes()).hexdigest(),
        ),
        third_party.AuditLock("approved", "2026-09-01", "test-tool", EVIDENCE),
    )


def _lock(checkout: Path, *skill_ids: str) -> third_party.ThirdPartyLock:
    revision = _git(checkout, "rev-parse", "HEAD")
    items = tuple(_locked(checkout, revision, skill_id) for skill_id in skill_ids)
    return third_party.ThirdPartyLock(1, "third-party-skills-lock", items, "d" * 64)


def test_acquire_all_fetches_a_shared_revision_once(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def counting_run(*args, **kwargs):
        calls.append(args[0])
        return subprocess.run(*args, **kwargs)

    lock = _lock(_upstream(tmp_path), "alpha", "beta")
    staged = third_party.acquire_all(
        lock, tmp_path / "staged", run=counting_run, cache=tmp_path / "cache"
    )

    assert sorted(path.name for path in staged.iterdir()) == ["alpha", "beta"]
    assert len([argv for argv in calls if "fetch" in argv]) == 1
    assert len(list((tmp_path / "cache").iterdir())) == 1


def test_acquire_all_stages_only_the_locked_paths(tmp_path: Path) -> None:
    lock = _lock(_upstream(tmp_path), "alpha")
    cache = tmp_path / "cache"
    third_party.acquire_all(lock, tmp_path / "staged", cache=cache)

    checkout = next(iter(cache.iterdir()))
    assert (checkout / "skills" / "alpha" / "SKILL.md").is_file()
    assert (checkout / "LICENSE").is_file()
    assert not (checkout / "unrelated").exists()
    assert not (checkout / "skills" / "beta").exists()


def test_acquire_all_serves_a_warm_cache_without_the_remote(tmp_path: Path) -> None:
    checkout = _upstream(tmp_path)
    lock = _lock(checkout, "alpha", "beta")
    cache = tmp_path / "cache"
    third_party.acquire_all(lock, tmp_path / "first", cache=cache)

    shutil.rmtree(checkout)
    second = third_party.acquire_all(lock, tmp_path / "second", cache=cache)

    assert sorted(path.name for path in second.iterdir()) == ["alpha", "beta"]
    assert (second / "beta" / "SKILL.md").read_text(encoding="utf-8") == "# beta\n"


def test_acquire_all_refuses_a_tampered_cache(tmp_path: Path) -> None:
    checkout = _upstream(tmp_path)
    lock = _lock(checkout, "alpha")
    cache = tmp_path / "cache"
    third_party.acquire_all(lock, tmp_path / "first", cache=cache)

    entry = next(iter(cache.iterdir()))
    (entry / "skills" / "alpha" / "SKILL.md").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(third_party.ThirdPartyLockError, match="content hash"):
        third_party.acquire_all(lock, tmp_path / "second", cache=cache)


def test_git_timeout_is_reported_as_a_lock_error(tmp_path: Path) -> None:
    def timing_out(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs.get("timeout", 0))

    with pytest.raises(third_party.ThirdPartyLockError, match="timed out after"):
        third_party._git(["git", "fetch", "origin"], cwd=tmp_path, run=timing_out)
