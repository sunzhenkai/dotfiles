"""Codex provider merge, managed catalogs, profile listing, and CLI -f contracts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "modules" / "codex"))
from merge_config import (  # noqa: E402
    ALIASES,
    current_profile_from_config,
    expand_env,
    describe_profiles,
    list_profiles,
    merge,
    overlay,
    resolve_profile_name,
)

VENDOR = ROOT / "agents" / "vendors" / "codex"
CATALOG_NAMES = {
    "company-catalog.json",
    "kimi-catalog.json",
    "minimax-catalog.json",
    "nativex-catalog.json",
    "scnet-catalog.json",
    "zhipu-catalog.json",
}


def _install(tmp_home: Path, profile: str = "scnet") -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["DOTFILES_ROOT"] = str(ROOT)
    env["DOTF_CODEX_PROFILE"] = profile
    script = r"""
set -euo pipefail
source "$DOTFILES_ROOT/scripts/lib/config_safe.sh"
source "$DOTFILES_ROOT/scripts/modules.sh"
source "$DOTFILES_ROOT/scripts/config.sh"
install_codex
"""
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )


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
    assert "XDG dotf overlay" in out


def test_all_profile_catalog_references_are_valid_repository_json() -> None:
    inputs = [VENDOR / "config.toml", *sorted(VENDOR.glob("*.config.toml"))]
    referenced: set[str] = set()
    for path in inputs:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
        value = document["model_catalog_json"]
        prefix = "~/.codex/model-catalogs/"
        assert value.startswith(prefix), path
        name = value.removeprefix(prefix)
        catalog = VENDOR / "model-catalogs" / name
        parsed = json.loads(catalog.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict) and isinstance(parsed.get("models"), list), catalog
        assert parsed["models"], catalog
        referenced.add(name)
    assert referenced == CATALOG_NAMES


def test_install_codex_manages_config_and_catalogs_only_and_preserves_runtime(
    tmp_home: Path,
) -> None:
    codex_home = tmp_home / ".codex"
    (codex_home / "sessions").mkdir(parents=True)
    (codex_home / "auth.json").write_text('{"token":"local-only"}\n', encoding="utf-8")
    (codex_home / "history.jsonl").write_text('{"local":true}\n', encoding="utf-8")
    (codex_home / "sessions" / "local.json").write_text("{}\n", encoding="utf-8")

    first = _install(tmp_home)
    assert first.returncode == 0, first.stdout + first.stderr
    cfg_path = codex_home / "config.toml"
    cfg = cfg_path.read_text(encoding="utf-8")
    preamble = cfg.split("[model_providers")[0]
    assert 'model_provider = "scnet"' in preamble
    assert 'model = "DeepSeek-V4-Flash-0731"' in preamble

    installed_catalogs = codex_home / "model-catalogs"
    assert {path.name for path in installed_catalogs.glob("*.json")} == CATALOG_NAMES
    selected_catalog = Path(
        tomllib.loads(cfg)["model_catalog_json"].replace("~", str(tmp_home), 1)
    )
    assert selected_catalog.is_file()
    assert not selected_catalog.is_symlink()
    for catalog in installed_catalogs.glob("*.json"):
        assert catalog.is_file() and not catalog.is_symlink()
        assert json.loads(catalog.read_text(encoding="utf-8"))["models"]

    assert (codex_home / "auth.json").read_text(encoding="utf-8") == '{"token":"local-only"}\n'
    assert (codex_home / "history.jsonl").read_text(encoding="utf-8") == '{"local":true}\n'
    assert (codex_home / "sessions" / "local.json").is_file()
    assert not (codex_home / ".dotf-profile").exists()
    for profile in list_profiles(VENDOR):
        assert not (codex_home / f"{profile}.config.toml").exists()

    manifest_path = tmp_home / ".local" / "state" / "dotf" / "config-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    codex_items = [item for item in manifest["items"] if item["owner"] == "config:codex"]
    assert {Path(item["target"]).relative_to(codex_home).as_posix() for item in codex_items} == {
        "config.toml",
        *(f"model-catalogs/{name}" for name in CATALOG_NAMES),
    }
    assert all(item["strategy"] == "merge" and item["sensitive"] for item in codex_items)

    mtimes = {path: path.stat().st_mtime_ns for path in [cfg_path, *installed_catalogs.glob("*.json")]}
    manifest_before = manifest_path.read_bytes()
    second = _install(tmp_home)
    assert second.returncode == 0, second.stdout + second.stderr
    assert "unchanged" in second.stdout
    assert {path: path.stat().st_mtime_ns for path in mtimes} == mtimes
    assert manifest_path.read_bytes() == manifest_before


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
    assert not (tmp_home / ".codex" / "company.config.toml").exists()
    assert (tmp_home / ".codex" / "model-catalogs" / "company-catalog.json").exists()


def test_cli_codex_f_dry_run() -> None:
    result = subprocess.run(
        ["bash", str(ROOT / "bin" / "dotf"), "codex", "-f", "kimi", "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "config" in result.stdout and "codex" in result.stdout


def test_cli_f_rejected_for_other_modules() -> None:
    result = subprocess.run(
        ["bash", str(ROOT / "bin" / "dotf"), "nvim", "-c", "-f", "kimi", "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert result.returncode != 0
    assert "codex" in (result.stdout + result.stderr).lower()


def test_unknown_profile_resolve_fails() -> None:
    result = subprocess.run(
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
    assert result.returncode == 2
    assert "未知" in result.stderr
    assert "kimi" in result.stderr


def test_cli_codex_f_lists_installed_current_or_deterministic_default(tmp_home: Path) -> None:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    marker = tmp_home / ".codex" / ".dotf-profile"
    marker.parent.mkdir(parents=True)
    marker.write_text("kimi\n", encoding="utf-8")

    fallback = subprocess.run(
        ["bash", str(ROOT / "bin" / "dotf"), "codex", "-f"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert fallback.returncode == 0, fallback.stdout + fallback.stderr
    out = fallback.stdout
    assert "可用 Codex profile" in out
    for name in ("minimax", "nativex", "company", "kimi", "zhipu", "scnet"):
        assert name in out
    assert "kimi-for-coding" in out
    assert "vanchin/deepseek-v4-pro-0813" in out
    assert "DeepSeek-V4-Flash-0731" in out
    assert "glm-5.3" in out
    assert "* minimax" in out
    assert "当前默认: minimax" in out
    assert "用法: dotf codex -f <profile>" in out

    (tmp_home / ".codex" / "config.toml").write_text(
        'model = "glm-5.3"\nmodel_provider = "zhipu"\n', encoding="utf-8"
    )
    installed = subprocess.run(
        ["bash", str(ROOT / "bin" / "dotf"), "codex", "-f"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    assert "* zhipu" in installed.stdout
    assert "当前默认: zhipu" in installed.stdout
    assert "用法: dotf codex -f <profile>" in installed.stdout


def test_current_profile_helper_rejects_marker_and_non_regular_config(tmp_home: Path) -> None:
    marker = tmp_home / ".dotf-profile"
    marker.write_text("kimi\n", encoding="utf-8")
    assert current_profile_from_config(VENDOR, None) == "minimax"
    directory = tmp_home / "config.toml"
    directory.mkdir()
    assert current_profile_from_config(VENDOR, directory) == "minimax"


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
    text = describe_profiles(VENDOR, current="bigmodel")
    assert "* zhipu" in text
    assert "bigmodel" in text
    assert "当前默认: zhipu" in text
