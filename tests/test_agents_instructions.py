"""全局 AGENTS.md：跨项目指令，由 agents sync 安装到用户级目标。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "agents"))

from instructions import CURSOR_MDC_HEADER, OWNER_PREFIX  # noqa: E402
from managed_runtime import AGENTS_MANIFEST_NAME  # noqa: E402

SOURCE = ROOT / "agents" / "instructions" / "AGENTS.md"


def _run(home: Path, *, dry_run: bool = False, root: Path = ROOT) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["XDG_STATE_HOME"] = str(home / ".state")
    cmd = [sys.executable, str(ROOT / "src" / "agents" / "instructions.py"), "--root", str(root)]
    if dry_run:
        cmd.append("--dry-run")
    return subprocess.run(cmd, text=True, capture_output=True, env=env, cwd=ROOT, check=False)


def test_source_is_global_and_omits_skill_catalog() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    assert "skill" not in text.lower()
    assert not text.lstrip().startswith("---")
    assert "简体中文" in text
    assert "不 commit" in text
    assert "这份文件" not in text


def test_sync_sh_invokes_instructions() -> None:
    script = (ROOT / "scripts" / "modules" / "agents" / "sync.sh").read_text(encoding="utf-8")
    assert 'python3 "$_SRC_AGENTS/instructions.py"' in script
    assert "--- instructions ---" in script


def test_installs_user_level_targets(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    result = _run(home)
    assert result.returncode == 0, result.stderr + result.stdout
    source = SOURCE.read_text(encoding="utf-8")
    if not source.endswith("\n"):
        source += "\n"
    agents = home / ".agents" / "AGENTS.md"
    codex = home / ".codex" / "AGENTS.md"
    cursor = home / ".cursor" / "rules" / "00-dotf-global.mdc"
    assert agents.read_text(encoding="utf-8") == source
    assert codex.read_text(encoding="utf-8") == source
    cursor_text = cursor.read_text(encoding="utf-8")
    assert cursor_text.startswith(CURSOR_MDC_HEADER)
    assert "alwaysApply: true" in cursor_text
    assert cursor_text.endswith(source)
    assert agents.stat().st_mode & 0o777 == 0o644


def test_dry_run_is_side_effect_free(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    result = _run(home, dry_run=True)
    assert result.returncode == 0, result.stderr + result.stdout
    assert not (home / ".agents").exists()
    assert not (home / ".codex").exists()
    assert not (home / ".cursor").exists()
    assert not (home / ".state").exists()


def test_second_sync_is_idempotent(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    first = _run(home)
    assert first.returncode == 0, first.stderr + first.stdout
    agents = home / ".agents" / "AGENTS.md"
    before = agents.stat().st_mtime_ns
    second = _run(home)
    assert second.returncode == 0, second.stderr + second.stdout
    assert "done instructions: changed=0" in second.stdout
    assert agents.stat().st_mtime_ns == before
    data = (home / ".state" / "dotf" / AGENTS_MANIFEST_NAME).read_text(encoding="utf-8")
    assert OWNER_PREFIX + "agents" in data
    assert OWNER_PREFIX + "codex" in data
    assert OWNER_PREFIX + "cursor" in data


def test_local_edit_conflicts_without_overwrite(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    assert _run(home).returncode == 0
    target = home / ".agents" / "AGENTS.md"
    target.write_text("local edit\n", encoding="utf-8")
    result = _run(home)
    assert result.returncode != 0
    assert "owned target was modified locally" in result.stderr + result.stdout
    assert target.read_text(encoding="utf-8") == "local edit\n"


def test_doctor_reports_missing_targets(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT / "src"))
    import doctor  # noqa: WPS433

    home = tmp_path / "home"
    home.mkdir()
    report = doctor.DoctorReport("research", None, "low")
    doctor.check_instructions_plan(ROOT, report, home=home, state_home=home / ".state")
    text = "\n".join(f"{item.id} {item.status} {item.message}" for item in report.items)
    assert "missing" in text
    assert str(home / ".agents" / "AGENTS.md") in text
    summary = next(item for item in report.items if item.id == "sync-plan")
    assert summary.status == doctor.STATUS_WARN


def test_missing_source_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "agents" / "instructions").mkdir(parents=True)
    (repo / "agents" / "instructions" / "install.yaml").write_text(
        (ROOT / "agents" / "instructions" / "install.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    home = tmp_path / "home"
    home.mkdir()
    result = _run(home, root=repo)
    assert result.returncode != 0
    assert "missing global AGENTS.md source" in result.stderr
    assert not (home / ".agents" / "AGENTS.md").exists()
