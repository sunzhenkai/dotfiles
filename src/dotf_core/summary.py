"""执行结果汇总：解析 RESULT 行协议，渲染最终结论。

run_plan.sh 结尾把收集到的 RESULT 行通过 stdin 传入：

    printf '%s\\n' "${RESULT_LINES[@]}" | python3 -m dotf_core.summary \\
        --total "$TOTAL_ACTIONS" --report "$saved"

不读执行 journal：status 模式没有 journal（RUN_ID 为空），RESULT 流是唯一在所有
路径上都存在的输入。
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

from . import term

STATUSES = ("changed", "unchanged", "skipped", "failed", "blocked", "not-run")
PERMANENT_STATUSES = frozenset({"changed", "failed"})
LABELS = {
    "changed": "变更",
    "skipped": "跳过",
    "failed": "失败",
    "blocked": "阻塞",
    "not-run": "未执行",
}
STYLES = {
    "changed": "ok",
    "skipped": "dim",
    "failed": "err",
    "blocked": "warn",
    "not-run": "dim",
}
DETAIL_ORDER = ("changed", "skipped", "failed", "blocked", "not-run")


@dataclass
class Outcome:
    status: str
    module: str
    action: str
    duration_ms: int = 0
    exit_code: int = 0
    reason: str = ""

    @property
    def item(self) -> str:
        return f"{self.module}/{self.action}"


def parse_result(line: str) -> Outcome | None:
    """`RESULT\\t<status>\\t<module>\\t<action>\\t<ms>\\t<exit>\\t<reason>`。"""
    if not line.startswith("RESULT\t"):
        return None
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 7 or parts[1] not in STATUSES:
        return None
    try:
        duration_ms = int(parts[4] or 0)
        exit_code = int(parts[5] or 0)
    except ValueError:
        duration_ms = 0
        exit_code = 0
    return Outcome(parts[1], parts[2], parts[3], duration_ms, exit_code, parts[6].strip())


def permanent_line(outcome: Outcome, enabled: bool | None = None) -> str:
    """quiet 模式下每个 changed/failed 动作留下的那一行。"""
    style = "ok" if outcome.status == "changed" else "err"
    symbol = term.SYMBOLS["ok" if outcome.status == "changed" else "err"]
    parts = [
        term.paint(symbol, style, enabled),
        term.paint(f"{outcome.module} · {outcome.action}", "bold", enabled),
    ]
    if outcome.duration_ms:
        parts.append(term.paint(term.humanize_ms(outcome.duration_ms), "dim", enabled))
    if outcome.reason and outcome.reason != "ok":
        parts.append(term.paint(outcome.reason, "dim", enabled))
    return "  ".join(parts)


def _shorten(path: str) -> str:
    home = os.environ.get("HOME", "")
    if home and path.startswith(home + os.sep):
        return "~" + path[len(home) :]
    return path


def _headline(counts: dict[str, int], done: int, total: int, interrupted: bool, enabled: bool) -> str:
    ok = term.SYMBOLS["ok"]
    err = term.SYMBOLS["err"]
    if interrupted:
        return f"{term.paint(err, 'err', enabled)} {term.paint('中断', 'err', enabled)}  {done}/{total}"
    if counts["failed"] or counts["blocked"] or counts["not-run"]:
        return f"{term.paint(err, 'err', enabled)} {term.paint('失败', 'err', enabled)}  {done}/{total}"
    bits: list[str] = []
    if counts["changed"]:
        bits.append(term.paint(f"{counts['changed']} 项变更", "ok", enabled))
    if counts["unchanged"]:
        bits.append(f"{counts['unchanged']} 项已是最新")
    if counts["skipped"]:
        bits.append(f"{counts['skipped']} 项跳过")
    text = " · ".join(bits) or "无变更"
    return f"{term.paint(ok, 'ok', enabled)} {term.paint('完成', 'ok', enabled)}  {text}"


def render_summary(
    outcomes: list[Outcome],
    *,
    total: int | None = None,
    report: str = "",
    interrupted: bool = False,
    enabled: bool | None = None,
) -> str:
    if enabled is None:
        enabled = term.color_mode()
    counts = {status: 0 for status in STATUSES}
    for outcome in outcomes:
        counts[outcome.status] = counts.get(outcome.status, 0) + 1
    total_actions = total if total is not None else len(outcomes)
    done = counts["changed"] + counts["unchanged"] + counts["skipped"] + counts["failed"]

    if total_actions <= 0 and not outcomes:
        return f"{term.paint(term.SYMBOLS['ok'], 'ok', enabled)} 无动作"

    head = _headline(counts, done, total_actions, interrupted, enabled)
    duration = sum(
        o.duration_ms
        for o in outcomes
        if o.status in ("changed", "unchanged", "skipped", "failed")
    )
    if duration:
        head += f"  {term.paint(term.humanize_ms(duration), 'dim', enabled)}"
    lines = [head]

    for status in DETAIL_ORDER:
        items = [o for o in outcomes if o.status == status]
        if not items:
            continue
        label = term.paint(LABELS[status], STYLES[status], enabled)
        if status in ("failed", "blocked", "not-run"):
            body = "  ".join(
                o.item + (f"  {o.reason}" if o.reason else "") for o in items
            )
        else:
            body = "  ".join(o.item for o in items)
        lines.append(f"  {label}  {body}")

    if report:
        lines.append(
            f"  {term.paint('报告', 'dim', enabled)}  "
            f"{term.paint(_shorten(report), 'dim', enabled)}"
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dotf_core.summary", description="执行结果汇总")
    parser.add_argument("--total", type=int, default=None, help="计划动作总数")
    parser.add_argument("--report", default="", help="最后一份执行报告路径")
    parser.add_argument("--interrupted", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    outcomes = [o for line in sys.stdin if (o := parse_result(line)) is not None]
    print(
        render_summary(
            outcomes,
            total=args.total,
            report=args.report,
            interrupted=args.interrupted,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
