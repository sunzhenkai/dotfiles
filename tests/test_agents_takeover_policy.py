"""Takeover policy resolution: backup by default, explicit flags win, no prompt."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "agents"))

from managed_runtime import AgentRuntimeError, on_takeover_from_env, parse_on_takeover  # noqa: E402


def test_default_takeover_policy_is_backup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOTF_TAKEOVER", raising=False)
    assert parse_on_takeover(None) == "backup"
    assert on_takeover_from_env() == "backup"


def test_explicit_takeover_policy_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOTF_TAKEOVER", "skip")
    assert on_takeover_from_env() == "skip"
    monkeypatch.setenv("DOTF_TAKEOVER", "backup")
    assert on_takeover_from_env() == "backup"


def test_unknown_takeover_policy_fails_closed() -> None:
    with pytest.raises(AgentRuntimeError, match="unknown on-takeover policy"):
        parse_on_takeover("overwrite")
