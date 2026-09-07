"""Module install / config fact persistence for the TUI manager.

Read by the TUI to display module status; written by the runner hook after each
action completes. The TUI itself never writes this file. Schema is deliberately
minimal: install / config facts are owned here; managed manifest owns config
hash / target / mode; XDG overlay owns Skill / MCP Desired Set. The three sources
never overlap.
"""

from __future__ import annotations

import datetime
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

CURRENT_SCHEMA_VERSION = 1
KNOWN_SCHEMA_VERSIONS = frozenset({None, 1, CURRENT_SCHEMA_VERSION})

INSTALL_ACTIONS = frozenset({"install"})
CONFIG_ACTIONS = frozenset({"config"})
DECONFIG_ACTIONS = frozenset({"deconfig"})
UNINSTALL_ACTIONS = frozenset({"uninstall"})
WRITABLE_ACTIONS = INSTALL_ACTIONS | CONFIG_ACTIONS | DECONFIG_ACTIONS | UNINSTALL_ACTIONS
SUCCESS_RESULTS = frozenset({"changed", "unchanged"})

Action = Literal["install", "config", "deconfig", "uninstall", "doctor", "retry"]
Result = Literal["changed", "unchanged", "skipped", "failed"]


def xdg_state_home(home: Path | None = None) -> Path:
    """Resolve XDG_STATE_HOME per spec; default ``$HOME/.local/state``."""
    configured = os.environ.get("XDG_STATE_HOME")
    if configured:
        path = Path(os.path.expanduser(configured))
        if not path.is_absolute():
            raise ValueError("XDG_STATE_HOME must be absolute")
        return path
    base = home or Path.home()
    return base / ".local" / "state"


def state_file_path(home: Path | None = None, state_home: Path | None = None) -> Path:
    """Return the canonical state file path.

    Resolution order: explicit ``state_home`` → ``XDG_STATE_HOME`` env → home-relative
    ``$HOME/.local/state``. Always ``<state_home>/dotf/modules-state.yaml``.
    """
    if state_home is None:
        state_home = xdg_state_home(home)
    return state_home / "dotf" / "modules-state.yaml"


@dataclass(frozen=True, slots=True)
class ModuleRecord:
    """Read-only projection of one module's install / config facts.

    Missing records surface as ``ModuleRecord(False, ...)`` so callers can
    render them as ``unknown`` without nullable gymnastics.
    """

    installed: bool
    last_install_at: str | None
    version: str | None
    path: str | None
    configured: bool
    last_config_at: str | None
    manifest_managed: int | None


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _coerce_module(value: Any) -> ModuleRecord:
    if not isinstance(value, dict):
        return ModuleRecord(False, None, None, None, False, None, None)
    install = value.get("install") if isinstance(value.get("install"), dict) else None
    config = value.get("config") if isinstance(value.get("config"), dict) else None
    return ModuleRecord(
        installed=install is not None,
        last_install_at=(install or {}).get("last_at") if install else None,
        version=(install or {}).get("version") if install else None,
        path=(install or {}).get("path") if install else None,
        configured=config is not None,
        last_config_at=(config or {}).get("last_at") if config else None,
        manifest_managed=(config or {}).get("manifest_managed") if config else None,
    )


def load_state(home: Path | None = None, state_home: Path | None = None) -> dict[str, ModuleRecord]:
    """Load and validate the state file. Always returns a mapping; never raises.

    Empty dict on: missing file, unreadable file, malformed YAML, non-dict root,
    unknown ``schema_version``, malformed ``modules`` mapping.
    """
    path = state_file_path(home, state_home)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as exc:
        logging.getLogger(__name__).warning("modules_state.load_state read failed: %s", exc)
        return {}
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        logging.getLogger(__name__).warning("modules_state.load_state yaml malformed: %s", exc)
        return {}
    if not isinstance(data, dict):
        return {}
    if data.get("schema_version") not in KNOWN_SCHEMA_VERSIONS:
        logging.getLogger(__name__).warning(
            "modules_state.load_state unknown schema_version %r, treating as unknown", data.get("schema_version")
        )
        return {}
    modules = data.get("modules")
    if not isinstance(modules, dict):
        return {}
    result: dict[str, ModuleRecord] = {}
    for name, value in modules.items():
        if not isinstance(name, str) or not name:
            continue
        result[name] = _coerce_module(value)
    return result


