#!/usr/bin/env python3
"""Canonical Agent doctor: shared plans, ownership, boundaries, and security."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import queue
import re
import shutil
import stat
import subprocess
import sys
import threading
import time
import tomllib
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from adapters import adapter_for  # noqa: E402
from common import Catalog, TOOLS  # noqa: E402
from managed_runtime import AgentRuntimeError, compile_skills_plan  # noqa: E402
from mcp_runtime import read_manifest as read_mcp_manifest  # noqa: E402
from openspec_skills import openspec_command  # noqa: E402
from sync import (  # noqa: E402
    KIRO_SKILL_IDENTITY_PREFIX,
    KIRO_SKILL_OWNER_PREFIX,
    kiro_skills_target,
    render_kiro_skill_bytes,
    render_skill_bytes,
    skills_target,
)
from sync_plan import compile_sync_plan  # noqa: E402
from dotf_core.paths import (  # noqa: E402
    PathBoundaryError,
    assert_no_symlinks,
    lstat_components,
    open_nofollow,
)
from dotf_core.sanitize import sanitize_for_terminal  # noqa: E402

try:  # registry is a shared source of config deployment metadata
    import modules as registry_modules  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - only an incomplete checkout
    registry_modules = None

try:
    import yaml
except ImportError:  # pragma: no cover - bootstrap handles this in supported installs
    yaml = None

STATUS_PASS = "pass"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"
STATUS_SKIP = "skip"
STATUSES = frozenset({STATUS_PASS, STATUS_WARN, STATUS_FAIL, STATUS_SKIP})
_STATUS_ORDER = {STATUS_PASS: 0, STATUS_SKIP: 0, STATUS_WARN: 1, STATUS_FAIL: 2}
_PARSE_SUFFIXES = frozenset({".json", ".yaml", ".yml", ".toml"})


@dataclass(frozen=True, slots=True)
class CheckItem:
    group: str
    id: str
    status: str
    message: str
    hint: str = ""

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"unsupported doctor status: {self.status}")


@dataclass(slots=True)
class DoctorReport:
    profile: str
    tool: Optional[str]
    risk: str
    items: list[CheckItem] = field(default_factory=list)

    def add(self, group: str, id_: str, status: str, message: str, hint: str = "") -> None:
        """Create one already-sanitized canonical check for every renderer."""
        self.items.append(
            CheckItem(
                sanitize_for_terminal(group),
                sanitize_for_terminal(id_),
                status,
                sanitize_for_terminal(message),
                sanitize_for_terminal(hint),
            )
        )

    def worst(self) -> str:
        if any(item.status == STATUS_FAIL for item in self.items):
            return STATUS_FAIL
        if any(item.status == STATUS_WARN for item in self.items):
            return STATUS_WARN
        return STATUS_PASS

    def exit_code(self, fail_on: str = "fail") -> int:
        return exit_code(self, fail_on)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose unified agents environment")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--tool", default=None, choices=[*TOOLS])
    parser.add_argument("--deep", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--verbose", action="store_true", help="文本模式展开全部分组详情")
    parser.add_argument("--fail-on", choices=["fail", "warn"], default="fail")
    parser.add_argument("--root", type=Path, default=None)
    return parser.parse_args(argv)


def cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run_cmd(cmd: Sequence[str], timeout: float = 15.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(list(cmd), capture_output=True, text=True, timeout=timeout, check=False)
        return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def run_mcp_browser_probe(cmd: Sequence[str], timeout: float = 30.0) -> tuple[int, str]:
    """Start a stdio MCP server and trigger a minimal browser launch."""
    try:
        proc = subprocess.Popen(
            list(cmd), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1,
        )
    except OSError as exc:
        return 127, str(exc)
    assert proc.stdin is not None and proc.stdout is not None and proc.stderr is not None
    out_q: queue.Queue[str] = queue.Queue()
    err_lines: list[str] = []

    def read_stdout() -> None:
        for line in proc.stdout:
            out_q.put(line)

    def read_stderr() -> None:
        for line in proc.stderr:
            err_lines.append(line)

    threading.Thread(target=read_stdout, daemon=True).start()
    threading.Thread(target=read_stderr, daemon=True).start()

    def send(value: Mapping[str, Any]) -> None:
        proc.stdin.write(json.dumps(value) + "\n")
        proc.stdin.flush()

    def receive(id_: int, deadline: float) -> dict[str, Any]:
        while time.monotonic() < deadline:
            try:
                line = out_q.get(timeout=0.25)
            except queue.Empty:
                if proc.poll() is not None:
                    break
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if message.get("id") == id_:
                return message
        raise TimeoutError(f"MCP response timeout for id={id_}")

    deadline = time.monotonic() + timeout
    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "agents-doctor", "version": "1"},
        }})
        initialized = receive(1, deadline)
        if "error" in initialized:
            return 1, json.dumps(initialized["error"], ensure_ascii=False)
        send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
            "name": "browser_navigate", "arguments": {"url": "about:blank"},
        }})
        navigated = receive(2, deadline)
        if navigated.get("result", {}).get("isError") or "error" in navigated:
            return 1, json.dumps(navigated, ensure_ascii=False)
        send({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
            "name": "browser_snapshot", "arguments": {"depth": 1},
        }})
        snapshot = receive(3, deadline)
        if snapshot.get("result", {}).get("isError") or "error" in snapshot:
            return 1, json.dumps(snapshot, ensure_ascii=False)
        return 0, "MCP browser navigate/snapshot ok"
    except (BrokenPipeError, TimeoutError) as exc:
        return 1, f"{exc}; {''.join(err_lines)[-300:]}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def check_env(cat: Catalog, report: DoctorReport, profile: str) -> None:
    for name, meta in (cat.env_schema.get("variables") or {}).items():
        profiles = meta.get("profiles") or []
        if profiles and profile not in profiles:
            continue
        tools = meta.get("tools")
        if tools and report.tool and report.tool not in tools:
            continue
        present = bool(os.environ.get(name))
        if present:
            suffix = "（敏感值已隐藏）" if meta.get("sensitive") else ""
            report.add("env", name, STATUS_PASS, f"{name} 已设置{suffix}")
        elif meta.get("required"):
            report.add("env", name, STATUS_FAIL, f"{name} 未设置", str(meta.get("setup_hint") or ""))
        else:
            report.add("env", name, STATUS_WARN, f"{name} 未设置（可选）", str(meta.get("setup_hint") or ""))


def check_tools(cat: Catalog, report: DoctorReport, profile: str) -> None:
    for name, meta in (cat.tools.get("tools") or {}).items():
        profiles = meta.get("profiles") or []
        if profiles and profile not in profiles:
            continue
        command = meta.get("command") or name
        if cmd_exists(command):
            version = ""
            if meta.get("version_cmd"):
                code, output = run_cmd(meta["version_cmd"], timeout=8)
                if code == 0 and output:
                    version = " — " + output.splitlines()[0][:120]
            report.add("tools", name, STATUS_PASS, f"{command} 可用{version}")
        else:
            status = STATUS_FAIL if meta.get("required") else STATUS_WARN
            suffix = "" if status == STATUS_FAIL else "（可选）"
            report.add("tools", name, status, f"{command} 未找到{suffix}", str(meta.get("install_hint") or ""))


def _record_state(
    report: DoctorReport,
    group: str,
    check_id: str,
    category: str,
    target: str,
    detail: str = "",
) -> str:
    status = {
        "missing": STATUS_WARN,
        "changed": STATUS_WARN,
        "stale": STATUS_WARN,
        "unowned": STATUS_WARN,
        "permission": STATUS_FAIL,
        "malformed": STATUS_FAIL,
        "link-boundary": STATUS_FAIL,
        "conflict": STATUS_FAIL,
    }[category]
    hint = ""
    if category in {"missing", "changed", "stale", "permission"}:
        hint = "运行 scripts/agents/sync.sh all --dry-run，确认后再同步"
    elif category == "unowned":
        hint = "保留未托管内容；如需接管请先显式审查并备份"
    elif category == "conflict":
        hint = "保留本机修改；先审查差异并显式解决，禁止静默覆盖"
    elif category == "malformed":
        hint = "修复格式后重试；doctor 未读取到的内容不会被覆盖"
    elif category == "link-boundary":
        hint = "移除意外软链并恢复 HOME 下真实目录/文件"
    message = f"{category}: {target}"
    if detail:
        message += f" ({detail})"
    report.add(group, check_id, status, message, hint)
    return status


def _counts_message(counts: Mapping[str, int]) -> str:
    order = ("managed", "missing", "changed", "stale", "unowned", "conflict", "permission", "malformed")
    return " ".join(f"{name}={counts.get(name, 0)}" for name in order)


def _check_skills_plan(
    root: Path,
    report: DoctorReport,
    *,
    home: Path,
    state_home: Path | None,
    renderer: Callable[[Path, str], bytes],
    target_root: Path,
    owner_prefix: str,
    label: str,
) -> None:
    """Reuse the runtime planner; never approximate manifest/target drift."""
    try:
        plan = compile_skills_plan(
            root,
            renderer,
            home=home,
            state_home=state_home,
            target_root=target_root,
            owner_prefix=owner_prefix,
            identity_prefix=(
                "agents/skills" if owner_prefix == "agents:skill:" else KIRO_SKILL_IDENTITY_PREFIX
            ),
        )
    except (AgentRuntimeError, OSError, SystemExit, ValueError) as exc:
        planner_id = "planner" if label == "shared" else f"{label}-planner"
        report.add("skills", planner_id, STATUS_FAIL, f"{label} planner unavailable: {exc}")
        return
    counts = Counter({name: 0 for name in (
        "managed", "missing", "changed", "stale", "unowned", "conflict", "permission", "malformed"
    )})
    statuses: list[str] = []
    if plan.manifest_status == "malformed":
        counts["malformed"] += 1
        if label == "shared":
            statuses.append(
                _record_state(
                    report,
                    "skills",
                    "manifest-malformed",
                    "malformed",
                    str(Path(plan.state_home) / "dotf" / "agents-manifest.json"),
                    "ownership manifest",
                )
            )
    for index, operation in enumerate(plan.operations):
        if operation.prior is not None:
            counts["managed"] += 1
        category: str | None = None
        detail = operation.conflict or operation.state
        if operation.state == "create" and operation.actual_state == "missing":
            category = "missing"
        elif operation.state == "update":
            category = "changed"
        elif operation.state == "prune":
            category = "stale"
        elif operation.state == "permission":
            category = "permission"
        elif operation.state == "conflict":
            reason = (operation.conflict or "").lower()
            if "without agents ownership" in reason:
                category = "unowned"
                counts["conflict"] += 1
            elif "symlink" in reason or "unsafe" in reason or operation.actual_state == "unsafe":
                category = "link-boundary"
                counts["conflict"] += 1
            elif "malformed" in reason:
                category = None  # represented once by manifest-malformed
            else:
                category = "conflict"
        if category is not None:
            count_name = "conflict" if category == "link-boundary" else category
            counts[count_name] += 1
            statuses.append(
                _record_state(
                    report,
                    "skills",
                    (
                        f"runtime-{category}-{index}"
                        if label == "shared"
                        else f"{label}-runtime-{category}-{index}"
                    ),
                    category,
                    operation.target,
                    detail,
                )
            )
    summary_status = max(statuses, key=lambda value: _STATUS_ORDER[value]) if statuses else STATUS_PASS
    sync_plan_id = "sync-plan" if label == "shared" else f"{label}-sync-plan"
    report.add("skills", sync_plan_id, summary_status, f"{label} runtime plan " + _counts_message(counts))


def check_skills_plan(root: Path, report: DoctorReport, *, home: Path, state_home: Path | None = None) -> None:
    """Check both the shared runtime and Kiro CLI's dedicated mirror."""
    _check_skills_plan(
        root,
        report,
        home=home,
        state_home=state_home,
        renderer=render_skill_bytes,
        target_root=home / ".agents" / "skills",
        owner_prefix="agents:skill:",
        label="shared",
    )
    _check_skills_plan(
        root,
        report,
        home=home,
        state_home=state_home,
        renderer=render_kiro_skill_bytes,
        target_root=kiro_skills_target(),
        owner_prefix=KIRO_SKILL_OWNER_PREFIX,
        label="kiro",
    )


