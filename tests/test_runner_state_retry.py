"""Runner journals, bounded reports, interruption, concurrency, and safe retry."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

from plan_test_helpers import plan_env, write_test_plan

ROOT = Path(__file__).resolve().parent.parent
RUN_PLAN = ROOT / "scripts" / "run_plan.sh"
sys.path.insert(0, str(ROOT / "scripts"))
import execution_state  # noqa: E402


def _handler(root: Path, module: str, action: str, body: str) -> Path:
    path = root / module / f"{action}.sh"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8")
    path.chmod(0o700)
    return path


def _env(home: Path, plan: Path, handlers: Path) -> dict[str, str]:
    value = os.environ.copy()
    value.update(plan_env(plan, handlers))
    value["HOME"] = str(home)
    value["XDG_STATE_HOME"] = str(home / ".local" / "state")
    return value


def _run(
    home: Path,
    plan: Path,
    handlers: Path,
    *args: str,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = _env(home, plan, handlers)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(RUN_PLAN), "--yes", *args, "--plan-file", str(plan)],
        cwd=str(ROOT), env=env, capture_output=True, text=True, check=False,
    )


def _state(home: Path) -> Path:
    return home / ".local" / "state" / "dotf"


def _latest(home: Path) -> dict:
    return json.loads((_state(home) / "last-run.json").read_text(encoding="utf-8"))


def _journal(home: Path, summary: dict | None = None) -> tuple[Path, dict]:
    summary = summary or _latest(home)
    path = _state(home) / summary["journal"]
    return path, json.loads(path.read_text(encoding="utf-8"))


def _dotf_retry(home: Path, plan: Path, handlers: Path, *, load_log: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = _env(home, plan, handlers)
    if load_log is not None:
        env["DOTF_LOAD_LOG"] = str(load_log)
    return subprocess.run(
        ["bash", str(ROOT / "bin" / "dotf"), "retry"],
        cwd=str(ROOT), env=env, capture_output=True, text=True, check=False,
    )


def test_checkpoint_schema_permissions_atomic_latest_and_not_run(tmp_home: Path, tmp_path: Path) -> None:
    handlers = tmp_path / "handlers"
    _handler(handlers, "broken", "install", 'dotf_result_failed "expected failure" 7\n')
    _handler(handlers, "later", "install", 'dotf_result_changed "must not run"\n')
    plan = tmp_path / "plan.json"
    write_test_plan(plan, handlers, [("install", "broken"), ("install", "later")])

    result = _run(tmp_home, plan, handlers)
    assert result.returncode != 0
    state = _state(tmp_home)
    summary = _latest(tmp_home)
    journal_path, journal = _journal(tmp_home, summary)
    assert stat.S_IMODE(state.stat().st_mode) == 0o700
    assert stat.S_IMODE((state / "runs").stat().st_mode) == 0o700
    assert stat.S_IMODE(journal_path.stat().st_mode) == 0o600
    assert stat.S_IMODE((state / "last-run.json").stat().st_mode) == 0o600
    assert stat.S_IMODE((state / ".latest.lock").stat().st_mode) == 0o600
    assert journal["complete"] is True and journal["status"] == "failed"
    assert journal["current_action"] is None
    assert journal["plan_version"] == 1
    assert len(journal["plan_hash"]) == 64
    assert [item["status"] for item in journal["actions"]] == ["failed", "not-run"]
    assert all(item["ended_at"] and item["duration_ms"] is not None for item in journal["actions"])
    raw = journal_path.read_bytes()
    assert summary["journal_hash"] == hashlib.sha256(raw).hexdigest()
    assert summary["actions"] == journal["actions"]
    assert not list(state.glob(".last-run.json.*"))


def test_secret_reason_is_redacted_on_terminal_json_journal_and_latest(tmp_home: Path, tmp_path: Path) -> None:
    handlers = tmp_path / "handlers"
    _handler(
        handlers,
        "leaky",
        "install",
        'echo "Authorization: Bearer leaked-auth"\n'
        'echo "https://alice:uri-pass@example.test/x"\n'
        'dotf_result_failed "API_KEY=$SERVICE_TOKEN cookie=session-secret" 9\n',
    )
    plan = tmp_path / "plan.json"
    write_test_plan(plan, handlers, [("install", "leaky")])
    secret = "actual-environment-secret-987"
    result = _run(tmp_home, plan, handlers, "--json", extra_env={"SERVICE_TOKEN": secret})
    assert result.returncode != 0
    machine = json.loads(result.stdout)
    summary = _latest(tmp_home)
    journal_path, _ = _journal(tmp_home, summary)
    surfaces = [
        result.stdout,
        result.stderr,
        journal_path.read_text(encoding="utf-8"),
        (_state(tmp_home) / "last-run.json").read_text(encoding="utf-8"),
        json.dumps(machine),
    ]
    for rendered in surfaces:
        for leaked in ("leaked-auth", "alice", "uri-pass", "session-secret", secret):
            assert leaked not in rendered
    assert "[REDACTED]" in "\n".join(surfaces)
    assert set(machine) <= execution_state.SUMMARY_KEYS | {"summary"}
    assert all(set(item) == execution_state.ACTION_KEYS for item in machine["actions"])


def test_sigterm_preserves_completed_marks_current_interrupted_and_updates_latest(tmp_home: Path, tmp_path: Path) -> None:
    handlers = tmp_path / "handlers"
    _handler(handlers, "first", "install", 'dotf_result_changed "done"\n')
    _handler(handlers, "slow", "install", 'echo started >"$HOME/slow.started"\nsleep 30\ndotf_result_changed "late"\n')
    plan = tmp_path / "plan.json"
    write_test_plan(plan, handlers, [("install", "first"), ("install", "slow")])
    process = subprocess.Popen(
        ["bash", str(RUN_PLAN), "--yes", "--plan-file", str(plan)],
        cwd=str(ROOT), env=_env(tmp_home, plan, handlers),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
    )
    runs = _state(tmp_home) / "runs"
    deadline = time.time() + 10
    running_journal: Path | None = None
    while time.time() < deadline:
        candidates = list(runs.glob("*.json")) if runs.exists() else []
        if candidates and (tmp_home / "slow.started").exists():
            current = json.loads(candidates[0].read_text(encoding="utf-8"))
            if current["current_action"] and current["current_action"]["module"] == "slow":
                running_journal = candidates[0]
                break
        time.sleep(0.05)
    assert running_journal is not None
    os.killpg(process.pid, signal.SIGTERM)
    process.communicate(timeout=10)
    assert process.returncode != 0
    summary = _latest(tmp_home)
    _, journal = _journal(tmp_home, summary)
    assert summary["run_id"] == journal["run_id"]
    assert journal["status"] == "interrupted" and journal["complete"] is True
    assert [item["status"] for item in journal["actions"]] == ["completed", "interrupted"]


def test_concurrent_runs_use_unique_journals_and_unmixed_atomic_latest(tmp_home: Path, tmp_path: Path) -> None:
    processes: list[subprocess.Popen[str]] = []
    for number in (1, 2):
        root = tmp_path / f"run-{number}"
        handlers = root / "handlers"
        _handler(handlers, f"demo{number}", "install", f'sleep 0.{number}\ndotf_result_changed "ok-{number}"\n')
        plan = root / "plan.json"
        plan.parent.mkdir(parents=True, exist_ok=True)
        write_test_plan(plan, handlers, [("install", f"demo{number}")])
        processes.append(subprocess.Popen(
            ["bash", str(RUN_PLAN), "--yes", "--plan-file", str(plan)],
            cwd=str(ROOT), env=_env(tmp_home, plan, handlers),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        ))
    for process in processes:
        process.communicate(timeout=15)
        assert process.returncode == 0
    journals = list((_state(tmp_home) / "runs").glob("*.json"))
    assert len(journals) == 2 and len({path.name for path in journals}) == 2
    documents = [json.loads(path.read_text(encoding="utf-8")) for path in journals]
    assert {doc["actions"][0]["module"] for doc in documents} == {"demo1", "demo2"}
    assert all(doc["complete"] and doc["status"] == "completed" for doc in documents)
    latest = _latest(tmp_home)
    latest_path, latest_journal = _journal(tmp_home, latest)
    assert latest["run_id"] == latest_journal["run_id"]
    assert latest["journal_hash"] == hashlib.sha256(latest_path.read_bytes()).hexdigest()


def test_retry_success_replans_only_failed_candidate(tmp_home: Path, tmp_path: Path) -> None:
    handlers = tmp_path / "handlers"
    handler = _handler(handlers, "retryable", "install", 'dotf_result_failed "first" 3\n')
    plan = tmp_path / "plan.json"
    write_test_plan(plan, handlers, [("install", "retryable")])
    first = _run(tmp_home, plan, handlers)
    assert first.returncode != 0
    handler.write_text('#!/usr/bin/env bash\ndotf_result_changed "retried"\n', encoding="utf-8")
    handler.chmod(0o700)
    load_log = tmp_path / "load.log"
    retry = _dotf_retry(tmp_home, plan, handlers, load_log=load_log)
    assert retry.returncode == 0, retry.stdout + retry.stderr
    assert "将重试 1 个失败动作" in retry.stdout
    loaded = load_log.read_text(encoding="utf-8")
    assert loaded.count("\n") == 1 and "retryable\tinstall" in loaded
    assert _latest(tmp_home)["status"] == "completed"


def _rewrite_complete_state(home: Path, mutate) -> None:
    summary = _latest(home)
    journal_path, journal = _journal(home, summary)
    mutate(journal)
    journal_raw = execution_state._json_bytes(journal)
    journal_path.write_bytes(journal_raw)
    journal_path.chmod(0o600)
    forged = execution_state._summary_from_journal(journal, journal_raw)
    latest = _state(home) / "last-run.json"
    latest.write_bytes(execution_state._json_bytes(forged))
    latest.chmod(0o600)


def test_retry_rejects_forged_undeclared_action_before_handler(tmp_home: Path, tmp_path: Path) -> None:
    handlers = tmp_path / "handlers"
    _handler(handlers, "known", "install", 'dotf_result_failed "first" 3\n')
    plan = tmp_path / "plan.json"
    write_test_plan(plan, handlers, [("install", "known")])
    assert _run(tmp_home, plan, handlers).returncode != 0
    _rewrite_complete_state(tmp_home, lambda journal: journal["actions"][0].update(module="forged-module"))
    load_log = tmp_path / "load.log"
    retry = _dotf_retry(tmp_home, plan, handlers, load_log=load_log)
    assert retry.returncode != 0
    assert "未知模块" in (retry.stdout + retry.stderr)
    assert not load_log.exists()


def test_retry_rejects_recursive_dependency_drift_before_handler(tmp_home: Path, tmp_path: Path) -> None:
    handlers = tmp_path / "handlers"
    _handler(handlers, "base", "install", 'dotf_result_changed "base"\n')
    _handler(handlers, "child", "install", 'dotf_result_failed "child" 4\n')
    plan = tmp_path / "plan.json"
    registry, _ = write_test_plan(
        plan, handlers, [("install", "base"), ("install", "child")],
        depends_on={"child": ["base"]},
    )
    assert _run(tmp_home, plan, handlers).returncode != 0
    text = registry.read_text(encoding="utf-8")
    registry.write_text(text.replace('"depends_on": ["base"]', '"depends_on": []'), encoding="utf-8")
    load_log = tmp_path / "retry-load.log"
    retry = _dotf_retry(tmp_home, plan, handlers, load_log=load_log)
    assert retry.returncode != 0
    assert "依赖已漂移" in (retry.stdout + retry.stderr)
    assert not load_log.exists()


def test_retry_rejects_os_mismatch_in_complete_report_before_handler(tmp_home: Path, tmp_path: Path) -> None:
    import modules

    handlers = tmp_path / "handlers"
    _handler(handlers, "known", "install", 'dotf_result_failed "first" 3\n')
    plan = tmp_path / "plan.json"
    write_test_plan(plan, handlers, [("install", "known")])
    assert _run(tmp_home, plan, handlers).returncode != 0
    other = "darwin" if modules.detect_os() != "darwin" else "ubuntu"
    _rewrite_complete_state(tmp_home, lambda journal: journal.update(os=other))
    load_log = tmp_path / "os-load.log"
    retry = _dotf_retry(tmp_home, plan, handlers, load_log=load_log)
    assert retry.returncode != 0
    assert "与当前 OS" in (retry.stdout + retry.stderr)
    assert not load_log.exists()


def test_retry_rejects_incomplete_and_no_failed_reports(tmp_home: Path, tmp_path: Path) -> None:
    handlers = tmp_path / "handlers"
    _handler(handlers, "ok", "install", 'dotf_result_changed "ok"\n')
    plan = tmp_path / "plan.json"
    write_test_plan(plan, handlers, [("install", "ok")])
    assert _run(tmp_home, plan, handlers).returncode == 0
    no_failed = _dotf_retry(tmp_home, plan, handlers)
    assert no_failed.returncode != 0
    assert "没有 failed" in (no_failed.stdout + no_failed.stderr)

    latest = _state(tmp_home) / "last-run.json"
    value = json.loads(latest.read_text(encoding="utf-8"))
    value["complete"] = False
    latest.write_text(json.dumps(value), encoding="utf-8")
    latest.chmod(0o600)
    incomplete = _dotf_retry(tmp_home, plan, handlers)
    assert incomplete.returncode != 0
    assert "未完整" in (incomplete.stdout + incomplete.stderr)
