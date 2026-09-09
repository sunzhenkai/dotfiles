#!/usr/bin/env python3
"""Read-only L0 status for MCP targets owned by agents sync."""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
if str(_SCRIPTS / "agents") not in sys.path:
    sys.path.insert(0, str(_SCRIPTS / "agents"))

from catalog import CatalogError, load_vendor_matrix  # noqa: E402
from mcp_runtime import read_manifest  # noqa: E402


def inspect(tool: str, *, root: Path, home: Path, state_home: Path) -> tuple[int, str]:
    try:
        capability = load_vendor_matrix(root).capability(tool)
    except (CatalogError, KeyError, OSError):
        return 2, ""
    if not capability.mcp or capability.target is None:
        return 2, ""
    target = home / capability.target[2:]
    snapshot = read_manifest(home, state_home)
    if snapshot.status == "malformed":
        return 1, f"fail  mcp: agents sync ownership manifest malformed → {state_home / 'dotf' / 'agents-mcp-manifest.json'}"
    if snapshot.status == "missing":
        return 0, f"warn  mcp: 由 agents sync 管理但 ownership manifest 尚未初始化；建议: dotf agents -c --tool {tool}"
    owned = [item for item in snapshot.manifest.items if item.tool == tool]
    if not owned:
        return 0, f"warn  mcp: 由 agents sync 管理但尚无 {tool} ownership；建议: dotf agents -c --tool {tool}"
    try:
        item = target.lstat()
    except FileNotFoundError:
        return 1, f"fail  mcp: agents sync 目标不存在 → {target}"
    if stat.S_ISLNK(item.st_mode) or not stat.S_ISREG(item.st_mode):
        return 1, f"fail  mcp: agents sync 目标类型不安全 → {target}"
    return 0, f"pass  mcp: 由 agents sync 管理（owned={len(owned)}）→ {target}"


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    if len(args) != 1:
        print("usage: managed_mcp_status.py <tool>", file=sys.stderr)
        return 2
    root = Path(os.environ.get("DOTFILES_ROOT", _SCRIPTS.parent)).resolve()
    home = Path(os.environ.get("HOME", str(Path.home()))).expanduser().absolute()
    configured = os.environ.get("XDG_STATE_HOME")
    state_home = Path(configured).expanduser().absolute() if configured else home / ".local" / "state"
    code, message = inspect(args[0], root=root, home=home, state_home=state_home)
    if message:
        print(message)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
