"""Tests for unified XDG config/state path resolution and apply_state_hook."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from dotf_core import execution_state, overlays, paths  # noqa: E402
from dotf_core.schemas import MANIFEST_SCHEMA_VERSION, ManagedItem, ManagedManifest  # noqa: E402
from dotf_tui import apply_state_hook  # noqa: E402


def test_xdg_config_home_and_dotf_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    fake_home = tmp_path / "home"
    assert paths.xdg_config_home(fake_home) == fake_home / ".config"
    assert paths.dotf_config_dir(fake_home) == fake_home / ".config" / "dotf"

    custom = tmp_path / "custom-cfg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(custom))
    assert paths.xdg_config_home(fake_home) == custom
    assert paths.dotf_config_dir(fake_home) == custom / "dotf"

    monkeypatch.setenv("XDG_CONFIG_HOME", "relative/cfg")
    with pytest.raises(ValueError, match="absolute path"):
        paths.xdg_config_home(fake_home)
    with pytest.raises(overlays.OverlayError, match="absolute path"):
        overlays.xdg_config_home(fake_home)


def test_xdg_state_home_and_dotf_state_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    fake_home = tmp_path / "home"
    assert paths.xdg_state_home(fake_home) == fake_home / ".local" / "state"
    assert paths.dotf_state_dir(fake_home) == fake_home / ".local" / "state" / "dotf"

    env_state = tmp_path / "env-state"
    monkeypatch.setenv("XDG_STATE_HOME", str(env_state))
    assert paths.xdg_state_home(fake_home) == env_state
    assert paths.dotf_state_dir(fake_home) == env_state / "dotf"

    explicit_state = tmp_path / "explicit-state"
    assert paths.xdg_state_home(fake_home, explicit_state) == explicit_state
    assert paths.dotf_state_dir(fake_home, explicit_state) == explicit_state / "dotf"

    monkeypatch.setenv("XDG_STATE_HOME", "relative/state")
    with pytest.raises(ValueError, match="absolute path"):
        paths.xdg_state_home(fake_home)
    with pytest.raises(execution_state.StateError, match="absolute path"):
        execution_state._state_dir()


def test_apply_state_hook_compute_manifest_managed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_home = tmp_path / "state"
    monkeypatch.setenv("XDG_STATE_HOME", str(state_home))
    digest = "0" * 64
    manifest = ManagedManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        kind="managed-manifest",
        generated_at="2026-11-28T00:00:00Z",
        items=(
            ManagedItem(
                owner="config:demo",
                target=str(tmp_path / "home" / ".demo1"),
                source_identity="config/demo/1",
                expected_hash=digest,
                installed_hash=digest,
                strategy="copy",
                mode=0o600,
                run_id="run-1",
                sensitive=False,
            ),
            ManagedItem(
                owner="config:demo:extra",
                target=str(tmp_path / "home" / ".demo2"),
                source_identity="config/demo/2",
                expected_hash=digest,
                installed_hash=digest,
                strategy="copy",
                mode=0o600,
                run_id="run-1",
                sensitive=False,
            ),
            ManagedItem(
                owner="config:other",
                target=str(tmp_path / "home" / ".other"),
                source_identity="config/other/1",
                expected_hash=digest,
                installed_hash=digest,
                strategy="copy",
                mode=0o600,
                run_id="run-1",
                sensitive=False,
            ),
        ),
    )
    manifest_file = state_home / "dotf" / "config-manifest.json"
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text(json.dumps(manifest.to_dict()), encoding="utf-8")

    assert apply_state_hook._compute_manifest_managed("config", "demo") == 2
    assert apply_state_hook._compute_manifest_managed("install", "demo") is None
