#!/usr/bin/env python3
"""Merge OpenCode vendor providers into ~/.config/opencode/opencode.json.

All providers stay in the file. ``-f/--profile`` only moves the default
``model`` pointer (and records it in ``.dotf-profile``). MCP / agent /
local extra providers are preserved.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ALIASES = {
    "bigmodel": "zhipu",
    "zai": "zhipu",
}

# Default model pointer per profile. Provider blocks live in vendor opencode.json.
PROFILES: dict[str, dict[str, Any]] = {
    "minimax": {
        "model": "minimax/MiniMax-M3",
        "env": ("MINIMAX_API_KEY",),
    },
    "nativex": {
        "model": "nativex/gpt-5.6-luna",
        "env": ("NATIVEX_API_KEY",),
    },
    "company": {
        "model": "company/vanchin/deepseek-v4-pro-0813",
        "env": ("COMPANY_API_KEY", "COMPANY_BASE_URL"),
    },
    "kimi": {
        "model": "kimi/kimi-for-coding",
        "env": ("KIMI_API_KEY",),
    },
    "zhipu": {
        "model": "zhipu/glm-5.3",
        "env": ("ZHIPU_API_KEY",),
    },
    "scnet": {
        "model": "scnet/DeepSeek-V4-Flash-0731",
        "env": ("SCNET_API_KEY",),
    },
}

MANAGED_PROVIDER_IDS = tuple(PROFILES)


def resolve_profile_name(name: str) -> str:
    key = name.strip().lower()
    return ALIASES.get(key, key)


def alias_names(canonical: str) -> list[str]:
    return sorted(alias for alias, target in ALIASES.items() if target == canonical)


def list_profiles() -> list[str]:
    return list(PROFILES)


def profile_default_model(name: str) -> str:
    resolved = resolve_profile_name(name)
    info = PROFILES.get(resolved)
    if not info:
        return ""
    return str(info["model"])


def profile_env_keys(name: str) -> tuple[str, ...]:
    resolved = resolve_profile_name(name)
    info = PROFILES.get(resolved)
    if not info:
        return ()
    return tuple(info["env"])


def describe_profiles(current: str | None = None) -> str:
    if current:
        current = resolve_profile_name(current)
    lines = [
        "可用 OpenCode provider:",
        "",
        f"  {'NAME':<10} {'DEFAULT MODEL':<42} ALIAS",
    ]
    for name in list_profiles():
        model = profile_default_model(name)
        mark = "*" if current and name == current else " "
        aliases = ", ".join(alias_names(name))
        lines.append(f"{mark} {name:<10} {model:<42} {aliases}".rstrip())
    lines.append("")
    if current:
        lines.append(f"当前默认: {current}")
    lines.append("用法: dotf opencode -f <provider>")
    lines.append("单次会话: opencode -m <provider>/<model>")
    return "\n".join(lines) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} 不是 JSON object")
    return data


def merge(
    existing: dict[str, Any] | None,
    vendor: dict[str, Any],
    profile: str | None,
) -> dict[str, Any]:
    """Merge vendor-managed providers; optionally set default model."""
    if existing:
        out = dict(existing)
    else:
        out = {key: value for key, value in vendor.items() if key not in ("provider", "model")}

    vendor_providers = vendor.get("provider")
    if not isinstance(vendor_providers, dict):
        vendor_providers = {}
    current_providers = out.get("provider")
    if not isinstance(current_providers, dict):
        current_providers = {}
    merged_providers = dict(current_providers)
    for pid, pcfg in vendor_providers.items():
        merged_providers[pid] = pcfg
    out["provider"] = merged_providers

    if "$schema" not in out and "$schema" in vendor:
        out["$schema"] = vendor["$schema"]

    if profile:
        resolved = resolve_profile_name(profile)
        if resolved not in PROFILES:
            raise KeyError(resolved)
        out["model"] = PROFILES[resolved]["model"]
    elif "model" not in out:
        out["model"] = vendor.get("model") or PROFILES["minimax"]["model"]

    return out


def persist_profile(path: Path, name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(resolve_profile_name(name) + "\n", encoding="utf-8")


def read_persisted_profile(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge OpenCode providers + default model")
    parser.add_argument("--vendor", type=Path, default=None)
    parser.add_argument("--target", type=Path, default=None)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--persist-file", type=Path, default=None)
    parser.add_argument("--list-profiles", action="store_true")
    parser.add_argument("--describe-profiles", action="store_true")
    parser.add_argument("--current", default=None)
    parser.add_argument("--resolve", metavar="NAME", default=None)
    args = parser.parse_args(argv)

    if args.list_profiles:
        print("\n".join(list_profiles()))
        return 0

    if args.describe_profiles:
        sys.stdout.write(describe_profiles(args.current))
        return 0

    if args.resolve is not None:
        resolved = resolve_profile_name(args.resolve)
        if resolved not in PROFILES:
            print(f"未知 OpenCode provider: {args.resolve}", file=sys.stderr)
            sys.stderr.write(describe_profiles())
            return 2
        print(resolved)
        print(PROFILES[resolved]["model"])
        return 0

    if args.vendor is None or args.target is None:
        parser.error("合并模式需要 --vendor 与 --target")

    vendor = _read_json(args.vendor)
    existing = _read_json(args.target) if args.target.is_file() else None
    profile = args.profile
    if profile:
        profile = resolve_profile_name(profile)
        if profile not in PROFILES:
            print(f"未知 OpenCode provider: {args.profile}", file=sys.stderr)
            sys.stderr.write(describe_profiles())
            return 2

    out = merge(existing, vendor, profile)
    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.persist_file and profile:
        persist_profile(args.persist_file, profile)
    return 0


if __name__ == "__main__":
    sys.exit(main())
