"""Pi settings 目录级 merge：packages 并集、退役包剔除、本机偏好保留。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

from dotf_core.config_producers import pi_settings_merge as merge  # noqa: E402

VENDOR = ROOT / "agents" / "vendors" / "pi"
VENDOR_SETTINGS = VENDOR / "settings.json"


def _vendor() -> dict:
    return json.loads(VENDOR_SETTINGS.read_text(encoding="utf-8"))


def test_vendor_declares_no_provider_model_or_secret() -> None:
    vendor = _vendor()
    assert "defaultModel" not in vendor
    assert "defaultProvider" not in vendor
    assert "theme" not in vendor
    text = VENDOR_SETTINGS.read_text(encoding="utf-8")
    assert not re.search(r"\bsk-[A-Za-z0-9]{8,}\b", text)
    assert not re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text)


def test_vendor_packages_are_declared_defaults() -> None:
    packages = _vendor()["packages"]
    assert packages[0] == "npm:pi-mcp-adapter"
    assert "npm:pi-powerline-footer" in packages
    assert "npm:pi-agent-extensions" not in packages
    assert "npm:pi-subagents" in packages
    assert "npm:@virdis/subagents" not in packages


def test_merge_preserves_local_preferences_and_unions_packages() -> None:
    existing = {
        "defaultModel": "MiniMax-M3",
        "defaultProvider": "senv-TokenApi",
        "lastChangelogVersion": "0.85.1",
        "theme": "dark",
        "packages": ["npm:pi-mcp-adapter", "npm:someone-local-only"],
    }
    out = merge(existing, _vendor())
    assert out["defaultModel"] == "MiniMax-M3"
    assert out["defaultProvider"] == "senv-TokenApi"
    assert out["theme"] == "dark"
    assert out["lastChangelogVersion"] == "0.85.1"
    # 托管布尔键由仓库强制
    assert out["enableSkillCommands"] is True
    assert out["enableInstallTelemetry"] is False
    # packages 取并集，本地独有包保留
    assert "npm:someone-local-only" in out["packages"]
    assert "npm:pi-powerline-footer" in out["packages"]
    assert "npm:pi-mcp-adapter" in out["packages"]


def test_merge_drops_retired_package_from_existing_machine() -> None:
    existing = {
        "packages": [
            "npm:pi-mcp-adapter",
            "npm:@virdis/subagents",
            "npm:pi-agent-extensions",
            "npm:someone-local-only",
        ],
    }
    out = merge(existing, _vendor())
    assert "npm:@virdis/subagents" not in out["packages"]
    assert "npm:pi-agent-extensions" not in out["packages"]
    assert "npm:someone-local-only" in out["packages"]
    assert "npm:pi-subagents" in out["packages"]
    assert "npm:pi-powerline-footer" in out["packages"]


def test_rpiv_todo_is_not_a_default_and_is_retired() -> None:
    # 曾与 pi-agent-extensions 的 todos 重名冲突；合集退役后仍保持剔除。
    assert "npm:@juicesharp/rpiv-todo" not in _vendor()["packages"]
    existing = {
        "packages": ["npm:@juicesharp/rpiv-todo", "npm:pi-agent-extensions"],
    }
    out = merge(existing, _vendor())
    assert "npm:@juicesharp/rpiv-todo" not in out["packages"]
    assert "npm:pi-agent-extensions" not in out["packages"]


def test_merge_uses_vendor_doc_when_no_existing() -> None:
    out = merge({}, _vendor())
    assert out["packages"] == _vendor()["packages"]
    assert out["enableSkillCommands"] is True


def test_merge_is_idempotent() -> None:
    first = merge({}, _vendor())
    second = merge(first, _vendor())
    assert second == first
