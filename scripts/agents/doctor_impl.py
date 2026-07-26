#!/usr/bin/env python3
"""agents/env 环境诊断：env / tools / mcp / browser / security / agents。"""

from __future__ import annotations

import argparse
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from common import (
    TOOLS,
    Catalog,
    render_server_for_tool,
    repo_root_from,
)

STATUS_PASS = "pass"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"
STATUS_SKIP = "skip"


def sanitize_browser_text(text: str, cat: Catalog) -> str:
    """Redact local browser paths/endpoints before adding them to reports."""
    out = text
    b = cat.browser_local()
    for key in (
        "user_data_dir",
        "isolated_user_data_dir",
        "artifact_dir",
        "browser_executable",
        "cdp_endpoint",
    ):
        val = b.get(key) or os.environ.get(f"AGENT_ENV_{key.upper()}")
        if not val:
            continue
        raw = str(val)
        expanded = os.path.expanduser(raw)
        for candidate in {raw, expanded}:
            if len(candidate) >= 4:
                out = out.replace(candidate, "<redacted-browser-local>")
    cdp = os.environ.get("AGENT_ENV_CDP_ENDPOINT")
    if cdp:
        out = out.replace(cdp, "<redacted-browser-local>")
    return out


@dataclass
class CheckItem:
    group: str
    id: str
    status: str
    message: str
    hint: str = ""


@dataclass
class DoctorReport:
    profile: str
    tool: Optional[str]
    risk: str
    items: List[CheckItem] = field(default_factory=list)

    def add(
        self,
        group: str,
        id_: str,
        status: str,
        message: str,
        hint: str = "",
    ) -> None:
        self.items.append(
            CheckItem(group=group, id=id_, status=status, message=message, hint=hint)
        )

    def worst(self) -> str:
        order = {STATUS_PASS: 0, STATUS_SKIP: 1, STATUS_WARN: 2, STATUS_FAIL: 3}
        worst = STATUS_PASS
        for it in self.items:
            if order.get(it.status, 0) > order.get(worst, 0):
                worst = it.status
        return worst

    def exit_code(self) -> int:
        w = self.worst()
        if w == STATUS_FAIL:
            return 1
        if w == STATUS_WARN:
            return 0  # warn 不失败；strict 可由调用方处理
        return 0


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Diagnose agents/env installation")
    p.add_argument("--profile", default=None, help="指定 profile")
    p.add_argument(
        "--tool",
        default=None,
        choices=[*TOOLS],
        help="仅检查某一目标工具的 MCP/适配相关项",
    )
    p.add_argument("--deep", action="store_true", help="启用远程/启动类深度检查")
    p.add_argument("--json", action="store_true", help="机器可读 JSON 输出")
    p.add_argument("--root", type=Path, default=None)
    return p.parse_args(argv)


