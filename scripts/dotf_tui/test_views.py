"""Textual Pilot tests for the manager screens (sync wrappers around asyncio)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from dotf_tui.app import (  # noqa: E402
    ConfirmModal,
    DotfTuiApp,
    McpPane,
    ModulesPane,
    ProgressModal,
    SkillsPane,
    TAB_IDS,
    format_action_status,
    format_row_cells,
    selection_mark,
)
from dotf_tui.state import (  # noqa: E402
    McpRow,
    ModuleRow,
    SkillRow,
    load_instructions,
)


@pytest.fixture
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("XDG_STATE_HOME", str(h / ".local" / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(h / ".config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(h / ".cache"))
    (h / ".local/state").mkdir(parents=True, exist_ok=True)
    return h


def _run(coro):
    return asyncio.run(coro)


def _bar_text(app: DotfTuiApp) -> str:
    from textual.widgets import Static

    return str(app.query_one("#status_bar", Static).content)


def _module_row(**kwargs) -> ModuleRow:
    fields = dict(
        name="demo",
        capabilities=("install", "config", "doctor", "deconfig"),
        installed=False,
        configured=False,
        last_install_at=None,
        last_config_at=None,
        version=None,
        path=None,
        drift="unknown",
        installed_unknown=True,
        configured_unknown=True,
    )
    fields.update(kwargs)
    return ModuleRow(**fields)


def test_format_action_status_lists_declared_module_actions():
    text = format_action_status(_module_row())
    assert text.startswith("j/k 上下") or "j/k 上下" in text
    assert "C-d/C-u 半屏" in text
    assert "gg/G 首末" in text
    assert "已选 0" in text
    assert "i install 安装软件" in text
    assert "c config 写入配置" in text
    assert "d deconfig 撤回受管配置" in text
    assert "D doctor 诊断" in text
    assert "uninstall" not in text


def test_format_action_status_includes_uninstall_when_declared():
    text = format_action_status(
        _module_row(capabilities=("install", "uninstall")),
        selected_count=2,
    )
    assert "已选 2" in text
    assert "C-x 清空选中" in text
    assert "u uninstall 卸载软件" in text
    assert "config" not in text


def test_format_action_status_hides_clear_when_nothing_selected():
    text = format_action_status(_module_row(), selected_count=0)
    assert "已选 0" in text
    assert "C-x" not in text


def test_format_row_cells_marks_selected():
    plain = [str(cell) for cell in format_row_cells(["nvim", "IC"], selected=False)]
    marked = [str(cell) for cell in format_row_cells(["nvim", "IC"], selected=True)]
    assert plain[0].startswith("[ ] ")
    assert marked[0].startswith("[x] ")
    assert "nvim" in marked[0]
    assert selection_mark(True) == "[x]"
    assert selection_mark(False) == "[ ]"


def test_format_action_status_skill_and_mcp():
    skill = format_action_status(SkillRow("grill-with-docs", "desired", True))
    assert "j/k 上下" in skill
    assert "a apply 写入 Desired Set" in skill
    assert "x remove 移出 Desired Set" in skill
    mcp = format_action_status(McpRow("cursor", "web-reader", True))
    assert "a apply" in mcp
    assert "x remove" in mcp


def test_format_action_status_readonly():
    text = format_action_status(None, readonly=True)
    assert "j/k 上下" in text
    assert "C-d/C-u 半屏" in text
    assert "只读" in text
    assert "install" not in text


def test_half_page_row_steps_by_half_view():
    from dotf_tui.app import half_page_row

    assert half_page_row(0, 20, 10, down=True) == 5
    assert half_page_row(5, 20, 10, down=False) == 0
    assert half_page_row(18, 20, 10, down=True) == 19
    assert half_page_row(1, 20, 10, down=False) == 0
    assert half_page_row(0, 0, 10, down=True) == 0


def test_tabs_visible_on_start(home):
    async def main():
        from textual.widgets import TabbedContent

        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tabs = app.query_one("#tabs", TabbedContent)
            assert tabs.tab_count == 5
            assert tabs.active == "modules"
            assert isinstance(app.active_pane, ModulesPane)

    _run(main())


def test_tab_cycles_categories(home):
    async def main():
        from textual.widgets import TabbedContent

        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tabs = app.query_one("#tabs", TabbedContent)
            await pilot.press("tab")
            await pilot.pause()
            assert tabs.active == "skills"
            assert isinstance(app.active_pane, SkillsPane)
            await pilot.press("shift+tab")
            await pilot.pause()
            assert tabs.active == "modules"

    _run(main())


def test_digit_jumps_into_skills(home):
    async def main():
        from textual.widgets import TabbedContent

        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("2")
            await pilot.pause()
            assert app.query_one("#tabs", TabbedContent).active == "skills"
            assert isinstance(app.active_pane, SkillsPane)

    _run(main())


def test_h_l_switch_tabs(home):
    async def main():
        from textual.widgets import TabbedContent

        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tabs = app.query_one("#tabs", TabbedContent)
            await pilot.press("l")
            await pilot.pause()
            assert tabs.active == "skills"
            await pilot.press("h")
            await pilot.pause()
            assert tabs.active == "modules"

    _run(main())


def test_table_sits_against_tabs_when_filter_closed(home):
    async def main():
        from textual.widgets import DataTable, Input
        from textual.widgets.tabbed_content import ContentTabs

        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            pane = app.active_pane
            tabs = app.query_one(ContentTabs)
            table = pane.query_one("#table", DataTable)
            filt = pane.query_one("#filter", Input)
            assert filt.display is False
            assert table.region.y == tabs.region.y + tabs.region.height
            await pilot.press("slash")
            await pilot.pause()
            assert filt.display is True
            await pilot.press("escape")
            await pilot.pause()
            assert filt.display is False
            assert table.region.y == tabs.region.y + tabs.region.height

    _run(main())


def test_filter_narrows_modules(home):
    async def main():
        from textual.widgets import DataTable, Input

        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            pane = app.active_pane
            table = pane.query_one("#table", DataTable)
            full = table.row_count
            assert full > 1
            await pilot.press("slash")
            await pilot.pause()
            pane.query_one("#filter", Input).value = "grep"
            await pilot.pause()
            await pilot.pause()
            assert table.row_count == 1

    _run(main())


def test_status_bar_shows_row_actions(home):
    async def main():
        from textual.widgets import Input

        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            pane = app.active_pane
            await pilot.press("slash")
            await pilot.pause()
            pane.query_one("#filter", Input).value = "grepom"
            await pilot.pause()
            await pilot.pause()
            text = _bar_text(app)
            assert "u uninstall 卸载软件" in text
            assert "i install 安装软件" in text
            pane.query_one("#filter", Input).value = "nvim"
            await pilot.pause()
            await pilot.pause()
            text = _bar_text(app)
            assert "c config 写入配置" in text
            assert "uninstall" not in text

    _run(main())


def test_vim_jk_moves_cursor(home):
    async def main():
        from textual.widgets import DataTable

        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            table = app.active_pane.query_one("#table", DataTable)
            assert table.row_count > 1
            start = table.cursor_row
            await pilot.press("j")
            await pilot.pause()
            assert table.cursor_row == start + 1
            await pilot.press("k")
            await pilot.pause()
            assert table.cursor_row == start

    _run(main())


def test_half_page_ctrl_d_and_ctrl_u(home):
    async def main():
        from textual.widgets import DataTable

        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            table = app.active_pane.query_one("#table", DataTable)
            assert table.row_count > 2
            start = table.cursor_row
            await pilot.press("ctrl+d")
            await pilot.pause()
            assert table.cursor_row > start
            after_down = table.cursor_row
            await pilot.press("ctrl+u")
            await pilot.pause()
            assert table.cursor_row < after_down

    _run(main())


def test_status_bar_shows_movement_help(home):
    async def main():
        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            text = _bar_text(app)
            assert "j/k 上下" in text
            assert "C-d/C-u 半屏" in text
            assert "gg/G 首末" in text

    _run(main())


def test_vim_gg_and_G_jump(home):
    async def main():
        from textual.widgets import DataTable

        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            table = app.active_pane.query_one("#table", DataTable)
            assert table.row_count > 1
            await pilot.press("G")
            await pilot.pause()
            assert table.cursor_row == table.row_count - 1
            await pilot.press("g")
            await pilot.press("g")
            await pilot.pause()
            assert table.cursor_row == 0

    _run(main())


def test_skills_and_mcp_render(home):
    async def main():
        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("2")
            await pilot.pause()
            assert isinstance(app.active_pane, SkillsPane)
            await pilot.press("3")
            await pilot.pause()
            assert isinstance(app.active_pane, McpPane)

    _run(main())


def test_status_and_conflicts_render(home):
    async def main():
        from textual.widgets import TabbedContent

        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("4")
            await pilot.pause()
            assert app.query_one("#tabs", TabbedContent).active == "status"
            assert "只读" in _bar_text(app)
            await pilot.press("5")
            await pilot.pause()
            assert app.query_one("#tabs", TabbedContent).active == "conflicts"

    _run(main())


def test_load_instructions_reports_missing_targets(home):
    rows = load_instructions(ROOT)
    assert {r.target_id: r.drift for r in rows} == {
        "agents": "missing",
        "codex": "missing",
        "cursor": "missing",
    }


def test_load_instructions_planner_failure_is_unknown(home, monkeypatch):
    import instructions

    def boom(root, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(instructions, "compile_instructions_plan", boom)
    rows = load_instructions(ROOT)
    assert [(r.target_id, r.drift) for r in rows] == [("planner", "unknown")]


def test_status_and_conflicts_show_instructions_drift(home):
    async def main():
        from textual.widgets import DataTable, TabbedContent

        app = DotfTuiApp(ROOT)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("4")
            await pilot.pause()
            assert app.query_one("#tabs", TabbedContent).active == "status"
            status_rows = [
                app.active_pane.query_one("#table", DataTable).get_row_at(i)[0]
                for i in range(app.active_pane.query_one("#table", DataTable).row_count)
            ]
            assert any(
                line.startswith("instructions:agents") and "drift=missing" in line
                for line in status_rows
            )
            await pilot.press("5")
            await pilot.pause()
            assert app.query_one("#tabs", TabbedContent).active == "conflicts"
            conflict_rows = [
                app.active_pane.query_one("#table", DataTable).get_row_at(i)[0]
                for i in range(app.active_pane.query_one("#table", DataTable).row_count)
            ]
            assert "instructions drift:" in conflict_rows
            assert any(line.startswith("  - agents (missing)") for line in conflict_rows)

    _run(main())


def test_confirm_modal_responds_to_y(home):
    async def main():
        from textual.widgets import Input

        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.push_screen(ConfirmModal("test?"))
            await pilot.pause()
            modal = app.screen
            modal.query_one("#confirm_input", Input).value = "y"
            await pilot.press("enter")
            await pilot.pause()

    _run(main())


def test_confirm_modal_default_cancels(home):
    async def main():
        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.push_screen(ConfirmModal("test?"))
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

    _run(main())


def test_filter_clear_with_escape(home):
    async def main():
        from textual.widgets import DataTable, Input

        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            pane = app.active_pane
            table = pane.query_one("#table", DataTable)
            full = table.row_count
            await pilot.press("slash")
            await pilot.pause()
            pane.query_one("#filter", Input).value = "no-such-module"
            await pilot.pause()
            await pilot.pause()
            assert table.row_count == 0
            await pilot.press("escape")
            await pilot.pause()
            assert table.row_count == full
            assert pane.query_one("#filter", Input).display is False

    _run(main())


def test_tab_ids_are_the_five_categories():
    assert TAB_IDS == ("modules", "skills", "mcp", "status", "conflicts")


def _first_cell(table, row: int = 0) -> str:
    return str(table.get_cell_at((row, 0)))


def test_space_marks_selected_row(home):
    async def main():
        from textual.widgets import DataTable

        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            pane = app.active_pane
            table = pane.query_one("#table", DataTable)
            before = _first_cell(table)
            assert before.startswith("[ ] ")
            await pilot.press("space")
            await pilot.pause()
            after = _first_cell(table)
            assert after.startswith("[x] ")
            assert "已选 1" in _bar_text(app)
            assert table.cursor_row == 0
            await pilot.press("space")
            await pilot.pause()
            assert _first_cell(table).startswith("[ ] ")
            assert "已选 0" in _bar_text(app)

    _run(main())


def test_ctrl_x_clear_selection_cancels_by_default(home):
    async def main():
        from textual.widgets import DataTable

        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            pane = app.active_pane
            table = pane.query_one("#table", DataTable)
            await pilot.press("space")
            await pilot.pause()
            assert pane.selected
            await pilot.press("ctrl+x")
            await pilot.pause()
            assert isinstance(app.screen, ConfirmModal)
            await pilot.press("enter")
            await pilot.pause()
            assert pane.selected
            assert _first_cell(table).startswith("[x] ")

    _run(main())


def test_ctrl_x_clear_selection_confirms_with_y(home):
    async def main():
        from textual.widgets import DataTable, Input

        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            pane = app.active_pane
            table = pane.query_one("#table", DataTable)
            await pilot.press("space")
            await pilot.press("j")
            await pilot.press("space")
            await pilot.pause()
            assert len(pane.selected) == 2
            await pilot.press("ctrl+x")
            await pilot.pause()
            modal = app.screen
            assert isinstance(modal, ConfirmModal)
            modal.query_one("#confirm_input", Input).value = "y"
            await pilot.press("enter")
            await pilot.pause()
            assert not pane.selected
            assert _first_cell(table).startswith("[ ] ")
            assert "已选 0" in _bar_text(app)

    _run(main())


def test_ctrl_x_noop_when_nothing_selected(home):
    async def main():
        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("ctrl+x")
            await pilot.pause()
            assert not isinstance(app.screen, ConfirmModal)
            assert "已选 0" in _bar_text(app)

    _run(main())


async def _wait_until(predicate, pilot, ticks: int = 40):
    for _ in range(ticks):
        if predicate():
            return
        await pilot.pause()
    raise AssertionError("condition not met")


def test_progress_modal_blocks_keys_until_done(home, monkeypatch):
    gate = asyncio.Event()

    async def slow(action, *, on_line=None):
        if on_line is not None:
            on_line("working")
        await gate.wait()
        return 0, "ok"

    monkeypatch.setattr("dotf_tui.app.exec_selected_action", slow)

    async def main():
        from textual.widgets import Label, TabbedContent

        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            pane = app.active_pane
            from textual.widgets import Input

            await pilot.press("slash")
            await pilot.pause()
            pane.query_one("#filter", Input).value = "grepom"
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            pane.action_act("install")
            await _wait_until(
                lambda: isinstance(app.screen, ProgressModal)
                and bool(app.screen.query("#progress_hint")),
                pilot,
            )
            modal = app.screen
            assert isinstance(modal, ProgressModal)
            assert modal._done is False
            hint = str(modal.query_one("#progress_hint", Label).content)
            assert "完成后才能继续" in hint
            await pilot.press("q")
            await pilot.press("escape")
            await pilot.press("tab")
            await pilot.pause()
            assert isinstance(app.screen, ProgressModal)
            assert app.query_one("#tabs", TabbedContent).active == "modules"
            gate.set()
            await _wait_until(lambda: isinstance(app.screen, ProgressModal) and app.screen._done, pilot)
            await pilot.press("enter")
            await _wait_until(lambda: not isinstance(app.screen, ProgressModal), pilot)

    _run(main())


def test_progress_modal_enter_ignored_while_running(home, monkeypatch):
    gate = asyncio.Event()

    async def slow(action, *, on_line=None):
        await gate.wait()
        return 0, "ok"

    monkeypatch.setattr("dotf_tui.app.exec_selected_action", slow)

    async def main():
        app = DotfTuiApp(Path.cwd())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            pane = app.active_pane
            from textual.widgets import Input

            await pilot.press("slash")
            await pilot.pause()
            pane.query_one("#filter", Input).value = "grepom"
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            pane.action_act("install")
            await _wait_until(
                lambda: isinstance(app.screen, ProgressModal)
                and bool(app.screen.query("#progress_hint")),
                pilot,
            )
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, ProgressModal)
            assert app.screen._done is False
            gate.set()
            await _wait_until(lambda: app.screen._done, pilot)
            await pilot.press("enter")
            await _wait_until(lambda: not isinstance(app.screen, ProgressModal), pilot)

    _run(main())
