#!/usr/bin/env python3
"""统一模块注册表与 profile 读取 API。

供 bin/dotf、scripts/install.sh、scripts/config.sh、scripts/doctor.sh 调用。
输出以纯文本/行分隔为主，便于 bash 消费。
"""

from __future__ import annotations

import argparse
import os
import posixpath
import re
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from ensure_pyyaml import ensure_yaml

yaml = ensure_yaml()

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = Path(os.environ.get("DOTF_REGISTRY_PATH", str(ROOT / "modules.yaml")))
PROFILES_PATH = Path(os.environ.get("DOTF_PROFILES_PATH", str(ROOT / "profiles.yaml")))
HANDLERS_DIR = Path(
    os.environ.get("DOTF_HANDLERS_DIR", str(ROOT / "scripts" / "modules"))
)

# 非工具型：不强制 doctor: true
NON_TOOL_MODULES = frozenset({"system", "homebrew", "fonts"})

# 注册表禁止的可执行 DSL 字段
FORBIDDEN_MODULE_KEYS = frozenset(
    {"script", "command", "handler", "function", "exec", "run"}
)

# init --list 展示的 OS profile 标识
OS_PROFILES = [
    "debian",
    "ubuntu",
    "arch",
    "fedora",
    "rhel",
    "darwin",
]

ACTIONS = ("install", "config", "doctor")

CONFIG_STRATEGIES = frozenset({"copy", "merge", "render", "symlink"})
CONFIG_KEYS = frozenset(
    {
        "source",
        "target",
        "strategy",
        "writable",
        "sensitive",
        "target_mode",
        "mode",  # compatibility alias; do not declare both
        "preserve",
        "exclude",
    }
)
CONFIG_REQUIRED_KEYS = frozenset(
    {"source", "target", "strategy", "writable", "sensitive", "preserve", "exclude"}
)
_MODE_RE = re.compile(r"^(?:0o)?[0-7]{3,4}$", re.IGNORECASE)


class _UniqueKeyLoader(yaml.SafeLoader):
    """PyYAML loader that rejects duplicate mapping keys instead of overwriting."""


def _construct_unique_mapping(loader: _UniqueKeyLoader, node: Any, deep: bool = False) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def parse_config_mode(value: Any) -> int:
    """Parse a registry permission mode without accepting booleans or decimal chmod text."""
    if isinstance(value, bool):
        raise ValueError("must be an octal mode")
    if isinstance(value, int):
        mode = value
    elif isinstance(value, str) and _MODE_RE.fullmatch(value):
        digits = value[2:] if value.lower().startswith("0o") else value
        mode = int(digits, 8)
    else:
        raise ValueError("must be an octal mode")
    if mode < 0 or mode > 0o777:
        raise ValueError("must be between 0000 and 0777")
    return mode


def module_config_mode(mod: dict[str, Any]) -> int | None:
    cfg = mod.get("config")
    if not isinstance(cfg, dict):
        return None
    keys = [key for key in ("target_mode", "mode") if key in cfg]
    if len(keys) != 1:
        return None
    try:
        return parse_config_mode(cfg[keys[0]])
    except ValueError:
        return None


def format_config_mode(mode: int | None) -> str:
    return f"{mode:04o}" if mode is not None else ""


def module_config_list(mod: dict[str, Any], field: str) -> list[str]:
    cfg = mod.get("config")
    if not isinstance(cfg, dict):
        return []
    value = cfg.get(field)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def module_target_mode(mod: dict[str, Any]) -> int | None:
    return module_config_mode(mod)


def module_mode(mod: dict[str, Any]) -> int | None:
    """Compatibility alias for registries/callers using mode."""
    return module_config_mode(mod)


def module_preserve(mod: dict[str, Any]) -> list[str]:
    return module_config_list(mod, "preserve")


def module_exclude(mod: dict[str, Any]) -> list[str]:
    return module_config_list(mod, "exclude")


def module_strategy(mod: dict[str, Any]) -> str:
    cfg = mod.get("config")
    value = cfg.get("strategy") if isinstance(cfg, dict) else None
    return value if isinstance(value, str) else ""


def module_writable(mod: dict[str, Any]) -> bool | None:
    cfg = mod.get("config")
    value = cfg.get("writable") if isinstance(cfg, dict) else None
    return value if isinstance(value, bool) else None


