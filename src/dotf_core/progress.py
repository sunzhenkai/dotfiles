"""执行期进度过滤器：插在 run_plan.sh 现有的 ``tee`` 位置。

    runner_run_action ... 2>&1 | sanitize-stream | python3 -u -m dotf_core.progress ...

约定
----
- stdin 的全部行原样写入 ``--log``，``RESULT`` / ``PROGRESS`` 行也不例外，
  run_plan.sh 的 RESULT 解析因此完全不受影响。
- ``PROGRESS\\t<stage>\\t<done>\\t<total>`` 由 handler 上报，只用于渲染，
  任何模式下都不进入终端（verbose 的原始阶段行已经说明了同样的事）。
- quiet（stderr 是 TTY，且未加 ``--verbose`` / ``--no-progress``）：终端只留一行
  进度，其余行收进日志，失败由 run_plan.sh 回放日志尾部。
- 其余情况（CI、管道、``--verbose``）：handler 行原样透传，不渲染进度。
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import threading
from dataclasses import dataclass

from . import summary, term

PROGRESS_PREFIX = "PROGRESS\t"
_SUBSTAGE_SEP = " · "


@dataclass
class ProgressState:
    total_actions: int = 1
    index: int = 1
    module: str = ""
    action: str = ""
    stage: str = ""
    stage_done: int = 0
    stage_total: int = 0

    def label(self) -> str:
        parts = [p for p in (self.module, self.action, self.stage) if p]
        return _SUBSTAGE_SEP.join(parts)


def parse_progress(line: str) -> tuple[str, int, int] | None:
    """`PROGRESS\\t<stage>\\t<done>\\t<total>` → (stage, done, total)；格式不符返回 None。"""
    if not line.startswith(PROGRESS_PREFIX):
        return None
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 4:
        return None
    stage = parts[1].strip()
    if not stage:
        return None
    try:
        done = int(parts[2] or 0)
        total = int(parts[3] or 0)
    except ValueError:
        return None
    return stage, max(done, 0), max(total, 0)


def render_line(
    state: ProgressState,
    *,
    enabled: bool = False,
    width: int = 80,
    frame: int = 0,
) -> str:
    """一格 = 一个动作；动作数 <2 时画不出有意义的条，改用旋转指示。"""
    if state.total_actions >= 2:
        bar_width = term.BAR_WIDTH if width >= 60 else 8
        prefix = term.bar(state.index, state.total_actions, width=bar_width, enabled=enabled)
        counter = f" {state.index}/{state.total_actions}"
    else:
        prefix = term.SPINNER[frame % len(term.SPINNER)]
        counter = " 1 项"
    label = state.label()
    if state.stage_total:
        label += f" {state.stage_done}/{state.stage_total}"
    room = width - term.display_width(prefix) - term.display_width(counter) - 2
    label = term.truncate(label, max(0, room))
    return f"{prefix}{term.paint(counter, 'dim', enabled)}  {label}"


class ProgressRenderer:
    """单行原地刷新；没有新输出时靠 ticker 让旋转符继续转。"""

    def __init__(
        self,
        stream,
        *,
        width: int | None = None,
        enabled: bool = True,
        animate: bool = True,
        interval: float = 0.12,
    ) -> None:
        self.stream = stream
        self.width = width or terminal_width(stream)
        self.enabled = enabled
        self.color = term.color_mode(stream=stream)
        self.animate = animate and enabled
        self.interval = interval
        self.state: ProgressState | None = None
        self.frame = 0
        self._lock = threading.Lock()
        self._drawn = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self.animate:
            return
        self._thread = threading.Thread(target=self._tick, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def update(self, state: ProgressState) -> None:
        if not self.enabled:
            return
        with self._lock:
            self.state = state
            self._draw()

    def clear(self) -> None:
        if not self.enabled or not self._drawn:
            return
        with self._lock:
            if self._drawn:
                self.stream.write("\r\033[K")
                self.stream.flush()
                self._drawn = False

    def freeze(self) -> None:
        """停止后续重绘，给永久结果行让位。"""
        with self._lock:
            self.state = None

    def _tick(self) -> None:
        while not self._stop.wait(self.interval):
            with self._lock:
                self.frame += 1
                if self.state is not None and self.state.total_actions < 2:
                    self._draw()

    def _draw(self) -> None:
        if self.state is None:
            return
        line = render_line(self.state, enabled=self.color, width=self.width, frame=self.frame)
        self.stream.write("\r" + line + "\033[K")
        self.stream.flush()
        self._drawn = True


def terminal_width(stream=None) -> int:
    columns = os.environ.get("COLUMNS", "")
    if columns.isdigit() and int(columns) > 0:
        return int(columns)
    try:
        return shutil.get_terminal_size((80, 24)).columns
    except OSError:
        return 80


def run(
    instream,
    passthrough,
    progress_stream,
    *,
    log_path: str,
    total_actions: int = 1,
    index: int = 1,
    module: str = "",
    action: str = "",
    verbose: bool = False,
    no_progress: bool = False,
    width: int | None = None,
    animate: bool = True,
) -> int:
    enabled = not no_progress and not verbose and term.is_tty(progress_stream)
    state = ProgressState(
        total_actions=max(1, int(total_actions)),
        index=max(1, int(index)),
        module=module,
        action=action,
    )
    renderer = ProgressRenderer(
        progress_stream, width=width, enabled=enabled, animate=animate
    )
    result_color = term.color_mode(stream=passthrough)
    with open(log_path, "w", encoding="utf-8", errors="replace") as log:
        renderer.start()
        try:
            renderer.update(state)
            for line in instream:
                log.write(line)
                parsed = parse_progress(line)
                if parsed is not None:
                    state.stage, state.stage_done, state.stage_total = parsed
                    renderer.update(state)
                    continue
                if enabled:
                    # quiet：除进度行与最终结果行外，handler 输出一律只进日志。
                    outcome = summary.parse_result(line)
                    if outcome is not None and outcome.status in summary.PERMANENT_STATUSES:
                        renderer.freeze()
                        renderer.clear()
                        passthrough.write(summary.permanent_line(outcome, result_color) + "\n")
                        passthrough.flush()
                    continue
                passthrough.write(line)
                passthrough.flush()
        finally:
            renderer.stop()
            renderer.clear()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dotf_core.progress", description="执行期进度过滤器"
    )
    parser.add_argument("--log", required=True, help="原始输出落盘路径")
    parser.add_argument("--total-actions", type=int, default=1)
    parser.add_argument("--index", type=int, default=1)
    parser.add_argument("--module", default="")
    parser.add_argument("--action", default="")
    parser.add_argument("--verbose", action="store_true", help="原样透传 handler 输出")
    parser.add_argument("--no-progress", action="store_true", help="不渲染进度行")
    parser.add_argument("--no-animate", action="store_true", help="不转动旋转符")
    parser.add_argument("--width", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    return run(
        sys.stdin,
        sys.stdout,
        sys.stderr,
        log_path=args.log,
        total_actions=args.total_actions,
        index=args.index,
        module=args.module,
        action=args.action,
        verbose=args.verbose,
        no_progress=args.no_progress,
        width=args.width,
        animate=not args.no_animate,
    )


if __name__ == "__main__":
    raise SystemExit(main())
