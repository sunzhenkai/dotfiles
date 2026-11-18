"""终端渲染原语：颜色、符号、显示宽度、进度条、时间格式。

人类输出的唯一样式来源。Python 侧直接调用；bash 侧用

    eval "$(python3 -m dotf_core.term --shell --tty "$([ -t 1 ] && echo 1 || echo 0)")"

取同一套常量，避免样式在两边各写一份。

`--tty` 必须由 bash 传入：命令替换里 Python 的 stdout 是管道，`isatty()` 恒为假。
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import unicodedata
from collections.abc import Mapping, Sequence

RESET = "\033[0m"

STYLES: dict[str, str] = {
    "bold": "\033[1m",
    "dim": "\033[2m",
    "ok": "\033[32m",
    "warn": "\033[33m",
    "err": "\033[31m",
    "accent": "\033[36m",
}

SYMBOLS: dict[str, str] = {
    "ok": "✓",
    "err": "✗",
    "warn": "!",
    "dot": "·",
    "arrow": "→",
    "branch": "↳",
    "step": "▸",
}

SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
BAR_FULL = "█"
BAR_EMPTY = "░"
BAR_WIDTH = 16

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")
_TRUE = frozenset({"always", "1", "true", "yes", "on"})
_FALSE = frozenset({"never", "0", "false", "no", "off"})


def color_mode(
    stream=None,
    env: Mapping[str, str] | None = None,
    tty: bool | None = None,
) -> bool:
    """显式 DOTF_COLOR > NO_COLOR > TERM=dumb > TTY。

    `tty` 显式给出时跳过流探测（bash 转发的判定比命令替换里的 `isatty()` 可信）。
    """
    env = os.environ if env is None else env
    choice = env.get("DOTF_COLOR", "").strip().lower()
    if choice in _TRUE:
        return True
    if choice in _FALSE:
        return False
    if env.get("NO_COLOR", ""):
        return False
    if env.get("TERM", "") == "dumb":
        return False
    if tty is None:
        tty = _isatty(sys.stdout if stream is None else stream)
    return tty


def is_tty(stream) -> bool:
    return _isatty(stream)


def _isatty(stream) -> bool:
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError, OSError):
        return False


def paint(text: str, style: str | None, enabled: bool | None = None) -> str:
    if not text or style is None:
        return text
    if enabled is None:
        enabled = color_mode()
    code = STYLES.get(style)
    if not enabled or not code:
        return text
    return f"{code}{text}{RESET}"


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def display_width(text: str) -> int:
    """终端列宽：中文/全角算 2 列，组合符与零宽字符算 0，ANSI 序列不算。"""
    width = 0
    for ch in strip_ansi(text):
        if unicodedata.combining(ch):
            continue
        if unicodedata.category(ch) in ("Mn", "Me", "Cf"):
            continue
        width += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return width


def truncate(text: str, width: int) -> str:
    """按显示宽度截断，超出时以 `…` 收尾。"""
    if width <= 0:
        return ""
    if display_width(text) <= width:
        return text
    kept: list[str] = []
    used = 0
    for ch in text:
        ch_width = display_width(ch)
        if used + ch_width > width - 1:
            break
        kept.append(ch)
        used += ch_width
    return "".join(kept) + "…"


def pad(text: str, width: int) -> str:
    return text + " " * max(0, width - display_width(text))


def table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    *,
    enabled: bool | None = None,
    gap: int = 2,
    rule: str = "─",
) -> list[str]:
    """按显示宽度对齐的文本表；列宽随内容，分隔线随内容长度。"""
    if enabled is None:
        enabled = color_mode()
    widths = [display_width(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row[: len(widths)]):
            widths[i] = max(widths[i], display_width(cell))

    def compose(cells: Sequence[str]) -> str:
        padded = [pad(cell, widths[i]) for i, cell in enumerate(cells[: len(widths)])]
        return (" " * gap).join(padded).rstrip()

    body = [
        paint(compose(headers), "bold", enabled),
        rule * min(sum(widths) + gap * (len(widths) - 1), 72),
    ]
    body.extend(compose(row) for row in rows)
    return body


def bar(done: int, total: int, width: int = BAR_WIDTH, enabled: bool | None = None) -> str:
    """`[████░░░░]`；done/total 超界时夹取，total<=0 返回空串。"""
    if total <= 0:
        return ""
    done = min(max(int(done), 0), total)
    filled = int(round(width * done / total))
    body_full = BAR_FULL * filled
    body_empty = BAR_EMPTY * (width - filled)
    if enabled is None:
        enabled = color_mode()
    if not enabled:
        return f"[{body_full}{body_empty}]"
    return f"[{paint(body_full, 'ok', True)}{paint(body_empty, 'dim', True)}]"


def humanize_ms(ms: int) -> str:
    """4934 → `4.9s`；60500 → `1m 0s`；不足 1 秒保留毫秒。"""
    ms = max(0, int(ms or 0))
    if ms < 1000:
        return f"{ms}ms"
    if ms < 60_000:
        return f"{ms / 1000:.1f}s"
    minutes, seconds = divmod(ms // 1000, 60)
    return f"{minutes}m {seconds}s"


def status_line(status: str, text: str, enabled: bool | None = None) -> str:
    """`pass|warn|fail|skip` 状态行；状态词留在行首，便于现有 grep 契约。"""
    style = {"pass": "ok", "warn": "warn", "fail": "err"}.get(status, "dim")
    return f"{paint(status, style, enabled)}  {text}"


def _single_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def _ansi_c(code: str) -> str:
    return "$'" + code.replace("\033", "\\033") + "'"


def shell_exports(enabled: bool | None = None) -> str:
    """bash 可 eval 的常量赋值（Bash 3.2 兼容：只用 ANSI-C 引用）。"""
    if enabled is None:
        enabled = color_mode()
    lines: list[str] = []
    for name, code in STYLES.items():
        lines.append(f"DOTF_C_{name.upper()}=" + (_ansi_c(code) if enabled else "''"))
    lines.append("DOTF_C_RESET=" + (_ansi_c(RESET) if enabled else "''"))
    for name, symbol in SYMBOLS.items():
        lines.append(f"DOTF_SYM_{name.upper()}=" + _single_quote(symbol))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dotf_core.term", description="终端渲染原语")
    parser.add_argument("--shell", action="store_true", help="输出 bash 常量赋值")
    parser.add_argument("--tty", choices=("auto", "0", "1"), default="auto")
    args = parser.parse_args(argv)
    if not args.shell:
        parser.print_help()
        return 2
    tty = None if args.tty == "auto" else args.tty == "1"
    print(shell_exports(color_mode(tty=tty)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
