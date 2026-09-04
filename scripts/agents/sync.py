#!/usr/bin/env python3
"""Install agents/ skills into shared and Kiro-specific runtime layouts."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from managed_runtime import (
    AgentRuntimeConflict,
    RenderSkill,
    apply_skills_plan,
    compile_skills_plan,
)

SLASH_RE = re.compile(r"\{\{slash:([a-z0-9-]+)\}\}")
FM_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.S)
POSITIONAL_RE = re.compile(r"\$\{\d+\}")
KIRO_SKILL_OWNER_PREFIX = "agents:kiro-skill:"
KIRO_SKILL_IDENTITY_PREFIX = "agents/skills:kiro"


def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def skills_target(home: Path | None = None) -> Path:
    return (home or Path.home()).expanduser().absolute() / ".agents" / "skills"


def kiro_home(home: Path | None = None) -> Path:
    """Resolve Kiro's global home; explicit home supplies HOME, not KIRO_HOME."""
    configured = os.environ.get("KIRO_HOME")
    if home is None and configured:
        return Path(configured).expanduser().absolute()
    return (home or Path.home()).expanduser().absolute() / ".kiro"


def kiro_skills_target(home: Path | None = None) -> Path:
    return kiro_home(home) / "skills"


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


def render_skill_bytes(skill_dir: Path, skill_id: str) -> bytes:
    """Render one SKILL.md without mutating source or destination state."""
    src = skill_dir / "SKILL.md"
    meta, body = parse_frontmatter(src.read_text(encoding="utf-8"))
    body = replace_slashes(body)
    content = render_skill_frontmatter(meta, skill_id) + "\n" + body.lstrip("\n")
    if not content.endswith("\n"):
        content += "\n"
    validate_output(src, content)
    return content.encode("utf-8")


def inject_kiro_arguments(body: str) -> str:
    """Kiro slash skills only receive arguments through an explicit marker."""
    if "$ARGUMENTS" in body or POSITIONAL_RE.search(body):
        return body
    return body.rstrip() + "\n\n$ARGUMENTS\n"


def render_kiro_skill_bytes(skill_dir: Path, skill_id: str) -> bytes:
    """Render one Kiro skill without mutating source or destination state."""
    src = skill_dir / "SKILL.md"
    content = render_skill_bytes(skill_dir, skill_id).decode("utf-8")
    marker = content.find("---\n", 1)
    if marker < 0:
        die(f"{src}: rendered frontmatter is malformed")
    body = content[marker + 4 :]
    content = content[: marker + 4] + inject_kiro_arguments(body)
    validate_output(src, content)
    return content.encode("utf-8")


def validate_output(path: Path, content: str) -> None:
    if "{{" in content:
        leftovers = re.findall(r"\{\{[^}]+\}\}", content)
        die(f"{path}: residual placeholders: {leftovers}")


def _sync_runtime(
    root: Path,
    base: Path,
    renderer: RenderSkill,
    *,
    owner_prefix: str,
    identity_prefix: str,
    label: str,
    dry_run: bool,
) -> int:
    print(f"==> sync {label} → {base}")
    plan = compile_skills_plan(
        root,
        renderer,
        target_root=base,
        owner_prefix=owner_prefix,
        identity_prefix=identity_prefix,
    )

    markers = {
        "none": "=",
        "create": "+",
        "update": "+",
        "chmod": "~",
        "prune": "-",
        "block": "!",
    }
    for operation in plan.operations:
        print(f"  {markers[operation.action]} {operation.target}")
        if operation.conflict:
            print(f"    conflict: {operation.conflict}")

    if dry_run:
        changed = sum(item.action in {"create", "update", "chmod"} for item in plan.operations)
        pruned = sum(item.action == "prune" for item in plan.operations)
        unchanged = sum(item.action == "none" for item in plan.operations)
        conflicts = len(plan.conflicts)
        print(
            f"  done {label} (plan): changed={changed} pruned={pruned} "
            f"unchanged={unchanged} conflicts={conflicts}"
        )
        return 1 if conflicts else 0

    try:
        result = apply_skills_plan(plan, renderer)
    except AgentRuntimeConflict as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        f"  done {label}: changed={result.changed} pruned={result.pruned} "
        f"unchanged={result.unchanged}"
    )
    return 0


def sync_skills(root: Path, dry_run: bool = False) -> int:
    return _sync_runtime(
        root,
        skills_target(),
        render_skill_bytes,
        owner_prefix="agents:skill:",
        identity_prefix="agents/skills",
        label="skills",
        dry_run=dry_run,
    )


def sync_kiro_skills(root: Path, dry_run: bool = False) -> int:
    """Kiro CLI does not consume ~/.agents, so keep a dedicated managed copy."""
    return _sync_runtime(
        root,
        kiro_skills_target(),
        render_kiro_skill_bytes,
        owner_prefix=KIRO_SKILL_OWNER_PREFIX,
        identity_prefix=KIRO_SKILL_IDENTITY_PREFIX,
        label="kiro skills",
        dry_run=dry_run,
    )


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
        description="Sync shared agents skills to ~/.agents/skills and Kiro CLI (tool 无关)"
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
        rc = sync_skills(root, dry_run=args.dry_run)
        if rc == 0:
            rc = sync_kiro_skills(root, dry_run=args.dry_run)
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
