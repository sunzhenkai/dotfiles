"""progress：PROGRESS 行解析、单行渲染、过滤器三种模式的行为。"""

from __future__ import annotations

import io

from dotf_core import progress, term

HANDLER_OUTPUT = (
    "==> skills  planning…\n"
    "PROGRESS\tskills\t2\t5\n"
    "  = /home/wii/.agents/AGENTS.md\n"
    "done skills: changed=0 pruned=0 unchanged=6\n"
    "RESULT\tunchanged\tagents\tconfig\t4934\t0\tok\n"
)


class FakeTty(io.StringIO):
    def isatty(self) -> bool:  # noqa: D102 - 测试替身
        return True


def _run(source: str, *, tty: bool, **kwargs):
    out = FakeTty() if tty else io.StringIO()
    err = FakeTty() if tty else io.StringIO()
    log = kwargs.pop("log_path")
    code = progress.run(
        io.StringIO(source),
        out,
        err,
        log_path=log,
        module="agents",
        action="config",
        animate=False,
        **kwargs,
    )
    return code, out.getvalue(), err.getvalue()


def test_parse_progress() -> None:
    assert progress.parse_progress("PROGRESS\tskills\t2\t5\n") == ("skills", 2, 5)
    assert progress.parse_progress("PROGRESS\tdefaults\t0\t0") == ("defaults", 0, 0)
    assert progress.parse_progress("PROGRESS\tskills\tx\t5\n") is None
    assert progress.parse_progress("PROGRESS\tskills\t1\n") is None
    assert progress.parse_progress("PROGRESS\t\t1\t5\n") is None
    assert progress.parse_progress("==> skills\n") is None


def test_render_line_uses_action_bar_when_multiple_actions() -> None:
    state = progress.ProgressState(
        total_actions=8, index=3, module="nvim", action="config"
    )
    line = term.strip_ansi(progress.render_line(state, width=80))
    assert "3/8" in line
    assert "nvim · config" in line
    assert line.startswith("[")


def test_render_line_uses_spinner_for_single_action() -> None:
    state = progress.ProgressState(
        total_actions=1,
        index=1,
        module="agents",
        action="config",
        stage="skills",
        stage_done=2,
        stage_total=5,
    )
    line = term.strip_ansi(progress.render_line(state, width=80, frame=0))
    assert "[" not in line
    assert "1 项" in line
    assert "agents · config · skills 2/5" in line
    assert line.startswith(term.SPINNER[0])


def test_render_line_fits_terminal_width() -> None:
    state = progress.ProgressState(
        total_actions=8,
        index=3,
        module="agents",
        action="config",
        stage="a-very-long-stage-name",
    )
    for width in (20, 30, 80):
        line = progress.render_line(state, width=width)
        assert term.display_width(line) <= width


def test_quiet_mode_keeps_only_progress_line(tmp_path) -> None:
    log = tmp_path / "capture.log"
    code, out, err = _run(
        HANDLER_OUTPUT,
        tty=True,
        log_path=str(log),
        total_actions=1,
        index=1,
    )
    assert code == 0
    # handler 输出不外泄
    assert out == ""
    stripped = term.strip_ansi(err)
    assert "==> skills" not in stripped
    assert "RESULT" not in stripped
    # 进度行出现过，末态带阶段子计数
    assert "agents · config · skills 2/5" in stripped
    # 结束时抹掉进度行
    assert err.endswith("\r\033[K")
    # 日志完整，RESULT 与 PROGRESS 都在
    assert log.read_text(encoding="utf-8") == HANDLER_OUTPUT


def test_passthrough_when_not_a_tty(tmp_path) -> None:
    log = tmp_path / "capture.log"
    code, out, err = _run(HANDLER_OUTPUT, tty=False, log_path=str(log))
    assert code == 0
    assert err == ""
    assert "==> skills  planning…" in out
    assert "RESULT\tunchanged\tagents\tconfig" in out
    # PROGRESS 是渲染指令，任何模式下都不外泄
    assert "PROGRESS\t" not in out
    assert log.read_text(encoding="utf-8") == HANDLER_OUTPUT


def test_verbose_passes_through_even_on_tty(tmp_path) -> None:
    log = tmp_path / "capture.log"
    code, out, err = _run(HANDLER_OUTPUT, tty=True, log_path=str(log), verbose=True)
    assert code == 0
    assert err == ""
    assert "==> skills  planning…" in out
    assert "\033[K" not in out


def test_no_progress_flag_disables_rendering(tmp_path) -> None:
    log = tmp_path / "capture.log"
    code, out, err = _run(HANDLER_OUTPUT, tty=True, log_path=str(log), no_progress=True)
    assert code == 0
    assert err == ""
    assert "==> skills  planning…" in out


def test_terminal_width_prefers_columns(monkeypatch) -> None:
    monkeypatch.setenv("COLUMNS", "123")
    assert progress.terminal_width() == 123
    monkeypatch.setenv("COLUMNS", "bogus")
    assert progress.terminal_width() >= 20


def test_drop_result_hides_machine_line_from_terminal_only(tmp_path) -> None:
    log = tmp_path / "capture.log"
    code, out, err = _run(HANDLER_OUTPUT, tty=False, log_path=str(log), drop_result=True)
    assert code == 0
    assert "RESULT\t" not in out
    assert "==> skills  planning…" in out
    assert "RESULT\tunchanged\tagents\tconfig" in log.read_text(encoding="utf-8")


def test_warning_lines_survive_quiet_mode(tmp_path) -> None:
    source = (
        "==> zsh  planning…\n"
        "warning: 保留不再托管的目标（本地有改动或类型不安全，未删除）: ~/.config/zsh/a.zwc\n"
        "RESULT\tunchanged\tzsh\tconfig\t100\t0\tok\n"
    )
    log = tmp_path / "capture.log"
    code, out, err = _run(source, tty=True, log_path=str(log))
    assert code == 0
    assert "保留不再托管的目标" in term.strip_ansi(out)
    assert "==> zsh" not in term.strip_ansi(out)
    assert log.read_text(encoding="utf-8") == source


def test_quiet_mode_leaves_permanent_line_for_changed_only(tmp_path) -> None:
    source = (
        "RESULT\tchanged\tagents\tconfig\t4934\t0\tok\n"
        "RESULT\tunchanged\tnvim\tconfig\t100\t0\tok\n"
    )
    log = tmp_path / "capture.log"
    code, out, err = _run(source, tty=True, log_path=str(log), total_actions=2, index=1)
    assert code == 0
    assert "✓  agents · config  4.9s" in term.strip_ansi(out)
    assert "RESULT" not in out
    assert "nvim" not in out
    # 进度行先被抹掉，永久行才落盘
    assert err.endswith("\r\033[K")
    assert log.read_text(encoding="utf-8") == source


def test_run_plan_replays_log_tail_on_failure_in_quiet_mode() -> None:
    from pathlib import Path

    run_plan = (Path(__file__).resolve().parent.parent / "scripts" / "run_plan.sh").read_text(
        encoding="utf-8"
    )
    assert "日志尾部" in run_plan
    assert "action_quiet" in run_plan
    assert "tail -n 25" in run_plan
