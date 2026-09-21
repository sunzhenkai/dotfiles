"""主体优先 CLI 基线契约 — 仅解析/拒绝路径，使用临时 HOME。"""

from __future__ import annotations

from pathlib import Path
import stat

from conftest import isolate_agents_sync_for_test, run_dotf


def test_help_lists_doctor_actions(tmp_home: Path, launch_home: Path) -> None:
    result = run_dotf("-h")
    assert result.returncode == 0
    out = result.stdout
    assert "--doctor" in out
    assert "-icd" in out
    assert "不含 doctor" in out
    assert "skills -c" in out
    assert "LLM provider" not in out
    assert "dotf codex -f" not in out
    assert Path.home().resolve() == tmp_home.resolve()
    assert tmp_home.resolve() != launch_home


def test_agents_research_profile_is_not_llm_provider(tmp_home: Path) -> None:
    result = run_dotf("agents", "-c", "--profile", "research", "--dry-run")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "agents" in result.stdout
    assert "LLM provider" not in (result.stdout + result.stderr)


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


def test_skills_add_resolves_catalog_skill_and_project_scope(tmp_home: Path) -> None:
    result = run_dotf(
        "skills",
        "add",
        "ui-skills-root",
        "--project",
        "--dry-run",
    )

    assert result.returncode == 0
    assert (
        "==> npx skills add https://github.com/ibelick/ui-skills"
        " -s ui-skills-root" in result.stdout
    )


def test_skills_add_resolves_catalog_alias(tmp_home: Path) -> None:
    result = run_dotf("skills", "add", "ppt", "--project", "--dry-run")
    assert result.returncode == 0
    assert (
        "==> npx skills add https://github.com/zarazhangrui/frontend-slides"
        " -s frontend-slides" in result.stdout
    )


def test_skills_add_global_scope_passes_global_flag(tmp_home: Path) -> None:
    result = run_dotf(
        "skills",
        "add",
        "ui-skills-root",
        "--global",
        "--dry-run",
    )

    assert result.returncode == 0
    assert (
        "==> npx skills add https://github.com/ibelick/ui-skills"
        " -s ui-skills-root -g" in result.stdout
    )


def test_skills_add_requires_explicit_scope_without_tty(tmp_home: Path) -> None:
    result = run_dotf("skills", "add", "ui-skills-root", "--dry-run")

    assert result.returncode == 2
    assert "请使用 --global 或 --project" in result.stderr


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


def test_skills_install_resolves_third_party_skill_id(tmp_home: Path) -> None:
    # catalogued third-party id resolves to its package with a -s selector.
    result = run_dotf("skills", "-i", "codebase-design", "--dry-run")

    assert result.returncode == 0
    assert (
        "==> npx skills add https://github.com/mattpocock/skills"
        " -s codebase-design" in result.stdout
    )


def test_skills_install_commented_out_skill_passes_through(tmp_home: Path) -> None:
    # taste-skill / ui-template-* are commented out of the catalog -> plain names.
    for name in ("taste-skill", "ui-template-apply"):
        result = run_dotf("skills", "-i", name, "--dry-run")

        assert result.returncode == 0
        assert f"==> npx skills add {name}" in result.stdout


def test_skills_install_passes_through_unknown_name(tmp_home: Path) -> None:
    # unknown names (not a group or catalogued id) pass through to npx search.
    result = run_dotf("skills", "-i", "frontend-design", "--dry-run")

    assert result.returncode == 0
    assert "==> npx skills add frontend-design" in result.stdout


def test_skills_install_rejects_first_party_skill_id(tmp_home: Path) -> None:
    result = run_dotf("skills", "-i", "commit-push", "--dry-run")

    assert result.returncode != 0
    assert "first-party" in result.stderr


def test_skills_install_resolves_group(tmp_home: Path) -> None:
    result = run_dotf("skills", "-i", "mattpocock", "--dry-run")

    assert result.returncode == 0
    assert (
        "==> npx skills add https://github.com/mattpocock/skills"
        " -s codebase-design -s diagnosing-bugs -s domain-modeling"
        " -s grill-with-docs -s grilling -s setup-matt-pocock-skills"
        " -s to-questionnaire -s wait-what -s wizard"
        " -s writing-for-agents" in result.stdout
    )


def test_skills_uninstall_resolves_third_party_skill_id(tmp_home: Path) -> None:
    result = run_dotf("skills", "-r", "codebase-design", "--dry-run")

    assert result.returncode == 0
    assert "==> npx skills remove codebase-design" in result.stdout


def test_skills_uninstall_resolves_multiple_mapped_skills(tmp_home: Path) -> None:
    result = run_dotf("skills", "-r", "mattpocock", "--dry-run")

    assert result.returncode == 0
    assert (
        "==> npx skills remove codebase-design diagnosing-bugs domain-modeling"
        " grill-with-docs grilling setup-matt-pocock-skills to-questionnaire"
        " wait-what wizard writing-for-agents" in result.stdout
    )


def test_skills_config_dry_run_skips_instructions(tmp_home: Path) -> None:
    isolate_agents_sync_for_test(tmp_home)
    result = run_dotf("skills", "-c", "--dry-run")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "--- skills ---" in result.stdout
    assert "--- default skills ---" in result.stdout
    assert "--- openspec skills ---" in result.stdout
    assert "--- instructions ---" not in result.stdout
    assert "✓ skills 全量安装完成" in result.stdout


def test_skills_config_requires_yes_without_tty(tmp_home: Path) -> None:
    result = run_dotf("skills", "-c")

    assert result.returncode == 2
    assert "非 TTY" in result.stderr


def test_skills_config_rejects_npx_flags_and_extra_args(tmp_home: Path) -> None:
    mixed = run_dotf("skills", "-c", "-g")
    assert mixed.returncode == 1
    assert "npx" in mixed.stderr

    extra = run_dotf("skills", "-c", "frontend-design")
    assert extra.returncode == 1
    assert "额外参数" in extra.stderr


def test_skills_help_lists_config(tmp_home: Path) -> None:
    result = run_dotf("skills", "-h")

    assert result.returncode == 0
    assert "-c 安装编目" in result.stdout
    assert "dotf skills -c --dry-run" in result.stdout


def test_skills_config_yes_installs_first_party_without_agents_md(tmp_home: Path) -> None:
    isolate_agents_sync_for_test(tmp_home)
    result = run_dotf("skills", "-c", "--yes")

    assert result.returncode == 0, result.stdout + result.stderr
    skill_dir = tmp_home / ".agents" / "skills" / "commit-push"
    assert (skill_dir / "SKILL.md").is_file()
    assert not (tmp_home / ".agents" / "AGENTS.md").exists()


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
