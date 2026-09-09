from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "src"
sys.path.insert(0, str(SCRIPTS / "agents"))

from common import Catalog  # noqa: E402
from sync_plan import apply_sync_plan, compile_sync_plan  # noqa: E402


def _status(tool: str, home: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        HOME=str(home),
        XDG_STATE_HOME=str(home / ".state"),
        DOTFILES_ROOT=str(ROOT),
    )
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "agents" / "managed_mcp_status.py"), tool],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_status_distinguishes_sync_managed_from_uninitialized(tmp_home: Path) -> None:
    missing = _status("cursor", tmp_home)
    assert missing.returncode == 0
    assert "由 agents sync 管理" in missing.stdout
    assert "尚未初始化" in missing.stdout
    assert "dotf agents -c --tool cursor" in missing.stdout

    cat = Catalog(ROOT, include_overlays=False)
    state = tmp_home / ".state"
    plan = compile_sync_plan(cat, "research", ["cursor"], home=tmp_home, state_home=state)
    apply_sync_plan(plan, cat, approved=True, home=tmp_home, state_home=state)
    managed = _status("cursor", tmp_home)
    assert managed.returncode == 0
    assert "pass  mcp: 由 agents sync 管理" in managed.stdout


def test_status_ignores_tools_without_mcp_capability(tmp_home: Path) -> None:
    result = _status("codex", tmp_home)
    assert result.returncode == 2
    assert result.stdout == ""
