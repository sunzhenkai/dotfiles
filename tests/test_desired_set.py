"""Desired Set 公式与 overlay 加法字段 — 隔离临时 HOME。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "agents"))

from desired_set import DesiredSetError, resolve_skill_desired_set  # noqa: E402
from defaults import first_party_skill_ids, selected_default_ids  # noqa: E402
from dotf_core.overlays import (  # noqa: E402
    OVERLAY_KIND,
    OVERLAY_SCHEMA_VERSION,
    OverlayCatalog,
    OverlayError,
    overlay_directory,
    validate_overlay_document,
)


def test_default_desired_set_is_first_party_plus_defaults() -> None:
    desired = resolve_skill_desired_set(ROOT, overlay_agents={})
    first = set(first_party_skill_ids(ROOT))
    defaults = set(selected_default_ids(ROOT))
    assert first <= desired
    assert defaults <= desired
    assert all(not item.startswith("openspec-") for item in desired)


def test_overlay_disable_removes_skill() -> None:
    desired = resolve_skill_desired_set(
        ROOT, overlay_agents={"disabled_skills": ["grill-with-docs"]}
    )
    assert "grill-with-docs" not in desired


def test_overlay_can_enable_locked_skill(tmp_path: Path) -> None:
    locked = set(selected_default_ids(ROOT))
    extra = "wayfinder"
    assert extra in locked
    desired = resolve_skill_desired_set(
        ROOT,
        overlay_agents={"enabled_skills": [extra], "disabled_skills": list(locked - {extra})},
    )
    assert extra in desired
    assert "grill-with-docs" not in desired


def test_unlocked_skill_rejected() -> None:
    with pytest.raises(DesiredSetError, match="unlocked"):
        resolve_skill_desired_set(ROOT, overlay_agents={"enabled_skills": ["not-a-real-skill"]})


def test_old_overlay_without_skill_keys_still_valid() -> None:
    catalog = OverlayCatalog(
        profiles=frozenset({"research"}),
        servers=frozenset({"web-reader"}),
        tools=frozenset({"cursor"}),
        skills=frozenset({"grill-with-docs"}),
    )
    doc = validate_overlay_document(
        {
            "schema_version": OVERLAY_SCHEMA_VERSION,
            "kind": OVERLAY_KIND,
            "agents": {"profile": "research", "disabled_servers": ["web-reader"]},
        },
        catalog,
    )
    assert "enabled_skills" not in doc["agents"]
    with pytest.raises(OverlayError, match="unlocked|unknown"):
        validate_overlay_document(
            {
                "schema_version": OVERLAY_SCHEMA_VERSION,
                "kind": OVERLAY_KIND,
                "agents": {"enabled_skills": ["floating"]},
            },
            catalog,
        )


def test_overlay_directory_stays_outside_repo(tmp_home: Path) -> None:
    directory = overlay_directory(tmp_home)
    assert directory.is_relative_to(tmp_home)
    assert not directory.is_relative_to(ROOT)
