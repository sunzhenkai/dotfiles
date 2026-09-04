"""CI, workflow, pytest collection, and state-boundary documentation contracts."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_pytest_module_basenames_are_unique_without_importlib_mode() -> None:
    files = [*ROOT.glob("tests/test*.py"), *ROOT.glob("agents/skills/**/tests/test*.py")]
    counts = Counter(path.name for path in files)
    duplicates = sorted(name for name, count in counts.items() if count > 1)
    assert duplicates == [], f"plain pytest import collisions: {duplicates}"
    assert not (ROOT / "pytest.ini").exists()
    assert "--import-mode=importlib" not in _text("Makefile")


def test_make_ci_exposes_every_mandatory_linux_gate_without_skip() -> None:
    makefile = _text("Makefile")
    assert "python3 -m pytest -q" in makefile
    assert "validate --strict-handlers" in makefile
    for target in ("shellcheck", "templates", "secret-scan", "acceptance", "smoke", "bash32"):
        assert re.search(rf"^ci:.*\b{re.escape(target)}\b", makefile, re.MULTILINE)
    assert "git diff --exit-code -- $(TEMPLATE_OUTPUTS)" in makefile
    assert "skip shellcheck" not in makefile
    assert "command -v shellcheck >/dev/null &&" not in makefile


def test_shellcheck_inventory_is_git_tracked_and_exclusions_are_visible() -> None:
    script = _text("scripts/ci/shellcheck-first-party.sh")
    assert "git ls-files -z" in script
    assert "selected=$selected_count excluded_third_party=$excluded_count" in script
    assert "config/multiplexers/tmux/3rd/*" in script
    assert "agents/skills/pretty-view-ppt/references/html-ppt/*" in script
    assert "shellcheck is required (no silent skip)" in script


def test_linux_workflow_runs_make_ci_with_immutable_action_pins() -> None:
    workflow = _text(".github/workflows/ci.yml")
    assert "runs-on: ubuntu-24.04" in workflow
    assert "run: make ci" in workflow
    assert "shellcheck=0.9.0-1" in workflow
    assert "PyYAML==6.0.3 pytest==9.1.1" in workflow
    action_uses = re.findall(r"uses:\s*[^@\s]+@([^\s]+)", workflow)
    assert action_uses and all(re.fullmatch(r"[0-9a-f]{40}", pin) for pin in action_uses)


def test_macos_workflow_requires_system_bash32_and_migration_smoke() -> None:
    workflow = _text(".github/workflows/ci.yml")
    smoke = _text("scripts/ci/smoke-macos.sh")
    acceptance = _text("scripts/ci/acceptance-isolated-home.sh")
    assert "runs-on: macos-15" in workflow
    assert "shell: /bin/bash {0}" in workflow
    assert "run: /bin/bash scripts/ci/smoke-macos.sh" in workflow
    assert "BASH_VERSINFO[0]" in smoke and "BASH_VERSINFO[1]" in smoke
    assert "-ne 3" in smoke and "-ne 2" in smoke
    combined = (workflow + smoke).lower()
    assert "brew install" not in combined and "brew --prefix" not in combined

    for marker in (
        "TMP_HOME",
        "init --list",
        "legacy writable config-link migration",
        "second config run did not report unchanged",
        "sync.sh\" cursor --profile research",
        "done skills: changed=0 pruned=0 unchanged=",
        "agents:mcp:cursor: unchanged",
        "metadata=inode+mtime+hash-stable",
        "repo_status=unchanged",
        "repo_diff=unchanged",
        "repo_content=unchanged",
    ):
        assert marker in acceptance


def test_isolated_acceptance_fail_closed_contract() -> None:
    acceptance = _text("scripts/ci/acceptance-isolated-home.sh")
    export_home = acceptance.index('export HOME="$TMP_HOME"')
    first_runtime_command = acceptance.index('"$BASH_BIN" "$ROOT/bin/dotf" -h')
    assert export_home < first_runtime_command
    for marker in (
        "unset ZHIPU_API_KEY Z_AI_API_KEY",
        "NETWORK_ATTEMPTED",
        "network/acquisition is disabled",
        "snapshot_paths \"$HOME\"",
        "metadata=mode,inode,mtime,size,sha256",
        "backup_count",
        "repo_before=\"$(repo_snapshot)\"",
        "repo_after=\"$(repo_snapshot)\"",
        "if [ \"$repo_after\" != \"$repo_before\" ]",
        "secrets=none",
    ):
        assert marker in acceptance
    assert "config_rerun=unchanged" not in acceptance


def test_secret_scan_emits_rule_and_count_evidence() -> None:
    scan = _text("scripts/ci/secret-scan.py")
    for marker in ("rule_version=", "scanned=", "skipped=", "findings="):
        assert marker in scan
    assert "check_security_scan" in scan


def test_version_controlled_acceptance_evidence_records_required_gates() -> None:
    evidence = _text("acceptance/harden-dotfiles-state-boundaries.md")
    for marker in (
        "Plain full pytest",
        "Strict registry/handlers",
        "Strict OpenSpec validation",
        "Template check/no delta",
        "First-party ShellCheck",
        "Bash 3.2 syntax",
        "Tracked source secret scan",
        "Isolated doctor parity",
        "Disposable HOME/XDG acceptance",
        "repo_status=unchanged",
        "repo_diff=unchanged",
        "repo_content=unchanged",
        "Staged `.gitignore` blob before and after implementation",
        "`tasks.md` SHA-256 retained without checkbox edits",
    ):
        assert marker in evidence
    assert "- [x]" not in evidence and "- [ ]" not in evidence


def test_state_boundary_docs_cover_operator_contracts() -> None:
    readme = _text("README.md")
    agents = _text("agents/README.md")
    env = _text("agents/env/README.md")
    module_guide = _text(".agents/skills/dotf-install/SKILL.md")
    init_guide = _text(".agents/skills/dotf-init/SKILL.md")
    user_guide = _text("Dotfiles.md")
    kitty_readme = _text("config/terminals/kitty/README.md")
    kitty_usage = _text("config/terminals/kitty/USAGE.md")
    zellij_readme = _text("config/multiplexers/zellij/README.md")
    herdr_readme = _text("config/multiplexers/herdr/README.md")
    tmux_readme = _text("config/multiplexers/tmux/README.md")
    alacritty_readme = _text("config/terminals/alacritty/README.md")
    codex_readme = _text("agents/vendors/codex/README.md")
    cursor_readme = _text("agents/vendors/cursor/README.md")
    kiro_readme = _text("agents/vendors/kiro/README.md")

    assert "managed with symlinks" not in readme
    stale_link_claims = ("是用户级软链", "是软链到 HOME")
    assert all(claim not in module_guide for claim in stale_link_claims)
    assert all(claim not in init_guide for claim in stale_link_claims)
    assert "dotf -a --profile" not in module_guide
    assert "dotf init --profile remote --dry-run" in module_guide
    assert "-a` 始终表示当前 OS 适用模块的完整 all 集合" in module_guide
    for kitty_doc in (kitty_readme, kitty_usage):
        assert "ln -s" not in kitty_doc
        assert "dotf kitty -c --dry-run" in kitty_doc
        assert "真实目录" in kitty_doc
        assert "重新运行 `dotf kitty -c`" in kitty_doc
    assert "将该目录或文件链到" not in zellij_readme
    assert "dotf zellij -c --dry-run" in zellij_readme
    assert "Install and link" not in herdr_readme
    assert "dotf herdr -ic --dry-run" in herdr_readme
    assert not re.search(r"git clone .*~/\.config/alacritty", alacritty_readme)
    assert "dotf alacritty -c --dry-run" in alacritty_readme

    for marker in ("dotf tmux -c --dry-run", "真实目录", "重新运行 `dotf tmux -c`", "copy"):
        assert marker in tmux_readme
    for tool_doc in (cursor_readme, kiro_readme):
        assert "默认 profile 为低风险 `research`" in tool_doc
        assert "--profile browser" in tool_doc and "--profile full" in tool_doc
        assert "默认 profile 为 `browser`" not in tool_doc

    assert "codex --profile" not in codex_readme
    assert "安装到 `~/.codex/<name>.config.toml`" not in codex_readme
    assert "symlink 到本仓库" not in codex_readme
    for marker in (
        "dotf codex -f <name>",
        "仓库内 merge 输入",
        "~/.codex/model-catalogs/*.json",
        "manifest",
        "真实文件",
        "不创建或读取 `.dotf-profile`",
    ):
        assert marker in codex_readme

    for marker in (
        "修改 `config/` 后必须重新运行 `dotf <module> -c`",
        "dotf_core.overlays init",
        "dotf_core.overlays migrate",
        "低风险 `research`",
        "managed manifest",
        "conflict",
        "generate_templates.py",
        "failed-rollback",
        "dotf retry",
        "历史整目录软链",
    ):
        assert marker in readme
    for marker in ("managed manifest", "conflict", "transaction journal", "generate_templates.py"):
        assert marker in agents
    for marker in ("research", "overlays migrate", "managed ownership", "failed-rollback", "rule_version"):
        assert marker in env
    for marker in ("仓库源修改后不会自动传播", "历史整目录软链", "dotf retry"):
        assert marker in module_guide
    for marker in ("重跑 `dotf <module> -c`", "外置 overlay", "failed-rollback"):
        assert marker in user_guide
