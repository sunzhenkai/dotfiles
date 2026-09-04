"""OpenCode provider 合并、默认 model 切换与 CLI -f 透传。"""

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
ALIASES = _merge.ALIASES
MANAGED_PROVIDER_IDS = _merge.MANAGED_PROVIDER_IDS
PROFILES = _merge.PROFILES
merge = _merge.merge
resolve_profile_name = _merge.resolve_profile_name

VENDOR = ROOT / "agents" / "vendors" / "opencode"
VENDOR_JSON = VENDOR / "opencode.json"


def _vendor() -> dict:
    return json.loads(VENDOR_JSON.read_text(encoding="utf-8"))


def test_profiles_match_vendor_providers() -> None:
    vendor = _vendor()
    providers = vendor["provider"]
    assert set(providers) == set(MANAGED_PROVIDER_IDS)
    assert vendor["model"] == PROFILES["minimax"]["model"]
    for name, info in PROFILES.items():
        model = info["model"]
        assert model.startswith(f"{name}/")
        slug = model.split("/", 1)[1]
        assert slug in providers[name]["models"]


def test_company_uses_chat_adapter_and_env_url() -> None:
    company = _vendor()["provider"]["company"]
    assert company["npm"] == "@ai-sdk/openai-compatible"
    assert company["options"]["baseURL"] == "{env:COMPANY_BASE_URL}"
    assert company["options"]["apiKey"] == "{env:COMPANY_API_KEY}"
    assert "vanchin/deepseek-v4-pro-0813" in company["models"]


def test_vendor_files_have_no_company_secrets() -> None:
    ip_re = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
    key_re = re.compile(r"\bsk-[A-Za-z0-9]{8,}\b")
    text = VENDOR_JSON.read_text(encoding="utf-8")
    assert not ip_re.search(text)
    assert not key_re.search(text)
    assert "39.106" not in text


def test_bigmodel_alias_resolves_to_zhipu() -> None:
    assert resolve_profile_name("bigmodel") == "zhipu"
    assert ALIASES["zai"] == "zhipu"
    rc = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "modules" / "opencode" / "merge_config.py"),
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
    assert rc.stdout.splitlines()[1] == "zhipu/glm-5.3"


def test_merge_preserves_mcp_and_local_provider() -> None:
    vendor = _vendor()
    existing = {
        "model": "kimi/k3",
        "mcp": {"keep-me": {"type": "local", "command": ["true"]}},
        "provider": {"ollama": {"name": "Local Ollama"}},
        "agent": {"build": {"prompt": "local"}},
    }
    out = merge(existing, vendor, None)
    assert out["model"] == "kimi/k3"
    assert out["mcp"] == existing["mcp"]
    assert out["agent"] == existing["agent"]
    assert out["provider"]["ollama"] == {"name": "Local Ollama"}
    assert "minimax" in out["provider"]
    assert "company" in out["provider"]


def test_merge_profile_sets_default_model() -> None:
    vendor = _vendor()
    out = merge({"mcp": {"x": 1}}, vendor, "company")
    assert out["model"] == "company/vanchin/deepseek-v4-pro-0813"
    assert out["mcp"] == {"x": 1}


def test_unknown_profile_resolve_fails() -> None:
    rc = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "modules" / "opencode" / "merge_config.py"),
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


def test_install_opencode_applies_profile(tmp_home: Path) -> None:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["DOTFILES_ROOT"] = str(ROOT)
    env["DOTF_OPENCODE_PROFILE"] = "company"
    env["COMPANY_API_KEY"] = "sk-test-not-a-secret"
    env["COMPANY_BASE_URL"] = "http://127.0.0.1:9/v1"
    script = r"""
set -euo pipefail
source "$DOTFILES_ROOT/scripts/lib/config_safe.sh"
source "$DOTFILES_ROOT/scripts/modules.sh"
source "$DOTFILES_ROOT/scripts/config.sh"
install_opencode
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
    cfg = json.loads((tmp_home / ".config" / "opencode" / "opencode.json").read_text(encoding="utf-8"))
    assert cfg["model"] == "company/vanchin/deepseek-v4-pro-0813"
    assert cfg["provider"]["company"]["options"]["baseURL"] == "{env:COMPANY_BASE_URL}"
    assert "http://127.0.0.1:9/v1" not in json.dumps(cfg)
    assert (tmp_home / ".config" / "opencode" / ".dotf-profile").read_text(
        encoding="utf-8"
    ).strip() == "company"


def test_install_opencode_keeps_profile_on_reinstall(tmp_home: Path) -> None:
    target = tmp_home / ".config" / "opencode"
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["DOTFILES_ROOT"] = str(ROOT)
    env["DOTF_OPENCODE_PROFILE"] = "company"
    script = r"""
set -euo pipefail
source "$DOTFILES_ROOT/scripts/lib/config_safe.sh"
source "$DOTFILES_ROOT/scripts/modules.sh"
source "$DOTFILES_ROOT/scripts/config.sh"
install_opencode
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
    cfg = json.loads((target / "opencode.json").read_text(encoding="utf-8"))
    assert cfg["model"] == "company/vanchin/deepseek-v4-pro-0813"

    # Reinstall without the env flag: the persisted profile keeps the model
    # pointer stable instead of falling back to the vendor default.
    env.pop("DOTF_OPENCODE_PROFILE")
    r = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    cfg = json.loads((target / "opencode.json").read_text(encoding="utf-8"))
    assert cfg["model"] == "company/vanchin/deepseek-v4-pro-0813"
    assert (target / ".dotf-profile").read_text(encoding="utf-8").strip() == "company"


def test_cli_opencode_f_dry_run() -> None:
    r = subprocess.run(
        ["bash", str(ROOT / "bin" / "dotf"), "opencode", "-f", "kimi", "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "config" in r.stdout and "opencode" in r.stdout


def test_cli_opencode_f_lists_profiles() -> None:
    r = subprocess.run(
        ["bash", str(ROOT / "bin" / "dotf"), "opencode", "-f"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    out = r.stdout
    assert "可用 OpenCode provider" in out
    for name in ("minimax", "nativex", "company", "kimi", "zhipu", "scnet"):
        assert name in out
    assert "company/vanchin/deepseek-v4-pro-0813" in out
    assert "用法: dotf opencode -f <provider>" in out