def module_sensitive(mod: dict[str, Any]) -> bool | None:
    cfg = mod.get("config")
    value = cfg.get("sensitive") if isinstance(cfg, dict) else None
    return value if isinstance(value, bool) else None


def load_registry(path: Path | None = None) -> list[dict[str, Any]]:
    reg_path = path or REGISTRY_PATH
    with reg_path.open(encoding="utf-8") as f:
        try:
            data = yaml.load(f, Loader=_UniqueKeyLoader) or {}
        except yaml.YAMLError as exc:
            raise SystemExit(f"无效注册表: {reg_path}: {exc}") from exc
    modules = data.get("modules") or []
    if not isinstance(modules, list):
        raise SystemExit(f"无效注册表: {reg_path}")
    return modules


def load_profiles(path: Path | None = None) -> dict[str, Any]:
    """返回 {version, default, profiles: {name: {desc, modules, includes}}}."""
    prof_path = path or PROFILES_PATH
    if not prof_path.is_file():
        return {"version": 1, "default": None, "profiles": {}}
    with prof_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"无效 profiles: {prof_path}")
    profiles = data.get("profiles") or {}
    if not isinstance(profiles, dict):
        raise SystemExit(f"无效 profiles.profiles: {prof_path}")
    return {
        "version": data.get("version", 1),
        "default": data.get("default"),
        "profiles": profiles,
    }


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
    if "linux" in module_os and current != "darwin" and current != "unknown":
        return True
    return False


def has_install(mod: dict[str, Any]) -> bool:
    return bool(mod.get("install"))


def has_config(mod: dict[str, Any]) -> bool:
    return isinstance(mod.get("config"), dict) and bool(mod["config"].get("source"))


def has_doctor(mod: dict[str, Any]) -> bool:
    return bool(mod.get("doctor"))


def is_enabled(mod: dict[str, Any]) -> bool:
    """enabled 缺省为 true；显式 false 时不参与自动全集/profile/--all。"""
    return mod.get("enabled", True) is not False


def is_tool_module(mod: dict[str, Any]) -> bool:
    name = mod.get("name")
    if not name or name in NON_TOOL_MODULES:
        return False
    return has_install(mod) or has_config(mod)


def module_bin(mod: dict[str, Any]) -> str:
    val = mod.get("bin")
    return str(val) if val else ""


def module_depends_on(mod: dict[str, Any]) -> list[str]:
    raw = mod.get("depends_on") or []
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw]


def module_group(mod: dict[str, Any]) -> str:
    val = mod.get("group")
    return str(val) if val else ""


