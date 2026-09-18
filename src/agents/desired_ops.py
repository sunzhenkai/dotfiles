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
from managed_runtime import (  # noqa: E402
    AgentRuntimeError,
    on_conflict_from_env,
    on_takeover_from_env,
    parse_on_conflict,
    parse_on_takeover,
)
from skills_catalog import SkillsCatalogError, load_skills_catalog  # noqa: E402
from sync import SyncOutcome, decide_takeover, summarize, sync_skills  # noqa: E402


def repo_root() -> Path:
    configured = os.environ.get("DOTFILES_ROOT")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[2]


def _third_party_ids(repo: Path) -> frozenset[str]:
    try:
        return frozenset(load_skills_catalog(repo).third_party_ids())
    except (SkillsCatalogError, OSError, UnicodeError):
        return frozenset()


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


def sync_all(repo: Path, artifact_id: str, *, on_conflict, on_takeover="skip") -> str:
    """Reconcile every source that can carry `artifact_id`; return a reason on failure.

    First-party skills come from the repository, locked third-party skills from
    an audited checkout. Applying either must run that source's installer, or the
    overlay records a skill that is never written to disk.
    """
    outcomes = sync_skills(repo, on_conflict=on_conflict, on_takeover=on_takeover)
    # `acquire_all` fetches per lock entry, so only pay for it when this artifact
    # actually comes from the lock. Otherwise a first-party apply would go to the
    # network for nothing.
    if artifact_id in _third_party_ids(repo):
        from defaults import install_defaults

        rc = install_defaults(repo, on_conflict=on_conflict, on_takeover=on_takeover)
        if rc:
            outcomes.append(SyncOutcome("locked third-party", rc, "install failed"))
    return summarize(outcomes)


def run_desired_op(
    action: str,
    selector: str,
    *,
    root: Path | None = None,
    on_conflict: str | None = None,
    on_takeover: str | None = None,
) -> int:
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
            catalog = load_skills_catalog(repo)
            canonical_id = catalog.canonical_id(artifact_id)
            if canonical_id is None or canonical_id not in approved_skill_ids(repo):
                raise DesiredSetError(f"拒绝未锁定或未知 skill: {artifact_id}")
            artifact_id = canonical_id
            policy = on_conflict_from_env() if on_conflict is None else parse_on_conflict(on_conflict)
            takeover = on_takeover_from_env() if on_takeover is None else parse_on_takeover(on_takeover)
            if on_takeover is None and takeover == "skip":
                takeover = decide_takeover(repo, on_conflict=policy)
            upsert_local_overlay(
                repo,
                lambda agents: _mutate_skill(agents, artifact_id, enable=enable),
            )
            reason = sync_all(repo, artifact_id, on_conflict=policy, on_takeover=takeover)
            if reason:
                _emit("failed", f"skill sync failed: {reason}", 1)
                return 1
            _emit("changed", f"skill {artifact_id} {'applied' if enable else 'removed'}")
            return 0
        raise DesiredSetError(f"不支持的制品: {selector}")
    except (DesiredSetError, OverlayError, AgentRuntimeError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        _emit("failed", str(exc), 1)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update Desired Set and sync one artifact")
    parser.add_argument("action", choices=("skill.apply", "skill.remove"))
    parser.add_argument("selector")
    parser.add_argument(
        "--on-conflict",
        choices=("block", "backup"),
        default=None,
        help="block（默认）本机改动即跳过该 Skill；backup 先备份再覆写已受管目标的漂移",
    )
    parser.add_argument(
        "--takeover",
        choices=("skip", "backup"),
        default=None,
        dest="on_takeover",
        help="skip（默认）跳过无所有权分歧目标；backup 先备份再接管",
    )
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    return run_desired_op(
        args.action,
        args.selector,
        root=args.root,
        on_conflict=args.on_conflict,
        on_takeover=args.on_takeover,
    )


if __name__ == "__main__":
    raise SystemExit(main())
