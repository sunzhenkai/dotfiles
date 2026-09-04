"""Config deployment metadata schema, safety conflicts, and accessors."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import modules
import pytest


def _config(source: Path, **updates: Any) -> dict[str, Any]:
    config: dict[str, Any] = {
        "source": str(source),
        "target": "~/.config/fixture",
        "strategy": "copy",
        "writable": True,
        "sensitive": False,
        "target_mode": "0755" if source.is_dir() else "0644",
        "preserve": [],
        "exclude": [],
    }
    config.update(updates)
    return config


def _errors(config: dict[str, Any]) -> list[str]:
    return modules.validate_registry(
        [{"name": "fixture", "doctor": True, "config": config}],
        profiles_data={"profiles": {}},
        strict_handlers=False,
    )


@pytest.mark.parametrize(
    "field",
    [
        "source",
        "target",
        "strategy",
        "writable",
        "sensitive",
        "target_mode",
        "preserve",
        "exclude",
    ],
)
def test_config_metadata_required(tmp_path: Path, field: str) -> None:
    source = tmp_path / "source"
    source.mkdir()
    config = _config(source)
    del config[field]

    errors = _errors(config)
    assert any(field in error and "缺失" in error for error in errors), errors


def test_config_metadata_rejects_unknown_field(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    errors = _errors(_config(source, stratgey="copy"))
    assert any("未知字段" in error and "stratgey" in error for error in errors)

    config = _config(source)
    config[1] = "unknown"
    errors = _errors(config)
    assert any("未知字段" in error and "1" in error for error in errors)


@pytest.mark.parametrize("strategy", ["link", "COPY", 1, None, [], {}])
def test_config_strategy_is_closed_enum(tmp_path: Path, strategy: Any) -> None:
    source = tmp_path / "source"
    source.mkdir()
    errors = _errors(_config(source, strategy=strategy))
    assert any("config.strategy" in error for error in errors)


@pytest.mark.parametrize("field", ["writable", "sensitive"])
@pytest.mark.parametrize("value", [0, 1, "false", None, []])
def test_config_boolean_metadata_requires_bool(
    tmp_path: Path, field: str, value: Any
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    errors = _errors(_config(source, **{field: value}))
    assert any(f"config.{field} 必须为 bool" in error for error in errors)


@pytest.mark.parametrize("value", ["0600", "0o600", 0o600, "0000", 0])
def test_config_mode_accepts_normalized_octal_values(tmp_path: Path, value: Any) -> None:
    source = tmp_path / "source.toml"
    source.write_text("x = 1\n", encoding="utf-8")
    assert _errors(_config(source, target_mode=value)) == []


@pytest.mark.parametrize(
    "value", [True, False, "0648", "0o888", "644x", "7777", 0o1000, 600, 1.5, None]
)
def test_config_mode_rejects_invalid_octal_or_type(tmp_path: Path, value: Any) -> None:
    source = tmp_path / "source.toml"
    source.write_text("x = 1\n", encoding="utf-8")
    errors = _errors(_config(source, target_mode=value))
    assert any("八进制权限" in error for error in errors)


def test_mode_alias_is_supported_but_cannot_conflict(tmp_path: Path) -> None:
    source = tmp_path / "source.toml"
    source.write_text("x = 1\n", encoding="utf-8")
    config = _config(source)
    del config["target_mode"]
    config["mode"] = "0600"
    assert _errors(config) == []
    mod = {"config": config}
    assert modules.module_config_mode(mod) == 0o600
    assert modules.module_target_mode(mod) == 0o600
    assert modules.module_mode(mod) == 0o600
    assert modules.module_preserve(mod) == []
    assert modules.module_exclude(mod) == []
    assert modules.format_config_mode(modules.module_config_mode(mod)) == "0600"

    config["target_mode"] = "0600"
    errors = _errors(config)
    assert any("不能同时声明" in error for error in errors)


def test_symlink_requires_explicit_read_only_non_sensitive_file(tmp_path: Path) -> None:
    source = tmp_path / "source.toml"
    source.write_text("x = 1\n", encoding="utf-8")
    valid = _config(
        source,
        strategy="symlink",
        writable=False,
        sensitive=False,
        target_mode="0644",
    )
    assert _errors(valid) == []

    for changes in (
        {"writable": True},
        {"sensitive": True, "target_mode": "0600"},
        {"writable": True, "sensitive": True, "target_mode": "0600"},
    ):
        errors = _errors({**valid, **changes})
        assert any("strategy symlink" in error for error in errors), errors


def test_symlink_rejects_directory_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    errors = _errors(
        _config(source, strategy="symlink", writable=False, sensitive=False)
    )
    assert any("仅允许单个普通文件" in error for error in errors)


def test_config_rejects_missing_source(tmp_path: Path) -> None:
    source = tmp_path / "missing"
    errors = _errors(_config(source))
    assert any("source 不存在" in error for error in errors), errors


def test_symlink_rejects_source_symlink_even_to_regular_file(tmp_path: Path) -> None:
    regular = tmp_path / "regular.toml"
    regular.write_text("x = 1\n", encoding="utf-8")
    source = tmp_path / "source.toml"
    source.symlink_to(regular)

    errors = _errors(
        _config(
            source,
            strategy="symlink",
            writable=False,
            sensitive=False,
            target_mode="0644",
        )
    )
    assert any("source 自身是符号链接" in error for error in errors), errors
    assert any("仅允许单个普通文件" in error for error in errors), errors


def test_config_rejects_fifo_source(tmp_path: Path) -> None:
    source = tmp_path / "source.fifo"
    os.mkfifo(source)

    errors = _errors(_config(source))
    assert any("source 是特殊文件" in error for error in errors), errors


def test_sensitive_config_rejects_missing_source_before_mode_check(
    tmp_path: Path,
) -> None:
    source = tmp_path / "missing-secret"
    errors = _errors(_config(source, sensitive=True, target_mode="0777"))
    assert errors
    assert any("source 不存在" in error for error in errors), errors
    assert any("无法确定目标是普通文件还是目录" in error for error in errors), errors


@pytest.mark.parametrize("mode", ["0601", "0610", "0700", "0100", "0640"])
def test_sensitive_regular_file_mode_not_broader_than_0600(
    tmp_path: Path, mode: str
) -> None:
    source = tmp_path / "secret.json"
    source.write_text("{}\n", encoding="utf-8")
    errors = _errors(_config(source, sensitive=True, target_mode=mode))
    assert any("敏感普通文件" in error for error in errors)


@pytest.mark.parametrize("mode", ["0701", "0710", "0750", "0777"])
def test_sensitive_directory_mode_not_broader_than_0700(
    tmp_path: Path, mode: str
) -> None:
    source = tmp_path / "secret-dir"
    source.mkdir()
    errors = _errors(_config(source, sensitive=True, target_mode=mode))
    assert any("敏感目录" in error for error in errors)


@pytest.mark.parametrize(
    ("preserve", "exclude"),
    [
        (["plugins"], ["plugins"]),
        (["plugins"], ["plugins/cache"]),
        (["plugins/cache"], ["plugins"]),
        (["a/../plugins"], ["plugins"]),
    ],
)
def test_preserve_exclude_reject_exact_or_nested_overlap(
    tmp_path: Path, preserve: list[str], exclude: list[str]
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    errors = _errors(_config(source, preserve=preserve, exclude=exclude))
    assert any("preserve/exclude 路径重叠" in error for error in errors)


@pytest.mark.parametrize("field", ["preserve", "exclude"])
@pytest.mark.parametrize("value", ["plugins", [1], [""], ["../escape"], ["/absolute"]])
def test_preserve_exclude_validate_list_and_safe_relative_paths(
    tmp_path: Path, field: str, value: Any
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    errors = _errors(_config(source, **{field: value}))
    assert any(f"config.{field}" in error for error in errors)


def test_regular_file_rejects_directory_path_metadata(tmp_path: Path) -> None:
    source = tmp_path / "source.toml"
    source.write_text("x = 1\n", encoding="utf-8")
    errors = _errors(_config(source, preserve=["runtime"]))
    assert any("普通文件 config 不兼容" in error for error in errors)


def test_real_registry_has_explicit_safe_metadata() -> None:
    config_modules = [mod for mod in modules.load_registry() if modules.has_config(mod)]
    assert config_modules
    for mod in config_modules:
        config = mod["config"]
        assert set(config) <= modules.CONFIG_KEYS
        assert modules.CONFIG_REQUIRED_KEYS <= set(config)
        assert ("target_mode" in config) ^ ("mode" in config)
        assert modules.module_strategy(mod) in modules.CONFIG_STRATEGIES
        assert modules.module_writable(mod) is not None
        assert modules.module_sensitive(mod) is not None
        assert modules.module_config_mode(mod) is not None
    # Until a read-only single-file allowlist is reviewed, no symlink is safer.
    assert not [mod for mod in config_modules if modules.module_strategy(mod) == "symlink"]
    assert modules.validate_registry(strict_handlers=True) == []


def test_logseq_preserves_all_authoritative_runtime_paths() -> None:
    logseq = next(mod for mod in modules.load_registry() if mod["name"] == "logseq")
    assert {"graphs", "plugins", "graphs.edn"} <= set(
        modules.module_preserve(logseq)
    )


def test_codex_uses_sensitive_merge_directory_and_preserves_runtime() -> None:
    codex = next(mod for mod in modules.load_registry() if mod["name"] == "codex")
    config = codex["config"]
    assert config["source"] == "agents/vendors/codex"
    assert config["target"] == "~/.codex"
    assert config["strategy"] == "merge"
    assert config["writable"] is True and config["sensitive"] is True
    assert config["target_mode"] == "0700"
    assert {"auth.json", "history.jsonl", "sessions", "log", "skills"} <= set(
        modules.module_preserve(codex)
    )
    assert {"README.md", "config.local.toml.example"} <= set(
        modules.module_exclude(codex)
    )


def test_cli_and_shell_accessors_expose_metadata(repo_root: Path) -> None:
    py = repo_root / "scripts" / "modules.py"
    get_result = subprocess.run(
        ["python3", str(py), "get", "logseq"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )
    values = dict(line.split("=", 1) for line in get_result.stdout.splitlines())
    assert values["strategy"] == "merge"
    assert values["writable"] == "true"
    assert values["sensitive"] == "true"
    assert values["target_mode"] == "0700"
    assert values["preserve"] == "cache,graphs,plugins,sessions,history,graphs.edn"
    assert values["exclude"] == ""

    shell_result = subprocess.run(
        [
            "bash",
            "-c",
            "source scripts/modules.sh; "
            "modules_strategy logseq; modules_writable logseq; "
            "modules_sensitive logseq; modules_target_mode logseq; "
            "modules_mode logseq; modules_preserve logseq; modules_exclude logseq",
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )
    assert shell_result.stdout.splitlines() == [
        "merge",
        "true",
        "true",
        "0700",
        "0700",
        "cache graphs plugins sessions history graphs.edn",
        "",
    ]
