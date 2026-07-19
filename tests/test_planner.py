"""planner：确定性、依赖、环、未知引用、OS 过滤。"""

from __future__ import annotations

from pathlib import Path

import planner
import yaml


def _reg(*items: dict) -> list[dict]:
    return list(items)


def _profiles(**kwargs) -> dict:
    return {"version": 1, "default": "full", "profiles": kwargs}


def test_deterministic_same_input() -> None:
    reg = _reg(
        {"name": "c", "install": True, "doctor": True},
        {"name": "a", "install": True, "doctor": True, "depends_on": ["b"]},
        {"name": "b", "install": True, "doctor": True, "depends_on": ["c"]},
    )
    p1 = planner.build_plan(
        os_id="linux",
        modules_explicit=["a"],
        actions=["install"],
        registry=reg,
        profiles_data=_profiles(),
    )
    p2 = planner.build_plan(
        os_id="linux",
        modules_explicit=["a"],
        actions=["install"],
        registry=reg,
        profiles_data=_profiles(),
    )
    assert p1.ok and p2.ok
    assert [(a.module, a.action) for a in p1.actions] == [
        (a.module, a.action) for a in p2.actions
    ]
    assert [a.module for a in p1.actions] == ["c", "b", "a"]


def test_recursive_depends_order() -> None:
    reg = _reg(
        {"name": "a", "install": True, "doctor": True, "depends_on": ["b"]},
        {"name": "b", "install": True, "doctor": True, "depends_on": ["c"]},
        {"name": "c", "install": True, "doctor": True},
    )
    plan = planner.build_plan(
        os_id="ubuntu",
        modules_explicit=["a"],
        actions=["install"],
        registry=reg,
        profiles_data=_profiles(),
    )
    assert plan.ok, plan.errors
    assert [a.module for a in plan.actions] == ["c", "b", "a"]


def test_dependency_cycle_fails() -> None:
    reg = _reg(
        {"name": "a", "install": True, "doctor": True, "depends_on": ["b"]},
        {"name": "b", "install": True, "doctor": True, "depends_on": ["a"]},
    )
    plan = planner.build_plan(
        os_id="ubuntu",
        modules_explicit=["a"],
        actions=["install"],
        registry=reg,
        profiles_data=_profiles(),
    )
    assert not plan.ok
    assert any("环" in e for e in plan.errors)


def test_unknown_module_fails() -> None:
    plan = planner.build_plan(
        os_id="ubuntu",
        modules_explicit=["nope"],
        actions=["install"],
        registry=_reg({"name": "a", "install": True, "doctor": True}),
        profiles_data=_profiles(),
    )
    assert not plan.ok
    assert any("未知模块" in e for e in plan.errors)


def test_unknown_dependency_fails() -> None:
    reg = _reg(
        {"name": "a", "install": True, "doctor": True, "depends_on": ["ghost"]},
    )
    plan = planner.build_plan(
        os_id="ubuntu",
        modules_explicit=["a"],
        actions=["install"],
        registry=reg,
        profiles_data=_profiles(),
    )
    assert not plan.ok
    assert any("ghost" in e for e in plan.errors)


def test_os_filter_all() -> None:
    reg = _reg(
        {"name": "lin", "config": {"source": "a", "target": "~/.a"}, "doctor": True, "os": ["linux"]},
        {"name": "mac", "config": {"source": "b", "target": "~/.b"}, "doctor": True, "os": ["darwin"]},
        {"name": "both", "config": {"source": "c", "target": "~/.c"}, "doctor": True},
    )
    plan = planner.build_plan(
        os_id="linux",
        actions=["config"],
        select_all=True,
        registry=reg,
        profiles_data=_profiles(),
    )
    assert plan.ok, plan.errors
    names = {a.module for a in plan.actions}
    assert names == {"lin", "both"}


def test_explicit_os_mismatch_fails() -> None:
    reg = _reg(
        {"name": "mac", "config": {"source": "b", "target": "~/.b"}, "doctor": True, "os": ["darwin"]},
    )
    plan = planner.build_plan(
        os_id="linux",
        modules_explicit=["mac"],
        actions=["config"],
        registry=reg,
        profiles_data=_profiles(),
    )
    assert not plan.ok
    assert any("不适用于" in e for e in plan.errors)