def cmd_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run_cmd(cmd: Sequence[str], timeout: float = 15.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            list(cmd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def run_mcp_browser_probe(cmd: Sequence[str], timeout: float = 30.0) -> tuple[int, str]:
    """Start a stdio MCP server and trigger a minimal browser launch."""
    try:
        proc = subprocess.Popen(
            list(cmd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except OSError as exc:
        return 127, str(exc)

    assert proc.stdin is not None
    assert proc.stdout is not None
    assert proc.stderr is not None
    out_q: "queue.Queue[str]" = queue.Queue()
    err_lines: List[str] = []

    def read_stdout() -> None:
        for line in proc.stdout:
            out_q.put(line)

    def read_stderr() -> None:
        for line in proc.stderr:
            err_lines.append(line)

    threading.Thread(target=read_stdout, daemon=True).start()
    threading.Thread(target=read_stderr, daemon=True).start()

    def send(obj: Dict[str, Any]) -> None:
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()

    def recv_id(id_: int, deadline: float) -> Dict[str, Any]:
        while time.monotonic() < deadline:
            try:
                line = out_q.get(timeout=0.25)
            except queue.Empty:
                if proc.poll() is not None:
                    break
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == id_:
                return msg
        raise TimeoutError(f"MCP response timeout for id={id_}")

    deadline = time.monotonic() + timeout
    try:
        send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "agents-doctor", "version": "1"},
                },
            }
        )
        init = recv_id(1, deadline)
        if "error" in init:
            return 1, json.dumps(init["error"], ensure_ascii=False)
        send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        send(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "browser_navigate",
                    "arguments": {"url": "about:blank"},
                },
            }
        )
        nav = recv_id(2, deadline)
        if nav.get("result", {}).get("isError") or "error" in nav:
            return 1, json.dumps(nav, ensure_ascii=False)
        send(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "browser_snapshot", "arguments": {"depth": 1}},
            }
        )
        snap = recv_id(3, deadline)
        if snap.get("result", {}).get("isError") or "error" in snap:
            return 1, json.dumps(snap, ensure_ascii=False)
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
    variables = cat.env_schema.get("variables") or {}
    for name, meta in variables.items():
        profiles = meta.get("profiles") or []
        if profiles and profile not in profiles:
            continue
        tools = meta.get("tools")
        if tools and report.tool and report.tool not in tools:
            continue
        required = bool(meta.get("required"))
        present = bool(os.environ.get(name))
        # 永不打印值
        if present:
            report.add(
                "env",
                name,
                STATUS_PASS,
                f"{name} 已设置（敏感值已隐藏）" if meta.get("sensitive") else f"{name} 已设置",
            )
        elif required:
            report.add(
                "env",
                name,
                STATUS_FAIL,
                f"{name} 未设置",
                hint=str(meta.get("setup_hint") or ""),
            )
        else:
            report.add(
                "env",
                name,
                STATUS_WARN,
                f"{name} 未设置（可选）",
                hint=str(meta.get("setup_hint") or ""),
            )


def check_tools(cat: Catalog, report: DoctorReport, profile: str) -> None:
    tools = cat.tools.get("tools") or {}
    for name, meta in tools.items():
        profiles = meta.get("profiles") or []
        if profiles and profile not in profiles:
            continue
        required = bool(meta.get("required"))
        command = meta.get("command") or name
        if cmd_exists(command):
            ver = ""
            vcmd = meta.get("version_cmd")
            if vcmd:
                code, out = run_cmd(vcmd, timeout=8)
                if code == 0 and out:
                    ver = " — " + out.splitlines()[0][:120]
            report.add("tools", name, STATUS_PASS, f"{command} 可用{ver}")
        elif required:
            report.add(
                "tools",
                name,
                STATUS_FAIL,
                f"{command} 未找到",
                hint=str(meta.get("install_hint") or ""),
            )
        else:
            report.add(
                "tools",
                name,
                STATUS_WARN,
                f"{command} 未找到（可选）",
                hint=str(meta.get("install_hint") or ""),
            )


