#!/usr/bin/env python3
"""agents/env 共享加载、合并与校验逻辑。"""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# agents/ 下运行时把 scripts/ 加入 path，复用无感安装
_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from catalog import (  # noqa: E402
    CatalogError,
    load_catalog_documents,
    load_manifest_tools,
)
from dotf_core.overlays import (  # noqa: E402
    OverlayError,
    catalog_from_repo,
    load_overlays,
)

_DEFAULT_ROOT = Path(__file__).resolve().parents[2]
TOOLS = load_manifest_tools(_DEFAULT_ROOT)


def die(msg: str, code: int = 1) -> None:
    raise SystemExit(f"error: {msg}")


def repo_root_from(here: Path) -> Path:
    return here.resolve().parents[2]


def agent_env_dir(root: Path) -> Path:
    return root / "agents" / "env"


def deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for key, val in overlay.items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = deep_merge(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out


class Catalog:
    def __init__(self, root: Path, *, include_overlays: bool = True):
        self.root = root
        self.env_dir = agent_env_dir(root)
        try:
            documents = load_catalog_documents(root)
        except CatalogError as exc:
            die(f"catalog 校验失败: {exc}")
        self.manifest = documents.manifest
        self.env_schema = documents.env_schema
        self.tools = documents.tools
        self.security = documents.security
        self.profiles = documents.profiles
        if include_overlays:
            try:
                self.overlays = load_overlays(
                    repo_root=root,
                    catalog=catalog_from_repo(root),
                )
            except OverlayError as exc:
                die(f"overlay 校验失败: {exc}")
            self.local = self.overlays.agents
        else:
            # Explicit repository generation must depend only on committed safe
            # catalog sources, never machine overlays, legacy locals, or secrets.
            self.overlays = None
            self.local = {}
        self.errors: List[str] = []
        self.validate()

    def default_profile(self) -> str:
        if isinstance(self.local.get("profile"), str):
            return self.local["profile"]
        return str(self.manifest["default_profile"])

    def validate(self) -> None:
        # Committed documents were validated as one cross-referenced catalog before
        # overlays were loaded. Only the external overlay can alter this selection.
        profile = self.default_profile()
        if profile not in self.profiles:
            die(f"overlay 引用未知 profile: {profile}")
        self.errors = []

    def resolve_profile(self, profile: Optional[str] = None) -> Dict[str, Any]:
        name = profile or self.default_profile()
        if name not in self.profiles:
            die(f"未知 profile: {name}（可选: {', '.join(sorted(self.profiles))}）")
        return self.profiles[name]
