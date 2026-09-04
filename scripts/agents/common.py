#!/usr/bin/env python3
"""agents/env 共享加载、合并与校验逻辑。"""

from __future__ import annotations

import copy
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# agents/ 下运行时把 scripts/ 加入 path，复用无感安装
_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from catalog import (  # noqa: E402
    CatalogError,
    load_catalog_documents,
    load_vendor_matrix,
)
from dotf_core.overlays import (  # noqa: E402
    OverlayCatalog,
    OverlayError,
    load_overlays,
)

_DEFAULT_ROOT = Path(__file__).resolve().parents[2]
TOOLS = load_vendor_matrix(_DEFAULT_ROOT).cli_tools
# 生成配置中允许保留的 env 占位符形式
PLACEHOLDER_OK = re.compile(
    r"(\$\{[A-Z][A-Z0-9_]*\}|\{env:[A-Z][A-Z0-9_]*\})"
)


def die(msg: str, code: int = 1) -> None:
    raise SystemExit(f"error: {msg}")


def repo_root_from(here: Path) -> Path:
    return here.resolve().parents[2]


def agent_env_dir(root: Path) -> Path:
    return root / "agents" / "env"



def deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for key, val in overlay.items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = deep_merge(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out


class Catalog:
    def __init__(self, root: Path, *, include_overlays: bool = True):
        self.root = root
        self.env_dir = agent_env_dir(root)
        try:
            documents = load_catalog_documents(root)
        except CatalogError as exc:
            die(f"catalog 校验失败: {exc}")
        self.manifest = documents.manifest
        self.env_schema = documents.env_schema
        self.tools = documents.tools
        self.security = documents.security
        self.browser = documents.browser
        self.servers_doc = documents.servers
        self.profiles = documents.profiles
        self.vendor_matrix = documents.vendors
        if include_overlays:
            try:
                self.overlays = load_overlays(
                    repo_root=root,
                    catalog=OverlayCatalog(
                        profiles=frozenset(self.profiles),
                        servers=frozenset(self.servers),
                        tools=frozenset(self.manifest.get("tools") or TOOLS),
                    ),
                )
            except OverlayError as exc:
                die(f"overlay 校验失败: {exc}")
            self.local = self.overlays.agents
        else:
            # Explicit repository generation must depend only on committed safe
            # catalog sources, never machine overlays, legacy locals, or secrets.
            self.overlays = None
            self.local = {}
        self.errors: List[str] = []
        self.validate()

    @property
    def servers(self) -> Dict[str, Dict[str, Any]]:
        return self.servers_doc["servers"]

    def default_profile(self) -> str:
        if isinstance(self.local.get("profile"), str):
            return self.local["profile"]
        return str(self.manifest["default_profile"])

    def validate(self) -> None:
        # Committed documents were validated as one cross-referenced catalog before
        # overlays were loaded. Only the external overlay can alter this selection.
        profile = self.default_profile()
        if profile not in self.profiles:
            die(f"overlay 引用未知 profile: {profile}")
        self.errors = []

    def resolve_profile(self, profile: Optional[str] = None) -> Dict[str, Any]:
        name = profile or self.default_profile()
        if name not in self.profiles:
            die(f"未知 profile: {name}（可选: {', '.join(sorted(self.profiles))}）")
        return self.profiles[name]

    def module_supports_tool(self, module: str, tool: str) -> bool:
        if module == "mcp":
            return self.vendor_matrix.capability(tool).mcp
        mods = self.manifest.get("modules") or {}
        mod = mods.get(module) or {}
        if mod.get("enabled") is False:
            return False
        exclude = set(mod.get("exclude") or [])
        if tool in exclude:
            return False
        allowed = mod.get("tools")
        if allowed is not None and tool not in allowed:
            return False
        unsupported = (self.manifest.get("unsupported") or {}).get(tool) or {}
        if unsupported.get(module) == "skip":
            return False
        return True

    def selected_servers(
        self, tool: str, profile: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        if not self.module_supports_tool("mcp", tool):
            return {}
        pdata = self.resolve_profile(profile)
        wanted = list(pdata.get("mcp_servers") or [])
        local_disabled = set(self.local.get("disabled_servers") or [])
        local_enabled = list(self.local.get("enabled_servers") or [])
        for sid in local_enabled:
            if sid not in wanted:
                wanted.append(sid)
        exclude_tool = (
            ((self.local.get("exclude") or {}).get(tool) or {}).get("servers") or []
        )
        local_disabled |= set(exclude_tool)

        out: Dict[str, Dict[str, Any]] = {}
        for sid in wanted:
            if sid in local_disabled:
                continue
            srv = self.servers.get(sid)
            if not srv:
                die(f"profile 引用未知 server: {sid}")
            tools = srv.get("tools") or list(TOOLS)
            if tool not in tools:
                continue
            profiles = srv.get("profiles") or []
            pname = pdata["id"]
            if profiles and pname not in profiles and sid not in local_enabled:
                continue
            # high risk browser servers：仅 browser/full，或 local 显式 enabled
            if srv.get("risk") == "high" and pname not in ("browser", "full"):
                if sid not in local_enabled:
                    continue
            cfg = copy.deepcopy(srv)
            if cfg.get("browser_provider") == "playwright":
                cfg = self._apply_browser_args(cfg)
            out[sid] = cfg
        return out

    def browser_local(self) -> Dict[str, Any]:
        base = copy.deepcopy(dict(self.browser))
        overlay = self.local.get("browser") or {}
        if isinstance(overlay, dict):
            base = deep_merge(base, overlay)
            # local 顶层键映射
            for key in (
                "provider",
                "headed",
                "browser_executable",
                "user_data_dir",
                "cdp_endpoint",
                "use_real_profile",
            ):
                if key in overlay:
                    base[key] = overlay[key]
        return base

    def _apply_browser_args(self, srv: Dict[str, Any]) -> Dict[str, Any]:
        b = self.browser_local()
        args = list(srv.get("args") or [])
        headed = bool(b.get("headed"))
        if not headed:
            harg = ((b.get("providers") or {}).get("playwright") or {}).get(
                "headless_arg", "--headless"
            )
            if harg and harg not in args:
                args.append(harg)
        user_data = b.get("user_data_dir") or b.get("isolated_user_data_dir")
        use_real = bool(b.get("use_real_profile"))
        if user_data and not use_real:
            user_data = os.path.expanduser(str(user_data))
            uarg = ((b.get("providers") or {}).get("playwright") or {}).get(
                "user_data_arg", "--user-data-dir"
            )
            # 避免重复
            if uarg not in args:
                args.extend([uarg, user_data])
        artifact_dir = b.get("artifact_dir")
        if artifact_dir and "--output-dir" not in args:
            args.extend(["--output-dir", os.path.expanduser(str(artifact_dir))])
        exe = b.get("browser_executable")
        if exe:
            args.extend(["--executable-path", os.path.expanduser(str(exe))])
        srv["args"] = args
        return srv

    def managed_server_ids(self) -> Set[str]:
        return set(self.servers.keys())

    def runtime_declarations(
        self,
        profile: Optional[str] = None,
        tools: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """Return pinned runtimes for the servers actually selected for these tools."""
        selected: Set[str] = set()
        for tool in tools or list(self.manifest.get("tools") or TOOLS):
            selected.update(self.selected_servers(tool, profile))

        declared: Dict[str, str] = {}
        for sid in sorted(selected):
            srv = self.servers.get(sid) or {}
            package = srv.get("package")
            version = srv.get("version")
            if package and version:
                declared[sid] = f"{package}@{version}"
        return declared


def auth_header(env_name: str, style: str) -> str:
    if style == "opencode":
        return f"Bearer {{env:{env_name}}}"
    return f"Bearer ${{{env_name}}}"


def lookup_env_value(name: str) -> str:
    """读取环境变量；当前进程没有时再尝试 senv。不打印值。"""
    val = os.environ.get(name) or ""
    if val:
        return val
    return _senv_get(name)


def _senv_get(name: str) -> str:
    import shutil
    import subprocess

    if not shutil.which("senv"):
        return ""
    try:
        proc = subprocess.run(
            ["senv", "env", "get", name],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def _placeholder_var(token: str) -> str:
    if token.startswith("${") and token.endswith("}"):
        return token[2:-1]
    if token.startswith("{env:") and token.endswith("}"):
        return token[len("{env:") : -1]
    return token


def expand_env_placeholders(obj: Any) -> Any:
    """把 ${VAR} / {env:VAR} 展开为 lookup_env_value(VAR)；缺值则失败。"""
    missing: List[str] = []

    def walk(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: walk(v) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v) for v in value]
        if isinstance(value, str):

            def repl(match: re.Match) -> str:
                var = _placeholder_var(match.group(0))
                found = lookup_env_value(var)
                if not found:
                    missing.append(var)
                    return match.group(0)
                return found

            return PLACEHOLDER_OK.sub(repl, value)
        return value

    out = walk(obj)
    if missing:
        names = ", ".join(f"${{{n}}}" for n in sorted(set(missing)))
        die(f"无法展开环境变量占位符: {names}（请 export 或通过 senv 提供）")
    return out


def collect_placeholders(obj: Any) -> List[str]:
    """收集对象中的 ${VAR} / {env:VAR} 占位符（去重、保序）。"""
    found: List[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)
        elif isinstance(value, str):
            found.extend(PLACEHOLDER_OK.findall(value))

    walk(obj)
    seen: Set[str] = set()
    out: List[str] = []
    for tok in found:
        if tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out


def entries_equivalent(expected: Any, actual: Any) -> bool:
    """比较 MCP 条目：expected 中的占位符可匹配 actual 里已展开的值。"""
    if isinstance(expected, dict) and isinstance(actual, dict):
        if expected.keys() != actual.keys():
            return False
        return all(entries_equivalent(expected[k], actual[k]) for k in expected)
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return False
        return all(entries_equivalent(a, b) for a, b in zip(expected, actual))
    if isinstance(expected, str) and isinstance(actual, str):
        if expected == actual:
            return True
        if not PLACEHOLDER_OK.search(expected):
            return False
        parts: List[str] = []
        pos = 0
        for match in PLACEHOLDER_OK.finditer(expected):
            parts.append(re.escape(expected[pos : match.start()]))
            parts.append(r".+")
            pos = match.end()
        parts.append(re.escape(expected[pos:]))
        try:
            return re.fullmatch("".join(parts), actual) is not None
        except re.error:
            return False
    return expected == actual


def render_server_for_tool(
    sid: str,
    srv: Dict[str, Any],
    tool: str,
    *,
    expand_secrets: bool = False,
) -> Dict[str, Any]:
    transport = srv.get("transport")
    auth = srv.get("auth") or {}
    env_name = auth.get("env")

    def finish(entry: Dict[str, Any]) -> Dict[str, Any]:
        if expand_secrets:
            return expand_env_placeholders(entry)
        return entry

    if tool == "kimi-code":
        # Kimi 不展开 ${ENV}；HTTP/SSE 用 bearerTokenEnvVar，stdio env 用 sh -c 映射
        # 见 https://www.kimi.com/code/docs/en/kimi-code-cli/customization/mcp.html
        if transport == "stdio":
            return _kimi_stdio_entry(srv)
        entry = {"url": srv["url"]}
        if env_name:
            entry["bearerTokenEnvVar"] = env_name
        return entry

    if tool in ("cursor", "zcode", "kiro"):
        if transport == "stdio":
            entry = {
                "command": srv["command"],
                "args": list(srv.get("args") or []),
            }
            # ZCode config.json 示例显式带 type: stdio
            if tool == "zcode":
                entry = {"type": "stdio", **entry}
            if srv.get("env"):
                entry["env"] = srv["env"]
            return finish(entry) if tool == "zcode" else entry
        # HTTP：cursor 用 streamable-http；kiro 文档无 type 字段；其余用 http
        if tool == "kiro":
            entry = {"url": srv["url"]}
            if env_name:
                entry["headers"] = {
                    "Authorization": auth_header(env_name, "kiro")
                }
            return entry
        tname = "streamable-http" if tool == "cursor" else "http"
        if transport == "http" and tool != "cursor":
            tname = "http"
        entry = {
            "type": tname,
            "url": srv["url"],
        }
        if env_name:
            entry["headers"] = {
                "Authorization": auth_header(env_name, tool)
            }
        return finish(entry) if tool == "zcode" else entry

    if tool == "opencode":
        if transport == "stdio":
            entry = {
                "type": "local",
                "command": [srv["command"], *list(srv.get("args") or [])],
            }
            if srv.get("env"):
                # OpenCode 只识别 {env:VAR} 占位符（见 opencode.ai/docs/mcp-servers）
                entry["environment"] = _to_opencode_env(srv["env"])
            return entry
        entry = {
            "type": "remote",
            "url": srv["url"],
        }
        if env_name:
            entry["headers"] = {
                "Authorization": auth_header(env_name, "opencode")
            }
        return entry

    die(f"无法为工具渲染 MCP: {tool}")


def _kimi_stdio_entry(srv: Dict[str, Any]) -> Dict[str, Any]:
    """Kimi 不展开 ${VAR}。stdio env 若含占位符，改成 sh -c 从进程环境映射。"""
    command = srv["command"]
    args = list(srv.get("args") or [])
    env = dict(srv.get("env") or {})
    if not env:
        return {"command": command, "args": args}

    if not any(isinstance(v, str) and PLACEHOLDER_OK.search(v) for v in env.values()):
        return {"command": command, "args": args, "env": env}

    assignments: List[str] = []
    for key, value in env.items():
        if isinstance(value, str) and PLACEHOLDER_OK.search(value):
            shell_v = re.sub(r"\$\{([A-Z][A-Z0-9_]*)\}", r'"$\1"', value)
            assignments.append(f"{key}={shell_v}")
        else:
            assignments.append(f"{key}={shlex.quote(str(value))}")
    quoted_cmd = " ".join(shlex.quote(x) for x in [command, *args])
    script = " ".join(assignments) + " exec " + quoted_cmd
    return {"command": "sh", "args": ["-c", script]}


def _to_opencode_env(env: Dict[str, Any]) -> Dict[str, Any]:
    """OpenCode 只识别 {env:VAR} 占位符；把 env 值里的 ${VAR} 转成 {env:VAR}。"""
    out: Dict[str, Any] = {}
    for k, v in env.items():
        if isinstance(v, str):
            v = re.sub(r"\$\{([A-Z][A-Z0-9_]*)\}", r"{env:\1}", v)
        out[k] = v
    return out
