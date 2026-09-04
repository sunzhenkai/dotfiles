"""Versioned plan protocol, fail-closed runner, dependency scheduling, and OS contract."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

from plan_test_helpers import plan_env, write_test_plan

ROOT = Path(__file__).resolve().parent.parent
RUN_PLAN = ROOT / "scripts" / "run_plan.sh"
PLANNER = ROOT / "scripts" / "planner.py"


def _reseal(document: dict) -> None:
    document.pop("plan_digest", None)
    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    document["plan_digest"] = hashlib.sha256(payload).hexdigest()


def _handler(root: Path, module: str, action: str, body: str) -> None:
    path = root / module / f"{action}.sh"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run(
    plan: Path,
    handlers: Path,
    home: Path,
    *args: str,
    load_log: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env.update(plan_env(plan, handlers))
    if load_log is not None:
        env["DOTF_LOAD_LOG"] = str(load_log)
    return subprocess.run(
        ["bash", str(RUN_PLAN), *args, "--plan-file", str(plan)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
        check=False,
    )


def _valid_fixture(tmp_path: Path) -> tuple[Path, Path]:
    handlers = tmp_path / "handlers"
    _handler(handlers, "demo", "install", 'dotf_result_changed "ok"\n')
    plan = tmp_path / "plan.json"
    write_test_plan(plan, handlers, [("install", "demo")])
    return plan, handlers


def test_planner_emits_versioned_complete_deterministic_plan() -> None:
    command = [
        "python3", str(PLANNER), "plan", "--actions", "install,config",
        "--profile", "minimal", "--format", "machine",
    ]
    first = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, check=True)
    second = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, check=True)
    assert first.stdout == second.stdout
    document = json.loads(first.stdout)
    assert document["header"] == "DOTF_EXECUTION_PLAN"
    assert document["version"] == 1
    assert document["success_marker"] == "DOTF_PLAN_COMPLETE_V1"
    assert set(("requested_os", "detected_os", "planned_os", "profile")) <= set(document)
    assert document["registry_digest"] and document["handler_digest"] and document["plan_digest"]
    assert [a["index"] for a in document["actions"]] == list(range(1, len(document["actions"]) + 1))
    assert len({(a["module"], a["action"]) for a in document["actions"]}) == len(document["actions"])
    for module in document["modules"]:
        assert set(module) == {"name", "registry_order", "depends_on", "capabilities", "planned_actions"}


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.pop("header"),
        lambda d: d.__setitem__("header", "UNKNOWN"),
        lambda d: d.pop("success_marker"),
        lambda d: d.__setitem__("success_marker", "UNKNOWN"),
        lambda d: d.__setitem__("version", 99),
        lambda d: d.pop("planned_os"),
        lambda d: d["actions"][0].__setitem__("index", 2),
        lambda d: d["actions"][0].__setitem__("action", "destroy"),
        lambda d: d["actions"].append(dict(d["actions"][0])),
        lambda d: d["actions"][0].__setitem__("module", "ghost"),
        lambda d: d["modules"].append(dict(d["modules"][0])),
        lambda d: d["modules"][0]["capabilities"].append("destroy"),
        lambda d: d["modules"][0]["capabilities"].append("install"),
        lambda d: d["modules"][0].__setitem__("capabilities", []),
    ],
)
def test_malformed_plan_rejected_before_handler_load(
    mutate, tmp_home: Path, tmp_path: Path
) -> None:
    plan, handlers = _valid_fixture(tmp_path)
    document = json.loads(plan.read_text(encoding="utf-8"))
    mutate(document)
    _reseal(document)
    plan.write_text(json.dumps(document), encoding="utf-8")
    load_log = tmp_path / "load.log"
    result = _run(plan, handlers, tmp_home, "--yes", load_log=load_log)
    assert result.returncode != 0
    assert not load_log.exists() or not load_log.read_text(encoding="utf-8")


def test_duplicate_header_and_truncated_plan_rejected_before_load(tmp_home: Path, tmp_path: Path) -> None:
    plan, handlers = _valid_fixture(tmp_path)
    original = plan.read_text(encoding="utf-8")
    duplicate = original.replace(
        '{\n  "header": "DOTF_EXECUTION_PLAN",',
        '{\n  "header": "DOTF_EXECUTION_PLAN",\n  "header": "DOTF_EXECUTION_PLAN",',
        1,
    )
    load_log = tmp_path / "load.log"
    plan.write_text(duplicate, encoding="utf-8")
    rejected = _run(plan, handlers, tmp_home, "--yes", load_log=load_log)
    assert rejected.returncode != 0
    assert not load_log.exists()
    duplicate_marker = original.replace(
        '  "success_marker": "DOTF_PLAN_COMPLETE_V1",',
        '  "success_marker": "DOTF_PLAN_COMPLETE_V1",\n  "success_marker": "DOTF_PLAN_COMPLETE_V1",',
        1,
    )
    plan.write_text(duplicate_marker, encoding="utf-8")
    rejected = _run(plan, handlers, tmp_home, "--yes", load_log=load_log)
    assert rejected.returncode != 0
    assert not load_log.exists()
    plan.write_text(original[: len(original) // 2], encoding="utf-8")
    rejected = _run(plan, handlers, tmp_home, "--yes", load_log=load_log)
    assert rejected.returncode != 0
    assert not load_log.exists()


def test_registry_drift_rejected_before_handler_load(tmp_home: Path, tmp_path: Path) -> None:
    plan, handlers = _valid_fixture(tmp_path)
    registry = plan.parent / "modules.yaml"
    registry.write_text(registry.read_text(encoding="utf-8") + "# drift\n", encoding="utf-8")
    # Semantic comments do not drift; mutate actual metadata instead.
    registry.write_text(registry.read_text(encoding="utf-8").replace('"doctor": true', '"doctor": false'), encoding="utf-8")
    load_log = tmp_path / "load.log"
    result = _run(plan, handlers, tmp_home, "--yes", load_log=load_log)
    assert result.returncode != 0
    assert "漂移" in result.stderr or "校验失败" in result.stderr
    assert not load_log.exists()


def test_planner_failure_status_preserved_through_dotf(tmp_home: Path, tmp_path: Path) -> None:
    handlers = tmp_path / "handlers"
    handlers.mkdir()
    plan = tmp_path / "seed.json"
    registry, profiles = write_test_plan(plan, handlers, [("install", "missing")])
    plan.unlink()
    env = os.environ.copy()
    env.update({
        "HOME": str(tmp_home), "DOTF_HANDLERS_DIR": str(handlers),
        "DOTF_REGISTRY_PATH": str(registry), "DOTF_PROFILES_PATH": str(profiles),
    })
    direct = subprocess.run(
        ["python3", str(PLANNER), "plan", "--actions", "install", "--modules", "missing", "--format", "machine"],
        cwd=str(ROOT), env=env, capture_output=True, text=True, check=False,
    )
    cli = subprocess.run(
        [str(ROOT / "bin" / "dotf"), "missing", "-i", "--dry-run"],
        cwd=str(ROOT), env=env, capture_output=True, text=True, check=False,
    )
    assert direct.returncode != 0 and direct.stdout == ""
    assert cli.returncode == direct.returncode
    assert "缺少处理器" in (cli.stdout + cli.stderr)


def test_default_fail_fast_blocks_lifecycle_and_recursive_dependents(tmp_home: Path, tmp_path: Path) -> None:
    handlers = tmp_path / "handlers"
    _handler(handlers, "base", "install", 'dotf_result_failed "boom" 7\n')
    _handler(handlers, "base", "config", 'dotf_result_changed "must-not-run"\n')
    _handler(handlers, "base", "doctor", 'dotf_result_changed "must-not-run"\n')
    for name in ("child", "grandchild", "independent"):
        _handler(handlers, name, "install", f'dotf_result_changed "{name}"\n')
        _handler(handlers, name, "doctor", f'dotf_result_changed "{name}-doctor"\n')
    plan = tmp_path / "plan.json"
    actions = [
        ("install", "base"), ("config", "base"), ("doctor", "base"),
        ("install", "child"), ("doctor", "child"),
        ("install", "grandchild"), ("doctor", "grandchild"),
        ("install", "independent"), ("doctor", "independent"),
    ]
    write_test_plan(
        plan, handlers, actions,
        depends_on={"child": ["base"], "grandchild": ["child"]},
    )
    load_log = tmp_path / "load.log"
    result = _run(plan, handlers, tmp_home, "--yes", load_log=load_log)
    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "RESULT\tblocked\tbase\tconfig" in combined
    assert "RESULT\tblocked\tbase\tdoctor" in combined
    assert "RESULT\tblocked\tchild\tinstall" in combined
    assert "RESULT\tblocked\tgrandchild\tinstall" in combined
    assert "RESULT\tnot-run\tindependent\tinstall" in combined
    loaded = load_log.read_text(encoding="utf-8")
    assert loaded.count("\n") == 1 and "base\tinstall" in loaded


def test_runner_uses_initial_validated_dependency_metadata(tmp_home: Path) -> None:
    runner = (ROOT / "scripts" / "run_plan.sh").read_text(encoding="utf-8")
    assert "DEPENDENCIES) DEPENDENCIES" in runner
    assert 'plan_protocol.py" is-blocked' not in runner
    assert "dependency-failed" in runner

def test_continue_on_error_runs_only_independent_actions(tmp_home: Path, tmp_path: Path) -> None:
    handlers = tmp_path / "handlers"
    _handler(handlers, "base", "install", 'dotf_result_failed "boom" 4\n')
    for name in ("child", "grandchild", "independent"):
        _handler(handlers, name, "install", f'dotf_result_changed "{name}"\n')
    plan = tmp_path / "plan.json"
    write_test_plan(
        plan, handlers,
        [("install", "base"), ("install", "child"), ("install", "grandchild"), ("install", "independent")],
        depends_on={"child": ["base"], "grandchild": ["child"]},
    )
    load_log = tmp_path / "load.log"
    result = _run(plan, handlers, tmp_home, "--yes", "--continue-on-error", load_log=load_log)
    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "RESULT\tblocked\tchild\tinstall" in combined
    assert "RESULT\tblocked\tgrandchild\tinstall" in combined
    assert "RESULT\tchanged\tindependent\tinstall" in combined
    loaded = load_log.read_text(encoding="utf-8")
    assert "base\tinstall" in loaded and "independent\tinstall" in loaded
    assert "child\tinstall" not in loaded and "grandchild\tinstall" not in loaded


def test_lifecycle_order_rejected_when_reordered(tmp_home: Path, tmp_path: Path) -> None:
    handlers = tmp_path / "handlers"
    for action in ("install", "config", "doctor"):
        _handler(handlers, "demo", action, 'dotf_result_changed "ok"\n')
    plan = tmp_path / "plan.json"
    write_test_plan(plan, handlers, [("install", "demo"), ("config", "demo"), ("doctor", "demo")])
    document = json.loads(plan.read_text(encoding="utf-8"))
    document["actions"][0], document["actions"][1] = document["actions"][1], document["actions"][0]
    document["actions"][0]["index"] = 1
    document["actions"][1]["index"] = 2
    _reseal(document)
    plan.write_text(json.dumps(document), encoding="utf-8")
    result = _run(plan, handlers, tmp_home, "--yes")
    assert result.returncode != 0
    assert "顺序" in result.stderr


def test_cross_os_only_dry_run_and_planned_os_propagates_immutably(tmp_home: Path, tmp_path: Path) -> None:
    import modules

    detected = modules.detect_os()
    other = "darwin" if detected != "darwin" else "ubuntu"
    handlers = tmp_path / "handlers"
    _handler(handlers, "demo", "install", 'declare -p DOTF_OS\necho "HANDLER_OS=$DOTF_OS"\ndotf_result_changed "ok"\n')
    cross_plan = tmp_path / "cross.json"
    write_test_plan(cross_plan, handlers, [("install", "demo")], requested_os=other)
    load_log = tmp_path / "load.log"
    preview = _run(cross_plan, handlers, tmp_home, "--dry-run", load_log=load_log)
    assert preview.returncode == 0
    assert f"OS={other}" in preview.stdout
    assert not load_log.exists()
    rejected = _run(cross_plan, handlers, tmp_home, "--yes", load_log=load_log)
    assert rejected.returncode != 0
    assert "跨 OS" in rejected.stderr or "不一致" in rejected.stderr
    assert not load_log.exists()

    native_plan = tmp_path / "native.json"
    write_test_plan(native_plan, handlers, [("install", "demo")])
    native = _run(native_plan, handlers, tmp_home, "--yes")
    assert native.returncode == 0
    assert f"HANDLER_OS={detected}" in native.stdout
    assert "declare -r" in native.stdout or "readonly" in native.stdout


def test_help_documents_continue_on_error_and_cross_os_dry_run(tmp_home: Path) -> None:
    result = subprocess.run(
        [str(ROOT / "bin" / "dotf"), "--help"],
        cwd=str(ROOT), env={**os.environ, "HOME": str(tmp_home)},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert "--continue-on-error" in result.stdout
    assert "跨 OS" in result.stdout
