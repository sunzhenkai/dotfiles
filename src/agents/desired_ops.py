"""Apply or remove one Skill by updating overlay then syncing."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
_AGENTS = Path(__file__).resolve().parent
for path in (_SCRIPTS, _AGENTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from desired_set import DesiredSetError, approved_skill_ids  # noqa: E402
from dotf_core.overlays import OverlayError, upsert_local_overlay  # noqa: E402
from dotf_core.plan_protocol import ProtocolError, parse_artifact_selector  # noqa: E402
from sync import sync_kiro_skills, sync_skills  # noqa: E402


def repo_root() -> Path:
    configured = os.environ.get("DOTFILES_ROOT")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[2]


def _unique(values: list[str], item: str, *, present: bool) -> list[str]:
    current = [value for value in values if value != item]
    if present:
        current.append(item)
    return sorted(set(current))


def _mutate_skill(agents: dict, skill_id: str, *, enable: bool) -> None:
    enabled = list(agents.get("enabled_skills") or [])
    disabled = list(agents.get("disabled_skills") or [])
    if enable:
        agents["enabled_skills"] = _unique(enabled, skill_id, present=True)
        agents["disabled_skills"] = _unique(disabled, skill_id, present=False)
    else:
        agents["enabled_skills"] = _unique(enabled, skill_id, present=False)
        agents["disabled_skills"] = _unique(disabled, skill_id, present=True)
    if not agents["enabled_skills"]:
        agents.pop("enabled_skills", None)
    if not agents["disabled_skills"]:
        agents.pop("disabled_skills", None)


def _emit(status: str, reason: str, exit_code: int = 0) -> None:
    module = os.environ.get("DOTF_MODULE", "")
    action = os.environ.get("DOTF_ACTION", "")
    reason = reason.replace("\t", " ").replace("\n", " ")
    print(f"RESULT\t{status}\t{module}\t{action}\t0\t{exit_code}\t{reason}")


def run_desired_op(action: str, selector: str, *, root: Path | None = None) -> int:
    repo = (root or repo_root()).resolve()
    try:
        kind, artifact_id, _tool = parse_artifact_selector(selector)
    except ProtocolError as exc:
        _emit("failed", str(exc), 1)
        return 1
    enable = action.endswith(".apply")
    try:
        if kind == "skill":
            if action not in {"skill.apply", "skill.remove"}:
                raise DesiredSetError(f"动作与选择器不匹配: {action} {selector}")
            if artifact_id not in approved_skill_ids(repo):
                raise DesiredSetError(f"拒绝未锁定或未知 skill: {artifact_id}")
            upsert_local_overlay(
                repo,
                lambda agents: _mutate_skill(agents, artifact_id, enable=enable),
            )
            skill_rc = sync_skills(repo)
            kiro_rc = sync_kiro_skills(repo)
            if skill_rc or kiro_rc:
                _emit("failed", "skill sync failed after overlay write", 1)
                return 1
            _emit("changed" if enable else "changed", f"skill {artifact_id} {'applied' if enable else 'removed'}")
            return 0
        raise DesiredSetError(f"不支持的制品: {selector}")
    except (DesiredSetError, OverlayError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        _emit("failed", str(exc), 1)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update Desired Set and sync one artifact")
    parser.add_argument("action", choices=("skill.apply", "skill.remove"))
    parser.add_argument("selector")
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    return run_desired_op(args.action, args.selector, root=args.root)


if __name__ == "__main__":
    raise SystemExit(main())
