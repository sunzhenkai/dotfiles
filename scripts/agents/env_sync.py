#!/usr/bin/env python3
"""将 agents/env MCP 声明同步到 Claude / Cursor / OpenCode / Codex。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from common import (
    TOOLS,
    Catalog,
    atomic_write_json,
    backup_file,
    die,
    render_server_for_tool,
    repo_root_from,
)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sync agents/env MCP to target tools")
    p.add_argument(
        "tool",
        nargs="?",
        default="all",
        choices=[*TOOLS, "all"],
        help="目标工具（默认 all）",
    )
    p.add_argument("--profile", default=None, help="覆盖 profile（默认读 manifest/local）")
    p.add_argument("--dry-run", action="store_true", help="只打印将要写入的内容")
    p.add_argument("--root", type=Path, default=None, help="仓库根目录")
    p.add_argument(
        "--also-repo-templates",
        action="store_true",
        default=True,
        help="同时更新仓库内 MCP 模板（默认开启）",
    )
    p.add_argument(
        "--no-repo-templates",
        action="store_false",
        dest="also_repo_templates",
        help="不更新仓库内 MCP 模板",
    )
    return p.parse_args(argv)


def merge_mcp_servers(
    existing: Dict[str, Any],
    managed: Dict[str, Any],
    managed_ids: Set[str],
) -> Dict[str, Any]:
    """更新托管 server，保留非托管 server。"""
    out = dict(existing)
    # 移除旧托管中已不在本次集合的 id（仅托管集合内）
    for sid in list(out.keys()):
        if sid in managed_ids and sid not in managed:
            del out[sid]
    out.update(managed)
    return out


def sync_cursor(
    cat: Catalog,
    profile: Optional[str],
    dry_run: bool,
    also_repo: bool,
) -> str:
    servers = cat.selected_servers("cursor", profile)
    rendered = {
        sid: render_server_for_tool(sid, srv, "cursor") for sid, srv in servers.items()
    }
    target = Path.home() / ".cursor" / "mcp.json"
    existing: Dict[str, Any] = {}
    if target.is_file():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            die(f"无法解析 {target}: {exc}")
    block = existing.get("mcpServers") or {}
    if not isinstance(block, dict):
        block = {}
    merged = merge_mcp_servers(block, rendered, cat.managed_server_ids())
    data = dict(existing)
    data["mcpServers"] = merged

    status = f"cursor: {len(rendered)} managed servers → {target}"
    if dry_run:
        print(f"[dry-run] {status}")
        print(json.dumps({"mcpServers": rendered}, indent=2, ensure_ascii=False))
        return "ok"
    if target.exists():
        backup_file(target, Path.home() / ".config" / "backups")
    atomic_write_json(target, data, dry_run=False)
    print(f"已同步: {status}")

    if also_repo:
        repo_tpl = cat.root / "agents" / "vendors" / "cursor" / "mcp.json"
        # 仓库模板只写托管 server，保持占位符
        atomic_write_json(repo_tpl, {"mcpServers": rendered}, dry_run=False)
        print(f"已更新仓库模板: {repo_tpl.relative_to(cat.root)}")
    return "ok"


def sync_claude(
    cat: Catalog,
    profile: Optional[str],
    dry_run: bool,
    also_repo: bool,
) -> str:
    servers = cat.selected_servers("claude", profile)
    rendered = {
        sid: render_server_for_tool(sid, srv, "claude") for sid, srv in servers.items()
    }
    mcp_target = Path.home() / ".claude" / ".mcp.json"
    payload = {"mcpServers": rendered}

    status = f"claude: {len(rendered)} managed servers → {mcp_target}"
    if dry_run:
        print(f"[dry-run] {status}")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return "ok"

    if mcp_target.exists():
        backup_file(mcp_target, Path.home() / ".config" / "backups")
    # 合并用户级 .mcp.json 中的非托管项
    existing: Dict[str, Any] = {}
    if mcp_target.is_file():
        try:
            existing = json.loads(mcp_target.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    block = existing.get("mcpServers") or {}
    if not isinstance(block, dict):
        block = {}
    merged = merge_mcp_servers(block, rendered, cat.managed_server_ids())
    atomic_write_json(mcp_target, {"mcpServers": merged}, dry_run=False)
    print(f"已同步: {status}")

    # 合并到 ~/.claude.json
    state = Path.home() / ".claude.json"
    if state.is_symlink() and not state.exists():
        print("⚠️  跳过 ~/.claude.json 合并：损坏的 symlink")
    else:
        data: Dict[str, Any] = {}
        if state.is_file():
            try:
                data = json.loads(state.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                die(f"无法解析 {state}: {exc}")
        cur = data.get("mcpServers") or {}
        if not isinstance(cur, dict):
            cur = {}
        data["mcpServers"] = merge_mcp_servers(cur, rendered, cat.managed_server_ids())
        if state.exists():
            backup_file(state, Path.home() / ".config" / "backups")
        atomic_write_json(state, data, dry_run=False)
        print("已合并 MCP 到 ~/.claude.json")

    if also_repo:
        repo_tpl = cat.root / "agents" / "vendors" / "claude" / ".mcp.json"
        atomic_write_json(repo_tpl, {"mcpServers": rendered}, dry_run=False)
        print(f"已更新仓库模板: {repo_tpl.relative_to(cat.root)}")
    return "ok"


def sync_opencode(
    cat: Catalog,
    profile: Optional[str],
    dry_run: bool,
    also_repo: bool,
) -> str:
    servers = cat.selected_servers("opencode", profile)
    rendered = {
        sid: render_server_for_tool(sid, srv, "opencode")
        for sid, srv in servers.items()
    }
    repo_cfg = cat.root / "agents" / "vendors" / "opencode" / "opencode.json"
    if not repo_cfg.is_file():
        die(f"缺少 OpenCode 配置: {repo_cfg}")
    try:
        data = json.loads(repo_cfg.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(f"无法解析 {repo_cfg}: {exc}")

    cur = data.get("mcp") or {}
    if not isinstance(cur, dict):
        cur = {}
    data["mcp"] = merge_mcp_servers(cur, rendered, cat.managed_server_ids())

    status = f"opencode: {len(rendered)} managed servers → {repo_cfg}"
    if dry_run:
        print(f"[dry-run] {status}")
        print(json.dumps({"mcp": rendered}, indent=2, ensure_ascii=False))
        return "ok"

    backup_file(repo_cfg, Path.home() / ".config" / "backups")
    atomic_write_json(repo_cfg, data, dry_run=False)
    print(f"已同步: {status}")
    if also_repo:
        print("（OpenCode MCP 已写入 agents/vendors/opencode/opencode.json，随 symlink 生效）")
    return "ok"


def sync_kimi_code(
    cat: Catalog,
    profile: Optional[str],
    dry_run: bool,
    also_repo: bool,
) -> str:
    servers = cat.selected_servers("kimi-code", profile)
    rendered = {
        sid: render_server_for_tool(sid, srv, "kimi-code")
        for sid, srv in servers.items()
    }
    target = Path.home() / ".kimi-code" / "mcp.json"
    existing: Dict[str, Any] = {}
    if target.is_file():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            die(f"无法解析 {target}: {exc}")
    block = existing.get("mcpServers") or {}
    if not isinstance(block, dict):
        block = {}
    merged = merge_mcp_servers(block, rendered, cat.managed_server_ids())
    data = dict(existing)
    data["mcpServers"] = merged

    status = f"kimi-code: {len(rendered)} managed servers → {target}"
    if dry_run:
        print(f"[dry-run] {status}")
        print(json.dumps({"mcpServers": rendered}, indent=2, ensure_ascii=False))
        return "ok"
    if target.exists():
        backup_file(target, Path.home() / ".config" / "backups")
    atomic_write_json(target, data, dry_run=False)
    print(f"已同步: {status}")

    if also_repo:
        repo_tpl = cat.root / "agents" / "vendors" / "kimi-code" / "mcp.json"
        atomic_write_json(repo_tpl, {"mcpServers": rendered}, dry_run=False)
        print(f"已更新仓库模板: {repo_tpl.relative_to(cat.root)}")
    return "ok"


def sync_codex(cat: Catalog, profile: Optional[str], dry_run: bool) -> str:
    reason = (
        (cat.manifest.get("unsupported") or {})
        .get("codex", {})
        .get("reason")
        or "Codex MCP unsupported"
    )
    msg = f"codex: skip MCP sync ({reason})"
    if dry_run:
        print(f"[dry-run] {msg}")
    else:
        print(msg)
    return "skip"


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    root = args.root or repo_root_from(Path(__file__))
    cat = Catalog(root)
    profile = args.profile
    pdata = cat.resolve_profile(profile)
    print(
        f"profile={pdata['id']} risk={pdata.get('risk', 'low')} "
        f"dry_run={args.dry_run}"
    )

    targets = list(TOOLS) if args.tool == "all" else [args.tool]
    results = []
    for tool in targets:
        if tool == "cursor":
            results.append(
                (
                    tool,
                    sync_cursor(cat, profile, args.dry_run, args.also_repo_templates),
                )
            )
        elif tool == "claude":
            results.append(
                (
                    tool,
                    sync_claude(cat, profile, args.dry_run, args.also_repo_templates),
                )
            )
        elif tool == "opencode":
            results.append(
                (
                    tool,
                    sync_opencode(cat, profile, args.dry_run, args.also_repo_templates),
                )
            )
        elif tool == "codex":
            results.append((tool, sync_codex(cat, profile, args.dry_run)))
        elif tool == "kimi-code":
            results.append(
                (
                    tool,
                    sync_kimi_code(cat, profile, args.dry_run, args.also_repo_templates),
                )
            )
        else:
            die(f"未知工具: {tool}")

    print("结果: " + ", ".join(f"{t}={r}" for t, r in results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