def check_mcp(
    cat: Catalog,
    report: DoctorReport,
    profile: str,
    tool: Optional[str],
    deep: bool,
) -> None:
    if cat.errors:
        report.add("mcp", "manifest", STATUS_FAIL, "; ".join(cat.errors))
        return
    report.add("mcp", "manifest", STATUS_PASS, "manifest / servers / profiles 校验通过")

    targets = [tool] if tool else list(TOOLS)
    for t in targets:
        if not cat.module_supports_tool("mcp", t):
            reason = (
                (cat.manifest.get("unsupported") or {})
                .get(t, {})
                .get("reason")
                or "manifest 排除或未启用"
            )
            report.add("mcp", f"{t}-support", STATUS_SKIP, f"{t}: {reason}")
            continue

        servers = cat.selected_servers(t, profile)
        report.add(
            "mcp",
            f"{t}-servers",
            STATUS_PASS,
            f"{t}: {len(servers)} managed servers ({', '.join(servers) or 'none'})",
        )
        for sid, srv in servers.items():
            auth = srv.get("auth") or {}
            env_name = auth.get("env")
            if env_name and not os.environ.get(env_name):
                report.add(
                    "mcp",
                    f"{t}-{sid}-env",
                    STATUS_FAIL,
                    f"{sid} 需要环境变量 {env_name}",
                    hint=f"export {env_name}=...",
                )
            risk = srv.get("risk", "low")
            if risk == "high":
                report.add(
                    "mcp",
                    f"{t}-{sid}-risk",
                    STATUS_WARN,
                    f"{sid} 风险等级: high",
                )

        # 漂移检查
        drift = _mcp_drift(cat, t, profile, servers)
        if drift is None:
            report.add("mcp", f"{t}-drift", STATUS_SKIP, f"{t}: 目标配置不存在，跳过漂移检查")
        elif drift:
            report.add(
                "mcp",
                f"{t}-drift",
                STATUS_WARN,
                f"{t}: 托管 MCP 与 agents/env 不一致: {', '.join(drift)}",
                hint="运行 scripts/agents/sync.sh --env-only " + t,
            )
        else:
            report.add("mcp", f"{t}-drift", STATUS_PASS, f"{t}: 托管 MCP 与源一致")

        if deep:
            for sid, srv in servers.items():
                url = srv.get("url")
                if not url:
                    continue
                # 轻量连通：不带 Authorization，避免泄露
                code, out = run_cmd(
                    ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "8", url],
                    timeout=12,
                )
                if code == 0 and out.strip().isdigit():
                    report.add(
                        "mcp",
                        f"{t}-{sid}-reach",
                        STATUS_PASS,
                        f"{sid} 可达 HTTP {out.strip()}（未发送鉴权头）",
                    )
                else:
                    report.add(
                        "mcp",
                        f"{t}-{sid}-reach",
                        STATUS_WARN,
                        f"{sid} 可达性检查失败",
                        hint="检查网络或 URL；未发送 Authorization",
                    )


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _mcp_drift(
    cat: Catalog,
    tool: str,
    profile: str,
    servers: Dict[str, Any],
) -> Optional[List[str]]:
    expected = {
        sid: render_server_for_tool(sid, srv, tool) for sid, srv in servers.items()
    }
    if tool == "cursor":
        data = _read_json(Path.home() / ".cursor" / "mcp.json")
        if data is None:
            return None
        actual = data.get("mcpServers") or {}
    elif tool == "claude":
        data = _read_json(Path.home() / ".claude" / ".mcp.json")
        if data is None:
            return None
        actual = data.get("mcpServers") or {}
    elif tool == "opencode":
        data = _read_json(
            cat.root / "agents" / "vendors" / "opencode" / "opencode.json"
        )
        if data is None:
            return None
        actual = data.get("mcp") or {}
    elif tool == "kimi-code":
        data = _read_json(Path.home() / ".kimi-code" / "mcp.json")
        if data is None:
            return None
        actual = data.get("mcpServers") or {}
    elif tool == "qoder":
        data = _read_json(Path.home() / ".qoder-cn" / "settings.json")
        if data is None:
            return None
        actual = data.get("mcpServers") or {}
    elif tool == "codebuddy-code":
        data = _read_json(Path.home() / ".codebuddy" / ".mcp.json")
        if data is None:
            return None
        actual = data.get("mcpServers") or {}
    elif tool == "zcode":
        data = _read_json(Path.home() / ".zcode" / "cli" / "config.json")
        if data is None:
            return None
        mcp = data.get("mcp") or {}
        actual = mcp.get("servers") or {} if isinstance(mcp, dict) else {}
    else:
        return None

    drift: List[str] = []
    for sid, exp in expected.items():
        if sid not in actual:
            drift.append(f"missing:{sid}")
        elif actual[sid] != exp:
            drift.append(f"changed:{sid}")
    for sid in cat.managed_server_ids():
        if sid in actual and sid not in expected:
            # 目标里仍有已禁用的托管 server
            drift.append(f"stale:{sid}")
    return drift