def test_icd_action_order() -> None:
    reg = _reg(
        {
            "name": "x",
            "install": True,
            "config": {"source": "s", "target": "~/.x"},
            "doctor": True,
        }
    )
    plan = planner.build_plan(
        os_id="linux",
        modules_explicit=["x"],
        actions=["install", "config", "doctor"],
        registry=reg,
        profiles_data=_profiles(),
    )
    assert plan.ok
    assert [a.action for a in plan.actions] == ["install", "config", "doctor"]


def test_missing_capability_fails() -> None:
    reg = _reg(
        {"name": "nvim", "config": {"source": "s", "target": "~/.c"}, "doctor": True},
    )
    plan = planner.build_plan(
        os_id="linux",
        modules_explicit=["nvim"],
        actions=["install"],
        registry=reg,
        profiles_data=_profiles(),
    )
    assert not plan.ok
    assert any("无 install 能力" in e for e in plan.errors)


def test_profile_includes_merge() -> None:
    reg = _reg(
        {"name": "a", "install": True, "doctor": True},
        {"name": "b", "install": True, "doctor": True},
        {"name": "c", "install": True, "doctor": True},
    )
    profiles = _profiles(
        minimal={"modules": ["a"], "includes": []},
        remote={"includes": ["minimal"], "modules": ["b"]},
    )
    plan = planner.build_plan(
        os_id="linux",
        profile="remote",
        modules_explicit=["c"],
        actions=["install"],
        registry=reg,
        profiles_data=profiles,
    )
    assert plan.ok, plan.errors
    assert [a.module for a in plan.actions] == ["a", "b", "c"]


def test_format_text_stable(tmp_home: Path) -> None:
    reg = _reg({"name": "a", "install": True, "doctor": True})
    plan = planner.build_plan(
        os_id="linux",
        modules_explicit=["a"],
        actions=["install"],
        registry=reg,
        profiles_data=_profiles(),
    )
    t1 = planner.format_plan_text(plan)
    t2 = planner.format_plan_text(plan)
    assert t1 == t2
    assert "install" in t1 and "a" in t1


def test_format_text_merges_actions_per_module() -> None:
    plan = planner.Plan(
        os_id="ubuntu",
        profile="full",
        actions=[
            planner.PlanAction("git", "install", "all", index=1),
            planner.PlanAction("git", "config", "all", index=2),
            planner.PlanAction("delta", "install", "all", index=3),
        ],
    )
    text = planner.format_plan_text(plan)
    assert "共 3 个动作" in text
    data_lines = [
        line
        for line in text.splitlines()
        if line and not line.startswith(("-", "执行", "共", "#"))
    ]
    assert len(data_lines) == 2
    assert "install,config" in data_lines[0] and "git" in data_lines[0]
    assert data_lines[1].split()[1:][:2] == ["install", "delta"]


def test_disabled_skipped_in_select_all_and_profile() -> None:
    reg = _reg(
        {"name": "a", "install": True, "doctor": True},
        {"name": "qoder", "install": True, "doctor": True, "enabled": False},
        {"name": "codebuddy-code", "install": True, "doctor": True, "enabled": False},
    )
    plan_all = planner.build_plan(
        os_id="linux",
        select_all=True,
        actions=["install"],
        registry=reg,
        profiles_data=_profiles(),
    )
    assert plan_all.ok, plan_all.errors
    names_all = {a.module for a in plan_all.actions}
    assert names_all == {"a"}
    assert "qoder" not in names_all
    assert "codebuddy-code" not in names_all

    plan_prof = planner.build_plan(
        os_id="linux",
        profile="with_disabled",
        actions=["install"],
        registry=reg,
        profiles_data=_profiles(
            with_disabled={"modules": ["a", "qoder"], "includes": []},
        ),
    )
    assert plan_prof.ok, plan_prof.errors
    assert [a.module for a in plan_prof.actions] == ["a"]


def test_disabled_still_runs_when_explicit() -> None:
    reg = _reg(
        {"name": "qoder", "install": True, "doctor": True, "enabled": False},
    )
    plan = planner.build_plan(
        os_id="linux",
        modules_explicit=["qoder"],
        actions=["install"],
        registry=reg,
        profiles_data=_profiles(),
    )
    assert plan.ok, plan.errors
    assert [a.module for a in plan.actions] == ["qoder"]