def check_openspec_skills(report: DoctorReport, *, home: Path) -> None:
    """OpenSpec CLI skills are installed globally, not per project."""
    if openspec_command() is None:
        report.add(
            "skills",
            "openspec-cli",
            STATUS_SKIP,
            "openspec CLI 未安装，跳过全局 OpenSpec skills 检查",
            "dotf npm -i",
        )
        return
    propose = skills_target(home) / "openspec-propose" / "SKILL.md"
    if propose.is_file() and not propose.is_symlink():
        report.add("skills", "openspec-global", STATUS_PASS, f"OpenSpec skills 已安装到 {propose.parent.parent}")
        return
    report.add(
        "skills",
        "openspec-global",
        STATUS_WARN,
        f"openspec CLI 已安装，但全局缺少 {propose}",
        "运行 dotf agents -c 将 OpenSpec skills 装到 ~/.agents/skills",
    )


def check_mcp_plan(
    cat: Catalog,
    report: DoctorReport,
    profile: str,
    tool: str | None,
    deep: bool,
    *,
    home: Path,
    state_home: Path | None = None,
) -> None:
    targets = [tool] if tool else list(cat.vendor_matrix.adapter_tools)
    unsupported = [name for name in targets if not cat.vendor_matrix.capability(name).mcp]
    for name in unsupported:
        report.add("mcp", f"{name}-support", STATUS_SKIP, f"{name}: MCP adapter unsupported")
    selected = [name for name in targets if cat.vendor_matrix.capability(name).mcp]
    snapshot = read_mcp_manifest(home, state_home)
    if snapshot.status == "malformed":
        _record_state(report, "mcp", "manifest-malformed", "malformed", str((state_home or home / ".local" / "state") / "dotf" / "agents-mcp-manifest.json"), "ownership manifest")
    elif snapshot.status == "missing":
        report.add("mcp", "managed-manifest", STATUS_WARN, "MCP ownership manifest missing")
    else:
        report.add("mcp", "managed-manifest", STATUS_PASS, f"MCP ownership manifest valid managed={len(snapshot.manifest.items)}")
    try:
        plan = compile_sync_plan(cat, profile, selected, home=home, state_home=state_home)
    except (OSError, SystemExit, ValueError) as exc:
        report.add("mcp", "planner", STATUS_FAIL, f"MCP planner unavailable: {exc}")
        return

    counts = Counter({name: 0 for name in (
        "managed", "missing", "changed", "stale", "unowned", "conflict", "permission", "malformed"
    )})
    statuses: list[str] = []
    for item in plan.items:
        for version in item.declared_runtime_versions:
            report.add(
                "mcp", f"{item.adapter}-{version.resource_id}-version", STATUS_PASS,
                f"{version.resource_id} declared runtime {version.package}@{version.version}",
            )
        if item.actual_state == "malformed":
            counts["malformed"] += 1
            statuses.append(_record_state(report, "mcp", f"{item.adapter}-malformed", "malformed", item.target, "JSON parse category"))
            continue
        if item.actual_state == "unsafe":
            counts["conflict"] += 1
            statuses.append(_record_state(report, "mcp", f"{item.adapter}-link-boundary", "link-boundary", item.target, item.conflict or "unsafe target"))
            continue
        if item.state == "permission":
            counts["permission"] += 1
            statuses.append(_record_state(report, "mcp", f"{item.adapter}-permission", "permission", item.target, "sensitive mode is broader than declared"))
        if item.actual_state == "missing" and not item.entries:
            counts["missing"] += 1
            statuses.append(_record_state(report, "mcp", f"{item.adapter}-missing", "missing", item.target))
        for entry in item.entries:
            if entry.ownership == "owned":
                counts["managed"] += 1
            category: str | None = None
            if entry.ownership == "unowned":
                category = "unowned"
            elif entry.state == "create":
                category = "missing"
            elif entry.state == "update":
                category = "changed"
            elif entry.state == "prune":
                category = "stale"
            elif entry.state == "conflict":
                reason = (entry.conflict or "").lower()
                if "without ownership" in reason:
                    category = "unowned"
                    counts["conflict"] += 1
                elif "malformed" in reason:
                    category = None
                else:
                    category = "conflict"
            if category is not None:
                counts[category] += 1
                statuses.append(_record_state(
                    report, "mcp", f"{item.adapter}-{category}-{entry.server_id}", category,
                    item.target, f"server={entry.server_id}; {entry.conflict or entry.state}",
                ))
        selected_servers = cat.selected_servers(item.adapter, profile)
        for server_id, server in selected_servers.items():
            auth = server.get("auth") or {}
            env_name = auth.get("env")
            if env_name and not os.environ.get(env_name):
                report.add("mcp", f"{item.adapter}-{server_id}-env", STATUS_FAIL, f"{server_id} 需要环境变量 {env_name}", f"export {env_name}=...")
            if deep and server.get("url"):
                code, output = run_cmd(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "8", str(server["url"])], timeout=12)
                if code == 0 and output.strip().isdigit():
                    report.add("mcp", f"{item.adapter}-{server_id}-reach", STATUS_PASS, f"{server_id} 可达 HTTP {output.strip()}（未发送鉴权头）")
                else:
                    report.add("mcp", f"{item.adapter}-{server_id}-reach", STATUS_WARN, f"{server_id} 可达性检查失败", "检查网络或 URL；未发送 Authorization")
    summary_status = max(statuses, key=lambda value: _STATUS_ORDER[value]) if statuses else STATUS_PASS
    report.add("mcp", "sync-plan", summary_status, "MCP plan " + _counts_message(counts))


