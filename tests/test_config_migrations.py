"""End-to-end config state-boundary migrations for OpenSpec tasks 2.6-2.8."""

from __future__ import annotations

import hashlib
import json
import os
import plistlib
import re
import stat
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import modules
import pytest
import yaml


NAMED_MODULES = (
    "logseq",
    "tmux",
    "k9s",
    "zed",
    "nvim",
    "yazi",
    "iterm2",
    "fcitx5",
)

RUNTIME_SENTINELS = {
    "logseq": "graphs/runtime/sentinel",
    "tmux": "plugins/runtime/sentinel",
    "k9s": "clusters/runtime/sentinel",
    "zed": "conversations/runtime/sentinel",
    "nvim": "data/runtime/sentinel",
    "yazi": "cache/runtime/sentinel",
    "iterm2": "sessions/runtime/sentinel",
    "fcitx5": "data/runtime/sentinel",
}

EXPECTED_RUNTIME_BOUNDARIES = {
    "logseq": {"graphs", "plugins", "cache", "sessions", "history"},
    "tmux": {"plugins", "resurrect", "cache", "sessions", "history"},
    "k9s": {"clusters", "screen-dumps", "snapshots", "cache", "sessions", "history", "plugins"},
    "zed": {"conversations", "prompts", "cache", "sessions", "history", "extensions", "plugins"},
    "nvim": {"data", "cache", "session", "sessions", "history", "plugin", "pack"},
    "yazi": {"cache", "sessions", "history"},
    "iterm2": {"cache", "sessions", "history"},
    "fcitx5": {"cache", "data", "history", "db", "dictionaries"},
}


def _module(name: str) -> dict[str, Any]:
    return next(item for item in modules.load_registry() if item["name"] == name)


def _target(module: dict[str, Any], home: Path) -> Path:
    raw = module["config"]["target"]
    assert raw.startswith("~/")
    return home / raw[2:]


