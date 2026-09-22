"""Production registry config dispatch through the safe plan/apply API."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import TextIO

from .config_deploy import (
    ConfigDeployError,
    ConfigPlan,
    OnTakeover,
    _load_registry_module,
    compile_config_plan,
    deploy_config,
    takeover_targets,
)
from .config_producers import producer_for
from .schemas import SchemaError

ON_TAKEOVER_ENV = "DOTF_TAKEOVER"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m dotf_core.config_handler")
    parser.add_argument("module")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--home", default=os.environ.get("HOME"))
    parser.add_argument("--state-home", default=None)
    parser.add_argument("--run-id", default=None)
    return parser


def _on_takeover_from_env(env: dict[str, str] | None = None) -> OnTakeover | None:
    """Explicit DOTF_TAKEOVER=skip|backup; unset means undecided."""
    raw = (env if env is not None else os.environ).get(ON_TAKEOVER_ENV)
    if not raw:
        return None
    policy = raw.strip().lower()
    if policy not in ("skip", "backup"):
        raise ValueError(f"unknown on-takeover policy: {raw!r} (expected skip or backup)")
    return policy  # type: ignore[return-value]


def _interactive_tty() -> tuple[TextIO, TextIO] | None:
    """Return controlling-terminal streams when the user can answer a prompt.

    The executor captures handler stdout/stderr (result parsing), so the
    prompt must go to /dev/tty; stdin still inherits the terminal. Tests and
    pipes have a non-TTY stdin, so they never touch /dev/tty.
    """
    if not sys.stdin.isatty():
        return None
    try:
        return (
            open("/dev/tty", "r", encoding="utf-8"),
            open("/dev/tty", "w", encoding="utf-8", buffering=1),
        )
    except OSError:
        return None


def _confirm_takeover(targets: list[str], *, tty_in: TextIO, tty_out: TextIO) -> bool:
    print(
        f"Takeover: {len(targets)} 个无主目标已存在且内容与受管版本不一致:",
        file=tty_out,
        flush=True,
    )
    for target in targets:
        print(f"  {target}", file=tty_out, flush=True)
    print(
        "备份原文件到 ${XDG_STATE_HOME:-~/.local/state}/dotf/backups/<run-id>/，"
        "然后写入受管内容并首次登记所有权？",
        file=tty_out,
        flush=True,
    )
    try:
        print("Takeover with backup? [y/N]: ", end="", file=tty_out, flush=True)
        answer = tty_in.readline().strip().lower()
    except (EOFError, OSError):
        return False
    return answer in {"y", "yes"}


def decide_takeover(plan, *, compile_backup) -> OnTakeover:
    """Resolve skip/backup for a plan blocked by unowned divergent files.

    Explicit DOTF_TAKEOVER wins without prompting; otherwise one aggregated
    confirmation runs on the controlling TTY. Non-TTY stays fail closed.
    """
    policy = _on_takeover_from_env()
    if policy is not None:
        return policy
    if not plan.conflicts:
        return "skip"
    streams = _interactive_tty()
    if streams is None:
        return "skip"
    tty_in, tty_out = streams
    try:
        # Probe with backup to enumerate exactly which conflicts Takeover can
        # resolve; symlink/type/foreign-owner conflicts stay blocked either way.
        backup_plan: ConfigPlan = compile_backup()
        candidates = list(takeover_targets(backup_plan))
        if not candidates:
            return "skip"
        if _confirm_takeover(candidates, tty_in=tty_in, tty_out=tty_out):
            return "backup"
        return "skip"
    finally:
        tty_in.close()
        tty_out.close()


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.home:
        raise SystemExit("HOME is required")
    repo = Path(args.repo_root).absolute()
    module = _load_registry_module(repo, args.module)
    strategy = module["config"]["strategy"]
    producer = None
    if strategy in {"merge", "render"}:
        producer = producer_for(args.module, repo_root=repo, home=args.home)

    def compile_plan(on_takeover: OnTakeover) -> ConfigPlan:
        return compile_config_plan(
            module,
            repo_root=repo,
            home=args.home,
            state_home=args.state_home,
            producer=producer,
            on_takeover=on_takeover,
        )

    try:
        plan = compile_plan("skip")
        on_takeover = decide_takeover(plan, compile_backup=lambda: compile_plan("backup"))
        result = deploy_config(
            module,
            repo_root=repo,
            home=args.home,
            state_home=args.state_home,
            producer=producer,
            run_id=args.run_id,
            on_takeover=on_takeover,
        )
    except (ConfigDeployError, SchemaError, OSError, ValueError) as exc:
        print(f"config deploy failed: {exc}", file=os.sys.stderr)
        return 1
    print(result.status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
