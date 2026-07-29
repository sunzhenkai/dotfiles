"""ensure_pyyaml：缺失时自动 pip 安装。"""

from __future__ import annotations

import subprocess
import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from ensure_pyyaml import _install_commands, ensure_yaml


def test_ensure_yaml_returns_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = MagicMock(spec=ModuleType)
    monkeypatch.setattr(
        "ensure_pyyaml._try_import",
        lambda: fake,
    )
    assert ensure_yaml() is fake


def test_ensure_yaml_installs_then_imports(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    state = {"n": 0}

    def fake_try() -> ModuleType | None:
        state["n"] += 1
        if state["n"] == 1:
            return None
        return MagicMock(spec=ModuleType)

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr("ensure_pyyaml._try_import", fake_try)
    monkeypatch.setattr("ensure_pyyaml.subprocess.run", fake_run)
    monkeypatch.setattr("ensure_pyyaml.importlib.invalidate_caches", lambda: None)

    mod = ensure_yaml(quiet=True)
    assert mod is not None
    assert calls, "应至少尝试一次 pip 安装"
    assert "PyYAML" in calls[0]


def test_ensure_yaml_exits_when_all_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ensure_pyyaml._try_import", lambda: None)

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr("ensure_pyyaml.subprocess.run", fake_run)

    with pytest.raises(SystemExit) as exc:
        ensure_yaml(quiet=True)
    assert exc.value.code == 1


def test_install_commands_prefer_pip_user() -> None:
    cmds = _install_commands()
    assert cmds[0][:4] == [sys.executable, "-m", "pip", "install"]
    assert "--user" in cmds[0]
    assert cmds[0][-1] == "PyYAML"
