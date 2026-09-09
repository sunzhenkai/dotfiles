"""dotf skills short-name mapping tests."""

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


def test_taste_skill_maps_to_audited_source_repo() -> None:
    result = run_resolver("taste-skill")
    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        "https://github.com/Leonxlnx/taste-skill",
        "-s",
        "design-taste-frontend",
    ]


def test_ui_template_maps_to_multiple_skills() -> None:
    result = run_resolver("ui-template")
    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        "sunzhenkai/ui-templates-skill",
        "-s",
        "ui-template-author",
        "-s",
        "ui-template-apply",
        "-s",
        "ui-template-design",
    ]


def test_remove_mode_resolves_multiple_installed_skill_names() -> None:
    result = run_resolver("ui-template", "--remove")
    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        "ui-template-author",
        "ui-template-apply",
        "ui-template-design",
    ]


def test_multiple_skill_selectors_reject_skill_alias(tmp_path: Path) -> None:
    map_file = tmp_path / "skills-map.yaml"
    map_file.write_text(
        (
            "version: 1\n"
            "skills:\n"
            "  demo:\n"
            "    package: owner/repo\n"
            "    skill: demo\n"
            "    skills:\n"
            "      - demo\n"
        ),
        encoding="utf-8",
    )
    result = run_resolver("demo", "--map", str(map_file))
    assert result.returncode != 0
    assert "cannot use both" in result.stderr


def test_unmapped_name_passes_through() -> None:
    result = run_resolver("frontend-design")
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["frontend-design"]


def test_remove_mode_resolves_installed_skill_name() -> None:
    result = run_resolver("taste-skill", "--remove")
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["design-taste-frontend"]


def test_remove_mode_unmapped_name_passes_through() -> None:
    result = run_resolver("frontend-design", "--remove")
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["frontend-design"]


def test_remove_mode_without_skill_selector_passes_through(tmp_path: Path) -> None:
    map_file = tmp_path / "skills-map.yaml"
    map_file.write_text(
        "version: 1\nskills:\n  demo: owner/repo\n",
        encoding="utf-8",
    )
    result = run_resolver("demo", "--remove", "--map", str(map_file))
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["demo"]


def test_string_entry_maps_to_package(tmp_path: Path) -> None:
    map_file = tmp_path / "skills-map.yaml"
    map_file.write_text(
        "version: 1\nskills:\n  demo: owner/repo\n",
        encoding="utf-8",
    )
    result = run_resolver("demo", "--map", str(map_file))
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["owner/repo"]


def test_invalid_entry_fails_loudly(tmp_path: Path) -> None:
    map_file = tmp_path / "skills-map.yaml"
    map_file.write_text(
        "version: 1\nskills:\n  demo: {package: ''}\n",
        encoding="utf-8",
    )
    result = run_resolver("demo", "--map", str(map_file))
    assert result.returncode != 0
    assert "error: skills map" in result.stderr


def test_missing_map_file_passes_through(tmp_path: Path) -> None:
    result = run_resolver("demo", "--map", str(tmp_path / "missing.yaml"))
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["demo"]