def _relative_rule_match(relative: str, rules: Iterable[str]) -> bool:
    path = PurePosixPath(relative)
    for rule in rules:
        normalized = str(PurePosixPath(rule))
        if relative == normalized or relative.startswith(normalized + "/") or path.match(normalized):
            return True
    return False


def _expand_home(value: str, home: Path) -> Path:
    if value == "~":
        return home
    if value.startswith("~/"):
        return home / value[2:]
    return Path(value).expanduser().absolute()


def _inside(path: Path, root: Path) -> bool:
    try:
        Path(os.path.realpath(path)).relative_to(Path(os.path.realpath(root)))
        return True
    except ValueError:
        return False


def _registry(root: Path) -> list[dict[str, Any]]:
    if registry_modules is None:
        raise RuntimeError("registry module unavailable")
    return registry_modules.load_registry(root / "modules.yaml")


def _walk_nofollow(directory: Path, ignored: Iterable[str] = ()) -> Iterable[tuple[Path, os.stat_result]]:
    stack = [(directory, "")]
    while stack:
        current, prefix = stack.pop()
        with os.scandir(current) as entries:
            for entry in sorted(entries, key=lambda item: item.name, reverse=True):
                relative = f"{prefix}/{entry.name}" if prefix else entry.name
                if _relative_rule_match(relative, ignored):
                    continue
                item = entry.stat(follow_symlinks=False)
                path = current / entry.name
                yield path, item
                if stat.S_ISDIR(item.st_mode) and not stat.S_ISLNK(item.st_mode):
                    stack.append((path, relative))


