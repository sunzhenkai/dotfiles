"""kind 物种声明与 Handler 对齐校验（module-registry 增量规格的五类场景）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from dotf_core import registry as modules


def _validate(mods: list[dict], hdir: Path | None = None) -> list[str]:
    return modules.validate_registry(
        mods,
        profiles_data={"profiles": {}},
        strict_handlers=False,
        handlers_dir=hdir,
    )


def _binary(name: str = "sdk") -> dict:
    return {"name": name, "kind": "binary", "install": True, "doctor": True}


def _config(name: str = "nvim") -> dict:
    return {"name": name, "kind": "config", "doctor": True}


def _make_hdir(tmp_path: Path, name: str, *files: tuple[str, str]) -> Path:
    hdir = tmp_path / "handlers"
    mod_dir = hdir / name
    mod_dir.mkdir(parents=True)
    for filename, body in files:
        path = mod_dir / filename
        path.write_text(body, encoding="utf-8")
    return hdir


def test_binary_module_with_install_handler_passes(tmp_path: Path) -> None:
    hdir = _make_hdir(tmp_path, "sdk", ("install.sh", "#!/usr/bin/env bash\ntrue\n"))
    assert _validate([_binary()], hdir=hdir) == []


def test_config_module_without_install_handler_passes(tmp_path: Path) -> None:
    hdir = _make_hdir(tmp_path, "nvim")
    assert _validate([_config()], hdir=hdir) == []


def test_config_module_may_keep_specialized_config_handler(tmp_path: Path) -> None:
    hdir = _make_hdir(tmp_path, "nvim", ("config.sh", "#!/usr/bin/env bash\ntrue\n"))
    assert _validate([_config()], hdir=hdir) == []


def test_binary_without_install_handler_is_rejected(tmp_path: Path) -> None:
    hdir = _make_hdir(tmp_path, "sdk")
    errors = _validate([_binary()], hdir=hdir)
    assert any("缺少处理器" in e and "install.sh" in e for e in errors)


def test_config_with_install_handler_is_rejected(tmp_path: Path) -> None:
    hdir = _make_hdir(
        tmp_path, "nvim", ("install.sh", "#!/usr/bin/env bash\ntrue\n")
    )
    errors = _validate([_config()], hdir=hdir)
    assert any("不得存在 install.sh" in e for e in errors)


def test_handler_dir_must_be_pure_bash(tmp_path: Path) -> None:
    hdir = _make_hdir(
        tmp_path,
        "sdk",
        ("install.sh", "#!/usr/bin/env bash\ntrue\n"),
        ("merge_config.py", "x = 1\n"),
    )
    errors = _validate([_binary()], hdir=hdir)
    assert any("只允许 .sh" in e and "merge_config.py" in e for e in errors)


def test_missing_kind_is_rejected() -> None:
    errors = _validate([{"name": "m", "install": True, "doctor": True}])
    assert any("缺失 kind" in e for e in errors)


def test_reserved_artifact_kind_is_rejected() -> None:
    errors = _validate([{"name": "m", "kind": "artifact", "install": True, "doctor": True}])
    assert any("kind 必须为 binary|config" in e for e in errors)


def test_kind_must_match_install_capability() -> None:
    mismatched = [{"name": "m", "kind": "config", "install": True, "doctor": True}]
    assert any("kind: config 不得声明 install" in e for e in _validate(mismatched))
    mismatched = [{"name": "m", "kind": "binary", "doctor": True}]
    assert any("kind: binary 必须声明 install" in e for e in _validate(mismatched))


def test_real_repo_registry_passes_kind_alignment() -> None:
    assert modules.validate_registry(strict_handlers=True) == []


@pytest.mark.parametrize("path", [modules.ROOT / "src"])
def test_src_root_only_allows_packages_and_exempt(path: Path) -> None:
    strays = [
        entry.name
        for entry in path.iterdir()
        if entry.is_file() and entry.suffix == ".py" and entry.name != "ensure_pyyaml.py"
    ]
    assert strays == []
