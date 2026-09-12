"""README 与注册表/profile 元数据一致性抽检。"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def test_readme_mentions_profiles() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    profiles = yaml.safe_load((ROOT / "profiles.yaml").read_text(encoding="utf-8"))
    for name in (profiles.get("profiles") or {}):
        assert name in readme, f"README 缺少 profile: {name}"


def test_readme_mentions_status_retry_bootstrap() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for needle in ("bootstrap", "status", "retry", "modules.yaml", "profiles.yaml"):
        assert needle in readme


def test_readme_agents_source_listing_matches_repo() -> None:
    """README 的 agents 源码清单必须指向真实存在的文件/目录（skills-defaults 漂移回归）。"""
    import re

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    match = re.search(r"agents/\{([^}]+)\}", readme)
    assert match, "README 缺少 agents 源码清单"
    for name in match.group(1).split(","):
        name = name.strip()
        assert (ROOT / "agents" / name).exists(), (
            f"README agents 清单指向不存在的条目: {name}"
        )
