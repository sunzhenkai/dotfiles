"""Pure expected-content producers for registry merge/render declarations.

These callbacks may inspect only immutable source/actual bytes (plus explicit,
repository-confined Codex profile inputs). They never write HOME, repository,
or manifest state; config_deploy retains all ownership and apply authority.
"""

from __future__ import annotations

import importlib.util
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .config_deploy import ConfigDeployError, ProducedContent, ProducedFile, ProducerContext
from .overlays import OverlayError, catalog_from_repo, load_overlays


def _json_object(raw: bytes | None, *, label: str) -> dict[str, Any]:
    if raw is None:
        return {}
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigDeployError(f"{label} is malformed JSON") from exc
    if not isinstance(value, dict):
        raise ConfigDeployError(f"{label} must contain a JSON object")
    return value


def _deep_overlay(base: Mapping[str, Any], managed: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in managed.items():
        current = result.get(key)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            result[key] = _deep_overlay(current, value)
        else:
            result[key] = value
    return result


def _copy_single(context: ProducerContext) -> ProducedContent:
    return ProducedContent(context.source_files["."])



def _private_overlay(base: Mapping[str, Any], managed: Mapping[str, Any]) -> dict[str, Any]:
    """Overlay public defaults without replacing machine-private plugin fields."""
    result = dict(base)
    for key, value in managed.items():
        normalized = "".join(char for char in key.lower() if char.isalnum())
        private = any(
            marker in normalized
            for marker in (
                "token",
                "secret",
                "credential",
                "account",
                "workspace",
                "path",
                "apikey",
            )
        )
        if private and key in result:
            continue
        current = result.get(key)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            result[key] = _private_overlay(current, value)
        else:
            result[key] = value
    return result

def _preserve_single(context: ProducerContext) -> ProducedContent:
    return ProducedContent(context.actual_files.get(".", context.source_files["."]))


def _ocr(context: ProducerContext) -> list[ProducedFile]:
    source = _json_object(context.source_files.get("config.json"), label="OCR source")
    actual = _json_object(context.actual_files.get("config.json"), label="OCR target")
    return [ProducedFile("config.json", _deep_overlay(actual, source), format="json")]


def _load_opencode_merge(repo_root: Path):
    path = repo_root / "scripts" / "modules" / "opencode" / "merge_config.py"
    spec = importlib.util.spec_from_file_location("dotf_opencode_merge_config", path)
    if spec is None or spec.loader is None:
        raise ConfigDeployError("cannot load OpenCode merge producer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _opencode_factory(repo_root: Path):
    merge_module = _load_opencode_merge(repo_root)

    def produce(context: ProducerContext) -> list[ProducedFile]:
        outputs: list[ProducedFile] = []
        source_doc: dict[str, Any] | None = None
        for path, content in sorted(context.source_files.items()):
            if path.startswith("agents/") and path.endswith(".md"):
                outputs.append(ProducedFile(path, content))
            elif path == "plugins.json":
                outputs.append(ProducedFile(path, content, format="json"))
            elif path == "opencode.json":
                source_doc = _json_object(content, label="OpenCode source")
        if source_doc is None:
            raise ConfigDeployError("OpenCode source is missing opencode.json")

        requested = os.environ.get("DOTF_OPENCODE_PROFILE", "").strip()
        profile: str | None = None
        if requested:
            resolved = merge_module.resolve_profile_name(requested)
            if resolved not in merge_module.PROFILES:
                raise ConfigDeployError(f"unknown OpenCode profile: {requested}")
            profile = resolved
        else:
            persisted_raw = context.actual_files.get(".dotf-profile")
            if persisted_raw is not None:
                try:
                    persisted = persisted_raw.decode("utf-8").strip()
                except UnicodeDecodeError:
                    persisted = ""
                if persisted:
                    resolved = merge_module.resolve_profile_name(persisted)
                    if resolved in merge_module.PROFILES:
                        profile = resolved

        actual_doc = _json_object(
            context.actual_files.get("opencode.json"), label="OpenCode target"
        )
        outputs.append(
            ProducedFile(
                "opencode.json",
                merge_module.merge(actual_doc or None, source_doc, profile),
                format="json",
            )
        )
        if profile:
            outputs.append(ProducedFile(".dotf-profile", profile + "\n"))
        return outputs

    return produce


def _pi(context: ProducerContext) -> list[ProducedFile]:
    managed = _json_object(context.source_files.get("settings.json"), label="Pi settings source")
    actual_settings = _json_object(
        context.actual_files.get("settings.json"), label="Pi settings target"
    )
    settings = dict(actual_settings)
    settings.update(managed)

    defaults = _json_object(context.source_files.get("auth.json.example"), label="Pi auth source")
    auth = _json_object(context.actual_files.get("auth.json"), label="Pi auth target")
    for provider, default in defaults.items():
        existing = auth.get(provider)
        if not (
            isinstance(existing, dict)
            and existing.get("type")
            and existing.get("key")
        ):
            auth[provider] = default
    return [
        ProducedFile("settings.json", settings, format="json"),
        ProducedFile("auth.json", auth, format="json"),
    ]


def _logseq(context: ProducerContext) -> list[ProducedFile]:
    outputs: list[ProducedFile] = []
    for path, source in sorted(context.source_files.items()):
        if path == ".gitignore":
            continue
        if path.endswith(".json"):
            managed = _json_object(source, label=f"Logseq source {path}")
            actual = _json_object(context.actual_files.get(path), label=f"Logseq target {path}")
            outputs.append(
                ProducedFile(
                    path,
                    _private_overlay(actual, managed),
                    format="json",
                    reconcile_owned=True,
                )
            )
        else:
            outputs.append(ProducedFile(path, source))
    return outputs


def _kiro(context: ProducerContext) -> list[ProducedFile]:
    return [ProducedFile("settings/mcp.json", context.source_files["mcp.json"], format="json")]


def _zcode(context: ProducerContext) -> list[ProducedFile]:
    return [ProducedFile("cli/config.json", context.source_files["mcp.json"], format="json")]


def _load_codex_merge(repo_root: Path):
    path = repo_root / "scripts" / "modules" / "codex" / "merge_config.py"
    spec = importlib.util.spec_from_file_location("dotf_codex_merge_config", path)
    if spec is None or spec.loader is None:
        raise ConfigDeployError("cannot load Codex merge producer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _codex_factory(repo_root: Path, home: Path):
    merge_module = _load_codex_merge(repo_root)

    def _toml_document(raw: bytes, *, label: str) -> tuple[str, dict[str, Any]]:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ConfigDeployError(f"{label} is not UTF-8") from exc
        try:
            import tomllib

            document = tomllib.loads(text)
        except (ImportError, ValueError) as exc:
            raise ConfigDeployError(f"{label} is malformed TOML") from exc
        return text, document

    def _catalog_relative(document: Mapping[str, Any], *, label: str) -> str:
        value = document.get("model_catalog_json")
        prefix = "~/.codex/"
        if not isinstance(value, str) or not value.startswith(prefix):
            raise ConfigDeployError(
                f"{label} model_catalog_json must be below ~/.codex"
            )
        relative = value[len(prefix) :]
        if not relative.startswith("model-catalogs/"):
            raise ConfigDeployError(
                f"{label} model_catalog_json must reference model-catalogs"
            )
        return relative

    def produce(context: ProducerContext) -> list[ProducedFile]:
        base_raw = context.source_files.get("config.toml")
        if base_raw is None:
            raise ConfigDeployError("Codex source is missing config.toml")
        base, base_document = _toml_document(base_raw, label="Codex base")

        profiles: dict[str, str] = {}
        catalog_paths = {_catalog_relative(base_document, label="Codex base")}
        for relative, raw in sorted(context.source_files.items()):
            if not relative.endswith(".config.toml"):
                continue
            name = relative[: -len(".config.toml")]
            profile_text, profile_document = _toml_document(
                raw, label=f"Codex profile {name}"
            )
            profiles[name] = profile_text
            catalog_paths.add(
                _catalog_relative(profile_document, label=f"Codex profile {name}")
            )

        requested = os.environ.get("DOTF_CODEX_PROFILE", "").strip()
        profile_text: str | None = None
        if requested:
            resolved = merge_module.resolve_profile_name(requested)
            try:
                profile_text = profiles[resolved]
            except KeyError as exc:
                raise ConfigDeployError(f"unknown Codex profile: {requested}") from exc

        try:
            local = load_overlays(
                repo_root=repo_root,
                catalog=catalog_from_repo(repo_root),
                home=home,
            ).codex_local_toml
        except OverlayError as exc:
            raise ConfigDeployError(f"Codex external overlay is invalid: {exc}") from exc

        outputs = [
            ProducedFile(
                "config.toml",
                merge_module.merge(base, profile_text, local),
                format="toml",
            )
        ]
        for relative in sorted(catalog_paths):
            try:
                catalog = context.source_files[relative]
            except KeyError as exc:
                raise ConfigDeployError(
                    f"Codex referenced catalog is missing: {relative}"
                ) from exc
            outputs.append(ProducedFile(relative, catalog, format="json"))
        return outputs

    return produce


def producer_for(
    module_name: str, *, repo_root: os.PathLike[str] | str, home: os.PathLike[str] | str
):
    """Return the reviewed pure producer for one merge/render declaration."""
    repo = Path(repo_root).absolute()
    home_path = Path(home).absolute()
    factories = {
        "ocr": _ocr,
        "agents": _copy_single,
        "cursor": _copy_single,
        "kiro": _kiro,
        "kimi-code": _preserve_single,
        "pi": _pi,
        "zcode": _zcode,
        "logseq": _logseq,
    }
    if module_name == "codex":
        return _codex_factory(repo, home_path)
    if module_name == "opencode":
        return _opencode_factory(repo)
    try:
        return factories[module_name]
    except KeyError as exc:
        raise ConfigDeployError(
            f"strategy module {module_name} has no reviewed pure producer"
        ) from exc
