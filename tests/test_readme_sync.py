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
