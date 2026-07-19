#!/usr/bin/env python3
"""统一模块注册表读取 API。

供 bin/dotf、scripts/install.sh、scripts/config.sh 调用。
输出以纯文本/行分隔为主，便于 bash 消费。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("错误: 需要 PyYAML（python3 -c 'import yaml'）", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "modules.yaml"

# init --list 展示的 profile 标识（覆盖 system.sh dispatch_init 主要族）
OS_PROFILES = [
    "debian",
    "ubuntu",
    "arch",
    "fedora",
    "rhel",
    "darwin",
]


def load_registry() -> list[dict[str, Any]]:
    with REGISTRY_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    modules = data.get("modules") or []
    if not isinstance(modules, list):
        raise SystemExit(f"无效注册表: {REGISTRY_PATH}")
    return modules


def detect_os() -> str:
    """与 scripts/tools/system.sh detect_os 语义对齐的轻量检测。"""
    os_release = Path("/etc/os-release")
    if os_release.is_file():
        kv: dict[str, str] = {}
        for line in os_release.read_text(encoding="utf-8").splitlines():
            if "=" not in line or line.startswith("#"):
                continue
            key, _, val = line.partition("=")
            kv[key] = val.strip().strip('"')
        return kv.get("ID", "unknown")
    if Path("/etc/arch-release").is_file():
        return "arch"
    if sys.platform == "darwin":
        return "darwin"
    return "unknown"


def matches_os(module_os: list[str] | None, current: str) -> bool:
    if not module_os:
        return True
    if current in module_os:
        return True
    # 族名 linux = 非 darwin
    if "linux" in module_os and current != "darwin" and current != "unknown":
        return True
    return False


def has_install(mod: dict[str, Any]) -> bool:
    return bool(mod.get("install"))


def has_config(mod: dict[str, Any]) -> bool:
    return isinstance(mod.get("config"), dict) and bool(mod["config"].get("source"))


def find_module(modules: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    # 别名
    if name == "codebuddy":
        name = "codebuddy-code"
    for mod in modules:
        if mod.get("name") == name:
            return mod
    return None


def filter_modules(
    modules: list[dict[str, Any]],
    *,
    capability: str | None = None,
    os_id: str | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for mod in modules:
        if capability == "install" and not has_install(mod):
            continue
        if capability == "config" and not has_config(mod):
            continue
        if capability == "both" and not (has_install(mod) and has_config(mod)):
            continue
        if os_id is not None:
            os_list = mod.get("os")
            if os_list is not None and not isinstance(os_list, list):
                os_list = [os_list]
            if not matches_os(os_list, os_id):
                continue
        out.append(mod)
    return out


def cmd_list(args: argparse.Namespace) -> int:
    modules = load_registry()
    os_id: str | None = None
    if args.os:
        os_id = args.os
    elif args.filter_os:
        os_id = detect_os()
    filtered = filter_modules(modules, capability=args.capability, os_id=os_id)
    filtered.sort(key=lambda m: m.get("name", ""))

    for mod in filtered:
        if args.desc:
            print(f"{mod['name']}\t{mod.get('desc', mod['name'])}")
        else:
            print(mod["name"])
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    mod = find_module(load_registry(), args.name)
    if not mod:
        print(f"未知模块: {args.name}", file=sys.stderr)
        return 1
    caps = []
    if has_install(mod):
        caps.append("install")
    if has_config(mod):
        caps.append("config")
    print(f"name={mod['name']}")
    print(f"desc={mod.get('desc', '')}")
    print(f"capabilities={','.join(caps)}")
    if has_config(mod):
        cfg = mod["config"]
        print(f"source={cfg.get('source', '')}")
        print(f"target={cfg.get('target', '')}")
    os_list = mod.get("os") or []
    if os_list:
        print(f"os={','.join(os_list)}")
    return 0


def cmd_has(args: argparse.Namespace) -> int:
    mod = find_module(load_registry(), args.name)
    if not mod:
        return 1
    if args.capability == "install":
        return 0 if has_install(mod) else 1
    if args.capability == "config":
        return 0 if has_config(mod) else 1
    return 1


def cmd_field(args: argparse.Namespace) -> int:
    mod = find_module(load_registry(), args.name)
    if not mod:
        print(f"未知模块: {args.name}", file=sys.stderr)
        return 1
    if args.field == "desc":
        print(mod.get("desc", args.name))
        return 0
    if args.field in ("source", "target"):
        if not has_config(mod):
            print(f"模块 {args.name} 无 config 能力", file=sys.stderr)
            return 1
        print(mod["config"].get(args.field, ""))
        return 0
    print(f"未知字段: {args.field}", file=sys.stderr)
    return 1


def cmd_exists(args: argparse.Namespace) -> int:
    return 0 if find_module(load_registry(), args.name) else 1


def cmd_detect_os(_: argparse.Namespace) -> int:
    print(detect_os())
    return 0


def cmd_profiles(_: argparse.Namespace) -> int:
    for p in OS_PROFILES:
        print(p)
    return 0


def cmd_names(args: argparse.Namespace) -> int:
    """空格分隔的名称列表（兼容旧 get_all_* 风格）。"""
    modules = load_registry()
    os_id = detect_os() if args.filter_os else None
    filtered = filter_modules(modules, capability=args.capability, os_id=os_id)
    filtered.sort(key=lambda m: m.get("name", ""))
    print(" ".join(m["name"] for m in filtered))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="dotfiles 模块注册表 API")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="列出模块名")
    p_list.add_argument(
        "--capability",
        choices=["install", "config", "both"],
        default=None,
        help="按能力过滤",
    )
    p_list.add_argument("--os", default=None, help="按指定 OS 过滤")
    p_list.add_argument(
        "--filter-os",
        action="store_true",
        help="按当前检测 OS 过滤",
    )
    p_list.add_argument("--desc", action="store_true", help="输出 name\\tdesc")
    p_list.set_defaults(func=cmd_list)

    p_names = sub.add_parser("names", help="空格分隔名称列表")
    p_names.add_argument("--capability", choices=["install", "config", "both"], default=None)
    p_names.add_argument("--filter-os", action="store_true")
    p_names.set_defaults(func=cmd_names)

    p_get = sub.add_parser("get", help="查询模块详情")
    p_get.add_argument("name")
    p_get.set_defaults(func=cmd_get)

    p_has = sub.add_parser("has", help="检查能力（exit 0/1）")
    p_has.add_argument("name")
    p_has.add_argument("capability", choices=["install", "config"])
    p_has.set_defaults(func=cmd_has)

    p_exists = sub.add_parser("exists", help="模块是否存在（exit 0/1）")
    p_exists.add_argument("name")
    p_exists.set_defaults(func=cmd_exists)

    p_field = sub.add_parser("field", help="读取字段")
    p_field.add_argument("name")
    p_field.add_argument("field", choices=["desc", "source", "target"])
    p_field.set_defaults(func=cmd_field)

    p_os = sub.add_parser("detect-os", help="检测当前 OS ID")
    p_os.set_defaults(func=cmd_detect_os)

    p_prof = sub.add_parser("profiles", help="列出 init OS profile")
    p_prof.set_defaults(func=cmd_profiles)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