def _mode_is_broad(item: os.stat_result) -> bool:
    mode = stat.S_IMODE(item.st_mode)
    if stat.S_ISDIR(item.st_mode):
        return bool(mode & ~0o700)
    if stat.S_ISREG(item.st_mode):
        return bool(mode & ~0o600)
    return True


def check_config_boundaries(root: Path, report: DoctorReport, *, home: Path) -> None:
    """Audit deployment targets from registry metadata with lstat/nofollow semantics."""
    try:
        modules = _registry(root)
    except (OSError, SystemExit, ValueError, RuntimeError) as exc:
        report.add("security", "registry-boundaries", STATUS_FAIL, f"registry boundary audit unavailable: {exc}")
        return
    audited = 0
    findings = 0
    for module in modules:
        config = module.get("config")
        if not isinstance(config, dict):
            continue
        name = str(module.get("name") or "unknown")
        target = _expand_home(str(config.get("target") or ""), home)
        source_raw = str(config.get("source") or "")
        source = Path(source_raw) if Path(source_raw).is_absolute() else root / source_raw
        strategy = config.get("strategy")
        writable = config.get("writable") is True
        sensitive = config.get("sensitive") is True
        audited += 1
        try:
            components = lstat_components(home, target, missing_ok=True)
        except (OSError, ValueError) as exc:
            findings += 1
            report.add("security", f"config-{name}-boundary", STATUS_FAIL, f"link-boundary: {target} ({exc})", f"运行 dotf {name} -c --dry-run")
            continue
        symlink_components = [(path, item) for path, item in components if item is not None and stat.S_ISLNK(item.st_mode)]
        if symlink_components:
            link_path, _ = symlink_components[0]
            if strategy == "symlink" and not writable and not sensitive and link_path == target:
                try:
                    correct = Path(os.path.realpath(target)) == source.resolve(strict=True)
                except OSError:
                    correct = False
                status = STATUS_PASS if correct else STATUS_FAIL
                report.add("security", f"config-{name}-readonly-link", status, f"allowed read-only symlink {'matches source' if correct else 'has wrong source'}: {target}")
                findings += int(not correct)
            else:
                findings += 1
                points_repo = _inside(link_path, root)
                label = "repository-pointing writable/sensitive root symlink" if link_path == target and points_repo and (writable or sensitive) else "unexpected symlink in managed path"
                report.add("security", f"config-{name}-link-boundary", STATUS_FAIL, f"{label}: {link_path}", f"运行 dotf {name} -c --dry-run；迁移只 unlink 链接，不跟随内容")
            continue
        try:
            target_item = target.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            findings += 1
            report.add("security", f"config-{name}-lstat", STATUS_FAIL, f"cannot inspect target: {target} ({exc})")
            continue
        if stat.S_ISDIR(target_item.st_mode):
            ignored = tuple(config.get("preserve") or ()) + tuple(config.get("exclude") or ())
            try:
                for path, item in _walk_nofollow(target):
                    relative = path.relative_to(target).as_posix()
                    managed_path = not _relative_rule_match(relative, ignored)
                    if stat.S_ISLNK(item.st_mode) and managed_path:
                        findings += 1
                        report.add("security", f"config-{name}-internal-link", STATUS_FAIL, f"unexpected internal symlink: {path}", f"运行 dotf {name} -c --dry-run")
                    if sensitive and _mode_is_broad(item):
                        findings += 1
                        report.add("security", f"config-{name}-permission-{path.name}", STATUS_FAIL, f"broad sensitive mode {stat.S_IMODE(item.st_mode):04o}: {path}", f"收紧为目录 0700/普通文件 0600 后重试")
            except OSError as exc:
                findings += 1
                report.add("security", f"config-{name}-walk", STATUS_FAIL, f"cannot safely inspect managed tree: {target} ({exc})")
        if sensitive and _mode_is_broad(target_item):
            findings += 1
            report.add("security", f"config-{name}-root-permission", STATUS_FAIL, f"broad sensitive mode {stat.S_IMODE(target_item.st_mode):04o}: {target}", "收紧为目录 0700/普通文件 0600 后重试")
    report.add("security", "registry-boundaries", STATUS_PASS if findings == 0 else STATUS_FAIL, f"registry targets audited={audited} findings={findings}")


