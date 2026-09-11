#!/usr/bin/env python3
"""Merge OpenCode vendor providers into ~/.config/opencode/opencode.json.

Vendor-managed provider blocks are refreshed. MCP / agent / local extra
providers and an existing default ``model`` pointer are preserved.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "minimax/MiniMax-M3"
MANAGED_PROVIDER_IDS = frozenset({"minimax", "kimi", "zhipu", "scnet", "deepseek"})


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} 不是 JSON object")
    return data


def merge(
    existing: dict[str, Any] | None,
    vendor: dict[str, Any],
) -> dict[str, Any]:
    """Merge vendor-managed providers; keep an existing default model."""
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

    if "model" not in out:
        out["model"] = vendor.get("model") or DEFAULT_MODEL

    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge OpenCode providers")
    parser.add_argument("--vendor", type=Path, default=None)
    parser.add_argument("--target", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.vendor is None or args.target is None:
        parser.error("合并模式需要 --vendor 与 --target")

    vendor = _read_json(args.vendor)
    existing = _read_json(args.target) if args.target.is_file() else None
    out = merge(existing, vendor)
    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
