#!/usr/bin/env python3
"""Runner hook: persist module fact after a successful action.

Invoked from ``scripts/run_plan.sh`` after each action result is determined.
Reads module / action / result from environment variables; write failures are
logged but never raise (the runner must not fail because of state persistence).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))

from dotf_core import modules_state  # noqa: E402


def _compute_manifest_managed(action: str, module: str) -> int | None:
    """Return managed-manifest entry count for this module, if available.

    Only meaningful for ``config`` action and only if the manifest is present;
    gracefully returns ``None`` otherwise.
    """
    if action != "config":
        return None
    try:
        from dotf_core.schemas import validate_managed_manifest
        from dotf_core.paths import xdg_state_home  # noqa: F401  (sanity import)

        manifest_path = (Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "dotf" / "agents-manifest.json")
        if not manifest_path.exists():
            return None
        import json
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = validate_managed_manifest(data)
        count = sum(1 for entry in manifest.items if entry.owner == f"config:{module}" or entry.owner.startswith(f"config:{module}:"))
        return count
    except Exception:
        return None


def main() -> int:
    module = os.environ.get("DOTF_STATE_MOD", "").strip()
    action = os.environ.get("DOTF_STATE_ACT", "").strip()
    result = os.environ.get("DOTF_STATE_RES", "").strip()
    if not module or not action or not result:
        return 0

    kwargs: dict = {}
    managed = _compute_manifest_managed(action, module)
    if managed is not None:
        kwargs["manifest_managed"] = managed

    ok = modules_state.apply_result(module, action, result, **kwargs)
    return 0 if ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
