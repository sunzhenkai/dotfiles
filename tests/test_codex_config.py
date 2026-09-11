"""Codex merge, managed catalogs, default MiniMax install, and no LLM -f CLI."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "modules" / "codex"))
from merge_config import expand_env, merge  # noqa: E402

VENDOR = ROOT / "agents" / "vendors" / "codex"
CATALOG_NAMES = {
    "kimi-catalog.json",
    "minimax-catalog.json",
    "scnet-catalog.json",
    "deepseek-catalog.json",
    "zhipu-catalog.json",
}


def _install(tmp_home: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["DOTFILES_ROOT"] = str(ROOT)
    env.pop("DOTF_CODEX_PROFILE", None)
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


def test_vendor_declares_all_providers_without_overlays() -> None:
    document = tomllib.loads((VENDOR / "config.toml").read_text(encoding="utf-8"))
    assert document["model_provider"] == "minimax"
    assert document["model"] == "MiniMax-M3"
    for name in ("minimax", "kimi", "zhipu", "scnet", "deepseek"):
        assert name in document["model_providers"]
    assert "nativex" not in document["model_providers"]
    assert "company" not in document["model_providers"]
    assert not list(VENDOR.glob("*.config.toml"))


def test_merge_appends_local_projects() -> None:
    base = 'model = "MiniMax-M3"\nmodel_provider = "minimax"\n'
    local = '[projects."/tmp/demo"]\ntrust_level = "trusted"\n'
    out = merge(base, local)
    assert 'model_provider = "minimax"' in out
    assert 'trust_level = "trusted"' in out
    assert "XDG dotf overlay" in out


def test_merge_harvests_runtime_projects_and_prefers_local() -> None:
    base = (VENDOR / "config.toml").read_text(encoding="utf-8")
    actual = merge(base)
    actual += (
        '\n[projects."/tmp/runtime"]\n'
        'trust_level = "trusted"\n'
        '\n[projects."/tmp/overlay"]\n'
        'trust_level = "untrusted"\n'
    )
    local = '[projects."/tmp/overlay"]\ntrust_level = "trusted"\n'
    out = merge(base, local, actual=actual)
    preamble = out.split("[model_providers")[0]
    assert 'model_provider = "minimax"' in preamble
    assert 'model = "MiniMax-M3"' in preamble
    parsed = tomllib.loads(out)
    assert parsed["projects"]["/tmp/runtime"]["trust_level"] == "trusted"
    assert parsed["projects"]["/tmp/overlay"]["trust_level"] == "trusted"


def test_all_catalogs_are_valid_repository_json() -> None:
    document = tomllib.loads((VENDOR / "config.toml").read_text(encoding="utf-8"))
    value = document["model_catalog_json"]
    prefix = "~/.codex/model-catalogs/"
    assert value.startswith(prefix)
    names = {path.name for path in (VENDOR / "model-catalogs").glob("*.json")}
    assert names == CATALOG_NAMES
    assert value.removeprefix(prefix) in names
    for path in sorted((VENDOR / "model-catalogs").glob("*.json")):
        parsed = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict) and isinstance(parsed.get("models"), list), path
        assert parsed["models"], path


def test_install_codex_manages_config_and_catalogs_only_and_preserves_runtime(
    tmp_home: Path,
) -> None:
    codex_home = tmp_home / ".codex"
    (codex_home / "sessions").mkdir(parents=True)
    (codex_home / "auth.json").write_text('{"token":"local-only"}\n', encoding="utf-8")
    (codex_home / "history.jsonl").write_text('{"local":true}\n', encoding="utf-8")
    (codex_home / "sessions" / "local.json").write_text("{}\n", encoding="utf-8")
    sock = codex_home / "app-server-control" / "app-server-control.sock"
    sock.parent.mkdir(parents=True)
    os.mknod(sock, mode=stat.S_IFSOCK | 0o600)
    (codex_home / "state_5.sqlite").write_bytes(b"runtime-db")

    first = _install(tmp_home)
    assert first.returncode == 0, first.stdout + first.stderr
    cfg_path = codex_home / "config.toml"
    cfg = cfg_path.read_text(encoding="utf-8")
    preamble = cfg.split("[model_providers")[0]
    assert 'model_provider = "minimax"' in preamble
    assert 'model = "MiniMax-M3"' in preamble

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
    assert stat.S_ISSOCK(sock.lstat().st_mode)
    assert (codex_home / "state_5.sqlite").read_bytes() == b"runtime-db"
    assert not (codex_home / ".dotf-profile").exists()
    assert not list(codex_home.glob("*.config.toml"))

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


def test_install_codex_reconciles_runtime_projects_on_reinstall(tmp_home: Path) -> None:
    first = _install(tmp_home)
    assert first.returncode == 0, first.stdout + first.stderr
    cfg_path = tmp_home / ".codex" / "config.toml"
    cfg_path.write_text(
        cfg_path.read_text(encoding="utf-8")
        + '\n[projects."/tmp/runtime"]\ntrust_level = "trusted"\n',
        encoding="utf-8",
    )

    harvested = _install(tmp_home)
    assert harvested.returncode == 0, harvested.stdout + harvested.stderr
    cfg = cfg_path.read_text(encoding="utf-8")
    preamble = cfg.split("[model_providers")[0]
    assert 'model_provider = "minimax"' in preamble
    assert 'model = "MiniMax-M3"' in preamble
    parsed = tomllib.loads(cfg)
    assert parsed["projects"]["/tmp/runtime"]["trust_level"] == "trusted"

    again = _install(tmp_home)
    assert again.returncode == 0, again.stdout + again.stderr
    assert "unchanged" in again.stdout
    assert tomllib.loads(cfg_path.read_text(encoding="utf-8"))["projects"]["/tmp/runtime"][
        "trust_level"
    ] == "trusted"


def test_cli_rejects_llm_provider_switch_flags() -> None:
    for args in (
        ["codex", "-f", "kimi", "--dry-run"],
        ["-f", "kimi", "--dry-run"],
        ["codex", "-f"],
        ["codex", "--codex-profile", "kimi", "--dry-run"],
    ):
        result = subprocess.run(
            ["bash", str(ROOT / "bin" / "dotf"), *args],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            check=False,
        )
        combined = result.stdout + result.stderr
        assert result.returncode != 0, args
        assert "未知选项" in combined


def test_cli_profile_is_not_llm_provider_rewrite() -> None:
    result = subprocess.run(
        ["bash", str(ROOT / "bin" / "dotf"), "nvim", "-c", "--profile", "kimi", "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    combined = result.stdout + result.stderr
    assert "LLM provider" not in combined
    assert "dotf {codex,opencode} -f" not in combined
    assert result.returncode == 0, combined
    assert "config" in result.stdout and "nvim" in result.stdout


def test_expand_env_replaces_placeholders() -> None:
    text = 'base_url = "${EXAMPLE_BASE_URL}"\nenv_key = "EXAMPLE_API_KEY"\n'
    out = expand_env(text, {"EXAMPLE_BASE_URL": "http://127.0.0.1:9/v1"})
    assert 'base_url = "http://127.0.0.1:9/v1"' in out
    assert "${EXAMPLE_BASE_URL}" not in out


def test_expand_env_keeps_placeholder_when_unset() -> None:
    text = 'base_url = "${EXAMPLE_BASE_URL}"\n'
    assert expand_env(text, {}) == text


def test_merge_expands_placeholders(monkeypatch: object) -> None:
    monkeypatch.setenv("EXAMPLE_BASE_URL", "http://127.0.0.1:9/v1")
    base = (
        'model = "MiniMax-M3"\nmodel_provider = "minimax"\n\n'
        '[model_providers.demo]\nbase_url = "${EXAMPLE_BASE_URL}"\n'
    )
    out = merge(base)
    assert 'base_url = "http://127.0.0.1:9/v1"' in out
    assert "${EXAMPLE_BASE_URL}" not in out


def test_vendor_files_have_no_company_secrets() -> None:
    import re

    ip_re = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
    key_re = re.compile(r"\bsk-[A-Za-z0-9]{8,}\b")
    banned = ("NATIVEX_API_KEY", "COMPANY_API_KEY", "COMPANY_BASE_URL", "nativex.com", "ailink.")
    paths = [
        VENDOR / "config.toml",
        VENDOR / "README.md",
        ROOT / "agents" / "env" / "env.schema.yaml",
        ROOT / "agents" / "env" / "template-bases" / "opencode.json",
        *[VENDOR / "model-catalogs" / name for name in CATALOG_NAMES],
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert not ip_re.search(text.replace("127.0.0.1", "")), f"{path} leaked an IP"
        assert not key_re.search(text), f"{path} leaked a token"
        for token in banned:
            assert token not in text, f"{path} still mentions {token}"
