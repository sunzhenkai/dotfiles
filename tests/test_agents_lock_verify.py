"""`lock_verify`: third-party lock change report and installed-copy verification."""

from __future__ import annotations

import contextlib
import hashlib
import io
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "agents"))

import defaults  # noqa: E402
import lock_update  # noqa: E402
import lock_verify  # noqa: E402
import third_party  # noqa: E402

SOURCE = "https://github.com/example/demo"


def _git(path: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(path), *args], text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout or f"git failed: {args}")
    return proc.stdout.strip()


def _git_init(path: Path) -> None:
    subprocess.run(
        ["git", "init", "--quiet", "-b", "main", str(path)],
        check=True, capture_output=True, text=True,
    )
    _git(path, "config", "user.email", "dev@example.com")
    _git(path, "config", "user.name", "dev")


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True)
    _git_init(path)


def _commit(path: Path, message: str) -> str:
    _git(path, "add", "-A")
    _git(path, "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", message)
    return _git(path, "rev-parse", "HEAD")


def _upstream(tmp_path: Path) -> Path:
    """Source tree with one skill: shipped extras, and a policy-excluded directory."""
    checkout = tmp_path / "checkout"
    skill = checkout / "skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nid: demo\nname: demo\ndescription: demo skill\n---\n\n# Demo\n\nbody\n",
        encoding="utf-8",
    )
    (skill / "references").mkdir()
    (skill / "references" / "notes.md").write_text("notes\n", encoding="utf-8")
    # Undeclared in runtime.yaml, so include_unlisted ships it.
    (skill / "tests").mkdir()
    (skill / "tests" / "contract.py").write_text("pass\n", encoding="utf-8")
    # policy.excluded -> stripped; its absence is never a finding.
    (skill / "patches").mkdir()
    (skill / "patches" / "p.md").write_text("history\n", encoding="utf-8")
    (checkout / "LICENSE").write_text("MIT\n", encoding="utf-8")
    _git_init(checkout)
    _commit(checkout, "init")
    return checkout


def _locked(checkout: Path, revision: str, skill_id: str = "demo") -> third_party.LockedSkill:
    return third_party.LockedSkill(
        skill_id,
        SOURCE,
        revision,
        "skill",
        third_party.tree_hash(checkout / "skill"),
        third_party.LicenseLock(
            "MIT", "LICENSE",
            hashlib.sha256((checkout / "LICENSE").read_bytes()).hexdigest(),
        ),
        third_party.AuditLock(
            "approved", "2026-09-01", "test-tool", f"{SOURCE}/commit/{revision}"
        ),
    )


def _make_repo(
    tmp_path: Path,
    items: list[third_party.LockedSkill],
    *,
    optional: bool = False,
) -> Path:
    repo = tmp_path / "repo"
    agents = repo / "agents"
    (agents / "skills").mkdir(parents=True)
    shutil.copy2(ROOT / "agents" / "runtime.yaml", agents / "runtime.yaml")
    member = "      - id: demo\n        optional: true\n" if optional else "      - demo\n"
    (agents / "skills.yaml").write_text(
        "version: 3\nlock: skills.lock.yaml\ngroups:\n"
        "  demo:\n    type: third-party\n    source: github\n"
        f"    package: {SOURCE}\n    skills:\n{member}",
        encoding="utf-8",
    )
    (agents / "skills.lock.yaml").write_text(lock_update.dump_lock(items), encoding="utf-8")
    return repo


def _stub_acquire(checkout: Path, revision: str):
    def acquire(lock, destination):
        """Stand in for `acquire_all`: fetch, verify, then stage."""
        destination.mkdir(mode=0o700, parents=True, exist_ok=True)
        skills = destination / "skills"
        skills.mkdir(mode=0o700, exist_ok=True)
        for item in lock.skills:
            verified = third_party.verify_checkout(item, checkout, revision)
            target = skills / item.id
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(verified, target)
        return skills

    return acquire


