"""Apply or remove one Skill / MCP Entry by updating overlay then syncing."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent.parent
_AGENTS = Path(__file__).resolve().parent
for path in (_SCRIPTS, _AGENTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from desired_set import DesiredSetError, approved_skill_ids  # noqa: E402
from dotf_core.overlays import OverlayError, catalog_from_repo, upsert_local_overlay  # noqa: E402
from env_sync import main as env_sync_main  # noqa: E402
from plan_protocol import ProtocolError, parse_artifact_selector  # noqa: E402
from sync import sync_kiro_skills, sync_skills  # noqa: E402


def repo_root() -> Path:
    configured = os.environ.get("DOTFILES_ROOT")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[2]


def _unique(values: list[str], item: str, *, present: bool) -> list[str]:
    current = [value for value in values if value != item]
    if present:
        current.append(item)
    return sorted(set(current))


def _mutate_skill(agents: dict[str, Any], skill_id: str, *, enable: bool) -> None:
    enabled = list(agents.get("enabled_skills") or [])
    disabled = list(agents.get("disabled_skills") or [])
    if enable:
        agents["enabled_skills"] = _unique(enabled, skill_id, present=True)
        agents["disabled_skills"] = _unique(disabled, skill_id, present=False)
    else:
        agents["enabled_skills"] = _unique(enabled, skill_id, present=False)
        agents["disabled_skills"] = _unique(disabled, skill_id, present=True)
    if not agents["enabled_skills"]:
        agents.pop("enabled_skills", None)
    if not agents["disabled_skills"]:
        agents.pop("disabled_skills", None)


def _mutate_mcp(
    agents: dict[str, Any],
    server_id: str,
    *,
    enable: bool,
    tool: str,
    tools: frozenset[str],
) -> None:
    enabled = list(agents.get("enabled_servers") or [])
    disabled = list(agents.get("disabled_servers") or [])
    exclude = dict(agents.get("exclude") or {})
    targets = sorted(tools) if tool == "*" else [tool]
    if enable:
        agents["enabled_servers"] = _unique(enabled, server_id, present=True)
        agents["disabled_servers"] = _unique(disabled, server_id, present=False)
        for name in targets:
            current = list((exclude.get(name) or {}).get("servers") or [])
            remaining = _unique(current, server_id, present=False)
            if remaining:
                exclude[name] = {"servers": remaining}
            else:
                exclude.pop(name, None)
    elif tool == "*":
        agents["enabled_servers"] = _unique(enabled, server_id, present=False)
        agents["disabled_servers"] = _unique(disabled, server_id, present=True)
    else:
        current = list((exclude.get(tool) or {}).get("servers") or [])
        exclude[tool] = {"servers": _unique(current, server_id, present=True)}
    if not agents.get("enabled_servers"):
        agents.pop("enabled_servers", None)
    if not agents.get("disabled_servers"):
        agents.pop("disabled_servers", None)
    if exclude:
        agents["exclude"] = exclude
    else:
        agents.pop("exclude", None)


def _emit(status: str, reason: str, exit_code: int = 0) -> None:
    module = os.environ.get("DOTF_MODULE", "")
    action = os.environ.get("DOTF_ACTION", "")
    reason = reason.replace("\t", " ").replace("\n", " ")
    print(f"RESULT\t{status}\t{module}\t{action}\t0\t{exit_code}\t{reason}")


def run_desired_op(action: str, selector: str, *, root: Path | None = None) -> int:
    repo = (root or repo_root()).resolve()
    try:
        kind, artifact_id, tool = parse_artifact_selector(selector)
    except ProtocolError as exc:
        _emit("failed", str(exc), 1)
        return 1
    catalog = catalog_from_repo(repo)
    enable = action.endswith(".apply")
    try:
        if kind == "skill":
            if action not in {"skill.apply", "skill.remove"}:
                raise DesiredSetError(f"动作与选择器不匹配: {action} {selector}")
            if artifact_id not in approved_skill_ids(repo):
                raise DesiredSetError(f"拒绝未锁定或未知 skill: {artifact_id}")
            upsert_local_overlay(
                repo,
                lambda agents: _mutate_skill(agents, artifact_id, enable=enable),
            )
            skill_rc = sync_skills(repo)
            kiro_rc = sync_kiro_skills(repo)
            if skill_rc or kiro_rc:
                _emit("failed", "skill sync failed after overlay write", 1)
                return 1
            _emit("changed" if enable else "changed", f"skill {artifact_id} {'applied' if enable else 'removed'}")
            return 0
        if kind == "mcp":
            if action not in {"mcp.apply", "mcp.remove"}:
                raise DesiredSetError(f"动作与选择器不匹配: {action} {selector}")
            if artifact_id not in catalog.servers:
                raise DesiredSetError(f"未知 MCP server: {artifact_id}")
            if tool != "*" and tool not in catalog.tools:
                raise DesiredSetError(f"未知 MCP 工具: {tool}")
            upsert_local_overlay(
                repo,
                lambda agents: _mutate_mcp(
                    agents,
                    artifact_id,
                    enable=enable,
                    tool=tool or "",
                    tools=catalog.tools,
                ),
            )
            targets = "all" if tool == "*" else tool
            sync_detail = ""
            try:
                env_rc = env_sync_main([targets, "--root", str(repo)])
            except SystemExit as exc:
                # common.die() 用字符串 code 退出；捕获后解释器不再打印消息，
                # 必须在这里保留原因，否则 RESULT 只剩笼统的 sync failed。
                if isinstance(exc.code, int):
                    env_rc = exc.code
                else:
                    env_rc = 1
                    sync_detail = str(exc.code).removeprefix("error: ")
            if env_rc != 0:
                _emit("failed", sync_detail or "mcp sync failed after overlay write", 1)
                return 1
            _emit("changed", f"mcp {artifact_id} {'applied' if enable else 'removed'}")
            return 0
        raise DesiredSetError(f"不支持的制品: {selector}")
    except (DesiredSetError, OverlayError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        _emit("failed", str(exc), 1)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update Desired Set and sync one artifact")
    parser.add_argument("action", choices=("skill.apply", "skill.remove", "mcp.apply", "mcp.remove"))
    parser.add_argument("selector")
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    return run_desired_op(args.action, args.selector, root=args.root)


if __name__ == "__main__":
    raise SystemExit(main())
