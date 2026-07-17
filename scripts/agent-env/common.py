#!/usr/bin/env python3
"""agent-env 共享加载、合并与校验逻辑。"""

from __future__ import annotations

import copy
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "error: 需要 PyYAML（pip install pyyaml / apt install python3-yaml）"
    ) from exc

TOOLS = ("claude", "cursor", "opencode", "codex", "kimi-code")
KNOWN_PROFILES = ("coding", "research", "browser", "full")
SERVER_ALLOWED_KEYS = {
    "transport",
    "url",
    "command",
    "args",
    "auth",
    "tools",
    "profiles",
    "risk",
    "required_tools",
    "browser_provider",
    "env",
    "headers",
    "cwd",
}
# 生成配置中允许保留的 env 占位符形式
PLACEHOLDER_OK = re.compile(
    r"(\$\{[A-Z][A-Z0-9_]*\}|\{env:[A-Z][A-Z0-9_]*\})"
)
# 未解析的模板占位（我们自己的 {{...}}）
UNRESOLVED_TMPL = re.compile(r"\{\{[^{}]+\}\}")


def die(msg: str, code: int = 1) -> None:
    raise SystemExit(f"error: {msg}")


def repo_root_from(here: Path) -> Path:
    return here.resolve().parents[2]


def agent_env_dir(root: Path) -> Path:
    return root / "agent-env"


