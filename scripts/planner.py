#!/usr/bin/env python3
"""统一执行计划：profile / 依赖展开 / 拓扑排序 / 动作生成。"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

# 与 modules.py 同目录
sys.path.insert(0, str(Path(__file__).resolve().parent))
import modules  # noqa: E402


ACTION_ORDER = ("install", "config", "doctor")

# agents -i 展开为独立单工具 install 动作（不污染 agents -c）
AGENTS_INSTALL_BUNDLE = ("claude", "cursor", "opencode", "codex", "kimi-code")


@dataclass
class PlanAction:
    module: str
    action: str
    reason: str
    index: int = 0


@dataclass
class Plan:
    os_id: str
    profile: str | None
    actions: list[PlanAction] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    module_reasons: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


class PlanError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init("; ".join(errors))


def expand_profile_modules(
    profile_name: str,
    profiles: dict[str, Any],
    *,
    _stack: list[str] | None = None,
) -> tuple[list[str], str]:
    """展开 includes，返回 (模块名列表按展开顺序, 原因标签)。"""
    stack = _stack or []
    if profile_name in stack:
        raise PlanError([f"profile include 环: {' -> '.join(stack + [profile_name])}"])
    if profile_name not in profiles:
        raise PlanError([f"未知 profile: {profile_name}"])

    pdata = profiles[profile_name] or {}
    out: list[str] = []
    seen: set[str] = set()
    for inc in pdata.get("includes") or []:
        part, _ = expand_profile_modules(inc, profiles, _stack=stack + [profile_name])
        for m in part:
            if m not in seen:
                seen.add(m)
                out.append(m)
    for m in pdata.get("modules") or []:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out, f"profile:{profile_name}"


def registry_order_map(mod_list: list[dict[str, Any]]) -> dict[str, int]:
    return {m["name"]: i for i, m in enumerate(mod_list) if m.get("name")}


def expand_depends(
    seeds: Iterable[str],
    by_name: dict[str, dict[str, Any]],
) -> tuple[set[str], dict[str, str], list[str]]:
    """递归展开 depends_on。返回 (模块集合, 原因, 错误)。"""
    errors: list[str] = []
    selected: set[str] = set()
    reasons: dict[str, str] = {}
    stack = list(seeds)

    while stack:
        name = stack.pop()
        if name in selected:
            continue
        mod = by_name.get(name)
        if mod is None:
            errors.append(f"未知模块: {name}")
            continue
        selected.add(name)
        for dep in modules.module_depends_on(mod):
            if dep not in by_name:
                errors.append(f"{name}: depends_on 引用未知模块 '{dep}'")
                continue
            if dep not in selected:
                reasons.setdefault(dep, f"depends:{name}")
                stack.append(dep)
    return selected, reasons, errors


def topo_sort(
    names: set[str],
    by_name: dict[str, dict[str, Any]],
    order_map: dict[str, int],
) -> tuple[list[str], list[str]]:
    """依赖优先，注册表顺序稳定打破平局。"""
    indeg: dict[str, int] = {n: 0 for n in names}
    graph: dict[str, list[str]] = {n: [] for n in names}
    for n in names:
        for dep in modules.module_depends_on(by_name[n]):
            if dep in names:
                graph[dep].append(n)
                indeg[n] += 1

    ready = sorted(
        [n for n, d in indeg.items() if d == 0],
        key=lambda x: order_map.get(x, 10**9),
    )
    result: list[str] = []
    while ready:
        n = ready.pop(0)
        result.append(n)
        for nxt in sorted(graph[n], key=lambda x: order_map.get(x, 10**9)):
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                ready.append(nxt)
                ready.sort(key=lambda x: order_map.get(x, 10**9))

    if len(result) != len(names):
        remaining = names - set(result)
        # 环检测复用 modules
        subgraph = {n: modules.module_depends_on(by_name[n]) for n in remaining}
        cycles = modules._find_cycles(subgraph)  # noqa: SLF001
        if cycles:
            return [], [f"模块依赖环: {' -> '.join(c)}" for c in cycles]
        return [], [f"无法完成拓扑排序，残留: {', '.join(sorted(remaining))}"]
    return result, []


def module_has_action(mod: dict[str, Any], action: str) -> bool:
    if action == "install":
        return modules.has_install(mod)
    if action == "config":
        return modules.has_config(mod)
    if action == "doctor":
        return modules.has_doctor(mod)
    return False


def build_plan(
    *,
    os_id: str | None = None,
    profile: str | None = None,
    modules_explicit: list[str] | None = None,
    actions: list[str] | None = None,
    select_all: bool = False,
    registry: list[dict[str, Any]] | None = None,
    profiles_data: dict[str, Any] | None = None,
) -> Plan:
    """生成不可变执行计划。"""
    mod_list = registry if registry is not None else modules.load_registry()
    profiles_data = profiles_data if profiles_data is not None else modules.load_profiles()
    profiles = profiles_data.get("profiles") or {}

    resolved_os = os_id or modules.detect_os()
    want_actions = list(actions or ["install", "config"])
    for a in want_actions:
        if a not in ACTION_ORDER:
            return Plan(
                os_id=resolved_os,
                profile=profile,
                errors=[f"未知动作: {a}"],
            )

    by_name = {m["name"]: m for m in mod_list if m.get("name")}
    order_map = registry_order_map(mod_list)
    errors: list[str] = []
    reasons: dict[str, str] = {}
    seeds: list[str] = []

    if profile:
        try:
            prof_mods, pref = expand_profile_modules(profile, profiles)
            # full 且 modules 为空 → 与 select_all 等价（当前 OS 适用全集）
            pdata = profiles.get(profile) or {}
            if profile == "full" and not (pdata.get("modules") or []) and not (
                pdata.get("includes") or []
            ):
                select_all = True
            else:
                for m in prof_mods:
                    if m not in reasons:
                        reasons[m] = pref
                    seeds.append(m)
        except PlanError as e:
            return Plan(os_id=resolved_os, profile=profile, errors=e.errors)

    if modules_explicit:
        for m in modules_explicit:
            if m not in reasons:
                reasons[m] = "explicit"
            seeds.append(m)

    if select_all:
        for m in mod_list:
            name = m.get("name")
            if not name:
                continue
            os_list = m.get("os")
            if os_list is not None and not isinstance(os_list, list):
                os_list = [os_list]
            if not modules.matches_os(os_list, resolved_os):
                continue
            # 至少具备一个请求动作
            if not any(module_has_action(m, a) for a in want_actions):
                continue
            if name not in reasons:
                reasons[name] = "all"
            seeds.append(name)

    # 稳定去重保持首次出现顺序
    seen_seed: set[str] = set()
    unique_seeds: list[str] = []
    for s in seeds:
        if s not in seen_seed:
            seen_seed.add(s)
            unique_seeds.append(s)

    # agents 聚合安装 → 拆成可展示的单工具 install（仅当请求含 install）
    if "install" in want_actions and "agents" in unique_seeds:
        for tool in AGENTS_INSTALL_BUNDLE:
            if tool not in seen_seed:
                seen_seed.add(tool)
                unique_seeds.append(tool)
            reasons.setdefault(tool, "depends:agents")

    if not unique_seeds and not errors:
        # 允许空计划（例如空 profile）
        return Plan(os_id=resolved_os, profile=profile, actions=[], module_reasons={})

    selected, dep_reasons, dep_errors = expand_depends(unique_seeds, by_name)
    errors.extend(dep_errors)
    for k, v in dep_reasons.items():
        reasons.setdefault(k, v)

    # OS 过滤：显式模块不适用则报错；profile/all 静默跳过；依赖不适用则报错
    filtered: set[str] = set()
    for name in selected:
        mod = by_name.get(name)
        if mod is None:
            continue
        os_list = mod.get("os")
        if os_list is not None and not isinstance(os_list, list):
            os_list = [os_list]
        if modules.matches_os(os_list, resolved_os):
            filtered.add(name)
        elif reasons.get(name) == "explicit":
            errors.append(f"模块 {name} 不适用于 OS={resolved_os}")
        elif reasons.get(name, "").startswith("depends:"):
            errors.append(f"依赖 {name} 不适用于 OS={resolved_os}")
        # profile:* / all → 按 OS 静默过滤

    if errors:
        return Plan(
            os_id=resolved_os,
            profile=profile,
            errors=errors,
            module_reasons=reasons,
        )

    ordered, topo_errors = topo_sort(filtered, by_name, order_map)
    if topo_errors:
        return Plan(
            os_id=resolved_os,
            profile=profile,
            errors=topo_errors,
            module_reasons=reasons,
        )

    plan_actions: list[PlanAction] = []
    idx = 0
    for name in ordered:
        mod = by_name[name]
        reason = reasons.get(name, "unknown")
        # 仅显式点名时缺能力报错；profile 按能力跳过（模块可只含 install 或 config）
        strict_caps = reason == "explicit"
        for action in ACTION_ORDER:
            if action not in want_actions:
                continue
            if not module_has_action(mod, action):
                if strict_caps:
                    errors.append(f"模块 {name} 无 {action} 能力")
                continue
            idx += 1
            plan_actions.append(
                PlanAction(
                    module=name,
                    action=action,
                    reason=reason,
                    index=idx,
                )
            )

    if errors:
        return Plan(
            os_id=resolved_os,
            profile=profile,
            errors=errors,
            module_reasons=reasons,
        )

    return Plan(
        os_id=resolved_os,
        profile=profile,
        actions=plan_actions,
        module_reasons=reasons,
    )


def format_plan_text(plan: Plan) -> str:
    lines = [
        f"执行计划  OS={plan.os_id}"
        + (f"  profile={plan.profile}" if plan.profile else ""),
        f"共 {len(plan.actions)} 个动作",
        "",
    ]
    if not plan.actions:
        lines.append("（空计划）")
        return "\n".join(lines)
    lines.append(f"{'#':<4} {'ACTION':<8} {'MODULE':<16} REASON")
    lines.append("-" * 56)
    for a in plan.actions:
        lines.append(f"{a.index:<4} {a.action:<8} {a.module:<16} {a.reason}")
    return "\n".join(lines)


def format_plan_machine(plan: Plan) -> str:
    """bash 易解析的行协议。"""
    lines = ["PLAN_OK" if plan.ok else "PLAN_ERR"]
    lines.append(f"OS\t{plan.os_id}")
    lines.append(f"PROFILE\t{plan.profile or ''}")
    for err in plan.errors:
        lines.append(f"ERROR\t{err}")
    for a in plan.actions:
        lines.append(f"ACTION\t{a.index}\t{a.action}\t{a.module}\t{a.reason}")
    return "\n".join(lines) + "\n"


def cmd_plan(args: argparse.Namespace) -> int:
    actions = [x.strip() for x in args.actions.split(",") if x.strip()]
    explicit = [x.strip() for x in (args.modules or "").split(",") if x.strip()]
    plan = build_plan(
        os_id=args.os,
        profile=args.profile,
        modules_explicit=explicit or None,
        actions=actions,
        select_all=args.all,
    )
    if args.format == "json":
        payload = {
            "ok": plan.ok,
            "os_id": plan.os_id,
            "profile": plan.profile,
            "errors": plan.errors,
            "actions": [asdict(a) for a in plan.actions],
            "module_reasons": plan.module_reasons,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.format == "machine":
        sys.stdout.write(format_plan_machine(plan))
    else:
        if plan.errors:
            print("计划校验失败:", file=sys.stderr)
            for e in plan.errors:
                print(f"  - {e}", file=sys.stderr)
        else:
            print(format_plan_text(plan))
    return 0 if plan.ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="dotfiles 执行计划")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="生成执行计划")
    p.add_argument("--os", default=None, help="OS 覆盖")
    p.add_argument("--profile", default=None, help="使用场景 profile")
    p.add_argument("--modules", default="", help="逗号分隔显式模块")
    p.add_argument(
        "--actions",
        default="install,config",
        help="逗号分隔动作 install,config,doctor",
    )
    p.add_argument("--all", action="store_true", help="当前 OS 适用全集")
    p.add_argument(
        "--format",
        choices=["text", "machine", "json"],
        default="text",
    )
    p.set_defaults(func=cmd_plan)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
