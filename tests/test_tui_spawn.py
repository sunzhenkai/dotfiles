"""Spawn argv construction + dispatch tests."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotf_tui import app as app_mod  # noqa: E402


def test_dotf_cmd_runs_bash_entry_not_python():
    """TUI must exec bin/dotf (bash). python3 bin/dotf raises SyntaxError at case."""
    argv = app_mod._dotf_cmd(ROOT, "grepom", "--install", "--yes")
    assert argv[0] == str(ROOT / "bin" / "dotf")
    assert argv[0] != sys.executable
    result = subprocess.run([argv[0], "-h"], capture_output=True, text=True)
    combined = result.stdout + result.stderr
    assert "SyntaxError" not in combined
    assert result.returncode == 0
    assert "用法" in result.stdout


def test_python_dotf_is_still_not_valid_python():
    """bin/dotf 必须保持非 Python 可执行（TUI 曾误用 python spawn 的回归护栏）。

    下沉后 bin/dotf 仍是 bash shim：用 python 解释它必须失败，
    防止 TUI 侧再把 argv[0] 换成 Python 解释器而静默变行为。
    """
    result = subprocess.run(
        [sys.executable, str(ROOT / "bin" / "dotf"), "-h"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "SyntaxError" in result.stderr


def test_argv_change_label_extracts_action_and_module():
    argv = app_mod._dotf_cmd(ROOT, "grepom", "--install", "--yes")
    label = app_mod._argv_change_label(argv)
    assert label == "install grepom"


def test_argv_change_label_unknown_action():
    argv = app_mod._dotf_cmd(ROOT, "foo")
    label = app_mod._argv_change_label(argv)
    assert "foo" in label


def test_modules_argv_includes_yes_in_pilot(tmp_path, monkeypatch):
    """ModulesScreen._argv must include --yes (TUI is the confirm point)."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "home" / ".local" / "state"))

    async def main():
        app = app_mod.DotfTuiApp(ROOT)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            pane = app.active_pane
            assert isinstance(pane, app_mod.ModulesPane)
            argv = pane._argv("grepom", "install")
            assert argv[0] == str(ROOT / "bin" / "dotf")
            assert argv[0] != sys.executable
            assert "grepom" in argv
            assert "--install" in argv
            assert "--yes" in argv

    asyncio.run(main())


def test_modules_argv_doctor_in_pilot(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "home" / ".local" / "state"))

    async def main():
        app = app_mod.DotfTuiApp(ROOT)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            pane = app.active_pane
            argv = pane._argv("nvim", "doctor")
            assert "--doctor" in argv
            assert "--yes" in argv

    asyncio.run(main())


def test_modules_action_act_dispatches_to_exec(tmp_path, monkeypatch):
    """Pressing install must run through exec_selected_action with --yes."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "home" / ".local" / "state"))

    captured: list[tuple[str, ...]] = []

    async def _capture(action, *, on_line=None):
        captured.append(tuple(action.argv))
        return 0, "ok"

    monkeypatch.setattr(app_mod, "exec_selected_action", _capture)

    async def main():
        app = app_mod.DotfTuiApp(ROOT)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            pane = app.active_pane
            assert isinstance(pane, app_mod.ModulesPane)
            from textual.widgets import Input

            await pilot.press("slash")
            await pilot.pause()
            pane.query_one("#filter", Input).value = "grepom"
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            pane.action_act("install")
            for _ in range(40):
                if captured and isinstance(app.screen, app_mod.ProgressModal) and app.screen._done:
                    break
                await pilot.pause()

    asyncio.run(main())

    assert captured, "exec_selected_action was not called"
    argv = captured[0]
    assert "--install" in argv
    assert "--yes" in argv


def test_non_tty_main_returns_2(monkeypatch, capsys):
    """__main__.main() must fail-fast (exit 2) outside a TTY."""
    from dotf_tui import __main__ as cli
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    rc = cli.main([])
    assert rc == 2
    captured = capsys.readouterr()
    assert "TTY" in captured.err or "CLI" in captured.err


def test_missing_textual_returns_1(monkeypatch, capsys):
    """__main__.main() must fail-fast (exit 1) when build_app raises."""
    from dotf_tui import __main__ as cli
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    import dotf_tui.app as real_app

    def _boom(*a, **k):
        raise RuntimeError("no textual here")

    monkeypatch.setattr(real_app, "build_app", _boom)
    rc = cli.main([])
    assert rc == 1
    captured = capsys.readouterr()
    assert "no textual" in captured.err