def load_yaml(path: Path) -> Any:
    if not path.is_file():
        die(f"缺少文件: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if data is not None else {}


def deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for key, val in overlay.items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = deep_merge(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out


def load_local_override(env_dir: Path) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    local_file = env_dir / "local.yaml"
    if local_file.is_file():
        data = load_yaml(local_file)
        if not isinstance(data, dict):
            die(f"local.yaml 必须是 mapping: {local_file}")
        merged = deep_merge(merged, data)
    local_dir = env_dir / "local"
    if local_dir.is_dir():
        for path in sorted(local_dir.glob("*.yaml")):
            data = load_yaml(path)
            if not isinstance(data, dict):
                die(f"local override 必须是 mapping: {path}")
            merged = deep_merge(merged, data)
    return merged


class Catalog:
    def __init__(self, root: Path):
        self.root = root
        self.env_dir = agent_env_dir(root)
        self.manifest = load_yaml(self.env_dir / "manifest.yaml")
        self.env_schema = load_yaml(self.env_dir / "env.schema.yaml")
        self.tools = load_yaml(self.env_dir / "tools.yaml")
        self.security = load_yaml(self.env_dir / "security.yaml")
        self.browser = load_yaml(self.env_dir / "browser.yaml")
        self.servers_doc = load_yaml(self.env_dir / "mcp" / "servers.yaml")
        self.local = load_local_override(self.env_dir)
        self.profiles = self._load_profiles()
        self.errors: List[str] = []
        self.validate()

    def _load_profiles(self) -> Dict[str, Dict[str, Any]]:
        profiles: Dict[str, Dict[str, Any]] = {}
        pdir = self.env_dir / "mcp" / "profiles"
        if not pdir.is_dir():
            die(f"缺少 profiles 目录: {pdir}")
        for path in sorted(pdir.glob("*.yaml")):
            data = load_yaml(path)
            if not isinstance(data, dict):
                die(f"profile 必须是 mapping: {path}")
            pid = data.get("id") or path.stem
            data["id"] = pid
            profiles[pid] = data
        return profiles

    @property
    def servers(self) -> Dict[str, Dict[str, Any]]:
        raw = self.servers_doc.get("servers") or {}
        if not isinstance(raw, dict):
            die("mcp/servers.yaml 的 servers 必须是 mapping")
        return raw

    def default_profile(self) -> str:
        if isinstance(self.local.get("profile"), str):
            return self.local["profile"]
        return str(self.manifest.get("default_profile") or "research")

    def validate(self) -> None:
        errs: List[str] = []
        known_tools = set(self.manifest.get("tools") or TOOLS)
        for t in known_tools:
            if t not in TOOLS:
                errs.append(f"manifest 声明未知工具: {t}")

        for pid, pdata in self.profiles.items():
            if pid not in KNOWN_PROFILES:
                errs.append(f"未知 profile 文件: {pid}")
            for sid in pdata.get("mcp_servers") or []:
                if sid not in self.servers:
                    errs.append(f"profile {pid} 引用未知 server: {sid}")

        seen: Set[str] = set()
        for sid, srv in self.servers.items():
            if sid in seen:
                errs.append(f"重复 server id: {sid}")
            seen.add(sid)
            if not isinstance(srv, dict):
                errs.append(f"server {sid} 必须是 mapping")
                continue
            unknown = set(srv.keys()) - SERVER_ALLOWED_KEYS
            if unknown:
                errs.append(f"server {sid} 含不支持字段: {sorted(unknown)}")
            for t in srv.get("tools") or []:
                if t not in TOOLS:
                    errs.append(f"server {sid} 未知工具: {t}")
            for p in srv.get("profiles") or []:
                if p not in self.profiles and p not in KNOWN_PROFILES:
                    errs.append(f"server {sid} 未知 profile: {p}")
            auth = srv.get("auth") or {}
            if auth:
                env_name = auth.get("env")
                if not env_name:
                    errs.append(f"server {sid} auth 缺少 env")
                else:
                    vars_ = (self.env_schema.get("variables") or {})
                    if env_name not in vars_:
                        errs.append(
                            f"server {sid} 引用未声明 env: {env_name}"
                        )
            transport = srv.get("transport")
            if transport in ("streamable-http", "http", "sse") and not srv.get("url"):
                errs.append(f"server {sid} HTTP transport 缺少 url")
            if transport == "stdio" and not srv.get("command"):
                errs.append(f"server {sid} stdio transport 缺少 command")

        dp = self.default_profile()
        if dp not in self.profiles:
            errs.append(f"默认 profile 不存在: {dp}")

        self.errors = errs
        if errs:
            die("manifest 校验失败:\n  - " + "\n  - ".join(errs))

    def resolve_profile(self, profile: Optional[str] = None) -> Dict[str, Any]:
        name = profile or self.default_profile()
        if name not in self.profiles:
            die(f"未知 profile: {name}（可选: {', '.join(sorted(self.profiles))}）")
        return self.profiles[name]

    def module_supports_tool(self, module: str, tool: str) -> bool:
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
        base = copy.deepcopy(self.browser)
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
        exe = b.get("browser_executable") or os.environ.get(
            "AGENT_ENV_BROWSER_EXECUTABLE"
        )
        if exe:
            args.extend(["--executable-path", os.path.expanduser(str(exe))])
        srv["args"] = args
        return srv

    def managed_server_ids(self) -> Set[str]:
        return set(self.servers.keys())


def auth_header(env_name: str, style: str) -> str:
    if style in ("cursor", "claude"):
        return f"Bearer ${{{env_name}}}"
    if style == "opencode":
        return f"Bearer {{env:{env_name}}}"
    return f"Bearer ${{{env_name}}}"


def render_server_for_tool(sid: str, srv: Dict[str, Any], tool: str) -> Dict[str, Any]:
    transport = srv.get("transport")
    auth = srv.get("auth") or {}
    env_name = auth.get("env")

    if tool == "kimi-code":
        # Kimi 不展开 headers 里的 ${ENV}；HTTP/SSE 用 bearerTokenEnvVar
        # 见 https://www.kimi.com/code/docs/en/kimi-code-cli/customization/mcp.html
        if transport == "stdio":
            entry: Dict[str, Any] = {
                "command": srv["command"],
                "args": list(srv.get("args") or []),
            }
            if srv.get("env"):
                entry["env"] = srv["env"]
            return entry
        entry = {"url": srv["url"]}
        if env_name:
            entry["bearerTokenEnvVar"] = env_name
        return entry

    if tool in ("cursor", "claude"):
        if transport == "stdio":
            entry = {
                "command": srv["command"],
                "args": list(srv.get("args") or []),
            }
            if srv.get("env"):
                entry["env"] = srv["env"]
            return entry
        # HTTP
        tname = "http" if tool == "claude" else "streamable-http"
        if transport == "http":
            tname = "http"
        entry = {
            "type": tname,
            "url": srv["url"],
        }
        if env_name:
            entry["headers"] = {
                "Authorization": auth_header(env_name, tool)
            }
        return entry

    if tool == "opencode":
        if transport == "stdio":
            entry = {
                "type": "local",
                "command": [srv["command"], *list(srv.get("args") or [])],
            }
            if srv.get("env"):
                entry["environment"] = srv["env"]
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


def check_no_unresolved(obj: Any, path: str = "$") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            check_no_unresolved(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            check_no_unresolved(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        if UNRESOLVED_TMPL.search(obj):
            die(f"未解析模板占位符: {path} = {obj}")


def atomic_write_json(path: Path, data: Any, dry_run: bool = False) -> str:
    import json
    import tempfile

    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    # 校验可解析
    json.loads(text)
    check_no_unresolved(data)
    if dry_run:
        return text
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp", text=True
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return text


def backup_file(path: Path, backup_root: Path) -> Optional[Path]:
    import time

    if not path.exists() and not path.is_symlink():
        return None
    backup_root.mkdir(parents=True, exist_ok=True)
    dest = backup_root / f"{path.name}-{int(time.time())}"
    import shutil

    if path.is_symlink() or path.is_file():
        shutil.copy2(path, dest, follow_symlinks=True)
    else:
        shutil.copytree(path, dest)
    return dest
