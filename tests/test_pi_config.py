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
    assert packages[0] == "npm:pi-goal-x"
    # 2026-11-06：MCP 改回 Pi 内置扩展，pi-mcp-adapter 退役
    assert "npm:pi-mcp-adapter" not in packages
    assert "npm:pi-powerline-footer" in packages
    assert "npm:pi-agent-extensions" not in packages
    assert "npm:pi-subagents" in packages
    assert "npm:@virdis/subagents" not in packages
    # 2026-09-27 扩容：目标管理换 pi-goal-x，新增上下文/可观测/todo/护栏等
    assert "npm:pi-goal-x" in packages
    assert "npm:@ogulcancelik/pi-goal" not in packages
    assert "npm:billion-context" in packages
    assert "npm:@langfuse/pi-observability-plugin" in packages
    assert "npm:@juicesharp/rpiv-todo" in packages
    assert "npm:pi-lens" in packages
    assert "npm:@gotgenes/pi-permission-system" in packages
    assert "npm:@plannotator/pi-extension" in packages
    assert "npm:@dietrichgebert/ponytail" in packages
    assert "npm:@ff-labs/pi-fff" in packages
    # 2026-11-06 扩容：provider 原生搜索、并行侧对话、记忆、worktree 管理
    assert "npm:pi-web-search" in packages
    assert "npm:pi-btw" in packages
    assert "npm:pi-memory" in packages
    assert "npm:@narumitw/pi-worktree" in packages


def test_web_search_packages_ordered_so_provider_native_wins() -> None:
    # pi-web-access 与 pi-web-search 都注册 web_search；Pi 按 packages 顺序
    # 加载扩展，后注册者覆盖，pi-web-search 必须排在后面。
    packages = _vendor()["packages"]
    assert packages.index("npm:pi-web-search") > packages.index("npm:pi-web-access")


def test_vendor_powerline_shows_tokens_and_cache_hit_rate() -> None:
    powerline = _vendor()["powerline"]
    assert powerline["preset"] == "full"
    assert powerline["cache_read"]["format"] == "both"


def test_merge_preserves_local_preferences_and_unions_packages() -> None:
    existing = {
        "defaultModel": "MiniMax-M3",
        "defaultProvider": "senv-TokenApi",
        "lastChangelogVersion": "0.85.1",
        "theme": "dark",
        "powerline": {"preset": "minimal"},
        "packages": ["npm:some-local-mcp", "npm:someone-local-only"],
    }
    out = merge(existing, _vendor())
    assert out["defaultModel"] == "MiniMax-M3"
    assert out["defaultProvider"] == "senv-TokenApi"
    assert out["theme"] == "dark"
    assert out["lastChangelogVersion"] == "0.85.1"
    # 托管布尔键与 powerline 由仓库强制
    assert out["enableSkillCommands"] is True
    assert out["enableInstallTelemetry"] is False
    assert out["powerline"] == _vendor()["powerline"]
    # packages 取并集，本地独有包保留
    assert "npm:someone-local-only" in out["packages"]
    assert "npm:pi-powerline-footer" in out["packages"]
    assert "npm:some-local-mcp" in out["packages"]


def test_merge_drops_retired_package_from_existing_machine() -> None:
    existing = {
        "packages": [
            "npm:pi-mcp-adapter",
            "npm:@virdis/subagents",
            "npm:pi-agent-extensions",
            "npm:@ogulcancelik/pi-goal",
            "npm:someone-local-only",
        ],
    }
    out = merge(existing, _vendor())
    assert "npm:@virdis/subagents" not in out["packages"]
    assert "npm:pi-agent-extensions" not in out["packages"]
    # pi-goal 换代：旧包从本机剔除，由 pi-goal-x 接替
    assert "npm:@ogulcancelik/pi-goal" not in out["packages"]
    assert "npm:pi-mcp-adapter" not in out["packages"]
    assert "npm:pi-goal-x" in out["packages"]
    assert "npm:someone-local-only" in out["packages"]
    assert "npm:pi-subagents" in out["packages"]
    assert "npm:pi-powerline-footer" in out["packages"]


def test_rpiv_todo_readopted_but_pi_agent_extensions_still_retired() -> None:
    # rpiv-todo 曾因与 pi-agent-extensions 的 todos 冲突退役；后者退役后
    # 于 2026-09-27 重新收编为默认包。pi-agent-extensions 保持剔除。
    assert "npm:@juicesharp/rpiv-todo" in _vendor()["packages"]
    existing = {
        "packages": ["npm:pi-agent-extensions", "npm:@virdis/subagents"],
    }
    out = merge(existing, _vendor())
    assert "npm:pi-agent-extensions" not in out["packages"]
    assert "npm:@virdis/subagents" not in out["packages"]
    assert "npm:@juicesharp/rpiv-todo" in out["packages"]


def test_merge_uses_vendor_doc_when_no_existing() -> None:
    out = merge({}, _vendor())
    assert out["packages"] == _vendor()["packages"]
    assert out["powerline"] == _vendor()["powerline"]
    assert out["enableSkillCommands"] is True


def test_merge_is_idempotent() -> None:
    first = merge({}, _vendor())
    second = merge(first, _vendor())
    assert second == first


def test_merge_restores_builtin_mcp_after_adapter_retirement() -> None:
    # pi-mcp-adapter 会往 settings.json 写 -builtin:mcp；适配器退役后若保留
    # 该标记，本机会既没有适配器也没有内置 MCP，因此 merge 时清掉。
    existing = {
        "packages": ["npm:pi-mcp-adapter"],
        "extensions": ["-builtin:mcp", "~/.pi/agent/extensions/exit.ts"],
    }
    out = merge(existing, _vendor())
    assert "npm:pi-mcp-adapter" not in out["packages"]
    assert out["extensions"] == ["~/.pi/agent/extensions/exit.ts"]

    only_marker = merge({"extensions": ["-builtin:mcp"]}, _vendor())
    assert "extensions" not in only_marker


def test_compact_output_extension_only_replaces_renderers() -> None:
    source = (VENDOR / "extensions" / "compact-output.ts").read_text(encoding="utf-8")
    # 只换渲染，不重注册工具：重注册会连带覆盖执行逻辑和工具定义里的 cwd
    assert "registerToolRenderer" in source
    assert "registerTool(" not in source
    assert "renderResult" in source
    for tool in ("bash", "grep", "find", "ls", "ffgrep", "fffind", "fff-multi-grep"):
        assert tool in source
    # 展现层不引入外部依赖
    assert "import type { ExtensionAPI }" in source
    assert '"@earendil-works/pi-tui"' in source