class _UniqueYamlLoader(yaml.SafeLoader if yaml is not None else object):  # type: ignore[misc]
    pass


if yaml is not None:
    def _unique_yaml_mapping(loader: Any, node: Any, deep: bool = False) -> dict[Any, Any]:
        result: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in result:
                raise ValueError(f"duplicate YAML key: {key}")
            result[key] = loader.construct_object(value_node, deep=deep)
        return result

    _UniqueYamlLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_yaml_mapping)


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _parse_document(path: Path, payload: bytes) -> None:
    text = payload.decode("utf-8")
    if path.suffix == ".json":
        json.loads(text, object_pairs_hook=_strict_json_object)
    elif path.suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise ValueError("YAML parser unavailable")
        yaml.load(text, Loader=_UniqueYamlLoader)
    elif path.suffix == ".toml":
        tomllib.loads(text)


def _source_format_targets(root: Path, home: Path, config: Mapping[str, Any]) -> Iterable[Path]:
    source_raw = str(config.get("source") or "")
    source = Path(source_raw) if Path(source_raw).is_absolute() else root / source_raw
    target = _expand_home(str(config.get("target") or ""), home)
    try:
        source_item = source.lstat()
    except OSError:
        return ()
    if stat.S_ISREG(source_item.st_mode) and source.suffix in _PARSE_SUFFIXES:
        return (target,)
    if not stat.S_ISDIR(source_item.st_mode):
        return ()
    ignored = tuple(config.get("exclude") or ())
    values: list[Path] = []
    for path, item in _walk_nofollow(source, ignored):
        if stat.S_ISREG(item.st_mode) and path.suffix in _PARSE_SUFFIXES:
            values.append(target / path.relative_to(source))
    return tuple(values)


def check_declared_formats(root: Path, report: DoctorReport, *, home: Path) -> None:
    """Parse existing declared JSON/YAML/TOML targets without ever printing content."""
    try:
        modules = _registry(root)
    except (OSError, SystemExit, ValueError, RuntimeError) as exc:
        report.add("security", "declared-formats", STATUS_FAIL, f"declared format audit unavailable: {exc}")
        return
    checked = malformed = 0
    seen: set[Path] = set()
    for module in modules:
        config = module.get("config")
        if not isinstance(config, dict):
            continue
        name = str(module.get("name") or "unknown")
        try:
            targets = _source_format_targets(root, home, config)
        except OSError as exc:
            report.add("security", f"format-{name}-source", STATUS_FAIL, f"cannot inspect declared source formats ({type(exc).__name__})")
            continue
        for target in targets:
            if target in seen:
                continue
            seen.add(target)
            try:
                assert_no_symlinks(home, target, missing_ok=False)
                fd = open_nofollow(home, target)
            except FileNotFoundError:
                continue
            except (OSError, PathBoundaryError):
                continue  # link-boundary audit owns this state
            try:
                chunks: list[bytes] = []
                while True:
                    block = os.read(fd, 1024 * 1024)
                    if not block:
                        break
                    chunks.append(block)
                payload = b"".join(chunks)
            finally:
                os.close(fd)
            checked += 1
            try:
                _parse_document(target, payload)
            except (UnicodeError, ValueError, json.JSONDecodeError, tomllib.TOMLDecodeError, Exception) as exc:
                # PyYAML exceptions do not share a stable base when bootstrap vendors it.
                malformed += 1
                report.add("security", f"format-{name}-{malformed}", STATUS_FAIL, f"malformed {target.suffix.lstrip('.').upper()}: {target} (parse category {type(exc).__name__}; content omitted)", "修复格式；原文件已保留")
    report.add("security", "declared-formats", STATUS_PASS if malformed == 0 else STATUS_FAIL, f"declared formats checked={checked} malformed={malformed}")


def _load_security_config(root: Path) -> Mapping[str, Any]:
    path = root / "agents" / "env" / "security.yaml"
    if yaml is None:
        raise ValueError("YAML parser unavailable")
    value = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueYamlLoader)
    if not isinstance(value, dict):
        raise ValueError("security config is not an object")
    return value


def _state_home(home: Path) -> Path:
    configured = os.environ.get("XDG_STATE_HOME")
    return Path(configured).expanduser().absolute() if configured else home / ".local" / "state"


