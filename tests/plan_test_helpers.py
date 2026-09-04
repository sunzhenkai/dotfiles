"""Helpers for constructing fully valid isolated execution-plan fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import modules
import plan_protocol


def write_test_plan(
    path: Path,
    handlers: Path,
    actions: Iterable[tuple[str, str]],
    *,
    depends_on: dict[str, list[str]] | None = None,
    profile: str | None = None,
    requested_os: str | None = None,
) -> tuple[Path, Path]:
    action_list = list(actions)
    depends_on = depends_on or {}
    names: list[str] = []
    caps: dict[str, set[str]] = {}
    for action, name in action_list:
        if name not in names:
            names.append(name)
        caps.setdefault(name, set()).add(action)
    # Include dependencies that have no action only when explicitly requested by a test.
    for name, deps in depends_on.items():
        if name not in names:
            names.append(name)
        for dep in deps:
            if dep not in names:
                names.insert(0, dep)

    sources = path.parent / "sources"
    sources.mkdir(exist_ok=True)
    registry: list[dict] = []
    for name in names:
        item: dict = {"name": name, "doctor": True}
        if "install" in caps.get(name, set()):
            item["install"] = True
        if "config" in caps.get(name, set()):
            source = sources / f"{name}.conf"
            source.write_text(f"fixture {name}\n", encoding="utf-8")
            item["config"] = {
                "source": str(source),
                "target": str(path.parent / "home-targets" / name),
                "strategy": "copy",
                "writable": True,
                "sensitive": False,
                "target_mode": "0600",
                "preserve": [],
                "exclude": [],
            }
        if depends_on.get(name):
            item["depends_on"] = depends_on[name]
        registry.append(item)

    registry_path = path.parent / "modules.yaml"
    registry_path.write_text(
        "modules:\n" + "".join(
            "  - " + json.dumps(item, ensure_ascii=False) + "\n" for item in registry
        ),
        encoding="utf-8",
    )
    profiles_path = path.parent / "profiles.yaml"
    profiles = {"version": 1, "default": "test", "profiles": {"test": {"modules": [], "includes": []}}}
    profiles_path.write_text(json.dumps(profiles), encoding="utf-8")

    detected = modules.detect_os()
    requested_actions = [
        action for action in plan_protocol.ACTION_ORDER if any(a == action for a, _ in action_list)
    ]
    document = plan_protocol.make_document(
        requested_os=requested_os,
        detected_os=detected,
        planned_os=requested_os or detected,
        profile=profile,
        requested_actions=requested_actions,
        registry=registry,
        ordered_modules=names,
        actions=[
            {"index": index, "action": action, "module": name, "reason": "explicit"}
            for index, (action, name) in enumerate(action_list, 1)
        ],
        handlers_dir=handlers,
    )
    path.write_text(plan_protocol.dumps(document), encoding="utf-8")
    return registry_path, profiles_path


def plan_env(plan: Path, handlers: Path) -> dict[str, str]:
    return {
        "DOTF_HANDLERS_DIR": str(handlers),
        "DOTF_REGISTRY_PATH": str(plan.parent / "modules.yaml"),
        "DOTF_PROFILES_PATH": str(plan.parent / "profiles.yaml"),
    }
