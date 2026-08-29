#!/usr/bin/env python3
"""Merge Codex base config with a profile overlay and optional local file.

Profile files (e.g. kimi.config.toml) only carry top-level scalars such as
model / model_provider / model_catalog_json. Those keys replace the same
keys in the base preamble (before the first [table]); other base content
is kept. Local projects are appended after a marker comment.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TABLE_RE = re.compile(r"^\s*\[")
ASSIGN_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=")

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
    path = vendor_dir / f"{resolved}.config.toml"
    return path


def merge(base: str, profile: str | None, local: str | None) -> str:
    text = overlay(base, profile or "")
    if local and local.strip():
        if not text.endswith("\n"):
            text += "\n"
        text += LOCAL_MARKER + local
        if not text.endswith("\n"):
            text += "\n"
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge Codex base + profile + local")
    parser.add_argument("--vendor-dir", type=Path, default=None)
    parser.add_argument("--list-profiles", action="store_true")
    parser.add_argument("--resolve", metavar="NAME", default=None)
    parser.add_argument("--base", type=Path, default=None)
    parser.add_argument("--profile", type=Path, default=None)
    parser.add_argument("--local", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.list_profiles:
        if args.vendor_dir is None:
            parser.error("--list-profiles 需要 --vendor-dir")
        print("\n".join(list_profiles(args.vendor_dir)))
        return 0

    if args.resolve is not None:
        if args.vendor_dir is None:
            parser.error("--resolve 需要 --vendor-dir")
        resolved = resolve_profile_name(args.resolve)
        path = profile_path(args.vendor_dir, resolved)
        names = list_profiles(args.vendor_dir)
        extra = sorted(set(ALIASES) - set(names))
        allowed = ", ".join(names + extra)
        if not path.is_file():
            print(f"未知 Codex profile: {args.resolve}（可用: {allowed}）", file=sys.stderr)
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
