"""skill.apply/remove must reconcile every source that can carry the artifact.

Regression: apply wrote the overlay and then only synced first-party skills, so
`dotf agents skill apply codebase-design` (a locked third-party skill) reported
success while installing nothing, and an unrelated conflict surfaced as the
opaque "skill sync failed after overlay write".
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "agents"))

import desired_ops  # noqa: E402
from dotf_core.overlays import catalog_from_repo, load_overlays  # noqa: E402

REVISION = "1" * 40
THIRD_PARTY = "external-skill"


def _repo(tmp_path: Path) -> Path:
    """A repo with one first-party skill and one locked third-party skill."""
    repo = tmp_path / "repo"
    first = repo / "agents" / "skills" / "demo"
    first.mkdir(parents=True)
    (first / "SKILL.md").write_text(
        "---\nname: demo\ndescription: demo skill\n---\nbody\n", encoding="utf-8"
    )
    env = repo / "agents" / "env"
    (env / "profiles").mkdir(parents=True)
    (env / "manifest.yaml").write_text(
        "version: 1\ntools: [cursor]\ndefault_profile: research\n", encoding="utf-8"
    )
    (env / "profiles" / "research.yaml").write_text(
        "version: 1\nid: research\n", encoding="utf-8"
    )
    (repo / "agents" / "runtime.yaml").write_text(
        "version: 1\nskills:\n  files: [SKILL.md]\n"
        "  sidecars: [references, scripts]\n"
        "  excluded: [patches, evals, experience, evolutions, authoring]\n",
        encoding="utf-8",
    )
    (repo / "agents" / "skills.yaml").write_text(
        "version: 3\nlock: skills.lock.yaml\ngroups:\n"
        "  dotfiles:\n    type: first-party\n    skills:\n      - demo\n"
        "  test:\n    type: third-party\n    source: github\n"
        "    package: https://github.com/example/demo\n"
        f"    skills:\n      - {THIRD_PARTY}\n",
        encoding="utf-8",
    )
    (repo / "agents" / "skills.lock.yaml").write_text(
        "schema_version: 1\nkind: third-party-skills-lock\nskills:\n"
        f"  - id: {THIRD_PARTY}\n    source: https://github.com/example/demo\n"
        f"    revision: '{REVISION}'\n    subdirectory: skill\n    content_hash: {'a' * 64}\n"
        f"    license: {{spdx: MIT, file: LICENSE, hash: {'b' * 64}}}\n"
        "    audit: {status: approved, date: '2026-09-04', tool: test-review-v1,"
        " evidence: https://example.com/audit/demo}\n",
        encoding="utf-8",
    )
    return repo


def _enabled_skills(repo: Path, home: Path) -> list[str]:
    overlays = load_overlays(repo_root=repo, catalog=catalog_from_repo(repo), home=home)
    return sorted(overlays.agents.get("enabled_skills") or [])


def test_third_party_apply_installs_the_locked_skill(
    tmp_path: Path, tmp_home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    repo = _repo(tmp_path)
    calls: list[tuple[Path, str]] = []

    def fake_install_defaults(root, *, dry_run=False, on_conflict=None, **kwargs):
        calls.append((root, on_conflict))
        return 0

    import defaults

    monkeypatch.setattr(defaults, "install_defaults", fake_install_defaults)

    rc = desired_ops.run_desired_op("skill.apply", f"skill:{THIRD_PARTY}", root=repo)

    assert rc == 0, capsys.readouterr()
    assert calls == [(repo, "block")]
    assert THIRD_PARTY in _enabled_skills(repo, tmp_home)


def test_first_party_apply_stays_offline(
    tmp_path: Path, tmp_home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """`acquire_all` fetches per lock entry, so a first-party apply must not call it."""
    repo = _repo(tmp_path)

    def fail_install_defaults(*args, **kwargs):
        raise AssertionError("first-party apply must not acquire locked third-party skills")

    import defaults

    monkeypatch.setattr(defaults, "install_defaults", fail_install_defaults)

    rc = desired_ops.run_desired_op("skill.apply", "skill:demo", root=repo)

    assert rc == 0, capsys.readouterr()
    assert (tmp_home / ".agents" / "skills" / "demo" / "SKILL.md").is_file()
    assert (tmp_home / ".claude" / "skills" / "demo" / "SKILL.md").is_file()


def test_conflict_failure_names_the_target_and_the_cause(
    tmp_path: Path, tmp_home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    repo = _repo(tmp_path)
    import defaults

    monkeypatch.setattr(defaults, "install_defaults", lambda *a, **k: 0)
    assert desired_ops.run_desired_op("skill.apply", "skill:demo", root=repo) == 0

    target = tmp_home / ".agents" / "skills" / "demo" / "SKILL.md"
    target.write_text("local edit\n", encoding="utf-8")
    capsys.readouterr()

    rc = desired_ops.run_desired_op("skill.apply", "skill:demo", root=repo)

    assert rc == 1
    emitted = [line for line in capsys.readouterr().out.splitlines() if line.startswith("RESULT\t")]
    reason = emitted[-1].split("\t")[6]
    # The failing layout, the target, and the cause — not a bare "sync failed".
    assert reason.startswith("skill sync failed: skills: ")
    assert "SKILL.md" in reason
    assert "owned target was modified locally" in reason
    assert target.read_text(encoding="utf-8") == "local edit\n"


def test_backup_policy_reaches_the_runtime_planner(
    tmp_path: Path, tmp_home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    repo = _repo(tmp_path)
    import defaults

    monkeypatch.setattr(defaults, "install_defaults", lambda *a, **k: 0)
    assert desired_ops.run_desired_op("skill.apply", "skill:demo", root=repo) == 0
    target = tmp_home / ".agents" / "skills" / "demo" / "SKILL.md"
    installed = target.read_bytes()
    target.write_text("local edit\n", encoding="utf-8")
    capsys.readouterr()

    rc = desired_ops.run_desired_op(
        "skill.apply", "skill:demo", root=repo, on_conflict="backup"
    )

    assert rc == 0, capsys.readouterr()
    assert target.read_bytes() == installed
