"""Read-only Agent status derived from the managed manifest, never source links."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from dotf_core.schemas import SchemaError, validate_managed_manifest  # noqa: E402


@dataclass(frozen=True, slots=True)
class ManagedStatus:
    status: str
    message: str
    managed_count: int = 0


def manifest_path(home: Path | None = None, state_home: Path | None = None) -> Path:
    base_home = home or Path.home()
    if state_home is None:
        configured = os.environ.get("XDG_STATE_HOME")
        state_home = Path(configured) if configured else base_home / ".local" / "state"
    return state_home / "dotf" / "agents-manifest.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_agents_manifest(
    *,
    home: Path | None = None,
    state_home: Path | None = None,
    owners: Iterable[str] = ("agents", "config:agents"),
) -> ManagedStatus:
    """Validate owned Agent entries and actual hashes without reading source trees."""
    path = manifest_path(home, state_home)
    try:
        item = path.lstat()
    except FileNotFoundError:
        legacy = path.with_name("config-manifest.json")
        try:
            item = legacy.lstat()
        except FileNotFoundError:
            return ManagedStatus("missing", f"managed manifest missing: {path}")
        path = legacy
    if stat.S_ISLNK(item.st_mode) or not stat.S_ISREG(item.st_mode):
        return ManagedStatus("malformed", f"managed manifest is not a regular file: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        manifest = validate_managed_manifest(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, SchemaError, TypeError):
        return ManagedStatus("malformed", f"managed manifest is malformed or incompatible: {path}")

    allowed = set(owners)
    entries = [
        entry for entry in manifest.items
        if entry.owner in allowed or entry.owner.startswith("agents:skill:")
    ]
    if not entries:
        return ManagedStatus("missing", "managed manifest has no agents ownership entries")
    for entry in entries:
        target = Path(entry.target)
        try:
            target_item = target.lstat()
        except FileNotFoundError:
            return ManagedStatus("missing", f"managed agents target missing: {target}", len(entries))
        if stat.S_ISLNK(target_item.st_mode) or not stat.S_ISREG(target_item.st_mode):
            return ManagedStatus("conflict", f"managed agents target has unsafe type: {target}", len(entries))
        if _sha256(target) != entry.installed_hash:
            return ManagedStatus("changed", f"managed agents target changed: {target}", len(entries))
        if stat.S_IMODE(target_item.st_mode) != entry.mode:
            return ManagedStatus("permission", f"managed agents target mode differs: {target}", len(entries))
    return ManagedStatus("unchanged", f"managed manifest confirms {len(entries)} agents item(s)", len(entries))


def main() -> int:
    result = inspect_agents_manifest()
    if result.status == "unchanged":
        print(f"pass  config: {result.message}")
        return 0
    level = "warn" if result.status == "missing" else "fail"
    print(f"{level}  config: {result.message}")
    return 0 if level == "warn" else 1


if __name__ == "__main__":
    raise SystemExit(main())
