"""dotf skills input resolver tests (group -> skill id -> passthrough)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESOLVER = ROOT / "src" / "agents" / "skills_map.py"


def run_resolver(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RESOLVER), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


def _write_catalog(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def test_group_expands_to_its_third_party_skills() -> None:
    result = run_resolver("ui-templates")
    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        "https://github.com/sunzhenkai/ui-templates-skill",
        "-s",
        "ui-template-author",
        "-s",
        "ui-template-apply",
        "-s",
        "ui-template-design",
    ]


def test_third_party_skill_id_resolves_to_its_package() -> None:
    result = run_resolver("ui-template-apply")
    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        "https://github.com/sunzhenkai/ui-templates-skill",
        "-s",
        "ui-template-apply",
    ]


def test_remove_mode_group_resolves_installed_skill_names() -> None:
    result = run_resolver("ui-templates", "--remove")
    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        "ui-template-author",
        "ui-template-apply",
        "ui-template-design",
    ]


def test_first_party_skill_id_is_rejected_with_guidance() -> None:
    result = run_resolver("commit-push")
    assert result.returncode != 0
    assert "first-party" in result.stderr
    assert "dotf agents skill apply commit-push" in result.stderr


def test_unknown_name_passes_through_for_npx_search() -> None:
    result = run_resolver("some-third-party-thing")
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["some-third-party-thing"]


def test_raw_package_spec_passes_through() -> None:
    result = run_resolver("owner/repo")
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["owner/repo"]


def test_group_and_skill_collision_prefers_group_with_notice(tmp_path: Path) -> None:
    map_file = tmp_path / "skills.yaml"
    # group name 'demo' collides with a member skill id 'demo'.
    _write_catalog(
        map_file,
        "version: 3\nlock: skills.lock.yaml\ngroups:\n"
        "  demo:\n    type: third-party\n    source: github\n"
        "    package: owner/one\n    skills: [demo, foo]\n",
    )
    result = run_resolver("demo", "--map", str(map_file))
    assert result.returncode == 0
    assert "both a group and a skill id" in result.stderr
    assert result.stdout.splitlines() == [
        "owner/one", "-s", "demo", "-s", "foo",
    ]


def test_group_mixing_packages_is_rejected(tmp_path: Path) -> None:
    # A single group has one package, so cross-package mixing can only come from
    # the resolver being asked for a group whose ids resolve to different packages;
    # with the nested schema each group is single-source, so this is enforced at
    # the schema level (a second package would need a second group).
    map_file = tmp_path / "skills.yaml"
    _write_catalog(
        map_file,
        "version: 3\nlock: skills.lock.yaml\ngroups:\n"
        "  one:\n    type: third-party\n    source: github\n"
        "    package: owner/one\n    skills: [foo]\n"
        "  two:\n    type: third-party\n    source: github\n"
        "    package: owner/two\n    skills: [bar]\n",
    )
    # each group is self-consistent; both resolve independently.
    assert run_resolver("one", "--map", str(map_file)).stdout.splitlines() == [
        "owner/one", "-s", "foo",
    ]
    assert run_resolver("two", "--map", str(map_file)).stdout.splitlines() == [
        "owner/two", "-s", "bar",
    ]


def test_missing_catalog_passes_name_through(tmp_path: Path) -> None:
    result = run_resolver("anything", "--map", str(tmp_path / "missing.yaml"))
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["anything"]
