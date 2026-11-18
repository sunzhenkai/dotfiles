"""summary：RESULT 行解析、永久结果行、结尾汇总。"""

from __future__ import annotations

from dotf_core import summary, term

RESULT_LINE = "RESULT\tchanged\tagents\tconfig\t4934\t0\tok"


def test_parse_result() -> None:
    outcome = summary.parse_result(RESULT_LINE)
    assert outcome is not None
    assert (outcome.status, outcome.module, outcome.action) == ("changed", "agents", "config")
    assert outcome.duration_ms == 4934
    assert outcome.reason == "ok"
    assert summary.parse_result("RESULT\tbogus\ta\tb\t0\t0\tx") is None
    assert summary.parse_result("RESULT\tonly\tthree") is None
    assert summary.parse_result("==> skills\n") is None


def test_permanent_line_for_changed() -> None:
    outcome = summary.parse_result(RESULT_LINE)
    assert outcome is not None
    line = summary.permanent_line(outcome, enabled=False)
    assert line == "✓  agents · config  4.9s"


def test_permanent_line_for_failed_keeps_reason() -> None:
    outcome = summary.parse_result("RESULT\tfailed\tm5\tinstall\t820\t1\thandler-failed")
    assert outcome is not None
    line = summary.permanent_line(outcome, enabled=False)
    assert line == "✗  m5 · install  820ms  handler-failed"


def test_summary_all_unchanged() -> None:
    outcomes = [
        summary.parse_result(f"RESULT\tunchanged\tmod{i}\tconfig\t1000\t0\tok")
        for i in range(3)
    ]
    text = summary.render_summary([o for o in outcomes if o], total=3, enabled=False)
    assert text.splitlines()[0] == "✓ 完成  3 项已是最新  3.0s"
    assert "变更" not in text


def test_summary_lists_changed_items() -> None:
    outcomes = [
        summary.parse_result("RESULT\tchanged\tagents\tconfig\t2000\t0\tok"),
        summary.parse_result("RESULT\tunchanged\tnvim\tconfig\t1000\t0\tok"),
    ]
    text = summary.render_summary([o for o in outcomes if o], total=2, enabled=False)
    lines = text.splitlines()
    assert lines[0] == "✓ 完成  1 项变更 · 1 项已是最新  3.0s"
    assert lines[1] == "  变更  agents/config"


def test_summary_failure_headline_and_details() -> None:
    outcomes = [
        summary.parse_result("RESULT\tchanged\tagents\tconfig\t2000\t0\tok"),
        summary.parse_result("RESULT\tfailed\tm5\tinstall\t820\t1\thandler-failed"),
        summary.parse_result("RESULT\tnot-run\tnvim\tconfig\t0\t0\tdependency-failed"),
    ]
    text = summary.render_summary([o for o in outcomes if o], total=3, enabled=False)
    lines = text.splitlines()
    assert lines[0] == "✗ 失败  2/3  2.8s"
    assert "失败  m5/install  handler-failed" in text
    assert "未执行  nvim/config  dependency-failed" in text


def test_summary_blocked_items() -> None:
    outcomes = [summary.parse_result("RESULT\tblocked\tbase\tconfig\t0\t0\tsame-module-failed")]
    text = summary.render_summary([o for o in outcomes if o], total=1, enabled=False)
    assert text.splitlines()[0] == "✗ 失败  0/1"
    assert "阻塞  base/config  same-module-failed" in text


def test_summary_interrupted() -> None:
    outcomes = [summary.parse_result("RESULT\tunchanged\tmod0\tconfig\t1000\t0\tok")]
    text = summary.render_summary(
        [o for o in outcomes if o], total=8, interrupted=True, enabled=False
    )
    assert text.splitlines()[0] == "✗ 中断  1/8  1.0s"


def test_summary_report_path_is_shortened(monkeypatch) -> None:
    monkeypatch.setenv("HOME", "/home/tester")
    outcomes = [summary.parse_result("RESULT\tunchanged\tmod0\tconfig\t1000\t0\tok")]
    text = summary.render_summary(
        [o for o in outcomes if o],
        total=1,
        report="/home/tester/.local/state/dotf/last-run.json",
        enabled=False,
    )
    assert text.splitlines()[-1] == "  报告  ~/.local/state/dotf/last-run.json"


def test_summary_empty_plan() -> None:
    assert summary.render_summary([], total=0, enabled=False) == "✓ 无动作"


def test_summary_colors_when_enabled() -> None:
    outcomes = [summary.parse_result("RESULT\tfailed\tm5\tinstall\t820\t1\tboom")]
    text = summary.render_summary([o for o in outcomes if o], total=1, enabled=True)
    assert "\033[31m" in text
    assert term.strip_ansi(text) == summary.render_summary(
        [o for o in outcomes if o], total=1, enabled=False
    )
