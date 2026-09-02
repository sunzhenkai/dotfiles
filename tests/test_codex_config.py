"""Codex provider merge、profile 解析与 CLI -f 透传。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "modules" / "codex"))
from merge_config import (  # noqa: E402
    ALIASES,
    expand_env,
    list_profiles,
    merge,
    overlay,
    resolve_profile_name,
)

VENDOR = ROOT / "agents" / "vendors" / "codex"


def test_list_profiles_includes_new_providers() -> None:
    names = list_profiles(VENDOR)
    for name in ("minimax", "nativex", "company", "kimi", "zhipu", "scnet"):
        assert name in names


def test_bigmodel_alias_resolves_to_zhipu() -> None:
    assert resolve_profile_name("bigmodel") == "zhipu"
    assert ALIASES["zai"] == "zhipu"
    rc = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "modules" / "codex" / "merge_config.py"),
            "--vendor-dir",
            str(VENDOR),
            "--resolve",
            "bigmodel",
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert rc.returncode == 0, rc.stderr
    assert rc.stdout.splitlines()[0] == "zhipu"
    assert rc.stdout.splitlines()[1].endswith("zhipu.config.toml")


def test_overlay_replaces_top_level_keys() -> None:
    base = (VENDOR / "config.toml").read_text(encoding="utf-8")
    profile = (VENDOR / "kimi.config.toml").read_text(encoding="utf-8")
    out = overlay(base, profile)
    assert 'model_provider = "kimi"' in out
    assert 'model = "kimi-for-coding"' in out
    assert 'model_provider = "minimax"' not in out.split("[model_providers")[0]
    assert "[model_providers.kimi]" in out
    assert "[model_providers.scnet]" in out
    assert "[model_providers.zhipu]" in out
    assert "[model_providers.company]" in out
    assert 'base_url = "${COMPANY_BASE_URL}"' in out


def test_merge_appends_local_projects() -> None:
    base = 'model = "MiniMax-M3"\nmodel_provider = "minimax"\n'
    profile = 'model = "k3"\nmodel_provider = "kimi"\n'
    local = '[projects."/tmp/demo"]\ntrust_level = "trusted"\n'
    out = merge(base, profile, local)
    assert 'model_provider = "kimi"' in out
    assert 'trust_level = "trusted"' in out
    assert "config.local.toml" in out


def test_install_codex_applies_profile(tmp_home: Path) -> None:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["DOTFILES_ROOT"] = str(ROOT)
    env["DOTF_CODEX_PROFILE"] = "scnet"
    script = r"""
set -euo pipefail
source "$DOTFILES_ROOT/scripts/lib/config_safe.sh"
source "$DOTFILES_ROOT/scripts/modules.sh"
source "$DOTFILES_ROOT/scripts/config.sh"
install_codex
"""
    r = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    cfg = (tmp_home / ".codex" / "config.toml").read_text(encoding="utf-8")
    preamble = cfg.split("[model_providers")[0]
    assert 'model_provider = "scnet"' in preamble
    assert 'model = "DeepSeek-V4-Flash-0731"' in preamble
    assert (tmp_home / ".codex" / ".dotf-profile").read_text(encoding="utf-8").strip() == "scnet"
    assert (tmp_home / ".codex" / "kimi.config.toml").exists() or (
        tmp_home / ".codex" / "kimi.config.toml"
    ).is_symlink()
    assert (tmp_home / ".codex" / "model-catalogs" / "scnet-catalog.json").exists()
    assert (tmp_home / ".codex" / "model-catalogs" / "minimax-catalog.json").exists()


def test_install_codex_expands_company_url(tmp_home: Path) -> None:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["DOTFILES_ROOT"] = str(ROOT)
    env["DOTF_CODEX_PROFILE"] = "company"
    env["COMPANY_BASE_URL"] = "http://127.0.0.1:9/v1"
    env["COMPANY_API_KEY"] = "sk-test-not-a-secret"
    script = r"""