def _parse_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def check_sensitive_backups(
    security: Mapping[str, Any], report: DoctorReport, *, home: Path,
    now: datetime | None = None,
) -> None:
    policy = security.get("sensitive_backups") or {}
    retention = policy.get("retention_days")
    metadata_name = policy.get("metadata_filename")
    if type(retention) is not int or retention < 1 or not isinstance(metadata_name, str) or not metadata_name:
        report.add("security", "sensitive-backups", STATUS_FAIL, "malformed sensitive backup retention policy")
        return
    backup_root = _state_home(home) / "dotf" / "backups"
    try:
        root_item = backup_root.lstat()
    except FileNotFoundError:
        report.add("security", "sensitive-backups", STATUS_PASS, f"sensitive backup retention={retention}d metadata=0 expired=0")
        return
    if stat.S_ISLNK(root_item.st_mode) or not stat.S_ISDIR(root_item.st_mode):
        report.add("security", "sensitive-backups", STATUS_FAIL, f"backup root is not a real directory: {backup_root}")
        return
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    metadata_count = expired = malformed = 0
    try:
        entries = _walk_nofollow(backup_root)
        for path, item in entries:
            if path.name != metadata_name or not stat.S_ISREG(item.st_mode):
                continue
            metadata_count += 1
            try:
                fd = open_nofollow(backup_root, path)
                try:
                    payload = b""
                    while True:
                        block = os.read(fd, 65536)
                        if not block:
                            break
                        payload += block
                finally:
                    os.close(fd)
                value = json.loads(payload.decode("utf-8"), object_pairs_hook=_strict_json_object)
                if not isinstance(value, dict) or value.get("version") != 1 or type(value.get("sensitive")) is not bool:
                    raise ValueError("unsupported metadata schema")
                if value["sensitive"] is not True:
                    continue
                created = _parse_time(value.get("created_at"))
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
                malformed += 1
                report.add("security", f"backup-metadata-malformed-{metadata_count}", STATUS_FAIL, f"malformed backup metadata: {path} ({type(exc).__name__}; backup content not read)")
                continue
            age = current - created
            if age.total_seconds() > retention * 86400:
                expired += 1
                report.add("security", f"backup-expired-{metadata_count}", STATUS_WARN, f"expired sensitive backup metadata: {path} retention={retention}d (backup content not read)", "审查后删除对应过期备份目录")
    except OSError as exc:
        report.add("security", "sensitive-backups-walk", STATUS_FAIL, f"cannot safely inspect backup metadata: {type(exc).__name__}")
        return
    status = STATUS_FAIL if malformed else (STATUS_WARN if expired else STATUS_PASS)
    report.add("security", "sensitive-backups", status, f"sensitive backup retention={retention}d metadata={metadata_count} expired={expired} malformed={malformed}")


def check_private_runtime_artifacts(root: Path, security: Mapping[str, Any], report: DoctorReport) -> None:
    patterns = (security.get("private_runtime") or {}).get("forbidden_in_repo") or []
    findings: set[Path] = set()
    for pattern in patterns:
        if not isinstance(pattern, str):
            continue
        for path in root.glob(pattern):
            if ".git" not in path.parts:
                findings.add(path)
    for index, path in enumerate(sorted(findings, key=lambda value: value.as_posix())):
        try:
            relative = path.relative_to(root)
        except ValueError:
            relative = path
        report.add("security", f"private-runtime-{index}", STATUS_FAIL, f"private runtime artifact under repository path: {relative} (content not read)", "移到 XDG state/cache 或 HOME 私有目录")
    report.add("security", "private-runtime", STATUS_PASS if not findings else STATUS_FAIL, f"private runtime artifacts={len(findings)} content_reads=0")


def _git_tracked(root: Path, roots: Sequence[str]) -> tuple[str, ...]:
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", *roots],
        capture_output=True, check=False,
    )
    if proc.returncode != 0:
        raise OSError("git ls-files failed")
    return tuple(item.decode("utf-8") for item in proc.stdout.split(b"\0") if item)


def check_security_scan(root: Path, security: Mapping[str, Any], report: DoctorReport) -> None:
    scan = security.get("scan") or {}
    rule_version = scan.get("rule_version")
    roots = scan.get("tracked_roots") or []
    suffixes = set(scan.get("text_extensions") or [])
    excluded = tuple(scan.get("exclude") or ())
    if type(rule_version) is not int or rule_version < 1:
        report.add("security", "tracked-scan", STATUS_FAIL, "malformed tracked scan rule version")
        return
    patterns: list[tuple[str, re.Pattern[str], str]] = []
    for raw in security.get("sensitive_patterns") or []:
        try:
            patterns.append((str(raw["name"]), re.compile(str(raw["pattern"])), str(raw["severity"])))
        except (KeyError, re.error, TypeError) as exc:
            report.add("security", "scan-pattern", STATUS_FAIL, f"invalid security scan rule: {type(exc).__name__}")
    try:
        tracked = _git_tracked(root, tuple(str(value) for value in roots))
    except OSError:
        report.add("security", "tracked-scan", STATUS_WARN, f"tracked security scan unavailable rule_version={rule_version} scanned=0 skipped=0")
        return
    scanned = skipped = findings = 0
    for relative in tracked:
        path = root / relative
        if any(fnmatch.fnmatchcase(relative, rule) for rule in excluded):
            skipped += 1
            continue
        try:
            item = path.lstat()
        except OSError:
            skipped += 1
            continue
        if stat.S_ISLNK(item.st_mode) or not stat.S_ISREG(item.st_mode) or path.suffix.lower() not in suffixes:
            skipped += 1
            continue
        try:
            fd = open_nofollow(root, path)
            try:
                chunks: list[bytes] = []
                while True:
                    block = os.read(fd, 1024 * 1024)
                    if not block:
                        break
                    chunks.append(block)
                payload = b"".join(chunks)
            finally:
                os.close(fd)
            if b"\0" in payload:
                skipped += 1
                continue
            text = payload.decode("utf-8")
        except (OSError, UnicodeError):
            skipped += 1
            continue
        scanned += 1
        for name, pattern, severity in patterns:
            match = pattern.search(text)
            if match is None:
                continue
            fragment = match.group(0)
            if "${" in fragment or "{env:" in fragment:
                continue
            findings += 1
            status = STATUS_FAIL if severity == "fail" else STATUS_WARN
            report.add("security", f"tracked-{name}-{findings}", status, f"sensitive rule {name} matched tracked source: {relative} (value omitted)", "移到外置 overlay/环境变量并清理 Git 历史")
    boundary_status = STATUS_FAIL if any(item.status == STATUS_FAIL and item.id.startswith("tracked-") for item in report.items) else (STATUS_WARN if findings else STATUS_PASS)
    report.add("security", "tracked-scan", boundary_status, f"tracked security scan rule_version={rule_version} scanned={scanned} skipped={skipped} findings={findings}")


