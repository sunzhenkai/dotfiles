#!/usr/bin/env python3
"""Plan and apply agents/env MCP declarations for supported vendors."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from common import Catalog, die, repo_root_from
from dotf_core.sanitize import sanitize_for_terminal
from sync_plan import SyncPlanError, apply_sync_plan, compile_sync_plan, plan_json


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sync agents/env MCP to target tools")
    p.add_argument("tool", nargs="?", default="all", help="目标工具（默认 all）")
    p.add_argument("--profile", default=None, help="覆盖 profile（默认读 manifest/local）")
    p.add_argument("--dry-run", action="store_true", help="只编译并打印无副作用 SyncPlan")
    p.add_argument("--json", action="store_true", help="输出严格机器可读 SyncPlan JSON")
    p.add_argument("--root", type=Path, default=None, help="仓库根目录")
    p.add_argument("--validate-tool", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--require-mcp", action="store_true", help=argparse.SUPPRESS)
    return p.parse_args(argv)


def merge_mcp_servers(
    existing: Dict[str, Any], managed: Dict[str, Any], managed_ids: Set[str]
) -> Dict[str, Any]:
    """Compatibility helper: update selected ids but do not reconcile without ownership."""
    del managed_ids
    out = dict(existing)
    out.update(managed)
    return out


def _text_plan(plan: Any) -> None:
    runtimes = {
        runtime.resource_id: f"{runtime.package}@{runtime.version}"
        for item in plan.items
        for runtime in item.declared_runtime_versions
    }
    print(f"profile={plan.profile} dry_run=True")
    print(
        "declared_runtime_versions="
        + (", ".join(f"{key}:{value}" for key, value in sorted(runtimes.items())) or "none")
    )
    for item in plan.items:
        secrets = ",".join(f"${{{name}}}" for name in item.required_secrets) or "none"
        print(
            f"[dry-run] {item.adapter}: state={item.state} action={item.action} "
            f"risk={item.risk} target={item.target} required_secrets={secrets} "
            f"expected={item.expected_hash} current={item.current_hash or 'none'} "
            f"installed={item.installed_hash or 'none'} actual={item.actual_state}"
        )


def _sync_one(
    cat: Catalog,
    tool: str,
    profile: Optional[str],
    dry_run: bool,
) -> str:
    capability = cat.vendor_matrix.capability(tool)
    if not capability.mcp:
        reason = ((cat.manifest.get("unsupported") or {}).get(tool) or {}).get("reason") or "MCP sync unsupported"
        print(("[dry-run] " if dry_run else "") + f"{tool}: skip MCP sync ({reason})")
        return "skip"
    plan = compile_sync_plan(cat, profile, [tool])
    if dry_run:
        _text_plan(plan)
        return "ok"
    try:
        results, secret_values = apply_sync_plan(plan, cat, approved=True)
    except (OSError, ValueError, SyncPlanError) as exc:
        die(sanitize_for_terminal(str(exc)))
    for result in results:
        message = f"{result.resource_id}: {result.status} → {result.target}"
        print(sanitize_for_terminal(message, secret_values=secret_values))
    return "ok"


def sync_cursor(cat: Catalog, profile: Optional[str], dry_run: bool) -> str:
    return _sync_one(cat, "cursor", profile, dry_run)


def sync_kiro(cat: Catalog, profile: Optional[str], dry_run: bool) -> str:
    return _sync_one(cat, "kiro", profile, dry_run)


def sync_opencode(cat: Catalog, profile: Optional[str], dry_run: bool) -> str:
    return _sync_one(cat, "opencode", profile, dry_run)


def sync_kimi_code(cat: Catalog, profile: Optional[str], dry_run: bool) -> str:
    return _sync_one(cat, "kimi-code", profile, dry_run)


def sync_zcode(cat: Catalog, profile: Optional[str], dry_run: bool) -> str:
    return _sync_one(cat, "zcode", profile, dry_run)


def sync_codex(cat: Catalog, profile: Optional[str], dry_run: bool) -> str:
    return _sync_one(cat, "codex", profile, dry_run)


def sync_pi(cat: Catalog, profile: Optional[str], dry_run: bool) -> str:
    return _sync_one(cat, "pi", profile, dry_run)


def sync_dsh(cat: Catalog, profile: Optional[str], dry_run: bool) -> str:
    return _sync_one(cat, "dsh", profile, dry_run)


def _validate_selection(cat: Catalog, tool: str, *, require_mcp: bool = False) -> tuple[str, ...]:
    valid = set(cat.vendor_matrix.cli_tools)
    if tool != "all" and tool not in valid:
        die(f"未知参数/工具: {tool}（可选: {', '.join(cat.vendor_matrix.cli_tools)}, all）")
    targets = cat.vendor_matrix.cli_tools if tool == "all" else (tool,)
    if require_mcp and tool != "all" and not cat.vendor_matrix.capability(tool).mcp:
        die(f"工具 {tool} 不支持 MCP sync（能力由 vendors.yaml 声明）")
    return targets


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    if args.require_mcp and not args.validate_tool:
        die("--require-mcp is only valid with delegated tool validation")
    root = args.root or repo_root_from(Path(__file__))
    cat = Catalog(root)
    targets = _validate_selection(cat, args.tool, require_mcp=args.require_mcp)
    if args.validate_tool:
        if args.profile is not None:
            cat.resolve_profile(args.profile)
        return 0
    plan = compile_sync_plan(cat, args.profile, targets)
    if args.json:
        if not args.dry_run:
            die("--json requires --dry-run; machine output is an immutable plan")
        print(plan_json(plan))
        return 0
    if args.dry_run:
        _text_plan(plan)
        for tool in targets:
            if not cat.vendor_matrix.capability(tool).mcp:
                _sync_one(cat, tool, args.profile, True)
        print("结果: " + ", ".join(f"{tool}={'ok' if cat.vendor_matrix.capability(tool).mcp else 'skip'}" for tool in targets))
        return 0
    print(f"profile={plan.profile} dry_run=False")
    try:
        results, secret_values = apply_sync_plan(plan, cat, approved=True)
    except (OSError, ValueError, SyncPlanError) as exc:
        die(sanitize_for_terminal(str(exc)))
    status_by_tool = {item.adapter: "ok" for item in plan.items}
    for result in results:
        print(sanitize_for_terminal(f"{result.resource_id}: {result.status} → {result.target}", secret_values=secret_values))
    for tool in targets:
        if not cat.vendor_matrix.capability(tool).mcp:
            status_by_tool[tool] = _sync_one(cat, tool, args.profile, False)
    print("结果: " + ", ".join(f"{tool}={status_by_tool[tool]}" for tool in targets))
    return 0


if __name__ == "__main__":
    sys.exit(main())
