"""grepom uninstall handler 与其它模块拒绝 --uninstall。"""

from __future__ import annotations

from pathlib import Path

from conftest import run_dotf


def test_grepom_uninstall_dry_run_does_not_remove(tmp_home: Path) -> None:
    target = tmp_home / ".local" / "bin" / "grepom"
    target.parent.mkdir(parents=True)
    target.write_text("binary\n", encoding="utf-8")
    result = run_dotf("grepom", "--uninstall", "--dry-run")
    assert result.returncode == 0, result.stderr
    assert target.is_file()
    assert target.read_text(encoding="utf-8") == "binary\n"


def test_grepom_uninstall_is_idempotent(tmp_home: Path) -> None:
    target = tmp_home / ".local" / "bin" / "grepom"
    target.parent.mkdir(parents=True)
    target.write_text("binary\n", encoding="utf-8")
    first = run_dotf("grepom", "--uninstall", "--yes")
    assert first.returncode == 0, first.stderr + first.stdout
    assert not target.exists()
    second = run_dotf("grepom", "--uninstall", "--yes")
    assert second.returncode == 0, second.stderr + second.stdout
    assert "unchanged" in second.stdout


def test_other_modules_cannot_guess_uninstall(tmp_home: Path) -> None:
    for name in ("nvim", "system", "homebrew", "sdk"):
        result = run_dotf(name, "--uninstall", "--yes")
        assert result.returncode != 0, name
        combined = result.stdout + result.stderr
        assert "uninstall" in combined.lower()


def test_uninstall_cannot_mix_with_icd(tmp_home: Path) -> None:
    result = run_dotf("grepom", "-i", "--uninstall")
    assert result.returncode != 0
    assert "字母串" in result.stdout + result.stderr or "不能" in result.stdout + result.stderr
