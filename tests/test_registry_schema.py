"""注册表 depends_on/group、profile schema 与校验。"""

from __future__ import annotations

from pathlib import Path

import modules
import yaml


def _write_registry(path: Path, modules_list: list) -> None:
    path.write_text(
        yaml.dump({"modules": modules_list}, allow_unicode=True),
        encoding="utf-8",
    )


def _write_profiles(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")


def test_real_registry_and_profiles_validate() -> None:
    errors = modules.validate_registry()
    assert errors == [], errors


def test_depends_on_and_group_api(tmp_path: Path) -> None:
    reg = tmp_path / "modules.yaml"
    _write_registry(
        reg,
        [
            {"name": "a", "install": True, "doctor": True, "group": "core"},
            {
                "name": "b",
                "install": True,
                "doctor": True,
                "depends_on": ["a"],
                "group": "tools",
            },
        ],
    )
    mods = modules.load_registry(reg)
    b = modules.find_module(mods, "b")
    assert b is not None
    assert modules.module_depends_on(b) == ["a"]
    assert modules.module_group(b) == "tools"


def test_unknown_dependency(tmp_path: Path) -> None:
    reg = tmp_path / "m.yaml"
    _write_registry(
        reg,
        [{"name": "a", "install": True, "doctor": True, "depends_on": ["missing"]}],
    )
    errors = modules.validate_registry(modules.load_registry(reg), profiles_data={"profiles": {}})
    assert any("未知模块 'missing'" in e for e in errors)


def test_duplicate_name(tmp_path: Path) -> None:
    reg = tmp_path / "m.yaml"
    _write_registry(
        reg,
        [
            {"name": "a", "install": True, "doctor": True},
            {"name": "a", "install": True, "doctor": True},
        ],
    )
    errors = modules.validate_registry(modules.load_registry(reg), profiles_data={"profiles": {}})
    assert any("重复模块名" in e for e in errors)


def test_bad_field_types(tmp_path: Path) -> None:
    reg = tmp_path / "m.yaml"
    _write_registry(
        reg,
        [{"name": "a", "install": "yes", "doctor": True, "depends_on": "b"}],
    )
    errors = modules.validate_registry(modules.load_registry(reg), profiles_data={"profiles": {}})
    assert any("install 必须为 bool" in e for e in errors)
    assert any("depends_on 必须为字符串列表" in e for e in errors)


def test_dependency_cycle_path(tmp_path: Path) -> None:
    reg = tmp_path / "m.yaml"
    _write_registry(
        reg,
        [
            {"name": "a", "install": True, "doctor": True, "depends_on": ["b"]},
            {"name": "b", "install": True, "doctor": True, "depends_on": ["a"]},
        ],
    )
    errors = modules.validate_registry(modules.load_registry(reg), profiles_data={"profiles": {}})
    cycle_errs = [e for e in errors if "依赖环" in e]
    assert cycle_errs
    assert "a" in cycle_errs[0] and "b" in cycle_errs[0]


def test_forbidden_executable_fields(tmp_path: Path) -> None:
    reg = tmp_path / "m.yaml"
    _write_registry(
        reg,
        [{"name": "a", "install": True, "doctor": True, "command": "echo hi"}],
    )
    errors = modules.validate_registry(modules.load_registry(reg), profiles_data={"profiles": {}})
    assert any("禁止可执行字段" in e for e in errors)


def test_profile_unknown_module(tmp_path: Path) -> None:
    reg = tmp_path / "m.yaml"
    prof = tmp_path / "p.yaml"
    _write_registry(reg, [{"name": "a", "install": True, "doctor": True}])
    _write_profiles(
        prof,
        {"default": "x", "profiles": {"x": {"modules": ["nope"], "includes": []}}},
    )
    errors = modules.validate_registry(
        modules.load_registry(reg),
        profiles_data=modules.load_profiles(prof),
    )
    assert any("未知模块 'nope'" in e for e in errors)


def test_profile_unknown_include(tmp_path: Path) -> None:
    reg = tmp_path / "m.yaml"
    prof = tmp_path / "p.yaml"
    _write_registry(reg, [{"name": "a", "install": True, "doctor": True}])
    _write_profiles(
        prof,
        {"profiles": {"x": {"modules": [], "includes": ["ghost"]}}},
    )
    errors = modules.validate_registry(
        modules.load_registry(reg),
        profiles_data=modules.load_profiles(prof),
    )
    assert any("未知 include 'ghost'" in e for e in errors)


def test_profile_include_cycle(tmp_path: Path) -> None:
    reg = tmp_path / "m.yaml"
    prof = tmp_path / "p.yaml"
    _write_registry(reg, [{"name": "a", "install": True, "doctor": True}])
    _write_profiles(
        prof,
        {
            "profiles": {
                "x": {"modules": [], "includes": ["y"]},
                "y": {"modules": [], "includes": ["x"]},
            }
        },
    )
    errors = modules.validate_registry(
        modules.load_registry(reg),
        profiles_data=modules.load_profiles(prof),
    )
    assert any("include 环" in e for e in errors)


def test_strict_handlers_missing_install(tmp_path: Path) -> None:
    reg = tmp_path / "m.yaml"
    hdir = tmp_path / "handlers"
    _write_registry(reg, [{"name": "a", "install": True, "doctor": True}])
    errors = modules.validate_registry(
        modules.load_registry(reg),
        profiles_data={"profiles": {}},
        strict_handlers=True,
        handlers_dir=hdir,
    )
    assert any("缺少处理器" in e and "install" in e for e in errors)


def test_migration_mode_skips_handler_errors(tmp_path: Path) -> None:
    reg = tmp_path / "m.yaml"
    hdir = tmp_path / "handlers"
    _write_registry(reg, [{"name": "a", "install": True, "doctor": True}])
    errors = modules.validate_registry(
        modules.load_registry(reg),
        profiles_data={"profiles": {}},
        strict_handlers=False,
        handlers_dir=hdir,
    )
    assert not any("缺少处理器" in e for e in errors)


def test_usage_profiles_cli(repo_root: Path) -> None:
    import subprocess

    out = subprocess.run(
        ["python3", str(repo_root / "scripts" / "modules.py"), "profiles", "usage"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert "minimal" in out
    assert "full" in out
