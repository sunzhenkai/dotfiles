#!/usr/bin/env python3
"""Install agents/ skills into the shared ~/.agents/skills layout."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SLASH_RE = re.compile(r"\{\{slash:([a-z0-9-]+)\}\}")
FM_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.S)


def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def backup_dir() -> Path:
    return Path.home() / ".config" / "backups"


def timestamp() -> str:
    return str(int(time.time()))


def skills_target() -> Path:
    return Path.home() / ".agents" / "skills"


def _is_indented(line: str) -> bool:
    return bool(line) and (line[0] == " " or line[0] == "\t")


def parse_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    m = FM_RE.match(text)
    if not m:
        return {}, text
    raw_fm, body = m.group(1), m.group(2)
    meta: Dict[str, str] = {}
    # Keep nested metadata block as raw text under key "_metadata_block"
    lines = raw_fm.splitlines()
    i = 0
    meta_lines: List[str] = []
    in_meta = False
    while i < len(lines):
        line = lines[i]
        if in_meta:
            if _is_indented(line):
                meta_lines.append(line)
                i += 1
                continue
            in_meta = False
        if line.startswith("metadata:"):
            in_meta = True
            meta_lines = []
            i += 1
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            # YAML folded/literal block scalars: description: > / |
            if val in (">", ">-", "|", "|-"):
                block: List[str] = []
                i += 1
                while i < len(lines) and _is_indented(lines[i]):
                    block.append(lines[i].strip())
                    i += 1
                meta[key] = " ".join(block).strip() if val.startswith(">") else "\n".join(block).strip()
                continue
            meta[key] = val
        i += 1
    if meta_lines:
        meta["_metadata_block"] = "\n".join(meta_lines)
    meta["_raw_fm"] = raw_fm
    return meta, body


def fm_get(meta: Dict[str, str], key: str, default: str = "") -> str:
    return meta.get(key, default)


def unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        return s[1:-1]
    return s


def yaml_quote(s: str) -> str:
    """Emit a single-line YAML string safe for frontmatter values."""
    s = unquote(s).replace("\n", " ").strip()
    if not s:
        return '""'
    if any(c in s for c in ':#"\'\\\n') or s.startswith(">") or s.startswith("|") or s[:1] in "|&*!>@`":
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return s


def replace_slashes(body: str) -> str:
    """共享目标下 slash 命令统一渲染为 /xxx。"""
    return SLASH_RE.sub(lambda m: "/" + m.group(1), body)


def render_skill_frontmatter(meta: Dict[str, str], skill_id: str) -> str:
    name = unquote(fm_get(meta, "name", skill_id))
    desc = unquote(fm_get(meta, "description"))
    if not desc:
        raise ValueError(f"skill {skill_id}: description is required (got empty after parse)")
    license_ = fm_get(meta, "license")
    compat = fm_get(meta, "compatibility")
    lines = [
        f"name: {yaml_quote(name)}",
        f"description: {yaml_quote(desc)}",
    ]
    if license_:
        lines.append(f"license: {yaml_quote(license_)}")
    if compat:
        lines.append(f"compatibility: {yaml_quote(compat)}")
    if meta.get("_metadata_block"):
        lines.append("metadata:")
        lines.append(meta["_metadata_block"])
    return "---\n" + "\n".join(lines) + "\n---\n"


def _skip_sidecar_file(path: Path) -> bool:
    if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
        return True
    return False


def install_skill_sidecars(
    skill_dir: Path,
    skill_id: str,
    base: Path,
    dry_run: bool,
) -> Tuple[int, int]:
    """Copy references/ and scripts/ as-is (no frontmatter render, no slash replace)."""
    written = 0
    skipped = 0
    for name in ("references", "scripts"):
        src_root = skill_dir / name
        if not src_root.is_dir():
            continue
        for src_file in sorted(p for p in src_root.rglob("*") if p.is_file()):
            if _skip_sidecar_file(src_file):
                continue
            dest = (base / f"{skill_id}/{name}/{src_file.relative_to(src_root)}").expanduser()
            data = src_file.read_bytes()
            if dest.is_file() and dest.read_bytes() == data:
                skipped += 1
                print(f"  = {dest}")
                continue
            written += 1
            print(f"  + {dest}")
            if dry_run:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
    return written, skipped


def install_file(content: str, dest: Path, dry_run: bool = False) -> str:
    """Write content to dest with backup/idempotent skip. Returns status."""
    dest = dest.expanduser()
    if dest.is_file():
        existing = dest.read_text()
        if existing == content:
            return "skip"
    if dry_run:
        return "dry-run"
    if dest.exists() or dest.is_symlink():
        bdir = backup_dir()
        bdir.mkdir(parents=True, exist_ok=True)
        backup_path = bdir / f"{dest.name}-{timestamp()}"
        # avoid clobber backup names
        n = 0
        while backup_path.exists():
            n += 1
            backup_path = bdir / f"{dest.name}-{timestamp()}-{n}"
        shutil.move(str(dest), str(backup_path))
        print(f"  已备份 {dest} → {backup_path}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content)
    return "write"


def validate_output(path: Path, content: str) -> None:
    if "{{" in content:
        leftovers = re.findall(r"\{\{[^}]+\}\}", content)
        die(f"{path}: residual placeholders: {leftovers}")


def sync_skills(root: Path, dry_run: bool = False) -> int:
    skills_root = root / "agents" / "skills"
    if not skills_root.is_dir():
        die(f"missing agents source under {root / 'agents'}")

    base = skills_target()
    written = 0
    skipped = 0

    print(f"==> sync skills → {base}")

    for skill_dir in sorted(p for p in skills_root.iterdir() if p.is_dir()):
        skill_id = skill_dir.name
        src = skill_dir / "SKILL.md"
        if not src.is_file():
            continue
        meta, body = parse_frontmatter(src.read_text())
        body = replace_slashes(body)
        content = render_skill_frontmatter(meta, skill_id) + "\n" + body.lstrip("\n")
        if not content.endswith("\n"):
            content += "\n"
        dest = base / skill_id / "SKILL.md"
        validate_output(dest, content)
        status = install_file(content, dest, dry_run=dry_run)
        if status == "skip":
            skipped += 1
            print(f"  = {dest}")
        else:
            written += 1
            print(f"  + {dest}")
        w, s = install_skill_sidecars(skill_dir, skill_id, base, dry_run)
        written += w
        skipped += s

    print(f"  done skills: wrote={written} skipped={skipped}")
    return 0


SHIMS: Dict[str, str] = {}


def install_shims(root: Path, dry_run: bool = False) -> None:
    """Put the canonical script on PATH so mirrored copies never shadow it."""
    bin_dir = Path.home() / ".local" / "bin"
    for name, rel in SHIMS.items():
        canonical = root / rel
        if not canonical.is_file():
            continue
        dest = bin_dir / name
        content = (
            "#!/usr/bin/env sh\n"
            f"# generated by scripts/agents/sync.py; points at the canonical {name}\n"
            f'exec python3 "{canonical}" "$@"\n'
        )
        if dest.is_file() and dest.read_text() == content:
            print(f"  = {dest}")
            continue
        print(f"  + {dest}")
        if dry_run:
            continue
        bin_dir.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        dest.chmod(0o755)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync shared agents skills to ~/.agents/skills (tool 无关)"
    )
    parser.add_argument(
        "tool",
        nargs="?",
        default="all",
        help="仅兼容旧用法，必须省略或为 all（skills 同步已与 tool 无关）",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--root", type=Path, default=None, help="dotfiles root (default: auto)")
    args = parser.parse_args(argv)

    if args.tool.lower() != "all":
        die(f"skills 同步已与 tool 无关，请直接运行 sync.py（收到: '{args.tool}'）")

    root = args.root.resolve() if args.root else repo_root()

    rc = 0
    try:
        sync_skills(root, dry_run=args.dry_run)
    except SystemExit as e:
        rc = int(e.code) if e.code else 1
    except Exception as e:
        print(f"error syncing skills: {e}", file=sys.stderr)
        rc = 1
    if rc == 0:
        print("==> shims")
        install_shims(root, dry_run=args.dry_run)
    return rc


if __name__ == "__main__":
    sys.exit(main())