def _run_main(*args: str) -> tuple[int, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        code = lock_verify.main(list(args))
    return code, buffer.getvalue()


@pytest.fixture
def env(tmp_path: Path, tmp_home: Path, monkeypatch: pytest.MonkeyPatch):
    checkout = _upstream(tmp_path)
    revision = _git(checkout, "rev-parse", "HEAD")
    item = _locked(checkout, revision)
    repo = _make_repo(tmp_path, [item])
    stub = _stub_acquire(checkout, revision)
    monkeypatch.setattr(lock_verify, "acquire_all", stub)
    monkeypatch.setattr(defaults, "acquire_all", stub)
    destinations = tuple(tmp_home / name / "skills" for name in (".agents", ".kiro", ".claude"))
    assert defaults.install_defaults(repo, dest_roots=destinations) == 0

    class Env:
        def __init__(self) -> None:
            self.repo = repo
            self.home = tmp_home
            self.checkout = checkout
            self.revision = revision
            self.item = item
            self.destinations = destinations

    return Env()


def test_verify_clean_install_passes_and_ignores_stripped_dirs(env) -> None:
    code, output = _run_main("verify", "--root", str(env.repo), "--ids", "demo")
    assert code == 0, output
    assert "tree_hash == content_hash: 1/1" in output
    assert "failures=0" in output
    assert "patches" not in output
    assert (env.destinations[0] / "demo" / "tests" / "contract.py").is_file()


def test_verify_flags_unowned_stale_file(env) -> None:
    stale = env.destinations[0] / "demo" / "experience"
    stale.mkdir(parents=True)
    (stale / "old.md").write_text("leftover\n", encoding="utf-8")
    code, output = _run_main("verify", "--root", str(env.repo), "--ids", "demo")
    assert code == 1
    assert "unowned demo/experience/old.md" in output


def test_verify_flags_undeployed_skill_file(env) -> None:
    shutil.rmtree(env.destinations[0] / "demo" / "references")
    code, output = _run_main("verify", "--root", str(env.repo), "--ids", "demo")
    assert code == 1
    assert "missing demo/references/notes.md" in output


def test_verify_ignores_run_residue(env) -> None:
    residue = env.destinations[0] / "demo" / "tests" / "__pycache__"
    residue.mkdir(parents=True)
    (residue / "contract.cpython-313.pyc").write_bytes(b"\x00")
    code, output = _run_main("verify", "--root", str(env.repo), "--ids", "demo")
    assert code == 0, output


def test_verify_optional_entry_is_reported_not_installed(tmp_path: Path, tmp_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    checkout = _upstream(tmp_path)
    revision = _git(checkout, "rev-parse", "HEAD")
    item = _locked(checkout, revision)
    repo = _make_repo(tmp_path, [item], optional=True)
    monkeypatch.setattr(lock_verify, "acquire_all", _stub_acquire(checkout, revision))
    code, output = _run_main("verify", "--root", str(repo), "--ids", "demo")
    assert code == 0, output
    assert "NOT-INSTALLED demo" in output


def test_verify_rejects_content_hash_mismatch(tmp_path: Path, tmp_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    checkout = _upstream(tmp_path)
    revision = _git(checkout, "rev-parse", "HEAD")
    stale_item = third_party.LockedSkill(
        "demo", SOURCE, revision, "skill",
        "a" * 64,  # a hash the upstream tree will not produce
        _locked(checkout, revision).license,
        _locked(checkout, revision).audit,
    )
    repo = _make_repo(tmp_path, [stale_item])
    monkeypatch.setattr(lock_verify, "acquire_all", _stub_acquire(checkout, revision))
    code, output = _run_main("verify", "--root", str(repo), "--ids", "demo")
    assert code == 1
    assert "content hash does not match lock" in output


def test_diff_locks_separates_content_from_revision_only() -> None:
    def lock_of(revision: str, content: str) -> third_party.ThirdPartyLock:
        return lock_update.load_lock_bytes(
            lock_update.dump_lock([
                third_party.LockedSkill(
                    "demo", SOURCE, revision, "skill", content,
                    third_party.LicenseLock("MIT", "LICENSE", "c" * 64),
                    third_party.AuditLock("approved", "2026-09-01", "tool", f"{SOURCE}/commit/x"),
                )
            ])
        )

    same_content = lock_verify.diff_locks(lock_of("a" * 40, "b" * 64), lock_of("c" * 40, "b" * 64))
    assert same_content.revision_only == ("demo",)
    assert same_content.content == ()
    assert same_content.verification_targets == ()

    moved = lock_verify.diff_locks(lock_of("a" * 40, "b" * 64), lock_of("c" * 40, "e" * 64))
    assert moved.content == ("demo",)
    assert moved.verification_targets == ("demo",)


def test_diff_locks_reports_added_and_removed_ids() -> None:
    def lock_of(skill_id: str) -> third_party.ThirdPartyLock:
        return lock_update.load_lock_bytes(
            lock_update.dump_lock([
                third_party.LockedSkill(
                    skill_id, SOURCE, "a" * 40, f"skills/{skill_id}", "b" * 64,
                    third_party.LicenseLock("MIT", "LICENSE", "c" * 64),
                    third_party.AuditLock("approved", "2026-09-01", "tool", f"{SOURCE}/commit/x"),
                )
            ])
        )

    report = lock_verify.diff_locks(lock_of("delivery-loop"), lock_of("task-delivery"))
    assert report.added == ("task-delivery",)
    assert report.removed == ("delivery-loop",)
    assert report.verification_targets == ("task-delivery",)


def test_changed_mode_runs_against_a_git_repo(env, tmp_path: Path) -> None:
    repo = env.repo
    _git_init(repo)
    _commit(repo, "base")
    code, output = _run_main("changed", "--root", str(repo))
    assert code == 0, output
    assert "changed_content=0 changed_revision_only=0 added=0 removed=0" in output
