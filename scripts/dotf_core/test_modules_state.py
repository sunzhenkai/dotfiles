"""State layer unit tests for the TUI manager."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from dotf_core import modules_state as ms  # noqa: E402


@pytest.fixture
def fake_state_home(tmp_path, monkeypatch):
    home = tmp_path
    state = home / ".local" / "state"
    monkeypatch.setenv("XDG_STATE_HOME", str(state))
    return home, state


def test_state_path_default(fake_state_home):
    home, state = fake_state_home
    assert ms.state_file_path(home) == state / "dotf" / "modules-state.yaml"


def test_load_missing_returns_empty(fake_state_home):
    home, _ = fake_state_home
    assert ms.load_state(home) == {}


def test_load_unknown_schema_version_returns_empty(fake_state_home, tmp_path):
    home, _ = fake_state_home
    state_file = ms.state_file_path(home)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text("schema_version: 99\nmodules: {}\n", encoding="utf-8")
    assert ms.load_state(home) == {}


def test_install_changed_writes_field(fake_state_home):
    home, _ = fake_state_home
    assert ms.apply_result("grepom", "install", "changed", home=home, version="1.2.3") is True
    records = ms.load_state(home)
    assert "grepom" in records
    r = records["grepom"]
    assert r.installed is True
    assert r.version == "1.2.3"
    assert r.last_install_at is not None


def test_install_unchanged_writes_field(fake_state_home):
    home, _ = fake_state_home
    assert ms.apply_result("grepom", "install", "unchanged", home=home) is True
    r = ms.load_state(home)["grepom"]
    assert r.installed is True
    assert r.version is None


def test_install_failed_does_not_write(fake_state_home):
    home, _ = fake_state_home
    assert ms.apply_result("grepom", "install", "failed", home=home) is True
    assert ms.load_state(home) == {}


def test_config_changed_writes_field(fake_state_home):
    home, _ = fake_state_home
    assert ms.apply_result("nvim", "config", "changed", home=home, manifest_managed=4) is True
    r = ms.load_state(home)["nvim"]
    assert r.configured is True
    assert r.manifest_managed == 4
    assert r.last_config_at is not None
    assert r.installed is False  # config alone does not imply install


def test_deconfig_strips_only_config(fake_state_home):
    home, _ = fake_state_home
    ms.apply_result("nvim", "install", "changed", home=home)
    ms.apply_result("nvim", "config", "changed", home=home, manifest_managed=2)
    ms.apply_result("nvim", "deconfig", "changed", home=home)
    r = ms.load_state(home)["nvim"]
    assert r.installed is True
    assert r.configured is False


def test_uninstall_clears_all(fake_state_home):
    home, _ = fake_state_home
    ms.apply_result("grepom", "install", "changed", home=home, version="1.2.3")
    ms.apply_result("grepom", "config", "changed", home=home, manifest_managed=0)
    ms.apply_result("grepom", "uninstall", "changed", home=home)
    assert ms.load_state(home) == {}


def test_uninstall_failed_does_not_clear(fake_state_home):
    home, _ = fake_state_home
    ms.apply_result("grepom", "install", "changed", home=home)
    ms.apply_result("grepom", "uninstall", "failed", home=home)
    assert "grepom" in ms.load_state(home)


def test_repeated_install_idempotent_no_field_drift(fake_state_home):
    home, _ = fake_state_home
    ms.apply_result("grepom", "install", "changed", home=home, version="1.2.3", path="/usr/local/bin/grepom")
    ms.apply_result("grepom", "install", "unchanged", home=home)
    r = ms.load_state(home)["grepom"]
    assert r.installed is True
    assert r.version == "1.2.3"
    assert r.path == "/usr/local/bin/grepom"


def test_atomic_write_failure_does_not_raise(fake_state_home, monkeypatch):
    home, state = fake_state_home

    def _explode(*_args, **_kwargs):
        raise OSError("simulated write failure")

    monkeypatch.setattr(ms, "_atomic_write_yaml", _explode)
    assert ms.apply_result("grepom", "install", "changed", home=home) is False


def test_load_malformed_yaml_returns_empty(fake_state_home):
    home, _ = fake_state_home
    state_file = ms.state_file_path(home)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text("schema_version: 1\nmodules: [unbalanced\n", encoding="utf-8")
    assert ms.load_state(home) == {}


def test_load_missing_module_fields(fake_state_home):
    home, _ = fake_state_home
    state_file = ms.state_file_path(home)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        "schema_version: 1\nmodules:\n  foo:\n    install:\n      last_at: 2026-09-07T12:00:00Z\n",
        encoding="utf-8",
    )
    records = ms.load_state(home)
    r = records["foo"]
    assert r.installed is True
    assert r.version is None
    assert r.path is None
    assert r.configured is False


def test_doctor_noop(fake_state_home):
    home, _ = fake_state_home
    assert ms.apply_result("grepom", "doctor", "changed", home=home) is True
    assert ms.load_state(home) == {}


def test_apply_unknown_action_noop(fake_state_home):
    home, _ = fake_state_home
    assert ms.apply_result("grepom", "frobnicate", "changed", home=home) is True
    assert ms.load_state(home) == {}


def test_atomic_replace_preserves_unrelated_fields(fake_state_home):
    """Re-running state writes must not delete unrelated modules."""
    home, _ = fake_state_home
    ms.apply_result("a", "install", "changed", home=home)
    ms.apply_result("b", "install", "changed", home=home)
    ms.apply_result("a", "config", "changed", home=home, manifest_managed=1)
    records = ms.load_state(home)
    assert "a" in records and "b" in records
    assert records["b"].installed is True
    assert records["a"].configured is True