def _apply_to_dict(
    data: dict[str, Any],
    module: str,
    action: str,
    result: Result,
    *,
    version: str | None = None,
    path: str | None = None,
    manifest_managed: int | None = None,
) -> None:
    modules = data.get("modules")
    if not isinstance(modules, dict):
        modules = {}
        data["modules"] = modules
    now = _now_iso()

    if action in INSTALL_ACTIONS:
        if result in SUCCESS_RESULTS:
            record = modules.get(module) if isinstance(modules.get(module), dict) else {}
            install = record.get("install") if isinstance(record.get("install"), dict) else {}
            install["last_at"] = now
            if version:
                install["version"] = version
            if path:
                install["path"] = path
            record["install"] = install
            modules[module] = record
        # failed / skipped: do not write install
        return

    if action in CONFIG_ACTIONS:
        if result in SUCCESS_RESULTS:
            record = modules.get(module) if isinstance(modules.get(module), dict) else {}
            config = record.get("config") if isinstance(record.get("config"), dict) else {}
            config["last_at"] = now
            if manifest_managed is not None:
                config["manifest_managed"] = int(manifest_managed)
            record["config"] = config
            modules[module] = record
        return

    if action in DECONFIG_ACTIONS:
        record = modules.get(module)
        if isinstance(record, dict):
            record.pop("config", None)
        return

    if action in UNINSTALL_ACTIONS:
        if result in SUCCESS_RESULTS:
            modules.pop(module, None)
        return


def _atomic_write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".modules-state.", suffix=".yaml.tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            yaml.safe_dump(payload, fh, sort_keys=False, allow_unicode=True, default_flow_style=False)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def apply_result(
    module: str,
    action: str,
    result: Result,
    *,
    home: Path | None = None,
    state_home: Path | None = None,
    version: str | None = None,
    path: str | None = None,
    manifest_managed: int | None = None,
) -> bool:
    """Apply a single action result to the state file.

    Idempotent for repeat success results. Non-write actions (``doctor``,
    ``retry``) are no-ops. ``deconfig`` always strips ``config`` regardless
    of result (it is the deconfigure verb's contract). ``uninstall`` clears
    the module on success only. Write failures log a warning and return False
    without raising.
    """
    if action not in WRITABLE_ACTIONS:
        return True

    target = state_file_path(home, state_home)
    try:
        try:
            existing_raw = target.read_text(encoding="utf-8") if target.exists() else None
        except OSError as exc:
            logging.getLogger(__name__).warning("modules_state.read failed: %s", exc)
            existing_raw = None
        data = yaml.safe_load(existing_raw) if existing_raw else None
        if not isinstance(data, dict):
            data = {}
        data.setdefault("schema_version", CURRENT_SCHEMA_VERSION)
        _apply_to_dict(
            data,
            module,
            action,
            result,
            version=version,
            path=path,
            manifest_managed=manifest_managed,
        )
        _atomic_write_yaml(target, data)
        return True
    except Exception as exc:
        logging.getLogger(__name__).warning("modules_state.apply_result failed: %s", exc)
        return False


def main() -> int:  # pragma: no cover - convenience CLI
    import argparse

    parser = argparse.ArgumentParser(description="Show module-state summary.")
    parser.add_argument("--module", default=None)
    args = parser.parse_args()

    records = load_state()
    if args.module is not None:
        record = records.get(args.module) or ModuleRecord(False, None, None, None, False, None, None)
        print(f"{args.module}: installed={record.installed} configured={record.configured}")
        if record.last_install_at:
            print(f"  last_install_at: {record.last_install_at}")
        if record.last_config_at:
            print(f"  last_config_at: {record.last_config_at}")
        if record.version:
            print(f"  version: {record.version}")
        if record.path:
            print(f"  path: {record.path}")
        if record.manifest_managed is not None:
            print(f"  manifest_managed: {record.manifest_managed}")
        return 0

    print(f"modules-state: {len(records)} module(s) recorded")
    for name, record in sorted(records.items()):
        flags = []
        if record.installed:
            flags.append("installed")
        if record.configured:
            flags.append("configured")
        if not flags:
            flags.append("unknown")
        print(f"  {name}: {','.join(flags)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
