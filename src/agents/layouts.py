"""Skill runtime layouts: where a Skill is installed, and who owns it there.

`sync` (first-party), `defaults` (locked third-party), and `openspec_skills`
all install the same Skill into the same set of layouts, so the layout list and
the owner/identity prefixes derived from it live here rather than being repeated
per installer.

Owner prefixes must stay distinct per layout. The runtime manifest is shared by
every layout, and `apply_owned_plan` retains an existing entry only when its
owner does *not* start with the plan's owner prefix; two layouts sharing a
prefix would drop each other's entries from the manifest.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Source = Literal["first-party", "third-party", "openspec"]
RenderKind = Literal["shared", "kiro"]

# Owner prefix stem per source; shared keeps the historical bare names.
_SOURCE_STEM = {"first-party": "skill", "third-party": "third-party", "openspec": "openspec"}


@dataclass(frozen=True, slots=True)
class SkillLayout:
    key: str
    label: str
    home_dir: str
    env_var: str | None
    owner_infix: str
    identity_suffix: str
    render: RenderKind
    reserved_ids: frozenset[str] = frozenset()


SHARED = SkillLayout("shared", "skills", ".agents", None, "", "", "shared")
KIRO = SkillLayout("kiro", "kiro skills", ".kiro", "KIRO_HOME", "kiro-", ":kiro", "kiro")
CLAUDE = SkillLayout(
    "claude",
    "claude skills",
    ".claude",
    None,
    "claude-",
    ":claude",
    "shared",
    # Claude Code downloads claude.ai skills into ~/.claude/skills/synced and
    # skips user-authored skills at that name.
    reserved_ids=frozenset({"synced"}),
)

LAYOUTS: tuple[SkillLayout, ...] = (SHARED, KIRO, CLAUDE)
SHARED_LAYOUT = SHARED
LAYOUTS_BY_KEY = {layout.key: layout for layout in LAYOUTS}

# Identity bases per source; `identity_prefix` appends the layout's suffix. The
# third-party base is completed with the lock digest by the caller.
FIRST_PARTY_IDENTITY = "agents/skills"
THIRD_PARTY_IDENTITY = "agents/skills.lock.yaml"
OPENSPEC_IDENTITY = "openspec-cli"


def owner_prefix(layout: SkillLayout, source: Source) -> str:
    return f"agents:{layout.owner_infix}{_SOURCE_STEM[source]}:"


def identity_prefix(layout: SkillLayout, base: str) -> str:
    return base + layout.identity_suffix


def layout_home(layout: SkillLayout, home: Path | None = None) -> Path:
    """Resolve a layout's home; an explicit home supplies HOME, not the env override."""
    if home is None and layout.env_var:
        configured = os.environ.get(layout.env_var)
        if configured:
            return Path(configured).expanduser().absolute()
    return (home or Path.home()).expanduser().absolute() / layout.home_dir


def skills_target(layout: SkillLayout, home: Path | None = None) -> Path:
    return layout_home(layout, home) / "skills"


def home_for_target(destination: Path) -> Path:
    """Infer HOME from a layout destination (`<home>/<dotdir>/skills`)."""
    destination = destination.expanduser().absolute()
    if destination.name == "skills" and destination.parent.name.startswith("."):
        return destination.parent.parent
    return Path.home().expanduser().absolute()


def layout_for_target(destination: Path) -> SkillLayout | None:
    destination = destination.expanduser().absolute()
    if destination.name != "skills":
        return None
    return next(
        (layout for layout in LAYOUTS if layout.home_dir == destination.parent.name),
        None,
    )
