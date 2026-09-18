#!/usr/bin/env python3
"""列出当前名册里可用的 Assignment（Endpoint + Model）。

只读、打 JSON（或 --render 的 Markdown 表），不写盘。模型来自画像默认值与
<data_root>/agents/models.yaml，不向各家 CLI 实时问模型列表。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import sys
from pathlib import Path

KIND_CLI = {
    "claude": "claude",
    "codex": "codex",
    "gemini": "gemini",
    "cursor": "cursor-agent",
    "opencode": "opencode",
    "qwen": "qwen",
    "kiro": "kiro-cli-chat",
    "copilot": "copilot",
    "pi": "pi",
}

HUMAN_STAGES = frozenset({"plan-review", "wrap-up"})
STAGE_IDS = (
    "understand",
    "plan",
    "plan-review",
    "implement",
    "code-review",
    "wrap-up",
)

MODEL_LINE = re.compile(
    r"^\s*-\s*\*\*模型\*\*\s*[:：]\s*(.+?)\s*$",
    re.MULTILINE,
)
CONFIG_DATA_ROOT = re.compile(
    r"^\s*data_root\s*:\s*(.+?)\s*$",
    re.MULTILINE,
)


def expand_user_path(raw: str) -> Path:
    return Path(os.path.expanduser(raw.strip().strip("'\""))).resolve()


def read_data_root(config_path: Path) -> Path:
    if not config_path.is_file():
        raise FileNotFoundError(f"missing agent-roster config: {config_path}")
    text = config_path.read_text(encoding="utf-8")
    match = CONFIG_DATA_ROOT.search(text)
    if not match:
        raise ValueError(f"data_root not set in {config_path}")
    return expand_user_path(match.group(1))


def parse_models_yaml(text: str) -> dict[str, list[str]]:
    """Parse the tiny Kind → list subset used by models.yaml. Stdlib only."""
    result: dict[str, list[str]] = {}
    current: str | None = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            if current is None:
                raise ValueError(f"orphaned models.yaml item: {stripped}")
            result.setdefault(current, []).append(stripped[2:].strip().strip("'\""))
            continue
        if stripped.endswith(":"):
            current = stripped[:-1].strip()
            result.setdefault(current, [])
            continue
        raise ValueError(f"unsupported models.yaml line: {line}")
    return result


def load_models_catalog(data_root: Path) -> dict[str, list[str]]:
    path = data_root / "agents" / "models.yaml"
    if not path.is_file():
        return {}
    return parse_models_yaml(path.read_text(encoding="utf-8"))


def default_model_from_portrait(text: str) -> str | None:
    match = MODEL_LINE.search(text)
    if not match:
        return None
    value = match.group(1).strip().strip("`'\"")
    if not value:
        return None
    lowered = value.lower()
    if "留空" in value or "探测不到" in value or value.startswith("<"):
        return None
    if lowered in {"-", "n/a", "none", "null"}:
        return None
    return value


def merge_models(default: str | None, catalog: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in ([default] if default else []) + catalog:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def probe_available(kind: str) -> bool | None:
    cli = KIND_CLI.get(kind)
    if not cli:
        return None
    return shutil.which(cli) is not None


def iter_endpoint_files(data_root: Path) -> list[Path]:
    agents = data_root / "agents"
    if not agents.is_dir():
        return []
    files: list[Path] = []
    for host_dir in sorted(p for p in agents.iterdir() if p.is_dir()):
        if host_dir.name in {"traces", "examples"}:
            continue
        files.extend(sorted(host_dir.glob("*.md")))
    return files


def collect_endpoints(data_root: Path, probe: bool) -> list[dict]:
    catalog = load_models_catalog(data_root)
    rows: list[dict] = []
    for path in iter_endpoint_files(data_root):
        if path.name.lower() == "readme.md":
            continue
        host = path.parent.name
        kind = path.stem
        portrait = path.read_text(encoding="utf-8")
        default = default_model_from_portrait(portrait)
        available = probe_available(kind) if probe else None
        rows.append(
            {
                "endpoint": f"{host}/{kind}",
                "host": host,
                "kind": kind,
                "available": available,
                "default_model": default,
                "models": merge_models(default, catalog.get(kind, [])),
                "portrait": str(path),
            }
        )
    return rows


def render_markdown(payload: dict) -> str:
    lines = [
        "| # | Endpoint | Models | available |",
        "|---|----------|--------|-----------|",
    ]
    index = 1
    if payload.get("human_allowed"):
        lines.append(f"| {index} | `human` | — | — |")
        index += 1
    for row in payload["endpoints"]:
        models = ", ".join(row["models"]) if row["models"] else "（手打）"
        avail = row["available"]
        if avail is True:
            flag = "yes"
        elif avail is False:
            flag = "no"
        else:
            flag = "—"
        lines.append(f"| {index} | `{row['endpoint']}` | {models} | {flag} |")
        index += 1
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=STAGE_IDS, default="implement")
    parser.add_argument("--probe", action="store_true", help="L1：CLI 是否在 PATH")
    parser.add_argument("--render", action="store_true", help="输出 Markdown 表")
    parser.add_argument(
        "--config",
        default=os.path.expanduser("~/.config/agent-roster/config.yaml"),
        help="agent-roster config.yaml",
    )
    parser.add_argument("--data-root", default=None, help="绕过 config，直接指定 data_root")
    args = parser.parse_args()

    try:
        data_root = (
            expand_user_path(args.data_root)
            if args.data_root
            else read_data_root(Path(args.config))
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    payload = {
        "host": socket.gethostname(),
        "data_root": str(data_root),
        "stage": args.stage,
        "human_allowed": args.stage in HUMAN_STAGES,
        "endpoints": collect_endpoints(data_root, args.probe),
    }
    if args.render:
        print(render_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
