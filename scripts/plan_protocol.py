#!/usr/bin/env python3
"""Strict, versioned execution-plan protocol and dependency scheduler helpers."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modules  # noqa: E402

PLAN_HEADER = "DOTF_EXECUTION_PLAN"
PLAN_VERSION = 1
PLAN_SUCCESS_MARKER = "DOTF_PLAN_COMPLETE_V1"
ACTION_ORDER = ("install", "config", "doctor")
PLAN_KEYS = {
    "header",
    "version",
    "success_marker",
    "requested_os",
    "detected_os",
    "planned_os",
    "profile",
    "requested_actions",
    "registry_digest",
    "handler_digest",
    "plan_digest",
    "modules",
    "actions",
}
MODULE_KEYS = {"name", "registry_order", "depends_on", "capabilities", "planned_actions"}
ACTION_KEYS = {"index", "action", "module", "reason"}


class ProtocolError(ValueError):
    pass


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError(f"重复字段: {key}")
        result[key] = value
    return result


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def registry_digest(registry: list[dict[str, Any]]) -> str:
    return hashlib.sha256(_canonical(registry)).hexdigest()


def _capabilities(mod: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if modules.has_install(mod):
        out.append("install")
    if modules.has_config(mod):
        out.append("config")
    if modules.has_doctor(mod):
        out.append("doctor")
    return out


def handler_digest(
    registry: list[dict[str, Any]], handlers_dir: Path | None = None
) -> str:
    root = handlers_dir or modules.HANDLERS_DIR
    records: list[dict[str, str]] = []
    for mod in registry:
        name = mod.get("name")
        if not isinstance(name, str):
            continue
        for action in ACTION_ORDER:
            path = root / name / f"{action}.sh"
            if path.is_file():
                records.append(
                    {
                        "module": name,
                        "action": action,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                )
    return hashlib.sha256(_canonical(records)).hexdigest()


def module_records(
    ordered_names: list[str],
    registry: list[dict[str, Any]],
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_name = {m.get("name"): m for m in registry}
    order = {m.get("name"): i for i, m in enumerate(registry)}
    planned = {
        name: [item["action"] for item in actions if item["module"] == name]
        for name in ordered_names
    }
    records: list[dict[str, Any]] = []
    for name in ordered_names:
        mod = by_name[name]
        records.append(
            {
                "name": name,
                "registry_order": order[name],
                "depends_on": modules.module_depends_on(mod),
                "capabilities": _capabilities(mod),
                "planned_actions": planned[name],
            }
        )
    return records


def dependency_digest(document: dict[str, Any], name: str) -> str:
    """Hash one planned module's complete recursive dependency declaration."""
    records = document.get("modules")
    if not isinstance(records, list):
        raise ProtocolError("modules 必须为列表")
    by_name = {
        record.get("name"): record
        for record in records
        if isinstance(record, dict) and isinstance(record.get("name"), str)
    }
    if name not in by_name:
        raise ProtocolError(f"依赖摘要引用未知模块: {name}")
    selected: set[str] = set()
    pending = [name]
    while pending:
        current = pending.pop()
        if current in selected:
            continue
        record = by_name.get(current)
        if record is None or not isinstance(record.get("depends_on"), list):
            raise ProtocolError(f"模块 {current} 依赖元数据无效")
        selected.add(current)
        for dependency in record["depends_on"]:
            if dependency not in by_name:
                raise ProtocolError(f"模块 {current} 的依赖 {dependency} 不在计划中")
            pending.append(dependency)
    payload = [
        {"name": record["name"], "depends_on": record["depends_on"]}
        for record in records
        if isinstance(record, dict) and record.get("name") in selected
    ]
    return hashlib.sha256(_canonical(payload)).hexdigest()