def check_browser(
    cat: Catalog,
    report: DoctorReport,
    profile: str,
    deep: bool,
) -> None:
    pdata = cat.resolve_profile(profile)
    if "browser" not in (pdata.get("modules") or []) and profile not in (
        "browser",
        "full",
    ):
        report.add(
            "browser",
            "profile",
            STATUS_SKIP,
            f"profile={profile} 未启用 browser 模块",
        )
        return

    report.add(
        "browser",
        "risk",
        STATUS_WARN,
        "browser 自动化为 high risk（隔离 profile；勿提交截图/trace）",
        hint="artifact_dir 使用仓库外缓存目录；不要提交截图、trace、downloads 或 profile",
    )

    b = cat.browser_local()
    if b.get("use_real_profile") or b.get("cdp_endpoint") or os.environ.get(
        "AGENT_ENV_CDP_ENDPOINT"
    ):
        report.add(
            "browser",
            "real-profile",
            STATUS_WARN,
            "已配置真实浏览器 profile / CDP；可能暴露登录态",
        )
    else:
        report.add(
            "browser",
            "isolate",
            STATUS_PASS,
            "默认隔离 profile 已配置（本机路径已隐藏）",
        )

    provider = b.get("provider") or b.get("default_provider") or "playwright"
    providers = b.get("providers") or {}
    meta = providers.get(provider) or {}
    for chk in meta.get("checks") or []:
        cid = chk.get("id", "check")
        kind = chk.get("kind")
        if kind == "command":
            cmd = chk.get("command")
            if cmd and cmd_exists(cmd):
                report.add("browser", f"{provider}-{cid}", STATUS_PASS, f"{cmd} 可用")
            else:
                report.add(
                    "browser",
                    f"{provider}-{cid}",
                    STATUS_FAIL,
                    f"{cmd} 未找到",
                    hint=str(chk.get("hint") or ""),
                )
        elif kind == "hint":
            report.add(
                "browser",
                f"{provider}-{cid}",
                STATUS_WARN,
                str(chk.get("hint") or cid),
            )
        elif kind in ("env_or_local", "optional_path"):
            keys = chk.get("keys") or []
            found = False
            for k in keys:
                if os.environ.get(k) or b.get(k):
                    found = True
                    break
            if found:
                report.add("browser", f"{provider}-{cid}", STATUS_PASS, f"{cid} 已配置")
            elif kind == "optional_path":
                report.add(
                    "browser",
                    f"{provider}-{cid}",
                    STATUS_SKIP,
                    f"{cid} 未配置（可选）",
                )
            else:
                report.add(
                    "browser",
                    f"{provider}-{cid}",
                    STATUS_FAIL,
                    f"{cid} 未配置",
                    hint=str(chk.get("hint") or ""),
                )

    if deep:
        cmd: List[str] = []
        if provider == "playwright":
            tool = report.tool if report.tool in TOOLS else "cursor"
            srv = cat.selected_servers(tool or "cursor", profile).get("playwright")
            if srv:
                cmd = [str(srv["command"]), *[str(a) for a in (srv.get("args") or [])]]
                code, out = run_mcp_browser_probe(cmd, timeout=45)
            else:
                code, out = 1, "playwright server is not selected for this profile/tool"
        else:
            deep_meta = meta.get("deep_check") or {}
            cmd = [str(x) for x in (deep_meta.get("command") or [])]
            code, out = run_cmd(cmd, timeout=60) if cmd else (0, "skip")
        if cmd:
            if code == 0:
                report.add(
                    "browser",
                    "deep-launch",
                    STATUS_PASS,
                    "provider 最小启动检查通过",
                )
            else:
                safe_out = sanitize_browser_text(out[:200], cat)
                report.add(
                    "browser",
                    "deep-launch",
                    STATUS_FAIL,
                    f"provider 深度检查失败: {safe_out}",
                    hint=str((meta.get("checks") or [{}])[-1].get("hint") or ""),
                )


