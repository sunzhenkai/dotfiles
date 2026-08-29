"""ZCode MCP 渲染：本机展开 ZHIPU_API_KEY，仓库模板保留占位符。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "agents"))

from common import (  # noqa: E402
    Catalog,
    collect_placeholders,
    entries_equivalent,
    expand_env_placeholders,
    render_server_for_tool,
)
from env_sync import sync_zcode  # noqa: E402

FAKE_KEY = "test-zhipu-key-not-a-secret"


@pytest.fixture
def no_senv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("common._senv_get", lambda name: "")


def _http_srv() -> dict:
    return {
        "transport": "streamable-http",
        "url": "https://open.bigmodel.cn/api/mcp/web_search_prime/mcp",
        "auth": {"type": "bearer-env", "env": "ZHIPU_API_KEY"},
    }


def _vision_srv() -> dict:
    return {
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@z_ai/mcp-server@latest"],
        "env": {
            "Z_AI_API_KEY": "${ZHIPU_API_KEY}",
            "Z_AI_MODE": "ZHIPU",
        },
    }


def test_zcode_http_keeps_placeholder_without_expand() -> None:
    entry = render_server_for_tool("web-search-prime", _http_srv(), "zcode")
    assert entry["headers"]["Authorization"] == "Bearer ${ZHIPU_API_KEY}"


def test_zcode_http_expands_zhipu_key(monkeypatch: pytest.MonkeyPatch, no_senv: None) -> None:
    monkeypatch.setenv("ZHIPU_API_KEY", FAKE_KEY)
    entry = render_server_for_tool(
        "web-search-prime", _http_srv(), "zcode", expand_secrets=True
    )
    assert entry["headers"]["Authorization"] == f"Bearer {FAKE_KEY}"
    assert "${" not in json.dumps(entry)


def test_zcode_stdio_expands_mapped_env(monkeypatch: pytest.MonkeyPatch, no_senv: None) -> None:
    monkeypatch.setenv("ZHIPU_API_KEY", FAKE_KEY)
    entry = render_server_for_tool("zai-vision", _vision_srv(), "zcode", expand_secrets=True)
    assert entry["command"] == "npx"
    assert entry["env"]["Z_AI_API_KEY"] == FAKE_KEY
    assert entry["env"]["Z_AI_MODE"] == "ZHIPU"


def test_zcode_expand_missing_key_fails(monkeypatch: pytest.MonkeyPatch, no_senv: None) -> None:
    monkeypatch.delenv("ZHIPU_API_KEY", raising=False)
    with pytest.raises(SystemExit, match=r"无法展开环境变量占位符"):
        render_server_for_tool(
            "web-search-prime", _http_srv(), "zcode", expand_secrets=True
        )


def test_cursor_does_not_expand_even_if_key_present(
    monkeypatch: pytest.MonkeyPatch, no_senv: None
) -> None:
    monkeypatch.setenv("ZHIPU_API_KEY", FAKE_KEY)
    entry = render_server_for_tool("web-search-prime", _http_srv(), "cursor")
    assert entry["headers"]["Authorization"] == "Bearer ${ZHIPU_API_KEY}"


def test_entries_equivalent_treats_expanded_secret_as_match() -> None:
    expected = {"headers": {"Authorization": "Bearer ${ZHIPU_API_KEY}"}}
    actual = {"headers": {"Authorization": f"Bearer {FAKE_KEY}"}}
    assert entries_equivalent(expected, actual)
    assert entries_equivalent(expected, expected)
    assert not entries_equivalent(expected, {"headers": {"Authorization": "Bearer"}})


def test_collect_placeholders_finds_unexpanded_header() -> None:
    toks = collect_placeholders({"headers": {"Authorization": "Bearer ${ZHIPU_API_KEY}"}})
    assert toks == ["${ZHIPU_API_KEY}"]
    assert collect_placeholders({"headers": {"Authorization": f"Bearer {FAKE_KEY}"}}) == []


def test_expand_env_placeholders_uses_senv_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ZHIPU_API_KEY", raising=False)
    monkeypatch.setattr("common._senv_get", lambda name: FAKE_KEY if name == "ZHIPU_API_KEY" else "")
    out = expand_env_placeholders("Bearer ${ZHIPU_API_KEY}")
    assert out == f"Bearer {FAKE_KEY}"


def test_sync_zcode_writes_expanded_home_config(
    tmp_home: Path, monkeypatch: pytest.MonkeyPatch, no_senv: None
) -> None:
    monkeypatch.setenv("ZHIPU_API_KEY", FAKE_KEY)
    cat = Catalog(ROOT)
    sync_zcode(cat, "research", dry_run=False, also_repo=False)
    target = tmp_home / ".zcode" / "cli" / "config.json"
    data = json.loads(target.read_text(encoding="utf-8"))
    servers = data["mcp"]["servers"]
    assert servers["web-search-prime"]["headers"]["Authorization"] == f"Bearer {FAKE_KEY}"
    assert servers["zai-vision"]["env"]["Z_AI_API_KEY"] == FAKE_KEY
    dumped = json.dumps(servers)
    assert "${ZHIPU_API_KEY}" not in dumped
    assert FAKE_KEY in dumped


def test_vendor_zcode_template_has_placeholder_not_secret() -> None:
    text = (ROOT / "agents" / "vendors" / "zcode" / "mcp.json").read_text(encoding="utf-8")
    data = json.loads(text)
    servers = data["mcp"]["servers"]
    assert servers["web-search-prime"]["headers"]["Authorization"] == "Bearer ${ZHIPU_API_KEY}"
    assert servers["zai-vision"]["env"]["Z_AI_API_KEY"] == "${ZHIPU_API_KEY}"
    assert FAKE_KEY not in text
    assert "sh" != servers["zai-vision"]["command"]


def test_kimi_http_uses_bearer_token_env_var() -> None:
    entry = render_server_for_tool("web-search-prime", _http_srv(), "kimi-code")
    assert entry == {
        "url": "https://open.bigmodel.cn/api/mcp/web_search_prime/mcp",
        "bearerTokenEnvVar": "ZHIPU_API_KEY",
    }


def test_kimi_stdio_maps_placeholder_via_shell() -> None:
    entry = render_server_for_tool("zai-vision", _vision_srv(), "kimi-code")
    assert entry["command"] == "sh"
    assert entry["args"][0] == "-c"
    script = entry["args"][1]
    assert 'Z_AI_API_KEY="$ZHIPU_API_KEY"' in script
    assert "Z_AI_MODE=ZHIPU" in script
    assert "npx" in script
    assert "@z_ai/mcp-server@latest" in script
    assert "${ZHIPU_API_KEY}" not in script
    assert "env" not in entry


def test_kimi_stdio_without_placeholder_keeps_command() -> None:
    srv = {
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@playwright/mcp@latest"],
        "env": {"FOO": "bar"},
    }
    entry = render_server_for_tool("playwright", srv, "kimi-code")
    assert entry["command"] == "npx"
    assert entry["env"]["FOO"] == "bar"


def test_vendor_kimi_vision_maps_zhipu_key_via_shell() -> None:
    text = (ROOT / "agents" / "vendors" / "kimi-code" / "mcp.json").read_text(
        encoding="utf-8"
    )
    data = json.loads(text)
    vision = data["mcpServers"]["zai-vision"]
    assert vision["command"] == "sh"
    script = vision["args"][1]
    assert 'Z_AI_API_KEY="$ZHIPU_API_KEY"' in script
    assert "${ZHIPU_API_KEY}" not in script
    assert FAKE_KEY not in text
