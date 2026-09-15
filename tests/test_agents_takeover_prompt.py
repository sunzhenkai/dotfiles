"""Takeover confirm uses the controlling TTY, not captured handler stdout."""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "agents"))

from sync import decide_takeover  # noqa: E402


def test_decide_takeover_non_tty_is_skip(monkeypatch) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert decide_takeover(Path("/tmp")) == "skip"


def test_decide_takeover_env_backup_does_not_prompt(monkeypatch) -> None:
    monkeypatch.setenv("DOTF_TAKEOVER", "backup")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    def fail_tty():
        raise AssertionError("explicit backup must not prompt")

    monkeypatch.setattr("sync._interactive_tty", fail_tty)
    assert decide_takeover(Path("/tmp")) == "backup"


def test_decide_takeover_yes_returns_backup(monkeypatch) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    class _TtyOut(io.StringIO):
        frozen = ""

        def close(self) -> None:
            type(self).frozen = self.getvalue()
            super().close()

    fake_in = io.StringIO("y\n")
    fake_out = _TtyOut()
    monkeypatch.setattr("sync._interactive_tty", lambda: (fake_in, fake_out))
    monkeypatch.setattr(
        "sync._takeover_candidates",
        lambda root, on_conflict: [("skills", "demo")],
    )
    assert decide_takeover(Path("/tmp")) == "backup"
    assert "Takeover with backup?" in _TtyOut.frozen
    assert "demo" in _TtyOut.frozen


def test_decide_takeover_no_returns_skip(monkeypatch) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    fake_in = io.StringIO("n\n")
    fake_out = io.StringIO()
    monkeypatch.setattr("sync._interactive_tty", lambda: (fake_in, fake_out))
    monkeypatch.setattr(
        "sync._takeover_candidates",
        lambda root, on_conflict: [("skills", "demo")],
    )
    assert decide_takeover(Path("/tmp")) == "skip"


def test_decide_takeover_cli_prints_skip() -> None:
    env = os.environ.copy()
    env.pop("DOTF_TAKEOVER", None)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "src" / "agents" / "sync.py"),
            "--decide-takeover",
            "--root",
            str(ROOT),
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "skip"
