"""模块别名：CLI 短名解析到正规模块名，且不得与模块名或其它别名冲突。"""

from __future__ import annotations

from pathlib import Path

from dotf_core import planner
from dotf_core import registry as modules


def _validate(items: list[dict]) -> list[str]:
    return modules.validate_registry(
        items,
        profiles_data={"profiles": {}},
        strict_handlers=False,
        handlers_dir=Path("/nonexistent"),
    )


def _binary(name: str, **extra) -> dict:
    return {"name": name, "kind": "binary", "install": True, "doctor": True, **extra}


def test_find_module_resolves_alias_to_canonical_entry() -> None:
    items = [_binary("antigravity", bin="agy", aliases=["agy"])]
    found = modules.find_module(items, "agy")
    assert found is not None and found["name"] == "antigravity"


def test_canonical_name_wins_over_alias() -> None:
    items = [_binary("agy", aliases=["other"]), _binary("antigravity", aliases=["agy"])]
    found = modules.find_module(items, "agy")
    assert found is not None and found["name"] == "agy"


def test_alias_must_not_shadow_a_module_name() -> None:
    errors = _validate([_binary("agy"), _binary("antigravity", aliases=["agy"])])
    assert any("与模块名冲突" in error for error in errors)


def test_alias_must_be_unique_across_modules() -> None:
    errors = _validate([_binary("a", aliases=["x"]), _binary("b", aliases=["x"])])
    assert any("已被模块 a 使用" in error for error in errors)


def test_alias_must_not_repeat_module_name_or_itself() -> None:
    errors = _validate([_binary("a", aliases=["a"])])
    assert any("不得与模块名同名" in error for error in errors)
    dup = _validate([_binary("a", aliases=["x", "x"])])
    assert any("重复" in error for error in dup)


def test_alias_must_be_non_empty_strings() -> None:
    errors = _validate([_binary("a", aliases=[""]), _binary("b", aliases="x")])
    assert any("a: aliases 必须为非空字符串列表" in error for error in errors)
    assert any("b: aliases 必须为非空字符串列表" in error for error in errors)


def test_planner_resolves_alias_into_canonical_module() -> None:
    items = [
        _binary("antigravity", aliases=["agy"]),
        {"name": "nvim", "kind": "config", "doctor": True},
    ]
    plan = planner.build_plan(
        os_id="arch",
        modules_explicit=["agy"],
        actions=["install"],
        registry=items,
        profiles_data={"version": 1, "default": None, "profiles": {}},
    )
    assert plan.ok, plan.errors
    assert [action.module for action in plan.actions] == ["antigravity"]
    assert plan.module_reasons["antigravity"] == "explicit"


def test_real_registry_exposes_agy_alias() -> None:
    registry = modules.load_registry()
    found = modules.find_module(registry, "agy")
    assert found is not None and found["name"] == "antigravity"
    assert "antigravity" not in modules.module_aliases(found)
