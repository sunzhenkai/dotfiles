"""Textual manager-mode skin. Keypress-driven, in-place action, persistent state."""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.text import Text

from . import state
from .state import ModuleRow, SkillRow, McpRow

try:
    from textual import events
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Vertical
    from textual.screen import ModalScreen
    from textual.widgets import DataTable, Footer, Header, Input, Label, Log, Static, TabbedContent, TabPane
except ImportError as exc:  # pragma: no cover - handled by __main__
    raise RuntimeError(
        "缺少 Textual。请用用户级安装后重试："
        "pip install --user textual   或   mise exec -- pip install textual\n"
        "也可以改用 CLI：dotf nvim --deconfig / dotf agents skill apply <id>"
    ) from exc

LOG = logging.getLogger(__name__)

TAB_IDS = ("modules", "skills", "mcp", "status", "conflicts")
TAB_TITLES = {
    "modules": "1 Modules",
    "skills": "2 Skills",
    "mcp": "3 MCP",
    "status": "4 Status",
    "conflicts": "5 Conflicts",
}

_MODULE_ACTIONS: tuple[tuple[str, str, str, str], ...] = (
    ("install", "i", "install", "安装软件"),
    ("config", "c", "config", "写入配置"),
    ("deconfig", "d", "deconfig", "撤回受管配置"),
    ("uninstall", "u", "uninstall", "卸载软件"),
    ("doctor", "D", "doctor", "诊断"),
)
_AGENT_ACTIONS: tuple[tuple[str, str, str, str], ...] = (
    ("apply", "a", "apply", "写入 Desired Set"),
    ("remove", "x", "remove", "移出 Desired Set"),
)


MOVE_HELP = "j/k 上下  ·  C-d/C-u 半屏  ·  gg/G 首末"
SELECTED_STYLE = "bold black on cyan"
SELECTED_MARK = "[x]"
UNSELECTED_MARK = "[ ]"


def selection_mark(selected: bool) -> str:
    return SELECTED_MARK if selected else UNSELECTED_MARK


def format_row_cells(cells: list[str], *, selected: bool) -> list[Text]:
    """Prefix the first cell with a checkbox and highlight selected rows."""
    marked = list(cells)
    if marked:
        marked[0] = f"{selection_mark(selected)} {marked[0]}"
    if selected:
        return [Text(cell, style=SELECTED_STYLE) for cell in marked]
    return [Text(cell) for cell in marked]