def check_browser(cat: Catalog, report: DoctorReport, profile: str, deep: bool) -> None:
    pdata = cat.resolve_profile(profile)
    if "browser" not in (pdata.get("modules") or []) and profile not in ("browser", "full"):
        report.add("browser", "profile", STATUS_SKIP, f"profile={profile} 未启用 browser 模块")
        return
    report.add("browser", "risk", STATUS_WARN, "browser 自动化为 high risk（隔离 profile；勿提交截图/trace）", "artifact_dir 使用仓库外缓存目录；不要提交截图、trace、downloads 或 profile")
    browser = cat.browser_local()
    if browser.get("use_real_profile") or browser.get("cdp_endpoint") or os.environ.get("AGENT_ENV_CDP_ENDPOINT"):
        report.add("browser", "real-profile", STATUS_WARN, "已配置真实浏览器 profile / CDP；可能暴露登录态")
    else:
        report.add("browser", "isolate", STATUS_PASS, "默认隔离 profile 已配置（本机路径已隐藏）")
    provider = browser.get("provider") or browser.get("default_provider") or "playwright"
    meta = (browser.get("providers") or {}).get(provider) or {}
    for check in meta.get("checks") or []:
        check_id = check.get("id", "check")
        kind = check.get("kind")
        if kind == "command":
            command = check.get("command")
            status = STATUS_PASS if command and cmd_exists(command) else STATUS_FAIL
            report.add("browser", f"{provider}-{check_id}", status, f"{command} {'可用' if status == STATUS_PASS else '未找到'}", "" if status == STATUS_PASS else str(check.get("hint") or ""))
        elif kind == "hint":
            report.add("browser", f"{provider}-{check_id}", STATUS_WARN, str(check.get("hint") or check_id))
        elif kind in {"env_or_local", "optional_path"}:
            found = any(os.environ.get(key) or browser.get(key) for key in (check.get("keys") or []))
            if found:
                report.add("browser", f"{provider}-{check_id}", STATUS_PASS, f"{check_id} 已配置")
            elif kind == "optional_path":
                report.add("browser", f"{provider}-{check_id}", STATUS_SKIP, f"{check_id} 未配置（可选）")
            else:
                report.add("browser", f"{provider}-{check_id}", STATUS_FAIL, f"{check_id} 未配置", str(check.get("hint") or ""))
    if not deep:
        return
    command: list[str] = []
    if provider == "playwright":
        selected_tool = report.tool if report.tool in TOOLS else "cursor"
        server = cat.selected_servers(selected_tool or "cursor", profile).get("playwright")
        if server:
            command = [str(server["command"]), *[str(arg) for arg in (server.get("args") or [])]]
            code, output = run_mcp_browser_probe(command, timeout=45)
        else:
            code, output = 1, "playwright server is not selected"
    else:
        command = [str(value) for value in ((meta.get("deep_check") or {}).get("command") or [])]
        code, output = run_cmd(command, timeout=60) if command else (0, "skip")
    if command:
        if code == 0:
            report.add("browser", "deep-launch", STATUS_PASS, "provider 最小启动检查通过")
        else:
            report.add("browser", "deep-launch", STATUS_FAIL, f"provider 深度检查失败: {output[:200]}")


def check_agents(root: Path, report: DoctorReport) -> None:
    script = root / "scripts" / "agents" / "sync.sh"
    status = STATUS_PASS if script.is_file() else STATUS_WARN
    report.add("agents", "sync-script", status, "agents sync 脚本存在" if status == STATUS_PASS else "找不到 scripts/agents/sync.sh")


def _safe_check(report: DoctorReport, group: str, check_id: str, callback: Callable[[], None]) -> None:
    before = len(report.items)
    try:
        callback()
    except (KeyboardInterrupt, GeneratorExit):
        raise
    except BaseException as exc:
        report.add(group, check_id, STATUS_FAIL, f"check unavailable: {type(exc).__name__}: {exc}")
    if len(report.items) == before:
        report.add(group, check_id, STATUS_SKIP, "check produced no result")


