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


def test_sync_installs_taskctl_shim_pointing_at_the_canonical_copy(tmp_path: Path) -> None:
    r = _run_sync(tmp_path, "kimi-code")
    assert r.returncode == 0, r.stderr + r.stdout
    shim = tmp_path / ".local" / "bin" / "taskctl"
    assert shim.is_file(), f"shim 未生成: {shim}\n{r.stdout}"
    assert os.access(shim, os.X_OK)
    canonical = ROOT / "agents" / "skills" / "task-workflow" / "scripts" / "taskctl.py"
    body = shim.read_text()
    assert str(canonical) in body
    # 镜像副本不得成为 shim 的目标。
    assert ".kimi-code" not in body and ".claude" not in body

    r2 = _run_sync(tmp_path, "kimi-code")
    assert r2.returncode == 0, r2.stderr + r2.stdout
    assert f"  = {shim}" in r2.stdout


def test_sync_kiro_commands_as_argument_aware_skills(tmp_path: Path) -> None:
    r = _run_sync(tmp_path, "kiro")
    assert r.returncode == 0, r.stderr + r.stdout

    task_new = tmp_path / ".kiro" / "skills" / "task-new" / "SKILL.md"
    assert task_new.is_file(), f"Kiro command 未生成 skill: {task_new}\n{r.stdout}"
    content = task_new.read_text()
    assert "name: task-new" in content
    assert "[TASK_NEW_INPUT_START]\n\n$ARGUMENTS" in content
    assert not (tmp_path / ".kiro" / "prompts" / "task-new.md").exists()

    # 同名 source skill 保持唯一 owner，也必须能够接收 slash 后的正文。
    commit_push = tmp_path / ".kiro" / "skills" / "commit-push" / "SKILL.md"
    assert commit_push.is_file()
    assert commit_push.read_text().rstrip().endswith("$ARGUMENTS")
    assert "skip command commit-push for kiro" in r.stdout


def test_sync_kiro_retires_legacy_command_prompts(tmp_path: Path) -> None:
    legacy = tmp_path / ".kiro" / "prompts" / "task-new.md"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("legacy managed prompt\n")

    r = _run_sync(tmp_path, "kiro")
    assert r.returncode == 0, r.stderr + r.stdout
    assert not legacy.exists()
    backups = list((tmp_path / ".config" / "backups").glob("task-new.md-*"))
    assert len(backups) == 1
    assert backups[0].read_text() == "legacy managed prompt\n"