def make_document(
    *,
    requested_os: str | None,
    detected_os: str,
    planned_os: str,
    profile: str | None,
    requested_actions: list[str],
    registry: list[dict[str, Any]],
    ordered_modules: list[str],
    actions: list[dict[str, Any]],
    handlers_dir: Path | None = None,
) -> dict[str, Any]:
    document = {
        "header": PLAN_HEADER,
        "version": PLAN_VERSION,
        "success_marker": PLAN_SUCCESS_MARKER,
        "requested_os": requested_os,
        "detected_os": detected_os,
        "planned_os": planned_os,
        "profile": profile,
        "requested_actions": requested_actions,
        "registry_digest": registry_digest(registry),
        "handler_digest": handler_digest(registry, handlers_dir),
        "modules": module_records(ordered_modules, registry, actions),
        "actions": actions,
    }
    document["plan_digest"] = hashlib.sha256(_canonical(document)).hexdigest()
    return document


def dumps(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def load(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProtocolError(f"无法读取计划: {exc}") from exc
    if not text.strip():
        raise ProtocolError("计划为空或 planner 未产生完整输出")
    try:
        value = json.loads(text, object_pairs_hook=_strict_object)
    except (json.JSONDecodeError, ProtocolError) as exc:
        raise ProtocolError(f"计划 JSON 无效或被截断: {exc}") from exc
    if not isinstance(value, dict):
        raise ProtocolError("计划根必须为对象")
    return value


def _exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    if missing:
        raise ProtocolError(f"{label} 缺少字段: {', '.join(missing)}")
    if unknown:
        raise ProtocolError(f"{label} 包含未知字段: {', '.join(unknown)}")


def _text(value: Any, label: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if not isinstance(value, str) or not value or "\t" in value or "\n" in value:
        raise ProtocolError(f"{label} 必须为非空单行字符串")
    return value


def _topological_order(names: list[str], by_name: dict[str, dict[str, Any]], order: dict[str, int]) -> list[str]:
    selected = set(names)
    indegree = {name: 0 for name in names}
    graph = {name: [] for name in names}
    for name in names:
        for dep in modules.module_depends_on(by_name[name]):
            if dep not in selected:
                raise ProtocolError(f"模块 {name} 的依赖 {dep} 未包含在完整计划中")
            graph[dep].append(name)
            indegree[name] += 1
    ready = sorted((n for n in names if indegree[n] == 0), key=order.__getitem__)
    result: list[str] = []
    while ready:
        name = ready.pop(0)
        result.append(name)
        for nxt in sorted(graph[name], key=order.__getitem__):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
                ready.sort(key=order.__getitem__)
    if len(result) != len(names):
        raise ProtocolError("计划模块依赖顺序无效或包含环")
    return result


def validate(document: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    _exact_keys(document, PLAN_KEYS, "计划")
    if document["header"] != PLAN_HEADER:
        raise ProtocolError("缺少或未知计划 header")
    if type(document["version"]) is not int or document["version"] != PLAN_VERSION:
        raise ProtocolError(
            f"计划版本不受支持: got={document['version']!r}, want={PLAN_VERSION}"
        )
    if document["success_marker"] != PLAN_SUCCESS_MARKER:
        raise ProtocolError("缺少或重复/未知 planner 成功标记")
    plan_digest_value = document["plan_digest"]
    if not isinstance(plan_digest_value, str) or len(plan_digest_value) != 64:
        raise ProtocolError("plan_digest 缺失或格式无效")
    digest_payload = {key: value for key, value in document.items() if key != "plan_digest"}
    expected_plan_digest = hashlib.sha256(_canonical(digest_payload)).hexdigest()
    if plan_digest_value != expected_plan_digest:
        raise ProtocolError("计划内容摘要不匹配，计划可能被截断或修改")

    requested_os = _text(document["requested_os"], "requested_os", nullable=True)
    detected_os = _text(document["detected_os"], "detected_os")
    planned_os = _text(document["planned_os"], "planned_os")
    profile = _text(document["profile"], "profile", nullable=True)
    if planned_os != (requested_os or detected_os):
        raise ProtocolError("planned_os 与 requested_os/detected_os 不一致")

    actual_os = modules.detect_os()
    if detected_os != actual_os:
        raise ProtocolError(
            f"计划检测 OS 已失效: plan={detected_os}, current={actual_os}"
        )
    if not dry_run and planned_os != actual_os:
        raise ProtocolError(
            f"请求 OS 与检测 OS 不一致: requested={planned_os}, detected={actual_os}; "
            "跨 OS 仅允许 --dry-run"
        )

    requested_actions = document["requested_actions"]
    if not isinstance(requested_actions, list) or not requested_actions:
        raise ProtocolError("requested_actions 必须为非空列表")
    if any(a not in ACTION_ORDER for a in requested_actions):
        raise ProtocolError("requested_actions 包含未知动作")
    if len(requested_actions) != len(set(requested_actions)):
        raise ProtocolError("requested_actions 包含重复动作")
    if requested_actions != [a for a in ACTION_ORDER if a in requested_actions]:
        raise ProtocolError("requested_actions 生命周期顺序无效")

    registry = modules.load_registry()
    profiles = modules.load_profiles()
    strict_errors = modules.validate_registry(
        registry, profiles_data=profiles, strict_handlers=True
    )
    if strict_errors:
        raise ProtocolError("strict registry/handler 校验失败: " + "; ".join(strict_errors))
    if profile is not None and profile not in (profiles.get("profiles") or {}):
        raise ProtocolError(f"未知 profile: {profile}")
    if document["registry_digest"] != registry_digest(registry):
        raise ProtocolError("注册表漂移: 计划与当前 modules.yaml 不一致")
    if document["handler_digest"] != handler_digest(registry):
        raise ProtocolError("handler 漂移: 计划验证后处理器集合或内容已变化")

    by_name = {m.get("name"): m for m in registry}
    registry_order = {m.get("name"): i for i, m in enumerate(registry)}
    plan_modules = document["modules"]
    if not isinstance(plan_modules, list):
        raise ProtocolError("modules 必须为列表")
    names: list[str] = []
    for pos, record in enumerate(plan_modules):
        if not isinstance(record, dict):
            raise ProtocolError(f"modules[{pos}] 必须为对象")
        _exact_keys(record, MODULE_KEYS, f"modules[{pos}]")
        name = _text(record["name"], f"modules[{pos}].name")
        if name in names:
            raise ProtocolError(f"重复计划模块: {name}")
        if name not in by_name:
            raise ProtocolError(f"未知计划模块: {name}")
        mod = by_name[name]
        if type(record["registry_order"]) is not int or record["registry_order"] != registry_order[name]:
            raise ProtocolError(f"模块 {name} registry_order 无效或注册表已漂移")
        expected_deps = modules.module_depends_on(mod)
        if record["depends_on"] != expected_deps:
            raise ProtocolError(f"模块 {name} 依赖元数据无效或注册表已漂移")
        caps = record["capabilities"]
        if not isinstance(caps, list) or any(cap not in ACTION_ORDER for cap in caps):
            raise ProtocolError(f"模块 {name} 包含未知 capability")
        if len(caps) != len(set(caps)):
            raise ProtocolError(f"模块 {name} 包含重复 capability")
        if caps != _capabilities(mod):
            raise ProtocolError(f"模块 {name} capability 缺失、截断或注册表已漂移")
        planned_actions = record["planned_actions"]
        if not isinstance(planned_actions, list) or any(
            action not in ACTION_ORDER for action in planned_actions
        ):
            raise ProtocolError(f"模块 {name} planned_actions 包含未知动作")
        if len(planned_actions) != len(set(planned_actions)):
            raise ProtocolError(f"模块 {name} planned_actions 包含重复动作")
        if planned_actions != [action for action in ACTION_ORDER if action in planned_actions]:
            raise ProtocolError(f"模块 {name} planned_actions 生命周期顺序无效")
        if any(action not in caps for action in planned_actions):
            raise ProtocolError(f"模块 {name} planned_actions 包含未声明 capability")
        if any(action not in requested_actions for action in planned_actions):
            raise ProtocolError(f"模块 {name} planned_actions 超出请求动作")
        os_list = mod.get("os")
        if os_list is not None and not isinstance(os_list, list):
            os_list = [os_list]
        if not modules.matches_os(os_list, planned_os):
            raise ProtocolError(f"模块 {name} 不适用于计划 OS={planned_os}")
        names.append(name)

    if names != _topological_order(names, by_name, registry_order):
        raise ProtocolError("模块顺序不是确定性的依赖优先/注册表顺序")

    raw_actions = document["actions"]
    if not isinstance(raw_actions, list):
        raise ProtocolError("actions 必须为列表")
    seen_pairs: set[tuple[str, str]] = set()
    actual_pairs: list[tuple[str, str]] = []
    for pos, action_record in enumerate(raw_actions, start=1):
        if not isinstance(action_record, dict):
            raise ProtocolError(f"actions[{pos - 1}] 必须为对象")
        _exact_keys(action_record, ACTION_KEYS, f"actions[{pos - 1}]")
        if type(action_record["index"]) is not int or action_record["index"] != pos:
            raise ProtocolError("动作 index 必须从 1 开始连续且唯一")
        action = _text(action_record["action"], f"actions[{pos - 1}].action")
        name = _text(action_record["module"], f"actions[{pos - 1}].module")
        _text(action_record["reason"], f"actions[{pos - 1}].reason")
        if action not in ACTION_ORDER:
            raise ProtocolError(f"未知动作: {action}")
        if name not in names:
            raise ProtocolError(f"动作引用未知或截断模块: {name}")
        pair = (name, action)
        if pair in seen_pairs:
            raise ProtocolError(f"重复动作: {name}/{action}")
        seen_pairs.add(pair)
        actual_pairs.append(pair)

    planned_by_module = {
        record["name"]: record["planned_actions"] for record in plan_modules
    }
    expected_pairs = [
        (name, action)
        for name in names
        for action in planned_by_module[name]
    ]
    if actual_pairs != expected_pairs:
        raise ProtocolError("动作缺失、截断或生命周期/依赖顺序无效")
    return document


def transitive_dependencies(document: dict[str, Any], name: str) -> tuple[str, ...]:
    """Return one module's unique recursive dependencies in declaration order."""
    deps = {m["name"]: m["depends_on"] for m in document["modules"]}
    if name not in deps:
        raise ProtocolError(f"依赖摘要引用未知模块: {name}")
    ordered: list[str] = []
    seen: set[str] = set()

    def visit(current: str) -> None:
        for dependency in deps.get(current, []):
            if dependency in seen:
                continue
            seen.add(dependency)
            ordered.append(dependency)
            visit(dependency)

    visit(name)
    return tuple(ordered)


def _transitive_depends(document: dict[str, Any], name: str, failed: set[str]) -> bool:
    return any(dependency in failed for dependency in transitive_dependencies(document, name))


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        document = validate(load(Path(args.plan)), dry_run=args.dry_run)
    except (ProtocolError, OSError, SystemExit) as exc:
        print(f"计划协议校验失败: {exc}", file=sys.stderr)
        return 2
    if args.emit_tsv:
        print(f"META\t{document['planned_os']}\t{document['profile'] or ''}")
        for action in document["actions"]:
            print(
                "ACTION\t{index}\t{action}\t{module}\t{reason}".format(**action)
            )
        for module in document["modules"]:
            dependencies = ",".join(transitive_dependencies(document, module["name"]))
            print(f"DEPENDENCIES\t{module['name']}\t{dependencies}")
    return 0


def cmd_is_blocked(args: argparse.Namespace) -> int:
    try:
        document = validate(load(Path(args.plan)), dry_run=args.dry_run)
    except (ProtocolError, OSError, SystemExit) as exc:
        print(f"计划协议校验失败: {exc}", file=sys.stderr)
        return 2
    failed = {name for name in args.failed.split(",") if name}
    if args.module in failed:
        print("same-module-failed")
        return 0
    if _transitive_depends(document, args.module, failed):
        print("dependency-failed")
        return 0
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="dotf execution plan protocol")
    sub = parser.add_subparsers(dest="command", required=True)
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--plan", required=True)
    validate_parser.add_argument("--dry-run", action="store_true")
    validate_parser.add_argument("--emit-tsv", action="store_true")
    validate_parser.set_defaults(func=cmd_validate)
    blocked_parser = sub.add_parser("is-blocked")
    blocked_parser.add_argument("--plan", required=True)
    blocked_parser.add_argument("--module", required=True)
    blocked_parser.add_argument("--failed", default="")
    blocked_parser.add_argument("--dry-run", action="store_true")
    blocked_parser.set_defaults(func=cmd_is_blocked)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