def half_page_row(cursor: int, row_count: int, view_height: int, *, down: bool) -> int:
    """Move by half the visible height, clamped to the table."""
    if row_count <= 0:
        return 0
    step = max(1, view_height // 2)
    if down:
        return min(row_count - 1, cursor + step)
    return max(0, cursor - step)


def format_action_status(
    item: ModuleRow | SkillRow | McpRow | None,
    *,
    selected_count: int = 0,
    readonly: bool = False,
) -> str:
    """Status-bar text: movement keys, selected count, and the current row's actions."""
    prefix = f"已选 {selected_count}"
    if selected_count:
        prefix = f"{prefix}  ·  C-x 清空选中"
    if readonly:
        return f"{MOVE_HELP}\n{prefix}  │  只读，无动作快捷键"
    if item is None:
        return f"{MOVE_HELP}\n{prefix}"
    parts: list[str] = []
    if isinstance(item, ModuleRow):
        for cap, key, name, desc in _MODULE_ACTIONS:
            if cap in item.capabilities:
                parts.append(f"{key} {name} {desc}")
    elif isinstance(item, (SkillRow, McpRow)):
        for _cap, key, name, desc in _AGENT_ACTIONS:
            parts.append(f"{key} {name} {desc}")
    extra = "  ·  ".join(parts)
    if extra:
        return f"{MOVE_HELP}\n{prefix}  │  {extra}"
    return f"{MOVE_HELP}\n{prefix}"


def _missing_textual_message() -> str:
    return (
        "缺少 Textual，无法打开 TUI。请用用户级安装后重试："
        "pip install --user textual   或   mise exec -- pip install textual\n"
        "也可以改用 CLI：dotf nvim --deconfig / dotf agents skill apply <id>"
    )


@dataclass(frozen=True, slots=True)
class SelectedAction:
    label: str
    argv: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProgressResult:
    ok: bool
    exit_code: int
    output: str
    completed: tuple[SelectedAction, ...]


async def exec_selected_action(
    action: SelectedAction,
    *,
    on_line: Any | None = None,
) -> tuple[int, str]:
    """Run one SelectedAction and optionally stream each output line."""
    argv = list(action.argv)
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except Exception as exc:
        msg = f"启动失败: {exc}"
        if on_line is not None:
            on_line(msg)
        return 1, msg
    lines: list[str] = []
    assert proc.stdout is not None
    while True:
        raw = await proc.stdout.readline()
        if not raw:
            break
        text = raw.decode("utf-8", errors="replace").rstrip("\n")
        lines.append(text)
        if on_line is not None:
            on_line(text)
    await proc.wait()
    return proc.returncode or 0, "\n".join(lines)


# -------------------------- Confirm / progress modals ---------------------


class ConfirmModal(ModalScreen[bool]):
    BINDINGS = [
        Binding("escape", "dismiss(False)", "取消", show=False),
    ]

    DEFAULT_CSS = """
    ConfirmModal {
        align: center middle;
    }
    ConfirmModal > Vertical {
        width: 60;
        height: auto;
        padding: 1 2;
        border: round $primary;
        background: $panel;
    }
    """

    def __init__(self, prompt: str) -> None:
        super().__init__()
        self._prompt = prompt

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self._prompt)
            yield Input(placeholder="输入 y 确认，Enter / Esc 取消", id="confirm_input")

    def on_mount(self) -> None:
        self.query_one("#confirm_input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = (event.value or "").strip().lower()
        self.dismiss(value == "y")


class ProgressModal(ModalScreen[ProgressResult]):
    """Block the TUI until spawned actions finish. Enter closes only after done."""

    BINDINGS = [
        Binding("enter", "close_if_done", show=False, priority=True),
        Binding("escape", "close_if_done", show=False, priority=True),
        Binding("q", "block_until_done", show=False, priority=True),
        Binding("tab", "block_until_done", show=False, priority=True),
        Binding("shift+tab", "block_until_done", show=False, priority=True),
    ]

    DEFAULT_CSS = """
    ProgressModal {
        align: center middle;
    }
    ProgressModal > Vertical {
        width: 90;
        height: 22;
        max-height: 90%;
        padding: 1 2;
        border: round $primary;
        background: $panel;
    }
    #progress_log {
        height: 1fr;
        margin: 1 0;
    }
    """

    def __init__(self, actions: list[SelectedAction]) -> None:
        super().__init__()
        self._actions = actions
        self._done = False
        self._result = ProgressResult(ok=True, exit_code=0, output="", completed=())

    def compose(self) -> ComposeResult:
        count = len(self._actions)
        heading = self._actions[0].label if count == 1 else f"{count} 项动作"
        with Vertical():
            yield Label(f"执行 {heading}", id="progress_title")
            yield Label("运行中…", id="progress_status")
            yield Log(id="progress_log", max_lines=400, auto_scroll=True)
            yield Label("运行中，完成后才能继续", id="progress_hint")

    def on_mount(self) -> None:
        self.call_after_refresh(lambda: self.run_worker(self._run, exclusive=True))

    async def _run(self) -> None:
        try:
            log = self.query_one("#progress_log", Log)
            status = self.query_one("#progress_status", Label)
            hint = self.query_one("#progress_hint", Label)
        except Exception as exc:
            self._result = ProgressResult(ok=False, exit_code=1, output=str(exc), completed=())
            self._done = True
            return
        completed: list[SelectedAction] = []
        chunks: list[str] = []
        exit_code = 0
        total = len(self._actions)

        def _append(line: str) -> None:
            log.write_line(line)
            chunks.append(line)

        try:
            for index, action in enumerate(self._actions, 1):
                status.update(f"运行中 {index}/{total}：{action.label}")
                _append(f"$ {_dotf_display(list(action.argv))}")
                code, _output = await exec_selected_action(action, on_line=_append)
                if code == 0:
                    completed.append(action)
                else:
                    exit_code = code
                    _append(f"失败 (exit={code})")
            ok = len(completed) == total
            self._result = ProgressResult(
                ok=ok,
                exit_code=exit_code,
                output="\n".join(chunks),
                completed=tuple(completed),
            )
            status.update("完成" if ok else "失败")
            hint.update("按 Enter 继续")
        except Exception as exc:
            _append(f"失败: {exc}")
            self._result = ProgressResult(
                ok=False,
                exit_code=1,
                output="\n".join(chunks) or str(exc),
                completed=tuple(completed),
            )
            status.update("失败")
            hint.update("按 Enter 继续")
        self._done = True

    def action_block_until_done(self) -> None:
        return

    def action_close_if_done(self) -> None:
        if self._done:
            self.dismiss(self._result)

    def on_key(self, event: events.Key) -> None:
        if not self._done:
            event.stop()
            event.prevent_default()


# -------------------------- Table with vim keys ---------------------------


class ManagerTable(DataTable):
    BINDINGS = [
        *DataTable.BINDINGS,
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
        Binding("h", "prev_tab", show=False),
        Binding("l", "next_tab", show=False),
        Binding("g", "vim_g", show=False),
        Binding("G", "go_bottom", show=False),
        Binding("ctrl+d", "half_page_down", show=False),
        Binding("ctrl+u", "half_page_up", show=False),
        Binding("space", "toggle_select", show=False),
        Binding("ctrl+x", "clear_selection", show=False),
    ]

    def action_select_cursor(self) -> None:
        self.app.action_run_batch()

    def action_scroll_home(self) -> None:
        self.action_go_top()

    def action_scroll_end(self) -> None:
        self.action_go_bottom()

    def action_prev_tab(self) -> None:
        self.app.action_prev_tab()

    def action_next_tab(self) -> None:
        self.app.action_next_tab()

    def action_vim_g(self) -> None:
        if self.app._pending_g:
            self.app._pending_g = False
            self.action_go_top()
            return
        self.app._pending_g = True

    def action_go_top(self) -> None:
        if self.row_count:
            self.move_cursor(row=0)

    def action_go_bottom(self) -> None:
        if self.row_count:
            self.move_cursor(row=self.row_count - 1)

    def action_half_page_down(self) -> None:
        if not self.row_count:
            return
        self.move_cursor(
            row=half_page_row(self.cursor_row, self.row_count, self.size.height, down=True)
        )

    def action_half_page_up(self) -> None:
        if not self.row_count:
            return
        self.move_cursor(
            row=half_page_row(self.cursor_row, self.row_count, self.size.height, down=False)
        )

    def action_toggle_select(self) -> None:
        self.app.action_toggle_select()

    def action_clear_selection(self) -> None:
        self.app.action_clear_selection()


# -------------------------- Pane base -------------------------------------


class _SubPane(Vertical):
    """Shared behaviours: filter Input + DataTable + selection state."""

    READONLY = False

    DEFAULT_CSS = """
    _SubPane {
        height: 1fr;
        layout: vertical;
    }
    _SubPane Input {
        height: 1;
        margin: 0;
        padding: 0;
        border: none;
    }
    _SubPane DataTable {
        height: 1fr;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.selected: set[Any] = set()
        self._key_to_row: dict[Any, Any] = {}
        self._last_headers: list[str] | None = None
        self._last_rows: list[tuple[Any, list[str]]] = []

    def compose(self) -> ComposeResult:
        yield Input(
            placeholder="按 / 过滤；Esc 清空",
            id="filter",
            compact=True,
        )
        yield ManagerTable(zebra_stripes=True, cursor_type="row", id="table")

    def on_mount(self) -> None:
        self.query_one("#filter", Input).display = False
        self._populate()

    def _populate(self) -> None:
        raise NotImplementedError

    def current_item(self) -> Any:
        key = self._current_key()
        if key is None:
            return None
        return self._key_to_row.get(key)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter":
            self._populate()

    def show_filter(self) -> None:
        filt = self.query_one("#filter", Input)
        filt.display = True
        filt.focus()

    def hide_filter(self) -> None:
        filt = self.query_one("#filter", Input)
        if filt.value:
            filt.value = ""
            self._populate()
        filt.display = False
        self.query_one("#table", DataTable).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter":
            self.query_one("#table", DataTable).focus()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self.app.refresh_action_status()

    def _current_key(self) -> Any:
        table = self.query_one("#table", DataTable)
        if table.row_count == 0:
            return None
        cell_key = table.coordinate_to_cell_key((table.cursor_row, 0))
        return cell_key.row_key.value if cell_key.row_key is not None else None

    def _populate_filtered(
        self,
        headers: list[str],
        rows: list[tuple[Any, list[str]]],
        *,
        keep_cursor: bool = False,
    ) -> None:
        table = self.query_one("#table", DataTable)
        cursor = table.cursor_row if keep_cursor else 0
        self._last_headers = headers
        self._last_rows = rows
        table.clear(columns=True)
        table.add_columns(*headers)
        for key, cells in rows:
            table.add_row(*format_row_cells(cells, selected=key in self.selected), key=key)
        if table.row_count:
            table.move_cursor(row=min(max(cursor, 0), table.row_count - 1))
        self.app.refresh_action_status()

    def redraw_selection(self, *, keep_cursor: bool = True) -> None:
        if self._last_headers is None:
            return
        self._populate_filtered(self._last_headers, self._last_rows, keep_cursor=keep_cursor)

    def _collect_selected_actions(self) -> list[SelectedAction]:
        return []

    def _run_with_progress(self, actions: list[SelectedAction]) -> None:
        if not actions:
            return

        def _on_done(result: ProgressResult | None) -> None:
            if result is None:
                return
            self._append_log(result.output)
            for action in result.completed:
                self.app.add_change(_argv_change_label(list(action.argv)))
            if result.completed:
                self._populate()
            if not result.ok:
                self.app.notify(f"动作失败 (exit={result.exit_code})", severity="error")

        self.app.push_screen(ProgressModal(actions), _on_done)

    def _append_log(self, text: str) -> None:
        log = self.app.query_one("#log", Static)
        log.update(text.splitlines()[-1] if text else "")

    def _confirm_then_run(self, action: SelectedAction, prompt: str) -> None:
        def _on_confirm(ok: bool | None) -> None:
            if not ok:
                return
            self._run_with_progress([action])

        self.app.push_screen(ConfirmModal(prompt), _on_confirm)


# -------------------------- Modules pane ----------------------------------


class ModulesPane(_SubPane):
    BINDINGS = [
        Binding("i", "act('install')", "install", show=False),
        Binding("c", "act('config')", "config", show=False),
        Binding("d", "act('deconfig')", "deconfig", show=False),
        Binding("u", "act('uninstall')", "uninstall", show=False),
        Binding("D", "act('doctor')", "doctor", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[ModuleRow] = []

    def _populate(self) -> None:
        self._rows = state.load_modules(self.app.dotfiles_root)
        needle = self.query_one("#filter", Input).value.strip().lower()
        headers = ["module", "actions", "status", "version/path", "drift"]
        rows: list[tuple[Any, list[str]]] = []
        visible: list[ModuleRow] = []
        keys: list[Any] = []
        for row in self._rows:
            label = f"{row.name} {row.path or ''}".strip()
            if needle and needle not in label.lower():
                continue
            key = ("module", row.name)
            cells = [
                row.name,
                row.actions_text or "-",
                row.status_text,
                (row.path or row.version or ""),
                row.drift_text,
            ]
            rows.append((key, cells))
            keys.append(key)
            visible.append(row)
        self._key_to_row = dict(zip(keys, visible))
        self._populate_filtered(headers, rows)

    def _collect_selected_actions(self) -> list[SelectedAction]:
        actions: list[SelectedAction] = []
        for key in self.selected:
            row = self._key_to_row.get(key)
            if row is None:
                continue
            for cap in row.capabilities:
                if cap in {"install", "config", "uninstall"}:
                    actions.append(
                        SelectedAction(label=f"{row.name}/{cap}", argv=tuple(self._argv(row.name, cap)))
                    )
        return actions

    def action_act(self, action: str) -> None:
        row = self.current_item()
        if row is None:
            return
        if action not in row.capabilities:
            return
        if action in {"uninstall", "deconfig"}:
            selected = SelectedAction(
                label=f"{row.name}/{action}",
                argv=tuple(self._argv(row.name, action)),
            )
            self._confirm_then_run(selected, f"确认 {action} {row.name}？输入 y 确认。")
            return
        self._run_with_progress(
            [SelectedAction(label=f"{row.name}/{action}", argv=tuple(self._argv(row.name, action)))]
        )

    def _argv(self, module: str, action: str) -> list[str]:
        extra = ["--doctor"] if action == "doctor" else [f"--{action}"]
        return _dotf_cmd(self.app.dotfiles_root, module, *extra, "--yes")


# -------------------------- Skills / MCP panes ----------------------------


class SkillsPane(_SubPane):
    BINDINGS = [
        Binding("a", "act('apply')", "apply", show=False),
        Binding("x", "act('remove')", "remove", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[SkillRow] = []

    def _populate(self) -> None:
        self._rows = state.load_skills(self.app.dotfiles_root)
        needle = self.query_one("#filter", Input).value.strip().lower()
        rows: list[tuple[Any, list[str]]] = []
        visible: list[SkillRow] = []
        keys: list[Any] = []
        for row in self._rows:
            if needle and needle not in row.skill_id.lower():
                continue
            key = ("skill", row.skill_id)
            cells = [row.skill_id, row.actions_text, row.status_text, "", ""]
            rows.append((key, cells))
            keys.append(key)
            visible.append(row)
        self._key_to_row = dict(zip(keys, visible))
        self._populate_filtered(["skill", "actions", "status", "", ""], rows)

    def action_act(self, verb: str) -> None:
        row = self.current_item()
        if row is None:
            return
        argv = _dotf_cmd(
            self.app.dotfiles_root,
            "agents",
            "skill",
            verb,
            row.skill_id,
        )
        if verb == "apply":
            argv.append("--yes")
        action = SelectedAction(label=f"{verb} {row.skill_id}", argv=tuple(argv))
        if verb == "remove":
            self._confirm_then_run(action, f"确认 remove skill {row.skill_id}？输入 y 确认。")
            return
        self._run_with_progress([action])


class McpPane(_SubPane):
    BINDINGS = [
        Binding("a", "act('apply')", "apply", show=False),
        Binding("x", "act('remove')", "remove", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[McpRow] = []

    def _populate(self) -> None:
        self._rows = state.load_mcp(self.app.dotfiles_root)
        needle = self.query_one("#filter", Input).value.strip().lower()
        rows: list[tuple[Any, list[str]]] = []
        visible: list[McpRow] = []
        keys: list[Any] = []
        for row in self._rows:
            label = f"{row.tool}/{row.server}"
            if needle and needle not in label.lower():
                continue
            key = ("mcp", label)
            cells = [label, row.actions_text, row.status_text, "", ""]
            rows.append((key, cells))
            keys.append(key)
            visible.append(row)
        self._key_to_row = dict(zip(keys, visible))
        self._populate_filtered(["server", "actions", "status", "", ""], rows)

    def action_act(self, verb: str) -> None:
        row = self.current_item()
        if row is None:
            return
        argv = _dotf_cmd(
            self.app.dotfiles_root,
            "agents",
            "mcp",
            verb,
            row.server,
            "--tool",
            row.tool,
        )
        if verb == "apply":
            argv.append("--yes")
        action = SelectedAction(label=f"{verb} {row.tool}/{row.server}", argv=tuple(argv))
        if verb == "remove":
            self._confirm_then_run(action, f"确认 remove MCP {row.tool}/{row.server}？输入 y 确认。")
            return
        self._run_with_progress([action])


# -------------------------- Status / Conflicts ----------------------------


class StatusPane(_SubPane):
    READONLY = True

    def _populate(self) -> None:
        rows = state.load_modules(self.app.dotfiles_root)
        table = self.query_one("#table", DataTable)
        table.clear(columns=True)
        table.add_columns("summary")
        for row in rows:
            table.add_row(
                f"{row.name:20s} install={str(row.installed):5s} "
                f"config={str(row.configured):5s} drift={row.drift}"
            )
        self._key_to_row = {}
        self.app.refresh_action_status()


class ConflictsPane(_SubPane):
    READONLY = True

    def _populate(self) -> None:
        rows = state.load_modules(self.app.dotfiles_root)
        failed = state.load_journal_failures()
        drifted = [r.name for r in rows if r.drift in {"changed", "missing", "conflict", "permission"}]
        body_lines: list[str] = []
        if drifted:
            body_lines.append("manifest drift:")
            body_lines.extend(f"  - {name}" for name in drifted)
        if failed:
            body_lines.append("journal failed modules:")
            body_lines.extend(f"  - {name}" for name in failed)
        if not body_lines:
            body_lines.append("(no conflicts)")
        table = self.query_one("#table", DataTable)
        table.clear(columns=True)
        table.add_columns("conflicts")
        for line in body_lines:
            table.add_row(line)
        self._key_to_row = {}
        self.app.refresh_action_status()


# -------------------------- helpers ---------------------------------------


def _dotf_cmd(root: Path, *args: str) -> list[str]:
    """``bin/dotf`` is bash; never prefix it with the Python interpreter."""
    return [str(root / "bin" / "dotf"), *args]


def _after_dotf(argv: list[str]) -> list[str]:
    names = [Path(part).name for part in argv]
    try:
        return list(argv[names.index("dotf") + 1 :])
    except ValueError:
        return list(argv[1:] if argv else [])


def _dotf_display(argv: list[str]) -> str:
    rest = _after_dotf(argv)
    return " ".join(["dotf", *rest] if rest else argv)


def _argv_change_label(argv: list[str]) -> str:
    """Best-effort change label from argv (used for session_changes echo)."""
    rest = _after_dotf(argv)
    module = next((arg for arg in rest if not arg.startswith("-")), "")
    skip = {"--yes", "--dry-run", "--json", "--tool"}
    action = next((arg.lstrip("-") for arg in rest if arg.startswith("--") and arg not in skip), None)
    if action and module:
        return f"{action} {module}"
    return " ".join(rest) if rest else " ".join(argv)


_PANE_TYPES: dict[str, type[_SubPane]] = {
    "modules": ModulesPane,
    "skills": SkillsPane,
    "mcp": McpPane,
    "status": StatusPane,
    "conflicts": ConflictsPane,
}

# Back-compat aliases for tests / smoke that imported *Screen names.
ModulesScreen = ModulesPane
SkillsScreen = SkillsPane
McpScreen = McpPane
StatusScreen = StatusPane
ConflictsScreen = ConflictsPane


# -------------------------- App -------------------------------------------


class DotfTuiApp(App[list[str] | None]):
    TITLE = "dotf tui"

    BINDINGS = [
        Binding("tab", "next_tab", "下一类", priority=True),
        Binding("shift+tab", "prev_tab", "上一类", priority=True),
        Binding("slash", "focus_filter", "过滤"),
        Binding("escape", "back_or_clear", "清空"),
        Binding("ctrl+x", "clear_selection", "清空选中"),
        Binding("q", "quit_manager", "退出"),
    ]

    CSS = """
    Screen { layout: vertical; }
    #tabs { height: 1fr; }
    TabbedContent { height: 1fr; }
    TabPane { height: 1fr; layout: vertical; }
    #log { height: 1; padding: 0 1; color: $text-muted; }
    #status_bar { height: 2; padding: 0 1; background: $boost; }
    """

    def __init__(self, dotfiles_root: Path) -> None:
        super().__init__()
        self.dotfiles_root = dotfiles_root
        self.session_changes: list[str] = []
        self._pending_g = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with TabbedContent(initial="modules", id="tabs"):
            with TabPane(TAB_TITLES["modules"], id="modules"):
                yield ModulesPane()
            with TabPane(TAB_TITLES["skills"], id="skills"):
                yield SkillsPane()
            with TabPane(TAB_TITLES["mcp"], id="mcp"):
                yield McpPane()
            with TabPane(TAB_TITLES["status"], id="status"):
                yield StatusPane()
            with TabPane(TAB_TITLES["conflicts"], id="conflicts"):
                yield ConflictsPane()
        yield Static("", id="log")
        yield Static("", id="status_bar")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(ModulesPane).query_one("#table", DataTable).focus()
        self.refresh_action_status()

    @property
    def active_pane(self) -> _SubPane:
        active = self.query_one("#tabs", TabbedContent).active
        return self.query_one(_PANE_TYPES[active])

    def _modal_open(self) -> bool:
        return isinstance(self.screen, ModalScreen)

    def action_go_tab(self, target: str) -> None:
        if self._modal_open() or target not in TAB_IDS:
            return
        self.query_one("#tabs", TabbedContent).active = target

    def action_next_tab(self) -> None:
        if self._modal_open():
            return
        tabs = self.query_one("#tabs", TabbedContent)
        idx = TAB_IDS.index(tabs.active) if tabs.active in TAB_IDS else 0
        tabs.active = TAB_IDS[(idx + 1) % len(TAB_IDS)]

    def action_prev_tab(self) -> None:
        if self._modal_open():
            return
        tabs = self.query_one("#tabs", TabbedContent)
        idx = TAB_IDS.index(tabs.active) if tabs.active in TAB_IDS else 0
        tabs.active = TAB_IDS[(idx - 1) % len(TAB_IDS)]

    def action_focus_filter(self) -> None:
        if self._modal_open():
            return
        self.active_pane.show_filter()

    def action_back_or_clear(self) -> None:
        if self._modal_open():
            return
        pane = self.active_pane
        filt = pane.query_one("#filter", Input)
        if filt.display or filt.value or isinstance(self.focused, Input):
            pane.hide_filter()

    def action_quit_manager(self) -> None:
        if self._modal_open():
            return
        self.exit()

    def action_toggle_select(self) -> None:
        pane = self.active_pane
        if pane.READONLY:
            return
        key = pane._current_key()
        if key is None:
            return
        if key in pane.selected:
            pane.selected.discard(key)
        else:
            pane.selected.add(key)
        pane.redraw_selection(keep_cursor=True)
        self.refresh_action_status()

    def action_clear_selection(self) -> None:
        if self._modal_open() or isinstance(self.focused, Input):
            return
        pane = self.active_pane
        if pane.READONLY or not pane.selected:
            return
        count = len(pane.selected)

        def _on_confirm(ok: bool | None) -> None:
            if not ok:
                return
            pane.selected.clear()
            pane.redraw_selection(keep_cursor=True)
            self.refresh_action_status()

        self.push_screen(ConfirmModal(f"确认清空 {count} 项选中？输入 y 确认。"), _on_confirm)

    def action_run_batch(self) -> None:
        pane = self.active_pane
        if pane.READONLY or not pane.selected:
            return
        actions = list(pane._collect_selected_actions())
        if not actions:
            return
        pane._run_with_progress(actions)

    def on_key(self, event) -> None:
        if self._modal_open():
            return
        if isinstance(self.focused, Input):
            if event.key != "g":
                self._pending_g = False
            return
        if event.character and event.character in "12345":
            self.action_go_tab(TAB_IDS[int(event.character) - 1])
            event.prevent_default()
            self._pending_g = False
            return
        if event.key != "g":
            self._pending_g = False

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        try:
            self.active_pane.query_one("#table", DataTable).focus()
        except Exception:
            return
        self.refresh_action_status()

    def refresh_action_status(self) -> None:
        try:
            pane = self.active_pane
        except Exception:
            return
        text = format_action_status(
            pane.current_item(),
            selected_count=len(pane.selected),
            readonly=pane.READONLY,
        )
        self.query_one("#status_bar", Static).update(text)

    def on_unmount(self) -> None:
        if self.session_changes:
            seen: set[str] = set()
            ordered: list[str] = []
            for change in self.session_changes:
                if change in seen:
                    continue
                seen.add(change)
                ordered.append(change)
            print("本会话改动：" + ", ".join(ordered), file=sys.stdout)
        else:
            print("本会话无改动", file=sys.stdout)

    def add_change(self, label: str) -> None:
        self.session_changes.append(label)


def build_app(root: Path):
    return DotfTuiApp(root)
