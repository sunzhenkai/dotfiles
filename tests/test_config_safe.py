"""公共配置安全库：symlink 幂等、备份、仅操作临时 HOME。"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "scripts" / "lib" / "config_safe.sh"


def _run_lib(
    script: str,
    *,
    home: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    full_env = os.environ.copy()
    full_env["HOME"] = str(home)
    full_env["DOTFILES_ROOT"] = str(ROOT)
    full_env["DOTF_BACKUP_DIR"] = str(home / ".config" / "backups")
    if env:
        full_env.update(env)
    wrapper = f"""
set -euo pipefail
source "{LIB}"
{script}
"""
    return subprocess.run(
        ["bash", "-c", wrapper],
        capture_output=True,
        text=True,
        env=full_env,
        cwd=str(ROOT),
        check=False,
    )


def test_expand_path_tilde(tmp_home: Path) -> None:
    # 单引号避免 bash 先展开 ~
    r = _run_lib("dotf_expand_path '~/foo/bar'", home=tmp_home)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == str(tmp_home / "foo" / "bar")


def test_ensure_parent_creates_dirs(tmp_home: Path) -> None:
    target = tmp_home / "a" / "b" / "c.txt"
    r = _run_lib(f'dotf_ensure_parent "{target}"', home=tmp_home)
    assert r.returncode == 0, r.stderr
    assert (tmp_home / "a" / "b").is_dir()


def test_symlink_missing_target_creates(tmp_home: Path, tmp_path: Path) -> None:
    src = tmp_path / "src.txt"
    src.write_text("hello", encoding="utf-8")
    target = tmp_home / ".config" / "demo" / "link"
    r = _run_lib(
        f'''
dotf_ensure_symlink "{src}" "{target}"
echo "STATUS=$DOTF_CFG_STATUS"
''',
        home=tmp_home,
    )
    assert r.returncode == 0, r.stderr
    assert "STATUS=changed" in r.stdout
    assert target.is_symlink()
    assert target.resolve() == src.resolve()


def test_correct_symlink_unchanged(tmp_home: Path, tmp_path: Path) -> None:
    src = tmp_path / "src.txt"
    src.write_text("hello", encoding="utf-8")
    target = tmp_home / "link"
    target.symlink_to(src)
    before = target.readlink()
    r = _run_lib(
        f'''
dotf_ensure_symlink "{src}" "{target}"
echo "STATUS=$DOTF_CFG_STATUS"
''',
        home=tmp_home,
    )
    assert r.returncode == 0, r.stderr
    assert "STATUS=unchanged" in r.stdout
    assert target.readlink() == before


def test_wrong_symlink_replaced_with_backup(tmp_home: Path, tmp_path: Path) -> None:
    src = tmp_path / "correct.txt"
    src.write_text("ok", encoding="utf-8")
    other = tmp_path / "other.txt"
    other.write_text("other", encoding="utf-8")
    target = tmp_home / "link"
    target.symlink_to(other)

    r = _run_lib(
        f'''
dotf_ensure_symlink "{src}" "{target}"
echo "STATUS=$DOTF_CFG_STATUS"
''',
        home=tmp_home,
    )
    assert r.returncode == 0, r.stderr
    assert "STATUS=changed" in r.stdout
    assert target.resolve() == src.resolve()
    backups = list((tmp_home / ".config" / "backups").iterdir())
    assert len(backups) == 1


def test_broken_symlink_replaced(tmp_home: Path, tmp_path: Path) -> None:
    src = tmp_path / "correct.txt"
    src.write_text("ok", encoding="utf-8")
    target = tmp_home / "link"
    target.symlink_to(tmp_path / "missing-nowhere")
    assert target.is_symlink() and not target.exists()

    r = _run_lib(
        f'''
dotf_ensure_symlink "{src}" "{target}"
echo "STATUS=$DOTF_CFG_STATUS"
''',
        home=tmp_home,
    )
    assert r.returncode == 0, r.stderr
    assert "STATUS=changed" in r.stdout
    assert target.resolve() == src.resolve()


def test_regular_file_backed_up(tmp_home: Path, tmp_path: Path) -> None:
    src = tmp_path / "correct.txt"
    src.write_text("ok", encoding="utf-8")
    target = tmp_home / "link"
    target.write_text("old content", encoding="utf-8")

    r = _run_lib(
        f'''
dotf_ensure_symlink "{src}" "{target}"
echo "STATUS=$DOTF_CFG_STATUS"
''',
        home=tmp_home,
    )
    assert r.returncode == 0, r.stderr
    assert "STATUS=changed" in r.stdout
    assert target.is_symlink()
    backups = list((tmp_home / ".config" / "backups").glob("link-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "old content"


def test_backup_paths_no_collision(tmp_home: Path) -> None:
    f = tmp_home / "item"
    f.write_text("a", encoding="utf-8")
    r = _run_lib(
        f'''
d1=$(dotf_backup_to "{f}")
echo "$d1" > "{tmp_home}/.d1"
# 重新创建同名文件再备份
echo b > "{f}"
d2=$(dotf_backup_to "{f}")
echo "$d2" > "{tmp_home}/.d2"
test -e "$d1"
test -e "$d2"
test "$d1" != "$d2"
echo OK
''',
        home=tmp_home,
    )
    assert r.returncode == 0, r.stderr
    assert "OK" in r.stdout
    d1 = Path((tmp_home / ".d1").read_text(encoding="utf-8").strip())
    d2 = Path((tmp_home / ".d2").read_text(encoding="utf-8").strip())
    assert d1 != d2
    assert str(tmp_home) in str(d1)
    assert str(tmp_home) in str(d2)


def test_operations_stay_in_tmp_home(
    tmp_home: Path, tmp_path: Path, launch_home: Path
) -> None:
    """所有配置操作仅触及临时 HOME，不碰真实 HOME。"""
    src = tmp_path / "src.txt"
    src.write_text("x", encoding="utf-8")
    target = tmp_home / ".config" / "app" / "cfg"
    # 真实 HOME 下不存在探测哨兵
    sentinel = launch_home / ".dotf_config_safe_test_sentinel"
    assert not sentinel.exists()

    r = _run_lib(
        f'dotf_ensure_symlink "{src}" "{target}"',
        home=tmp_home,
    )
    assert r.returncode == 0, r.stderr
    assert target.is_symlink()
    assert not sentinel.exists()
    assert Path(os.environ["HOME"]).resolve() == tmp_home.resolve()
    # 链接路径本身在临时 HOME（resolve 会跟到 tmp_path 源，故不 follow）
    assert str(target).startswith(str(tmp_home))
