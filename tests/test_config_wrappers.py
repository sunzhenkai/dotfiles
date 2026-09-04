from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any

import modules
import pytest


COPY_MODULES = tuple(
    module
    for module in modules.load_registry()
    if modules.has_config(module) and modules.module_strategy(module) == "copy"
)
SPECIALIZED_MODULES = tuple(
    module
    for module in modules.load_registry()
    if modules.has_config(module) and modules.module_strategy(module) in {"merge", "render"}
)
SPECIALIZED_CONFIG_HANDLERS = frozenset({"codex", "opencode"})


def _expand_home(value: str, home: Path) -> Path:
    if value == "~":
        return home
    if value.startswith("~/"):
        return home / value[2:]
    path = Path(value)
    return path if path.is_absolute() else home / path


def _target_snapshot(target: Path) -> tuple[tuple[Any, ...], ...]:
    paths = [target]
    if target.is_dir():
        paths.extend(sorted(target.rglob("*")))
    snapshot: list[tuple[Any, ...]] = []
    for path in paths:
        item = path.lstat()
        relative = "." if path == target else str(path.relative_to(target))
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if stat.S_ISREG(item.st_mode) else None
        snapshot.append(
            (
                relative,
                stat.S_IFMT(item.st_mode),
                stat.S_IMODE(item.st_mode),
                item.st_ino,
                item.st_size,
                item.st_mtime_ns,
                digest,
            )
        )
    return tuple(snapshot)


def _run_config(repo_root: Path, module: dict[str, Any], home: Path, run_id: str):
    name = module["name"]
    state = home / ".local" / "state"
    config = home / ".config"
    cache = home / ".cache"
    for directory in (state, config, cache):
        directory.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        HOME=str(home),
        XDG_STATE_HOME=str(state),
        XDG_CONFIG_HOME=str(config),
        XDG_CACHE_HOME=str(cache),
        DOTFILES_ROOT=str(repo_root),
        DOTF_RUN_ID=run_id,
    )
    return subprocess.run(
        [
            "bash",
            "-c",
            'source "$1/scripts/lib/runner.sh"; runner_run_action config "$2"',
            "runner-config",
            str(repo_root),
            name,
        ],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_generic_config_uses_registry_fallback_without_wrapper(repo_root: Path) -> None:
    assert COPY_MODULES
    runner = (repo_root / "scripts" / "lib" / "runner.sh").read_text(encoding="utf-8")
    assert 'elif [ "$action" = "config" ]' in runner
    assert 'dotf_registry_config "$module"' in runner
    for module in (*COPY_MODULES, *SPECIALIZED_MODULES):
        wrapper = repo_root / "scripts" / "modules" / module["name"] / "config.sh"
        if module["name"] in SPECIALIZED_CONFIG_HANDLERS:
            assert wrapper.is_file()
        else:
            assert not wrapper.exists(), module["name"]
    assert modules.validate_registry(strict_handlers=True) == []


@pytest.mark.parametrize("module", COPY_MODULES, ids=lambda module: module["name"])
def test_generic_copy_fallback_creates_real_targets_and_second_run_is_unchanged(
    repo_root: Path,
    tmp_path: Path,
    module: dict[str, Any],
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    name = module["name"]

    first = _run_config(repo_root, module, home, f"strict-{name}-1")
    assert first.returncode == 0, first.stdout + first.stderr
    assert "RESULT\tchanged\t" in first.stdout, first.stdout + first.stderr

    target = _expand_home(module["config"]["target"], home)
    target_stat = target.lstat()
    source = repo_root / module["config"]["source"]
    if source.is_dir():
        assert stat.S_ISDIR(target_stat.st_mode), name
    else:
        assert stat.S_ISREG(target_stat.st_mode), name
    assert not stat.S_ISLNK(target_stat.st_mode), name
    for path in [target, *target.rglob("*")] if target.is_dir() else [target]:
        assert not path.is_symlink(), f"{name}: managed output is a symlink: {path}"
        path.relative_to(home)
    before = _target_snapshot(target)

    second = _run_config(repo_root, module, home, f"strict-{name}-2")
    assert second.returncode == 0, second.stdout + second.stderr
    assert "RESULT\tunchanged\t" in second.stdout, second.stdout + second.stderr
    assert _target_snapshot(target) == before, name


EXPECTED_COPY_MODULE_NAMES = {
    "git", "zsh", "starship", "nvim", "helix", "zed", "kitty", "alacritty",
    "ghostty", "wezterm", "iterm2", "tmux", "zellij", "herdr", "hypr", "fcitx5",
    "yazi", "k9s", "shell_gpt",
}


def test_generic_copy_inventory_is_complete() -> None:
    assert {module["name"] for module in COPY_MODULES} == EXPECTED_COPY_MODULE_NAMES
    tmux = next(module for module in COPY_MODULES if module["name"] == "tmux")
    zellij = next(module for module in COPY_MODULES if module["name"] == "zellij")
    assert tmux["config"]["source"] == "config/multiplexers/tmux"
    assert tmux["config"]["target"] == "~/.config/tmux"
    assert zellij["config"]["source"] == "config/multiplexers/zellij"
    assert zellij["config"]["target"] == "~/.config/zellij"


EXPECTED_SPECIALIZED_MODULE_NAMES = {
    "ocr", "agents", "cursor", "kiro", "opencode", "codex", "kimi-code", "pi", "zcode", "logseq",
}


def test_specialized_strategy_inventory_uses_safe_registry_dispatch(repo_root: Path) -> None:
    assert {module["name"] for module in SPECIALIZED_MODULES} == EXPECTED_SPECIALIZED_MODULE_NAMES
    production = (repo_root / "scripts" / "dotf_core" / "config_handler.py").read_text(encoding="utf-8")
    assert "deploy_config(" in production
    codex = repo_root / "scripts" / "modules" / "codex" / "config.sh"
    text = codex.read_text(encoding="utf-8")
    assert "dotf_registry_config" in text
    assert "dotf_ensure_symlink" not in text


@pytest.mark.parametrize("module", SPECIALIZED_MODULES, ids=lambda module: module["name"])
def test_specialized_config_is_manifest_owned_real_and_idempotent(
    repo_root: Path,
    tmp_path: Path,
    module: dict[str, Any],
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    name = module["name"]

    first = _run_config(repo_root, module, home, f"specialized-{name}-1")
    assert first.returncode == 0, first.stdout + first.stderr
    assert "RESULT\tchanged\t" in first.stdout, first.stdout + first.stderr

    target = _expand_home(module["config"]["target"], home)
    assert target.exists() and not target.is_symlink(), name
    paths = [target, *target.rglob("*")] if target.is_dir() else [target]
    assert all(not path.is_symlink() for path in paths), name
    before = _target_snapshot(target)

    manifest_path = home / ".local" / "state" / "dotf" / "config-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    owned = [item for item in manifest["items"] if item["owner"] == f"config:{name}"]
    assert owned, f"{name}: no manifest ownership"
    for item in owned:
        managed = Path(item["target"])
        assert managed == target or target in managed.parents
        assert managed.is_file() and not managed.is_symlink()

    second = _run_config(repo_root, module, home, f"specialized-{name}-2")
    assert second.returncode == 0, second.stdout + second.stderr
    assert "RESULT\tunchanged\t" in second.stdout, second.stdout + second.stderr
    assert _target_snapshot(target) == before, name
