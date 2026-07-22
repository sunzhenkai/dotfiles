#!/usr/bin/env python3
"""Adapt agents/ skills & commands into per-tool layouts and install them."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

TOOLS = ("claude", "cursor", "opencode", "codex", "kimi-code", "pi")
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

def resolve_slash(tool: str, cmd_id: str) -> str:
    if tool == "claude" and cmd_id.startswith("opsx-"):
        return "/opsx:" + cmd_id[len("opsx-") :]
    return "/" + cmd_id


def replace_slashes(body: str, tool: str) -> str:
    def repl(m: re.Match) -> str:
        return resolve_slash(tool, m.group(1))

    return SLASH_RE.sub(repl, body)


def read_exclude(path: Path) -> set:
    if not path.is_file():
        return set()
    tools = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tools.add(line.lower())
    return tools


def skill_excluded(skill_dir: Path, tool: str) -> bool:
    return tool in read_exclude(skill_dir / "exclude")


def command_excluded(cmd_file: Path, tool: str) -> bool:
    return tool in read_exclude(cmd_file.with_suffix(cmd_file.suffix + ".exclude")) or tool in read_exclude(
        cmd_file.parent / f"{cmd_file.stem}.exclude"
    )


def render_skill_frontmatter(tool: str, meta: Dict[str, str], skill_id: str) -> str:
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

def render_command_frontmatter(tool: str, meta: Dict[str, str], cmd_id: str) -> str:
    title = unquote(fm_get(meta, "title", cmd_id))
    desc = fm_get(meta, "description")
    # preserve quotes if description has special chars
    if desc and not (desc.startswith('"') or desc.startswith("'")):
        if ":" in desc or desc.startswith(" ") or "#" in desc:
            desc_out = f'"{desc}"'
        else:
            desc_out = desc
    else:
        desc_out = desc
    category = unquote(fm_get(meta, "category", "Workflow"))
    tags = fm_get(meta, "tags", "[workflow]")

    if tool == "claude":
        return (
            "---\n"
            f'name: "{title}"\n'
            f"description: {desc_out}\n"
            f"category: {category}\n"
            f"tags: {tags}\n"
            "---\n"
        )
    if tool == "cursor":
        return (
            "---\n"
            f"name: /{cmd_id}\n"
            f"id: {cmd_id}\n"
            f"category: {category}\n"
            f"description: {desc_out}\n"
            "---\n"
        )
    if tool == "opencode":
        lines = [f"description: {desc_out}"]
        # OpenCode-only：若存在对应 persona，注入 agent 字段（不出现在共享源）
        agent = unquote(fm_get(meta, "agent"))
        if not agent and cmd_id:
            # 约定：command id 与 persona 同名时可注入（如 en-chat）
            persona = repo_root() / "agents" / "vendors" / "opencode" / "agents" / f"{cmd_id}.md"
            if persona.is_file():
                agent = cmd_id
        if agent:
            lines.append(f"agent: {agent}")
        return "---\n" + "\n".join(lines) + "\n---\n"
    if tool == "kimi-code":
        # commands 对 kimi 整体 skip；此分支仅作防御
        return "---\n" f"description: {desc_out}\n" "---\n"
    # codex prompts: minimal
    return "---\n" f"description: {desc_out}\n" "---\n"


def command_relpath(tool: str, cmd_id: str) -> str:
    if tool == "claude":
        if cmd_id.startswith("opsx-"):
            action = cmd_id[len("opsx-") :]
            return f"commands/opsx/{action}.md"
        return f"commands/{cmd_id}.md"
    if tool in ("codex", "pi"):
        return f"prompts/{cmd_id}.md"
    return f"commands/{cmd_id}.md"


def skill_relpath(skill_id: str) -> str:
    return f"skills/{skill_id}/SKILL.md"


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
        if dest.is_dir() and not dest.is_symlink():
            shutil.move(str(dest), str(backup_path))
        else:
            shutil.move(str(dest), str(backup_path))
        print(f"  已备份 {dest} → {backup_path}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content)
    return "write"


def validate_output(path: Path, content: str) -> None:
    if "{{" in content:
        leftovers = re.findall(r"\{\{[^}]+\}\}", content)
        die(f"{path}: residual placeholders: {leftovers}")


def targets_for_tool(tool: str, root: Path) -> List[Path]:
    """Base directories to install into (relative paths resolved under each)."""
    home = Path.home()
    if tool == "claude":
        return [home / ".claude", root / ".claude"]
    if tool == "cursor":
        return [home / ".cursor", root / ".cursor"]
    if tool == "opencode":
        # Generate into vendors/opencode/; user symlink covers ~/.config/opencode
        return [root / "agents" / "vendors" / "opencode"]
    if tool == "codex":
        return [home / ".codex"]
    if tool == "kimi-code":
        return [home / ".kimi-code"]
    if tool == "pi":
        return [home / ".pi" / "agent"]
    die(f"unknown tool: {tool}")
    return []


def sync_tool(tool: str, root: Path, dry_run: bool = False) -> int:
    agents = root / "agents"
    skills_root = agents / "skills"
    cmds_root = agents / "commands"
    if not skills_root.is_dir() and not cmds_root.is_dir():
        die(f"missing agents source under {agents}")

    bases = targets_for_tool(tool, root)
    written = 0
    skipped = 0

    print(f"==> sync {tool}")

    # Skills
    if skills_root.is_dir():
        for skill_dir in sorted(p for p in skills_root.iterdir() if p.is_dir()):
            skill_id = skill_dir.name
            src = skill_dir / "SKILL.md"
            if not src.is_file():
                continue
            if skill_excluded(skill_dir, tool):
                print(f"  skip skill {skill_id} (excluded for {tool})")
                continue
            meta, body = parse_frontmatter(src.read_text())
            body = replace_slashes(body, tool)
            content = render_skill_frontmatter(tool, meta, skill_id) + "\n" + body.lstrip("\n")
            if not content.endswith("\n"):
                content += "\n"
            rel = skill_relpath(skill_id)
            for base in bases:
                dest = base / rel
                validate_output(dest, content)
                status = install_file(content, dest, dry_run=dry_run)
                if status == "skip":
                    skipped += 1
                    print(f"  = {dest}")
                else:
                    written += 1
                    print(f"  + {dest}")

    # Commands（kimi-code 无稳定 commands 布局 → skip，不阻断 skills）
    if tool == "kimi-code":
        print("  skip commands for kimi-code (no stable commands layout)")
    elif cmds_root.is_dir():
        for cmd_file in sorted(cmds_root.glob("*.md")):
            cmd_id = cmd_file.stem
            if command_excluded(cmd_file, tool):
                print(f"  skip command {cmd_id} (excluded for {tool})")
                continue
            meta, body = parse_frontmatter(cmd_file.read_text())
            body = replace_slashes(body, tool)
            content = render_command_frontmatter(tool, meta, cmd_id) + "\n" + body.lstrip("\n")
            if not content.endswith("\n"):
                content += "\n"
            rel = command_relpath(tool, cmd_id)
            for base in bases:
                dest = base / rel
                validate_output(dest, content)
                status = install_file(content, dest, dry_run=dry_run)
                if status == "skip":
                    skipped += 1
                    print(f"  = {dest}")
                else:
                    written += 1
                    print(f"  + {dest}")

    print(f"  done {tool}: wrote={written} skipped={skipped}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Sync shared agents skills/commands to tools")
    parser.add_argument(
        "tool",
        nargs="?",
        default="all",
        help="claude|cursor|opencode|codex|kimi-code|pi|all",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--root", type=Path, default=None, help="dotfiles root (default: auto)")
    args = parser.parse_args(argv)

    root = args.root.resolve() if args.root else repo_root()
    tool = args.tool.lower()
    if tool == "all":
        tools = list(TOOLS)
    elif tool in TOOLS:
        tools = [tool]
    else:
        die(f"unknown tool '{tool}'. Use: {'|'.join(TOOLS)}|all")

    rc = 0
    for t in tools:
        try:
            sync_tool(t, root, dry_run=args.dry_run)
        except SystemExit as e:
            rc = int(e.code) if e.code else 1
            break
        except Exception as e:
            print(f"error syncing {t}: {e}", file=sys.stderr)
            rc = 1
            break
    return rc


if __name__ == "__main__":
    sys.exit(main())
