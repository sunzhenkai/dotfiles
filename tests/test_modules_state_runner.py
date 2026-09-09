"""Integration: runner hook persists module fact in isolated HOME."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotf_core import modules_state as ms  # noqa: E402
from plan_test_helpers import write_test_plan  # noqa: E402

RUN_PLAN = ROOT / "scripts" / "run_plan.sh"

# Tab-separated RESULT line per the runner contract.
_TAB = "\\t"
_RESULT_OK = "printf 'RESULT\\tchanged\\t%s\\t%s\\t0\\t0\\tok\\n'"
_RESULT_FAIL = "printf 'RESULT\\tfailed\\t%s\\t%s\\t0\\t1\\tnope\\n'"


def _handler(root: Path, module: str, action: str, body: str) -> None:
    path = root / module / f"{action}.sh"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + body + "\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


def _run_plan(plan: Path, tmp_home: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["XDG_CONFIG_HOME"] = str(tmp_home / ".config")
    env["XDG_STATE_HOME"] = str(tmp_home / ".local" / "state")
    env["XDG_CACHE_HOME"] = str(tmp_home / ".cache")
    env["DOTF_REGISTRY_PATH"] = str(plan.parent / "modules.yaml")
    env["DOTF_PROFILES_PATH"] = str(plan.parent / "profiles.yaml")
    env["DOTF_HANDLERS_DIR"] = str(plan.parent / "handlers")
    for sub in (".config", ".local/state", ".cache"):
        (tmp_home / sub).mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        ["bash", str(RUN_PLAN), "--yes", "--plan-file", str(plan)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
        check=False,
    )


def test_install_changed_writes_state(tmp_path):
    home = tmp_path / "home"
    handlers = tmp_path / "handlers"
    _handler(handlers, "demo", "install", _RESULT_OK % ("demo", "install"))
    plan = tmp_path / "plan.json"
    write_test_plan(plan, handlers, [("install", "demo")])
    proc = _run_plan(plan, home)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    records = ms.load_state(state_home=home / ".local" / "state")
    assert "demo" in records
    assert records["demo"].installed is True
    assert records["demo"].configured is False


def test_config_changed_writes_state_and_does_not_imply_install(tmp_path):
    home = tmp_path / "home"
    handlers = tmp_path / "handlers"
    _handler(handlers, "demo", "config", _RESULT_OK % ("demo", "config"))
    plan = tmp_path / "plan.json"
    write_test_plan(plan, handlers, [("config", "demo")])
    proc = _run_plan(plan, home)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    records = ms.load_state(state_home=home / ".local" / "state")
    assert "demo" in records
    assert records["demo"].installed is False
    assert records["demo"].configured is True


def test_deconfig_strips_config_keeps_install(tmp_path):
    home = tmp_path / "home"
    handlers = tmp_path / "handlers"
    _handler(handlers, "demo", "install", _RESULT_OK % ("demo", "install"))
    _handler(handlers, "demo", "config", _RESULT_OK % ("demo", "config"))
    _handler(handlers, "demo", "deconfig", _RESULT_OK % ("demo", "deconfig"))
    plan = tmp_path / "plan.json"
    write_test_plan(plan, handlers, [("install", "demo"), ("config", "demo"), ("deconfig", "demo")])
    proc = _run_plan(plan, home)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    records = ms.load_state(state_home=home / ".local" / "state")
    r = records["demo"]
    assert r.installed is True
    assert r.configured is False


def test_uninstall_clears_all(tmp_path):
    home = tmp_path / "home"
    handlers = tmp_path / "handlers"
    _handler(handlers, "demo", "install", _RESULT_OK % ("demo", "install"))
    _handler(handlers, "demo", "uninstall", _RESULT_OK % ("demo", "uninstall"))
    plan = tmp_path / "plan.json"
    write_test_plan(plan, handlers, [("install", "demo"), ("uninstall", "demo")])
    proc = _run_plan(plan, home)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    records = ms.load_state(state_home=home / ".local" / "state")
    assert "demo" not in records


def test_failed_action_does_not_write_state(tmp_path):
    home = tmp_path / "home"
    handlers = tmp_path / "handlers"
    _handler(handlers, "demo", "install", _RESULT_FAIL % ("demo", "install"))
    plan = tmp_path / "plan.json"
    write_test_plan(plan, handlers, [("install", "demo")])
    proc = _run_plan(plan, home)
    assert proc.returncode != 0
    records = ms.load_state(state_home=home / ".local" / "state")
    assert "demo" not in records
