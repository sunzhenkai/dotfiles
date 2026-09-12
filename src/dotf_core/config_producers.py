"""Pure expected-content producers for registry merge/render declarations.

These callbacks may inspect only immutable source/actual bytes (plus Codex XDG
local overlay). They never write HOME, repository, or manifest state;
config_deploy retains all ownership and apply authority.
"""

from __future__ import annotations

import json
import os
import re
import tomllib
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


# ---- OpenCode provider 合并（原 scripts/modules/opencode/merge_config.py） ----

OPENCODE_DEFAULT_MODEL = "minimax/MiniMax-M3"
OPENCODE_MANAGED_PROVIDER_IDS = frozenset({"minimax", "kimi", "zhipu", "scnet", "deepseek"})


def opencode_merge(
    existing: dict[str, Any] | None,
    vendor: dict[str, Any],
) -> dict[str, Any]:
    """Merge vendor-managed providers; keep an existing default model."""
    if existing:
        out = dict(existing)
    else:
        out = {key: value for key, value in vendor.items() if key not in ("provider", "model")}

    vendor_providers = vendor.get("provider")
    if not isinstance(vendor_providers, dict):
        vendor_providers = {}
    current_providers = out.get("provider")
    if not isinstance(current_providers, dict):
        current_providers = {}
    merged_providers = dict(current_providers)
    for pid, pcfg in vendor_providers.items():
        merged_providers[pid] = pcfg
    out["provider"] = merged_providers

    if "$schema" not in out and "$schema" in vendor:
        out["$schema"] = vendor["$schema"]

    if "model" not in out:
        out["model"] = vendor.get("model") or OPENCODE_DEFAULT_MODEL

    return out


def _opencode_factory(repo_root: Path):
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

        actual_raw = context.actual_files.get("opencode.json")
        actual_doc = _json_object(actual_raw, label="OpenCode target")
        outputs.append(
            ProducedFile(
                "opencode.json",
                opencode_merge(actual_doc or None, source_doc),
                format="json",
                reconcile_owned=actual_raw is not None,
            )
        )
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


# ---- Codex base + XDG overlay 合并（原 scripts/modules/codex/merge_config.py） ----

_CODEX_PLACEHOLDER_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_CODEX_LOCAL_MARKER = (
    "\n# ============================================================\n"
    "# ↓↓↓ 以下来自 XDG dotf overlay（机器特定，不纳入 git） ↓↓↓\n"
)
_CODEX_PROJECT_HEADER_RE = re.compile(r"^\[projects(?:\.[^\]]*)?\]\s*$")


def codex_expand_env(text: str, environ: dict[str, str] | None = None) -> str:
    """Replace ${VAR} from the environment; leave unknown placeholders intact."""
    env = os.environ if environ is None else environ

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        value = env.get(key)
        return value if value else match.group(0)

    return _CODEX_PLACEHOLDER_RE.sub(repl, text)


def _codex_project_keys(text: str) -> set[str]:
    try:
        document = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return set()
    projects = document.get("projects")
    if not isinstance(projects, dict):
        return set()
    return {str(key) for key in projects}


def _codex_extract_project_tables(text: str) -> list[str]:
    """Return raw ``[projects...]`` tables, omitting trailing comment footnotes."""
    lines = text.splitlines(keepends=True)
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        if not _CODEX_PROJECT_HEADER_RE.match(lines[index].rstrip("\n")):
            index += 1
            continue
        start = index
        index += 1
        while index < len(lines) and not lines[index].lstrip().startswith("["):
            index += 1
        block_lines = lines[start:index]
        while block_lines and block_lines[-1].lstrip().startswith("#"):
            block_lines.pop()
        while block_lines and not block_lines[-1].strip():
            block_lines.pop()
        if block_lines:
            blocks.append("".join(block_lines).rstrip() + "\n")
    return blocks


def _codex_harvest_runtime_projects(managed: str, actual: str | None) -> str:
    """Keep Codex-written ``[projects]`` that are not already in managed output."""
    if not actual or not actual.strip():
        return managed
    existing = _codex_project_keys(managed)
    extras: list[str] = []
    for block in _codex_extract_project_tables(actual):
        keys = _codex_project_keys(block)
        if not keys or keys <= existing:
            continue
        extras.append(block if block.endswith("\n") else f"{block}\n")
        existing |= keys
    if not extras:
        return managed
    text = managed if managed.endswith("\n") else f"{managed}\n"
    if not text.endswith("\n\n"):
        text += "\n"
    return text + "".join(extras)


def codex_merge(
    base: str,
    local: str | None = None,
    actual: str | None = None,
) -> str:
    text = base
    if local and local.strip():
        if not text.endswith("\n"):
            text += "\n"
        text += _CODEX_LOCAL_MARKER + local
        if not text.endswith("\n"):
            text += "\n"
    return codex_expand_env(_codex_harvest_runtime_projects(text, actual))


def _codex_factory(repo_root: Path, home: Path):
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

        catalog_paths = {_catalog_relative(base_document, label="Codex base")}
        for relative, raw in sorted(context.source_files.items()):
            if relative.startswith("model-catalogs/") and relative.endswith(".json"):
                catalog_paths.add(relative)

        try:
            local = load_overlays(
                repo_root=repo_root,
                catalog=catalog_from_repo(repo_root),
                home=home,
            ).codex_local_toml
        except OverlayError as exc:
            raise ConfigDeployError(f"Codex external overlay is invalid: {exc}") from exc

        actual_raw = context.actual_files.get("config.toml")
        actual_text: str | None = None
        if actual_raw is not None:
            actual_text, _ = _toml_document(actual_raw, label="Codex target")

        outputs = [
            ProducedFile(
                "config.toml",
                codex_merge(base, local, actual=actual_text),
                format="toml",
                reconcile_owned=actual_raw is not None,
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
