"""sync.py 分发 skill 到共享 ~/.agents/skills：references/scripts 原样拷贝。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run_sync(tmp_home: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "agents" / "sync.py"), "--root", str(ROOT)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
        check=False,
    )


def test_sync_copies_skill_references(tmp_path: Path) -> None:
    r = _run_sync(tmp_path)
    assert r.returncode == 0, r.stderr + r.stdout
    src = ROOT / "agents" / "skills" / "task-design" / "references" / "design-template.md"
    dest = tmp_path / ".agents" / "skills" / "task-design" / "references" / "design-template.md"
    assert dest.is_file(), f"references 未分发: {dest}\n{r.stdout}"
    # 原样拷贝：字节一致（不做 frontmatter 渲染 / slash 替换）
    assert dest.read_bytes() == src.read_bytes()


def test_sync_references_idempotent(tmp_path: Path) -> None:
    r1 = _run_sync(tmp_path)
    assert r1.returncode == 0, r1.stderr + r1.stdout
    r2 = _run_sync(tmp_path)
    assert r2.returncode == 0, r2.stderr + r2.stdout
    # 第二次运行不再写入（全部 skip）
    assert "references/design-template.md" not in "\n".join(
        line for line in r2.stdout.splitlines() if line.startswith("  +")
    )


def test_sync_copies_skill_scripts(tmp_path: Path) -> None:
    r = _run_sync(tmp_path)
    assert r.returncode == 0, r.stderr + r.stdout
    src = ROOT / "agents" / "skills" / "task-workflow" / "scripts" / "taskctl.py"
    dest = tmp_path / ".agents" / "skills" / "task-workflow" / "scripts" / "taskctl.py"
    assert dest.is_file(), f"scripts 未分发: {dest}\n{r.stdout}"
    assert dest.read_bytes() == src.read_bytes()


def test_sync_renders_slash_placeholders(tmp_path: Path) -> None:
    r = _run_sync(tmp_path)
    assert r.returncode == 0, r.stderr + r.stdout
    # {{slash:xxx}} 统一渲染为 /xxx；输出不得残留占位符
    skill = tmp_path / ".agents" / "skills" / "task-design" / "SKILL.md"
    assert skill.is_file(), f"skill 未同步: {skill}\n{r.stdout}"
    content = skill.read_text()
    assert "{{slash:" not in content
    assert "/task-propose" in content


def test_sync_installs_taskctl_shim_pointing_at_the_canonical_copy(tmp_path: Path) -> None:
    r = _run_sync(tmp_path)
    assert r.returncode == 0, r.stderr + r.stdout
    shim = tmp_path / ".local" / "bin" / "taskctl"
    assert shim.is_file(), f"shim 未生成: {shim}\n{r.stdout}"
    assert os.access(shim, os.X_OK)
    canonical = ROOT / "agents" / "skills" / "task-workflow" / "scripts" / "taskctl.py"
    body = shim.read_text()
    assert str(canonical) in body
    # 镜像副本不得成为 shim 的目标。
    assert ".agents/skills" not in body

    r2 = _run_sync(tmp_path)
    assert r2.returncode == 0, r2.stderr + r2.stdout
    assert f"  = {shim}" in r2.stdout
