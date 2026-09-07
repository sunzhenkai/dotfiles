"""Build the same planner argv the CLI uses for a TUI selection."""

from __future__ import annotations

from collections.abc import Sequence

from .catalog import MODULE_ACTIONS, Selectable


def planner_argv(items: Sequence[Selectable]) -> list[str]:
    if not items:
        raise ValueError("selection is empty")
    if any(item.action == "update" for item in items):
        raise ValueError("update is not a supported action")
    actions: list[str] = []
    selectors: list[str] = []
    for item in items:
        if item.action not in actions:
            actions.append(item.action)
        if item.selector not in selectors:
            selectors.append(item.selector)
    module_actions = [action for action in MODULE_ACTIONS if action in actions]
    agent_actions = [action for action in actions if action not in MODULE_ACTIONS]
    ordered = module_actions + agent_actions
    return [
        "plan",
        "--actions",
        ",".join(ordered),
        "--modules",
        ",".join(selectors),
        "--format",
        "machine",
    ]
