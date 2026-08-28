#!/usr/bin/env python3
"""Install curated third-party skills into ~/.agents/skills via npx skills."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from ensure_pyyaml import ensure_yaml  # noqa: E402

yaml = ensure_yaml()

CATALOG_REL = Path("agents") / "skills-defaults.yaml"
RunFn = Callable[..., subprocess.CompletedProcess]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def skills_target() -> Path:
    return Path.home() / ".agents" / "skills"


def catalog_path(root: Path) -> Path:
    return root / CATALOG_REL


def dest_skill_md(skill: str, dest_root: Optional[Path] = None) -> Path:
    base = dest_root if dest_root is not None else skills_target()
    return base / skill / "SKILL.md"


def first_party_skill_ids(root: Path) -> List[str]:
    skills_root = root / "agents" / "skills"
    if not skills_root.is_dir():
        return []
    return sorted(
        p.name
        for p in skills_root.iterdir()
        if p.is_dir() and (p / "SKILL.md").is_file()
    )


def load_catalog(root: Path) -> List[Dict[str, str]]:
    path = catalog_path(root)
    if not path.is_file():
        raise SystemExit(f"error: 缺少默认 skill 清单: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"error: {path} 必须是 mapping")
    raw = data.get("skills")
    if not isinstance(raw, list) or not raw:
        raise SystemExit(f"error: {path} 需要非空 skills 列表")

    items: List[Dict[str, str]] = []
    seen: set[str] = set()
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise SystemExit(f"error: {path} skills[{i}] 必须是 mapping")
        source = str(entry.get("source") or "").strip()
        skill = str(entry.get("skill") or "").strip()
        if not source or not skill:
            raise SystemExit(f"error: {path} skills[{i}] 需要 source 与 skill")
        if skill in seen:
            raise SystemExit(f"error: {path} 重复 skill: {skill}")
        seen.add(skill)
        items.append({"source": source, "skill": skill})

    overlap = sorted(seen.intersection(first_party_skill_ids(root)))
    if overlap:
        raise SystemExit(
            "error: 默认 skill 与 agents/skills/ 同名，会互相覆盖: " + ", ".join(overlap)
        )
    return items


def add_command(source: str, skill: str) -> List[str]:
    """全局安装到 ~/.agents/skills；不传 -a，避免写入各工具私有 skills 目录。"""
    return [
        "npx",
        "--yes",
        "skills",
        "add",
        source,
        "--skill",
        skill,
        "--global",
        "--yes",
        "--copy",
    ]


def _run_add(
    cmd: Sequence[str],
    *,
    run: RunFn,
) -> subprocess.CompletedProcess:
    return run(
        list(cmd),
        cwd=str(Path.home()),
        check=False,
        timeout=180,
    )


def install_defaults(
    root: Path,
    *,
    dry_run: bool = False,
    dest_root: Optional[Path] = None,
    run: Optional[RunFn] = None,
    which: Callable[[str], Optional[str]] = shutil.which,
) -> int:
    items = load_catalog(root)
    dest = dest_root if dest_root is not None else skills_target()
    runner: RunFn = run or subprocess.run

    print(f"==> default skills → {dest}")

    if which("npx") is None:
        missing = [it["skill"] for it in items if not dest_skill_md(it["skill"], dest).is_file()]
        if missing:
            print(
                "  ! 未找到 npx，跳过第三方默认 skill："
                + ", ".join(missing)
                + "（安装 Node.js 后重跑 dotf agents -c）"
            )
        else:
            print("  = npx 缺失，但清单内 skill 均已存在")
        return 0

    failed = 0
    for it in items:
        skill = it["skill"]
        marker = dest_skill_md(skill, dest)
        cmd = add_command(it["source"], skill)
        cmd_s = " ".join(cmd)
        if marker.is_file():
            print(f"  = {marker}")
            continue
        print(f"  + {marker}")
        print(f"    npx: {cmd_s}")
        if dry_run:
            continue
        dest.mkdir(parents=True, exist_ok=True)
        try:
            proc = _run_add(cmd, run=runner)
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"  ! {skill} 安装失败: {exc}", file=sys.stderr)
            failed += 1
            continue
        if proc.returncode != 0:
            print(f"  ! {skill} 安装失败 (exit {proc.returncode})", file=sys.stderr)
            failed += 1
            continue
        if not marker.is_file():
            print(f"  ! {skill} 安装后仍缺少 {marker}", file=sys.stderr)
            failed += 1

    if failed:
        print(
            f"  ! 有 {failed} 个默认 skill 未装上；一手 skills 仍已同步。"
            " 缺 npx/网络时稍后重跑 dotf agents -c",
            file=sys.stderr,
        )
    print(f"  done defaults: items={len(items)} failed={failed}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install curated third-party skills to ~/.agents/skills"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    root = args.root.resolve() if args.root else repo_root()
    try:
        return install_defaults(root, dry_run=args.dry_run)
    except SystemExit as e:
        code = e.code
        if isinstance(code, int):
            return code
        return 1


if __name__ == "__main__":
    sys.exit(main())
