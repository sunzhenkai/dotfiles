"""agents sync 失败必须点名阶段，RESULT 不能只写 agents sync failed。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

ROOT = Path(__file__).resolve().parent.parent
SYNC_SH = ROOT / "scripts" / "modules" / "agents" / "sync.sh"
CONFIG_SH = ROOT / "scripts" / "modules" / "agents" / "config.sh"

sys.path.insert(0, str(ROOT / "src" / "agents"))
from sync import SyncOutcome, main as sync_main  # noqa: E402


def _stub_agents(root: Path, *, skills_rc: int = 0, defaults_rc: int = 0, openspec_rc: int = 0) -> None:
    agents = root / "src" / "agents"
    agents.mkdir(parents=True)
    (agents / "instructions.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    (agents / "sync.py").write_text(
        dedent(
            f"""\
            import sys
            if "--decide-takeover" in sys.argv:
                print("skip")
                raise SystemExit(0)
            print("stub skills")
            raise SystemExit({skills_rc})
            """
        ),
        encoding="utf-8",
    )
    (agents / "defaults.py").write_text(
        f'print("stub defaults")\nraise SystemExit({defaults_rc})\n',
        encoding="utf-8",
    )
    (agents / "openspec_skills.py").write_text(
        f'print("stub openspec")\nraise SystemExit({openspec_rc})\n',
        encoding="utf-8",
    )


def _run_sync_sh(root: Path, home: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["DOTFILES_ROOT"] = str(root)
    env["XDG_STATE_HOME"] = str(home / ".local" / "state")
    return subprocess.run(
        ["bash", str(SYNC_SH)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
        check=False,
    )


def test_sync_sh_names_failed_skills_stage(tmp_path: Path) -> None:
    root = tmp_path / "root"
    home = tmp_path / "home"
    home.mkdir()
    _stub_agents(root, skills_rc=1)
    result = _run_sync_sh(root, home)
    combined = result.stdout + result.stderr
    assert result.returncode == 1
    assert "有阶段失败: skills" in combined
    assert "有阶段失败: defaults" not in combined
    assert "有阶段失败: openspec" not in combined


def test_sync_sh_names_every_failed_stage(tmp_path: Path) -> None:
    root = tmp_path / "root"
    home = tmp_path / "home"
    home.mkdir()
    _stub_agents(root, skills_rc=1, openspec_rc=2)
    result = _run_sync_sh(root, home)
    combined = result.stdout + result.stderr
    assert result.returncode == 2
    assert "有阶段失败: skills, openspec" in combined


def test_config_sh_forwards_named_stage_to_result() -> None:
    text = CONFIG_SH.read_text(encoding="utf-8")
    assert 'dotf_result_failed "agents sync failed"' not in text
    assert "grep '^error: agents sync 有阶段失败'" in text
    assert 'dotf_result_failed "${reason:-agents sync failed}"' in text


def test_sync_main_prints_summarize_on_layout_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "sync.sync_skills",
        lambda *args, **kwargs: [SyncOutcome("kiro skills", 1, "skipped bar")],
    )
    rc = sync_main(["--root", str(tmp_path), "--takeover", "skip"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "error: skills: kiro skills: skipped bar" in err
