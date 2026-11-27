#!/usr/bin/env python3
"""Unified single-process orchestrator for agents sync."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence

_AGENTS = Path(__file__).resolve().parent
_SRC = _AGENTS.parent
for _path in (_SRC, _AGENTS):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from managed_runtime import (  # noqa: E402
    AgentRuntimeConflict,
    AgentRuntimeError,
    OnConflict,
    OnTakeover,
    on_conflict_from_env,
    on_takeover_from_env,
)


@dataclass(frozen=True, slots=True)
class StageResult:
    stage: str
    rc: int
    detail: str = ""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _progress(stage: str, index: int, total: int) -> None:
    print(f"PROGRESS\t{stage}\t{index}\t{total}", flush=True)


def _run_instructions(
    root: Path, *, dry_run: bool, on_conflict: OnConflict, on_takeover: OnTakeover
) -> StageResult:
    from instructions import apply_instructions_plan, compile_instructions_plan

    try:
        plan = compile_instructions_plan(
            root, on_conflict=on_conflict, on_takeover=on_takeover
        )
    except AgentRuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr, flush=True)
        return StageResult("instructions", 1, str(exc))

    print(f"==> sync instructions → {plan.home}", flush=True)
    markers = {
        "none": "=",
        "create": "+",
        "update": "+",
        "chmod": "~",
        "prune": "-",
        "block": "!",
    }
    for op in plan.operations:
        print(f"  {markers[op.action]} {op.target}", flush=True)
        if op.conflict:
            print(f"    conflict: {op.conflict}", flush=True)
    changed = sum(op.action in {"create", "update", "chmod"} for op in plan.operations)
    pruned = sum(op.action == "prune" for op in plan.operations)
    unchanged = sum(op.action == "none" for op in plan.operations)
    conflicts = len(plan.conflicts)
    if dry_run:
        print(
            f"  done instructions (plan): changed={changed} pruned={pruned} "
            f"unchanged={unchanged} conflicts={conflicts}",
            flush=True,
        )
        if conflicts:
            first = f"{plan.conflicts[0].target}: {plan.conflicts[0].conflict}"
            return StageResult("instructions", 1, first)
        return StageResult("instructions", 0)
    try:
        result = apply_instructions_plan(plan)
    except AgentRuntimeConflict as exc:
        print(f"error: {exc}", file=sys.stderr, flush=True)
        return StageResult("instructions", 1, str(exc))
    print(
        f"  done instructions: changed={result.changed} pruned={result.pruned} "
        f"unchanged={result.unchanged}",
        flush=True,
    )
    return StageResult("instructions", 0)


def _run_bridge(
    root: Path, *, dry_run: bool, on_conflict: OnConflict, on_takeover: OnTakeover
) -> StageResult:
    import antigravity_bridge
    from dotf_core.config_deploy import ConfigDeployError

    try:
        rc = antigravity_bridge.run(
            root,
            Path.home(),
            dry_run=dry_run,
            on_conflict=on_conflict,
            on_takeover=on_takeover,
        )
        return StageResult("bridge", rc, "bridge failed" if rc else "")
    except (ConfigDeployError, OSError, ValueError) as exc:
        print(f"error: antigravity bridge: {exc}", file=sys.stderr, flush=True)
        return StageResult("bridge", 1, str(exc))


def _run_skills(
    root: Path,
    *,
    dry_run: bool,
    on_conflict: OnConflict,
    on_takeover: OnTakeover,
    verbose: bool,
) -> StageResult:
    from sync import install_shims, summarize, sync_skills

    try:
        outcomes = sync_skills(
            root,
            dry_run=dry_run,
            on_conflict=on_conflict,
            on_takeover=on_takeover,
            verbose=verbose,
        )
    except SystemExit as exc:
        code = int(exc.code) if exc.code else 1
        return StageResult("skills", code, f"exit {code}")
    except Exception as exc:
        print(f"error syncing skills: {exc}", file=sys.stderr, flush=True)
        return StageResult("skills", 1, str(exc))

    rc = max((item.rc for item in outcomes), default=0)
    if rc != 0:
        detail = summarize(outcomes) or "failed"
        print(f"error: skills: {detail}", file=sys.stderr, flush=True)
        return StageResult("skills", rc, detail)
    print("==> shims", flush=True)
    install_shims(root, dry_run=dry_run)
    return StageResult("skills", 0)


def _run_defaults(
    root: Path, *, dry_run: bool, on_conflict: OnConflict, on_takeover: OnTakeover
) -> StageResult:
    from defaults import sync_defaults
    from sync import summarize
    from third_party import ThirdPartyLockError

    try:
        outcomes = sync_defaults(
            root,
            dry_run=dry_run,
            on_conflict=on_conflict,
            on_takeover=on_takeover,
        )
    except ThirdPartyLockError as exc:
        print(f"error: {exc}", file=sys.stderr, flush=True)
        return StageResult("defaults", 1, str(exc))

    rc = max((item.rc for item in outcomes), default=0)
    if rc != 0:
        detail = summarize(outcomes) or "failed"
        return StageResult("defaults", rc, detail)
    return StageResult("defaults", 0)


def _run_openspec(
    root: Path, *, dry_run: bool, on_conflict: OnConflict, on_takeover: OnTakeover
) -> StageResult:
    from openspec_skills import install_openspec_skills

    rc = install_openspec_skills(
        root,
        dry_run=dry_run,
        on_conflict=on_conflict,
        on_takeover=on_takeover,
    )
    return StageResult("openspec", rc, "openspec skills failed" if rc else "")


def _run_stub_script(script_path: Path, stage: str, root: Path, args: list[str]) -> StageResult:
    proc = subprocess.run(
        [sys.executable, str(script_path), "--root", str(root), *args],
        text=True,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.stderr:
        sys.stderr.write(proc.stderr)
        sys.stderr.flush()
    if proc.returncode != 0:
        detail = next(
            (
                line.removeprefix("error:").strip()
                for line in (proc.stderr or "").splitlines()
                if line.startswith("error:")
            ),
            f"exit {proc.returncode}",
        )
        return StageResult(stage, proc.returncode, detail)
    return StageResult(stage, 0)


def run_sync(
    root: Path,
    *,
    skills_only: bool = False,
    dry_run: bool = False,
    on_conflict: OnConflict | None = None,
    on_takeover: OnTakeover | None = None,
    verbose: bool = False,
) -> list[StageResult]:
    """Run all agents sync stages in one process and return per-stage results."""
    root = root.expanduser().resolve()
    conflict = on_conflict if on_conflict is not None else on_conflict_from_env()
    takeover = on_takeover if on_takeover is not None else on_takeover_from_env()
    verbose = verbose or os.environ.get("DOTF_VERBOSE", "") == "1"

    use_local_stubs = root != repo_root().resolve() and (root / "src" / "agents").is_dir()

    stages: list[tuple[str, str, Callable[[], StageResult]]] = []
    if not skills_only:
        if use_local_stubs:
            common = ["--dry-run"] if dry_run else []
            stages.append((
                "instructions",
                "--- instructions ---",
                lambda: _run_stub_script(root / "src" / "agents" / "instructions.py", "instructions", root, common),
            ))
            stages.append((
                "bridge",
                "--- antigravity bridge ---",
                lambda: _run_stub_script(root / "src" / "agents" / "antigravity_bridge.py", "bridge", root, common),
            ))
        else:
            stages.append((
                "instructions",
                "--- instructions ---",
                lambda: _run_instructions(root, dry_run=dry_run, on_conflict=conflict, on_takeover=takeover),
            ))
            stages.append((
                "bridge",
                "--- antigravity bridge ---",
                lambda: _run_bridge(root, dry_run=dry_run, on_conflict=conflict, on_takeover=takeover),
            ))

    if use_local_stubs:
        s_args: list[str] = []
        if dry_run:
            s_args.append("--dry-run")
        if verbose:
            s_args.append("--verbose")
        stages.append((
            "skills",
            "--- skills ---",
            lambda: _run_stub_script(root / "src" / "agents" / "sync.py", "skills", root, s_args),
        ))
        stages.append((
            "defaults",
            "--- default skills ---",
            lambda: _run_stub_script(root / "src" / "agents" / "defaults.py", "defaults", root, s_args),
        ))
        stages.append((
            "openspec",
            "--- openspec skills ---",
            lambda: _run_stub_script(root / "src" / "agents" / "openspec_skills.py", "openspec", root, s_args),
        ))
    else:
        stages.append((
            "skills",
            "--- skills ---",
            lambda: _run_skills(root, dry_run=dry_run, on_conflict=conflict, on_takeover=takeover, verbose=verbose),
        ))
        stages.append((
            "defaults",
            "--- default skills ---",
            lambda: _run_defaults(root, dry_run=dry_run, on_conflict=conflict, on_takeover=takeover),
        ))
        stages.append((
            "openspec",
            "--- openspec skills ---",
            lambda: _run_openspec(root, dry_run=dry_run, on_conflict=conflict, on_takeover=takeover),
        ))

    if not skills_only:
        print(f"agents sync  dry_run={int(dry_run)}", flush=True)

    total = len(stages)
    results: list[StageResult] = []
    for index, (stage, banner, fn) in enumerate(stages, start=1):
        _progress(stage, index, total)
        print(banner, flush=True)
        res = fn()
        results.append(res)
        if res.rc != 0:
            print(f"error: agents sync 阶段失败: {stage}（exit={res.rc}）", file=sys.stderr, flush=True)
    return results


def format_failure_summary(results: Sequence[StageResult]) -> tuple[int, str, list[str]]:
    """Return `(worst_rc, summary_line, detail_lines)` for failed stages."""
    failed = [r for r in results if r.rc != 0]
    if not failed:
        return 0, "", []
    rc = failed[-1].rc
    names = ", ".join(r.stage for r in failed)
    details = [f"{r.stage}: {r.detail}" if r.detail else r.stage for r in failed]
    first_detail = next((r.detail for r in failed if r.detail), "")
    reason_part = f" — {first_detail}" if first_detail else ""
    summary = f"agents sync 有阶段失败: {names}（exit={rc}）{reason_part}"
    return rc, summary, details


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Unified agents sync: instructions + bridge + first-party + defaults + openspec"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--on-conflict", choices=("block", "backup"), default=None)
    parser.add_argument("--takeover", choices=("skip", "backup"), default=None, dest="on_takeover")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--skills-only", action="store_true")
    parser.add_argument("--doctor", action="store_true")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("positional", nargs="*")
    args = parser.parse_args(argv)

    if args.doctor:
        print("error: --doctor 已不再作为 sync 旁路旗标", file=sys.stderr)
        print("请改用: dotf agents -d  或  dotf agents -cd", file=sys.stderr)
        return 1

    root = args.root.resolve() if args.root else repo_root()
    if args.on_conflict:
        os.environ["DOTF_ON_CONFLICT"] = args.on_conflict
    if args.on_takeover:
        os.environ["DOTF_TAKEOVER"] = args.on_takeover
    if args.verbose:
        os.environ["DOTF_VERBOSE"] = "1"

    results = run_sync(
        root,
        skills_only=args.skills_only,
        dry_run=args.dry_run,
        on_conflict=args.on_conflict,
        on_takeover=args.on_takeover,
        verbose=args.verbose,
    )
    rc, summary, details = format_failure_summary(results)
    if rc != 0:
        print(f"error: {summary}", file=sys.stderr, flush=True)
        for line in details:
            print(f"  ↳ {line}", file=sys.stderr, flush=True)
        return rc
    print("✓ agents sync 完成", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
