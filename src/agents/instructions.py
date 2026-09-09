#!/usr/bin/env python3
"""Install the global AGENTS.md into user-level Agent instruction targets."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import Optional

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from ensure_pyyaml import ensure_yaml
from managed_runtime import (
    AgentRuntimeConflict,
    AgentRuntimeError,
    RuntimeFile,
    SkillsPlan,
    apply_owned_plan,
    compile_owned_plan,
    resolve_state_home,
)
from dotf_core.paths import assert_path_confined

yaml = ensure_yaml()

OWNER_PREFIX = "agents:instructions:"
IDENTITY_PREFIX = "agents/instructions"
INSTALL_REL = Path("agents") / "instructions" / "install.yaml"
SOURCE_NAME = "AGENTS.md"
CURSOR_MDC_HEADER = (
    "---\n"
    "description: 跨项目全局 Agent 指令\n"
    "alwaysApply: true\n"
    "---\n\n"
)
_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_FORMATS = frozenset({"markdown", "cursor-mdc"})


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _source_bytes(body: str, fmt: str) -> bytes:
    text = body if body.endswith("\n") else body + "\n"
    if fmt == "markdown":
        return text.encode("utf-8")
    if fmt == "cursor-mdc":
        return (CURSOR_MDC_HEADER + text.lstrip("\n")).encode("utf-8")
    raise AgentRuntimeError(f"unsupported instruction format: {fmt}")


def _target_path(home: Path, spec: str) -> Path:
    if not isinstance(spec, str) or not spec.startswith("~/") or spec == "~/":
        raise AgentRuntimeError("instruction target path must be a ~/ relative path")
    relative = spec[2:]
    if relative.startswith("/") or "\x00" in relative:
        raise AgentRuntimeError(f"instruction target path is unsafe: {spec}")
    parts = Path(relative).parts
    if not parts or any(part in {".", ".."} for part in parts):
        raise AgentRuntimeError(f"instruction target path is unsafe: {spec}")
    return assert_path_confined(home, home / relative)


def load_install_spec(root: Path) -> tuple[Path, tuple[dict[str, str], ...]]:
    path = root / INSTALL_REL
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise AgentRuntimeError(f"cannot load instruction install spec: {path}") from exc
    if not isinstance(raw, dict) or set(raw) != {"version", "source", "targets"}:
        raise AgentRuntimeError("instruction install spec requires exactly version, source, targets")
    if raw["version"] != 1 or raw["source"] != SOURCE_NAME:
        raise AgentRuntimeError("instruction install spec version or source is unsupported")
    targets = raw["targets"]
    if not isinstance(targets, list) or not targets:
        raise AgentRuntimeError("instruction install spec targets must be a non-empty list")
    normalized: list[dict[str, str]] = []
    ids: set[str] = set()
    paths: set[str] = set()
    for item in targets:
        if not isinstance(item, dict) or set(item) != {"id", "path", "format"}:
            raise AgentRuntimeError("instruction target requires exactly id, path, format")
        target_id = item["id"]
        target_path = item["path"]
        fmt = item["format"]
        if not isinstance(target_id, str) or not _ID_RE.fullmatch(target_id):
            raise AgentRuntimeError(f"instruction target id is invalid: {target_id}")
        if target_id in ids:
            raise AgentRuntimeError(f"instruction target id is duplicated: {target_id}")
        if not isinstance(target_path, str) or target_path in paths:
            raise AgentRuntimeError(f"instruction target path is invalid or duplicated: {target_path}")
        if fmt not in _FORMATS:
            raise AgentRuntimeError(f"instruction target format is unsupported: {fmt}")
        ids.add(target_id)
        paths.add(target_path)
        normalized.append({"id": target_id, "path": target_path, "format": fmt})
    source = root / "agents" / "instructions" / SOURCE_NAME
    if not source.is_file() or source.is_symlink():
        raise AgentRuntimeError(f"missing global AGENTS.md source: {source}")
    return source, tuple(normalized)


def collect_instruction_files(root: Path, home: Path) -> tuple[RuntimeFile, ...]:
    source, targets = load_install_spec(root)
    body = source.read_text(encoding="utf-8")
    if body.lstrip().startswith("---"):
        raise AgentRuntimeError("global AGENTS.md must not use YAML frontmatter")
    files: list[RuntimeFile] = []
    seen: set[str] = set()
    for item in targets:
        target = _target_path(home, item["path"])
        content = _source_bytes(body, item["format"])
        identity = f"{IDENTITY_PREFIX}/{item['id']}"
        runtime = RuntimeFile(
            OWNER_PREFIX + item["id"],
            str(target),
            identity,
            _sha256(content),
            content,
            0o644,
        )
        if runtime.target in seen:
            raise AgentRuntimeError(f"instruction install produced duplicate target: {runtime.target}")
        seen.add(runtime.target)
        files.append(runtime)
    return tuple(files)


def compile_instructions_plan(
    root: Path,
    *,
    home: Path | None = None,
    state_home: Path | None = None,
) -> SkillsPlan:
    repo = root.expanduser().absolute()
    base_home = (home or Path.home()).expanduser().absolute()
    source_root = repo / "agents" / "instructions"
    expected = collect_instruction_files(repo, base_home)
    state = resolve_state_home(base_home, state_home)
    return compile_owned_plan(
        repo,
        expected,
        home=base_home,
        state=state,
        target_root=base_home,
        source_root=source_root,
        owner_prefix=OWNER_PREFIX,
        identity_prefix=IDENTITY_PREFIX,
    )


def apply_instructions_plan(plan: SkillsPlan, *, run_id: str | None = None):
    def compile_current() -> SkillsPlan:
        return compile_instructions_plan(
            Path(plan.repo_root),
            home=Path(plan.home),
            state_home=Path(plan.state_home),
        )

    return apply_owned_plan(plan, compile_current, run_id=run_id)


def _print_plan(plan: SkillsPlan, *, dry_run: bool) -> int:
    print(f"==> sync instructions → {plan.home}")
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
    changed = sum(item.action in {"create", "update", "chmod"} for item in plan.operations)
    pruned = sum(item.action == "prune" for item in plan.operations)
    unchanged = sum(item.action == "none" for item in plan.operations)
    conflicts = len(plan.conflicts)
    if dry_run:
        print(
            f"  done instructions (plan): changed={changed} pruned={pruned} "
            f"unchanged={unchanged} conflicts={conflicts}"
        )
        return 1 if conflicts else 0
    try:
        result = apply_instructions_plan(plan)
    except AgentRuntimeConflict as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        f"  done instructions: changed={result.changed} pruned={result.pruned} "
        f"unchanged={result.unchanged}"
    )
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync global AGENTS.md to user-level Agent instruction targets"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--root", type=Path, default=None, help="dotfiles root (default: auto)")
    args = parser.parse_args(argv)
    root = args.root.resolve() if args.root else repo_root()
    try:
        plan = compile_instructions_plan(root)
    except AgentRuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return _print_plan(plan, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
