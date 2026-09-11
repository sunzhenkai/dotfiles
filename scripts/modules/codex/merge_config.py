#!/usr/bin/env python3
"""Merge Codex base config with optional local overlay.

When an installed ``config.toml`` is supplied, Codex-written ``[projects]``
tables that are not already present in the managed output are harvested.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tomllib
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

LOCAL_MARKER = (
    "\n# ============================================================\n"
    "# ↓↓↓ 以下来自 XDG dotf overlay（机器特定，不纳入 git） ↓↓↓\n"
)

PROJECT_HEADER_RE = re.compile(r"^\[projects(?:\.[^\]]*)?\]\s*$")


def expand_env(text: str, environ: dict[str, str] | None = None) -> str:
    """Replace ${VAR} from the environment; leave unknown placeholders intact."""
    env = os.environ if environ is None else environ

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        value = env.get(key)
        return value if value else match.group(0)

    return PLACEHOLDER_RE.sub(repl, text)


def project_keys(text: str) -> set[str]:
    try:
        document = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return set()
    projects = document.get("projects")
    if not isinstance(projects, dict):
        return set()
    return {str(key) for key in projects}


def extract_project_tables(text: str) -> list[str]:
    """Return raw ``[projects...]`` tables, omitting trailing comment footnotes."""
    lines = text.splitlines(keepends=True)
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        if not PROJECT_HEADER_RE.match(lines[index].rstrip("\n")):
            index += 1
            continue
        start = index
        index += 1
        while index < len(lines) and not lines[index].lstrip().startswith("["):
            index += 1
        block_lines = lines[start:index]
        while block_lines and block_lines[-1].lstrip().startswith("#"):
            block_lines.pop()
        while block_lines and not block_lines[-1].strip():
            block_lines.pop()
        if block_lines:
            blocks.append("".join(block_lines).rstrip() + "\n")
    return blocks


def harvest_runtime_projects(managed: str, actual: str | None) -> str:
    """Keep Codex-written ``[projects]`` that are not already in managed output."""
    if not actual or not actual.strip():
        return managed
    existing = project_keys(managed)
    extras: list[str] = []
    for block in extract_project_tables(actual):
        keys = project_keys(block)
        if not keys or keys <= existing:
            continue
        extras.append(block if block.endswith("\n") else f"{block}\n")
        existing |= keys
    if not extras:
        return managed
    text = managed if managed.endswith("\n") else f"{managed}\n"
    if not text.endswith("\n\n"):
        text += "\n"
    return text + "".join(extras)


def merge(
    base: str,
    local: str | None = None,
    actual: str | None = None,
) -> str:
    text = base
    if local and local.strip():
        if not text.endswith("\n"):
            text += "\n"
        text += LOCAL_MARKER + local
        if not text.endswith("\n"):
            text += "\n"
    return expand_env(harvest_runtime_projects(text, actual))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge Codex base + local")
    parser.add_argument("--base", type=Path, default=None)
    parser.add_argument("--local", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.base is None or args.output is None:
        parser.error("合并模式需要 --base 与 --output")

    base = args.base.read_text(encoding="utf-8")
    local = args.local.read_text(encoding="utf-8") if args.local else None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(merge(base, local), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