def build_report(args: argparse.Namespace) -> DoctorReport:
    root = args.root.resolve() if args.root else Path(__file__).resolve().parents[2]
    home = Path.home().expanduser().absolute()
    try:
        cat = Catalog(root)
        profile = args.profile or cat.default_profile()
        profile_data = cat.resolve_profile(profile)
        report = DoctorReport(str(profile_data["id"]), args.tool, str(profile_data.get("risk") or "low"))
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, GeneratorExit)):
            raise
        report = DoctorReport(args.profile or "unavailable", args.tool, "unknown")
        report.add("agents", "catalog-malformed", STATUS_FAIL, f"malformed Agent JSON/YAML/TOML catalog or overlay: {exc}")
        _safe_check(report, "security", "registry-boundaries-unavailable", lambda: check_config_boundaries(root, report, home=home))
        _safe_check(report, "security", "declared-formats-unavailable", lambda: check_declared_formats(root, report, home=home))
        try:
            security = _load_security_config(root)
        except BaseException as security_exc:
            report.add("security", "config-malformed", STATUS_FAIL, f"malformed security YAML: {security_exc}")
        else:
            _safe_check(report, "security", "sensitive-backups-unavailable", lambda: check_sensitive_backups(security, report, home=home))
            _safe_check(report, "security", "private-runtime-unavailable", lambda: check_private_runtime_artifacts(root, security, report))
            _safe_check(report, "security", "tracked-scan-unavailable", lambda: check_security_scan(root, security, report))
        check_agents(root, report)
        return report

    profile = report.profile
    _safe_check(report, "env", "environment", lambda: check_env(cat, report, profile))
    _safe_check(report, "tools", "runtime-tools", lambda: check_tools(cat, report, profile))
    _safe_check(report, "mcp", "sync-plan-unavailable", lambda: check_mcp_plan(cat, report, profile, args.tool, args.deep, home=home))
    _safe_check(report, "skills", "sync-plan-unavailable", lambda: check_skills_plan(root, report, home=home))
    _safe_check(report, "skills", "openspec-unavailable", lambda: check_openspec_skills(report, home=home))
    _safe_check(report, "browser", "browser-unavailable", lambda: check_browser(cat, report, profile, args.deep))
    _safe_check(report, "security", "registry-boundaries-unavailable", lambda: check_config_boundaries(root, report, home=home))
    _safe_check(report, "security", "declared-formats-unavailable", lambda: check_declared_formats(root, report, home=home))
    _safe_check(report, "security", "sensitive-backups-unavailable", lambda: check_sensitive_backups(cat.security, report, home=home))
    _safe_check(report, "security", "private-runtime-unavailable", lambda: check_private_runtime_artifacts(root, cat.security, report))
    _safe_check(report, "security", "tracked-scan-unavailable", lambda: check_security_scan(root, cat.security, report))
    check_agents(root, report)
    return report


def summarize(items: list[CheckItem]) -> dict[str, Any]:
    counts = Counter(item.status for item in items)
    status = STATUS_FAIL if counts[STATUS_FAIL] else (STATUS_WARN if counts[STATUS_WARN] else STATUS_PASS)
    return {
        "status": status,
        "counts": {
            "pass": counts[STATUS_PASS], "warn": counts[STATUS_WARN],
            "fail": counts[STATUS_FAIL], "skip": counts[STATUS_SKIP], "total": len(items),
        },
    }


def build_next_steps(items: list[CheckItem]) -> list[str]:
    seen: set[str] = set()
    steps: list[str] = []
    for item in items:
        if item.status not in {STATUS_WARN, STATUS_FAIL} or not item.hint:
            continue
        if item.hint not in seen:
            seen.add(item.hint)
            steps.append(item.hint)
    return steps


def canonical_payload(report: DoctorReport) -> dict[str, Any]:
    payload = {
        "profile": report.profile,
        "tool": report.tool,
        "risk": report.risk,
        "summary": summarize(report.items),
        "problems": [asdict(item) for item in report.items if item.status in {STATUS_WARN, STATUS_FAIL}],
        "next_steps": build_next_steps(report.items),
        "checks": [asdict(item) for item in report.items],
        "exit_status_meaning": {
            "0": "no fail (warn/skip allowed unless --fail-on warn)",
            "1": "one or more fail (or warn if --fail-on warn)",
        },
    }
    return payload


def format_json(report: DoctorReport) -> str:
    return json.dumps(canonical_payload(report), indent=2, ensure_ascii=False) + "\n"


def format_text(report: DoctorReport, verbose: bool = False) -> str:
    payload = canonical_payload(report)
    summary = payload["summary"]
    lines = [
        f"agents doctor  profile={payload['profile']}  risk={payload['risk']}  tool={payload['tool'] or '*'}",
        "", "== summary ==", f"  status: {summary['status']}",
        "  counts: " + ", ".join(f"{key}={value}" for key, value in summary["counts"].items()), "",
        "== problems ==",
    ]
    problems = payload["problems"]
    if not problems:
        lines.append("  (none)")
    else:
        for item in problems:
            suffix = f"  → {item['hint']}" if item.get("hint") else ""
            lines.append(f"  [{item['status']}] {item['group']}/{item['id']}: {item['message']}{suffix}")
    if payload["next_steps"]:
        lines.extend(["", "== next_steps ==", *[f"  - {step}" for step in payload["next_steps"]]])
    if verbose:
        lines.extend(["", "== checks =="])
        groups: dict[str, list[dict[str, Any]]] = {}
        for item in payload["checks"]:
            groups.setdefault(item["group"], []).append(item)
        for group, items in groups.items():
            lines.append(f"[{group}]")
            for item in items:
                suffix = f"  hint: {item['hint']}" if item.get("hint") else ""
                lines.append(f"  {item['status']:4}  {item['id']}: {item['message']}{suffix}")
    else:
        lines.extend(["", "（使用 --verbose 查看全量 checks）"])
    return "\n".join(lines)


def exit_code(report: DoctorReport, fail_on: str) -> int:
    statuses = {item.status for item in report.items}
    if STATUS_FAIL in statuses or (fail_on == "warn" and STATUS_WARN in statuses):
        return 1
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    report = build_report(args)
    if args.json:
        sys.stdout.write(format_json(report))
    else:
        print(format_text(report, verbose=args.verbose))
    return exit_code(report, args.fail_on)


if __name__ == "__main__":
    raise SystemExit(main())