set -euo pipefail
source "$DOTFILES_ROOT/scripts/lib/config_safe.sh"
source "$DOTFILES_ROOT/scripts/modules.sh"
source "$DOTFILES_ROOT/scripts/config.sh"
install_codex
"""
    r = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    cfg = (tmp_home / ".codex" / "config.toml").read_text(encoding="utf-8")
    preamble = cfg.split("[model_providers")[0]
    assert 'model_provider = "company"' in preamble
    assert 'model = "vanchin/deepseek-v4-pro-0813"' in preamble
    assert 'base_url = "http://127.0.0.1:9/v1"' in cfg
    assert "${COMPANY_BASE_URL}" not in cfg
    assert (tmp_home / ".codex" / "company.config.toml").exists() or (
        tmp_home / ".codex" / "company.config.toml"
    ).is_symlink()
    assert (tmp_home / ".codex" / "model-catalogs" / "company-catalog.json").exists()


def test_cli_codex_f_dry_run() -> None:
    r = subprocess.run(
        ["bash", str(ROOT / "bin" / "dotf"), "codex", "-f", "kimi", "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "config" in r.stdout and "codex" in r.stdout


def test_cli_f_rejected_for_other_modules() -> None:
    r = subprocess.run(
        ["bash", str(ROOT / "bin" / "dotf"), "nvim", "-c", "-f", "kimi", "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode != 0
    combined = r.stdout + r.stderr
    assert "codex" in combined.lower()


def test_unknown_profile_resolve_fails() -> None:
    rc = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "modules" / "codex" / "merge_config.py"),
            "--vendor-dir",
            str(VENDOR),
            "--resolve",
            "not-a-provider",
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert rc.returncode == 2
    assert "未知" in rc.stderr
    assert "kimi" in rc.stderr


def test_cli_codex_f_lists_profiles() -> None:
    r = subprocess.run(
        ["bash", str(ROOT / "bin" / "dotf"), "codex", "-f"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    out = r.stdout
    assert "可用 Codex profile" in out
    for name in ("minimax", "nativex", "company", "kimi", "zhipu", "scnet"):
        assert name in out
    assert "kimi-for-coding" in out
    assert "vanchin/deepseek-v4-pro-0813" in out
    assert "DeepSeek-V4-Flash-0731" in out
    assert "glm-5.3" in out
    assert "用法: dotf codex -f <profile>" in out


def test_expand_env_replaces_company_base_url() -> None:
    text = 'base_url = "${COMPANY_BASE_URL}"\nenv_key = "COMPANY_API_KEY"\n'
    out = expand_env(text, {"COMPANY_BASE_URL": "http://127.0.0.1:9/v1"})
    assert 'base_url = "http://127.0.0.1:9/v1"' in out
    assert "${COMPANY_BASE_URL}" not in out


def test_expand_env_keeps_placeholder_when_unset() -> None:
    text = 'base_url = "${COMPANY_BASE_URL}"\n'
    assert expand_env(text, {}) == text


def test_merge_expands_company_base_url(monkeypatch: object) -> None:
    monkeypatch.setenv("COMPANY_BASE_URL", "http://127.0.0.1:9/v1")
    base = (VENDOR / "config.toml").read_text(encoding="utf-8")
    profile = (VENDOR / "company.config.toml").read_text(encoding="utf-8")
    out = merge(base, profile, None)
    assert 'model_provider = "company"' in out.split("[model_providers")[0]
    assert 'base_url = "http://127.0.0.1:9/v1"' in out
    assert "${COMPANY_BASE_URL}" not in out
    assert "39.106" not in out


def test_vendor_files_have_no_company_secrets() -> None:
    import re

    ip_re = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
    key_re = re.compile(r"\bsk-[A-Za-z0-9]{8,}\b")
    paths = [
        VENDOR / "config.toml",
        VENDOR / "company.config.toml",
        VENDOR / "README.md",
        VENDOR / "model-catalogs" / "company-catalog.json",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert not ip_re.search(text), f"{path} leaked an IP"
        assert not key_re.search(text), f"{path} leaked a token"


def test_describe_profiles_marks_current_and_aliases() -> None:
    from merge_config import describe_profiles

    text = describe_profiles(VENDOR, current="bigmodel")
    assert "* zhipu" in text
    assert "bigmodel" in text
    assert "当前默认: zhipu" in text
