"""Production registry config dispatch through the safe plan/apply API."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .config_deploy import ConfigDeployError, _load_registry_module, deploy_config
from .config_producers import producer_for
from .schemas import SchemaError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m dotf_core.config_handler")
    parser.add_argument("module")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--home", default=os.environ.get("HOME"))
    parser.add_argument("--state-home", default=None)
    parser.add_argument("--run-id", default=None)
    return parser


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
    try:
        result = deploy_config(
            module,
            repo_root=repo,
            home=args.home,
            state_home=args.state_home,
            producer=producer,
            run_id=args.run_id,
        )
    except (ConfigDeployError, SchemaError, OSError, ValueError) as exc:
        print(f"config deploy failed: {exc}", file=os.sys.stderr)
        return 1
    print(result.status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
