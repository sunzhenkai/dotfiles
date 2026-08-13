"""sync.py 分发 skill references/ 目录：原样拷贝到目标 base。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run_sync(tmp_home: Path, tool: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "agents" / "sync.py"), tool, "--root", str(ROOT)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
        check=False,
    )


def test_sync_copies_skill_references(tmp_path: Path) -> None:
    r = _run_sync(tmp_path, "kimi-code")
    assert r.returncode == 0, r.stderr + r.stdout
    src = ROOT / "agents" / "skills" / "task-design" / "references" / "design-template.md"
    dest = tmp_path / ".kimi-code" / "skills" / "task-design" / "references" / "design-template.md"
    assert dest.is_file(), f"references 未分发: {dest}\n{r.stdout}"
    # 原样拷贝：字节一致（不做 frontmatter 渲染 / slash 替换）
    assert dest.read_bytes() == src.read_bytes()


def test_sync_references_idempotent(tmp_path: Path) -> None:
    r1 = _run_sync(tmp_path, "kimi-code")
    assert r1.returncode == 0, r1.stderr + r1.stdout
    r2 = _run_sync(tmp_path, "kimi-code")
    assert r2.returncode == 0, r2.stderr + r2.stdout
    # 第二次运行不再写入（全部 skip）
    assert "references/design-template.md" not in "\n".join(
        line for line in r2.stdout.splitlines() if line.startswith("  +")
    )


def test_sync_copies_skill_scripts(tmp_path: Path) -> None:
    r = _run_sync(tmp_path, "kimi-code")
    assert r.returncode == 0, r.stderr + r.stdout
    src = ROOT / "agents" / "skills" / "task-workflow" / "scripts" / "taskctl.py"
    dest = tmp_path / ".kimi-code" / "skills" / "task-workflow" / "scripts" / "taskctl.py"
    assert dest.is_file(), f"scripts 未分发: {dest}\n{r.stdout}"
    assert dest.read_bytes() == src.read_bytes()
