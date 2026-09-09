#!/usr/bin/env python3
"""Explicit deterministic repository MCP template generator from committed safe inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

from adapters import ActualDocument, adapter_for
from common import Catalog, repo_root_from
from dotf_core.atomic import atomic_write

PROFILE = "full"
OUTPUTS = {
    "cursor": Path("agents/vendors/cursor/mcp.json"),
    "kiro": Path("agents/vendors/kiro/mcp.json"),
    "opencode": Path("agents/vendors/opencode/opencode.json"),
    "kimi-code": Path("agents/vendors/kimi-code/mcp.json"),
    "zcode": Path("agents/vendors/zcode/mcp.json"),
}
BASES = {"opencode": Path("agents/env/template-bases/opencode.json")}


def _actual(root: Path, tool: str, target: Path) -> ActualDocument:
    base = BASES.get(tool)
    if base is None:
        return ActualDocument("missing", target, None, None, None)
    raw = (root / base).read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"template base for {tool} must be a JSON object")
    return ActualDocument("present", target, raw, hashlib.sha256(raw).hexdigest(), None)


def render_templates(root: Path, tools: Iterable[str] = OUTPUTS) -> dict[Path, bytes]:
    """Render with overlays disabled and without any secret resolver."""
    catalog = Catalog(root, include_overlays=False)
    rendered: dict[Path, bytes] = {}
    for tool in tools:
        if tool not in OUTPUTS:
            raise ValueError(f"unsupported template tool: {tool}")
        adapter = adapter_for(catalog.vendor_matrix, tool)
        output = root / OUTPUTS[tool]
        selected = catalog.selected_servers(tool, PROFILE)
        servers = adapter.render(selected).servers
        payload = adapter.merge(_actual(root, tool, output), servers)
        # Safe source generation may retain variable references, never literal-at-apply values.
        if catalog.vendor_matrix.capability(tool).secret_mode == "literal-at-apply":
            assert b"${ZHIPU_API_KEY}" in payload
        rendered[output] = payload
    return rendered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate committed MCP templates from safe catalog sources")
    parser.add_argument("--check", action="store_true", help="compare only; do not write")
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    root = (args.root or repo_root_from(Path(__file__))).resolve()
    outputs = render_templates(root)
    drift = [path for path, payload in outputs.items() if not path.is_file() or path.read_bytes() != payload]
    if args.check:
        for path in drift:
            print(f"drift: {path.relative_to(root)}")
        return 1 if drift else 0
    for path, payload in outputs.items():
        atomic_write(path, payload, root=root, format="json", mode=0o644, sensitive=False)
        print(f"generated: {path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
