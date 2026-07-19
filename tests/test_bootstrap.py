"""bootstrap 预检：不读 modules.yaml；覆盖依赖完整 / 缺 PyYAML / 未知 OS / 拒绝安装。"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

BOOTSTRAP = Path(__file__).resolve().parent.parent / "scripts" / "bootstrap.sh"


def run_bootstrap(
    *args: str,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    full = os.environ.copy()
    if env:
        full.update(env)
    return subprocess.run(
        ["bash", str(BOOTSTRAP), *args],
        capture_output=True,
        text=True,
        input=input_text,
        env=full,
        check=False,
    )


def _link_real(stub_bin: Path, name: str) -> None:
    real = shutil.which(name)
    if real is None:
        return
    target = stub_bin / name
    if not target.exists():
        target.symlink_to(real)


def test_check_only_ok_when_deps_present(tmp_home: Path) -> None:
    result = run_bootstrap("--check-only", env={"HOME": str(tmp_home)})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "基础运行时就绪" in result.stdout
    assert "modules.yaml" not in result.stdout + result.stderr


def test_delegates_to_dotf_init(tmp_home: Path, tmp_path: Path) -> None:
    stub = tmp_path / "fake-dotf"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        "printf 'DOTF_ARGS:%s\\n' \"$*\"\n"
        "exit 0\n",
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)

    result = run_bootstrap(
        "--",
        "--list",
        env={"HOME": str(tmp_home), "DOTF_BIN": str(stub)},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "DOTF_ARGS:init --list" in result.stdout
    assert "委托" in result.stdout


def test_missing_pyyaml_detected_without_registry(tmp_home: Path, stub_bin_dir: Path) -> None:
    py = stub_bin_dir / "python3"
    py.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"$1\" = \"-c\" ] && [[ \"$2\" == *yaml* ]]; then exit 1; fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    py.chmod(py.stat().st_mode | stat.S_IXUSR)
    for name in ("bash", "git", "curl"):
        _link_real(stub_bin_dir, name)

    result = run_bootstrap(
        "--check-only",
        env={
            "HOME": str(tmp_home),
            "PATH": os.environ["PATH"],
            "DOTF_BOOTSTRAP_OS": "ubuntu",
        },
    )
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "PyYAML" in combined
    assert "modules.yaml" not in combined
    assert "需要 PyYAML（python3 -c" not in combined


def test_unknown_os_fails(tmp_home: Path) -> None:
    result = run_bootstrap(
        "--check-only",
        env={"HOME": str(tmp_home), "DOTF_BOOTSTRAP_OS": "unknown"},
    )
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "不支持" in combined or "无法识别" in combined


def test_refuse_install_noninteractive(tmp_home: Path, stub_bin_dir: Path) -> None:
    """管道 stdin 非 TTY：缺依赖且无 --yes 时应快速失败，不执行安装。"""
    py = stub_bin_dir / "python3"
    py.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"$1\" = \"-c\" ] && [[ \"$2\" == *yaml* ]]; then exit 1; fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    py.chmod(py.stat().st_mode | stat.S_IXUSR)
    for name in ("bash", "git", "curl"):
        _link_real(stub_bin_dir, name)

    result = run_bootstrap(
        env={
            "HOME": str(tmp_home),
            "PATH": os.environ["PATH"],
            "DOTF_BOOTSTRAP_OS": "ubuntu",
        },
        input_text="n\n",
    )
    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert "非交互" in combined or "取消" in combined
    # 引导文案可含 apt 建议；不得真正进入安装阶段
    assert "开始安装缺失依赖" not in combined


def test_output_has_no_env_secrets(tmp_home: Path) -> None:
    secret = "SUPER_SECRET_TOKEN_xyz"
    result = run_bootstrap(
        "--check-only",
        env={"HOME": str(tmp_home), "API_KEY": secret, "OPENAI_API_KEY": secret},
    )
    combined = result.stdout + result.stderr
    assert secret not in combined
    assert "API_KEY=" not in combined
    assert "OPENAI_API_KEY=" not in combined
