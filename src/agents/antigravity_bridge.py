#!/usr/bin/env python3
"""Deploy Antigravity's global skill-discovery bridge from the agents sync pipeline.

The bridge is `~/.gemini/config/skills.json`, which points Antigravity at the
single `~/.agents/skills` tree instead of a third copy of the skills. The
registry keeps the declaration (`antigravity.config`) as the single source of
truth; this stage reuses it so `dotf agents -c` covers the bridge too.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from managed_runtime import on_conflict_from_env, on_takeover_from_env

from dotf_core import registry as modules
from dotf_core.config_deploy import (
    ConfigDeployError,
    compile_config_plan,
    deploy_config,
)
from dotf_core.config_producers import producer_for

MODULE = "antigravity"
BRIDGE = Path(".gemini") / "config" / "skills.json"


def _module(root: Path) -> dict:
    module = modules.find_module(modules.load_registry(root / "modules.yaml"), MODULE)
    if module is None or not modules.has_config(module):
        raise ConfigDeployError(f"registry has no {MODULE} config declaration")
    return module


def detected(home: Path) -> bool:
    """Antigravity is installed, or we already manage its bridge file.

    Without detection the stage would create `~/.gemini/config/` on machines
    that do not run Antigravity at all.
    """
    return (
        (home / ".gemini" / "antigravity").is_dir()
        or (home / BRIDGE).exists()
        or (home / BRIDGE).is_symlink()
    )


def run(
    root: Path,
    home: Path,
    *,
    dry_run: bool = False,
    on_conflict: str | None = None,
    on_takeover: str | None = None,
) -> int:
    home = home.expanduser().absolute()
    if not detected(home):
        print("  skip antigravity bridge: 未检测到 Antigravity")
        return 0
    module = _module(root)
    producer = producer_for(MODULE, repo_root=root, home=home)
    policy = on_conflict or on_conflict_from_env()
    takeover = on_takeover or on_takeover_from_env()
    print(f"==> antigravity bridge → {home / BRIDGE}", flush=True)

    if dry_run:
        plan = compile_config_plan(
            module,
            repo_root=root,
            home=home,
            producer=producer,
            on_conflict=policy,
            on_takeover=takeover,
        )
        markers = {"create": "+", "update": "+", "chmod": "~", "prune": "-", "block": "!", "none": "="}
        for operation in plan.operations:
            print(f"  {markers.get(operation.item.action, '?')} {operation.item.target}")
            if operation.item.state == "conflict":
                print(f"    conflict: {operation.item.conflict_reason}")
        print(
            "  done antigravity bridge (plan): "
            f"changed={sum(1 for op in plan.operations if op.item.action in {'create', 'update', 'chmod'})} "
            f"pruned={sum(1 for op in plan.operations if op.item.action == 'prune')} "
            f"unchanged={sum(1 for op in plan.operations if op.item.action == 'none')} "
            f"conflicts={len(plan.conflicts)}"
        )
        return 1 if plan.conflicts else 0

    result = deploy_config(
        module,
        repo_root=root,
        home=home,
        producer=producer,
        on_conflict=policy,
        on_takeover=takeover,
    )
    print(
        f"  done antigravity bridge: changed={result.changed} "
        f"pruned={result.pruned} unchanged={result.unchanged}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deploy Antigravity's skills.json bridge")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--home", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--on-conflict", choices=("block", "backup"), default=None)
    parser.add_argument("--takeover", choices=("skip", "backup"), default=None)
    args = parser.parse_args(argv)
    try:
        return run(
            args.root.expanduser().absolute(),
            args.home or Path.home(),
            dry_run=args.dry_run,
            on_conflict=args.on_conflict,
            on_takeover=args.takeover,
        )
    except (ConfigDeployError, OSError, ValueError) as exc:
        print(f"error: antigravity bridge: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
