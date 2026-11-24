"""skill/instructions 卫生门禁的行为测试。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ci" / "skill-hygiene.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def test_repo_skill_sources_are_clean() -> None:
    result = _run()
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "findings=0" in output


def test_clean_examples_pass(tmp_path: Path) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text(
        "使用 ~/.local/bin 与 /home/linuxbrew/.linuxbrew；示例地址 <host>、<ip>。\n",
        encoding="utf-8",
    )
    result = _run(str(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr


def test_private_context_is_flagged_and_redacted(tmp_path: Path) -> None:
    doc = tmp_path / "leak.md"
    doc.write_text(
        "\n".join(
            (
                "访问 192.168.1.10 与 10.0.0.5",
                "路径 /Users/alice/code/repo",
                "域名 nas.internal 和 html.lan",
                "token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            )
        ),
        encoding="utf-8",
    )
    result = _run(str(tmp_path))
    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert "private-ip" in output
    assert "home-path" in output
    assert "internal-domain" in output
    assert "credential-token" in output
    # 凭据不得原样回显
    assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" not in output
    assert "已脱敏" in output
