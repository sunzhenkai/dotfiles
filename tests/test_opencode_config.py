"""OpenCode provider 合并、默认 MiniMax 安装，以及不再提供 -f 切换。"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_merge():
    path = ROOT / "scripts" / "modules" / "opencode" / "merge_config.py"
    spec = importlib.util.spec_from_file_location("opencode_merge_config", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_merge = _load_merge()
MANAGED_PROVIDER_IDS = _merge.MANAGED_PROVIDER_IDS
DEFAULT_MODEL = _merge.DEFAULT_MODEL
merge = _merge.merge

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
source "$DOTFILES_ROOT/scripts/modules.sh"
source "$DOTFILES_ROOT/scripts/config.sh"
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


def test_vendor_providers_match_managed_ids() -> None:
    vendor = _vendor()
    providers = vendor["provider"]
    assert set(providers) == set(MANAGED_PROVIDER_IDS)
    assert vendor["model"] == DEFAULT_MODEL
    pid, slug = DEFAULT_MODEL.split("/", 1)
    assert slug in providers[pid]["models"]


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


def test_merge_preserves_mcp_and_local_provider() -> None:
    vendor = _vendor()
    existing = {
        "model": "kimi/k3",
        "mcp": {"keep-me": {"type": "local", "command": ["true"]}},
        "provider": {"ollama": {"name": "Local Ollama"}},
        "agent": {"build": {"prompt": "local"}},
    }
    out = merge(existing, vendor)
    assert out["model"] == "kimi/k3"
    assert out["mcp"] == existing["mcp"]
    assert out["agent"] == existing["agent"]
    assert out["provider"]["ollama"] == {"name": "Local Ollama"}
    assert "minimax" in out["provider"]
    assert "kimi" in out["provider"]
    assert "company" not in out["provider"]
    assert "nativex" not in out["provider"]


def test_merge_uses_vendor_default_when_missing_model() -> None:
    vendor = _vendor()
    out = merge({"mcp": {"x": 1}}, vendor)
    assert out["model"] == DEFAULT_MODEL
    assert out["mcp"] == {"x": 1}


def test_install_opencode_uses_vendor_default(tmp_home: Path) -> None:
    r = _install(tmp_home)
    assert r.returncode == 0, r.stdout + r.stderr
    target = tmp_home / ".config" / "opencode"
    cfg = json.loads((target / "opencode.json").read_text(encoding="utf-8"))
    assert cfg["model"] == DEFAULT_MODEL
    assert "COMPANY_BASE_URL" not in json.dumps(cfg)
    assert not (target / ".dotf-profile").exists()


def test_install_opencode_keeps_existing_model_on_reinstall(tmp_home: Path) -> None:
    target = tmp_home / ".config" / "opencode"
    r = _install(tmp_home)
    assert r.returncode == 0, r.stdout + r.stderr
    cfg_path = target / "opencode.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg["model"] = "kimi/kimi-for-coding"
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    r = _install(tmp_home)
    assert r.returncode == 0, r.stdout + r.stderr
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert cfg["model"] == "kimi/kimi-for-coding"
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
