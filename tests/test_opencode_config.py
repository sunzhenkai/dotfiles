"""OpenCode vendor→目标 merge、安装，以及不再提供 -f 切换。"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


from dotf_core.config_producers import opencode_merge as merge  # noqa: E402

VENDOR = ROOT / "agents" / "vendors" / "opencode"
VENDOR_JSON = VENDOR / "opencode.json"


def _vendor() -> dict:
    return json.loads(VENDOR_JSON.read_text(encoding="utf-8"))


def _install(tmp_home: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["DOTFILES_ROOT"] = str(ROOT)
    env.pop("DOTF_OPENCODE_PROFILE", None)
    script = r"""
set -euo pipefail
source "$DOTFILES_ROOT/scripts/lib/config_safe.sh"
source "$DOTFILES_ROOT/scripts/lib/registry.sh"
source "$DOTFILES_ROOT/scripts/lib/dispatch_config.sh"
install_opencode
"""
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )


def test_vendor_declares_no_provider_or_model() -> None:
    vendor = _vendor()
    assert "provider" not in vendor
    assert "model" not in vendor
    assert vendor["$schema"] == "https://opencode.ai/config.json"
    assert set(vendor["agents"]) == {"build", "plan"}


def test_vendor_declares_opencode_plugins_and_drops_legacy_file() -> None:
    plugins = _vendor()["plugins"]
    names = {entry.split("@", 1)[0] for entry in plugins if isinstance(entry, str)}
    assert "oh-my-opencode-slim" in names
    assert "opencode-sessions-sidebar" in names
    assert "opencode-user-timeline" in names
    # v2 原生键取代了 v1 时代的独立 plugins.json（{"plugin": [...]}，已移除）
    assert not (VENDOR / "plugins.json").exists()


def test_vendor_files_have_no_company_secrets() -> None:
    ip_re = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
    key_re = re.compile(r"\bsk-[A-Za-z0-9]{8,}\b")
    text = VENDOR_JSON.read_text(encoding="utf-8")
    assert not ip_re.search(text)
    assert not key_re.search(text)
    assert "39.106" not in text
    assert "NATIVEX_API_KEY" not in text
    assert "COMPANY_API_KEY" not in text
    assert "nativex.com" not in text
    assert "nativex" not in text
    assert '"company"' not in text


def test_merge_preserves_existing_and_fills_vendor_defaults() -> None:
    vendor = _vendor()
    existing = {
        "model": "local/ollama-qwen",
        "provider": {"ollama": {"name": "Local Ollama"}},
        "agents": {"build": {"system": "local"}},
    }
    out = merge(existing, vendor)
    assert out["model"] == "local/ollama-qwen"
    assert out["agents"] == existing["agents"]
    assert out["provider"] == existing["provider"]
    assert out["$schema"] == vendor["$schema"]
    assert out["plugins"] == vendor["plugins"]


def test_merge_unions_plugins_vendor_first_and_dedupes() -> None:
    vendor = {"plugins": ["a@1", "b"]}
    existing = {"plugins": ["b", "c"]}
    out = merge(existing, vendor)
    assert out["plugins"] == ["a@1", "b", "c"]


def test_merge_keeps_local_plugins_when_vendor_declares_none() -> None:
    out = merge({"plugins": ["local-only"]}, {"$schema": "x"})
    assert out["plugins"] == ["local-only"]
    assert "plugins" not in merge({}, {"$schema": "x"})


def test_merge_uses_vendor_doc_when_no_existing() -> None:
    out = merge({}, _vendor())
    assert out == _vendor()


def test_install_opencode_uses_vendor_doc(tmp_home: Path) -> None:
    r = _install(tmp_home)
    assert r.returncode == 0, r.stdout + r.stderr
    target = tmp_home / ".config" / "opencode"
    cfg = json.loads((target / "opencode.json").read_text(encoding="utf-8"))
    assert cfg == _vendor()
    assert "COMPANY_BASE_URL" not in json.dumps(cfg)
    assert not (target / ".dotf-profile").exists()


def test_install_opencode_keeps_existing_keys_on_reinstall(tmp_home: Path) -> None:
    target = tmp_home / ".config" / "opencode"
    r = _install(tmp_home)
    assert r.returncode == 0, r.stdout + r.stderr
    cfg_path = target / "opencode.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg["model"] = "local/ollama-qwen"
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    r = _install(tmp_home)
    assert r.returncode == 0, r.stdout + r.stderr
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert cfg["model"] == "local/ollama-qwen"
    assert cfg["agents"] == _vendor()["agents"]
    assert cfg["plugins"] == _vendor()["plugins"]
    assert not (target / ".dotf-profile").exists()


def test_cli_rejects_llm_provider_switch_flags() -> None:
    for args in (
        ["opencode", "-f", "kimi", "--dry-run"],
        ["opencode", "-f"],
        ["opencode", "--opencode-profile", "kimi", "--dry-run"],
        ["opencode", "-c", "--profile", "kimi", "--dry-run"],
    ):
        result = subprocess.run(
            ["bash", str(ROOT / "bin" / "dotf"), *args],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            check=False,
        )
        combined = result.stdout + result.stderr
        if "--profile" in args:
            assert "LLM provider" not in combined
            assert result.returncode == 0, combined
            assert "config" in result.stdout and "opencode" in result.stdout
            continue
        assert result.returncode != 0, args
        assert "未知选项" in combined