def _run_wrapper(repo: Path, module: dict[str, Any], home: Path, run_id: str):
    for directory in (home / ".config", home / ".cache", home / ".local" / "state"):
        directory.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        HOME=str(home),
        XDG_CONFIG_HOME=str(home / ".config"),
        XDG_CACHE_HOME=str(home / ".cache"),
        XDG_STATE_HOME=str(home / ".local" / "state"),
        DOTFILES_ROOT=str(repo),
        DOTF_MODULE=module["name"],
        DOTF_ACTION="config",
        DOTF_RUN_ID=run_id,
    )
    return subprocess.run(
        [
            "bash",
            "-c",
            'source "$1/scripts/lib/runner.sh"; runner_run_action config "$2"',
            "runner-config",
            str(repo),
            module["name"],
        ],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _repository_digest(repo: Path) -> str:
    listed = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout.split(b"\0")
    digest = hashlib.sha256(b"repository-v1\0")
    for raw in sorted(item for item in listed if item):
        relative = os.fsdecode(raw)
        path = repo / relative
        try:
            item = path.lstat()
        except FileNotFoundError:
            # The cached index may still list the old side of an unstaged rename.
            continue
        digest.update(raw + b"\0" + str(stat.S_IFMT(item.st_mode)).encode() + b"\0")
        if stat.S_ISLNK(item.st_mode):
            digest.update(os.fsencode(os.readlink(path)))
        elif stat.S_ISREG(item.st_mode):
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _git_diff_snapshot(repo: Path) -> tuple[bytes, bytes, bytes]:
    def git(*args: str) -> bytes:
        return subprocess.run(
            ["git", *args], cwd=repo, check=True, capture_output=True
        ).stdout

    return (
        git("status", "--porcelain=v1", "-z"),
        git("diff", "--binary", "--no-ext-diff"),
        git("diff", "--cached", "--binary", "--no-ext-diff"),
    )


def _tree_snapshot(root: Path) -> tuple[tuple[str, int, int, int, int, str | None], ...]:
    paths = [root, *sorted(root.rglob("*"))]
    result = []
    for path in paths:
        item = path.lstat()
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        result.append(
            (
                "." if path == root else str(path.relative_to(root)),
                stat.S_IFMT(item.st_mode),
                stat.S_IMODE(item.st_mode),
                item.st_ino,
                item.st_mtime_ns,
                digest,
            )
        )
    return tuple(result)


def _assert_declared_formats(target: Path) -> None:
    for path in target.rglob("*"):
        if not path.is_file():
            continue
        raw = path.read_bytes()
        suffix = path.suffix.lower()
        if suffix == ".json":
            text = raw.decode("utf-8")
            try:
                json.loads(text)
            except json.JSONDecodeError:
                # Zed settings/keymaps use JSONC (comments/trailing commas).
                without_comments = re.sub(r"(?m)^\s*//.*$", "", text)
                json.loads(re.sub(r",(\s*[}\]])", r"\1", without_comments))
        elif suffix in {".yaml", ".yml"}:
            yaml.safe_load(raw)
        elif suffix == ".toml":
            tomllib.loads(raw.decode("utf-8"))
        elif suffix in {".plist", ".itermcolors"}:
            plistlib.loads(raw)
        elif suffix == ".edn":
            text = raw.decode("utf-8")
            assert text.strip() and text.count("{") == text.count("}")
        else:
            raw.decode("utf-8")


def test_registry_is_the_only_symlink_allowlist_and_runtime_inventory() -> None:
    registry = modules.load_registry()
    symlink_allowlist = tuple(
        module["name"]
        for module in registry
        if modules.has_config(module) and modules.module_strategy(module) == "symlink"
    )
    assert symlink_allowlist == ()
    assert all(
        modules.module_strategy(module) != "symlink"
        for module in registry
        if modules.has_config(module)
        and (modules.module_writable(module) or modules.module_sensitive(module))
    )
    for name, expected in EXPECTED_RUNTIME_BOUNDARIES.items():
        config = _module(name)["config"]
        declared = set(config["preserve"]) | set(config["exclude"])
        assert expected <= declared, name


@pytest.mark.parametrize("name", NAMED_MODULES)
def test_named_module_real_root_runtime_preservation_formats_modes_and_idempotence(
    repo_root: Path, tmp_path: Path, name: str
) -> None:
    module = _module(name)
    home = tmp_path / "home"
    home.mkdir()
    target = _target(module, home)
    sentinel = target / RUNTIME_SENTINELS[name]
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("home-runtime-only\n", encoding="utf-8")
    repo_before = _repository_digest(repo_root)
    diff_before = _git_diff_snapshot(repo_root)

    first = _run_wrapper(repo_root, module, home, f"migration-{name}-1")
    assert first.returncode == 0, first.stdout + first.stderr
    assert "RESULT\tchanged\t" in first.stdout
    assert target.is_dir() and not target.is_symlink()
    assert sentinel.read_text(encoding="utf-8") == "home-runtime-only\n"
    assert stat.S_IMODE(target.stat().st_mode) == int(module["config"]["target_mode"], 8)
    manifest = json.loads(
        (home / ".local" / "state" / "dotf" / "config-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    owned = [item for item in manifest["items"] if item["owner"] == f"config:{name}"]
    assert owned
    for item in owned:
        managed = Path(item["target"])
        assert stat.S_IMODE(managed.stat().st_mode) == item["mode"]
        if module["config"]["sensitive"]:
            assert item["mode"] & ~0o600 == 0
    assert all(not path.is_symlink() for path in [target, *target.rglob("*")])
    _assert_declared_formats(target)
    before_second = _tree_snapshot(target)

    second = _run_wrapper(repo_root, module, home, f"migration-{name}-2")
    assert second.returncode == 0, second.stdout + second.stderr
    assert "RESULT\tunchanged\t" in second.stdout
    assert _tree_snapshot(target) == before_second
    assert sentinel.read_text(encoding="utf-8") == "home-runtime-only\n"
    assert _repository_digest(repo_root) == repo_before
    assert _git_diff_snapshot(repo_root) == diff_before


@pytest.mark.parametrize("name", NAMED_MODULES)
def test_named_module_legacy_root_link_is_only_unlinked(
    repo_root: Path, tmp_path: Path, name: str
) -> None:
    module = _module(name)
    home = tmp_path / "home"
    home.mkdir()
    target = _target(module, home)
    source = repo_root / module["config"]["source"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(source, target_is_directory=True)
    repo_before = _repository_digest(repo_root)
    diff_before = _git_diff_snapshot(repo_root)

    result = _run_wrapper(repo_root, module, home, f"legacy-root-{name}")
    assert result.returncode == 0, result.stdout + result.stderr
    assert target.is_dir() and not target.is_symlink()
    assert source.is_dir()
    assert _repository_digest(repo_root) == repo_before
    assert _git_diff_snapshot(repo_root) == diff_before


@pytest.mark.parametrize("name", NAMED_MODULES)
def test_named_module_non_directory_root_conflicts_without_mutation(
    repo_root: Path, tmp_path: Path, name: str
) -> None:
    module = _module(name)
    home = tmp_path / "home"
    home.mkdir()
    target = _target(module, home)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("foreign-non-link-target\n", encoding="utf-8")
    repo_before = _repository_digest(repo_root)
    diff_before = _git_diff_snapshot(repo_root)

    result = _run_wrapper(repo_root, module, home, f"non-link-conflict-{name}")
    assert result.returncode != 0
    assert target.is_file() and target.read_text(encoding="utf-8") == "foreign-non-link-target\n"
    assert _repository_digest(repo_root) == repo_before
    assert _git_diff_snapshot(repo_root) == diff_before


def test_logseq_legacy_settings_link_private_fields_and_unowned_runtime(
    repo_root: Path, tmp_path: Path
) -> None:
    module = _module("logseq")
    home = tmp_path / "home"
    home.mkdir()
    target = _target(module, home)
    source = repo_root / module["config"]["source"]
    target.mkdir(parents=True)
    (target / "settings").symlink_to(source / "settings", target_is_directory=True)
    runtime = target / "plugins" / "runtime-only.json"
    runtime.parent.mkdir()
    runtime.write_text('{"credential": "home-only"}\n', encoding="utf-8")
    repo_before = _repository_digest(repo_root)
    diff_before = _git_diff_snapshot(repo_root)

    migrated = _run_wrapper(repo_root, module, home, "logseq-settings-link-1")
    assert migrated.returncode == 0, migrated.stdout + migrated.stderr
    assert (target / "settings").is_dir() and not (target / "settings").is_symlink()
    assert (target / "config" / "config.edn").is_file()
    assert (target / "config" / "plugins.edn").is_file()
    assert (target / "preferences.json").is_file()
    assert runtime.read_text(encoding="utf-8") == '{"credential": "home-only"}\n'

    setting = target / "settings" / "logseq-todoist-plugin.json"
    payload = json.loads(setting.read_text(encoding="utf-8"))
    payload.update(
        apiToken="destination-api-token",
        accountId="destination-account",
        workspacePath="/private/workspace",
        credentialFile="/private/credential",
        runtimeState={"session": "unowned"},
    )
    setting.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

    merged = _run_wrapper(repo_root, module, home, "logseq-settings-link-2")
    assert merged.returncode == 0, merged.stdout + merged.stderr
    preserved = json.loads(setting.read_text(encoding="utf-8"))
    assert preserved["apiToken"] == "destination-api-token"
    assert preserved["accountId"] == "destination-account"
    assert preserved["workspacePath"] == "/private/workspace"
    assert preserved["credentialFile"] == "/private/credential"
    assert preserved["runtimeState"] == {"session": "unowned"}
    stable = _tree_snapshot(target)

    repeated = _run_wrapper(repo_root, module, home, "logseq-settings-link-3")
    assert repeated.returncode == 0, repeated.stdout + repeated.stderr
    assert "RESULT\tunchanged\t" in repeated.stdout
    assert _tree_snapshot(target) == stable
    assert _repository_digest(repo_root) == repo_before
    assert _git_diff_snapshot(repo_root) == diff_before


def test_logseq_field_merge_preserves_declared_private_keys() -> None:
    from dotf_core.config_producers import _private_overlay

    destination = {
        "apiToken": "destination-token",
        "accountId": "destination-account",
        "workspacePath": "/destination/workspace",
        "credentialFile": "/destination/credential",
        "nested": {"privateToken": "nested-destination", "managed": "old"},
        "runtimeState": {"session": "unowned"},
    }
    managed = {
        "apiToken": "public-default",
        "accountId": "public-account",
        "workspacePath": "/public/workspace",
        "credentialFile": "/public/credential",
        "nested": {"privateToken": "nested-public", "managed": "new"},
        "safeSetting": True,
    }

    merged = _private_overlay(destination, managed)
    assert merged["apiToken"] == "destination-token"
    assert merged["accountId"] == "destination-account"
    assert merged["workspacePath"] == "/destination/workspace"
    assert merged["credentialFile"] == "/destination/credential"
    assert merged["nested"] == {"privateToken": "nested-destination", "managed": "new"}
    assert merged["runtimeState"] == {"session": "unowned"}
    assert merged["safeSetting"] is True
