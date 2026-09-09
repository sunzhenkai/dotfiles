"""主体优先 CLI 基线契约 — 仅解析/拒绝路径，使用临时 HOME。"""

from __future__ import annotations

from pathlib import Path
import stat

from conftest import run_dotf


def test_help_lists_doctor_actions(tmp_home: Path, launch_home: Path) -> None:
    result = run_dotf("-h")
    assert result.returncode == 0
    out = result.stdout
    assert "--doctor" in out
    assert "-icd" in out
    assert "不含 doctor" in out
    assert Path.home().resolve() == tmp_home.resolve()
    assert tmp_home.resolve() != launch_home


def test_legacy_action_first_rejected(tmp_home: Path) -> None:
    result = run_dotf("-i", "sdk")
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "旧语法" in combined or "主体优先" in combined


def test_unknown_module_rejected(tmp_home: Path) -> None:
    result = run_dotf("no-such-module-xyz", "-i")
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "未知" in combined or "no-such" in combined.lower() or "可用" in combined


def test_module_without_doctor_rejected(tmp_home: Path) -> None:
    result = run_dotf("system", "-d")
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "诊断" in combined or "doctor" in combined.lower()


def test_old_doctor_bypass_rejected(tmp_home: Path) -> None:
    result = run_dotf("agents", "-c", "--doctor")
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "-d" in combined or "-cd" in combined


def test_init_list_profiles(tmp_home: Path) -> None:
    result = run_dotf("init", "--list")
    assert result.returncode == 0
    out = result.stdout
    assert "darwin" in out
    assert "ubuntu" in out or "debian" in out


def test_unknown_option_rejected(tmp_home: Path) -> None:
    result = run_dotf("-x")
    assert result.returncode != 0


def test_tmp_home_not_polluted_by_help(tmp_home: Path) -> None:
    run_dotf("-h")
    # 帮助不应在临时 HOME 写入配置
    config = Path(tmp_home) / ".config"
    # 允许空的 .config 目录（夹具创建），不允许新增非预期内容
    leftover = [p for p in config.rglob("*") if p.is_file()]
    assert leftover == []


def test_command_stub_on_path(tmp_home: Path, make_command_stub) -> None:
    make_command_stub("fake-tool", stdout="ok\n")
    import shutil
    import subprocess

    path = shutil.which("fake-tool")
    assert path is not None
    out = subprocess.run(["fake-tool"], capture_output=True, text=True, check=True)
    assert "ok" in out.stdout


def test_skills_install_defaults_to_interactive_npx(
    tmp_home: Path, stub_bin_dir: Path
) -> None:
    npx = stub_bin_dir / "npx"
    npx.write_text(
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$@\"\n",
        encoding="utf-8",
    )
    npx.chmod(npx.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    result = run_dotf("skills", "-i", "frontend-design")

    assert result.returncode == 0
    assert result.stdout.splitlines()[1:] == [
        "--yes",
        "skills",
        "add",
        "frontend-design",
    ]


def test_skills_install_dry_run_can_select_project(
    tmp_home: Path, make_command_stub
) -> None:
    make_command_stub("npx", stdout="should not execute\n")

    result = run_dotf(
        "skills",
        "-i",
        "frontend-design",
        "-s",
        "demo",
        "--project",
        "--agent",
        "cursor",
        "--dry-run",
    )

    assert result.returncode == 0
    assert "should not execute" not in result.stdout
    assert "==> npx skills add frontend-design -s demo --agent cursor" in result.stdout


def test_skills_install_global_and_yes_pass_through(stub_bin_dir: Path) -> None:
    npx = stub_bin_dir / "npx"
    npx.write_text(
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$@\"\n",
        encoding="utf-8",
    )
    npx.chmod(npx.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    result = run_dotf("skills", "-i", "frontend-design", "-g", "-y")

    assert result.returncode == 0
    assert result.stdout.splitlines()[1:] == [
        "--yes",
        "skills",
        "add",
        "frontend-design",
        "-g",
        "-y",
    ]


def test_skills_install_rejects_project_global_conflict(tmp_home: Path) -> None:
    result = run_dotf("skills", "-i", "frontend-design", "-g", "--project")

    assert result.returncode != 0
    assert "只能二选一" in result.stdout


def test_skills_install_resolves_mapped_name(tmp_home: Path) -> None:
    result = run_dotf("skills", "-i", "taste-skill", "--dry-run")

    assert result.returncode == 0
    assert (
        "==> npx skills add https://github.com/Leonxlnx/taste-skill"
        " -s design-taste-frontend" in result.stdout
    )


def test_skills_install_resolves_multiple_mapped_skills(tmp_home: Path) -> None:
    result = run_dotf("skills", "-i", "ui-template", "--dry-run")

    assert result.returncode == 0
    assert (
        "==> npx skills add sunzhenkai/ui-templates-skill"
        " -s ui-template-author -s ui-template-apply"
        " -s ui-template-design" in result.stdout
    )


def test_skills_uninstall_resolves_mapped_name(tmp_home: Path) -> None:
    result = run_dotf("skills", "-r", "taste-skill", "--dry-run")

    assert result.returncode == 0
    assert "==> npx skills remove design-taste-frontend" in result.stdout


def test_skills_uninstall_resolves_multiple_mapped_skills(tmp_home: Path) -> None:
    result = run_dotf("skills", "-r", "ui-template", "--dry-run")

    assert result.returncode == 0
    assert (
        "==> npx skills remove ui-template-author"
        " ui-template-apply ui-template-design" in result.stdout
    )


def test_skills_uninstall_passthrough_and_interactive(tmp_home: Path) -> None:
    result = run_dotf("skills", "--uninstall", "frontend-design", "--dry-run")

    assert result.returncode == 0
    assert "==> npx skills remove frontend-design" in result.stdout

    result = run_dotf("skills", "-r", "--dry-run")

    assert result.returncode == 0
    assert "==> npx skills remove\n" in result.stdout


def test_tmp_state_dir_ready(tmp_state_dir: Path, tmp_home: Path) -> None:
    assert tmp_state_dir.is_dir()
    assert tmp_state_dir.is_relative_to(tmp_home)
