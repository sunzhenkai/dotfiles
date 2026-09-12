"""错误码与输出契约测试（spec: cli-surface）。

覆盖六类错误码的退出码、stderr [dotf] 前缀、--verbose 链路、--json 错误结构。
"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import run_dotf

import pytest


def test_legacy_syntax_usage_code(tmp_home: Path) -> None:
    result = run_dotf("-i", "sdk")
    assert result.returncode == 1
    assert result.stderr.startswith("[dotf] usage:")


def test_doctor_bypass_usage_code(tmp_home: Path) -> None:
    result = run_dotf("agents", "-c", "--doctor")
    assert result.returncode == 1
    assert "[dotf] usage:" in result.stderr


def test_unknown_module_plan_code(tmp_home: Path) -> None:
    result = run_dotf("no-such-module-xyz", "-i")
    # 契约：planner 失败退出码逐字透传（rc=1），错误码仍为 plan
    assert result.returncode == 1
    assert "[dotf] plan:" in result.stderr


def test_tui_requires_tty_env_code(tmp_home: Path) -> None:
    result = run_dotf("tui")
    assert result.returncode == 2
    assert "[dotf] env:" in result.stderr or "需要 TTY" in result.stderr


def test_guard_message_preserved_verbatim(tmp_home: Path) -> None:
    result = run_dotf("-i", "sdk")
    assert "错误: 旧语法已移除（动作优先不再支持）" in result.stderr
    assert "dotf sdk -i" in result.stderr


def test_verbose_chain_on_plan_failure(tmp_home: Path) -> None:
    result = run_dotf("no-such-module-xyz", "-i", "--verbose")
    assert result.returncode == 1
    assert "调用链:" in result.stderr
    assert "planner.py" in result.stderr


def test_non_verbose_no_chain(tmp_home: Path) -> None:
    result = run_dotf("no-such-module-xyz", "-i")
    assert "调用链:" not in result.stderr


def test_json_error_structure(tmp_home: Path) -> None:
    result = run_dotf("no-such-module-xyz", "-i", "--json", "--dry-run")
    # planner 先于 JSON 错误输出自己的文本诊断到 stderr；stdout 须为单一 JSON
    doc = json.loads(result.stdout)
    assert doc["ok"] is False
    assert doc["error"]["code"] == "plan"
    assert "message" in doc["error"]


def test_skills_json_error_structure(tmp_home: Path) -> None:
    result = run_dotf("skills", "-i", "commit-push", "--dry-run")
    assert result.returncode == 1
    # skills_map 的 first-party 拒绝文案保持可见
    assert "first-party" in result.stderr


def test_unknown_option_exit_code(tmp_home: Path) -> None:
    result = run_dotf("-x")
    assert result.returncode == 1


def test_shim_legacy_escape_hatch(tmp_home: Path) -> None:
    result = run_dotf("__path", env={"DOTF_LEGACY_CLI": "1"})
    assert result.returncode == 0
    assert result.stdout.strip()
