"""Strict external overlays for machine-private Agent and Codex settings.

Only sorted ``*.yaml`` files below ``${XDG_CONFIG_HOME:-~/.config}/dotf/overlays``
are loaded.  Documents are validated before and after deterministic deep merge;
unknown keys, invalid types, unsupported versions, and catalog cross references
fail closed.  This module never writes while loading.
"""

from __future__ import annotations

import argparse
import copy
import os
import re
import stat
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

OVERLAY_SCHEMA_VERSION = 1
OVERLAY_KIND = "dotf-overlay"
PROFILE_RE = re.compile(r"^[a-z][a-z0-9-]*$")

_TOP_KEYS = {"schema_version", "kind", "agents", "codex"}
_AGENT_KEYS = {"profile", "enabled_servers", "disabled_servers", "browser", "exclude"}
_BROWSER_KEYS = {
    "provider",
    "headed",
    "browser_executable",
    "user_data_dir",
    "artifact_dir",
    "cdp_endpoint",
    "use_real_profile",
}
_BROWSER_BOOL_KEYS = {"headed", "use_real_profile"}
_CODEX_KEYS = {"local_toml"}
_EXCLUDE_KEYS = {"servers"}


class OverlayError(ValueError):
    """An external overlay is malformed, unsafe, or incompatible."""


@dataclass(frozen=True, slots=True)
class OverlayCatalog:
    profiles: frozenset[str]
    servers: frozenset[str]
    tools: frozenset[str]


@dataclass(frozen=True, slots=True)
class LoadedOverlays:
    data: Mapping[str, Any]
    files: tuple[Path, ...]
    legacy_files: tuple[Path, ...] = ()

    @property
    def agents(self) -> dict[str, Any]:
        value = self.data.get("agents", {})
        return copy.deepcopy(value) if isinstance(value, dict) else {}

    @property
    def codex_local_toml(self) -> str | None:
        codex = self.data.get("codex", {})
        if not isinstance(codex, dict):
            return None
        value = codex.get("local_toml")
        return value if isinstance(value, str) and value.strip() else None


def xdg_config_home(home: Path | None = None) -> Path:
    configured = os.environ.get("XDG_CONFIG_HOME")
    if configured:
        path = Path(os.path.expanduser(configured))
        if not path.is_absolute():
            raise OverlayError("XDG_CONFIG_HOME must be an absolute path")
        return path
    base = home or Path.home()
    return base / ".config"


def overlay_directory(home: Path | None = None) -> Path:
    return xdg_config_home(home) / "dotf" / "overlays"


