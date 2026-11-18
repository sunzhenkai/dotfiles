"""term：显示宽度、截断、进度条、时间格式、颜色开关矩阵。"""

from __future__ import annotations

from dotf_core import term


def test_display_width_counts_cjk_as_two() -> None:
    assert term.display_width("abc") == 3
    assert term.display_width("中文") == 4
    assert term.display_width("a中b") == 4
    assert term.display_width("") == 0


def test_display_width_ignores_ansi() -> None:
    painted = term.paint("中文", "ok", True)
    assert painted != "中文"
    assert term.display_width(painted) == 4


def test_truncate_respects_display_width() -> None:
    assert term.truncate("abcdef", 6) == "abcdef"
    assert term.truncate("abcdef", 4) == "abc…"
    assert term.truncate("中文中文", 4) == "中…"
    assert term.truncate("abc", 0) == ""


def test_bar_fills_and_clamps() -> None:
    assert term.bar(0, 8, width=8, enabled=False) == "[░░░░░░░░]"
    assert term.bar(3, 8, width=8, enabled=False) == "[███░░░░░]"
    assert term.bar(8, 8, width=8, enabled=False) == "[████████]"
    assert term.bar(99, 8, width=8, enabled=False) == "[████████]"
    assert term.bar(1, 0) == ""


def test_bar_paints_only_when_enabled() -> None:
    plain = term.bar(1, 2, width=4, enabled=False)
    colored = term.bar(1, 2, width=4, enabled=True)
    assert "\033" not in plain
    assert "\033[32m" in colored and "\033[0m" in colored
    assert term.strip_ansi(colored) == plain


def test_humanize_ms() -> None:
    assert term.humanize_ms(0) == "0ms"
    assert term.humanize_ms(999) == "999ms"
    assert term.humanize_ms(1000) == "1.0s"
    assert term.humanize_ms(4934) == "4.9s"
    assert term.humanize_ms(60_000) == "1m 0s"
    assert term.humanize_ms(732_000) == "12m 12s"
    assert term.humanize_ms(-5) == "0ms"


def test_color_mode_matrix() -> None:
    assert term.color_mode(env={}, tty=True) is True
    assert term.color_mode(env={}, tty=False) is False
    assert term.color_mode(env={"NO_COLOR": "1"}, tty=True) is False
    assert term.color_mode(env={"TERM": "dumb"}, tty=True) is False
    # 显式 DOTF_COLOR 覆盖 NO_COLOR 与非 TTY
    assert term.color_mode(env={"DOTF_COLOR": "always", "NO_COLOR": "1"}, tty=False) is True
    assert term.color_mode(env={"DOTF_COLOR": "never"}, tty=True) is False


def test_paint() -> None:
    assert term.paint("x", "ok", True) == "\033[32mx\033[0m"
    assert term.paint("x", "ok", False) == "x"
    assert term.paint("x", None, True) == "x"
    assert term.paint("x", "unknown", True) == "x"


def test_shell_exports_disable_colors_but_keep_symbols() -> None:
    plain = term.shell_exports(False)
    assert "\033" not in plain
    assert "DOTF_C_OK=''" in plain
    assert "DOTF_SYM_OK='✓'" in plain
    assert "DOTF_SYM_DOT='·'" in plain


def test_shell_exports_use_bash32_ansi_c_quoting() -> None:
    colored = term.shell_exports(True)
    assert "DOTF_C_OK=$'\\033[32m'" in colored
    assert "DOTF_C_RESET=$'\\033[0m'" in colored


def test_table_aligns_by_display_width() -> None:
    lines = term.table(("A", "B"), [("中", "x"), ("ab", "y")], enabled=False)
    assert lines[0] == "A   B"
    assert lines[1].startswith("─")
    assert lines[2] == "中  x"
    assert lines[3] == "ab  y"


def test_table_styles_header_only() -> None:
    plain = term.table(("A",), [("1",)], enabled=False)
    colored = term.table(("A",), [("1",)], enabled=True)
    assert "\033" not in "\n".join(plain)
    assert term.strip_ansi("\n".join(colored)) == "\n".join(plain)
