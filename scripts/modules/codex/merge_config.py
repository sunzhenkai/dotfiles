#!/usr/bin/env python3
"""Merge Codex base config with a profile overlay and optional local file.

Profile files (e.g. kimi.config.toml) only carry top-level scalars such as
model / model_provider / model_catalog_json. Those keys replace the same
keys in the base preamble (before the first [table]); other base content
is kept. Local projects are appended after a marker comment.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

TABLE_RE = re.compile(r"^\s*\[")
ASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=")
PLACEHOLDER_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

ALIASES = {
    "bigmodel": "zhipu",
    "zai": "zhipu",
}

LOCAL_MARKER = (
    "\n# ============================================================\n"
    "# ↓↓↓ 以下来自 agents/vendors/codex/config.local.toml（机器特定，不纳入 git） ↓↓↓\n"
)


def split_preamble(text: str) -> tuple[str, str]:
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if TABLE_RE.match(line):
            return "".join(lines[:i]), "".join(lines[i:])
    return text, ""


def parse_assignments(preamble: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in preamble.splitlines():
        match = ASSIGN_RE.match(line)
        if match:
            out[match.group(1)] = line
    return out


def overlay(base: str, profile: str) -> str:
    if not profile.strip():
        return base
    base_pre, base_rest = split_preamble(base)
    prof_pre, _ = split_preamble(profile)
    prof_assign = parse_assignments(prof_pre)
    if not prof_assign:
        return base

    lines: list[str] = []
    seen: set[str] = set()
    for line in base_pre.splitlines(keepends=True):
        raw = line.rstrip("\n")
        match = ASSIGN_RE.match(raw)
        if match and match.group(1) in prof_assign:
            lines.append(prof_assign[match.group(1)] + "\n")
            seen.add(match.group(1))
        else:
            if not line.endswith("\n"):
                line = line + "\n"
            lines.append(line)
    for key, value in prof_assign.items():
        if key not in seen:
            lines.append(value + "\n")
    return "".join(lines) + base_rest


def resolve_profile_name(name: str) -> str:
    key = name.strip().lower()
    return ALIASES.get(key, key)


def list_profiles(vendor_dir: Path) -> list[str]:
    suffix = ".config.toml"
    return sorted(
        path.name[: -len(suffix)]
        for path in vendor_dir.glob(f"*{suffix}")
        if path.name.endswith(suffix)
    )


def profile_path(vendor_dir: Path, name: str) -> Path:
    resolved = resolve_profile_name(name)
    return vendor_dir / f"{resolved}.config.toml"


def profile_default_model(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ASSIGN_RE.match(line)
        if match and match.group(1) == "model":
            value = line.split("=", 1)[1].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value
    return ""


def alias_names(canonical: str) -> list[str]:
    return sorted(alias for alias, target in ALIASES.items() if target == canonical)


def describe_profiles(vendor_dir: Path, current: str | None = None) -> str:
    names = list_profiles(vendor_dir)
    if current:
        current = resolve_profile_name(current)
    lines = [
        "可用 Codex profile:",
        "",
        f"  {'NAME':<10} {'DEFAULT MODEL':<28} ALIAS",
    ]
    for name in names:
        model = profile_default_model(profile_path(vendor_dir, name))
        mark = "*" if current and name == current else " "
        aliases = ", ".join(alias_names(name))
        lines.append(f"{mark} {name:<10} {model:<28} {aliases}".rstrip())
    lines.append("")
    if current:
        lines.append(f"当前默认: {current}")
    lines.append("用法: dotf codex -f <profile>")
    return "\n".join(lines) + "\n"


def expand_env(text: str, environ: dict[str, str] | None = None) -> str:
    """Replace ${VAR} from the environment; leave unknown placeholders intact."""
    env = os.environ if environ is None else environ

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        value = env.get(key)
        return value if value else match.group(0)

    return PLACEHOLDER_RE.sub(repl, text)


def merge(base: str, profile: str | None, local: str | None) -> str:
    text = overlay(base, profile or "")
    if local and local.strip():
        if not text.endswith("\n"):
            text += "\n"
        text += LOCAL_MARKER + local
        if not text.endswith("\n"):
            text += "\n"
    return expand_env(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge Codex base + profile + local")
    parser.add_argument("--vendor-dir", type=Path, default=None)
    parser.add_argument("--list-profiles", action="store_true")
    parser.add_argument("--describe-profiles", action="store_true")
    parser.add_argument("--current", default=None, help="当前默认 profile（describe 时标记）")
    parser.add_argument("--resolve", metavar="NAME", default=None)
    parser.add_argument("--base", type=Path, default=None)
    parser.add_argument("--profile", type=Path, default=None)
    parser.add_argument("--local", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.list_profiles or args.describe_profiles:
        if args.vendor_dir is None:
            parser.error("--list-profiles / --describe-profiles 需要 --vendor-dir")
        if args.describe_profiles:
            sys.stdout.write(describe_profiles(args.vendor_dir, args.current))
        else:
            print("\n".join(list_profiles(args.vendor_dir)))
        return 0

    if args.resolve is not None:
        if args.vendor_dir is None:
            parser.error("--resolve 需要 --vendor-dir")
        resolved = resolve_profile_name(args.resolve)
        path = profile_path(args.vendor_dir, resolved)
        if not path.is_file():
            print(f"未知 Codex profile: {args.resolve}", file=sys.stderr)
            sys.stderr.write(describe_profiles(args.vendor_dir))
            return 2
        print(resolved)
        print(path)
        return 0

    if args.base is None or args.output is None:
        parser.error("合并模式需要 --base 与 --output")

    base = args.base.read_text(encoding="utf-8")
    profile = args.profile.read_text(encoding="utf-8") if args.profile else None
    local = args.local.read_text(encoding="utf-8") if args.local else None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(merge(base, profile, local), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
