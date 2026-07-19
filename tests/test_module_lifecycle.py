"""P1 module-lifecycle：结果协议、runner、约定式处理器与幂等契约。"""

from __future__ import annotations

import os
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RUN_PLAN = ROOT / "scripts" / "run_plan.sh"


def _write_plan(path: Path, *actions: tuple[str, str]) -> None:
    lines = ["PLAN_OK", "OS\tlinux", "PROFILE\t"]
    for i, (action, module) in enumerate(actions, start=1):
        lines.append(f"ACTION\t{i}\t{action}\t{module}\texplicit")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_handler(handlers: Path, module: str, action: str, body: str) -> Path:
    d = handlers / module
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{action}.sh"
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _run_plan(
    plan: Path,
    *,
    home: Path,
    handlers: Path | None = None,
    load_log: Path | None = None,
    require_handlers: bool = False,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    if handlers is not None:
        env["DOTF_HANDLERS_DIR"] = str(handlers)
    if load_log is not None:
        env["DOTF_LOAD_LOG"] = str(load_log)
    if require_handlers:
        env["DOTF_REQUIRE_HANDLERS"] = "1"
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(RUN_PLAN), "--yes", "--plan-file", str(plan)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )


def test_result_protocol_changed(tmp_home: Path, tmp_path: Path) -> None:
    handlers = tmp_path / "handlers"
    _write_handler(
        handlers,
        "demo",
        "install",
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            dotf_result_changed "installed demo"
            """
        ),
    )
    plan = tmp_path / "plan.txt"
    _write_plan(plan, ("install", "demo"))
    r = _run_plan(plan, home=tmp_home, handlers=handlers)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "RESULT\tchanged\tdemo\tinstall" in r.stdout
    assert "changed=1" in r.stdout


def test_missing_handler_fails_when_required(tmp_home: Path, tmp_path: Path) -> None:
    handlers = tmp_path / "handlers"
    handlers.mkdir()
    plan = tmp_path / "plan.txt"
    _write_plan(plan, ("install", "missingmod"))
    r = _run_plan(plan, home=tmp_home, handlers=handlers, require_handlers=True)
    assert r.returncode != 0
    assert "RESULT\tfailed\tmissingmod\tinstall" in (r.stdout + r.stderr)
    assert "缺少处理器" in (r.stdout + r.stderr)


def test_undeclared_handler_reported_by_validate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """未声明处理器：注册表校验报告不一致。"""
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import modules as m

    reg = tmp_path / "modules.yaml"
    reg.write_text(
        textwrap.dedent(
            """\
            modules:
              - name: onlyinstall
                install: true
            """
        ),
        encoding="utf-8",
    )
    hdir = tmp_path / "handlers"
    _write_handler(hdir, "onlyinstall", "config", "#!/bin/bash\ntrue\n")
    monkeypatch.setattr(m, "REGISTRY_PATH", reg)
    errors = m.validate_registry(
        m.load_registry(reg),
        strict_handlers=True,
        handlers_dir=hdir,
    )
    assert any("未声明能力" in e and "config" in e for e in errors)


def test_declared_missing_handler_reported_by_validate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import modules as m

    reg = tmp_path / "modules.yaml"
    reg.write_text(
        textwrap.dedent(
            """\
            modules:
              - name: needinstall
                install: true
            """
        ),
        encoding="utf-8",
    )
    hdir = tmp_path / "handlers"
    hdir.mkdir()
    monkeypatch.setattr(m, "REGISTRY_PATH", reg)
    errors = m.validate_registry(
        m.load_registry(reg),
        strict_handlers=True,
        handlers_dir=hdir,
    )
    assert any("缺少处理器" in e and "needinstall" in e for e in errors)


def test_handler_failure_propagates(tmp_home: Path, tmp_path: Path) -> None:
    handlers = tmp_path / "handlers"
    _write_handler(
        handlers,
        "boom",
        "install",
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            dotf_result_failed "boom exploded" 3
            """
        ),
    )
    plan = tmp_path / "plan.txt"
    _write_plan(plan, ("install", "boom"), ("install", "never"))
    # 第二个不应被加载
    _write_handler(
        handlers,
        "never",
        "install",
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            dotf_result_changed "should not run"
            """
        ),
    )
    load_log = tmp_path / "load.log"
    r = _run_plan(plan, home=tmp_home, handlers=handlers, load_log=load_log)
    assert r.returncode != 0
    assert "RESULT\tfailed\tboom\tinstall" in (r.stdout + r.stderr)
    assert "failed=1" in r.stdout or "→ failed" in (r.stdout + r.stderr)
    # 失败传播：不应加载第二个处理器
    loaded = load_log.read_text(encoding="utf-8") if load_log.exists() else ""
    assert "boom\tinstall" in loaded
    assert "never\tinstall" not in loaded


def test_lazy_load_only_planned_handler(tmp_home: Path, tmp_path: Path) -> None:
    handlers = tmp_path / "handlers"
    for name in ("alpha", "beta", "gamma"):
        _write_handler(
            handlers,
            name,
            "install",
            textwrap.dedent(
                f"""\
                #!/usr/bin/env bash
                dotf_result_changed "ok {name}"
                """
            ),
        )
    plan = tmp_path / "plan.txt"
    _write_plan(plan, ("install", "beta"))
    load_log = tmp_path / "load.log"
    r = _run_plan(plan, home=tmp_home, handlers=handlers, load_log=load_log)
    assert r.returncode == 0, r.stdout + r.stderr
    loaded = load_log.read_text(encoding="utf-8").strip().splitlines()
    assert len(loaded) == 1
    assert loaded[0].startswith("beta\tinstall\t")


def test_idempotent_second_run_unchanged(tmp_home: Path, tmp_path: Path) -> None:
    """重复执行：目标已满足时返回 unchanged。"""
    handlers = tmp_path / "handlers"
    marker = tmp_home / ".demo_marker"
    _write_handler(
        handlers,
        "idem",
        "config",
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            MARKER="{marker}"
            if [ -f "$MARKER" ]; then
              dotf_result_unchanged "already configured"
              exit 0
            fi
            mkdir -p "$(dirname "$MARKER")"
            echo configured >"$MARKER"
            dotf_result_changed "wrote marker"
            """
        ),
    )
    plan = tmp_path / "plan.txt"
    _write_plan(plan, ("config", "idem"))

    first = _run_plan(plan, home=tmp_home, handlers=handlers)
    assert first.returncode == 0, first.stdout + first.stderr
    assert "RESULT\tchanged\tidem\tconfig" in first.stdout
    assert marker.is_file()

    second = _run_plan(plan, home=tmp_home, handlers=handlers)
    assert second.returncode == 0, second.stdout + second.stderr
    assert "RESULT\tunchanged\tidem\tconfig" in second.stdout
    assert "unchanged=1" in second.stdout


def test_dry_run_does_not_load_handlers(tmp_home: Path, tmp_path: Path) -> None:
    handlers = tmp_path / "handlers"
    _write_handler(
        handlers,
        "demo",
        "install",
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            echo SHOULD_NOT_RUN
            dotf_result_changed "nope"
            """
        ),
    )
    plan = tmp_path / "plan.txt"
    _write_plan(plan, ("install", "demo"))
    load_log = tmp_path / "load.log"
    env = os.environ.copy()
    env["HOME"] = str(tmp_home)
    env["DOTF_HANDLERS_DIR"] = str(handlers)
    env["DOTF_LOAD_LOG"] = str(load_log)
    r = subprocess.run(
        ["bash", str(RUN_PLAN), "--dry-run", "--plan-file", str(plan)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert r.returncode == 0
    assert "SHOULD_NOT_RUN" not in r.stdout
    assert not load_log.exists() or load_log.read_text(encoding="utf-8") == ""