def find_module(modules: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for mod in modules:
        if mod.get("name") == name:
            return mod
    return None


def filter_modules(
    modules: list[dict[str, Any]],
    *,
    capability: str | None = None,
    os_id: str | None = None,
    include_disabled: bool = False,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for mod in modules:
        if not include_disabled and not is_enabled(mod):
            continue
        if capability == "install" and not has_install(mod):
            continue
        if capability == "config" and not has_config(mod):
            continue
        if capability == "doctor" and not has_doctor(mod):
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


def handler_path(name: str, action: str) -> Path:
    return HANDLERS_DIR / name / f"{action}.sh"


def handler_exists(name: str, action: str) -> bool:
    return handler_path(name, action).is_file()


def _find_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """返回环路径列表（每条以起点重复结尾，如 A->B->A）。"""
    cycles: list[list[str]] = []
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def dfs(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            if node in stack:
                idx = stack.index(node)
                cycles.append(stack[idx:] + [node])
            return
        visiting.add(node)
        stack.append(node)
        for nxt in graph.get(node, []):
            dfs(nxt)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for n in graph:
        dfs(n)
    return cycles


def _metadata_path(value: str) -> str | None:
    """Normalize a relative metadata path; return None for unsafe/empty paths."""
    if not value or "\x00" in value or PurePosixPath(value).is_absolute():
        return None
    normalized = posixpath.normpath(value)
    if normalized in {"", ".", ".."} or normalized.startswith("../"):
        return None
    return normalized


def _paths_overlap(left: str, right: str) -> bool:
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def _config_source_type(source: Any) -> str:
    """Classify the source directory entry without following its leaf symlink."""
    if not isinstance(source, str) or not source:
        return "invalid"
    path = Path(source).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    try:
        source_stat = path.lstat()
    except FileNotFoundError:
        return "missing"
    except OSError:
        return "unreadable"
    mode = source_stat.st_mode
    if stat.S_ISREG(mode):
        return "file"
    if stat.S_ISDIR(mode):
        return "dir"
    if stat.S_ISLNK(mode):
        return "symlink"
    return "special"


def _validate_config_metadata(name: str, cfg: dict[str, Any], errors: list[str]) -> None:
    unknown = sorted(
        repr(key) for key in cfg if not isinstance(key, str) or key not in CONFIG_KEYS
    )
    if unknown:
        errors.append(f"{name}: config 包含未知字段 {unknown}")

    for key in sorted(CONFIG_REQUIRED_KEYS):
        if key not in cfg:
            errors.append(f"{name}: config.{key} 缺失")

    src = cfg.get("source")
    tgt = cfg.get("target")
    if not isinstance(src, str) or not src:
        errors.append(f"{name}: config.source 必须为非空字符串")
    if not isinstance(tgt, str) or not tgt:
        errors.append(f"{name}: config.target 必须为非空字符串")

    strategy = cfg.get("strategy")
    if not isinstance(strategy, str) or strategy not in CONFIG_STRATEGIES:
        errors.append(
            f"{name}: config.strategy 必须为 " + "|".join(sorted(CONFIG_STRATEGIES))
        )

    writable = cfg.get("writable")
    sensitive = cfg.get("sensitive")
    if not isinstance(writable, bool):
        errors.append(f"{name}: config.writable 必须为 bool")
    if not isinstance(sensitive, bool):
        errors.append(f"{name}: config.sensitive 必须为 bool")

    mode_keys = [key for key in ("target_mode", "mode") if key in cfg]
    mode: int | None = None
    if not mode_keys:
        errors.append(f"{name}: config.target_mode（或 mode）缺失")
    elif len(mode_keys) > 1:
        errors.append(f"{name}: config.target_mode 与 config.mode 不能同时声明")
    else:
        try:
            mode = parse_config_mode(cfg[mode_keys[0]])
        except ValueError:
            errors.append(
                f"{name}: config.{mode_keys[0]} 必须为 0000..0777 的八进制权限"
            )

    normalized_lists: dict[str, list[str]] = {}
    for field in ("preserve", "exclude"):
        value = cfg.get(field)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            errors.append(f"{name}: config.{field} 必须为字符串列表")
            continue
        normalized: list[str] = []
        for item in value:
            path = _metadata_path(item)
            if path is None:
                errors.append(f"{name}: config.{field} 包含非法相对路径 {item!r}")
            else:
                normalized.append(path)
        if len(normalized) != len(set(normalized)):
            errors.append(f"{name}: config.{field} 包含重复路径")
        normalized_lists[field] = normalized

    preserve = normalized_lists.get("preserve", [])
    exclude = normalized_lists.get("exclude", [])
    overlaps = sorted(
        {f"{left} <-> {right}" for left in preserve for right in exclude if _paths_overlap(left, right)}
    )
    if overlaps:
        errors.append(f"{name}: config.preserve/exclude 路径重叠 {overlaps}")

    source_type = _config_source_type(src)
    source_type_errors = {
        "missing": "source 不存在",
        "symlink": "source 自身是符号链接，不允许跟随",
        "special": "source 是特殊文件，必须为普通文件或目录",
        "unreadable": "source 无法 lstat，不能确定文件类型",
    }
    if source_type in source_type_errors:
        errors.append(f"{name}: config.{source_type_errors[source_type]}")

    if strategy == "symlink":
        if writable is not False or sensitive is not False:
            errors.append(
                f"{name}: strategy symlink 必须显式 writable: false 且 sensitive: false"
            )
        if source_type != "file":
            errors.append(
                f"{name}: strategy symlink 仅允许单个普通文件，source 类型为 {source_type}"
            )

    if source_type == "file" and (preserve or exclude):
        errors.append(f"{name}: 普通文件 config 不兼容 preserve/exclude 路径")

    if sensitive is True:
        if source_type not in {"file", "dir"}:
            errors.append(f"{name}: 敏感 config 无法确定目标是普通文件还是目录")
        elif mode is not None:
            if source_type == "file" and mode & ~0o600:
                errors.append(f"{name}: 敏感普通文件 target_mode 不得宽于 0600")
            elif source_type == "dir" and mode & ~0o700:
                errors.append(f"{name}: 敏感目录 target_mode 不得宽于 0700")


def validate_registry(
    modules: list[dict[str, Any]] | None = None,
    *,
    profiles_data: dict[str, Any] | None = None,
    strict_handlers: bool | None = None,
    handlers_dir: Path | None = None,
) -> list[str]:
    """返回错误列表；空列表表示通过。"""
    errors: list[str] = []
    mods = modules if modules is not None else load_registry()
    profiles_data = profiles_data if profiles_data is not None else load_profiles()
    if strict_handlers is None:
        strict_handlers = os.environ.get("DOTF_STRICT_HANDLERS", "").lower() in {
            "1",
            "true",
            "yes",
        }
    hdir = handlers_dir or HANDLERS_DIR

    names: list[str] = []
    by_name: dict[str, dict[str, Any]] = {}

    for idx, mod in enumerate(mods):
        if not isinstance(mod, dict):
            errors.append(f"modules[{idx}]: 条目必须为 mapping")
            continue

        bad = FORBIDDEN_MODULE_KEYS.intersection(mod.keys())
        if bad:
            errors.append(
                f"modules[{idx}] ({mod.get('name', '?')}): 禁止可执行字段 {sorted(bad)}"
            )

        name = mod.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"modules[{idx}]: name 必须为非空字符串")
            continue
        if name in by_name:
            errors.append(f"重复模块名: {name}")
        names.append(name)
        by_name[name] = mod

        if "install" in mod and not isinstance(mod["install"], bool):
            errors.append(f"{name}: install 必须为 bool")
        if "doctor" in mod and not isinstance(mod["doctor"], bool):
            errors.append(f"{name}: doctor 必须为 bool")
        if "enabled" in mod and not isinstance(mod["enabled"], bool):
            errors.append(f"{name}: enabled 必须为 bool")
        if "bin" in mod and mod["bin"] is not None and not isinstance(mod["bin"], str):
            errors.append(f"{name}: bin 必须为字符串")
        if "group" in mod and mod["group"] is not None and not isinstance(mod["group"], str):
            errors.append(f"{name}: group 必须为字符串")
        if "os" in mod and mod["os"] is not None:
            os_val = mod["os"]
            if isinstance(os_val, str):
                pass
            elif isinstance(os_val, list) and all(isinstance(x, str) for x in os_val):
                pass
            else:
                errors.append(f"{name}: os 必须为字符串或字符串列表")
        if "depends_on" in mod and mod["depends_on"] is not None:
            dep = mod["depends_on"]
            if not isinstance(dep, list) or not all(isinstance(x, str) for x in dep):
                errors.append(f"{name}: depends_on 必须为字符串列表")

        cfg = mod.get("config")
        if cfg is not None:
            if not isinstance(cfg, dict):
                errors.append(f"{name}: config 必须为 mapping")
            else:
                _validate_config_metadata(name, cfg, errors)

        if is_tool_module(mod) and not has_doctor(mod):
            errors.append(f"{name}: 工具型模块缺少 doctor: true")

    # 依赖引用与环
    dep_graph: dict[str, list[str]] = {}
    for name, mod in by_name.items():
        deps = module_depends_on(mod)
        dep_graph[name] = deps
        for d in deps:
            if d not in by_name:
                errors.append(f"{name}: depends_on 引用未知模块 '{d}'")

    for cycle in _find_cycles(dep_graph):
        errors.append("模块依赖环: " + " -> ".join(cycle))

    # profiles
    profiles = profiles_data.get("profiles") or {}
    default = profiles_data.get("default")
    if default is not None and default not in profiles:
        errors.append(f"profiles: default '{default}' 未定义")

    include_graph: dict[str, list[str]] = {}
    if not isinstance(profiles, dict):
        errors.append("profiles: 必须为 mapping")
    else:
        for pname, pdata in profiles.items():
            if not isinstance(pdata, dict):
                errors.append(f"profile '{pname}': 必须为 mapping")
                continue
            mods_list = pdata.get("modules") or []
            includes = pdata.get("includes") or []
            if not isinstance(mods_list, list) or not all(
                isinstance(x, str) for x in mods_list
            ):
                errors.append(f"profile '{pname}': modules 必须为字符串列表")
                mods_list = []
            if not isinstance(includes, list) or not all(
                isinstance(x, str) for x in includes
            ):
                errors.append(f"profile '{pname}': includes 必须为字符串列表")
                includes = []
            include_graph[pname] = list(includes)
            for m in mods_list:
                if m not in by_name:
                    errors.append(f"profile '{pname}': 未知模块 '{m}'")
            for inc in includes:
                if inc not in profiles:
                    errors.append(f"profile '{pname}': 未知 include '{inc}'")

        for cycle in _find_cycles(include_graph):
            errors.append("profile include 环: " + " -> ".join(cycle))

    # 处理器声明一致性（迁移模式默认关闭严格失败）
    if hdir.is_dir() or strict_handlers:
        for name, mod in by_name.items():
            for action in ACTIONS:
                declared = (
                    (action == "install" and has_install(mod))
                    or (action == "config" and has_config(mod))
                    or (action == "doctor" and has_doctor(mod))
                )
                path = hdir / name / f"{action}.sh"
                exists = path.is_file()
                if declared and not exists and strict_handlers:
                    # Config has a registry-backed generic fallback; install is
                    # executable behavior and therefore still requires a handler.
                    if action == "install":
                        errors.append(
                            f"{name}: 声明 {action} 但缺少处理器 "
                            f"scripts/modules/{name}/{action}.sh"
                        )
                if exists and not declared:
                    msg = f"{name}: 存在处理器 {action}.sh 但未声明能力"
                    if strict_handlers:
                        errors.append(msg)

    return errors


def cmd_list(args: argparse.Namespace) -> int:
    modules = load_registry()
    os_id: str | None = None
    if args.os:
        os_id = args.os
    elif args.filter_os:
        os_id = detect_os()
    filtered = filter_modules(modules, capability=args.capability, os_id=os_id)
    if args.registry_order:
        pass  # 保持 modules.yaml 声明顺序
    else:
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
    if has_doctor(mod):
        caps.append("doctor")
    print(f"name={mod['name']}")
    print(f"desc={mod.get('desc', '')}")
    print(f"capabilities={','.join(caps)}")
    if has_config(mod):
        cfg = mod["config"]
        print(f"source={cfg.get('source', '')}")
        print(f"target={cfg.get('target', '')}")
        print(f"strategy={module_strategy(mod)}")
        writable = module_writable(mod)
        sensitive = module_sensitive(mod)
        print(f"writable={str(writable).lower() if writable is not None else ''}")
        print(f"sensitive={str(sensitive).lower() if sensitive is not None else ''}")
        print(f"target_mode={format_config_mode(module_config_mode(mod))}")
        print(f"preserve={','.join(module_config_list(mod, 'preserve'))}")
        print(f"exclude={','.join(module_config_list(mod, 'exclude'))}")
    bin_name = module_bin(mod)
    if bin_name:
        print(f"bin={bin_name}")
    deps = module_depends_on(mod)
    if deps:
        print(f"depends_on={','.join(deps)}")
    group = module_group(mod)
    if group:
        print(f"group={group}")
    os_list = mod.get("os") or []
    if os_list:
        if not isinstance(os_list, list):
            os_list = [os_list]
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
    if args.capability == "doctor":
        return 0 if has_doctor(mod) else 1
    return 1


def cmd_field(args: argparse.Namespace) -> int:
    mod = find_module(load_registry(), args.name)
    if not mod:
        print(f"未知模块: {args.name}", file=sys.stderr)
        return 1
    if args.field == "desc":
        print(mod.get("desc", args.name))
        return 0
    if args.field == "bin":
        print(module_bin(mod))
        return 0
    if args.field == "group":
        print(module_group(mod))
        return 0
    if args.field == "depends_on":
        print(" ".join(module_depends_on(mod)))
        return 0
    if args.field in (
        "source",
        "target",
        "strategy",
        "writable",
        "sensitive",
        "target_mode",
        "mode",
        "preserve",
        "exclude",
    ):
        if not has_config(mod):
            print(f"模块 {args.name} 无 config 能力", file=sys.stderr)
            return 1
        cfg = mod["config"]
        if args.field in ("source", "target"):
            print(cfg.get(args.field, ""))
        elif args.field == "strategy":
            print(module_strategy(mod))
        elif args.field == "writable":
            value = module_writable(mod)
            print(str(value).lower() if value is not None else "")
        elif args.field == "sensitive":
            value = module_sensitive(mod)
            print(str(value).lower() if value is not None else "")
        elif args.field in ("target_mode", "mode"):
            print(format_config_mode(module_config_mode(mod)))
        else:
            print(" ".join(module_config_list(mod, args.field)))
        return 0
    print(f"未知字段: {args.field}", file=sys.stderr)
    return 1


def cmd_exists(args: argparse.Namespace) -> int:
    return 0 if find_module(load_registry(), args.name) else 1


def cmd_detect_os(_: argparse.Namespace) -> int:
    print(detect_os())
    return 0


def cmd_profiles(args: argparse.Namespace) -> int:
    if args.kind == "os":
        for p in OS_PROFILES:
            print(p)
        return 0
    data = load_profiles()
    if args.kind == "default":
        default = data.get("default")
        if default:
            print(default)
        return 0 if default else 1
    for name in data.get("profiles") or {}:
        print(name)
    return 0


def cmd_names(args: argparse.Namespace) -> int:
    """空格分隔的名称列表（兼容旧 get_all_* 风格）。"""
    modules = load_registry()
    os_id = detect_os() if args.filter_os else None
    filtered = filter_modules(modules, capability=args.capability, os_id=os_id)
    filtered.sort(key=lambda m: m.get("name", ""))
    print(" ".join(m["name"] for m in filtered))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    errors = validate_registry(strict_handlers=args.strict_handlers)
    if errors:
        print("错误: 注册表/profile 校验失败:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    mode = "strict-handlers" if args.strict_handlers else "migration"
    print(f"✓ 注册表校验通过（{mode}）")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="dotfiles 模块注册表 API")
    sub = parser.add_subparsers(dest="cmd", required=True)

    cap_choices = ["install", "config", "doctor", "both"]

    p_list = sub.add_parser("list", help="列出模块名")
    p_list.add_argument(
        "--capability",
        choices=cap_choices,
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
    p_list.add_argument(
        "--registry-order",
        action="store_true",
        help="保持 modules.yaml 声明顺序（默认按名称排序）",
    )
    p_list.set_defaults(func=cmd_list)

    p_names = sub.add_parser("names", help="空格分隔名称列表")
    p_names.add_argument("--capability", choices=cap_choices, default=None)
    p_names.add_argument("--filter-os", action="store_true")
    p_names.set_defaults(func=cmd_names)

    p_get = sub.add_parser("get", help="查询模块详情")
    p_get.add_argument("name")
    p_get.set_defaults(func=cmd_get)

    p_has = sub.add_parser("has", help="检查能力（exit 0/1）")
    p_has.add_argument("name")
    p_has.add_argument("capability", choices=["install", "config", "doctor"])
    p_has.set_defaults(func=cmd_has)

    p_exists = sub.add_parser("exists", help="模块是否存在（exit 0/1）")
    p_exists.add_argument("name")
    p_exists.set_defaults(func=cmd_exists)

    p_field = sub.add_parser("field", help="读取字段")
    p_field.add_argument("name")
    p_field.add_argument(
        "field",
        choices=[
            "desc",
            "source",
            "target",
            "strategy",
            "writable",
            "sensitive",
            "target_mode",
            "mode",
            "preserve",
            "exclude",
            "bin",
            "group",
            "depends_on",
        ],
    )
    p_field.set_defaults(func=cmd_field)

    p_os = sub.add_parser("detect-os", help="检测当前 OS ID")
    p_os.set_defaults(func=cmd_detect_os)

    p_prof = sub.add_parser("profiles", help="列出 profile")
    p_prof.add_argument(
        "kind",
        nargs="?",
        default="os",
        choices=["usage", "os", "default"],
        help="os=平台 profile（默认，兼容 init --list）；usage=使用场景；default=默认场景名",
    )
    p_prof.set_defaults(func=cmd_profiles)

    p_val = sub.add_parser("validate", help="校验注册表与 profile")
    p_val.add_argument(
        "--strict-handlers",
        action="store_true",
        help="严格校验约定式处理器（迁移完成后启用）",
    )
    p_val.set_defaults(func=cmd_validate)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