def check_security(cat: Catalog, report: DoctorReport) -> None:
    patterns = []
    for p in cat.security.get("sensitive_patterns") or []:
        try:
            patterns.append(
                (
                    p.get("name", "pattern"),
                    re.compile(p.get("pattern") or r"(?!)"),
                    p.get("severity", "warn"),
                )
            )
        except re.error as exc:
            report.add("security", "pattern", STATUS_WARN, f"无效正则: {exc}")

    scan_roots = [
        cat.env_dir,
        cat.root / "agents" / "vendors" / "claude" / ".mcp.json",
        cat.root / "agents" / "vendors" / "cursor" / "mcp.json",
        cat.root / "agents" / "vendors" / "opencode" / "opencode.json",
        cat.root / "agents" / "vendors" / "kimi-code" / "mcp.json",
        cat.root / "agents" / "vendors" / "zcode" / "mcp.json",
        cat.root / "agents" / "vendors" / "qoder" / "settings.json",
        cat.root / "agents" / "vendors" / "codebuddy-code" / ".mcp.json",
    ]
    # 跳过 local overrides（允许私有路径）
    skip_names = {"local.yaml"}
    findings = 0
    for root in scan_roots:
        paths: List[Path]
        if root.is_dir():
            paths = [p for p in root.rglob("*") if p.is_file()]
        elif root.is_file():
            paths = [root]
        else:
            continue
        for path in paths:
            if path.name in skip_names or "local/" in str(path.relative_to(cat.root) if cat.root in path.parents else path):
                continue
            if path.suffix not in {".yaml", ".yml", ".json", ".md", ".toml", ".txt", ".example"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            # 忽略 schema 里的 pattern 行本身
            if path.name == "security.yaml":
                continue
            for pname, cre, sev in patterns:
                for m in cre.finditer(text):
                    # 允许占位符
                    frag = m.group(0)
                    if "${" in frag or "{env:" in frag:
                        continue
                    findings += 1
                    status = STATUS_FAIL if sev == "fail" else STATUS_WARN
                    rel = path
                    try:
                        rel = path.relative_to(cat.root)
                    except ValueError:
                        pass
                    report.add(
                        "security",
                        f"{pname}:{rel}",
                        status,
                        f"可疑模式 {pname} @ {rel}（值已隐藏）",
                        hint="移到 local override 或环境变量",
                    )
                    break

    # browser state in repo
    forbidden = ((cat.security.get("browser_state") or {}).get("forbidden_in_repo") or [])
    artifact_hint = str(
        ((cat.security.get("browser_state") or {}).get("artifact_hint"))
        or "移到 ~/.cache/agent-env/browser/ 并加入 gitignore"
    )
    artifact_findings = 0
    for pattern in forbidden:
        for hit in cat.root.glob(pattern):
            if ".git" in hit.parts:
                continue
            artifact_findings += 1
            try:
                rel = hit.relative_to(cat.root)
            except ValueError:
                rel = hit
            report.add(
                "security",
                f"browser-state:{pattern}",
                STATUS_WARN,
                f"仓库内发现疑似浏览器调试产物 @ {rel}",
                hint=artifact_hint,
            )
            break

    if findings == 0 and artifact_findings == 0:
        report.add("security", "scan", STATUS_PASS, "未发现明显密钥/内网 URL 或浏览器产物泄漏")


def check_agents(cat: Catalog, report: DoctorReport, tool: Optional[str]) -> None:
    sync_sh = cat.root / "scripts" / "agents" / "sync.sh"
    if not sync_sh.is_file():
        report.add(
            "agents",
            "sync-script",
            STATUS_WARN,
            "找不到 scripts/agents/sync.sh",
        )
        return
    report.add("agents", "sync-script", STATUS_PASS, "agents sync 脚本存在")

    # 轻量漂移：比较 agents/skills 与工具生成目录是否存在
    skills_src = cat.root / "agents" / "skills"
    if not skills_src.is_dir():
        report.add("agents", "source", STATUS_WARN, "agents/skills 不存在")
        return

    targets = {
        "claude": Path.home() / ".claude" / "skills",
        "cursor": Path.home() / ".cursor" / "skills",
        "opencode": cat.root / "agents" / "vendors" / "opencode" / "skills",
        "codex": Path.home() / ".codex" / "skills",
        "kimi-code": Path.home() / ".kimi-code" / "skills",
        "pi": Path.home() / ".pi" / "agent" / "skills",
        "zcode": Path.home() / ".zcode" / "skills",
        "qoder": Path.home() / ".qoder-cn" / "skills",
        "codebuddy-code": Path.home() / ".codebuddy" / "skills",
    }
    # 更可靠：对常用工具目录 skills 做存在性抽查（opt-in 工具仅在 --tool 时检查）
    sample = next(skills_src.iterdir(), None) if skills_src.is_dir() else None
    check_tools = [tool] if tool else ["opencode", "cursor", "kimi-code", "pi", "zcode"]
    drifted = False
    for t in check_tools:
        if t == "opencode":
            dest = cat.root / "agents" / "vendors" / "opencode" / "skills"
            if sample and sample.is_dir():
                marker = dest / sample.name
                if not marker.exists():
                    drifted = True
                    report.add(
                        "agents",
                        f"{t}-drift",
                        STATUS_WARN,
                        f"{t} skills 可能未同步（缺 {sample.name}）",
                        hint="运行 scripts/agents/sync.sh opencode",
                    )
                else:
                    report.add("agents", f"{t}-drift", STATUS_PASS, f"{t} skills 看起来已同步")
        elif t == "cursor":
            dest = Path.home() / ".cursor" / "skills"
            if not dest.is_dir():
                report.add(
                    "agents",
                    f"{t}-drift",
                    STATUS_WARN,
                    "Cursor skills 目录不存在",
                    hint="运行 scripts/agents/sync.sh cursor",
                )
            else:
                report.add("agents", f"{t}-drift", STATUS_PASS, "Cursor skills 目录存在")
        elif t == "kimi-code":
            dest = Path.home() / ".kimi-code" / "skills"
            if sample and sample.is_dir():
                marker = dest / sample.name
                if not dest.is_dir() or not marker.exists():
                    drifted = True
                    report.add(
                        "agents",
                        f"{t}-drift",
                        STATUS_WARN,
                        f"{t} skills 可能未同步（缺 {sample.name}）",
                        hint="运行 scripts/agents/sync.sh kimi-code",
                    )
                else:
                    report.add("agents", f"{t}-drift", STATUS_PASS, f"{t} skills 看起来已同步")
            elif not dest.is_dir():
                report.add(
                    "agents",
                    f"{t}-drift",
                    STATUS_WARN,
                    "Kimi skills 目录不存在",
                    hint="运行 scripts/agents/sync.sh kimi-code",
                )
            else:
                report.add("agents", f"{t}-drift", STATUS_PASS, "Kimi skills 目录存在")
        elif t == "pi":
            dest = Path.home() / ".pi" / "agent" / "skills"
            if sample and sample.is_dir():
                marker = dest / sample.name
                if not dest.is_dir() or not marker.exists():
                    drifted = True
                    report.add(
                        "agents",
                        f"{t}-drift",
                        STATUS_WARN,
                        f"{t} skills 可能未同步（缺 {sample.name}）",
                        hint="运行 scripts/agents/sync.sh pi",
                    )
                else:
                    report.add("agents", f"{t}-drift", STATUS_PASS, f"{t} skills 看起来已同步")
            elif not dest.is_dir():
                report.add(
                    "agents",
                    f"{t}-drift",
                    STATUS_WARN,
                    "Pi skills 目录不存在",
                    hint="运行 scripts/agents/sync.sh pi",
                )
            else:
                report.add("agents", f"{t}-drift", STATUS_PASS, "Pi skills 目录存在")
        elif t == "zcode":
            dest = Path.home() / ".zcode" / "skills"
            if sample and sample.is_dir():
                marker = dest / sample.name
                if not dest.is_dir() or not marker.exists():
                    drifted = True
                    report.add(
                        "agents",
                        f"{t}-drift",
                        STATUS_WARN,
                        f"{t} skills 可能未同步（缺 {sample.name}）",
                        hint="运行 scripts/agents/sync.sh zcode",
                    )
                else:
                    report.add(
                        "agents", f"{t}-drift", STATUS_PASS, f"{t} skills 看起来已同步"
                    )
            elif not dest.is_dir():
                report.add(
                    "agents",
                    f"{t}-drift",
                    STATUS_WARN,
                    "ZCode skills 目录不存在",
                    hint="运行 scripts/agents/sync.sh zcode",
                )
            else:
                report.add("agents", f"{t}-drift", STATUS_PASS, "ZCode skills 目录存在")
        elif t in ("qoder", "codebuddy-code"):
            dest = targets[t]
            label = "Qoder" if t == "qoder" else "CodeBuddy"
            if sample and sample.is_dir():
                marker = dest / sample.name
                if not dest.is_dir() or not marker.exists():
                    drifted = True
                    report.add(
                        "agents",
                        f"{t}-drift",
                        STATUS_WARN,
                        f"{t} skills 可能未同步（缺 {sample.name}）",
                        hint=f"运行 scripts/agents/sync.sh {t}",
                    )
                else:
                    report.add(
                        "agents", f"{t}-drift", STATUS_PASS, f"{t} skills 看起来已同步"
                    )
            elif not dest.is_dir():
                report.add(
                    "agents",
                    f"{t}-drift",
                    STATUS_WARN,
                    f"{label} skills 目录不存在",
                    hint=f"运行 scripts/agents/sync.sh {t}",
                )
            else:
                report.add(
                    "agents", f"{t}-drift", STATUS_PASS, f"{label} skills 目录存在"
                )
        else:
            report.add(
                "agents",
                f"{t}-check",
                STATUS_SKIP,
                f"{t}: 详细漂移检查请运行 scripts/agents/sync.sh {t}",
            )

    if not drifted:
        pass


def format_text(report: DoctorReport) -> str:
    lines = [
        f"agents doctor  profile={report.profile}  risk={report.risk}  tool={report.tool or '*'}",
        "",
    ]
    groups: Dict[str, List[CheckItem]] = {}
    for it in report.items:
        groups.setdefault(it.group, []).append(it)
    for g in ("env", "tools", "mcp", "browser", "security", "agents"):
        items = groups.get(g) or []
        if not items:
            continue
        lines.append(f"[{g}]")
        for it in items:
            extra = f"  hint: {it.hint}" if it.hint else ""
            lines.append(f"  {it.status:4}  {it.id}: {it.message}{extra}")
        lines.append("")
    lines.append(f"summary: {report.worst()}")
    return "\n".join(lines)


def format_json(report: DoctorReport) -> str:
    payload = {
        "profile": report.profile,
        "tool": report.tool,
        "risk": report.risk,
        "summary": report.worst(),
        "exit_status_meaning": {
            "0": "pass/warn/skip only",
            "1": "one or more fail",
        },
        "checks": [asdict(it) for it in report.items],
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    # 二次确认不包含常见 secret 值形态（环境变量真实值）
    for key, val in os.environ.items():
        if not val or len(val) < 8:
            continue
        if key.endswith("API_KEY") or key.endswith("_TOKEN") or key.endswith("_SECRET"):
            if val in text:
                raise SystemExit("error: JSON 输出意外包含 secret 值，已中止")
    return text + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    root = args.root or repo_root_from(Path(__file__))
    try:
        cat = Catalog(root)
    except SystemExit as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "summary": "fail",
                        "checks": [
                            {
                                "group": "mcp",
                                "id": "manifest",
                                "status": "fail",
                                "message": str(exc),
                            }
                        ],
                    },
                    indent=2,
                )
            )
            return 1
        raise

    profile = args.profile or cat.default_profile()
    pdata = cat.resolve_profile(profile)
    report = DoctorReport(
        profile=pdata["id"], tool=args.tool, risk=str(pdata.get("risk") or "low")
    )

    check_env(cat, report, profile)
    check_tools(cat, report, profile)
    check_mcp(cat, report, profile, args.tool, args.deep)
    check_browser(cat, report, profile, args.deep)
    check_security(cat, report)
    check_agents(cat, report, args.tool)

    if args.json:
        sys.stdout.write(format_json(report))
    else:
        print(format_text(report))
    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