def _unknown(value: Mapping[str, Any], allowed: set[str], label: str) -> None:
    extra = sorted(set(value) - allowed)
    if extra:
        raise OverlayError(f"{label} contains unknown keys: {', '.join(extra)}")


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise OverlayError(f"{label} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise OverlayError(f"{label} keys must be strings")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OverlayError(f"{label} must be a non-empty string")
    return value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise OverlayError(f"{label} must be an array of non-empty strings")
    if len(set(value)) != len(value):
        raise OverlayError(f"{label} contains duplicate values")
    return value


def _validate_agents(value: Any, catalog: OverlayCatalog, label: str) -> dict[str, Any]:
    agents = _mapping(value, label)
    _unknown(agents, _AGENT_KEYS, label)
    profile = agents.get("profile")
    if profile is not None:
        profile = _string(profile, f"{label}.profile")
        if profile not in catalog.profiles:
            raise OverlayError(f"{label}.profile references unknown profile: {profile}")
    for key in ("enabled_servers", "disabled_servers"):
        if key not in agents:
            continue
        refs = _string_list(agents[key], f"{label}.{key}")
        unknown = sorted(set(refs) - catalog.servers)
        if unknown:
            raise OverlayError(f"{label}.{key} references unknown servers: {', '.join(unknown)}")
    if "browser" in agents:
        browser = _mapping(agents["browser"], f"{label}.browser")
        _unknown(browser, _BROWSER_KEYS, f"{label}.browser")
        for key, item in browser.items():
            if key in _BROWSER_BOOL_KEYS:
                if type(item) is not bool:
                    raise OverlayError(f"{label}.browser.{key} must be a boolean")
            else:
                _string(item, f"{label}.browser.{key}")
    if "exclude" in agents:
        exclude = _mapping(agents["exclude"], f"{label}.exclude")
        unknown_tools = sorted(set(exclude) - catalog.tools)
        if unknown_tools:
            raise OverlayError(f"{label}.exclude references unknown tools: {', '.join(unknown_tools)}")
        for tool, raw in exclude.items():
            config = _mapping(raw, f"{label}.exclude.{tool}")
            _unknown(config, _EXCLUDE_KEYS, f"{label}.exclude.{tool}")
            refs = _string_list(config.get("servers", []), f"{label}.exclude.{tool}.servers")
            unknown = sorted(set(refs) - catalog.servers)
            if unknown:
                raise OverlayError(
                    f"{label}.exclude.{tool}.servers references unknown servers: {', '.join(unknown)}"
                )
    return agents


def validate_overlay_document(value: Any, catalog: OverlayCatalog, *, label: str = "overlay") -> dict[str, Any]:
    doc = _mapping(value, label)
    _unknown(doc, _TOP_KEYS, label)
    if doc.get("schema_version") != OVERLAY_SCHEMA_VERSION or type(doc.get("schema_version")) is not int:
        raise OverlayError(f"{label}.schema_version must be {OVERLAY_SCHEMA_VERSION}")
    if doc.get("kind") != OVERLAY_KIND:
        raise OverlayError(f"{label}.kind must be {OVERLAY_KIND!r}")
    if "agents" in doc:
        _validate_agents(doc["agents"], catalog, f"{label}.agents")
    if "codex" in doc:
        codex = _mapping(doc["codex"], f"{label}.codex")
        _unknown(codex, _CODEX_KEYS, f"{label}.codex")
        if "local_toml" in codex:
            local_toml = _string(codex["local_toml"], f"{label}.codex.local_toml")
            try:
                tomllib.loads(local_toml)
            except tomllib.TOMLDecodeError as exc:
                raise OverlayError(f"{label}.codex.local_toml is malformed TOML") from exc
    return copy.deepcopy(doc)


def _deep_merge(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    """Merge mappings recursively; later scalar/list values replace earlier ones."""
    result = copy.deepcopy(dict(base))
    for key, value in overlay.items():
        current = result.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            result[key] = _deep_merge(current, value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _read_yaml_file(path: Path) -> Any:
    if path.is_symlink():
        raise OverlayError(f"overlay file must not be a symlink: {path}")
    item = path.stat()
    if not stat.S_ISREG(item.st_mode):
        raise OverlayError(f"overlay path is not a regular file: {path}")
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise OverlayError(f"cannot parse overlay YAML: {path}") from exc


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=True))
        return True
    except (ValueError, FileNotFoundError):
        return False


def legacy_agent_files(repo_root: Path) -> tuple[Path, ...]:
    env_dir = repo_root / "agents" / "env"
    found: set[Path] = set()
    found.update(path for path in env_dir.glob("local*.yaml") if path.is_file())
    local_dir = env_dir / "local"
    if local_dir.is_dir():
        found.update(path for path in local_dir.glob("*.yaml") if path.is_file())
    return tuple(sorted(found, key=lambda path: path.as_posix()))


def legacy_codex_file(repo_root: Path) -> Path | None:
    path = repo_root / "agents" / "vendors" / "codex" / "config.local.toml"
    return path if path.is_file() else None


def _warn_legacy(paths: Iterable[Path], destination: Path) -> None:
    paths = tuple(paths)
    if not paths:
        return
    joined = ", ".join(str(path) for path in paths)
    print(
        f"warning: deprecated repository-local config is read-only migration input: {joined}; "
        f"run 'PYTHONPATH=scripts python3 -m dotf_core.overlays migrate' to write {destination}",
        file=sys.stderr,
    )


def load_overlays(
    *,
    repo_root: Path,
    catalog: OverlayCatalog,
    home: Path | None = None,
    include_legacy: bool = True,
) -> LoadedOverlays:
    """Load validated overlays without creating or modifying any path."""
    repo = repo_root.resolve(strict=True)
    directory = overlay_directory(home)
    if _inside(directory, repo):
        raise OverlayError(f"overlay directory must be outside the repository: {directory}")

    merged: dict[str, Any] = {"schema_version": OVERLAY_SCHEMA_VERSION, "kind": OVERLAY_KIND}
    legacy: list[Path] = []
    if include_legacy:
        agent_files = legacy_agent_files(repo)
        for path in agent_files:
            raw = _read_yaml_file(path)
            wrapped = {
                "schema_version": OVERLAY_SCHEMA_VERSION,
                "kind": OVERLAY_KIND,
                "agents": raw if raw is not None else {},
            }
            validated = validate_overlay_document(wrapped, catalog, label=str(path))
            merged = _deep_merge(merged, validated)
        legacy.extend(agent_files)
        codex_path = legacy_codex_file(repo)
        if codex_path is not None:
            if codex_path.is_symlink():
                raise OverlayError(f"legacy Codex local config must not be a symlink: {codex_path}")
            local_toml = codex_path.read_text(encoding="utf-8")
            wrapped = {
                "schema_version": OVERLAY_SCHEMA_VERSION,
                "kind": OVERLAY_KIND,
                "codex": {"local_toml": local_toml},
            }
            validated = validate_overlay_document(wrapped, catalog, label=str(codex_path))
            merged = _deep_merge(merged, validated)
            legacy.append(codex_path)
        _warn_legacy(legacy, directory / "90-migrated.yaml")

    files: tuple[Path, ...] = ()
    if directory.exists():
        if directory.is_symlink() or not directory.is_dir():
            raise OverlayError(f"overlay root must be a real directory: {directory}")
        files = tuple(sorted(directory.glob("*.yaml"), key=lambda path: path.name.encode("utf-8")))
        for path in files:
            validated = validate_overlay_document(_read_yaml_file(path), catalog, label=str(path))
            merged = _deep_merge(merged, validated)
    validate_overlay_document(merged, catalog, label="merged overlay")
    return LoadedOverlays(merged, files, tuple(legacy))


def catalog_from_repo(repo_root: Path) -> OverlayCatalog:
    env_dir = repo_root / "agents" / "env"
    manifest = yaml.safe_load((env_dir / "manifest.yaml").read_text(encoding="utf-8")) or {}
    servers = yaml.safe_load((env_dir / "mcp" / "servers.yaml").read_text(encoding="utf-8")) or {}
    profiles = set()
    for path in sorted((env_dir / "mcp" / "profiles").glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        profiles.add(str(raw.get("id") or path.stem))
    return OverlayCatalog(
        profiles=frozenset(profiles),
        servers=frozenset((servers.get("servers") or {}).keys()),
        tools=frozenset(manifest.get("tools") or []),
    )


def _ensure_external_destination(repo_root: Path, destination: Path) -> None:
    if _inside(destination, repo_root):
        raise OverlayError(f"refusing to write overlay inside repository: {destination}")
    current = destination.parent
    while not current.exists() and current != current.parent:
        current = current.parent
    if current.is_symlink():
        raise OverlayError(f"overlay destination traverses a symlink: {current}")


def _write_new_overlay(repo_root: Path, destination: Path, data: Mapping[str, Any]) -> Path:
    _ensure_external_destination(repo_root, destination)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(destination.parent, 0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(destination, flags, 0o600)
    try:
        text = yaml.safe_dump(dict(data), allow_unicode=True, sort_keys=False)
        os.write(fd, text.encode("utf-8"))
        os.fchmod(fd, 0o600)
        os.fsync(fd)
    finally:
        os.close(fd)
    return destination


def init_overlay(repo_root: Path, *, home: Path | None = None) -> Path:
    destination = overlay_directory(home) / "00-local.yaml"
    data = {
        "schema_version": OVERLAY_SCHEMA_VERSION,
        "kind": OVERLAY_KIND,
        "agents": {"profile": "research"},
    }
    validate_overlay_document(data, catalog_from_repo(repo_root), label="initializer")
    return _write_new_overlay(repo_root, destination, data)


def migrate_legacy(repo_root: Path, *, home: Path | None = None) -> Path:
    catalog = catalog_from_repo(repo_root)
    loaded = load_overlays(repo_root=repo_root, catalog=catalog, home=home, include_legacy=True)
    if not loaded.legacy_files:
        raise OverlayError("no legacy Agent or Codex local configuration found")
    destination = overlay_directory(home) / "90-migrated.yaml"
    return _write_new_overlay(repo_root, destination, loaded.data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Initialize or migrate external dotf overlays")
    parser.add_argument("command", choices=("init", "migrate", "check"))
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args(argv)
    repo = args.repo_root.resolve(strict=True)
    try:
        if args.command == "init":
            path = init_overlay(repo)
            print(f"initialized external overlay: {path}")
        elif args.command == "migrate":
            path = migrate_legacy(repo)
            print(f"migrated legacy config to external overlay: {path}")
        else:
            loaded = load_overlays(repo_root=repo, catalog=catalog_from_repo(repo))
            print(f"overlay schema v{OVERLAY_SCHEMA_VERSION}: {len(loaded.files)} external file(s) valid")
        return 0
    except (OSError, OverlayError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
